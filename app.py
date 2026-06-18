"""
Grocery Pricing Dashboard

A Streamlit dashboard for exploring historical grocery pricing data
collected from Wayback Machine archives (2019-2025).

Tab 1: Pricing Map & Aggregate Statistics
Tab 2: Product View – ranked product table with sortable metrics
Tab 3: Custom Baskets – build/save custom baskets with inflation tracking
Tab 4: Harter House Case Study

Run locally:
    streamlit run app.py
"""

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data_loader import load_all_prices, get_data_summary
from categories import ALL_CATEGORIES
from geocoder import ALL_LOCATION_TYPES, LOC_STORE, LOC_CITY, LOC_CHAIN, LOC_UNKNOWN
from baskets import ALL_BASKET_NAMES, build_basket_product_sets, basket_display_name

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Grocery Pricing Dashboard",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    password = st.text_input("Enter password", type="password")
    if not password:
        st.stop()
    if password != st.secrets["app_password"]:
        st.error("Incorrect password.")
        st.stop()
    st.session_state.authenticated = True
    st.rerun()

# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------
if "location_overrides" not in st.session_state:
    # dict of (chain, location) -> bool; True = include, False = exclude.
    # Missing keys fall back to the left-sidebar Location Precision default.
    st.session_state.location_overrides = {}
# Migrate legacy session state
if "excluded_locations" in st.session_state:
    for k in st.session_state.excluded_locations:
        st.session_state.location_overrides.setdefault(k, False)
    del st.session_state["excluded_locations"]
if "map_key_idx" not in st.session_state:
    st.session_state.map_key_idx = 0
if "editor_key_idx" not in st.session_state:
    st.session_state.editor_key_idx = 0
if "user_baskets" not in st.session_state:
    st.session_state.user_baskets = {}  # id -> {name, products, weights}

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
df = load_all_prices()

if df.empty:
    st.error("No data loaded. Check that the data/ directory contains pricing CSVs.")
    st.stop()

summary = get_data_summary(df)

# ---------------------------------------------------------------------------
# Build basket-to-product crosswalk (once, cached in session_state)
# ---------------------------------------------------------------------------
if "basket_to_products" not in st.session_state:
    _unique_products = df["product_name"].unique().tolist()
    _b2p, _p2b = build_basket_product_sets(_unique_products)
    st.session_state.basket_to_products = _b2p
    st.session_state.product_to_baskets = _p2b

basket_to_products: dict[str, set[str]] = st.session_state.basket_to_products

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_map, tab_pv, tab_cb, tab_hh = st.tabs([
    "Pricing Map", "Product View", "Custom Baskets", "Harter House Case Study",
])


# ---------------------------------------------------------------------------
# Sidebar filters (shared across all tabs)
# ---------------------------------------------------------------------------
st.sidebar.header("Filters")


def _reset_all():
    """Clear every resettable filter & selection, then rerun."""
    st.session_state.location_overrides = {}
    st.session_state.map_key_idx = (
        st.session_state.get("map_key_idx", 0) + 1
    )
    st.session_state.editor_key_idx = (
        st.session_state.get("editor_key_idx", 0) + 1
    )
    _RESET_KEYS = [
        # sidebar
        "sidebar_categories", "sidebar_year_range",
        "sidebar_sale", "sidebar_loc_types", "sidebar_baskets",
        # custom baskets tab
        "cb_basket_name", "cb_cat_filter", "cb_products",
        # product view
        "pv_sort", "pv_order", "pv_min_obs",
        "pv_min_years", "pv_min_chains", "pv_cat_filter",
        # harter house
        "hh_snapshot_slider", "hh_weighting", "hh_bundle_select",
        # panel widgets
        "chainwide_directory",
    ]
    for key in _RESET_KEYS:
        st.session_state.pop(key, None)
    for key in [k for k in st.session_state
                if k.startswith("weight_")
                or k.startswith("cb_weight_")
                or k.startswith("location_editor_")]:
        del st.session_state[key]
    st.rerun()


if st.sidebar.button("Reset All Filters", type="secondary"):
    _reset_all()

# Basket filter (overrides categories when active)
_basket_counts = {
    name: len(prods) for name, prods in basket_to_products.items()
}
selected_baskets = st.sidebar.multiselect(
    "Baskets",
    options=ALL_BASKET_NAMES,
    default=[],
    format_func=lambda b: basket_display_name(b, _basket_counts.get(b, 0)),
    key="sidebar_baskets",
    help=(
        "Select one or more curated baskets grouped by NHANES meal archetype. "
        "When active, Product Categories are ignored."
    ),
)

_baskets_active = len(selected_baskets) > 0

st.sidebar.markdown(
    "<div style='text-align:center; color:#888; font-size:0.85em; "
    "margin:-0.25rem 0 -0.25rem 0;'>"
    "&mdash;&mdash;&mdash;&mdash; OR &mdash;&mdash;&mdash;&mdash;"
    "</div>",
    unsafe_allow_html=True,
)

# Category filter
available_categories = sorted(df["category"].unique().tolist())
selected_categories = st.sidebar.multiselect(
    "Product Categories",
    options=available_categories,
    default=available_categories,
    key="sidebar_categories",
    disabled=_baskets_active,
    help="Disabled when a Basket is selected." if _baskets_active else None,
)

# Sale filter
sale_filter = st.sidebar.radio(
    "Sale Status",
    options=["Non-sale only", "All", "Sale only"],
    index=0,
    key="sidebar_sale",
)

# Location type filter
selected_loc_types = st.sidebar.multiselect(
    "Location Precision",
    options=ALL_LOCATION_TYPES,
    default=ALL_LOCATION_TYPES,
    format_func=lambda x: {
        LOC_STORE: "Store-specific",
        LOC_CITY: "City-level",
        LOC_CHAIN: "Chain-wide (approximate)",
        LOC_UNKNOWN: "Unknown location",
    }.get(x, x),
    key="sidebar_loc_types",
)

# Year range filter  -------------------------------------------------------
# Build a filter-aware histogram of chains-per-year (excludes year filter
# itself so the user sees the full available spread).
min_year = int(df["year"].min())
max_year = int(df["year"].max())

# Mask that mirrors the active sidebar context but omits the year range
if _baskets_active:
    _yr_hist_mask = df["product_name"].isin(
        set().union(*(basket_to_products.get(b, set()) for b in selected_baskets))
    )
else:
    _yr_hist_mask = df["category"].isin(selected_categories)
if sale_filter == "Non-sale only":
    _yr_hist_mask = _yr_hist_mask & (~df["sale"])
elif sale_filter == "Sale only":
    _yr_hist_mask = _yr_hist_mask & df["sale"]
_yr_hist_mask = _yr_hist_mask & df["location_type"].isin(selected_loc_types)

_yr_hist_data = (
    df.loc[_yr_hist_mask]
    .groupby("year")["chain"]
    .nunique()
    .reindex(range(min_year, max_year + 1), fill_value=0)
)

# Read the persisted year range from session state (set on previous run)
# so the histogram can highlight the selected span before the slider renders.
_prev_yr = st.session_state.get(
    "sidebar_year_range",
    (max(min_year, 2020), min(max_year, 2025)),
)

# Compact Plotly bar chart (histogram) rendered above the slider
_yr_colors = [
    "#636EFA" if _prev_yr[0] <= yr <= _prev_yr[1] else "#D3D3D3"
    for yr in _yr_hist_data.index
]
_fig_yr = go.Figure(go.Bar(
    x=_yr_hist_data.index.astype(str),
    y=_yr_hist_data.values,
    marker_color=_yr_colors,
    hovertemplate="Year %{x}<br>%{y} chains<extra></extra>",
))
_fig_yr.update_layout(
    height=90,
    margin=dict(l=0, r=0, t=0, b=0),
    xaxis=dict(
        visible=True,
        showticklabels=True,
        tickmode="array",
        tickvals=_yr_hist_data.index.astype(str).tolist(),
        ticktext=[
            str(yr) if yr == _yr_hist_data.index.min()
            or yr == _yr_hist_data.index.max()
            else ""
            for yr in _yr_hist_data.index
        ],
        tickfont=dict(size=9, color="#888"),
        fixedrange=True,
    ),
    yaxis=dict(visible=False, fixedrange=True),
    bargap=0.15,
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
)
st.sidebar.plotly_chart(_fig_yr, use_container_width=True, config={"displayModeBar": False})

# Year slider (rendered directly below the histogram)
year_range = st.sidebar.slider(
    "Year Range",
    min_value=min_year,
    max_value=max_year,
    value=(max(min_year, 2020), min(max_year, 2025)),
    key="sidebar_year_range",
)

# --- Apply filters ---
if _baskets_active:
    # Union of all products matched by selected baskets
    _allowed_products: set[str] = set()
    for bname in selected_baskets:
        _allowed_products |= basket_to_products.get(bname, set())
    base_mask = (
        df["product_name"].isin(_allowed_products)
        & df["year"].between(year_range[0], year_range[1])
    )
else:
    base_mask = (
        df["category"].isin(selected_categories)
        & df["year"].between(year_range[0], year_range[1])
    )
if sale_filter == "Non-sale only":
    base_mask = base_mask & (~df["sale"])
elif sale_filter == "Sale only":
    base_mask = base_mask & df["sale"]

# `filtered` applies location-type filter — used by Product View, Baskets
filtered = df[base_mask & df["location_type"].isin(selected_loc_types)].copy()
# `map_base` keeps all location types — Pricing Map tab uses per-location
# overrides from the right-side panel instead of the blanket type filter.
map_base = df[base_mask].copy()


# ===========================================================================
# TAB 1: PRICING MAP & AGGREGATE STATS
# ===========================================================================
with tab_map:

    # ---------------------------------------------------------------
    # Determine which (chain, location) pairs have continuous year
    # coverage so the map can gray-out non-qualifying locations.
    # ---------------------------------------------------------------
    required_years = set(range(year_range[0], year_range[1] + 1))

    if len(required_years) > 1 and not map_base.empty:
        _pair_years = (
            map_base.groupby(["chain", "product_name"], observed=True)["year"]
            .apply(set)
        )
        _qualifying_pairs = _pair_years[
            _pair_years.apply(lambda yrs: required_years.issubset(yrs))
        ].index
        # Locations that own at least one continuously-covered product
        _qual_keys = pd.DataFrame(
            _qualifying_pairs.tolist(), columns=["chain", "product_name"]
        )
        _qual_rows = map_base.merge(
            _qual_keys, on=["chain", "product_name"], how="inner"
        )
        qualifying_locs: set | None = set(
            zip(_qual_rows["chain"], _qual_rows["location"])
        )
    else:
        # Single year selected -- every location trivially qualifies
        qualifying_locs = None

    # ---------------------------------------------------------------
    # Pre-compute the set of (chain, location) keys that would
    # contribute to stats under the current left-sidebar filters
    # (loc_type + continuous year coverage).  Used by the right-panel
    # checkboxes so their defaults match the actual stats output.
    # ---------------------------------------------------------------
    _baseline_df = map_base[
        map_base["location_type"].isin(selected_loc_types)
    ]
    if len(required_years) > 1 and not _baseline_df.empty:
        _bl_pair_years = (
            _baseline_df.groupby(["chain", "product_name"], observed=True)["year"]
            .apply(set)
        )
        _bl_qualifying = _bl_pair_years[
            _bl_pair_years.apply(
                lambda yrs: required_years.issubset(yrs)
            )
        ].index
        if len(_bl_qualifying) > 0:
            _bl_keys = pd.DataFrame(
                _bl_qualifying.tolist(),
                columns=["chain", "product_name"],
            )
            _baseline_df = _baseline_df.merge(
                _bl_keys, on=["chain", "product_name"], how="inner"
            )
        else:
            _baseline_df = _baseline_df.iloc[0:0]
    _default_included_keys: set[tuple] = set(
        zip(_baseline_df["chain"], _baseline_df["location"])
    ) if not _baseline_df.empty else set()

    # ---------------------------------------------------------------
    # Map first -- we need the click selection before rendering stats
    # ---------------------------------------------------------------
    st.markdown("### Pricing Data Map")

    map_df = map_base.dropna(subset=["lat", "lon"]).copy()

    if map_df.empty:
        st.info("No geocoded locations available for the current filter.")
    else:
        # Aggregate by location for the map
        map_agg = (
            map_df.groupby(
                ["lat", "lon", "chain", "location", "location_type"],
                observed=True,
            )
            .agg(
                count=("price", "size"),
                avg_price=("price", "mean"),
                min_year=("year", "min"),
                max_year=("year", "max"),
                n_products=("product_name", "nunique"),
            )
            .reset_index()
        )

        # Flag each location as qualifying (has continuous year coverage)
        if qualifying_locs is not None:
            map_agg["qualifying"] = [
                (c, l) in qualifying_locs
                for c, l in zip(map_agg["chain"], map_agg["location"])
            ]
        else:
            map_agg["qualifying"] = True

        # Flag each location as effectively included
        # (sidebar Location Precision baseline + right-panel overrides).
        # This drives dot lighting so the map stays in sync with stats.
        map_agg["included"] = [
            (
                st.session_state.location_overrides.get((c, l))
                if (c, l) in st.session_state.location_overrides
                else (c, l) in _default_included_keys
            )
            for c, l in zip(map_agg["chain"], map_agg["location"])
        ]

        color_map = {
            LOC_STORE: "#1f77b4",
            LOC_CITY: "#2ca02c",
            LOC_UNKNOWN: "#999999",
        }

        # Exclude chain-wide markers from the map -- they are now
        # discoverable via the Chain-Wide Directory panel to the right
        # and would otherwise pile up at the US-center fallback point.
        map_plot = map_agg[map_agg["location_type"] != LOC_CHAIN]

        # ---- Coordinate-level aggregation ----
        # Merge overlapping points into a single visible marker per
        # (lat, lon) so the user sees one dot with a combined hover
        # listing every store/chain at that coordinate.
        _type_priority = {LOC_STORE: 0, LOC_CITY: 1, LOC_UNKNOWN: 2}
        coord_members: dict[tuple[float, float], list[dict]] = {}
        coord_rows: list[dict] = []

        for (lat, lon), grp in map_plot.groupby(["lat", "lon"]):
            members = []
            for _, row in grp.iterrows():
                members.append({
                    "chain": row["chain"],
                    "location": row["location"],
                    "location_type": row["location_type"],
                    "count": int(row["count"]),
                    "n_products": int(row["n_products"]),
                    "min_year": int(row["min_year"]),
                    "max_year": int(row["max_year"]),
                    "avg_price": round(float(row["avg_price"]), 2),
                    "qualifying": bool(row["qualifying"]),
                    "included": bool(row["included"]),
                })
            coord_members[(lat, lon)] = members

            total_count = int(grp["count"].sum())
            # A dot is "active" (lit) when at least one member is both
            # qualifying (year coverage) AND effectively included
            # (sidebar baseline + right-panel overrides).
            _active_mask = grp["qualifying"] & grp["included"]
            any_active = bool(_active_mask.any())
            _active_types = grp.loc[_active_mask, "location_type"].unique()
            if len(_active_types) > 0:
                best_type = min(
                    _active_types,
                    key=lambda t: _type_priority.get(t, 99),
                )
            else:
                best_type = min(
                    grp["location_type"].unique(),
                    key=lambda t: _type_priority.get(t, 99),
                )

            # Build hover text
            if len(members) == 1:
                m = members[0]
                hover = (
                    f"<b>{m['chain']}</b><br>"
                    f"{m['location']}<br>"
                    f"{m['count']} price points<br>"
                    f"{m['n_products']} unique products<br>"
                    f"Years: {m['min_year']}-{m['max_year']}<br>"
                    f"Avg price: ${m['avg_price']}<br>"
                    f"<i>{m['location_type']}</i>"
                )
            else:
                lines = [
                    f"<b>{len(members)} entries at this location</b><br>"
                ]
                for m in members[:8]:
                    qual_tag = "" if m["qualifying"] else " *"
                    lines.append(
                        f"\u2022 <b>{m['chain']}</b> \u2014 "
                        f"{m['location']} "
                        f"({m['count']} prices){qual_tag}<br>"
                    )
                if len(members) > 8:
                    lines.append(
                        f"<i>...and {len(members) - 8} more</i><br>"
                    )
                lines.append("<br><i>Click to see full list</i>")
                hover = "".join(lines)

            coord_rows.append({
                "lat": lat,
                "lon": lon,
                "hover_text": hover,
                "marker_size": float(
                    np.clip(np.log1p(total_count) * 3, 4, 30)
                ),
                "qualifying": any_active,
                "best_type": best_type,
            })

        coord_df = pd.DataFrame(coord_rows)

        fig_map = go.Figure()

        if not coord_df.empty:
            # --- Non-qualifying coordinates (gray, behind) ---
            non_qual = coord_df[~coord_df["qualifying"]]
            if not non_qual.empty:
                fig_map.add_trace(go.Scattergeo(
                    lat=non_qual["lat"],
                    lon=non_qual["lon"],
                    text=non_qual["hover_text"],
                    hoverinfo="text",
                    customdata=list(zip(
                        non_qual["lat"].tolist(),
                        non_qual["lon"].tolist(),
                    )),
                    marker=dict(
                        size=non_qual["marker_size"],
                        color="#cccccc",
                        opacity=0.3,
                        line=dict(width=1, color="white"),
                        symbol="circle",
                    ),
                    name="No continuous coverage",
                ))

            # --- Qualifying coordinates (colored by best type) ---
            qual = coord_df[coord_df["qualifying"]]
            for loc_type, color in color_map.items():
                subset = qual[qual["best_type"] == loc_type]
                if subset.empty:
                    continue
                label = {
                    LOC_STORE: "Store-specific",
                    LOC_CITY: "City-level",
                    LOC_UNKNOWN: "Unknown",
                }.get(loc_type, loc_type)

                fig_map.add_trace(go.Scattergeo(
                    lat=subset["lat"],
                    lon=subset["lon"],
                    text=subset["hover_text"],
                    hoverinfo="text",
                    customdata=list(zip(
                        subset["lat"].tolist(),
                        subset["lon"].tolist(),
                    )),
                    marker=dict(
                        size=subset["marker_size"],
                        color=color,
                        opacity=0.7,
                        line=dict(width=1, color="white"),
                        symbol="circle",
                    ),
                    name=label,
                ))

        fig_map.update_geos(
            scope="usa",
            showland=True,
            landcolor="rgb(243, 243, 243)",
            showlakes=True,
            lakecolor="rgb(204, 224, 255)",
            showcountries=False,
            showsubunits=True,
            subunitcolor="rgb(200, 200, 200)",
        )
        fig_map.update_layout(
            height=550,
            margin=dict(l=0, r=0, t=30, b=0),
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                bgcolor="rgba(255,255,255,0.8)",
            ),
        )

        # --- Two-column layout: map (left) + context panel (right) ---
        col_map, col_panel = st.columns([7, 3])

        with col_map:
            map_event = st.plotly_chart(
                fig_map,
                use_container_width=True,
                on_select="rerun",
                selection_mode="points",
                key=f"pricing_map_{st.session_state.map_key_idx}",
            )

            # Extract selected coordinates from map click/lasso
            selected_coords: list[tuple[float, float]] = []
            try:
                sel = (
                    map_event.get("selection", {})
                    if isinstance(map_event, dict)
                    else getattr(map_event, "selection", None)
                    or map_event.get("selection", {})
                    if hasattr(map_event, "get")
                    else {}
                )
                points = (
                    sel.get("points", [])
                    if isinstance(sel, dict)
                    else getattr(sel, "points", [])
                )
                for pt in points:
                    custom = (
                        pt.get("customdata")
                        if isinstance(pt, dict)
                        else getattr(pt, "customdata", None)
                    )
                    if custom and len(custom) >= 2:
                        selected_coords.append(
                            (float(custom[0]), float(custom[1]))
                        )
            except Exception:
                pass

            st.caption(
                "Click, box-select, or lasso map points to "
                "inspect them in the panel on the right."
            )

        # --- Location filter panel (right column) ---
        with col_panel:
            # Global lookup: (chain, location) -> location_type for
            # every row in map_agg (needed by override logic later).
            _key_to_type: dict[tuple, str] = dict(zip(
                zip(map_agg["chain"], map_agg["location"]),
                map_agg["location_type"],
            ))

            def _effective_include(key: tuple) -> bool:
                """Effective include state for a location.

                Priority: explicit user override > baseline default.
                The baseline accounts for left-sidebar Location
                Precision AND continuous year coverage, so the
                checkbox defaults match the actual stats output.
                """
                override = st.session_state.location_overrides.get(key)
                if override is not None:
                    return override
                return key in _default_included_keys

            # ----------------------------------------------------------
            # Decide what the panel shows:
            #   - No map selection -> Chain-Wide Directory (chain-wide
            #     rows from map_agg)
            #   - Map selection    -> union of entries at those coords
            # ----------------------------------------------------------
            _panel_mode = "selected" if selected_coords else "chainwide"

            if _panel_mode == "selected":
                # Union of all entries at the selected coordinates,
                # de-duplicated by (chain, location).
                _seen: set[tuple] = set()
                _panel_rows: list[dict] = []
                for coord in selected_coords:
                    for m in coord_members.get(coord, []):
                        k = (m["chain"], m["location"])
                        if k not in _seen:
                            _seen.add(k)
                            _panel_rows.append(m)
                # Sort by price count descending
                _panel_rows.sort(key=lambda r: r["count"], reverse=True)

                if _panel_rows:
                    panel_locs = pd.DataFrame(_panel_rows)
                else:
                    # Fallback: selected coords had no members
                    _panel_mode = "chainwide"

            if _panel_mode == "chainwide":
                panel_locs = map_agg[
                    map_agg["location_type"] == LOC_CHAIN
                ].sort_values("count", ascending=False)

            # Build the key list for the rows being displayed
            _panel_keys = list(zip(
                panel_locs["chain"].tolist(),
                panel_locs["location"].tolist(),
            ))

            # Fingerprint so the editor re-keys when contents or
            # baseline inclusion changes (basket, year, loc-type, etc.)
            _panel_fp = hash((
                _panel_mode,
                tuple(_panel_keys),
                tuple(sorted(selected_loc_types)),
                frozenset(_default_included_keys),
            ))

            n_panel = len(_panel_keys)
            n_panel_included = sum(
                1 for k in _panel_keys if _effective_include(k)
            )

            # --- Panel header ---
            if _panel_mode == "chainwide":
                st.markdown(
                    f"**Chain-Wide Directory "
                    f"({n_panel_included}/{n_panel} included)**",
                    help="Chain-wide locations not shown on the map. "
                         "Check rows to include them in statistics. "
                         "Select map points to inspect local entries.",
                )
            else:
                st.markdown(
                    f"**Selected Locations "
                    f"({n_panel_included}/{n_panel} included)**",
                    help="Entries at the selected map point(s). "
                         "Uncheck to exclude from statistics.",
                )

            btn_cols = st.columns(2)
            with btn_cols[0]:
                if st.button("Include All", key="incl_all"):
                    for k in _panel_keys:
                        st.session_state.location_overrides[k] = True
                    st.session_state.editor_key_idx += 1
                    st.rerun()
            with btn_cols[1]:
                if st.button("Exclude All", key="excl_all"):
                    for k in _panel_keys:
                        st.session_state.location_overrides[k] = False
                    st.session_state.editor_key_idx += 1
                    st.rerun()

            loc_display = pd.DataFrame({
                "Include": [
                    _effective_include(k) for k in _panel_keys
                ],
                "Chain": panel_locs["chain"].values,
                "Location": panel_locs["location"].values,
                "Type": panel_locs["location_type"].values,
                "Prices": panel_locs["count"].values,
            })

            edited_locs = st.data_editor(
                loc_display,
                column_config={
                    "Include": st.column_config.CheckboxColumn(
                        "Include",
                    ),
                },
                disabled=["Chain", "Location", "Type", "Prices"],
                use_container_width=True,
                hide_index=True,
                height=min(500, 35 * len(loc_display) + 38),
                key=f"location_editor_{st.session_state.editor_key_idx}_{_panel_fp}",
            )

            # Sync editor state back to location_overrides using
            # stable (chain, location) keys.
            for i, k in enumerate(_panel_keys):
                if i < len(edited_locs):
                    user_val = bool(edited_locs["Include"].iloc[i])
                    default_val = k in _default_included_keys
                    if user_val != default_val:
                        st.session_state.location_overrides[k] = user_val
                    elif k in st.session_state.location_overrides:
                        del st.session_state.location_overrides[k]

            if _panel_mode == "chainwide":
                st.caption(
                    "Select map points to inspect local stores."
                )
            else:
                st.caption(
                    "Clear map selection to return to the "
                    "Chain-Wide Directory."
                )

    # ---------------------------------------------------------------
    # Determine effective included locations and filter map_base for
    # stats.  _default_included_keys (pre-computed above) captures
    # the baseline; location_overrides layer user choices on top.
    # ---------------------------------------------------------------
    # Collect every (chain, location) from map_base (not just map_agg,
    # which requires map_df to be non-empty).
    _all_loc_keys_full = set(zip(
        map_base["chain"].tolist(),
        map_base["location"].tolist(),
    ))
    _included_keys = set()
    _excluded_keys = set()
    for k in _all_loc_keys_full:
        override = st.session_state.location_overrides.get(k)
        if override is not None:
            if override:
                _included_keys.add(k)
            else:
                _excluded_keys.add(k)
        elif k in _default_included_keys:
            _included_keys.add(k)
        else:
            _excluded_keys.add(k)

    if _included_keys:
        stats_df = map_base[
            map_base.apply(
                lambda r: (r["chain"], r["location"]) in _included_keys,
                axis=1,
            )
        ]
    else:
        stats_df = map_base

    if _excluded_keys:
        stats_label = f"{len(_excluded_keys)} Location(s) Excluded"
    else:
        stats_label = "All Locations"

    if stats_df.empty:
        stats_df = map_base  # fallback: don't lose all data
        st.warning(
            "All locations are excluded. "
            "Showing full filtered data instead."
        )
        stats_label = "All Locations"

    # ---------------------------------------------------------------
    # Filter to products with continuous year coverage
    # ---------------------------------------------------------------
    required_years = set(range(year_range[0], year_range[1] + 1))

    if len(required_years) > 1 and not stats_df.empty:
        # For each chain+product pair, find the set of years it has data in.
        # Grouping by (chain, product_name) prevents a generic product name
        # at one chain from qualifying via another chain's year coverage.
        pair_years = (
            stats_df.groupby(["chain", "product_name"], observed=True)["year"].apply(set)
        )
        # Keep only pairs that have at least one data point in every
        # year of the selected range
        qualifying_pairs = pair_years[
            pair_years.apply(lambda yrs: required_years.issubset(yrs))
        ].index
        qualifying_keys = pd.DataFrame(
            qualifying_pairs.tolist(), columns=["chain", "product_name"]
        )
        stats_df = stats_df.merge(
            qualifying_keys, on=["chain", "product_name"], how="inner"
        )

    # ---------------------------------------------------------------
    # Aggregate statistics (react to location overrides)
    # ---------------------------------------------------------------
    if _excluded_keys:
        st.info(
            f"**{len(_excluded_keys)} location(s)** excluded. "
            "Use *Include All* or *Reset All Filters* "
            "to restore."
        )
        st.markdown(f"### Statistics: {stats_label}")
    else:
        st.markdown("### Aggregate Statistics")

    if stats_df.empty:
        st.warning(
            "No products have continuous coverage across every year in "
            f"the selected range ({year_range[0]}-{year_range[1]}). "
            "Try narrowing the year range."
        )
    else:
        n_qualifying = stats_df["product_name"].nunique()
        st.caption(
            f"{n_qualifying:,} product(s) with data in every year "
            f"from {year_range[0]} to {year_range[1]}"
        )

        yearly_median = stats_df.groupby("year")["price"].median()

        if len(yearly_median) >= 2:
            first_year = yearly_median.index.min()
            last_year = yearly_median.index.max()
            first_price = yearly_median.iloc[0]
            last_price = yearly_median.iloc[-1]
            total_change_pct = ((last_price - first_price) / first_price) * 100
            n_years = last_year - first_year
            if n_years > 0:
                annualized = ((last_price / first_price) ** (1 / n_years) - 1) * 100
            else:
                annualized = 0.0
        else:
            total_change_pct = 0.0
            annualized = 0.0
            first_year = last_year = (
                yearly_median.index[0] if len(yearly_median) > 0 else 0
            )

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric("Data Points", f"{len(stats_df):,}")
        with col2:
            st.metric("Unique Chains", f"{stats_df['chain'].nunique():,}")
        with col3:
            st.metric(
                "Unique Products",
                f"{stats_df['product_name'].nunique():,}",
            )
        with col4:
            st.metric(
                f"Total Change ({first_year}-{last_year})",
                f"{total_change_pct:+.1f}%",
                delta=f"{total_change_pct:+.1f}%",
                delta_color="inverse",
            )
        with col5:
            st.metric(
                "Annualized",
                f"{annualized:+.1f}%/yr",
                delta=f"{annualized:+.1f}%",
                delta_color="inverse",
            )

        # Year-over-year line chart
        if len(yearly_median) >= 2:
            st.markdown("### Year-over-Year Median Price")

            years_sorted = sorted(yearly_median.index)
            yoy_pcts = []
            for i in range(1, len(years_sorted)):
                prev_p = yearly_median[years_sorted[i - 1]]
                curr_p = yearly_median[years_sorted[i]]
                yoy_pcts.append(((curr_p - prev_p) / prev_p) * 100)

            fig_yoy = go.Figure()

            fig_yoy.add_trace(go.Scatter(
                x=[int(y) for y in years_sorted],
                y=[yearly_median[y] for y in years_sorted],
                mode="lines+markers",
                name="Median Price ($)",
                line=dict(color="#1f77b4", width=2.5),
                marker=dict(size=8),
                yaxis="y",
            ))

            fig_yoy.add_trace(go.Bar(
                x=[int(years_sorted[i]) for i in range(1, len(years_sorted))],
                y=yoy_pcts,
                name="YoY Change (%)",
                marker_color=[
                    "#e45756" if p > 0 else "#54a24b" for p in yoy_pcts
                ],
                opacity=0.5,
                yaxis="y2",
            ))

            fig_yoy.update_layout(
                xaxis=dict(title="Year", dtick=1, tickformat="d"),
                yaxis=dict(
                    title="Median Price ($)",
                    side="left",
                    showgrid=True,
                    tickprefix="$",
                ),
                yaxis2=dict(
                    title="YoY Change (%)",
                    side="right",
                    overlaying="y",
                    showgrid=False,
                    ticksuffix="%",
                    zeroline=True,
                    zerolinecolor="gray",
                    zerolinewidth=1,
                ),
                height=350,
                margin=dict(l=50, r=50, t=30, b=50),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="center",
                    x=0.5,
                ),
                hovermode="x unified",
            )

            st.plotly_chart(fig_yoy, use_container_width=True)

        # --- Data table ---
        st.markdown("### Browse Filtered Data")
        display_cols = [
            "timestamp", "chain", "location", "product_name",
            "price", "unit", "sale", "category", "year",
            "location_type", "wayback_url",
        ]
        browse_df = stats_df[display_cols]
        st.download_button(
            "Generate CSV",
            data=browse_df.to_csv(index=False).encode("utf-8"),
            file_name="filtered_data.csv",
            mime="text/csv",
        )
        st.dataframe(
            browse_df.head(1000),
            use_container_width=True,
            hide_index=True,
            column_config={
                "wayback_url": st.column_config.LinkColumn(
                    "Wayback URL",
                    display_text="View",
                ),
            },
        )
        if len(browse_df) > 1000:
            st.caption(
                f"Showing first 1,000 of {len(browse_df):,} rows. "
                "CSV download includes all rows."
            )




# ===========================================================================
# TAB 2: PRODUCT VIEW
# ===========================================================================
with tab_pv:
    st.markdown("### Product View")
    st.caption(
        "Explore and rank individual products across the dataset. "
        "Results respect the sidebar filters."
    )

    if filtered.empty:
        st.warning("No data matches current filters.")
    else:
        # ---------------------------------------------------------------
        # Per-product metrics (computed from *filtered*, not stats_df)
        # ---------------------------------------------------------------
        n_selected_years = year_range[1] - year_range[0] + 1

        @st.cache_data(show_spinner=False)
        def _build_product_metrics(_filt: pd.DataFrame, _n_sel_years: int):
            """Build a product-level summary table from the filtered data."""
            g = _filt.groupby("product_name", observed=True)

            agg = g.agg(
                observations=("price", "size"),
                chains=("chain", "nunique"),
                locations=("location", "nunique"),
                years_covered=("year", "nunique"),
                first_year=("year", "min"),
                last_year=("year", "max"),
                avg_price=("price", "mean"),
                median_price=("price", "median"),
                category=("category", "first"),
            ).reset_index()

            # Coverage ratio
            agg["coverage_pct"] = (
                (agg["years_covered"] / _n_sel_years * 100)
                .clip(upper=100)
                .round(0)
                .astype(int)
            )

            # --- Inflation via yearly median first-vs-last ---
            yearly_med = (
                _filt.groupby(["product_name", "year"], observed=True)["price"]
                .median()
                .reset_index()
            )
            first_prices = (
                yearly_med.sort_values("year")
                .drop_duplicates("product_name", keep="first")
                .rename(columns={"price": "_first_price", "year": "_fy"})
                [["product_name", "_first_price", "_fy"]]
            )
            last_prices = (
                yearly_med.sort_values("year")
                .drop_duplicates("product_name", keep="last")
                .rename(columns={"price": "_last_price", "year": "_ly"})
                [["product_name", "_last_price", "_ly"]]
            )
            trend = first_prices.merge(last_prices, on="product_name")
            trend["total_change_pct"] = (
                (trend["_last_price"] - trend["_first_price"])
                / trend["_first_price"]
                * 100
            )
            span = trend["_ly"] - trend["_fy"]
            trend["annualized_pct"] = np.where(
                span > 0,
                ((trend["_last_price"] / trend["_first_price"])
                 ** (1 / span) - 1) * 100,
                0.0,
            )
            # Only keep trend for products with 2+ years
            trend.loc[span < 1, ["total_change_pct", "annualized_pct"]] = np.nan

            agg = agg.merge(
                trend[["product_name", "total_change_pct", "annualized_pct"]],
                on="product_name",
                how="left",
            )

            # Round monetary & pct columns
            agg["avg_price"] = agg["avg_price"].round(2)
            agg["median_price"] = agg["median_price"].round(2)
            agg["total_change_pct"] = agg["total_change_pct"].round(1)
            agg["annualized_pct"] = agg["annualized_pct"].round(1)

            return agg

        pv_metrics = _build_product_metrics(filtered, n_selected_years)

        # ---------------------------------------------------------------
        # Controls (in-tab, not sidebar)
        # ---------------------------------------------------------------
        ctrl_cols = st.columns([2, 1, 1, 1, 1])

        SORT_OPTIONS = {
            "Data Points": "observations",
            "Chain Count": "chains",
            "Location Count": "locations",
            "Years Covered": "years_covered",
            "Coverage %": "coverage_pct",
            "Median Price": "median_price",
            "Avg Price": "avg_price",
            "Total Change %": "total_change_pct",
            "Annualized Change %": "annualized_pct",
        }

        with ctrl_cols[0]:
            sort_label = st.selectbox(
                "Sort by",
                options=list(SORT_OPTIONS.keys()),
                index=0,
                key="pv_sort",
            )
        with ctrl_cols[1]:
            sort_dir = st.radio(
                "Order",
                options=["Descending", "Ascending"],
                index=0,
                key="pv_order",
                horizontal=True,
            )
        with ctrl_cols[2]:
            min_obs = st.number_input(
                "Min observations",
                min_value=1,
                max_value=1000,
                value=3,
                step=1,
                key="pv_min_obs",
            )
        with ctrl_cols[3]:
            min_years = st.number_input(
                "Min years",
                min_value=1,
                max_value=n_selected_years,
                value=1,
                step=1,
                key="pv_min_years",
            )
        with ctrl_cols[4]:
            min_chains = st.number_input(
                "Min chains",
                min_value=1,
                max_value=max(int(pv_metrics["chains"].max()), 1),
                value=1,
                step=1,
                key="pv_min_chains",
            )

        # Optional category filter scoped to this tab
        pv_cat_filter = st.multiselect(
            "Filter by category",
            options=sorted(pv_metrics["category"].unique().tolist()),
            default=[],
            key="pv_cat_filter",
        )

        # ---------------------------------------------------------------
        # Apply in-tab filters & sort
        # ---------------------------------------------------------------
        pv_view = pv_metrics.copy()
        pv_view = pv_view[
            (pv_view["observations"] >= min_obs)
            & (pv_view["years_covered"] >= min_years)
            & (pv_view["chains"] >= min_chains)
        ]
        if pv_cat_filter:
            pv_view = pv_view[pv_view["category"].isin(pv_cat_filter)]

        sort_col = SORT_OPTIONS[sort_label]
        ascending = sort_dir == "Ascending"
        pv_view = pv_view.sort_values(
            sort_col, ascending=ascending, na_position="last"
        )

        # ---------------------------------------------------------------
        # Display table
        # ---------------------------------------------------------------
        st.markdown(
            f"**{len(pv_view):,}** products match "
            f"(of {len(pv_metrics):,} total after sidebar filters)"
        )

        display_cols = {
            "product_name": "Product",
            "category": "Category",
            "observations": "Data Points",
            "chains": "Chains",
            "locations": "Locations",
            "years_covered": "Years",
            "coverage_pct": "Coverage %",
            "first_year": "First Year",
            "last_year": "Last Year",
            "median_price": "Median $",
            "avg_price": "Avg $",
            "total_change_pct": "Total Change %",
            "annualized_pct": "Annual %",
        }

        pv_display = pv_view[list(display_cols.keys())].head(500).copy()
        pv_display.columns = list(display_cols.values())

        st.dataframe(
            pv_display,
            use_container_width=True,
            hide_index=True,
            height=min(600, 35 * len(pv_display) + 38),
        )
        if len(pv_view) > 500:
            st.caption(f"Showing first 500 of {len(pv_view):,} rows.")

        # ---------------------------------------------------------------
        # Single-product detail chart
        # ---------------------------------------------------------------
        st.divider()
        st.markdown("### Product Detail")

        # Build search list from the current filtered/sorted view
        pv_product_list = pv_view["product_name"].tolist()

        detail_product = st.selectbox(
            "Select a product to view its price history",
            options=[""] + pv_product_list[:2000],
            index=0,
            key="pv_detail_product",
            help="Start typing to search. List is ordered by your current sort.",
        )

        if detail_product:
            detail_df = filtered[
                filtered["product_name"] == detail_product
            ].copy()

            if detail_df.empty:
                st.warning("No data for this product in current filters.")
            else:
                # Summary metrics row
                d_cols = st.columns(5)
                with d_cols[0]:
                    st.metric("Data Points", f"{len(detail_df):,}")
                with d_cols[1]:
                    st.metric("Chains", f"{detail_df['chain'].nunique()}")
                with d_cols[2]:
                    st.metric(
                        "Year Range",
                        f"{int(detail_df['year'].min())}-"
                        f"{int(detail_df['year'].max())}",
                    )
                with d_cols[3]:
                    st.metric(
                        "Median Price",
                        f"${detail_df['price'].median():.2f}",
                    )
                with d_cols[4]:
                    yr_med = detail_df.groupby("year")["price"].median()
                    if len(yr_med) >= 2:
                        _tc = (
                            (yr_med.iloc[-1] - yr_med.iloc[0])
                            / yr_med.iloc[0]
                            * 100
                        )
                        st.metric(
                            "Total Change",
                            f"{_tc:+.1f}%",
                            delta=f"{_tc:+.1f}%",
                            delta_color="inverse",
                        )
                    else:
                        st.metric("Total Change", "N/A")

                # --- Monthly median price chart ---
                detail_df["month"] = detail_df["timestamp"].dt.to_period("M")
                monthly = (
                    detail_df.groupby("month")["price"]
                    .median()
                    .reset_index()
                )
                monthly["month"] = monthly["month"].dt.to_timestamp()

                fig_detail = go.Figure()
                fig_detail.add_trace(go.Scatter(
                    x=monthly["month"],
                    y=monthly["price"],
                    mode="lines+markers",
                    name="Monthly Median",
                    line=dict(color="#1f77b4", width=2),
                    marker=dict(size=5),
                ))
                fig_detail.update_layout(
                    xaxis_title="Date",
                    yaxis_title="Price ($)",
                    height=400,
                    margin=dict(l=50, r=20, t=30, b=50),
                    hovermode="x unified",
                    yaxis=dict(tickprefix="$"),
                )
                st.plotly_chart(fig_detail, use_container_width=True)

                # --- By-chain breakdown ---
                chain_counts = detail_df["chain"].value_counts()
                if len(chain_counts) > 1:
                    with st.expander(
                        f"Price by chain ({len(chain_counts)} chains)"
                    ):
                        chain_monthly = (
                            detail_df.groupby(
                                [detail_df["timestamp"].dt.to_period("M"),
                                 "chain"],
                                observed=True,
                            )["price"]
                            .median()
                            .reset_index()
                        )
                        chain_monthly.columns = [
                            "month", "chain", "price",
                        ]
                        chain_monthly["month"] = (
                            chain_monthly["month"].dt.to_timestamp()
                        )

                        fig_chains = px.line(
                            chain_monthly,
                            x="month",
                            y="price",
                            color="chain",
                            markers=True,
                            labels={
                                "month": "Date",
                                "price": "Price ($)",
                                "chain": "Chain",
                            },
                        )
                        fig_chains.update_layout(
                            height=400,
                            margin=dict(l=50, r=20, t=30, b=50),
                            hovermode="x unified",
                            yaxis=dict(tickprefix="$"),
                            legend=dict(
                                orientation="h",
                                yanchor="bottom",
                                y=-0.25,
                                xanchor="center",
                                x=0.5,
                            ),
                        )
                        st.plotly_chart(
                            fig_chains, use_container_width=True
                        )

                # --- Raw data ---
                with st.expander("Raw price data"):
                    raw_detail = detail_df[
                        [
                            "timestamp", "chain", "location",
                            "price", "unit", "sale", "wayback_url",
                        ]
                    ].sort_values("timestamp")
                    st.dataframe(
                        raw_detail.head(500),
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "wayback_url": st.column_config.LinkColumn(
                                "Source", display_text="View",
                            ),
                        },
                    )
                    if len(raw_detail) > 500:
                        st.caption(
                            f"Showing first 500 of "
                            f"{len(raw_detail):,} rows."
                        )
        else:
            st.info(
                "Select a product above to see its full price history, "
                "chain breakdown, and raw data."
            )


# ===========================================================================
# TAB 3: CUSTOM BASKETS
# ===========================================================================
with tab_cb:
    st.markdown("### Custom Basket Builder")
    st.markdown(
        "Build and save custom baskets to track inflation over time. "
        "Select products and assign weights, then save the basket for "
        "later comparison. Saved baskets persist until the app is restarted."
    )

    if filtered.empty:
        st.warning("No data matches current filters.")
    else:
        # ---------------------------------------------------------------
        # Saved baskets management
        # ---------------------------------------------------------------
        user_baskets: dict = st.session_state.user_baskets

        if user_baskets:
            st.markdown("#### Saved Baskets")
            saved_cols = st.columns([3, 1])
            with saved_cols[0]:
                saved_names = {
                    bid: b["name"] for bid, b in user_baskets.items()
                }
                _view_id = st.selectbox(
                    "View a saved basket",
                    options=[""] + list(saved_names.keys()),
                    format_func=lambda x: saved_names.get(x, "-- Select --"),
                    key="cb_view_saved",
                )
            with saved_cols[1]:
                if _view_id and st.button(
                    "Delete", key="cb_delete_btn", type="secondary"
                ):
                    del st.session_state.user_baskets[_view_id]
                    st.rerun()

            # Display saved basket performance
            if _view_id and _view_id in user_baskets:
                _saved = user_baskets[_view_id]
                _s_products = _saved["products"]
                _s_weights = _saved["weights"]
                _s_total_w = sum(_s_weights.values())
                if _s_total_w > 0:
                    _s_norm = {k: v / _s_total_w for k, v in _s_weights.items()}
                else:
                    _s_norm = {k: 1.0 / len(_s_products) for k in _s_products}

                with st.expander(f"Basket: {_saved['name']}", expanded=True):
                    _s_summary = []
                    for _sp in _s_products:
                        _sp_data = filtered[filtered["product_name"] == _sp]
                        _s_summary.append({
                            "Product": _sp,
                            "Weight": f"{_s_norm.get(_sp, 0) * 100:.1f}%",
                            "Data Points": len(_sp_data),
                            "Median $": f"${_sp_data['price'].median():.2f}" if not _sp_data.empty else "N/A",
                        })
                    st.dataframe(
                        pd.DataFrame(_s_summary),
                        use_container_width=True,
                        hide_index=True,
                    )

            st.divider()

        # ---------------------------------------------------------------
        # Build a new basket
        # ---------------------------------------------------------------
        st.markdown("#### Build a New Basket")

        cb_basket_name = st.text_input(
            "Basket name",
            value="",
            key="cb_basket_name",
            placeholder="e.g. My Breakfast Basket",
        )

        # Product selection
        cb_product_stats = (
            filtered.groupby("product_name", observed=True)
            .agg(
                avg_price=("price", "mean"),
                count=("price", "size"),
                chains=("chain", "nunique"),
                min_year=("year", "min"),
                max_year=("year", "max"),
                category=("category", "first"),
            )
            .reset_index()
        )
        cb_product_stats = cb_product_stats[
            cb_product_stats["count"] >= 2
        ].sort_values("count", ascending=False)

        # Category filter for product selection
        cb_cat_filter = st.multiselect(
            "Filter products by category",
            options=sorted(cb_product_stats["category"].unique().tolist()),
            default=[],
            key="cb_cat_filter",
        )
        if cb_cat_filter:
            cb_filtered_products = cb_product_stats[
                cb_product_stats["category"].isin(cb_cat_filter)
            ]
        else:
            cb_filtered_products = cb_product_stats

        cb_product_options = cb_filtered_products["product_name"].tolist()

        cb_selected = st.multiselect(
            "Select products for your basket",
            options=cb_product_options,
            default=[],
            key="cb_products",
            help="Start typing to search. Sorted by data points.",
        )

        if not cb_selected:
            st.info(
                "Select products above to build your basket. "
                "Use the **Product View** tab to explore products first."
            )
        else:
            # --- Weight assignment ---
            st.markdown("##### Weights")
            st.caption(
                "Assign a weight to each product. Weights are normalized to 100%."
            )

            cb_weights: dict[str, float] = {}
            _cb_cols_per_row = 3
            for _ci in range(0, len(cb_selected), _cb_cols_per_row):
                _cb_cols = st.columns(_cb_cols_per_row)
                for _cj, _ccol in enumerate(_cb_cols):
                    _cidx = _ci + _cj
                    if _cidx >= len(cb_selected):
                        break
                    _cprod = cb_selected[_cidx]
                    with _ccol:
                        _cw = st.number_input(
                            _cprod[:40] + ("..." if len(_cprod) > 40 else ""),
                            min_value=0.0,
                            max_value=100.0,
                            value=1.0,
                            step=0.1,
                            key=f"cb_weight_{_cidx}",
                        )
                        cb_weights[_cprod] = _cw

            cb_total_w = sum(cb_weights.values())
            if cb_total_w <= 0:
                st.warning("All weights are zero.")
            else:
                cb_norm_weights = {
                    k: v / cb_total_w for k, v in cb_weights.items()
                }

                # --- Save button ---
                _save_cols = st.columns([2, 1])
                with _save_cols[0]:
                    if st.button(
                        "Save Basket",
                        key="cb_save_btn",
                        type="primary",
                        disabled=not cb_basket_name.strip(),
                    ):
                        import uuid
                        _bid = str(uuid.uuid4())[:8]
                        st.session_state.user_baskets[_bid] = {
                            "name": cb_basket_name.strip() or "Untitled",
                            "products": list(cb_selected),
                            "weights": dict(cb_weights),
                        }
                        st.success(
                            f"Saved basket '{cb_basket_name.strip()}' "
                            f"with {len(cb_selected)} products."
                        )
                with _save_cols[1]:
                    st.caption(
                        f"{len(st.session_state.user_baskets)} basket(s) saved"
                    )

                # --- Live basket performance preview ---
                st.divider()
                st.markdown("#### Basket Performance Preview")

                basket_df = filtered[
                    filtered["product_name"].isin(cb_selected)
                ].copy()

                if basket_df.empty:
                    st.warning("No data for selected products in current filters.")
                else:
                    basket_df["period"] = basket_df["timestamp"].dt.to_period("M")
                    basket_df["period_dt"] = basket_df["period"].dt.to_timestamp()

                    period_prices = (
                        basket_df.groupby(["period_dt", "product_name"], observed=True)["price"]
                        .median()
                        .unstack(fill_value=np.nan)
                    )

                    if period_prices.empty:
                        st.warning("Not enough data to compute basket index.")
                    else:
                        period_prices = period_prices.sort_index().ffill()

                        product_indices = pd.DataFrame(index=period_prices.index)
                        for _bp in cb_selected:
                            if _bp not in period_prices.columns:
                                continue
                            _bseries = period_prices[_bp].dropna()
                            if _bseries.empty:
                                continue
                            _base_p = _bseries.iloc[0]
                            if _base_p > 0:
                                product_indices[_bp] = (
                                    period_prices[_bp] / _base_p * 100
                                )

                        if product_indices.empty:
                            st.warning("Not enough data to compute basket index.")
                        else:
                            basket_index = pd.Series(
                                0.0, index=product_indices.index
                            )
                            for _bp in product_indices.columns:
                                _bw = cb_norm_weights.get(_bp, 0)
                                basket_index += (
                                    product_indices[_bp].fillna(100) * _bw
                                )
                            basket_index = basket_index.dropna()

                            if len(basket_index) < 2:
                                st.warning(
                                    "Need at least 2 time periods. "
                                    "Try products with more coverage."
                                )
                            else:
                                _bstart = basket_index.iloc[0]
                                _bend = basket_index.iloc[-1]
                                _btotal = ((_bend - _bstart) / _bstart) * 100
                                _bsd = basket_index.index[0]
                                _bed = basket_index.index[-1]
                                _bnyrs = max(
                                    (_bed - _bsd).days / 365.25, 0.01
                                )
                                _bann = (
                                    (_bend / _bstart) ** (1 / _bnyrs) - 1
                                ) * 100

                                mc1, mc2, mc3, mc4 = st.columns(4)
                                with mc1:
                                    _dir = "Inflation" if _btotal > 0 else "Deflation"
                                    st.metric(
                                        f"Total {_dir}",
                                        f"{abs(_btotal):.1f}%",
                                        delta=f"{_btotal:+.1f}%",
                                        delta_color="inverse",
                                    )
                                with mc2:
                                    st.metric(
                                        "Annualized",
                                        f"{_bann:+.1f}%/yr",
                                    )
                                with mc3:
                                    st.metric(
                                        "Peak",
                                        f"{basket_index.max():.1f}",
                                        delta=f"{basket_index.max() - 100:+.1f}",
                                        delta_color="inverse",
                                    )
                                with mc4:
                                    st.metric(
                                        "Trough",
                                        f"{basket_index.min():.1f}",
                                        delta=f"{basket_index.min() - 100:+.1f}",
                                        delta_color="inverse",
                                    )

                                st.caption(
                                    f"Period: {_bsd.strftime('%b %Y')} - "
                                    f"{_bed.strftime('%b %Y')} "
                                    f"({_bnyrs:.1f} years)"
                                )

                                # Basket index chart
                                fig_cb = go.Figure()
                                fig_cb.add_trace(go.Scatter(
                                    x=basket_index.index,
                                    y=basket_index.values,
                                    mode="lines",
                                    name="Basket Index",
                                    line=dict(color="#1f77b4", width=2.5),
                                    fill="tozeroy",
                                    fillcolor="rgba(31, 119, 180, 0.1)",
                                ))
                                fig_cb.add_hline(
                                    y=100,
                                    line_dash="dash",
                                    line_color="gray",
                                    annotation_text="Base (100)",
                                    annotation_position="bottom right",
                                )
                                fig_cb.update_layout(
                                    xaxis_title="Date",
                                    yaxis_title="Basket Index",
                                    height=450,
                                    margin=dict(l=50, r=20, t=30, b=50),
                                    hovermode="x unified",
                                    yaxis=dict(tickformat=".1f"),
                                )
                                st.plotly_chart(
                                    fig_cb, use_container_width=True
                                )

                                # Individual product indices
                                with st.expander("Individual Product Indices"):
                                    fig_bp = go.Figure()
                                    _bp_colors = px.colors.qualitative.Set2
                                    for _bi, _bprod in enumerate(
                                        product_indices.columns
                                    ):
                                        fig_bp.add_trace(go.Scatter(
                                            x=product_indices.index,
                                            y=product_indices[_bprod],
                                            mode="lines",
                                            name=_bprod[:50],
                                            line=dict(
                                                color=_bp_colors[
                                                    _bi % len(_bp_colors)
                                                ]
                                            ),
                                        ))
                                    fig_bp.add_hline(
                                        y=100,
                                        line_dash="dash",
                                        line_color="gray",
                                    )
                                    fig_bp.update_layout(
                                        xaxis_title="Date",
                                        yaxis_title="Price Index (Base = 100)",
                                        height=400,
                                        margin=dict(l=50, r=20, t=30, b=50),
                                        hovermode="x unified",
                                        legend=dict(
                                            orientation="h",
                                            yanchor="bottom",
                                            y=-0.3,
                                            xanchor="center",
                                            x=0.5,
                                        ),
                                    )
                                    st.plotly_chart(
                                        fig_bp, use_container_width=True
                                    )

                                # Raw data
                                with st.expander("Basket Raw Data"):
                                    _raw = basket_df[
                                        [
                                            "timestamp", "chain", "location",
                                            "product_name", "price", "unit",
                                            "sale", "wayback_url",
                                        ]
                                    ].sort_values("timestamp")
                                    st.dataframe(
                                        _raw.head(500),
                                        use_container_width=True,
                                        hide_index=True,
                                    )
                                    if len(_raw) > 500:
                                        st.caption(
                                            f"Showing first 500 of "
                                            f"{len(_raw):,} rows."
                                        )


# ===========================================================================
# TAB 4: HARTER HOUSE CASE STUDY
# ===========================================================================
with tab_hh:

    # -------------------------------------------------------------------
    # Custom CSS matching Harter House website color scheme
    # -------------------------------------------------------------------
    st.markdown("""
    <style>
    .hh-header {
        background: linear-gradient(135deg, #300606 0%, #4a0e0e 100%);
        padding: 24px 32px;
        border-radius: 8px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 24px;
    }
    .hh-header img {
        height: 100px;
    }
    .hh-header-text h1 {
        color: #c7a34b;
        font-family: Georgia, serif;
        font-size: 28px;
        margin: 0 0 4px 0;
        letter-spacing: 0.03em;
    }
    .hh-header-text h2 {
        color: #e5c380;
        font-family: Georgia, serif;
        font-size: 15px;
        font-weight: normal;
        font-style: italic;
        margin: 0;
    }
    .hh-section-rule {
        border: none;
        border-top: 4px double #8f273e;
        margin: 28px 0 20px 0;
    }
    .hh-section-title {
        font-family: Georgia, serif;
        font-size: 22px;
        color: #7e1b14;
        border-bottom: 4px double #8f273e;
        padding-bottom: 6px;
        margin-bottom: 16px;
    }
    .hh-bundle-card {
        background: #faf6ee;
        border: 1px solid #d1c9b0;
        border-bottom: 3px solid #8f273e;
        border-radius: 6px;
        padding: 14px 12px 12px 12px;
        margin-bottom: 14px;
        min-height: 220px;
    }
    .hh-bundle-card h3 {
        font-family: Georgia, serif;
        font-size: 16px;
        font-weight: bold;
        color: #7e1b14;
        margin: 0 0 8px 0;
        line-height: 1.3;
    }
    .hh-bundle-card ul {
        list-style: none;
        padding: 0;
        margin: 0 0 10px 0;
    }
    .hh-bundle-card ul li {
        font-family: Helvetica, Arial, sans-serif;
        font-size: 12.5px;
        line-height: 1.55;
        color: #333;
    }
    .hh-bundle-price {
        font-family: Georgia, serif;
        font-weight: bold;
        font-size: 15px;
        color: #2a0506;
        margin-top: 6px;
    }
    .hh-price-badge {
        display: inline-block;
        font-size: 11.5px;
        font-weight: bold;
        padding: 2px 7px;
        border-radius: 4px;
        margin-left: 6px;
    }
    .hh-price-up {
        background: #f8d7da;
        color: #842029;
    }
    .hh-price-down {
        background: #d1e7dd;
        color: #0f5132;
    }
    .hh-price-same {
        background: #e2e3e5;
        color: #41464b;
    }
    .hh-intro {
        font-family: Helvetica, Arial, sans-serif;
        font-size: 14px;
        line-height: 1.6;
        color: #333;
        margin-bottom: 8px;
    }
    .hh-disclaimer {
        font-family: Georgia, serif;
        font-style: italic;
        font-size: 13px;
        color: #666;
        margin-top: 8px;
    }
    .hh-locations-title {
        font-family: Georgia, serif;
        font-size: 18px;
        font-weight: bold;
        color: #7d1a13;
        margin: 0 0 12px 0;
        text-align: center;
    }

    </style>
    """, unsafe_allow_html=True)

    # -------------------------------------------------------------------
    # Data preparation
    # -------------------------------------------------------------------
    hh_all = df[df["chain"] == "Harter House"].copy()
    hh_bundles = hh_all[hh_all["unit"] == "bundle"].copy()

    # Normalize #15 Classique -> Classic for continuity
    hh_bundles["product_name"] = hh_bundles["product_name"].str.replace(
        r"#15 Classique Steak Pack",
        "#15 Classic Steak Pack",
        regex=False,
    )

    # Build snapshot index
    hh_bundles["ts_str"] = hh_bundles["timestamp"].dt.strftime("%Y-%m-%d")
    snapshot_dates = sorted(hh_bundles["ts_str"].unique())
    snapshot_labels = {
        d: pd.to_datetime(d).strftime("%b %d, %Y") for d in snapshot_dates
    }

    # Ordered bundle list matching the website layout
    BUNDLE_ORDER = [
        "1/2 A Hog",
        "#1 Beef Bundle",
        "#2 Steak Bundle",
        "#3 Roast Bundle",
        "#4 Pork Bundle",
        "#5 Assorted Quarters",
        "#6 Piggy Back",
        "#7 Deluxe Steak Pack",
        "#8 Chicken Pack",
        "#9 Variety Pack",
        "#10 Economy Pack",
        "#11 Family Pack",
        "#12 Ground Beef Pack",
        "#13 Budget Bundle",
        "#14 Mixed Bundle",
        "#15 Classic Steak Pack",
    ]

    # Earliest price per bundle for change badges
    earliest_prices = {}
    for bname in BUNDLE_ORDER:
        bdata = hh_bundles[hh_bundles["product_name"] == bname].sort_values(
            "timestamp"
        )
        if not bdata.empty:
            earliest_prices[bname] = bdata.iloc[0]["price"]

    # -------------------------------------------------------------------
    # Section 1: Header & Branding
    # -------------------------------------------------------------------
    st.markdown("""
    <div class="hh-header">
        <img src="https://www.harterhouse.com/images/harter-house-logo.png"
             alt="Harter House Logo" />
        <div class="hh-header-text">
            <h1>Famous For Our Meats</h1>
            <h2>We're Your Old Fashioned Neighborhood Market</h2>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <p class="hh-intro">
        <strong>Harter House</strong> is a family-owned grocery chain with
        7 locations across the Springfield, Missouri area, including Nixa,
        Strafford, Hollister, Kimberling City, Shell Knob, and Berryville, AR.
        Known for their full-service butcher counters and meat quality, they
        offer 15 named meat bundle packs with stable compositions.
    </p>
    <p class="hh-intro">
        This case study tracks Harter House bundle prices across
        <strong>33 Wayback Machine snapshots</strong> from January 2020 to
        October 2025, providing a unique longitudinal view of retail meat
        pricing through the COVID-19 pandemic and the subsequent inflation
        period.
    </p>
    """, unsafe_allow_html=True)

    # Store locations map & directory
    import pydeck as pdk

    hh_stores = pd.DataFrame([
        {"name": "South Springfield", "address": "1500 E Republic Rd", "city": "Springfield, MO", "phone": "(417) 886-4410", "lat": 37.1614, "lon": -93.2656, "note": "& World Flavors"},
        {"name": "Eastgate", "address": "1625 S Eastgate Ave", "city": "Springfield, MO", "phone": "(417) 883-1650", "lat": 37.1801, "lon": -93.2347, "note": ""},
        {"name": "Nixa", "address": "815 W Kenneth St", "city": "Nixa, MO", "phone": "(417) 724-1470", "lat": 37.0456, "lon": -93.2985, "note": ""},
        {"name": "Strafford", "address": "421 E Old Route 66", "city": "Strafford, MO", "phone": "(417) 736-2100", "lat": 37.2706, "lon": -93.1172, "note": ""},
        {"name": "Kimberling City", "address": "11798 Missouri 13", "city": "Kimberling City, MO", "phone": "(417) 739-4811", "lat": 36.6340, "lon": -93.4170, "note": ""},
        {"name": "Hollister", "address": "175 Gage Dr", "city": "Hollister, MO", "phone": "(417) 336-3616", "lat": 36.6218, "lon": -93.2150, "note": ""},
        {"name": "Shell Knob", "address": "24988 MO-39", "city": "Shell Knob, MO", "phone": "(417) 858-6647", "lat": 36.6327, "lon": -93.6347, "note": ""},
        {"name": "Berryville", "address": "326 Eureka Ave", "city": "Berryville, AR", "phone": "(870) 423-1088", "lat": 36.3625, "lon": -93.5683, "note": ""},
    ])

    st.markdown(
        '<div class="hh-locations-title">8 Locations Across Southwest Missouri & Northwest Arkansas</div>',
        unsafe_allow_html=True,
    )

    map_layer = pdk.Layer(
        "ScatterplotLayer",
        data=hh_stores,
        get_position=["lon", "lat"],
        get_radius=2500,
        get_fill_color=[126, 27, 20, 200],  # Harter House maroon
        pickable=True,
        auto_highlight=True,
        get_line_color=[143, 39, 62],
        line_width_min_pixels=1,
    )
    label_layer = pdk.Layer(
        "TextLayer",
        data=hh_stores,
        get_position=["lon", "lat"],
        get_text="name",
        get_size=14,
        get_color=[80, 15, 10],
        get_angle=0,
        get_text_anchor='"middle"',
        get_alignment_baseline='"top"',
        get_pixel_offset=[0, 14],
        font_family='"Georgia, serif"',
    )
    view = pdk.ViewState(
        latitude=36.82,
        longitude=-93.38,
        zoom=7.5,
        pitch=0,
    )
    st.pydeck_chart(
        pdk.Deck(
            layers=[map_layer, label_layer],
            initial_view_state=view,
            tooltip={"text": "{name}\n{address}\n{city}\n{phone}"},
            map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        ),
        use_container_width=True,
    )



    if hh_bundles.empty:
        st.warning("No Harter House bundle data available.")
        st.stop()

    # -------------------------------------------------------------------
    # Section 2: Snapshot Time-Travel Menu
    # -------------------------------------------------------------------
    st.markdown(
        '<hr class="hh-section-rule">'
        '<div class="hh-section-title">Bundle Packs &mdash; '
        "We Specialize In Quality Meats</div>",
        unsafe_allow_html=True,
    )

    selected_snap = st.select_slider(
        "Travel through time: select a Wayback Machine snapshot",
        options=snapshot_dates,
        value=snapshot_dates[-1],
        format_func=lambda d: snapshot_labels.get(d, d),
        key="hh_snapshot_slider",
    )

    # Filter to selected snapshot
    snap_df = hh_bundles[hh_bundles["ts_str"] == selected_snap]

    # Build the 4-column bundle grid
    cols_per_row = 4
    displayed_bundles = [
        b for b in BUNDLE_ORDER
        if b in snap_df["product_name"].values
    ]

    for row_start in range(0, len(displayed_bundles), cols_per_row):
        row_bundles = displayed_bundles[row_start:row_start + cols_per_row]
        cols = st.columns(cols_per_row)
        for idx, bname in enumerate(row_bundles):
            brow = snap_df[snap_df["product_name"] == bname].iloc[0]
            price = brow["price"]
            # Price change badge
            badge_html = ""
            base_price = earliest_prices.get(bname)
            if base_price and base_price > 0 and price != base_price:
                pct = ((price - base_price) / base_price) * 100
                if pct > 0:
                    badge_html = (
                        f'<span class="hh-price-badge hh-price-up">'
                        f"+{pct:.0f}%</span>"
                    )
                elif pct < 0:
                    badge_html = (
                        f'<span class="hh-price-badge hh-price-down">'
                        f"{pct:.0f}%</span>"
                    )
            elif base_price and price == base_price:
                badge_html = (
                    '<span class="hh-price-badge hh-price-same">'
                    "unchanged</span>"
                )

            card_html = f"""
            <div class="hh-bundle-card">
                <h3>{bname}</h3>
                <div class="hh-bundle-price">
                    ${price:,.2f}{badge_html}
                </div>
            </div>
            """
            with cols[idx]:
                st.markdown(card_html, unsafe_allow_html=True)

    st.markdown(
        '<p class="hh-disclaimer">'
        "Due to unstable meat costs Bundle prices are subject to change "
        "without notice</p>",
        unsafe_allow_html=True,
    )

    # -------------------------------------------------------------------
    # Section 3: Bundle Price Index (combined chart)
    # -------------------------------------------------------------------
    st.markdown(
        '<hr class="hh-section-rule">'
        '<div class="hh-section-title">'
        "Bundle Price Index</div>",
        unsafe_allow_html=True,
    )

    weighting_mode = st.radio(
        "Aggregate weighting",
        options=["Equal-weighted", "Dollar-weighted (by price)"],
        index=0,
        key="hh_weighting",
        horizontal=True,
    )

    # Build index matrix for all bundles with full 2020-2025 coverage
    basket_bundles = []
    for bname in BUNDLE_ORDER:
        bdata = hh_bundles[hh_bundles["product_name"] == bname]
        years_covered = set(bdata["year"].unique())
        required = {2020, 2021, 2022, 2023, 2024, 2025}
        if required.issubset(years_covered):
            basket_bundles.append(bname)

    if len(basket_bundles) < 2:
        st.warning("Not enough bundles with full 2020-2025 coverage.")
    else:
        basket_df_hh = hh_bundles[
            hh_bundles["product_name"].isin(basket_bundles)
        ].copy()

        price_matrix = basket_df_hh.pivot_table(
            index="timestamp",
            columns="product_name",
            values="price",
            aggfunc="first",
        ).sort_index()

        # Compute index for each bundle (base = 100 at first observation)
        index_matrix = pd.DataFrame(index=price_matrix.index)
        base_prices_basket = {}
        for bname in basket_bundles:
            if bname in price_matrix.columns:
                series = price_matrix[bname].dropna()
                if not series.empty:
                    base_p = series.iloc[0]
                    base_prices_basket[bname] = base_p
                    if base_p > 0:
                        index_matrix[bname] = (
                            price_matrix[bname] / base_p * 100
                        )

        if index_matrix.empty:
            st.warning("Not enough data to compute basket index.")
        else:
            # Compute weighted aggregate basket index
            if weighting_mode == "Equal-weighted":
                weights_hh = {
                    b: 1.0 / len(index_matrix.columns)
                    for b in index_matrix.columns
                }
            else:
                total_base = sum(
                    base_prices_basket.get(b, 0)
                    for b in index_matrix.columns
                )
                weights_hh = {
                    b: base_prices_basket.get(b, 0) / total_base
                    for b in index_matrix.columns
                } if total_base > 0 else {
                    b: 1.0 / len(index_matrix.columns)
                    for b in index_matrix.columns
                }

            basket_idx = pd.Series(0.0, index=index_matrix.index)
            for bname in index_matrix.columns:
                w = weights_hh.get(bname, 0)
                basket_idx += index_matrix[bname].ffill().fillna(100) * w
            basket_idx = basket_idx.dropna()

            # Bundle selector — default to aggregate + two featured bundles
            _AGGREGATE_LABEL = "Aggregate (All Bundles)"
            available_bundles = [_AGGREGATE_LABEL] + [
                b for b in BUNDLE_ORDER
                if b in index_matrix.columns
            ]
            default_picks = [_AGGREGATE_LABEL]
            for pick in ["#6 Piggy Back", "#5 Assorted Quarters"]:
                if pick in available_bundles:
                    default_picks.append(pick)

            selected_lines = st.multiselect(
                "Select lines to display",
                options=available_bundles,
                default=default_picks,
                key="hh_bundle_select",
            )

            if selected_lines and len(basket_idx) >= 2:
                # Summary metrics from aggregate
                start_v = basket_idx.iloc[0]
                end_v = basket_idx.iloc[-1]
                total_chg = ((end_v - start_v) / start_v) * 100
                start_dt = basket_idx.index[0]
                end_dt = basket_idx.index[-1]
                n_yrs = max(
                    (end_dt - start_dt).days / 365.25, 0.01
                )
                ann_chg = (
                    (end_v / start_v) ** (1 / n_yrs) - 1
                ) * 100

                mc1, mc2, mc3 = st.columns(3)
                with mc1:
                    st.metric(
                        "Total Inflation",
                        f"{total_chg:.1f}%",
                        delta=f"{total_chg:+.1f}%",
                        delta_color="inverse",
                    )
                with mc2:
                    st.metric(
                        "Annualized",
                        f"{ann_chg:+.1f}%/yr",
                    )
                with mc3:
                    st.metric(
                        "Period",
                        f"{start_dt.strftime('%b %Y')} - "
                        f"{end_dt.strftime('%b %Y')}",
                    )

                # Color palette for individual bundles
                hh_colors = [
                    "#c7a34b", "#8f273e", "#5b450e", "#a85a32",
                    "#4a0e0e", "#d4a855", "#6b2d3e", "#8b6914",
                    "#b5453a", "#3d2b06", "#c48a5c", "#922d42",
                    "#7a6320", "#d47a6e", "#2a0506",
                ]

                fig_combined = go.Figure()
                color_idx = 0
                # Collect end-points for labels
                _end_labels = []

                for line_name in selected_lines:
                    if line_name == _AGGREGATE_LABEL:
                        chg = ((basket_idx.iloc[-1] - basket_idx.iloc[0])
                               / basket_idx.iloc[0] * 100)
                        fig_combined.add_trace(go.Scatter(
                            x=basket_idx.index,
                            y=basket_idx.values,
                            mode="lines+markers",
                            name=f"Aggregate ({chg:+.0f}%)",
                            line=dict(color="#7e1b14", width=4),
                            marker=dict(size=7, color="#7e1b14"),
                            fill="tozeroy",
                            fillcolor="rgba(126, 27, 20, 0.07)",
                            hovertemplate=(
                                "<b>Aggregate</b><br>"
                                "Date: %{x|%b %d, %Y}<br>"
                                "Index: %{y:.1f}<br>"
                                "<extra></extra>"
                            ),
                        ))
                        _end_labels.append((
                            basket_idx.index[-1],
                            basket_idx.iloc[-1],
                            f"Aggregate ({chg:+.0f}%)",
                            "#7e1b14", True,
                        ))
                    else:
                        if line_name not in index_matrix.columns:
                            continue
                        s = index_matrix[line_name].dropna()
                        if s.empty:
                            continue
                        chg = ((s.iloc[-1] - s.iloc[0])
                               / s.iloc[0] * 100)
                        lc = hh_colors[color_idx % len(hh_colors)]
                        fig_combined.add_trace(go.Scatter(
                            x=s.index,
                            y=s.values,
                            mode="lines+markers",
                            name=f"{line_name} ({chg:+.0f}%)",
                            line=dict(color=lc, width=2, dash="dot"),
                            marker=dict(size=4),
                            hovertemplate=(
                                f"<b>{line_name}</b><br>"
                                "Date: %{x|%b %d, %Y}<br>"
                                "Index: %{y:.1f}<br>"
                                "<extra></extra>"
                            ),
                        ))
                        _end_labels.append((
                            s.index[-1], s.iloc[-1],
                            f"{line_name} ({chg:+.0f}%)",
                            lc, False,
                        ))
                        color_idx += 1

                # End-of-line labels
                for _lx, _ly, _lt, _lcolor, _bold in _end_labels:
                    fig_combined.add_annotation(
                        x=_lx, y=_ly,
                        text=(f"<b>{_lt}</b>" if _bold else _lt),
                        xanchor="left",
                        yanchor="middle",
                        xshift=8,
                        showarrow=False,
                        font=dict(
                            color=_lcolor,
                            size=12 if _bold else 10,
                        ),
                        bgcolor="rgba(255,255,255,0.8)",
                    )

                # Base-100 reference line
                fig_combined.add_hline(
                    y=100,
                    line_dash="dash",
                    line_color="#8f273e",
                    line_width=1,
                    annotation_text="Base (100)",
                    annotation_position="bottom right",
                    annotation_font_color="#8f273e",
                )

                fig_combined.update_layout(
                    xaxis_title="Date",
                    yaxis=dict(
                        title="Price Index (Jan 2020 = 100)",
                        gridcolor="rgba(143, 39, 62, 0.1)",
                    ),
                    height=500,
                    margin=dict(l=60, r=180, t=30, b=60),
                    hovermode="x unified",
                    plot_bgcolor="rgba(250, 246, 238, 0.3)",
                    paper_bgcolor="white",
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=-0.25,
                        xanchor="center",
                        x=0.5,
                        font=dict(size=11),
                    ),
                    xaxis=dict(
                        gridcolor="rgba(143, 39, 62, 0.08)",
                    ),
                )

                st.plotly_chart(fig_combined, use_container_width=True)

    # -------------------------------------------------------------------
    # Section 5: Data Source & Citations
    # -------------------------------------------------------------------
    st.markdown(
        '<hr class="hh-section-rule">'
        '<div class="hh-section-title">'
        "Data Source &amp; Citations</div>",
        unsafe_allow_html=True,
    )

    with st.expander("Methodology & Data Provenance"):
        st.markdown("""
**Data Collection**: Pricing data was extracted from archived snapshots of
[harterhouse.com/bundle-packs](https://www.harterhouse.com/bundle-packs)
preserved by the [Wayback Machine](https://web.archive.org).

**Coverage**: 33 snapshots spanning January 2020 through October 2025,
capturing bundle names, component item lists, and total prices.

**Scope**: 15 named meat bundle packs, plus steak gift packs and party
trays. Weekly ad sale prices were also extracted via PDF OCR from
store-specific flyers.

**Limitations**: Snapshots are not evenly spaced; some months/quarters
have no archived data. Component items within bundles occasionally
changed (e.g., #3 Roast Bundle switched from "Boneless Pot Roast"
to "Boneless Chuck Roast"). The basket index uses the bundle as the
unit of analysis regardless of composition changes.
        """)

    with st.expander("Browse Raw Bundle Data"):
        hh_display = hh_bundles[
            [
                "timestamp", "product_name", "price", "unit",
                "description", "wayback_url",
            ]
        ].sort_values(["product_name", "timestamp"])
        st.dataframe(
            hh_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "wayback_url": st.column_config.LinkColumn(
                    "Wayback URL",
                    display_text="View Archive",
                ),
                "price": st.column_config.NumberColumn(
                    "Price",
                    format="$%.2f",
                ),
            },
        )
        st.caption(
            f"{len(hh_display):,} bundle price observations across "
            f"{len(snapshot_dates)} snapshots."
        )
