"""
Product categorization based on the Target Items list from AGENTS.md.

Maps free-text product names to predefined categories using keyword matching.
"""

import re
from typing import Optional

# ---------------------------------------------------------------------------
# Category definitions
# ---------------------------------------------------------------------------
# Each category maps to a list of keyword patterns (case-insensitive).
# Order matters: first match wins, so more specific patterns go first.

CATEGORY_PATTERNS: dict[str, list[str]] = {
    "Deli / Prepared Meat": [
        r"boar.?s?\s*head",
        r"liverwurst",
        r"deli\s+(turkey|ham|roast\s*beef|salami|bologna|pastrami)",
        r"sliced\s+(turkey|ham|cheese)",
    ],
    # Frozen Foods MUST come before Dairy (to catch "ice cream" before "cream")
    "Frozen Foods": [
        r"ice\s*cream",
        r"birds?\s*eye.*peas|frozen\s*peas",
        r"\bfrozen\b",
        r"\bpopsicle\b",
        r"\bpizza\b",
    ],
    # Snacks MUST come before Produce (to catch "potato chip" before "potato")
    "Snacks": [
        r"lay.?s.*chip|potato\s*chip",
        r"\boreo\b|cookies?\b",
        r"\bchips?\b",
        r"\bcrackers?\b",
        r"\bpretzels?\b",
        r"\bpopcorn\b",
        r"\bnuts?\b(?!.*donut)",
        r"\bcandy\b",
        r"\bchocolate\b",
        r"\bgranola\b.*bar",
    ],
    "Meat & Poultry": [
        r"ground\s*beef",
        r"chuck\s*roast",
        r"sirloin\s*steak",
        r"chicken\s*(leg|breast|thigh|wing|drumstick)",
        r"boneless\s*chicken",
        r"butterball",
        r"frozen\s*turkey",
        r"\bturkey\b(?!.*deli)(?!.*sandwich)",
        r"\bham\b(?!.*burger)(?!.*sandwich)",
        r"\bsteak\b",
        r"\bbeef\b",
        r"\bpork\b",
        r"\bchicken\b",
        r"\bsausage\b",
        r"\bbacon\b",
        r"oscar\s*mayer",
        r"\bfranks?\b",
        r"\bhot\s*dog",
        r"\brib(?:s|eye)?\b",
        r"\blamb\b",
        r"\bveal\b",
        r"\bbrisket\b",
        r"roast\b",
        r"\bmeat\b",
        r"filet",
        r"tenderloin",
        r"ground\b.*\blean\b",
        # Meat bundles/packs (e.g., Harter House named bundles)
        r"1/2\s*a?\s*hog\b",
        r"\bassorted\s*quarters\b",
        r"\bpiggy\s*back\b",
        r"#\d+\s*(?:economy|variety|budget|mixed|family)\s*(?:pack|bundle)\b",
    ],
    "Seafood": [
        r"\bsalmon\b",
        r"\btuna\b",
        r"\bshrimp\b",
        r"\bcod\b",
        r"\blobster\b",
        r"\bcrab\b",
        r"\bfish\b",
        r"\bscallop",
        r"\bclam",
        r"\btilapia\b",
        r"\bswordfish\b",
        r"\bhalibut\b",
        r"\bscrod\b",
        r"\bflounder\b",
        r"\bseafood\b",
    ],
    "Produce": [
        r"\bapple",
        r"\blettuce\b",
        r"\bromaine\b",
        r"\borange",
        r"\bnavel\b",
        r"\btomato",
        r"\bpotato",
        r"\bidaho\b",
        r"\bbanana",
        r"\bgrape(?!.*jelly)",
        r"\bstrawberr",
        r"\bblueberr",
        r"\braspberr",
        r"\bpeach",
        r"\bpear\b",
        r"\blemon",
        r"\blime\b",
        r"\bavocado",
        r"\bonion",
        r"\bgarlic\b",
        r"\bpepper",
        r"\bbroccoli\b",
        r"\bcarrot",
        r"\bcelery\b",
        r"\bcucumber",
        r"\bmushroom",
        r"\bcorn\b(?!.*flake)(?!.*chip)",
        r"\bsquash\b",
        r"\bspinach\b",
        r"\bkale\b",
        r"\bcilantro\b",
        r"\bparsley\b",
        r"\bwatermelon\b",
        r"\bcantaloupe\b",
        r"\bnectarine",
        r"\bplum\b",
        r"\bcherry\b",
        r"\bfruit\b",
        r"\bvegetable",
        r"\bproduce\b",
        r"\bsalad\b",
    ],
    "Dairy & Eggs": [
        r"\bmilk\b",
        r"\beggs?\b",
        r"\bdozen\b.*\begg",
        r"cream\s*cheese",
        r"philadelphia",
        r"\bbutter\b",
        r"land\s*o.?\s*lakes",
        r"\bcheese\b",
        r"\byogurt\b",
        r"\bcream\b(?!.*ice\s*cream)",
        r"\bsour\s*cream\b",
        r"\bcottage\b",
        r"\bhalf\s*&?\s*half\b",
        r"\bwhipping\b",
        r"\bdairy\b",
    ],
    "Bread & Bakery": [
        r"english\s*muffin",
        r"thomas.?\s*(english|muffin)",
        r"sara\s*lee.*bread",
        r"wonder.*bread",
        r"ball\s*park.*bun",
        r"\bbread\b",
        r"\bbun[s]?\b",
        r"\bbagel",
        r"\bcroissant",
        r"\btortilla",
        r"\broll[s]?\b(?!.*toilet)(?!.*paper)",
        r"\bbakery\b",
        r"\bdonut\b",
        r"\bmuffin",
        r"\bcake\b",
        r"\bpie\b(?!.*pizza)",
    ],
    "Pantry & Canned": [
        r"skippy.*peanut|peanut\s*butter",
        r"welch.?s.*jelly|grape\s*jelly",
        r"folgers|coffee\b",
        r"lipton.*tea|\btea\b",
        r"cheerios",
        r"quaker.*oat|oatmeal",
        r"kellogg.?s|corn\s*flakes",
        r"\bcereal\b",
        r"domino.?s?\s*sugar|\bsugar\b",
        r"pillsbury.*flour|\bflour\b",
        r"uncle\s*ben.?s|rice\b",
        r"campbell.?s?\s*soup",
        r"progresso.*soup",
        r"\bsoup\b",
        r"cranberry\s*sauce|ocean\s*spray",
        r"green\s*giant",
        r"mott.?s|apple\s*sauce",
        r"kraft.*mac|mac.*cheese",
        r"ronzoni|pasta\b",
        r"bertoli|marinara|spaghetti\s*sauce",
        r"star\s*kist|tuna\b.*water",
        r"heinz.*ketchup|ketchup\b",
        r"hellman.?s|mayo\b",
        r"kraft.*dressing|salad\s*dressing",
        r"\bjelly\b",
        r"\bjam\b",
        r"\bhoney\b",
        r"\bsyrup\b",
        r"\bvinegar\b",
        r"\bmustard\b",
        r"\bolive\s*oil\b",
        r"\bcooking\s*oil\b",
        r"\bcanola\b",
        r"\bvegetable\s*oil\b",
        r"\bsalsa\b",
        r"\bsoy\s*sauce\b",
        r"\bspice",
        r"\bseasoning",
        r"\bcan(?:ned)?\b",
        r"\bbeans?\b",
    ],
    "Beverages": [
        r"tropicana|orange\s*juice|\boj\b",
        r"\bcoke\b|coca[\s-]?cola",
        r"\bpepsi\b",
        r"\bsoda\b",
        r"\bjuice\b",
        r"\bwater\b(?!.*dish)(?!.*laundry)",
        r"\bgatorade\b",
        r"\bsprite\b",
        r"\blemonade\b",
        r"\benergy\s*drink\b",
    ],
    "Household": [
        r"charmin|toilet\s*paper",
        r"bounty|paper\s*towel",
        r"tide.*detergent|laundry\s*detergent",
        r"palmolive|dish\s*soap",
        r"dial.*soap|bar\s*of\s*soap",
        r"cascade|dishwasher",
        r"crest|toothpaste",
        r"\bdetergent\b",
        r"\bbleach\b",
        r"\btrash\s*bag",
        r"\bpaper\s*plate",
        r"\bnapkin",
        r"\bfoil\b",
        r"\bplastic\s*wrap",
        r"\bsponge",
        r"\bcleaner\b",
        r"\bwipes?\b",
        r"\bshampoo\b",
        r"\bsoap\b",
        r"\bdeodorant\b",
        r"\brazor\b",
        r"\bbattery\b",
        r"\blight\s*bulb",
    ],
}

# Pre-compile all patterns for performance
_COMPILED_PATTERNS: list[tuple[str, re.Pattern]] = []
for category, patterns in CATEGORY_PATTERNS.items():
    for pattern in patterns:
        _COMPILED_PATTERNS.append((category, re.compile(pattern, re.IGNORECASE)))


def categorize_product(product_name: str) -> str:
    """
    Categorize a product name into one of the predefined categories.

    Returns the category string, or "Other" if no match is found.
    """
    if not product_name or not isinstance(product_name, str):
        return "Other"
    for category, compiled_re in _COMPILED_PATTERNS:
        if compiled_re.search(product_name):
            return category
    return "Other"


def categorize_series(product_names) -> list[str]:
    """
    Categorize a pandas Series or list of product names.

    Deduplicates first (categorises only unique names), then maps results
    back to every row.  This avoids redundant regex work when many rows
    share the same product name.
    """
    import pandas as pd

    if not isinstance(product_names, pd.Series):
        return [categorize_product(name) for name in product_names]

    # Only categorize each unique name once, then broadcast back
    unique_names = product_names.unique()  # ndarray of unique strings
    lookup: dict[str, str] = {}
    for name in unique_names:
        lookup[name] = categorize_product(name)

    return product_names.map(lookup).tolist()


# All category names in display order
ALL_CATEGORIES: list[str] = list(CATEGORY_PATTERNS.keys()) + ["Other"]
