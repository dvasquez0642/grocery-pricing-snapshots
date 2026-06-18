"""
Curated basket definitions and product-name matching.

Each basket maps a human-readable basket name to a list of basket items.
Each basket item has a label (e.g. "Oatmeal") and a set of regex patterns
used to match raw scraped ``product_name`` values from the pricing dataset.

Baskets are organized into groups:
  - **Reference**: Karen's Basket (the 60-item OFRA / Target Items master list)
  - **Breakfast / Lunch / Dinner / Snack**: NHANES 2021-2023 meal archetypes
    derived from the WWEIA dietary recall analysis.  See
    ``analysis/nhanes/nhanes_meal_archetypes.html`` for methodology.
  - **Specialty**: Child Specific, Exercise Snacks (legacy occasion baskets)

Public API
----------
CURATED_BASKETS : dict
    Basket definitions keyed by basket name.

BASKET_GROUPS : OrderedDict
    Maps display group -> list of basket names in display order.

BASKET_GROUP_FOR : dict
    Reverse lookup: basket name -> group name.

ALL_BASKET_NAMES : list
    Flat list of all basket names in display order.

basket_display_name(name, count=None)
    Returns a human-friendly display label with group prefix and product count.

build_basket_product_sets(product_names)
    Given an iterable of unique product names, returns:
    - basket_to_products: dict mapping basket name -> set of matched names
    - product_to_baskets: dict mapping product name -> set of basket names
"""

import re
from collections import OrderedDict
from typing import Iterable

from target_items import TARGET_ITEMS

# ---------------------------------------------------------------------------
# Basket definitions
# ---------------------------------------------------------------------------
# Structure:
#   basket_name -> list of { "label": str, "patterns": list[str] }
#
# Patterns are case-insensitive regexes matched via re.search against the
# raw product_name string.  A product matches a basket item if ANY of the
# item's patterns match.  A product belongs to a basket if it matches ANY
# item in that basket.

CURATED_BASKETS: dict[str, list[dict[str, object]]] = {
    # ==================================================================
    # REFERENCE BASKET
    # ==================================================================

    # ------------------------------------------------------------------
    # Karen's Basket  (the 60-item OFRA / Target Items master list)
    # ------------------------------------------------------------------
    # The 60-item list itself lives in ``target_items.py`` at the repo
    # root so that both this module and the wayback AO's
    # ``helpers/confirm_stores.py`` share one source of truth.
    "Karen's Basket": TARGET_ITEMS,

    # ==================================================================
    # NHANES BREAKFAST ARCHETYPES
    # ==================================================================

    # --- cereal or oatmeal breakfast (21.6% of breakfasts) ---
    # Key NiQ: CEREAL & GRANOLA + MILK PRODUCTS
    "cereal or oatmeal breakfast": [
        {"label": "Cold cereal", "patterns": [
            r"\bcheerios\b", r"frosted\s*flakes", r"cinnamon\s*toast",
            r"corn\s*flakes", r"\bcereal\b", r"raisin\s*bran",
            r"lucky\s*charms", r"honey\s*nut",
        ]},
        {"label": "Oatmeal", "patterns": [
            r"quaker.*oat", r"\boatmeal\b", r"bob.?s\s*red\s*mill.*oat",
            r"instant\s*oat",
        ]},
        {"label": "Milk", "patterns": [r"\bmilk\b"]},
        {"label": "Granola", "patterns": [
            r"\bgranola\b",
        ]},
    ],

    # --- coffee-first breakfast (15.8%) ---
    # Key NiQ: COFFEE
    "coffee-first breakfast": [
        {"label": "Coffee", "patterns": [
            r"\bcoffee\b", r"folgers", r"maxwell\s*house",
            r"starbucks", r"\bk[\s-]?cup",
        ]},
        {"label": "Creamer", "patterns": [
            r"\bcreamer\b", r"coffee[\s-]?mate", r"half\s*(?:and|&)\s*half",
        ]},
    ],

    # --- coffee and pastry breakfast (9.8%) ---
    # Key NiQ: COFFEE + BREAD + COOKIES & CRACKERS
    "coffee and pastry breakfast": [
        {"label": "Coffee", "patterns": [
            r"\bcoffee\b", r"folgers", r"maxwell\s*house",
            r"starbucks", r"\bk[\s-]?cup",
        ]},
        {"label": "Pastry or muffin", "patterns": [
            r"\bmuffin", r"\bcroissant", r"\bdanish\b",
            r"\bdough?nut", r"pastry", r"toaster\s*strudel",
            r"pop[\s-]?tart", r"sweet\s*roll",
        ]},
        {"label": "Bread", "patterns": [
            r"\bbagel", r"english\s*muffin",
            r"biscuit",
        ]},
    ],

    # --- breakfast sandwich or burrito (9.6%) ---
    # Key NiQ: EGGS + BREAD + WRAPS & TORTILLA SHELLS
    "breakfast sandwich or burrito": [
        {"label": "Eggs", "patterns": [r"\beggs?\b"]},
        {"label": "English muffins", "patterns": [
            r"thomas.?\s*english\s*muffin", r"english\s*muffin",
        ]},
        {"label": "Tortillas or wraps", "patterns": [
            r"\btortilla", r"\bwraps?\b", r"flour\s*tortilla",
        ]},
        {"label": "Breakfast sausage", "patterns": [
            r"breakfast\s*sausage", r"jimmy\s*dean",
            r"\bsausage\s*patt", r"sausage\s*link",
        ]},
        {"label": "Breakfast sandwich (frozen)", "patterns": [
            r"breakfast\s*sandwich", r"hot\s*pocket.*breakfast",
        ]},
    ],

    # --- eggs with bread or meat (9.5%) ---
    # Key NiQ: EGGS + BREAD + breakfast meat
    "eggs with bread or meat": [
        {"label": "Eggs", "patterns": [r"\beggs?\b"]},
        {"label": "Bread", "patterns": [
            r"wonder.*bread", r"sara\s*lee.*bread", r"nature.?s\s*own.*bread",
            r"pepperidge.*bread", r"dave.?s.*killer.*bread",
            r"sandwich\s*bread", r"white\s*bread", r"wheat\s*bread",
        ]},
        {"label": "Bacon", "patterns": [
            r"\bbacon\b", r"oscar\s*mayer.*bacon",
        ]},
        {"label": "Sausage", "patterns": [
            r"\bsausage\b",
        ]},
        {"label": "Butter", "patterns": [
            r"(?<!peanut\s)\bbutter\b",
        ]},
    ],

    # --- fruit and bread breakfast (2.0%) ---
    # Key NiQ: FRUIT + BREAD + NUT BUTTERS/JAM/JELLIES
    "fruit and bread breakfast": [
        {"label": "Bananas", "patterns": [r"\bbanana"]},
        {"label": "Berries", "patterns": [
            r"\bstrawberr", r"\bblueberr", r"\braspberr",
            r"\bberries\b",
        ]},
        {"label": "Toast bread", "patterns": [
            r"\bbread\b", r"\bbagel", r"\btoast\b",
        ]},
        {"label": "Peanut butter", "patterns": [
            r"peanut\s*butter", r"\bskippy\b", r"\bjif\b",
        ]},
        {"label": "Jelly or jam", "patterns": [
            r"\bjelly\b", r"\bjam\b", r"\bpreserves\b",
            r"smucker", r"welch",
        ]},
    ],

    # --- yogurt and fruit breakfast (1.1%) ---
    # Key NiQ: FRUIT + (yogurt not in our 20 supercats, but included here)
    "yogurt and fruit breakfast": [
        {"label": "Yogurt", "patterns": [
            r"\byogurt\b", r"chobani", r"fage\b", r"dannon",
            r"oikos",
        ]},
        {"label": "Berries", "patterns": [
            r"\bstrawberr", r"\bblueberr", r"\braspberr",
            r"\bberries\b",
        ]},
        {"label": "Bananas", "patterns": [r"\bbanana"]},
        {"label": "Granola", "patterns": [r"\bgranola\b"]},
    ],

    # ==================================================================
    # NHANES LUNCH ARCHETYPES
    # ==================================================================

    # --- sandwich lunch (28.3% of lunches) ---
    # Key NiQ: BREAD + CONDIMENTS + CHEESE + NUT BUTTERS
    "sandwich lunch": [
        {"label": "Sandwich bread", "patterns": [
            r"wonder.*bread", r"sara\s*lee.*bread", r"nature.?s\s*own.*bread",
            r"pepperidge.*bread", r"dave.?s.*killer.*bread",
            r"sandwich\s*bread", r"white\s*bread", r"wheat\s*bread",
            r"\bbread\b",
        ]},
        {"label": "Deli meat", "patterns": [
            r"boar.?s?\s*head", r"\bdeli\b.*(?:meat|turkey|ham)",
            r"turkey\s*breast", r"\bsliced\s*(?:turkey|ham|roast)",
            r"lunch\s*meat",
        ]},
        {"label": "Sliced cheese", "patterns": [
            r"american\s*cheese", r"sliced\s*cheese",
            r"swiss\s*cheese", r"cheddar\s*cheese",
        ]},
        {"label": "Mayo or mustard", "patterns": [
            r"\bmayo(?:nnaise)?\b", r"hellman", r"\bmustard\b",
        ]},
        {"label": "Peanut butter", "patterns": [
            r"peanut\s*butter", r"\bskippy\b", r"\bjif\b",
        ]},
    ],

    # --- plate lunch (10.9%) ---
    # Key NiQ: PASTA/RICE/GRAINS + VEGETABLES + (meat gap)
    "plate lunch": [
        {"label": "Chicken", "patterns": [
            r"chicken\s*breast", r"chicken\s*thigh",
            r"chicken\s*tender", r"chicken\s*nugget",
            r"chicken\s*patt", r"rotisserie\s*chicken",
        ]},
        {"label": "Rice", "patterns": [
            r"\brice\b",
        ]},
        {"label": "Potatoes", "patterns": [
            r"\bpotato(?!.*chip)", r"french\s*fries?", r"tater\s*tot",
        ]},
        {"label": "Vegetables", "patterns": [
            r"\bcorn\b", r"\bpeas\b", r"\bcarrot",
            r"green\s*bean", r"mixed\s*vegetable",
        ]},
        {"label": "Ketchup or sauce", "patterns": [
            r"\bketchup\b", r"tomato\s*sauce",
        ]},
    ],

    # --- mixed entree lunch (10.5%) ---
    # Key NiQ: MEAL COMBOS + PREPARED FOODS + PASTA/RICE
    "mixed entree lunch": [
        {"label": "Frozen meals", "patterns": [
            r"lean\s*cuisine", r"healthy\s*choice",
            r"stouffer", r"banquet\b", r"frozen\s*(?:dinner|meal|entree)",
            r"amy.?s\b.*(?:meal|bowl|entree)",
        ]},
        {"label": "Mac and cheese", "patterns": [
            r"kraft.*mac", r"mac.*cheese", r"velveeta",
        ]},
        {"label": "Pasta", "patterns": [
            r"\bpasta\b", r"ronzoni", r"barilla",
        ]},
        {"label": "Canned entrees", "patterns": [
            r"chef\s*boyardee", r"\bravioli\b", r"spaghetti.*os?\b",
        ]},
    ],

    # --- salad lunch (7.1%) ---
    # Key NiQ: VEGETABLES + CHEESE + CONDIMENTS
    "salad lunch": [
        {"label": "Salad greens", "patterns": [
            r"romaine", r"\blettuce\b", r"baby\s*spinach",
            r"spring\s*mix", r"salad\s*mix", r"salad\s*kit",
            r"salad\s*blend",
        ]},
        {"label": "Salad vegetables", "patterns": [
            r"\btomato", r"\bcucumber", r"\bcrouton",
            r"\bcarrot", r"\bcelery",
        ]},
        {"label": "Cheese", "patterns": [
            r"shredded\s*cheese", r"crumbled.*cheese",
            r"\bfeta\b", r"parmesan",
        ]},
        {"label": "Salad dressing", "patterns": [
            r"salad\s*dressing", r"\branch\b.*dressing",
            r"vinaigrette", r"hidden\s*valley",
            r"caesar\s*dressing",
        ]},
    ],

    # --- tortilla lunch (5.1%) ---
    # Key NiQ: WRAPS & TORTILLA SHELLS
    "tortilla lunch": [
        {"label": "Tortillas or taco shells", "patterns": [
            r"\btortilla", r"taco\s*shell", r"mission\s*(?:tortilla|wrap)",
            r"old\s*el\s*paso", r"\bwraps?\b",
        ]},
        {"label": "Salsa", "patterns": [
            r"\bsalsa\b", r"tostitos.*salsa", r"pace\s*(?:salsa|picante)",
        ]},
        {"label": "Taco seasoning", "patterns": [
            r"taco\s*(?:seasoning|mix)", r"enchilada\s*sauce",
            r"fajita\s*seasoning",
        ]},
        {"label": "Refried beans", "patterns": [
            r"refried\s*beans?", r"black\s*beans?",
        ]},
        {"label": "Sour cream", "patterns": [
            r"sour\s*cream",
        ]},
    ],

    # --- pizza lunch (5.0%) ---
    # Key NiQ: PIZZA
    "pizza lunch": [
        {"label": "Frozen pizza", "patterns": [
            r"\bpizza\b", r"digiorno", r"tombstone",
            r"totino", r"red\s*baron", r"freschetta",
            r"jack.?s\s*pizza",
        ]},
        {"label": "Pizza sauce", "patterns": [
            r"pizza\s*sauce",
        ]},
        {"label": "Mozzarella", "patterns": [
            r"mozzarella",
        ]},
    ],

    # --- soup lunch (4.6%) ---
    # Key NiQ: PREPARED FOODS (soup)
    "soup lunch": [
        {"label": "Canned soup", "patterns": [
            r"campbell.?s.*soup", r"progresso.*soup",
            r"\bsoup\b", r"\bramen\b",
        ]},
        {"label": "Broth or stock", "patterns": [
            r"\bbroth\b", r"\bstock\b", r"swanson.*broth",
        ]},
        {"label": "Crackers", "patterns": [
            r"\bcrackers?\b", r"saltine",
        ]},
    ],

    # ==================================================================
    # NHANES DINNER ARCHETYPES
    # ==================================================================

    # --- mixed entree dinner (16.4% of dinners) ---
    # Key NiQ: MEAL COMBOS + PREPARED FOODS
    "mixed entree dinner": [
        {"label": "Frozen dinners", "patterns": [
            r"stouffer", r"lean\s*cuisine", r"healthy\s*choice",
            r"banquet\b", r"marie\s*callender",
            r"frozen\s*(?:dinner|meal|entree)",
        ]},
        {"label": "Skillet meals", "patterns": [
            r"skillet\s*meal", r"hamburger\s*helper",
            r"helper\b.*(?:dinner|meal)",
        ]},
        {"label": "Mac and cheese", "patterns": [
            r"kraft.*mac", r"mac.*cheese", r"velveeta",
        ]},
        {"label": "Pasta with sauce", "patterns": [
            r"\bpasta\b", r"marinara", r"spaghetti\s*sauce",
            r"\bprego\b", r"rao.?s",
        ]},
    ],

    # --- sandwich dinner (15.0%) ---
    # Key NiQ: BREAD + CONDIMENTS + (meat gap)
    "sandwich dinner": [
        {"label": "Buns", "patterns": [
            r"hot\s*dog\s*bun", r"hamburger\s*bun",
            r"\bbuns?\b", r"ball\s*park.*bun",
        ]},
        {"label": "Hot dogs or franks", "patterns": [
            r"\bhot\s*dog", r"\bfranks?\b",
            r"oscar\s*mayer.*frank",
        ]},
        {"label": "Bread", "patterns": [
            r"\bbread\b",
        ]},
        {"label": "Deli meat", "patterns": [
            r"boar.?s?\s*head", r"\bdeli\b",
            r"lunch\s*meat", r"sliced\s*(?:turkey|ham)",
        ]},
        {"label": "Condiments", "patterns": [
            r"\bketchup\b", r"\bmustard\b", r"\bmayo(?:nnaise)?\b",
        ]},
    ],

    # --- protein vegetable starch dinner (9.4%) ---
    # Key NiQ: VEGETABLES + PASTA/RICE + SEAFOOD + (meat gap)
    "protein vegetable starch dinner": [
        {"label": "Chicken or meat", "patterns": [
            r"chicken\s*breast", r"chicken\b",
            r"ground\s*beef", r"\bsteak\b",
            r"\bpork\b",
        ]},
        {"label": "Seafood", "patterns": [
            r"\bsalmon\b", r"\bshrimp\b", r"\btilapia\b",
            r"fish\s*fillet", r"gorton",
        ]},
        {"label": "Vegetables", "patterns": [
            r"\bbroccoli\b", r"green\s*bean", r"\bpeas\b",
            r"\bcarrot", r"\bcorn\b", r"\bspinach\b",
            r"mixed\s*vegetable",
        ]},
        {"label": "Potatoes", "patterns": [
            r"\bpotato(?!.*chip)", r"mashed\s*potato",
        ]},
        {"label": "Rice or pasta", "patterns": [
            r"\brice\b", r"\bpasta\b", r"\bnoodle",
        ]},
    ],

    # --- protein and starch dinner (8.6%) ---
    # Key NiQ: PASTA/RICE + (meat is defining ingredient)
    "protein and starch dinner": [
        {"label": "Chicken", "patterns": [
            r"chicken\s*breast", r"chicken\s*thigh",
            r"chicken\s*tender", r"chicken\b",
        ]},
        {"label": "Ground beef", "patterns": [
            r"ground\s*beef", r"lean\s*ground",
        ]},
        {"label": "Pork", "patterns": [
            r"\bpork\s*(?:chop|loin|tenderloin)",
            r"\bpork\b",
        ]},
        {"label": "Rice", "patterns": [
            r"\brice\b", r"rice.?a.?roni",
        ]},
        {"label": "Pasta", "patterns": [
            r"\bpasta\b", r"\bnoodle", r"ronzoni", r"barilla",
        ]},
    ],

    # --- tortilla dinner (7.7%) ---
    # Key NiQ: WRAPS & TORTILLA SHELLS (SES-sensitive)
    "tortilla dinner": [
        {"label": "Tortillas or taco shells", "patterns": [
            r"\btortilla", r"taco\s*shell", r"mission\s*(?:tortilla|wrap)",
            r"old\s*el\s*paso", r"\bwraps?\b",
        ]},
        {"label": "Salsa", "patterns": [
            r"\bsalsa\b", r"tostitos.*salsa", r"pace\s*(?:salsa|picante)",
        ]},
        {"label": "Beans", "patterns": [
            r"refried\s*beans?", r"black\s*beans?",
            r"\bbeans?\b",
        ]},
        {"label": "Taco or enchilada seasoning", "patterns": [
            r"taco\s*(?:seasoning|mix)", r"enchilada\s*sauce",
            r"fajita\s*seasoning",
        ]},
        {"label": "Sour cream", "patterns": [
            r"sour\s*cream",
        ]},
    ],

    # --- pizza dinner (6.5%) ---
    # Key NiQ: PIZZA
    "pizza dinner": [
        {"label": "Frozen pizza", "patterns": [
            r"\bpizza\b", r"digiorno", r"tombstone",
            r"totino", r"red\s*baron", r"freschetta",
            r"jack.?s\s*pizza",
        ]},
        {"label": "Pizza sauce", "patterns": [
            r"pizza\s*sauce",
        ]},
        {"label": "Mozzarella", "patterns": [
            r"mozzarella",
        ]},
    ],

    # --- soup dinner (5.9%) ---
    # Key NiQ: PREPARED FOODS (soup)
    "soup dinner": [
        {"label": "Canned soup", "patterns": [
            r"campbell.?s.*soup", r"progresso.*soup",
            r"\bsoup\b", r"\bramen\b",
        ]},
        {"label": "Broth or stock", "patterns": [
            r"\bbroth\b", r"\bstock\b", r"swanson.*broth",
        ]},
        {"label": "Bread or crackers", "patterns": [
            r"\bcrackers?\b", r"saltine",
            r"dinner\s*roll", r"french\s*bread",
        ]},
    ],

    # ==================================================================
    # NHANES SNACK ARCHETYPES
    # ==================================================================

    # --- sweet snack (35.8% of snacks) ---
    # Key NiQ: COOKIES & CRACKERS + DESSERTS/SWEET GOODS
    "sweet snack": [
        {"label": "Cookies", "patterns": [
            r"\bcookies?\b", r"\boreo\b", r"chips\s*ahoy",
        ]},
        {"label": "Candy or chocolate", "patterns": [
            r"\bcandy\b", r"\bchocolate\b", r"hershey",
            r"reese.?s\b", r"m\s*&\s*m", r"snickers",
            r"kit\s*kat",
        ]},
        {"label": "Ice cream", "patterns": [
            r"ice\s*cream",
        ]},
        {"label": "Cake or brownies", "patterns": [
            r"\bcake\b", r"\bbrownie", r"\bpie\b",
            r"little\s*debbie", r"hostess",
        ]},
    ],

    # --- salty snack (22.0%) ---
    # Key NiQ: SALTY SNACKS
    "salty snack": [
        {"label": "Potato chips", "patterns": [
            r"potato\s*chip", r"lay.?s.*chip",
            r"\bpringles\b", r"kettle.*chip",
        ]},
        {"label": "Tortilla chips", "patterns": [
            r"tortilla\s*chip", r"\bdoritos\b", r"tostitos",
        ]},
        {"label": "Crackers", "patterns": [
            r"\bcrackers?\b", r"goldfish", r"\britz\b",
            r"cheez[\s-]?it",
        ]},
        {"label": "Pretzels", "patterns": [
            r"\bpretzel", r"snyder",
        ]},
        {"label": "Popcorn", "patterns": [
            r"\bpopcorn\b", r"smartfood", r"skinny\s*pop",
        ]},
    ],

    # --- coffee or tea snack (3.0%) ---
    # Key NiQ: COFFEE
    "coffee or tea snack": [
        {"label": "Coffee", "patterns": [
            r"\bcoffee\b", r"folgers", r"maxwell\s*house",
            r"starbucks", r"\bk[\s-]?cup",
        ]},
        {"label": "Tea", "patterns": [
            r"\btea\b", r"lipton", r"celestial\s*seasoning",
            r"bigelow\b",
        ]},
    ],

    # --- sandwich snack (1.4%) ---
    # Key NiQ: BREAD + NUT BUTTERS + CONDIMENTS
    "sandwich snack": [
        {"label": "Bread", "patterns": [
            r"\bbread\b",
        ]},
        {"label": "Peanut butter", "patterns": [
            r"peanut\s*butter", r"\bskippy\b", r"\bjif\b",
        ]},
        {"label": "Jelly", "patterns": [
            r"\bjelly\b", r"\bjam\b", r"smucker",
        ]},
        {"label": "Cheese", "patterns": [
            r"\bcheese\b",
        ]},
    ],

    # --- fruit and dairy snack (0.9%) ---
    # Key NiQ: FRUIT + CHEESE (yogurt gap)
    "fruit and dairy snack": [
        {"label": "Apples", "patterns": [r"\bapple(?:s)?\b"]},
        {"label": "Bananas", "patterns": [r"\bbanana"]},
        {"label": "Berries", "patterns": [
            r"\bstrawberr", r"\bblueberr", r"\bgrapes?\b",
        ]},
        {"label": "String cheese", "patterns": [
            r"string\s*cheese", r"babybel",
        ]},
        {"label": "Yogurt", "patterns": [
            r"\byogurt\b", r"chobani", r"dannon",
        ]},
    ],

    # ==================================================================
    # SPECIALTY / LEGACY BASKETS
    # ==================================================================

    # ------------------------------------------------------------------
    # Child Specific  (from Baskets.md)
    # ------------------------------------------------------------------
    "Child Specific": [
        {"label": "Dino nuggets", "patterns": [
            r"dino\s*nugget", r"dino\s*budd", r"dinosaur\s*nugget",
            r"chicken\s*nugget",
        ]},
        {"label": "Mac and cheese cups", "patterns": [
            r"easy\s*mac", r"mac.*cheese.*cup", r"mac.*cheese",
        ]},
        {"label": "Applesauce cups", "patterns": [
            r"applesauce\s*cup", r"apple\s*sauce\s*cup",
            r"gogo\s*squeez", r"\bapplesauce\b",
        ]},
        {"label": "Crackers", "patterns": [
            r"\bcrackers?\b", r"goldfish",
        ]},
        {"label": "Milk", "patterns": [r"\bmilk\b"]},
        {"label": "Juice boxes", "patterns": [
            r"juice\s*box", r"capri\s*sun", r"juicy\s*juice",
            r"juice\b",
        ]},
        {"label": "Frozen peas", "patterns": [
            r"frozen\s*peas", r"birds?\s*eye.*peas",
        ]},
    ],

    # ------------------------------------------------------------------
    # Exercise Snacks  (from Baskets.md)
    # ------------------------------------------------------------------
    "Exercise Snacks": [
        {"label": "Granola bars", "patterns": [
            r"granola\s*bar", r"nature\s*valley", r"\bkind\s*bar",
            r"clif\s*bar",
        ]},
        {"label": "Peanut butter", "patterns": [
            r"peanut\s*butter",
        ]},
        {"label": "Crackers", "patterns": [
            r"\bcrackers?\b",
        ]},
        {"label": "String cheese", "patterns": [
            r"string\s*cheese",
        ]},
        {"label": "Bananas", "patterns": [r"\bbanana"]},
        {"label": "Chocolate milk", "patterns": [
            r"chocolate\s*milk",
        ]},
        {"label": "Sports drink", "patterns": [
            r"gatorade", r"powerade", r"bodyarmor", r"sports?\s*drink",
        ]},
    ],
}


# ---------------------------------------------------------------------------
# Display metadata
# ---------------------------------------------------------------------------

BASKET_GROUPS: OrderedDict[str, list[str]] = OrderedDict([
    ("Reference", [
        "Karen's Basket",
    ]),
    ("Breakfast", [
        "cereal or oatmeal breakfast",
        "coffee-first breakfast",
        "coffee and pastry breakfast",
        "breakfast sandwich or burrito",
        "eggs with bread or meat",
        "fruit and bread breakfast",
        "yogurt and fruit breakfast",
    ]),
    ("Lunch", [
        "sandwich lunch",
        "plate lunch",
        "mixed entree lunch",
        "salad lunch",
        "tortilla lunch",
        "pizza lunch",
        "soup lunch",
    ]),
    ("Dinner", [
        "mixed entree dinner",
        "sandwich dinner",
        "protein vegetable starch dinner",
        "protein and starch dinner",
        "tortilla dinner",
        "pizza dinner",
        "soup dinner",
    ]),
    ("Snack", [
        "sweet snack",
        "salty snack",
        "coffee or tea snack",
        "sandwich snack",
        "fruit and dairy snack",
    ]),
    ("Specialty", [
        "Child Specific",
        "Exercise Snacks",
    ]),
])

# Reverse lookup: basket name -> group name
BASKET_GROUP_FOR: dict[str, str] = {
    name: group
    for group, names in BASKET_GROUPS.items()
    for name in names
}

# All basket names in display order (derived from groups)
ALL_BASKET_NAMES: list[str] = [
    name for names in BASKET_GROUPS.values() for name in names
]

# Occasion suffixes stripped from archetype names in the display label
_OCCASION_SUFFIXES = (" breakfast", " lunch", " dinner", " snack")


def basket_display_name(name: str, count: int | None = None) -> str:
    """Return a human-friendly display label for a basket.

    Archetype baskets are prefixed with their meal group and the
    redundant occasion suffix is stripped, e.g.:

        ``"cereal or oatmeal breakfast"`` -> ``"Breakfast \u2014 cereal or oatmeal (23)"``
        ``"Karen's Basket"``              -> ``"Karen's Basket (45)"``
    """
    group = BASKET_GROUP_FOR.get(name, "")
    suffix = f" ({count})" if count is not None else ""

    if group in ("Reference", "Specialty"):
        return f"{name}{suffix}"

    # Strip trailing occasion word for cleaner display
    short = name
    for occ in _OCCASION_SUFFIXES:
        if name.endswith(occ):
            short = name[: -len(occ)]
            break

    return f"{group} \u2014 {short}{suffix}"


# ---------------------------------------------------------------------------
# Matching engine
# ---------------------------------------------------------------------------

def _compile_basket_patterns() -> dict[str, list[tuple[str, re.Pattern]]]:
    """Pre-compile all regex patterns for every basket."""
    compiled: dict[str, list[tuple[str, re.Pattern]]] = {}
    for basket_name, items in CURATED_BASKETS.items():
        item_patterns: list[tuple[str, re.Pattern]] = []
        for item in items:
            for pat_str in item["patterns"]:
                item_patterns.append(
                    (item["label"], re.compile(pat_str, re.IGNORECASE))
                )
        compiled[basket_name] = item_patterns
    return compiled


_COMPILED = _compile_basket_patterns()


def match_product(product_name: str) -> dict[str, str]:
    """
    Match a single product name against all curated baskets.

    Returns a dict of {basket_name: matched_item_label} for every basket
    the product belongs to.  Empty dict if no match.
    """
    result: dict[str, str] = {}
    if not product_name:
        return result
    for basket_name, item_patterns in _COMPILED.items():
        for label, compiled_re in item_patterns:
            if compiled_re.search(product_name):
                # First match wins within a basket
                if basket_name not in result:
                    result[basket_name] = label
                break
    return result


def build_basket_product_sets(
    product_names: Iterable[str],
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """
    Build basket<->product mappings from a collection of unique product names.

    Parameters
    ----------
    product_names : iterable of str
        Unique product names from the dataset (e.g. ``df["product_name"].unique()``).

    Returns
    -------
    basket_to_products : dict[str, set[str]]
        Maps each basket name to the set of product names that match it.
    product_to_baskets : dict[str, set[str]]
        Maps each product name to the set of basket names it belongs to.
    """
    basket_to_products: dict[str, set[str]] = {
        name: set() for name in ALL_BASKET_NAMES
    }
    product_to_baskets: dict[str, set[str]] = {}

    for pname in product_names:
        matches = match_product(pname)
        if matches:
            product_to_baskets[pname] = set(matches.keys())
            for basket_name in matches:
                basket_to_products[basket_name].add(pname)

    return basket_to_products, product_to_baskets
