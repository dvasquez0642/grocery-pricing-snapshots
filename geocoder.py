"""
Location parsing and geocoding for the pricing dashboard.

Extracts geographic information from the free-text `location` column
in pricing CSVs and maps to approximate lat/lon coordinates using a
bundled US state/city lookup table. No external API calls.
"""

import re
from typing import Optional

# ---------------------------------------------------------------------------
# Location type constants
# ---------------------------------------------------------------------------
LOC_STORE = "store-specific"
LOC_CITY = "city-level"
LOC_CHAIN = "chain-wide"
LOC_UNKNOWN = "unknown"

ALL_LOCATION_TYPES = [LOC_STORE, LOC_CITY, LOC_CHAIN, LOC_UNKNOWN]

# ---------------------------------------------------------------------------
# US state abbreviations -> (lat, lon) centroids
# ---------------------------------------------------------------------------
STATE_COORDS: dict[str, tuple[float, float]] = {
    "AL": (32.806671, -86.791130),
    "AK": (61.370716, -152.404419),
    "AZ": (33.729759, -111.431221),
    "AR": (34.969704, -92.373123),
    "CA": (36.116203, -119.681564),
    "CO": (39.059811, -105.311104),
    "CT": (41.597782, -72.755371),
    "DE": (39.318523, -75.507141),
    "FL": (27.766279, -81.686783),
    "GA": (33.040619, -83.643074),
    "HI": (21.094318, -157.498337),
    "ID": (44.240459, -114.478773),
    "IL": (40.349457, -88.986137),
    "IN": (39.849426, -86.258278),
    "IA": (42.011539, -93.210526),
    "KS": (38.526600, -96.726486),
    "KY": (37.668140, -84.670067),
    "LA": (31.169546, -91.867805),
    "ME": (44.693947, -69.381927),
    "MD": (39.063946, -76.802101),
    "MA": (42.230171, -71.530106),
    "MI": (43.326618, -84.536095),
    "MN": (45.694454, -93.900192),
    "MS": (32.741646, -89.678696),
    "MO": (38.456085, -92.288368),
    "MT": (46.921925, -110.454353),
    "NE": (41.125370, -98.268082),
    "NV": (38.313515, -117.055374),
    "NH": (43.452492, -71.563896),
    "NJ": (40.298904, -74.521011),
    "NM": (34.840515, -106.248482),
    "NY": (42.165726, -74.948051),
    "NC": (35.630066, -79.806419),
    "ND": (47.528912, -99.784012),
    "OH": (40.388783, -82.764915),
    "OK": (35.565342, -96.928917),
    "OR": (44.572021, -122.070938),
    "PA": (40.590752, -77.209755),
    "RI": (41.680893, -71.511780),
    "SC": (33.856892, -80.945007),
    "SD": (44.299782, -99.438828),
    "TN": (35.747845, -86.692345),
    "TX": (31.054487, -97.563461),
    "UT": (40.150032, -111.862434),
    "VT": (44.045876, -72.710686),
    "VA": (37.769337, -78.169968),
    "WA": (47.400902, -121.490494),
    "WV": (38.491226, -80.954453),
    "WI": (44.268543, -89.616508),
    "WY": (42.755966, -107.302490),
    "DC": (38.897438, -77.026817),
}

# State full names -> abbreviation
STATE_NAMES: dict[str, str] = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT",
    "delaware": "DE", "florida": "FL", "georgia": "GA", "hawaii": "HI",
    "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME",
    "maryland": "MD", "massachusetts": "MA", "michigan": "MI",
    "minnesota": "MN", "mississippi": "MS", "missouri": "MO",
    "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM",
    "new york": "NY", "north carolina": "NC", "north dakota": "ND",
    "ohio": "OH", "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
    "rhode island": "RI", "south carolina": "SC", "south dakota": "SD",
    "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
    "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY", "district of columbia": "DC",
}

# ---------------------------------------------------------------------------
# Major US cities -> (lat, lon)
# ~200 cities covering most metro areas where grocery chains operate
# ---------------------------------------------------------------------------
CITY_COORDS: dict[str, tuple[float, float]] = {
    # Format: "city, ST" -> (lat, lon)
    "new york, ny": (40.7128, -74.0060),
    "los angeles, ca": (34.0522, -118.2437),
    "chicago, il": (41.8781, -87.6298),
    "houston, tx": (29.7604, -95.3698),
    "phoenix, az": (33.4484, -112.0740),
    "philadelphia, pa": (39.9526, -75.1652),
    "san antonio, tx": (29.4241, -98.4936),
    "san diego, ca": (32.7157, -117.1611),
    "dallas, tx": (32.7767, -96.7970),
    "san jose, ca": (37.3382, -121.8863),
    "austin, tx": (30.2672, -97.7431),
    "jacksonville, fl": (30.3322, -81.6557),
    "fort worth, tx": (32.7555, -97.3308),
    "columbus, oh": (39.9612, -82.9988),
    "charlotte, nc": (35.2271, -80.8431),
    "indianapolis, in": (39.7684, -86.1581),
    "san francisco, ca": (37.7749, -122.4194),
    "seattle, wa": (47.6062, -122.3321),
    "denver, co": (39.7392, -104.9903),
    "washington, dc": (38.9072, -77.0369),
    "nashville, tn": (36.1627, -86.7816),
    "oklahoma city, ok": (35.4676, -97.5164),
    "el paso, tx": (31.7619, -106.4850),
    "boston, ma": (42.3601, -71.0589),
    "portland, or": (45.5152, -122.6784),
    "las vegas, nv": (36.1699, -115.1398),
    "memphis, tn": (35.1495, -90.0490),
    "louisville, ky": (38.2527, -85.7585),
    "baltimore, md": (39.2904, -76.6122),
    "milwaukee, wi": (43.0389, -87.9065),
    "albuquerque, nm": (35.0844, -106.6504),
    "tucson, az": (32.2226, -110.9747),
    "fresno, ca": (36.7378, -119.7871),
    "mesa, az": (33.4152, -111.8315),
    "sacramento, ca": (38.5816, -121.4944),
    "atlanta, ga": (33.7490, -84.3880),
    "kansas city, mo": (39.0997, -94.5786),
    "omaha, ne": (41.2565, -95.9345),
    "colorado springs, co": (38.8339, -104.8214),
    "raleigh, nc": (35.7796, -78.6382),
    "long beach, ca": (33.7701, -118.1937),
    "virginia beach, va": (36.8529, -75.9780),
    "miami, fl": (25.7617, -80.1918),
    "oakland, ca": (37.8044, -122.2712),
    "minneapolis, mn": (44.9778, -93.2650),
    "tulsa, ok": (36.1540, -95.9928),
    "tampa, fl": (27.9506, -82.4572),
    "arlington, tx": (32.7357, -97.1081),
    "new orleans, la": (29.9511, -90.0715),
    "cleveland, oh": (41.4993, -81.6944),
    "honolulu, hi": (21.3069, -157.8583),
    "anaheim, ca": (33.8366, -117.9143),
    "orlando, fl": (28.5383, -81.3792),
    "cincinnati, oh": (39.1031, -84.5120),
    "pittsburgh, pa": (40.4406, -79.9959),
    "st. louis, mo": (38.6270, -90.1994),
    "st louis, mo": (38.6270, -90.1994),
    "greensboro, nc": (36.0726, -79.7920),
    "lincoln, ne": (40.8136, -96.7026),
    "buffalo, ny": (42.8864, -78.8784),
    "detroit, mi": (42.3314, -83.0458),
    "richmond, va": (37.5407, -77.4360),
    "baton rouge, la": (30.4515, -91.1871),
    "salt lake city, ut": (40.7608, -111.8910),
    "birmingham, al": (33.5207, -86.8025),
    "hartford, ct": (41.7658, -72.6734),
    "rochester, ny": (43.1566, -77.6088),
    "spokane, wa": (47.6588, -117.4260),
    "des moines, ia": (41.5868, -93.6250),
    "providence, ri": (41.8240, -71.4128),
    "little rock, ar": (34.7465, -92.2896),
    "boise, id": (43.6150, -116.2023),
    "columbia, sc": (34.0007, -81.0348),
    "charleston, sc": (32.7765, -79.9311),
    "savannah, ga": (32.0809, -81.0912),
    "chula vista, ca": (32.6401, -117.0842),
    "terre haute, in": (39.4667, -87.4139),
    "meredith, nh": (43.6573, -71.4998),
    "harrisburg, pa": (40.2732, -76.8867),
    "mechanicsburg, pa": (40.2143, -76.9994),
    "south bend, in": (41.6764, -86.2520),
    "edgewater, md": (38.9576, -76.5497),
    "albany, ny": (42.6526, -73.7562),
    "newark, nj": (40.7357, -74.1724),
    "jersey city, nj": (40.7178, -74.0431),
    "madison, wi": (43.0731, -89.4012),
    "anchorage, ak": (61.2181, -149.9003),
    "st. paul, mn": (44.9537, -93.0900),
    "st paul, mn": (44.9537, -93.0900),
    "durham, nc": (35.9940, -78.8986),
    "reno, nv": (39.5296, -119.8138),
    "springfield, ma": (42.1015, -72.5898),
    "springfield, il": (39.7817, -89.6501),
    "springfield, mo": (37.2090, -93.2923),
    "knoxville, tn": (35.9606, -83.9207),
    "dayton, oh": (39.7589, -84.1916),
    "canton, oh": (40.7990, -81.3784),
    "akron, oh": (41.0814, -81.5190),
    "toledo, oh": (41.6528, -83.5379),
    "syracuse, ny": (43.0481, -76.1474),
    "lisbon, ct": (41.6038, -72.0070),
    "canterbury, ct": (41.6979, -72.0959),
}

# ---------------------------------------------------------------------------
# ZIP code prefix -> approximate (lat, lon)
# First 3 digits of ZIP mapped to region centroids
# ---------------------------------------------------------------------------
ZIP3_COORDS: dict[str, tuple[float, float]] = {
    "010": (42.10, -72.59),  # Springfield MA
    "021": (42.36, -71.06),  # Boston MA
    "030": (43.00, -71.50),  # NH
    "032": (43.66, -71.50),  # NH (central)
    "060": (41.77, -72.67),  # Hartford CT
    "063": (41.30, -72.93),  # New Haven CT
    "070": (40.74, -74.17),  # Newark NJ
    "100": (40.71, -74.01),  # NYC
    "104": (40.85, -73.87),  # Bronx NY
    "112": (40.65, -73.95),  # Brooklyn NY
    "130": (43.05, -76.15),  # Syracuse NY
    "140": (42.89, -78.88),  # Buffalo NY
    "150": (40.44, -79.99),  # Pittsburgh PA
    "170": (40.27, -76.89),  # Harrisburg PA
    "190": (39.95, -75.17),  # Philadelphia PA
    "200": (38.90, -77.04),  # DC
    "210": (39.29, -76.61),  # Baltimore MD
    "270": (35.78, -78.64),  # Raleigh NC
    "282": (35.23, -80.84),  # Charlotte NC
    "303": (33.75, -84.39),  # Atlanta GA
    "327": (28.54, -81.38),  # Orlando FL
    "331": (25.76, -80.19),  # Miami FL
    "337": (27.95, -82.46),  # Tampa FL
    "400": (38.25, -85.76),  # Louisville KY
    "432": (39.96, -82.99),  # Columbus OH
    "441": (41.50, -81.69),  # Cleveland OH
    "452": (39.10, -84.51),  # Cincinnati OH
    "461": (39.77, -86.16),  # Indianapolis IN
    "478": (39.47, -87.41),  # Terre Haute IN
    "481": (42.33, -83.05),  # Detroit MI
    "530": (43.04, -87.91),  # Milwaukee WI
    "537": (43.07, -89.40),  # Madison WI
    "554": (44.98, -93.27),  # Minneapolis MN
    "600": (41.88, -87.63),  # Chicago IL
    "631": (38.63, -90.20),  # St Louis MO
    "641": (39.10, -94.58),  # Kansas City MO
    "658": (37.21, -93.29),  # Springfield MO
    "700": (29.95, -90.07),  # New Orleans LA
    "708": (30.45, -91.19),  # Baton Rouge LA
    "730": (35.47, -97.52),  # OKC
    "741": (36.15, -95.99),  # Tulsa OK
    "750": (32.78, -96.80),  # Dallas TX
    "770": (29.76, -95.37),  # Houston TX
    "781": (29.42, -98.49),  # San Antonio TX
    "787": (30.27, -97.74),  # Austin TX
    "802": (39.74, -104.99),  # Denver CO
    "841": (40.76, -111.89),  # SLC UT
    "850": (33.45, -112.07),  # Phoenix AZ
    "891": (36.17, -115.14),  # Las Vegas NV
    "900": (34.05, -118.24),  # LA
    "920": (32.72, -117.16),  # San Diego CA
    "921": (32.64, -117.08),  # Chula Vista CA
    "941": (37.77, -122.42),  # San Francisco CA
    "951": (33.95, -117.40),  # Riverside CA
    "958": (38.58, -121.49),  # Sacramento CA
    "967": (21.31, -157.86),  # Honolulu HI
    "970": (45.52, -122.68),  # Portland OR
    "981": (47.61, -122.33),  # Seattle WA
}

# US center for chain-wide fallback
US_CENTER = (39.8283, -98.5795)

# ---------------------------------------------------------------------------
# Regex patterns for location parsing
# ---------------------------------------------------------------------------
# "City, ST" or "City, ST (anything)"
_RE_CITY_STATE = re.compile(
    r"^([A-Za-z\s\.\'-]+),\s*([A-Z]{2})(?:\s|$|\()", re.IGNORECASE
)
# ZIP code (5 digits)
_RE_ZIP = re.compile(r"\b(\d{5})\b")
# State abbreviation at end or after city name
_RE_STATE_ABBR = re.compile(r"\b([A-Z]{2})\b")
# "All stores" pattern
_RE_ALL_STORES = re.compile(
    r"all\s+stores|chain[\s-]*wide|no\s+store\s+selected|my\s+store",
    re.IGNORECASE,
)
# Store ID pattern (various formats)
_RE_STORE_ID = re.compile(
    r"(?:store[\s_]*id|rsid)[/=:\s]*(\d+)", re.IGNORECASE
)


def _normalize_city_key(city: str, state: str) -> str:
    """Normalize a city name for lookup."""
    return f"{city.strip().lower()}, {state.strip().lower()}"


def _find_state_abbr(text: str) -> Optional[str]:
    """Try to find a 2-letter state abbreviation in text."""
    # First check for known state abbreviations
    for match in _RE_STATE_ABBR.finditer(text):
        abbr = match.group(1).upper()
        if abbr in STATE_COORDS:
            return abbr
    # Check for full state names
    text_lower = text.lower()
    for name, abbr in STATE_NAMES.items():
        if name in text_lower:
            return abbr
    return None


def geocode_location(location: str) -> tuple[Optional[float], Optional[float], str]:
    """
    Parse a location string and return (lat, lon, location_type).

    Returns:
        (lat, lon, location_type) where location_type is one of:
        - "store-specific": parsed from a street address or specific store
        - "city-level": parsed from city/state
        - "chain-wide": generic "all stores" type location
        - "unknown": could not parse
    """
    if not location or not isinstance(location, str):
        return (None, None, LOC_UNKNOWN)

    location = location.strip()

    # Check for "All stores" / generic patterns
    if _RE_ALL_STORES.search(location):
        # Try to extract a state from the generic string for better placement
        state = _find_state_abbr(location)
        if state and state in STATE_COORDS:
            lat, lon = STATE_COORDS[state]
            return (lat, lon, LOC_CHAIN)
        return (US_CENTER[0], US_CENTER[1], LOC_CHAIN)

    # Try "City, ST" pattern
    m = _RE_CITY_STATE.match(location)
    if m:
        city = m.group(1).strip()
        state = m.group(2).strip().upper()
        key = _normalize_city_key(city, state)
        if key in CITY_COORDS:
            lat, lon = CITY_COORDS[key]
            return (lat, lon, LOC_CITY)
        # Fall back to state centroid
        if state in STATE_COORDS:
            lat, lon = STATE_COORDS[state]
            return (lat, lon, LOC_CITY)

    # Try ZIP code extraction
    zip_match = _RE_ZIP.search(location)
    if zip_match:
        zip_code = zip_match.group(1)
        zip3 = zip_code[:3]
        if zip3 in ZIP3_COORDS:
            lat, lon = ZIP3_COORDS[zip3]
            return (lat, lon, LOC_STORE)
        # Use first digit for rough region
        state = _find_state_abbr(location)
        if state and state in STATE_COORDS:
            lat, lon = STATE_COORDS[state]
            return (lat, lon, LOC_STORE)

    # Try to find any state reference
    state = _find_state_abbr(location)
    if state and state in STATE_COORDS:
        lat, lon = STATE_COORDS[state]
        # If it looks like a specific store name, classify as store-specific
        if any(
            kw in location.lower()
            for kw in ["store", "market", "shop", "#", "location"]
        ):
            return (lat, lon, LOC_STORE)
        return (lat, lon, LOC_CITY)

    # Try city name lookup without state (check all known cities)
    loc_lower = location.lower().strip()
    for city_key, coords in CITY_COORDS.items():
        city_name = city_key.split(",")[0].strip()
        if city_name in loc_lower:
            return (coords[0], coords[1], LOC_CITY)

    return (None, None, LOC_UNKNOWN)


def geocode_series(locations) -> tuple[list, list, list]:
    """
    Geocode a pandas Series or list of location strings.

    Uses a cache of unique values to avoid redundant work – many rows
    share the same location string, so we only geocode each distinct
    value once and then map the results back.

    Returns:
        (lats, lons, location_types) - three parallel lists
    """
    import pandas as pd

    if not isinstance(locations, pd.Series):
        locations = pd.Series(locations)

    # Geocode only distinct values
    unique_locs = locations.fillna("").unique()
    cache: dict[str, tuple[Optional[float], Optional[float], str]] = {}
    for loc in unique_locs:
        cache[loc] = geocode_location(loc)

    # Map back to full series (use NaN instead of None for float columns)
    import numpy as np
    filled = locations.fillna("")
    lats = filled.map(lambda l: cache[l][0]).fillna(np.nan).tolist()
    lons = filled.map(lambda l: cache[l][1]).fillna(np.nan).tolist()
    loc_types = filled.map(lambda l: cache[l][2]).tolist()
    return lats, lons, loc_types
