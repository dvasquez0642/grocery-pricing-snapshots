# Karen's Basket -- Adjacent & Supplementary Items

**Date:** 2026-04-29
**Source:** `analysis/sandbox/karens_basket_perturbation/candidate_substitutes.csv`
**Companion report:** `analysis/karens_basket_perturbation.html`

## Purpose

This document is a handoff for the data-quality agent working the *original*
60-item Karen's Basket.  It catalogues **49 Karen-adjacent grocery items**
mined from the master parquet (`data/pricing.parquet`, 2020-2025, non-sale
only).  Each item is documented with its regex patterns, parquet coverage
stats, and a pattern-leakage assessment so you can decide whether to:

- adopt the item as a **REPLACEMENT** for a weak Karen item,
- adopt it as a **SUPPLEMENT** that broadens the basket without disturbing
  the original 60, or
- skip it because the leakage is too high to use as-is.

All items below have **6/6 year coverage in the parquet** (2020 through 2025).
That was a hard filter on the candidate-mining step.

## Data-quality columns explained

| Column | Meaning |
|--------|---------|
| `n_chains` | distinct chains contributing rows in 2020-2025 non-sale |
| `n_rows` | total non-sale rows matching the regex(es) in 2020-2025 |
| `median_price` | naive median of all matching prices (NOT unit-normalised) |
| `dominant_unit` | most common value in the `unit` field |
| `unit_homogeneity` | share of rows that have the dominant unit |
| `robustness_score` | `n_years*100 + n_chains*5 + log10(n_rows+1)` -- used only for ranking |
| `pattern_leakage` | manual rating of how much the regex pulls in unintended products: **CLEAN**, **mostly-clean**, **LEAKY** |

A low `unit_homogeneity` (<50%) is almost always driven by chains that don't
expose a structured unit (blank string), not by genuine package-size mixing.
The blank-unit problem is a known parquet-level issue affecting both Karen
and adjacent items equally.

## Flag legend

- **REPLACEMENT** -- a Karen-Robust replacement.  The companion report
  proposes substituting this item for a specific weak Karen item (named).
- **SUPPLEMENT** -- a Karen-Broad addition.  Karen's basket has no equivalent
  (or a much weaker one), and adding this strengthens the basket panel.
- **CAUTION (leaky regex)** -- has high pattern leakage; use only with a
  tightened regex.  See the LEAKY-fixes table at the bottom.

---

## Items by category


## Breakfast

### Bacon (any brand)

- **Flag:** **REPLACEMENT** for `Oscar Mayer Bacon`
- **Theme key:** `breakfast.bacon`
- **Patterns:** `\bbacon\b`
- **Coverage:** 6/6 years, 126 chains, 9,980 rows
- **Median price:** $12.99
- **Dominant unit:** (blank) (40% homogeneity)
- **Robustness score:** 1234.0
- **Pattern leakage:** mostly-clean -- "bacon" pattern picks up "bacon-wrapped" prepared dishes; real bacon dominates the panel but not exclusively.
- **Top 5 matched product names:** Kenricks Bacon Wrapped Filet Mignon 8 Oz. Steak Package / Sliced Bacon / 3 Foot Grinder - Grilled Chicken with Crispy Bacon / 3 Foot. Grinder - Chicken Cutlet with Crispy Bacon / Karns Bundle Booster Add To Any Bundle Order (Click Add Under 'Select Bundle Options' Of Your Desired Bundle) 2 lb 26-30 Ct. EZ Peel Extra Large Shrimp 2 lb Karns Double Smoked Bacon 4 Lump Crab Cakes

### Bananas

- **Flag:** **SUPPLEMENT** - **CAUTION (leaky regex)**
- **Theme key:** `breakfast.banana`
- **Patterns:** `\bbanana`
- **Coverage:** 6/6 years, 83 chains, 4,685 rows
- **Median price:** $3.99
- **Dominant unit:** (blank) (35% homogeneity)
- **Robustness score:** 1018.7
- **Pattern leakage:** LEAKY -- picks up strawberry-banana drinks and birthday-cake decor. Suggest tightening to bare "banana" or with produce category constraint.
- **Top 5 matched product names:** Bananas / Core Organic Strawberry Banana / Strawberry Banana / Yellow Bananas / 99 Strawberry Banana From  Pink - Happy Birthday From  Blue - Happy Birthday Fro

### Greek yogurt

- **Flag:** **SUPPLEMENT**
- **Theme key:** `breakfast.greek_yogurt`
- **Patterns:** `greek\s*yogurt`, `chobani`, `\byogurt\b`
- **Coverage:** 6/6 years, 68 chains, 6,963 rows
- **Median price:** $3.99
- **Dominant unit:** (blank) (28% homogeneity)
- **Robustness score:** 943.8
- **Pattern leakage:** mostly-clean -- generic "yogurt" pattern is broad but yogurt products dominate. Yogurt-flavored candy and dips leak in.
- **Top 5 matched product names:** Yogurt Parfait / Yogurt Jelly 1.76oz(50g) / Yogurt (Ithaca Farm) / Lowfat Vanilla Yogurt / Fruit Yogurt Dip /lb

### Bagels

- **Flag:** **SUPPLEMENT**
- **Theme key:** `breakfast.bagel`
- **Patterns:** `\bbagel`
- **Coverage:** 6/6 years, 49 chains, 2,547 rows
- **Median price:** $4.99
- **Dominant unit:** (blank) (51% homogeneity)
- **Robustness score:** 848.4
- **Pattern leakage:** CLEAN -- bagels and bagel chips/sandwiches; bagels themselves dominate.
- **Top 5 matched product names:** Basic Toasted Bagel / Bagel Medley with Additional Fresh Fruit Salad / Bagel Medley / Toasted Bagel / Deluxe Toasted Bagel

### Breakfast sausage

- **Flag:** **SUPPLEMENT**
- **Theme key:** `breakfast.breakfast_sausage`
- **Patterns:** `breakfast\s*sausage`, `sausage\s*links?`, `sausage\s*patties?`
- **Coverage:** 6/6 years, 48 chains, 4,200 rows
- **Median price:** $5.99
- **Dominant unit:** lb (18% homogeneity)
- **Robustness score:** 843.6
- **Pattern leakage:** CLEAN -- patterns explicitly target breakfast sausage links/patties.
- **Top 5 matched product names:** Mild Italian Sausage Links / Pork Breakfast Sausage / Breakfast Sausage Links / Butterball Sausage Link / Applegate Naturals Chicken & Apple Breakfast Sausage, 10 count, 7 oz

### Cold cereal (generic)

- **Flag:** **SUPPLEMENT**
- **Theme key:** `breakfast.cold_cereal_generic`
- **Patterns:** `\bcheerios\b`, `frosted\s*flakes`, `raisin\s*bran`, `corn\s*flakes`, `\bcereal\b`
- **Coverage:** 6/6 years, 47 chains, 3,495 rows
- **Median price:** $4.99
- **Dominant unit:** (blank) (35% homogeneity)
- **Robustness score:** 838.5
- **Pattern leakage:** CLEAN -- Cheerios, Raisin Bran, Frosted Flakes, generic cereal.
- **Top 5 matched product names:** Choco Ring Cereal 20.1oz(570g) / Almond Cranberry Cereal 22.22oz(630g) / Honey Nut Cheerios / Corn Sweet Cereal 21.16oz(600g) / General Mills Cheerios Honey Nut Cereal, 10.8 oz


## Lunch / sandwich

### Canned tuna (any)

- **Flag:** **REPLACEMENT** for `StarKist Tuna`
- **Theme key:** `lunch.canned_tuna`
- **Patterns:** `\btuna\b`
- **Coverage:** 6/6 years, 61 chains, 4,239 rows
- **Median price:** $4.29
- **Dominant unit:** (blank) (74% homogeneity)
- **Robustness score:** 908.6
- **Pattern leakage:** mostly-clean -- sushi tuna rolls and tuna salad leak in; canned tuna dominates with high unit homogeneity (74%).
- **Top 5 matched product names:** Tuna with Hot Pepper Sauce 5.29oz(150g) 4 Cans / StarKist Chunk Light Tuna in Water / Combo Tuna Salmon Roll / White Albacore Tuna Salad / Tuna Brown Rice Roll

### Sliced cheese (any)

- **Flag:** **REPLACEMENT** for `American Cheese`
- **Theme key:** `lunch.sliced_cheese`
- **Patterns:** `sliced\s*cheese`, `cheese\s*slices?`, `american\s*cheese`, `cheddar\s*slice`
- **Coverage:** 6/6 years, 45 chains, 2,491 rows
- **Median price:** $7.99
- **Dominant unit:** (blank) (30% homogeneity)
- **Robustness score:** 828.4
- **Pattern leakage:** mostly-clean -- American cheese, sliced cheddar, cheese slices dominate.
- **Top 5 matched product names:** American Cheese Slices / Swiss Cheese Slices / Colby Jack Sliced Cheese / White American Cheese / Sliced American Cheese

### Deli ham (any brand)

- **Flag:** **REPLACEMENT** for `Boar's Head Ham`
- **Theme key:** `lunch.deli_ham_generic`
- **Patterns:** `deli\s*ham`, `sliced\s*ham`, `black\s*forest\s*ham`
- **Coverage:** 6/6 years, 37 chains, 868 rows
- **Median price:** $10.74
- **Dominant unit:** (blank) (59% homogeneity)
- **Robustness score:** 787.9
- **Pattern leakage:** CLEAN -- deli ham, sliced ham, black forest ham.
- **Top 5 matched product names:** Black Forest Ham / Spiral Sliced Ham / Black Forest Ham Sandwich / Description: Beautifully prepared, this sweet and succulent  spiral-cut sliced ham is a feast for the palate as  well as the eye. / Piggery Sliced Ham (6 oz)

### Deli turkey (any brand)

- **Flag:** **REPLACEMENT** for `Boar's Head Turkey`
- **Theme key:** `lunch.deli_turkey_generic`
- **Patterns:** `deli\s*turkey`, `oven\s*roasted\s*turkey`, `sliced\s*turkey`, `turkey\s*breast.*deli`
- **Coverage:** 6/6 years, 26 chains, 1,209 rows
- **Median price:** $9.99
- **Dominant unit:** (blank) (28% homogeneity)
- **Robustness score:** 733.1
- **Pattern leakage:** CLEAN -- deli turkey, oven-roasted turkey, sliced turkey.
- **Top 5 matched product names:** Oven Roasted Turkey Breast / Shaved Oven Roasted Turkey / Applegate Naturals Oven Roasted Turkey Breast, 7 oz / Applegate Organics Oven Roasted Turkey Breast, 6 oz / Sliced Turkey Breast


## Dinner proteins

### Shrimp

- **Flag:** **SUPPLEMENT**
- **Theme key:** `dinner.shrimp`
- **Patterns:** `\bshrimp\b`
- **Coverage:** 6/6 years, 90 chains, 9,232 rows
- **Median price:** $15.99
- **Dominant unit:** (blank) (34% homogeneity)
- **Robustness score:** 1054.0
- **Pattern leakage:** mostly-clean -- picks up prepared/breaded shrimp items; raw and cocktail shrimp dominate.
- **Top 5 matched product names:** Karns Bundle Booster Add To Any Bundle Order (Click Add Under 'Select Bundle Options' Of Your Desired Bundle) 2 lb 26-30 Ct. EZ Peel Extra Large Shrimp 2 lb Karns Double Smoked Bacon 4 Lump Crab Cakes / Cocktail Shrimp Ring with Sauce / Hand Breaded Butterfly Shrimp / Karns Bundle Booster Add To Any Bundle Order 2 lb 26-30 Ct. EZ Peel Extra Large Shrimp 2 lb Karns Double Smoked Bacon 4 Lump Crab Cakes / 50 Jumbo Peeled & Deveined Shrimp Platter

### Ribeye steak

- **Flag:** **SUPPLEMENT**
- **Theme key:** `dinner.ribeye`
- **Patterns:** `\bribeye\b`, `rib\s*eye`
- **Coverage:** 6/6 years, 62 chains, 2,289 rows
- **Median price:** $13.69
- **Dominant unit:** (blank) (51% homogeneity)
- **Robustness score:** 913.4
- **Pattern leakage:** mostly-clean -- "ribeye seasoning" / "ribeye sauce" leak in; ribeye steaks dominate.
- **Top 5 matched product names:** Ribeye Steak / Certified Angus Beef Delmonico Ribeye Steaks / Robust Ribeye Steak Seasoning / Robust Ribeye Steak Sauce / Robust Ribeye Marinade

### Salmon fillet

- **Flag:** **SUPPLEMENT**
- **Theme key:** `dinner.salmon`
- **Patterns:** `\bsalmon\b`
- **Coverage:** 6/6 years, 61 chains, 4,149 rows
- **Median price:** $10.99
- **Dominant unit:** (blank) (60% homogeneity)
- **Robustness score:** 908.6
- **Pattern leakage:** mostly-clean -- salmon seasoning leaks in; fresh and frozen salmon portions dominate.
- **Top 5 matched product names:** Alaskan Salmon / Savory Salmon Seasoning / Bowl & Basket Boneless and Skinless Wild Caught Salmon Portions, 8 count, 32 oz / Bowl & Basket Boneless & Skinless Salmon Portions, 16 oz / Smoked Salmon Sampler

### Pork chops

- **Flag:** **SUPPLEMENT**
- **Theme key:** `dinner.pork_chop`
- **Patterns:** `pork\s*chop`
- **Coverage:** 6/6 years, 58 chains, 1,429 rows
- **Median price:** $5.99
- **Dominant unit:** lb (47% homogeneity)
- **Robustness score:** 893.2
- **Pattern leakage:** CLEAN -- almost exclusively pork chops, with smoked, boneless, and bone-in variants.
- **Top 5 matched product names:** Smoked Pork Chops – / Sweet Bourbon Flavored Boneless Pork Chops – / Boneless Pork Chops – / Pork Chops / 4 - Smoked Pork Chops Appr 2lbs, 8 oz each

### Pork loin / tenderloin

- **Flag:** **SUPPLEMENT**
- **Theme key:** `dinner.pork_loin`
- **Patterns:** `pork\s*loin`, `pork\s*tenderloin`
- **Coverage:** 6/6 years, 51 chains, 1,634 rows
- **Median price:** $4.48
- **Dominant unit:** lb (49% homogeneity)
- **Robustness score:** 858.2
- **Pattern leakage:** CLEAN -- pork loin and tenderloin cuts dominate.
- **Top 5 matched product names:** Fresh Pork Loin / Fresh Pork Tenderloin / Pork Tenderloin / Pork Tenderloin – / Pork Loin, Natural, Boneless, Center-Cut Strap-Off, 1/8 Inch Trim 8 Pound Average, (NAMP 414) Fresh, 8 Lb Avg Package

### Chicken drumsticks

- **Flag:** **REPLACEMENT** for `Chicken Legs`
- **Theme key:** `dinner.chicken_drumstick`
- **Patterns:** `drumstick`
- **Coverage:** 6/6 years, 50 chains, 1,168 rows
- **Median price:** $3.99
- **Dominant unit:** lb (42% homogeneity)
- **Robustness score:** 853.1
- **Pattern leakage:** CLEAN -- drumsticks dominate; very high signal-to-noise.
- **Top 5 matched product names:** Chicken Drumsticks / Fresh Chicken Drumsticks / Bowl & Basket Fresh Young Turkey Drumsticks / Tyson Chicken Drumsticks / Drumsticks

### Chicken thighs

- **Flag:** **SUPPLEMENT**
- **Theme key:** `dinner.bone_in_chicken_thigh`
- **Patterns:** `chicken\s*thigh`
- **Coverage:** 6/6 years, 47 chains, 1,504 rows
- **Median price:** $8.60
- **Dominant unit:** (blank) (48% homogeneity)
- **Robustness score:** 838.2
- **Pattern leakage:** CLEAN -- chicken thigh dominates.
- **Top 5 matched product names:** Grilled Lemony Herb Chicken Thigh Skewers / Chicken Thighs / Jumbo Chicken Thighs / Boneless Skinless Chicken Thighs / Boneless, Skinless Chicken Thighs

### Strip steak

- **Flag:** **SUPPLEMENT**
- **Theme key:** `dinner.strip_steak`
- **Patterns:** `new\s*york\s*strip`, `strip\s*steak`, `ny\s*strip`
- **Coverage:** 6/6 years, 45 chains, 1,328 rows
- **Median price:** $16.99
- **Dominant unit:** lb (34% homogeneity)
- **Robustness score:** 828.1
- **Pattern leakage:** CLEAN -- NY strip / strip steak dominates.
- **Top 5 matched product names:** New York Strip Steak / Strip Steak – / NY Strip Steak / Black Nugget Marinated Strip Steaks – / Two River’s New York Strip or Ribeye Steak

### Whole chicken

- **Flag:** **SUPPLEMENT**
- **Theme key:** `dinner.whole_chicken`
- **Patterns:** `whole\s*chicken`, `roaster\s*chicken`
- **Coverage:** 6/6 years, 34 chains, 434 rows
- **Median price:** $5.99
- **Dominant unit:** lb (55% homogeneity)
- **Robustness score:** 772.6
- **Pattern leakage:** CLEAN -- whole / roaster chicken.
- **Top 5 matched product names:** Whole Chicken Wings / Whole Chicken / Tyson Whole Chicken / Premium Young Whole Chicken / Roaster Chicken Breast - Sold Cold


## Produce / sides

### Onions

- **Flag:** **SUPPLEMENT**
- **Theme key:** `side.onion`
- **Patterns:** `\bonion`
- **Coverage:** 6/6 years, 118 chains, 8,526 rows
- **Median price:** $4.99
- **Dominant unit:** (blank) (59% homogeneity)
- **Robustness score:** 1193.9
- **Pattern leakage:** mostly-clean -- picks up "onion-flavored" sauces/dressings; raw onions dominate.
- **Top 5 matched product names:** Diced Onions / Spanish Onions / Vidalia Onion BBQ Sauce / Vidalia Onion & Peppercorn Dressing / Vidalia Onion & Poppyseed Dressing

### Strawberries

- **Flag:** **SUPPLEMENT** - **CAUTION (leaky regex)**
- **Theme key:** `side.strawberries`
- **Patterns:** `strawberr`
- **Coverage:** 6/6 years, 105 chains, 16,690 rows
- **Median price:** $13.99
- **Dominant unit:** (blank) (65% homogeneity)
- **Robustness score:** 1129.2
- **Pattern leakage:** LEAKY -- "strawberr" matches strawberry-flavored beverages, snacks, sparkling water. Suggest tightening to require produce category.
- **Top 5 matched product names:** Strawberries / Kiwi Strawberry Sparkling Water / Bai São Paulo Strawberry Lemonade / Bai S\u00e3o Paulo Strawberry Lemonade / Kupang Kiwi Strawberry

### Blueberries

- **Flag:** **SUPPLEMENT** - **CAUTION (leaky regex)**
- **Theme key:** `side.blueberries`
- **Patterns:** `blueberr`
- **Coverage:** 6/6 years, 88 chains, 5,891 rows
- **Median price:** $5.29
- **Dominant unit:** (blank) (34% homogeneity)
- **Robustness score:** 1043.8
- **Pattern leakage:** LEAKY -- "blueberr" matches blueberry granola bars, lemonade, even toothpaste. Suggest tightening.
- **Top 5 matched product names:** Brasilia Blueberry / Blueberries / Bali Blueberry Lemonade / CZY MONKY BLUEBERRY GRANOLA BITES 7.5Z / Kids Toothpaste Blueberry 3.52oz(100g) 5 Packs

### Bell peppers

- **Flag:** **SUPPLEMENT**
- **Theme key:** `side.bell_pepper`
- **Patterns:** `bell\s*pepper`, `green\s*pepper`, `red\s*pepper`
- **Coverage:** 6/6 years, 86 chains, 3,124 rows
- **Median price:** $4.49
- **Dominant unit:** (blank) (59% homogeneity)
- **Robustness score:** 1033.5
- **Pattern leakage:** mostly-clean -- some "red pepper aioli" and "roasted red pepper hummus" leakage; raw peppers dominate.
- **Top 5 matched product names:** Mollie's Famous Grilled Tri-Tip Slider Board with Red Pepper Aioli / Green Peppers / Red Peppers / Green Pepper / Roasted Red Pepper Hummus

### Avocados

- **Flag:** **SUPPLEMENT**
- **Theme key:** `side.avocado`
- **Patterns:** `\bavocado`
- **Coverage:** 6/6 years, 79 chains, 2,274 rows
- **Median price:** $4.40
- **Dominant unit:** (blank) (60% homogeneity)
- **Robustness score:** 998.4
- **Pattern leakage:** mostly-clean -- sushi rolls leak in; raw and Hass avocados dominate.
- **Top 5 matched product names:** Avocados / Large Hass Avocados / Eel Avocado Brown Rice Roll / Spicy Tuna Avocado Roll / Cucumber Avocado Roll

### Carrots

- **Flag:** **SUPPLEMENT**
- **Theme key:** `side.carrots`
- **Patterns:** `\bcarrots?\b`
- **Coverage:** 6/6 years, 71 chains, 4,956 rows
- **Median price:** $3.49
- **Dominant unit:** (blank) (57% homogeneity)
- **Robustness score:** 958.7
- **Pattern leakage:** mostly-clean -- carrot cake leakage; baby/whole carrots dominate.
- **Top 5 matched product names:** Carrot Cake / Pickled Carrots / Bowl & Basket Baby Carrots, 16 oz / Carrots [2 lb] – Organic / Baby Carrots

### Spinach

- **Flag:** **SUPPLEMENT**
- **Theme key:** `side.spinach`
- **Patterns:** `\bspinach\b`
- **Coverage:** 6/6 years, 64 chains, 4,376 rows
- **Median price:** $5.99
- **Dominant unit:** (blank) (48% homogeneity)
- **Robustness score:** 923.6
- **Pattern leakage:** mostly-clean -- spinach dip and spinach-and-cheese pasta leak in; raw spinach dominates.
- **Top 5 matched product names:** Spinach Dip in Bread Bowl / Spinach & Ricotta Ravioli / Spinach & Cheese Tortellini / Organic Baby Rice Snack Spinach 1.05oz(30g) / Spinach Salad

### Broccoli

- **Flag:** **SUPPLEMENT**
- **Theme key:** `side.broccoli`
- **Patterns:** `\bbroccoli\b`
- **Coverage:** 6/6 years, 63 chains, 6,327 rows
- **Median price:** $8.99
- **Dominant unit:** (blank) (67% homogeneity)
- **Robustness score:** 918.8
- **Pattern leakage:** mostly-clean -- beef-and-broccoli prepared dishes leak in; raw and frozen broccoli dominate.
- **Top 5 matched product names:** Beef and Broccoli (Half Tray) / Chicken And Broccoli (Half Tray) / Broccoli Florets / Broccoli Oreganata / Bite-Sized Broccoli Florets

### Green beans

- **Flag:** **SUPPLEMENT**
- **Theme key:** `side.green_beans`
- **Patterns:** `green\s*bean`
- **Coverage:** 6/6 years, 54 chains, 2,284 rows
- **Median price:** $2.69
- **Dominant unit:** (blank) (43% homogeneity)
- **Robustness score:** 873.4
- **Pattern leakage:** CLEAN -- fresh, frozen, and canned green beans.
- **Top 5 matched product names:** Cut Green Beans / Green Beans / Hannaford Cut Green Beans / Cut Green Beans or Whole Kernel Golden Corn / Bowl & Basket Green Beans, 12 oz


## Pantry & canned

### Salsa

- **Flag:** **SUPPLEMENT**
- **Theme key:** `pantry.salsa`
- **Patterns:** `\bsalsa\b`
- **Coverage:** 6/6 years, 55 chains, 3,906 rows
- **Median price:** $4.99
- **Dominant unit:** (blank) (50% homogeneity)
- **Robustness score:** 878.6
- **Pattern leakage:** CLEAN -- almost exclusively jarred salsa.
- **Top 5 matched product names:** CHOLULA SALSA MED ORIG 12Z / CHOLULA SALSA VERDE MLD 12Z / CHOLULA SALSA HOT CHPTL SMKY 12Z / Cholula Salsa / Description: Our grilled vegetable quesadillas and corn  & blackbean tortilla cakes served with fresh guacamole, salsa and sour cream.

### Olive oil

- **Flag:** **SUPPLEMENT**
- **Theme key:** `pantry.olive_oil`
- **Patterns:** `olive\s*oil`
- **Coverage:** 6/6 years, 49 chains, 2,864 rows
- **Median price:** $6.99
- **Dominant unit:** (blank) (56% homogeneity)
- **Robustness score:** 848.5
- **Pattern leakage:** CLEAN -- olive oil bottles dominate.
- **Top 5 matched product names:** Spaghetti Sauce Garlic, Olive Oil & Chili Pepper 1.57oz(44.6g) / Country Crock Plant Butter with Olive Oil / Extra Virgin Olive Oil / Olive Oil / Castillo de Canena Harissa Olive Oil / Dorothy Lane Market

### Black beans (canned)

- **Flag:** **SUPPLEMENT**
- **Theme key:** `pantry.black_beans`
- **Patterns:** `black\s*beans?`
- **Coverage:** 6/6 years, 45 chains, 2,071 rows
- **Median price:** $4.29
- **Dominant unit:** (blank) (60% homogeneity)
- **Robustness score:** 828.3
- **Pattern leakage:** CLEAN -- canned black beans dominate.
- **Top 5 matched product names:** Braised Black Beans in Soy Sauce 2.4oz(70g) / Description: Our grilled vegetable quesadillas and corn  & blackbean tortilla cakes served with fresh guacamole, salsa and sour cream. / Black Bean Paste with Smoky Flavor 10.58oz(300g) / Black Bean Paste 10.58oz(300g) / Roasted Corn & Black Bean Blend

### Tomato sauce / paste

- **Flag:** **SUPPLEMENT**
- **Theme key:** `pantry.tomato_sauce`
- **Patterns:** `tomato\s*sauce`, `tomato\s*paste`
- **Coverage:** 6/6 years, 29 chains, 1,016 rows
- **Median price:** $1.49
- **Dominant unit:** (blank) (50% homogeneity)
- **Robustness score:** 748.0
- **Pattern leakage:** CLEAN -- tomato sauce / paste.
- **Top 5 matched product names:** Hunt's Tomato Sauce / Hannaford Tomato Sauce / Hannaford No Salt Added Tomato Sauce / Amore Double Concentrated Tomato Paste, 4.5 oz / Bowl & Basket Tomato Paste, 6 oz

### Canola / vegetable oil

- **Flag:** **SUPPLEMENT**
- **Theme key:** `pantry.canola_oil`
- **Patterns:** `canola\s*oil`, `vegetable\s*oil`
- **Coverage:** 6/6 years, 26 chains, 1,301 rows
- **Median price:** $3.99
- **Dominant unit:** (blank) (31% homogeneity)
- **Robustness score:** 733.1
- **Pattern leakage:** CLEAN -- canola / vegetable oil.
- **Top 5 matched product names:** Bowl & Basket 100% Pure Vegetable Oil, 48 fl oz / Bowl & Basket 100% Pure Vegetable Oil, 1 gal / Bowl & Basket 100% Pure Canola Oil, 1 gal / Vegetable Oil / Bowl & Basket 100% Pure Canola Oil, 24 fl oz

### Chickpeas / garbanzo

- **Flag:** **SUPPLEMENT**
- **Theme key:** `pantry.chickpeas`
- **Patterns:** `chickpea`, `garbanzo`
- **Coverage:** 6/6 years, 23 chains, 631 rows
- **Median price:** $3.49
- **Dominant unit:** (blank) (33% homogeneity)
- **Robustness score:** 717.8
- **Pattern leakage:** CLEAN -- chickpeas / garbanzo beans.
- **Top 5 matched product names:** Banza Rotini Made from Chickpeas Pasta, 8 oz / Banza Shells Made from Chickpeas Pasta, 8 oz / Wholesome Pantry Organic Garbanzo Beans, 15.5 oz / Barilla Chickpea Penne Pasta, 8.8 oz / Barilla Chickpea Rotini Pasta, 8.8 oz

### Canned diced tomatoes

- **Flag:** **SUPPLEMENT**
- **Theme key:** `pantry.diced_tomato`
- **Patterns:** `diced\s*tomato`
- **Coverage:** 6/6 years, 17 chains, 852 rows
- **Median price:** $1.55
- **Dominant unit:** (blank) (48% homogeneity)
- **Robustness score:** 687.9
- **Pattern leakage:** CLEAN -- canned diced tomatoes.
- **Top 5 matched product names:** Muir Glen Organic Fire Roasted Diced Tomatoes / Hot Diced Tomatoes with Habaneros / Hannaford No Salt Added Diced Tomatoes / Hannaford Diced Tomatoes / Diced Tomatoes


## Dairy

### Block cheddar

- **Flag:** **SUPPLEMENT**
- **Theme key:** `dairy.block_cheddar`
- **Patterns:** `\bblock\s*cheddar`, `sharp\s*cheddar(?!.*slice)`, `\bcheddar\s*cheese\b(?!.*slice)(?!.*shred)`
- **Coverage:** 6/6 years, 52 chains, 4,722 rows
- **Median price:** $5.75
- **Dominant unit:** (blank) (35% homogeneity)
- **Robustness score:** 863.7
- **Pattern leakage:** mostly-clean -- pattern excludes "slice" and "shred" so it pulls block cheddar specifically.
- **Top 5 matched product names:** Mild Cheddar Cheese / Medium Cheddar Cheese Cubes / Sharp Cheddar Cheese / Shredded Mild Cheddar Cheese / Sharp Cheddar Cheese Spread

### Sour cream

- **Flag:** **SUPPLEMENT**
- **Theme key:** `dairy.sour_cream`
- **Patterns:** `sour\s*cream`
- **Coverage:** 6/6 years, 47 chains, 3,370 rows
- **Median price:** $5.50
- **Dominant unit:** (blank) (39% homogeneity)
- **Robustness score:** 838.5
- **Pattern leakage:** CLEAN -- sour cream dominates.
- **Top 5 matched product names:** Sour Cream / Rippled Sour Cream & Cheddar Potato Chips / Natural Sour Cream / Description: Our grilled vegetable quesadillas and corn  & blackbean tortilla cakes served with fresh guacamole, salsa and sour cream. / Cheddar & Sour Cream Flavored Chip Pack

### Shredded cheese

- **Flag:** **SUPPLEMENT**
- **Theme key:** `dairy.shredded_cheese`
- **Patterns:** `shredded\s*cheese`, `shredded\s*cheddar`, `shredded\s*mozzarella`, `finely\s*shredded`
- **Coverage:** 6/6 years, 36 chains, 1,674 rows
- **Median price:** $3.59
- **Dominant unit:** (blank) (34% homogeneity)
- **Robustness score:** 783.2
- **Pattern leakage:** CLEAN -- shredded cheese / cheddar / mozzarella.
- **Top 5 matched product names:** Finely Shredded Lettuce / Shredded Mozzarella Cheese / Bowl & Basket Whole Milk Shredded Mozzarella Cheese, 8 oz / Bowl & Basket Finely Shredded Mexican Style Blend Cheese, 8 oz / Bowl & Basket Finely Shredded Cheddar Jack Cheese, 8 oz


## Frozen

### Frozen pizza

- **Flag:** **SUPPLEMENT** - **CAUTION (leaky regex)**
- **Theme key:** `frozen.frozen_pizza`
- **Patterns:** `\bpizza\b`
- **Coverage:** 6/6 years, 81 chains, 7,012 rows
- **Median price:** $9.99
- **Dominant unit:** (blank) (27% homogeneity)
- **Robustness score:** 1008.8
- **Pattern leakage:** LEAKY -- "pizza" matches refrigerated and prepared pizza, pizza-flavored cheese blends, pizza-themed sides. Real frozen pizza is a subset.
- **Top 5 matched product names:** Margherita Pizza / Italian Sausage Pizza / Four Cheese Pizza / Roasted Veggie Pizza / Pizza Cheese Blend, Mozzarella/Provolone/Muenster, Diced

### Frozen french fries

- **Flag:** **SUPPLEMENT**
- **Theme key:** `frozen.frozen_french_fries`
- **Patterns:** `french\s*fries`, `\btater\s*tots?`, `frozen.*fries`
- **Coverage:** 6/6 years, 31 chains, 2,047 rows
- **Median price:** $28.99
- **Dominant unit:** case (65% homogeneity)
- **Robustness score:** 758.3
- **Pattern leakage:** CLEAN -- french fries and tater tots.
- **Top 5 matched product names:** 3/8 Inch Straight Cut French Fries / 3\/8 Inch Straight Cut French Fries / French Fries / 1/2 inch Crinkle Cut French Fries / 1\/2 inch Crinkle Cut French Fries

### Frozen vegetables (mixed)

- **Flag:** **SUPPLEMENT**
- **Theme key:** `frozen.frozen_vegetables`
- **Patterns:** `frozen.*veget`, `frozen.*broccoli`, `frozen.*corn`, `frozen.*green\s*bean`
- **Coverage:** 6/6 years, 17 chains, 157 rows
- **Median price:** $3.19
- **Dominant unit:** (blank) (39% homogeneity)
- **Robustness score:** 687.2
- **Pattern leakage:** mostly-clean -- pattern requires "frozen" prefix; mixed frozen vegetable bags dominate.
- **Top 5 matched product names:** Frozen Broccoli or Cauliflower / Frozen Vegetables / Essential Everyday Frozen Vegetables / Pictsweet Farms® Steam'ables® Edamame with Sea Salt, Farm Favorites, Frozen Vegetables, 10 oz / Nature's Promise Organic Frozen Broccoli Florets


## Beverages

### Bottled water (case)

- **Flag:** **SUPPLEMENT**
- **Theme key:** `bev.bottled_water`
- **Patterns:** `bottled\s*water`, `spring\s*water`, `\bdasani\b`, `poland\s*spring`, `\bfiji\b`
- **Coverage:** 6/6 years, 50 chains, 1,415 rows
- **Median price:** $3.33
- **Dominant unit:** (blank) (45% homogeneity)
- **Robustness score:** 853.2
- **Pattern leakage:** mostly-clean -- case-pack bottled water dominates; some private-label spring water mixed in.
- **Top 5 matched product names:** Absopure Spring Water / Spring Water / Natural Spring Water / Bottled Water per bottle Buehler’s own 100% Natural Spring Water. / Bowl & Basket Spring Water, 16.9 fl oz, 24 count

### Sports drink

- **Flag:** **SUPPLEMENT**
- **Theme key:** `bev.gatorade`
- **Patterns:** `\bgatorade\b`, `\bpowerade\b`
- **Coverage:** 6/6 years, 23 chains, 1,035 rows
- **Median price:** $8.59
- **Dominant unit:** (blank) (44% homogeneity)
- **Robustness score:** 718.0
- **Pattern leakage:** CLEAN -- Gatorade and Powerade.
- **Top 5 matched product names:** Description: A high carbohydrate, high protein assortment that includes Gatorade, protein drinks, nuts, Power Bars, fresh fruit and granola bars. / Gatorade / Mountain Blast Powerade / Gatorade Zero Variety Pack / Zero Sugar Mixed Berry Powerade

### Domestic beer (12-pack)

- **Flag:** **SUPPLEMENT**
- **Theme key:** `bev.beer_domestic`
- **Patterns:** `\bbud\s*light\b`, `\bcoors\b`, `\bmiller\s*lite\b`, `\bcorona\b`
- **Coverage:** 6/6 years, 23 chains, 481 rows
- **Median price:** $14.99
- **Dominant unit:** (blank) (90% homogeneity)
- **Robustness score:** 717.7
- **Pattern leakage:** CLEAN -- Bud Light, Coors, Miller Lite, Corona; 12-pack and 24-pack.
- **Top 5 matched product names:** Bud Light / Coors Light / Corona Extra / Miller Lite / Bolsa Corona


## Snacks

### Tortilla chips

- **Flag:** **SUPPLEMENT**
- **Theme key:** `snack.tortilla_chips`
- **Patterns:** `tortilla\s*chip`, `\bdoritos\b`, `\btostitos\b`
- **Coverage:** 6/6 years, 51 chains, 2,656 rows
- **Median price:** $4.79
- **Dominant unit:** bag (26% homogeneity)
- **Robustness score:** 858.4
- **Pattern leakage:** CLEAN -- Tostitos, Doritos, and chain-private-label tortilla chips dominate.
- **Top 5 matched product names:** Round Corn Tortilla Chips / Doritos Cheeto Mix Variety Pack / Triangle Corn Tortilla Chips / Nacho Cheese Flavored Tortilla Chip Pack / Tortilla Chips

### Granola bars

- **Flag:** **SUPPLEMENT**
- **Theme key:** `snack.granola_bars`
- **Patterns:** `granola\s*bar`, `\bnature\s*valley\b`, `\bclif\s*bar\b`, `\bkind\s*bar\b`
- **Coverage:** 6/6 years, 24 chains, 977 rows
- **Median price:** $11.99
- **Dominant unit:** (blank) (47% homogeneity)
- **Robustness score:** 723.0
- **Pattern leakage:** CLEAN -- Nature Valley, Clif, Kind, generic granola bars.
- **Top 5 matched product names:** Description: A high carbohydrate, high protein assortment that includes Gatorade, protein drinks, nuts, Power Bars, fresh fruit and granola bars. / Description: A low fat assortment of fresh fruit, juice boxes, granola bars and low fat cookies. / Peanut Butter Granola Bar / Sweet & Salty Nut Granola Bars / Fruit & Nut Granola Bar


## Bread & bakery

### Sandwich bread (any)

- **Flag:** **REPLACEMENT** for `Sara Lee Bread / Wonder Bread` - **CAUTION (leaky regex)**
- **Theme key:** `bread.bread_loaf_generic`
- **Patterns:** `\bbread\b(?!.*pan)(?!.*pita)(?!.*tortilla)`
- **Coverage:** 6/6 years, 111 chains, 9,827 rows
- **Median price:** $5.49
- **Dominant unit:** (blank) (44% homogeneity)
- **Robustness score:** 1159.0
- **Pattern leakage:** LEAKY -- "bread" matches garlic bread, breadcrumbs, breadsticks, dip bowls. Treat as a generic-bread proxy, not pure sandwich bread.
- **Top 5 matched product names:** Spinach Dip in Bread Bowl / Garlic Bread Platter / Garlic Bread / BREAD GARL SLCD 16CT / Bread, Garlic, Sliced, Frozen, 1.2 Ounce, 48 Ct Package

### Tortillas

- **Flag:** **SUPPLEMENT** - **CAUTION (leaky regex)**
- **Theme key:** `bread.tortilla`
- **Patterns:** `\btortilla`
- **Coverage:** 6/6 years, 73 chains, 5,507 rows
- **Median price:** $4.49
- **Dominant unit:** (blank) (38% homogeneity)
- **Robustness score:** 968.7
- **Pattern leakage:** LEAKY -- pattern matches tortilla CHIPS heavily (and tortilla wraps less so). Recommend split: separate "tortilla wraps" from "tortilla chips".
- **Top 5 matched product names:** Round Corn Tortilla Chips / Triangle Corn Tortilla Chips / Nacho Cheese Flavored Tortilla Chip Pack / Description: Our grilled vegetable quesadillas and corn  & blackbean tortilla cakes served with fresh guacamole, salsa and sour cream. / 12″ Flour Tortillas

### Hot dog / hamburger buns

- **Flag:** **SUPPLEMENT**
- **Theme key:** `bread.hot_dog_bun`
- **Patterns:** `hot\s*dog\s*bun`, `hamburger\s*bun`
- **Coverage:** 6/6 years, 35 chains, 781 rows
- **Median price:** $3.49
- **Dominant unit:** package (28% homogeneity)
- **Robustness score:** 777.9
- **Pattern leakage:** CLEAN -- hot dog and hamburger buns.
- **Top 5 matched product names:** Hot Dog Buns / Hamburger Buns / Fresh Hamburger Buns / Hawaiian Sweet Hamburger Buns / Hawaiian Sweet Top-Sliced Hot Dog Buns


---

## Summary tables

### All replacements (paste-ready for Karen-Robust adoption)

| Original Karen item | Proposed replacement | Theme key | n_chains | n_rows | Pattern leakage |
|---|---|---|---|---|---|
| Oscar Mayer Bacon | Bacon (any brand) | `breakfast.bacon` | 126 | 9,980 | mostly-clean |
| StarKist Tuna | Canned tuna (any) | `lunch.canned_tuna` | 61 | 4,239 | mostly-clean |
| Chicken Legs | Chicken drumsticks | `dinner.chicken_drumstick` | 50 | 1,168 | CLEAN |
| American Cheese | Sliced cheese (any) | `lunch.sliced_cheese` | 45 | 2,491 | mostly-clean |
| Boar's Head Ham | Deli ham (any brand) | `lunch.deli_ham_generic` | 37 | 868 | CLEAN |
| Boar's Head Turkey | Deli turkey (any brand) | `lunch.deli_turkey_generic` | 26 | 1,209 | CLEAN |
| Sara Lee Bread / Wonder Bread | Sandwich bread (any) | `bread.bread_loaf_generic` | 111 | 9,827 | LEAKY |

### CLEAN / mostly-clean supplements (recommended for Karen-Broad)

| Item | Theme key | n_chains | n_rows | Median $ | Pattern leakage |
|---|---|---|---|---|---|
| Onions | `side.onion` | 118 | 8,526 | $4.99 | mostly-clean |
| Shrimp | `dinner.shrimp` | 90 | 9,232 | $15.99 | mostly-clean |
| Bell peppers | `side.bell_pepper` | 86 | 3,124 | $4.49 | mostly-clean |
| Avocados | `side.avocado` | 79 | 2,274 | $4.40 | mostly-clean |
| Carrots | `side.carrots` | 71 | 4,956 | $3.49 | mostly-clean |
| Greek yogurt | `breakfast.greek_yogurt` | 68 | 6,963 | $3.99 | mostly-clean |
| Spinach | `side.spinach` | 64 | 4,376 | $5.99 | mostly-clean |
| Broccoli | `side.broccoli` | 63 | 6,327 | $8.99 | mostly-clean |
| Ribeye steak | `dinner.ribeye` | 62 | 2,289 | $13.69 | mostly-clean |
| Salmon fillet | `dinner.salmon` | 61 | 4,149 | $10.99 | mostly-clean |
| Pork chops | `dinner.pork_chop` | 58 | 1,429 | $5.99 | CLEAN |
| Salsa | `pantry.salsa` | 55 | 3,906 | $4.99 | CLEAN |
| Green beans | `side.green_beans` | 54 | 2,284 | $2.69 | CLEAN |
| Block cheddar | `dairy.block_cheddar` | 52 | 4,722 | $5.75 | mostly-clean |
| Tortilla chips | `snack.tortilla_chips` | 51 | 2,656 | $4.79 | CLEAN |
| Pork loin / tenderloin | `dinner.pork_loin` | 51 | 1,634 | $4.48 | CLEAN |
| Bottled water (case) | `bev.bottled_water` | 50 | 1,415 | $3.33 | mostly-clean |
| Olive oil | `pantry.olive_oil` | 49 | 2,864 | $6.99 | CLEAN |
| Bagels | `breakfast.bagel` | 49 | 2,547 | $4.99 | CLEAN |
| Breakfast sausage | `breakfast.breakfast_sausage` | 48 | 4,200 | $5.99 | CLEAN |
| Cold cereal (generic) | `breakfast.cold_cereal_generic` | 47 | 3,495 | $4.99 | CLEAN |
| Sour cream | `dairy.sour_cream` | 47 | 3,370 | $5.50 | CLEAN |
| Chicken thighs | `dinner.bone_in_chicken_thigh` | 47 | 1,504 | $8.60 | CLEAN |
| Black beans (canned) | `pantry.black_beans` | 45 | 2,071 | $4.29 | CLEAN |
| Strip steak | `dinner.strip_steak` | 45 | 1,328 | $16.99 | CLEAN |
| Shredded cheese | `dairy.shredded_cheese` | 36 | 1,674 | $3.59 | CLEAN |
| Hot dog / hamburger buns | `bread.hot_dog_bun` | 35 | 781 | $3.49 | CLEAN |
| Whole chicken | `dinner.whole_chicken` | 34 | 434 | $5.99 | CLEAN |
| Frozen french fries | `frozen.frozen_french_fries` | 31 | 2,047 | $28.99 | CLEAN |
| Tomato sauce / paste | `pantry.tomato_sauce` | 29 | 1,016 | $1.49 | CLEAN |
| Canola / vegetable oil | `pantry.canola_oil` | 26 | 1,301 | $3.99 | CLEAN |
| Granola bars | `snack.granola_bars` | 24 | 977 | $11.99 | CLEAN |
| Sports drink | `bev.gatorade` | 23 | 1,035 | $8.59 | CLEAN |
| Chickpeas / garbanzo | `pantry.chickpeas` | 23 | 631 | $3.49 | CLEAN |
| Domestic beer (12-pack) | `bev.beer_domestic` | 23 | 481 | $14.99 | CLEAN |
| Canned diced tomatoes | `pantry.diced_tomato` | 17 | 852 | $1.55 | CLEAN |
| Frozen vegetables (mixed) | `frozen.frozen_vegetables` | 17 | 157 | $3.19 | mostly-clean |

### LEAKY items -- DO NOT USE without tightening

| Item | Theme key | What leaks in | Recommended fix |
|---|---|---|---|
| Sandwich bread (any) | `bread.bread_loaf_generic` | garlic bread, breadcrumbs, breadsticks, dip bowls | Restrict to `^bread$|sandwich bread|loaf|wheat bread|white bread`; require category=Bread & Bakery. |
| Strawberries | `side.strawberries` | strawberry-flavored beverages, snacks, sparkling water, candy | Restrict to category=Produce, or require fresh-produce keywords (e.g. `\bpint\b|\bclamshell\b|\b1\s*lb\b`) near the match. |
| Blueberries | `side.blueberries` | blueberry granola bars, lemonade, toothpaste | Restrict to category=Produce, or require fresh-produce keywords near the match. |
| Bananas | `breakfast.banana` | strawberry-banana drinks, banana-flavored snacks, banana-cake decor | Restrict to category=Produce. |
| Frozen pizza | `frozen.frozen_pizza` | refrigerated pizza, pizza-flavored cheese blends, pizza-themed sides | Require `frozen` token within 5 words of `pizza`, or restrict to category=Frozen Foods. |
| Tortillas | `bread.tortilla` | tortilla chips dominate over tortilla wraps | Split into two themes: `(?<!corn\s)tortilla(?!\s*chip)` for wraps and `tortilla\s*chip` for chips. |

---

## Notes for the data-quality agent

1. **Verify replacements before adoption.**  The replacements proposed above
   are the highest-coverage parquet items in the same conceptual role as a
   weak Karen item.  Before adopting any of them, please:
   - Inspect 50 random matched product names per replacement and confirm the
     match rate is acceptable for the Karen role.
   - Check that the substitute's price level is plausible relative to the
     original (e.g., generic deli turkey should be cheaper than Boar's Head;
     if our parquet's "deli turkey" candidate is dominated by Boar's Head
     products, that's not actually a substitute, just a relabel).

2. **Supplements are additive, not destructive.**  If you're uncertain about
   a supplement, it's safe to skip it.  None of the supplements above are
   required for Karen's existing index to work.

3. **The blank-unit problem is upstream.**  Many items here show
   `unit_homogeneity` below 50% because chains expose a blank `unit` field.
   This is a parquet-level issue affecting both the original Karen items and
   the adjacent items.  Fixing it would require enriching `unit` from
   `package_size_raw` parsing, which is out of scope for basket selection.

4. **All counts are 2020-2025 non-sale only.**  Adding 2019 or 2026 coverage
   would increase row counts but is irrelevant for the 2020-2025 inflation
   index.

5. **Companion artefacts you can pull from:**
   - `analysis/sandbox/karens_basket_perturbation/qc_table.csv` -- same QC
     stats but for the *original* 60 Karen items.  Useful for deciding
     which Karen items most need replacement.
   - `analysis/sandbox/karens_basket_perturbation/perturbed_baskets.csv` --
     the assembled Karen-Lean / Karen-Robust / Karen-Broad basket
     definitions in machine-readable form.
   - `analysis/sandbox/karens_basket_perturbation/sample_matches.csv` --
     top 10 matched product names per *Karen* item (helps identify leakage
     in the original basket).
   - `analysis/sandbox/karens_basket_perturbation/build_qc.py` -- the
     mining script.  Re-run it if the parquet is updated.

---

## Provenance

- All coverage stats in this file are derived directly from
  `data/pricing.parquet` filtered to `2020 <= year <= 2025` and
  `sale == False`.
- Pattern-leakage ratings were assigned by manual inspection of the top
  5-10 matched product names per theme (column `top_examples` in
  `candidate_substitutes.csv`).  They are *not* the result of a classifier
  or annotated test set.
- For full methodology, see `analysis/karens_basket_perturbation.Rmd` and
  the rendered `analysis/karens_basket_perturbation.html`.
