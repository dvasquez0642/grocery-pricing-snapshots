"""
Target Items — the authoritative 60-item OFRA / Karen's Basket list.

This module is the SINGLE SOURCE OF TRUTH for the mission-critical Target
Items list.  It is imported by:

  - ``baskets.py`` (repo root)          — drives app-side basket matching
  - ``wayback grocery AO/helpers/confirm_stores.py`` — drives the
    store-confirmation gate against the mission stop condition

The list mirrors Appendix A ("Target Items") of every
``task_group_*/AGENTS.md``:

  Highest Priority (15 per-pound items)
  Also of Interest  (38 branded staples)
  Household         ( 7 items)

Public API
----------
TARGET_ITEMS : list[dict]
    The 60 item definitions, each ``{"label": str, "patterns": list[str]}``.
    Pattern strings are case-insensitive regexes matched via ``re.search``.

TARGET_ITEM_LABELS : list[str]
    Ordered list of the 60 canonical labels.

TARGET_ITEM_COUNT : int
    Convenience constant == 60.

compile_target_patterns() -> list[tuple[str, re.Pattern]]
    Returns ``[(label, compiled_regex), ...]``.  Each label has ONE
    combined regex (alternation of all its patterns) for speed.  The
    list preserves TARGET_ITEMS ordering.

match_target_item(product_name: str) -> str | None
    Returns the first Karen label whose regex matches ``product_name``
    (case-insensitive ``re.search``), or ``None`` if no match.  Match
    order follows TARGET_ITEMS.  Pattern compilation is cached.
"""

import re
from typing import Optional

# ---------------------------------------------------------------------------
# The 60 Target Items
# ---------------------------------------------------------------------------
# Structure:  list of {"label": str, "patterns": list[str]}
#
# Patterns are case-insensitive regexes matched via ``re.search`` against
# the raw product_name string.  A product matches an item if ANY of the
# item's patterns match.

TARGET_ITEMS: list[dict[str, object]] = [
    # --- Highest Priority: per-pound items (15) ---
    {"label": "Boar's Head Turkey", "patterns": [
        r"boar.?s?\s*head.*turkey",
    ]},
    {"label": "Boar's Head Ham", "patterns": [
        r"boar.?s?\s*head.*ham",
    ]},
    {"label": "Liverwurst", "patterns": [
        r"liverwurst", r"braunschweiger",
    ]},
    {"label": "American Cheese", "patterns": [
        r"american\s*cheese",
    ]},
    {"label": "Delicious Apples", "patterns": [
        r"delicious\s*apple", r"red\s*delicious", r"golden\s*delicious",
    ]},
    {"label": "Romaine Lettuce", "patterns": [
        r"romaine\s*lettuce", r"romaine\s*heart",
    ]},
    {"label": "Navel Orange", "patterns": [
        r"navel\s*orange",
    ]},
    {"label": "Tomato (hot house)", "patterns": [
        r"hot\s*house\s*tomato", r"hothouse\s*tomato",
        r"tomato.*hot\s*house", r"greenhouse\s*tomato",
        r"\btomato(?:es)?\b",
    ]},
    {"label": "Idaho Potatoes", "patterns": [
        r"idaho\s*potato", r"russet\s*potato",
    ]},
    {"label": "Ground Beef (lean)", "patterns": [
        r"ground\s*beef", r"lean\s*ground",
    ]},
    {"label": "Chicken Legs", "patterns": [
        r"chicken\s*leg",
    ]},
    {"label": "Boneless Chicken Breasts", "patterns": [
        r"boneless\s*chicken\s*breast", r"chicken\s*breast.*boneless",
        r"chicken\s*breast",
    ]},
    {"label": "Butterball Frozen Turkey", "patterns": [
        r"butterball.*turkey", r"frozen\s*turkey",
    ]},
    {"label": "Chuck Roast", "patterns": [
        # Hannaford and similar grocers label chuck roasts in many forms:
        # 'Chuck Roast', 'Boneless Beef Chuck Pot Roast',
        # 'Bone-In Chuck Blade Pot Roast', 'Chuck Shoulder Roast', etc.
        r"chuck.*roast",
        r"beef\s*chuck(?:\s|$)",
    ]},
    {"label": "Sirloin Steak", "patterns": [
        # Covers 'Sirloin Steak', 'Top Sirloin', 'Sirloin Tips', and
        # 'Sirloin Spoon Roast'/'Sirloin Tip Oven Roast' which are
        # unambiguously sirloin cuts.
        r"sirloin\s*steak",
        r"top\s*sirloin",
        r"sirloin\s*tip",
        r"sirloin\s*spoon\s*roast",
    ]},

    # --- Also of interest: branded staples (38) ---
    {"label": "Thomas' English Muffins", "patterns": [
        r"thomas.?\s*english\s*muffin", r"english\s*muffin",
    ]},
    {"label": "Sara Lee Bread", "patterns": [
        r"sara\s*lee.*bread", r"sara\s*lee.*wheat",
    ]},
    {"label": "Wonder Bread", "patterns": [
        r"wonder.*bread", r"wonder\s*white",
    ]},
    {"label": "Ball Park Buns", "patterns": [
        r"ball\s*park.*bun",
    ]},
    {"label": "Skippy Peanut Butter", "patterns": [
        r"skippy.*peanut\s*butter", r"peanut\s*butter",
    ]},
    {"label": "Welch's Grape Jelly", "patterns": [
        r"welch.?s.*jelly", r"grape\s*jelly",
    ]},
    {"label": "Folgers Coffee", "patterns": [
        r"folgers.*coffee", r"folgers",
    ]},
    {"label": "Lipton Tea", "patterns": [
        r"lipton.*tea", r"lipton",
    ]},
    {"label": "Cheerios", "patterns": [
        r"\bcheerios\b",
    ]},
    {"label": "Quaker Oats Oatmeal", "patterns": [
        r"quaker.*oat", r"quaker.*oatmeal", r"\boatmeal\b",
    ]},
    {"label": "Kellogg's Corn Flakes", "patterns": [
        r"kellogg.?s.*corn\s*flake", r"corn\s*flakes",
    ]},
    {"label": "Domino's Sugar", "patterns": [
        r"domino.?s?\s*sugar", r"\bdomino\b.*sugar",
    ]},
    {"label": "Pillsbury Flour", "patterns": [
        r"pillsbury.*flour", r"\bflour\b",
    ]},
    {"label": "Uncle Ben's Rice", "patterns": [
        r"uncle\s*ben.?s.*rice", r"ben.?s\s*original.*rice",
    ]},
    {"label": "Campbell's Soup", "patterns": [
        r"campbell.?s.*soup",
    ]},
    {"label": "Progresso Soup", "patterns": [
        r"progresso.*soup", r"progresso\b",
    ]},
    {"label": "Ocean Spray Cranberry Sauce", "patterns": [
        r"ocean\s*spray.*cranberry", r"cranberry\s*sauce",
    ]},
    {"label": "Green Giant Corn", "patterns": [
        r"green\s*giant.*corn", r"green\s*giant",
    ]},
    {"label": "Mott's Apple Sauce", "patterns": [
        r"mott.?s.*apple\s*sauce", r"mott.?s.*applesauce",
        r"\bapplesauce\b", r"\bapple\s*sauce\b",
    ]},
    {"label": "Kraft Mac and Cheese", "patterns": [
        r"kraft.*mac", r"mac.*cheese",
    ]},
    {"label": "Ronzoni Pasta", "patterns": [
        r"ronzoni.*pasta", r"ronzoni\b", r"\bpasta\b",
    ]},
    {"label": "Bertoli Marinara Sauce", "patterns": [
        r"bertol(?:i|li).*marinara", r"marinara\s*sauce",
        r"spaghetti\s*sauce",
    ]},
    {"label": "StarKist Tuna", "patterns": [
        r"star\s*kist.*tuna", r"starkist", r"\btuna\b.*water",
    ]},
    {"label": "Oscar Mayer Bacon", "patterns": [
        r"oscar\s*mayer.*bacon", r"oscar\s*mayer\b",
    ]},
    {"label": "Oscar Mayer Franks", "patterns": [
        r"oscar\s*mayer.*frank", r"oscar\s*mayer.*hot\s*dog",
        r"\bfranks?\b",
    ]},
    {"label": "Heinz Ketchup", "patterns": [
        r"heinz.*ketchup", r"\bketchup\b",
    ]},
    {"label": "Hellman's Mayo", "patterns": [
        r"hellman.?s.*mayo", r"\bmayo(?:nnaise)?\b",
    ]},
    {"label": "Kraft Salad Dressing", "patterns": [
        r"kraft.*dressing", r"salad\s*dressing",
    ]},
    {"label": "Milk (gallon)", "patterns": [
        r"\bmilk\b.*gallon", r"gallon.*\bmilk\b", r"\bwhole\s*milk\b",
        r"\b2%?\s*milk\b", r"\bmilk\b",
    ]},
    {"label": "Eggs (dozen)", "patterns": [
        r"\beggs?\b.*dozen", r"dozen.*\beggs?\b",
        r"large\s*eggs?", r"\beggs?\b",
    ]},
    {"label": "Tropicana OJ", "patterns": [
        r"tropicana.*(?:oj|orange\s*juice)", r"tropicana\b",
        r"orange\s*juice",
    ]},
    {"label": "Philadelphia Cream Cheese", "patterns": [
        r"philadelphia.*cream\s*cheese", r"philly.*cream\s*cheese",
        r"cream\s*cheese",
    ]},
    {"label": "Land O'Lakes Butter", "patterns": [
        r"land\s*o.?\s*lakes.*butter", r"\bbutter\b",
    ]},
    {"label": "Lay's Potato Chips", "patterns": [
        r"lay.?s.*(?:potato\s*)?chip", r"potato\s*chips?",
    ]},
    {"label": "Oreo Cookies", "patterns": [
        r"\boreo\b", r"oreo.*cookie",
    ]},
    {"label": "Ice Cream", "patterns": [
        r"ice\s*cream",
    ]},
    {"label": "Birds Eye Frozen Peas", "patterns": [
        r"birds?\s*eye.*peas", r"frozen\s*peas",
    ]},
    {"label": "Coke (6-pack)", "patterns": [
        r"coca[\s-]?cola", r"\bcoke\b", r"6\s*pack.*coke",
    ]},

    # --- Household (7) ---
    {"label": "Charmin Toilet Paper", "patterns": [
        r"charmin.*toilet", r"charmin\b", r"toilet\s*paper",
    ]},
    {"label": "Bounty Paper Towels", "patterns": [
        r"bounty.*paper\s*towel", r"bounty\b", r"paper\s*towel",
    ]},
    {"label": "Tide Laundry Detergent", "patterns": [
        r"tide.*detergent", r"tide\s*(?:pod|liquid|powder)?",
        r"laundry\s*detergent",
    ]},
    {"label": "Palmolive Dish Soap", "patterns": [
        r"palmolive.*dish", r"palmolive\b", r"dish\s*soap",
    ]},
    {"label": "Dial Bar Soap", "patterns": [
        r"dial.*(?:bar\s*)?soap", r"bar\s*(?:of\s*)?soap",
    ]},
    {"label": "Cascade Dishwasher Soap", "patterns": [
        r"cascade.*dish", r"cascade\b", r"dishwasher\s*(?:soap|detergent|pod)",
    ]},
    {"label": "Crest Toothpaste", "patterns": [
        r"crest.*toothpaste", r"crest\b", r"toothpaste\b",
    ]},
]

# ---------------------------------------------------------------------------
# Derived constants
# ---------------------------------------------------------------------------

TARGET_ITEM_LABELS: list[str] = [item["label"] for item in TARGET_ITEMS]
TARGET_ITEM_COUNT: int = len(TARGET_ITEMS)

# Sanity check: the Target Items list is defined as exactly 60 items in
# every task_group_*/AGENTS.md Appendix A.  If this ever trips, the
# appendix or this module is out of sync.
assert TARGET_ITEM_COUNT == 60, (
    "TARGET_ITEMS must contain exactly 60 entries; got %d" % TARGET_ITEM_COUNT
)


# ---------------------------------------------------------------------------
# Matching engine
# ---------------------------------------------------------------------------

_compiled_cache: Optional[list[tuple[str, "re.Pattern[str]"]]] = None


def compile_target_patterns() -> list[tuple[str, "re.Pattern[str]"]]:
    """Return ``[(label, compiled_regex), ...]`` in TARGET_ITEMS order.

    Each item's multiple patterns are joined into a single alternation
    regex so matching is a single ``re.search`` call per product name.
    Result is cached at module scope.
    """
    global _compiled_cache
    if _compiled_cache is not None:
        return _compiled_cache

    compiled: list[tuple[str, "re.Pattern[str]"]] = []
    for item in TARGET_ITEMS:
        label = item["label"]
        patterns = item["patterns"]
        # Wrap each pattern in a non-capturing group and OR them together.
        combined = "|".join("(?:%s)" % p for p in patterns)
        compiled.append((label, re.compile(combined, re.IGNORECASE)))
    _compiled_cache = compiled
    return compiled


def match_target_item(product_name: str) -> Optional[str]:
    """Return the first Target Item label that matches ``product_name``.

    Match semantics: case-insensitive ``re.search`` against the raw
    product name.  The first matching label in TARGET_ITEMS order is
    returned.  Returns ``None`` if no item matches or if
    ``product_name`` is falsy.
    """
    if not product_name:
        return None
    for label, regex in compile_target_patterns():
        if regex.search(product_name):
            return label
    return None
