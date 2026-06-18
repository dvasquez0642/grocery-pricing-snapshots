"""
Data loader for the pricing dashboard.

Scans *_prices.csv files from the data directory, normalizes timestamps
and schemas, filters junk rows, and produces a clean unified DataFrame.

The data directory defaults to ``wayback grocery AO/data/`` relative to
this file, but can be overridden by setting the ``DATA_DIR`` environment
variable.
"""

import os
import re
import warnings
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
import streamlit as st

from categories import categorize_series
from geocoder import geocode_series

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# Data directory: configurable via DATA_DIR env var, defaults to
# wayback grocery AO/data/ relative to this script's location.
_DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "wayback grocery AO" / "data"
DATA_DIR = Path(os.environ.get("DATA_DIR", str(_DEFAULT_DATA_DIR)))

# Skip files larger than this (bytes) -- the 12GB megamart, 770MB namaste, 206MB trucchis
MAX_FILE_SIZE_BYTES = 200 * 1024 * 1024  # 200 MB

# Standard column schema (9 columns)
STANDARD_COLS = [
    "timestamp", "chain", "location", "product_name",
    "price", "unit", "sale", "description", "wayback_url",
]

# Minimum columns required to load a file
REQUIRED_COLS = {"timestamp", "product_name", "price"}

# Max product name length (filter HTML dumps)
MAX_PRODUCT_NAME_LEN = 200

# Regex to detect HTML in product names
_RE_HTML = re.compile(r"<[a-zA-Z/][^>]*>")

# Regex for Wayback-style timestamp: YYYYMMDDHHmmss (14 digits)
_RE_WAYBACK_TS = re.compile(r"^\d{14}$")

# Pre-built parquet file (committed to repo — the primary data source on
# Streamlit Cloud where rebuilding from 203 CSVs would exceed boot timeout).
_PREBUILT_PARQUET = Path(__file__).resolve().parent / "data" / "pricing.parquet"

# Runtime parquet cache (generated on first CSV load, gitignored)
_PARQUET_CACHE = Path(__file__).resolve().parent / "_pricing_cache.parquet"

# Combined junk-substring regex (compiled once, used vectorized)
_JUNK_SUBSTRINGS = [
    "unknown product", "weekly circular", "can i know when",
    "frequently asked", "javascript", "<!doctype",
    "http://", "https://", "gift card", "gift certificate",
    "e-gift", "egift", "default title",
]
_RE_JUNK = re.compile("|".join(re.escape(p) for p in _JUNK_SUBSTRINGS), re.IGNORECASE)

# Reject product names that are entirely a price pattern
# Matches: "$3.07", "$59.95 $37.99", "$9.99 - $69.99", "$10.99/lb.", etc.
_RE_PRICE_NAME = re.compile(
    r"\s*\$?\s*\d+[.,]?\s*\d*"
    r"(?:\s+\$\d+[.,]?\d*)*"
    r"(?:\s*[-]\s*\$?\d+[.,]?\d*)*"
    r"(?:\s*[/]\s*\$?\d*[.,]?\d*)*"
    r"(?:\s*(?:lb|oz|fl\s*oz|ea|each|per\s*lb|per\s*oz|ct|pk|gal)\.?\s*)*"
    r"[)\s.]*",
    re.IGNORECASE,
)

# Names that are purely a quantity + unit: "12 FL OZ", "1 LB", "6 CT"
_RE_UNIT_ONLY = re.compile(
    r"\s*\d+\.?\d*\s*(?:fl\s*oz|oz|lb|lbs|ct|pk|pt|qt|gal|ml|l|kg|g)\s*",
    re.IGNORECASE,
)

# Bare numbers with no product text: "8", "11.99", "1199"
_RE_BARE_NUMBER = re.compile(r"\s*\d+\.?\d*\s*")

# Bare placeholders: "Unknown", "N/A", "None", "Description", "Default Title",
# "Starting At", "Your product's name", "/ person"
_RE_PLACEHOLDER = re.compile(
    r"\s*(?:unknown|n/a|none|na|description|default title|starting at"
    r"|your product'?s name|/\s*person)\s*",
    re.IGNORECASE,
)

# Repeated Shopify/template placeholders, e.g.
# "Your product's name  Your product's name  Your product's name ..."
# optionally prefixed with "You May Also Want to Check Out These..."
_RE_REPEATED_PLACEHOLDER = re.compile(
    r".*?(?:your product'?s name)(?:\s+your product'?s name){1,5}\s*",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Vectorized helpers (replace row-by-row .apply() calls)
# ---------------------------------------------------------------------------

def _parse_timestamps_vectorized(series: pd.Series) -> pd.Series:
    """
    Parse a string Series of timestamps that may be Wayback numeric
    (14 digits) or ISO 8601.  Returns a datetime64 Series (tz-naive).
    """
    s = series.astype(str).str.strip()

    # Identify Wayback-format rows (exactly 14 digits)
    is_wayback = s.str.fullmatch(r"\d{14}", na=False)

    # --- Wayback timestamps: reformat to ISO then bulk-convert ----------
    wb = s[is_wayback]
    if not wb.empty:
        # "20200626010522" -> "2020-06-26 01:05:22"
        wb_iso = (
            wb.str[:4] + "-" + wb.str[4:6] + "-" + wb.str[6:8] + " " +
            wb.str[8:10] + ":" + wb.str[10:12] + ":" + wb.str[12:14]
        )
        wb_parsed = pd.to_datetime(wb_iso, format="%Y-%m-%d %H:%M:%S", errors="coerce")
    else:
        wb_parsed = pd.Series(dtype="datetime64[ns]")

    # --- ISO / other timestamps -----------------------------------------
    other = s[~is_wayback]
    if not other.empty:
        other_parsed = pd.to_datetime(other, errors="coerce", utc=True)
        # Strip timezone to make concat safe
        other_parsed = other_parsed.dt.tz_localize(None)
    else:
        other_parsed = pd.Series(dtype="datetime64[ns]")

    # Combine
    result = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    if not wb_parsed.empty:
        result.loc[wb_parsed.index] = wb_parsed
    if not other_parsed.empty:
        result.loc[other_parsed.index] = other_parsed
    return result


def _parse_prices_vectorized(series: pd.Series) -> pd.Series:
    """Strip '$', convert to float, set non-positive to NaN."""
    cleaned = series.astype(str).str.strip().str.lstrip("$").str.strip()
    prices = pd.to_numeric(cleaned, errors="coerce")
    prices[prices <= 0] = np.nan
    return prices


def _filter_junk_products_vectorized(names: pd.Series) -> pd.Series:
    """Return a boolean mask where True = KEEP (not junk)."""
    # Must be non-empty strings
    valid = names.notna() & names.astype(bool)
    # Length check
    valid = valid & (names.str.len() <= MAX_PRODUCT_NAME_LEN)
    # No HTML tags
    valid = valid & ~names.str.contains(_RE_HTML, na=False)
    # No junk substrings
    valid = valid & ~names.str.contains(_RE_JUNK, na=False)
    # No price-only names ("$3.07", "$9.99 - $69.99", "$10.99/lb.", etc.)
    valid = valid & ~names.str.fullmatch(_RE_PRICE_NAME, na=False)
    # No unit-only names ("12 FL OZ", "1 LB", "6 CT")
    valid = valid & ~names.str.fullmatch(_RE_UNIT_ONLY, na=False)
    # No bare numbers ("8", "11.99")
    valid = valid & ~names.str.fullmatch(_RE_BARE_NUMBER, na=False)
    # No bare placeholders ("Unknown", "N/A", "Description", "Default Title", etc.)
    valid = valid & ~names.str.fullmatch(_RE_PLACEHOLDER, na=False)
    # No repeated template placeholders ("Your product's name" x2-4)
    valid = valid & ~names.str.fullmatch(_RE_REPEATED_PLACEHOLDER, na=False)
    return valid


def _parse_sale_vectorized(series: pd.Series) -> pd.Series:
    """Parse sale column to boolean, vectorized."""
    lower = series.fillna("").astype(str).str.strip().str.lower()
    return lower.isin(("true", "1", "yes", "sale"))


# ---------------------------------------------------------------------------
# CSV loading (single file)
# ---------------------------------------------------------------------------

def _load_single_csv(filepath: Path) -> pd.DataFrame:
    """
    Load a single pricing CSV file and return a normalized DataFrame.
    Returns an empty DataFrame on failure.
    """
    try:
        # Read with flexible parsing
        df = pd.read_csv(
            filepath,
            dtype=str,
            on_bad_lines="skip",
            encoding="utf-8",
            encoding_errors="replace",
            low_memory=False,
        )
    except Exception:
        return pd.DataFrame()

    if df.empty:
        return pd.DataFrame()

    # Normalize column names to lowercase
    df.columns = [c.strip().lower() for c in df.columns]

    # Check for required columns
    if not REQUIRED_COLS.issubset(set(df.columns)):
        return pd.DataFrame()

    # Fill missing optional columns
    for col in STANDARD_COLS:
        if col not in df.columns:
            df[col] = ""

    # --- Vectorized timestamp parsing ---
    df["timestamp"] = _parse_timestamps_vectorized(df["timestamp"])
    df = df.dropna(subset=["timestamp"])
    df["year"] = df["timestamp"].dt.year.astype("int64")

    # Filter to 2019-2026 range (reasonable data)
    df = df[(df["year"] >= 2019) & (df["year"] <= 2026)]

    # --- Vectorized price parsing ---
    df["price"] = _parse_prices_vectorized(df["price"])
    df = df.dropna(subset=["price"])

    # --- Vectorized junk-product filtering ---
    df["product_name"] = df["product_name"].fillna("").astype(str)
    keep_mask = _filter_junk_products_vectorized(df["product_name"])
    df = df[keep_mask]

    # --- Vectorized sale parsing ---
    df["sale"] = _parse_sale_vectorized(df["sale"])

    # Fill other string columns
    for col in ["chain", "location", "unit", "description", "wayback_url"]:
        df[col] = df[col].fillna("").astype(str)

    # Add source file
    df["source_file"] = filepath.name

    # Select output columns
    out_cols = [
        "timestamp", "year", "chain", "location", "product_name",
        "price", "unit", "sale", "description", "wayback_url", "source_file",
    ]
    return df[out_cols].reset_index(drop=True)



def _optimize_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Shrink the in-memory footprint of the loaded pricing DataFrame.

    Background (2026-05-14 OOM outage): the prebuilt parquet is ~87 MB on
    disk but ~1.47 GB in RAM after pandas decode (default object/float64
    dtypes). Streamlit Cloud's free-tier container has roughly 1 GB of
    addressable memory, so Tab 1 render was silently OOM-killed (SIGKILL
    → no Python traceback, just /healthz "connection reset by peer").

    This pass drops the in-RAM size to ~617 MB (58% reduction) by:

      - Casting low-cardinality string columns to ``category`` dtype.
      - Down-casting ``price``, ``lat``, ``lon`` from float64 → float32
        (penny-level / coordinate precision is unaffected).

    ``year`` is deliberately kept at int64. An older defense in this
    function (still preserved below) casts int32 → int64 because numpy
    2.x on Python 3.14 hits a nargsort IndexError on int32 year columns.
    Down-casting to int16 here would re-introduce that risk for ~14 MB
    of savings — not worth it.

    ``wayback_url`` and ``description`` are left as object dtype because
    they are high-cardinality / mostly-unique strings where ``category``
    would actually *increase* memory.
    """
    if df.empty:
        return df

    # Numeric down-casts (safe: data values fit comfortably in float32).
    for col in ("price", "lat", "lon"):
        if col in df.columns and df[col].dtype == np.float64:
            df[col] = df[col].astype(np.float32)

    # Categorical conversion for repeated string columns. Skip
    # wayback_url / description / product_name (already covered or
    # too high-cardinality).
    cat_columns = (
        "chain",
        "location",
        "unit",
        "category",
        "location_type",
        "source_file",
        "product_name",
    )
    for col in cat_columns:
        if col in df.columns and df[col].dtype == object:
            df[col] = df[col].astype("category")

    return df


@st.cache_data(show_spinner="Loading pricing data...")
def load_all_prices() -> pd.DataFrame:
    """
    Load pricing data with a three-tier strategy:

    1. **Pre-built parquet** (``data/pricing.parquet``, committed to the
       repo).  This is the primary path on Streamlit Cloud where
       rebuilding from 203 CSVs would exceed the boot timeout.
    2. **Runtime parquet cache** (``_pricing_cache.parquet``, gitignored).
       Survives local Streamlit restarts without re-reading CSVs.
    3. **Full CSV rebuild** — parallel load of all CSVs, categorise,
       geocode, then persist to the runtime cache for next time.
    """
    # ------------------------------------------------------------------
    # Tier 1: pre-built parquet (fast path — ~0.2 s)
    # ------------------------------------------------------------------
    if _PREBUILT_PARQUET.exists():
        try:
            df = pd.read_parquet(_PREBUILT_PARQUET)
            # Ensure year is int64 — parquet files written with older
            # data_loader versions store it as int32, which triggers a
            # nargsort IndexError on Python 3.14 / numpy 2.x.
            if "year" in df.columns and df["year"].dtype != np.int64:
                df["year"] = df["year"].astype(np.int64)
            return _optimize_dtypes(df)
        except Exception:
            pass  # fall through to CSV rebuild

    # ------------------------------------------------------------------
    # Tier 2: runtime parquet cache
    # ------------------------------------------------------------------
    if _PARQUET_CACHE.exists():
        try:
            df = pd.read_parquet(_PARQUET_CACHE)
            if "year" in df.columns and df["year"].dtype != np.int64:
                df["year"] = df["year"].astype(np.int64)
            return _optimize_dtypes(df)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Tier 3: full CSV rebuild
    # ------------------------------------------------------------------
    if not DATA_DIR.exists():
        st.error(f"Data directory not found: {DATA_DIR}")
        return pd.DataFrame()

    # Find all price files (exclude no_prices files)
    price_files = sorted(DATA_DIR.glob("*_prices.csv"))
    price_files = [
        f for f in price_files
        if "no_prices" not in f.name
    ]

    if not price_files:
        st.error("No pricing CSV files found in data directory.")
        return pd.DataFrame()

    # Filter out oversized files
    loadable_files: list[Path] = []
    skipped_large: list[tuple[str, int]] = []
    for fpath in price_files:
        file_size = fpath.stat().st_size
        if file_size > MAX_FILE_SIZE_BYTES:
            skipped_large.append((fpath.name, file_size))
        else:
            loadable_files.append(fpath)

    # Parallel CSV loading
    progress = st.progress(0, text="Loading pricing files...")
    total = len(loadable_files)
    frames: list[pd.DataFrame] = []
    skipped_empty = 0
    loaded_count = 0

    max_workers = min(8, os.cpu_count() or 4)
    future_to_path = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for fpath in loadable_files:
            future_to_path[pool.submit(_load_single_csv, fpath)] = fpath

        for i, future in enumerate(as_completed(future_to_path)):
            fpath = future_to_path[future]
            progress.progress(
                (i + 1) / total, text=f"Loaded {fpath.name}..."
            )
            try:
                df = future.result()
            except Exception:
                df = pd.DataFrame()

            if df.empty:
                skipped_empty += 1
                continue

            frames.append(df)
            loaded_count += 1

    progress.empty()

    if not frames:
        st.error("No valid pricing data found after loading all files.")
        return pd.DataFrame()

    # Concatenate all frames
    combined = pd.concat(frames, ignore_index=True)

    # Add categories
    combined["category"] = categorize_series(combined["product_name"])

    # Add geocoding
    lats, lons, loc_types = geocode_series(combined["location"])
    combined["lat"] = lats
    combined["lon"] = lons
    combined["location_type"] = loc_types

    # Sort by timestamp
    combined = combined.sort_values("timestamp").reset_index(drop=True)

    # Persist to runtime cache for next restart
    try:
        combined.to_parquet(_PARQUET_CACHE, index=False)
    except Exception:
        pass

    # Log summary
    if skipped_large:
        names = ", ".join(f"{n} ({s / 1e6:.0f}MB)" for n, s in skipped_large)
        st.info(f"Skipped {len(skipped_large)} large file(s): {names}")

    return _optimize_dtypes(combined)


def get_data_summary(df: pd.DataFrame) -> dict:
    """Return summary statistics for the loaded dataset."""
    if df.empty:
        return {
            "total_rows": 0,
            "unique_chains": 0,
            "unique_products": 0,
            "year_range": (None, None),
            "categories": [],
            "files_loaded": 0,
        }
    return {
        "total_rows": len(df),
        "unique_chains": df["chain"].nunique(),
        "unique_products": df["product_name"].nunique(),
        "year_range": (int(df["year"].min()), int(df["year"].max())),
        "categories": sorted(df["category"].unique().tolist()),
        "files_loaded": df["source_file"].nunique(),
    }
