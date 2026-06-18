# NHANES Meal Archetypes (August 2021-August 2023)

This note summarizes a first-pass meal-archetype extraction using NHANES/WWEIA Day 1 dietary recall data and NHANES demographics.

## What This Is

- Meal unit: one respondent, one day, one eating occasion
- Source files: NHANES demographics plus WWEIA individual foods
- Weighting: Day 1 dietary weight (`WTDRD1`)
- SES split: poverty-income ratio (`INDFMPIR`)
- Caveat: these are heuristic meal archetypes, so the `other` buckets are still broad

## Sample Sizes

| Group | Participants | Mean age |
|---|---:|---:|
| All Respondents | 6,679 | 42.3 |
| Higher SES (PIR >= 3) | 2,691 | 45.9 |
| Highest SES (PIR >= 5) | 1,436 | 46.1 |
| Lower SES (PIR < 1.3) | 1,432 | 35.4 |

## All Respondents

- Participants: 6,679
- Mean age: 42.3

### Breakfast

1. **other breakfast** - 30.7% weighted share; 1,790 participants
   - Typical groups: sweet_drink, sweet_baked, water, fruit
   - Typical foods: Doughnuts, sweet rolls, pastries, Eggs and omelets
2. **cereal or oatmeal breakfast** - 21.6% weighted share; 1,469 participants
   - Typical groups: milk_dairy_drink, cereal_oatmeal, fruit
   - Typical foods: Ready-to-eat cereal, higher sugar (>21.2g/100g), Milk, whole
3. **coffee-first breakfast** - 15.8% weighted share; 991 participants
   - Typical groups: condiment_fat, coffee_tea, milk_dairy_drink
   - Typical foods: Coffee, Cream and cream substitutes, Tea
4. **coffee and pastry breakfast** - 9.8% weighted share; 639 participants
   - Typical groups: condiment_fat, bread, coffee_tea, sweet_baked
   - Typical foods: Doughnuts, sweet rolls, pastries, Coffee
5. **breakfast sandwich or burrito** - 9.6% weighted share; 561 participants
   - Typical groups: sandwich, coffee_tea, water, condiment_fat
   - Typical foods: Egg/breakfast sandwiches, Coffee, Tap water
   - Remaining archetypes: 12.6% of breakfast weight

### Lunch

1. **other lunch** - 28.4% weighted share; 1,508 participants
   - Typical groups: sweet_drink, water, grain_starch, fruit
   - Typical foods: Bottled water, Pasta mixed dishes, excludes macaroni and cheese, Tap water
2. **sandwich lunch** - 28.3% weighted share; 1,506 participants
   - Typical groups: sandwich, condiment_fat, water
   - Typical foods: Deli and cured meat sandwiches, Mayonnaise, Peanut butter and jelly sandwiches, Cheese sandwiches
3. **plate lunch** - 10.9% weighted share; 573 participants
   - Typical groups: meat_poultry, grain_starch, vegetables
   - Typical foods: French fries and other fried white potatoes, Chicken patties, nuggets and tenders, Chicken
4. **mixed entree lunch** - 10.5% weighted share; 525 participants
   - Typical groups: mixed_main, grain_starch, water, sweet_drink
   - Typical foods: Poultry mixed dishes, Meat mixed dishes, Fried rice and lo/chow mein, Tap water
5. **salad lunch** - 7.1% weighted share; 376 participants
   - Typical groups: vegetables, condiment_fat, meat_poultry
   - Typical foods: Crackers, excludes saltines, Other vegetables and combinations, Chicken
   - Remaining archetypes: 14.7% of lunch weight

### Dinner

1. **other dinner** - 30.4% weighted share; 2,027 participants
   - Typical groups: grain_starch, sweet_baked, water, meat_poultry
   - Typical foods: Pasta mixed dishes, excludes macaroni and cheese, Chicken, whole pieces
2. **mixed entree dinner** - 16.4% weighted share; 1,028 participants
   - Typical groups: mixed_main, water, grain_starch
   - Typical foods: Meat mixed dishes, Poultry mixed dishes, Fried rice and lo/chow mein, Pasta mixed dishes
3. **sandwich dinner** - 15.0% weighted share; 930 participants
   - Typical groups: sandwich, condiment_fat, sweet_drink
   - Typical foods: Egg/breakfast sandwiches, Peanut butter and jelly sandwiches, Meat and BBQ sandwiches, Mayonnaise
4. **protein vegetable starch dinner** - 9.4% weighted share; 637 participants
   - Typical groups: vegetables, grain_starch, meat_poultry
   - Typical foods: Macaroni and cheese, String beans, Chicken patties, nuggets and tenders
5. **protein and starch dinner** - 8.6% weighted share; 577 participants
   - Typical groups: grain_starch, meat_poultry, water, sweet_drink
   - Typical foods: Chicken patties, nuggets and tenders, French fries and other fried white potatoes, Rice
   - Remaining archetypes: 20.1% of dinner weight

### Snack

1. **other snack** - 37.0% weighted share; 2,811 participants
   - Typical groups: fruit, water, beans_nuts, sweet_drink
   - Typical foods: Nuts and seeds, Apples, Bananas, Citrus fruits
2. **sweet snack** - 35.8% weighted share; 2,920 participants
   - Typical groups: sweet_baked, water, sweet_drink
   - Typical foods: Candy not containing chocolate, Cookies and brownies, Candy containing chocolate, Ice cream and frozen dairy desserts
3. **salty snack** - 22.0% weighted share; 1,989 participants
   - Typical groups: salty_snack, water, sweet_baked
   - Typical foods: Tortilla, corn, other chips, Popcorn
4. **coffee or tea snack** - 3.0% weighted share; 295 participants
   - Typical groups: coffee_tea, condiment_fat, fruit
   - Typical foods: Tea, Coffee, Cream and cream substitutes
5. **sandwich snack** - 1.4% weighted share; 137 participants
   - Typical groups: sandwich, condiment_fat, water
   - Typical foods: Peanut butter and jelly sandwiches, Deli and cured meat sandwiches, Mayonnaise, Cheese sandwiches
   - Remaining archetypes: 0.9% of snack weight

## Higher SES (PIR >= 3)

- Participants: 2,691
- Mean age: 45.9

### Breakfast

1. **other breakfast** - 27.6% weighted share; 684 participants
   - Typical groups: sweet_drink, sweet_baked, fruit, water
   - Typical foods: Doughnuts, sweet rolls, pastries, Tap water
2. **cereal or oatmeal breakfast** - 22.0% weighted share; 643 participants
   - Typical groups: milk_dairy_drink, cereal_oatmeal, fruit
   - Typical foods: Milk, reduced fat, Ready-to-eat cereal, higher sugar (>21.2g/100g)
3. **coffee-first breakfast** - 17.8% weighted share; 484 participants
   - Typical groups: coffee_tea, condiment_fat, milk_dairy_drink
   - Typical foods: Coffee, Cream and cream substitutes, Tea
4. **coffee and pastry breakfast** - 10.3% weighted share; 289 participants
   - Typical groups: coffee_tea, sweet_baked, condiment_fat, bread
   - Typical foods: Doughnuts, sweet rolls, pastries, Coffee
5. **eggs with bread or meat** - 9.9% weighted share; 252 participants
   - Typical groups: condiment_fat, eggs, bread, coffee_tea
   - Typical foods: Yeast breads, Eggs and omelets, Butter and animal fats, Mustard and other condiments
   - Remaining archetypes: 12.4% of breakfast weight

### Lunch

1. **sandwich lunch** - 28.8% weighted share; 668 participants
   - Typical groups: sandwich, condiment_fat, water
   - Typical foods: Mayonnaise, Deli and cured meat sandwiches, Peanut butter and jelly sandwiches, Cheese sandwiches
2. **other lunch** - 27.7% weighted share; 619 participants
   - Typical groups: sweet_drink, grain_starch, sweet_baked, water
   - Typical foods: Pasta mixed dishes, excludes macaroni and cheese, Nutritional beverages, Tap water
3. **mixed entree lunch** - 11.1% weighted share; 243 participants
   - Typical groups: mixed_main, grain_starch, water, condiment_fat
   - Typical foods: Meat mixed dishes, Poultry mixed dishes, Seafood mixed dishes, Tap water
4. **plate lunch** - 9.7% weighted share; 219 participants
   - Typical groups: meat_poultry, vegetables, grain_starch, condiment_fat
   - Typical foods: Chicken, whole pieces, Rice mixed dishes, Tomato-based condiments
5. **salad lunch** - 8.6% weighted share; 217 participants
   - Typical groups: condiment_fat, vegetables, meat_poultry, water
   - Typical foods: Crackers, excludes saltines, Other vegetables and combinations, Chicken
   - Remaining archetypes: 14.2% of lunch weight

### Dinner

1. **other dinner** - 29.7% weighted share; 811 participants
   - Typical groups: sweet_baked, grain_starch, alcohol, fruit
   - Typical foods: Pasta mixed dishes, excludes macaroni and cheese, Cakes and pies, Beer
2. **mixed entree dinner** - 19.2% weighted share; 480 participants
   - Typical groups: mixed_main, water, grain_starch
   - Typical foods: Meat mixed dishes, Fried rice and lo/chow mein, Stir-fry and soy-based sauce mixtures, Rice
3. **sandwich dinner** - 14.5% weighted share; 366 participants
   - Typical groups: sandwich, sweet_drink, condiment_fat
   - Typical foods: Meat and BBQ sandwiches, Egg/breakfast sandwiches, Peanut butter and jelly sandwiches, Mayonnaise
4. **protein vegetable starch dinner** - 10.6% weighted share; 308 participants
   - Typical groups: meat_poultry, vegetables, grain_starch, condiment_fat
   - Typical foods: Not included in a food category, Mashed potatoes and white potato mixtures, Wine, Other vegetables and combinations
5. **protein and starch dinner** - 7.5% weighted share; 188 participants
   - Typical groups: grain_starch, meat_poultry, water
   - Typical foods: Rice, Beans, peas, legumes
   - Remaining archetypes: 18.6% of dinner weight

### Snack

1. **other snack** - 37.1% weighted share; 1,171 participants
   - Typical groups: fruit, beans_nuts, water, sweet_drink
   - Typical foods: Nuts and seeds, Apples, Bananas, Cheese
2. **sweet snack** - 35.6% weighted share; 1,229 participants
   - Typical groups: sweet_baked, water, coffee_tea
   - Typical foods: Candy containing chocolate, Candy not containing chocolate, Cookies and brownies, Ice cream and frozen dairy desserts
3. **salty snack** - 21.7% weighted share; 821 participants
   - Typical groups: salty_snack, water, sweet_baked
   - Typical foods: Crackers, excludes saltines, Tortilla, corn
4. **coffee or tea snack** - 3.6% weighted share; 145 participants
   - Typical groups: coffee_tea, condiment_fat, beans_nuts
   - Typical foods: Coffee, Tea, Cream and cream substitutes, Nuts and seeds
5. **fruit and dairy snack** - 1.0% weighted share; 43 participants
   - Typical groups: cheese, fruit, yogurt
   - Typical foods: Apples, Cheese, Bananas, Yogurt
   - Remaining archetypes: 1.0% of snack weight

## Highest SES (PIR >= 5)

- Participants: 1,436
- Mean age: 46.1

### Breakfast

1. **other breakfast** - 26.0% weighted share; 353 participants
   - Typical groups: sweet_drink, sweet_baked, fruit, water
   - Typical foods: Tap water, Smoothies and grain drinks, Eggs and omelets, Nutritional beverages
2. **cereal or oatmeal breakfast** - 23.7% weighted share; 364 participants
   - Typical groups: milk_dairy_drink, cereal_oatmeal, coffee_tea
   - Typical foods: Ready-to-eat cereal, higher sugar (>21.2g/100g), Milk, whole
3. **coffee-first breakfast** - 18.0% weighted share; 266 participants
   - Typical groups: coffee_tea, condiment_fat, milk_dairy_drink
   - Typical foods: Coffee, Cream and cream substitutes, Tea
4. **coffee and pastry breakfast** - 10.5% weighted share; 160 participants
   - Typical groups: coffee_tea, sweet_baked, condiment_fat, bread
   - Typical foods: Yeast breads, Coffee, Butter and animal fats, Biscuits
5. **eggs with bread or meat** - 10.2% weighted share; 140 participants
   - Typical groups: sweet_drink, eggs, breakfast_meat, condiment_fat
   - Typical foods: Eggs and omelets, Yeast breads, Mustard and other condiments, Bagels and English muffins
   - Remaining archetypes: 11.7% of breakfast weight

### Lunch

1. **sandwich lunch** - 29.3% weighted share; 359 participants
   - Typical groups: sandwich, condiment_fat, vegetables
   - Typical foods: Peanut butter and jelly sandwiches, Deli and cured meat sandwiches, Cheese sandwiches, Mayonnaise
2. **other lunch** - 26.9% weighted share; 341 participants
   - Typical groups: sweet_drink, grain_starch, sweet_baked, fruit
   - Typical foods: Pasta mixed dishes, excludes macaroni and cheese, Smoothies and grain drinks, Nutritional beverages
3. **mixed entree lunch** - 12.1% weighted share; 139 participants
   - Typical groups: mixed_main, grain_starch, condiment_fat, sweet_drink
   - Typical foods: Meat mixed dishes, Poultry mixed dishes, Rice, Tap water
4. **salad lunch** - 9.5% weighted share; 131 participants
   - Typical groups: meat_poultry, condiment_fat, vegetables, water
   - Typical foods: Crackers, excludes saltines, Other vegetables and combinations, Chicken
5. **plate lunch** - 8.7% weighted share; 103 participants
   - Typical groups: meat_poultry, vegetables, sweet_drink, grain_starch
   - Typical foods: Rice mixed dishes, Tea, Chicken, whole pieces
   - Remaining archetypes: 13.6% of lunch weight

### Dinner

1. **other dinner** - 28.7% weighted share; 421 participants
   - Typical groups: grain_starch, sweet_baked, alcohol, meat_poultry
   - Typical foods: Pasta mixed dishes, excludes macaroni and cheese, Cakes and pies, Cookies and brownies
2. **mixed entree dinner** - 21.4% weighted share; 280 participants
   - Typical groups: mixed_main, water, cheese, grain_starch
   - Typical foods: Meat mixed dishes, Fried rice and lo/chow mein, Cheese, Pasta mixed dishes
3. **sandwich dinner** - 12.8% weighted share; 167 participants
   - Typical groups: sandwich, condiment_fat, vegetables, grain_starch
   - Typical foods: Egg/breakfast sandwiches, Meat and BBQ sandwiches, Seafood sandwiches, Mayonnaise
4. **protein vegetable starch dinner** - 11.5% weighted share; 183 participants
   - Typical groups: vegetables, grain_starch, meat_poultry, seafood
   - Typical foods: Not included in a food category, Mashed potatoes and white potato mixtures, Wine, Other vegetables and combinations
5. **protein and starch dinner** - 7.3% weighted share; 102 participants
   - Typical groups: grain_starch, meat_poultry, water, seafood
   - Typical foods: Rice, Beans, peas, legumes
   - Remaining archetypes: 18.3% of dinner weight

### Snack

1. **other snack** - 36.8% weighted share; 629 participants
   - Typical groups: fruit, beans_nuts, water, sweet_drink
   - Typical foods: Nuts and seeds, Apples, Bananas, Citrus fruits
2. **sweet snack** - 34.9% weighted share; 640 participants
   - Typical groups: sweet_baked, water, coffee_tea
   - Typical foods: Cookies and brownies, Candy containing chocolate, Candy not containing chocolate, Ice cream and frozen dairy desserts
3. **salty snack** - 22.4% weighted share; 450 participants
   - Typical groups: salty_snack, water, sweet_baked
   - Typical foods: Crackers, excludes saltines, Tortilla, corn
4. **coffee or tea snack** - 4.0% weighted share; 84 participants
   - Typical groups: coffee_tea, condiment_fat, fruit
   - Typical foods: Coffee, Tea, Nuts and seeds
5. **fruit and dairy snack** - 1.1% weighted share; 26 participants
   - Typical groups: fruit, cheese, yogurt, beans_nuts
   - Typical foods: Apples, Cheese, Bananas, Yogurt
   - Remaining archetypes: 0.7% of snack weight

## Lower SES (PIR < 1.3)

- Participants: 1,432
- Mean age: 35.4

### Breakfast

1. **other breakfast** - 32.8% weighted share; 392 participants
   - Typical groups: sweet_drink, water, fruit, sweet_baked
   - Typical foods: Eggs and omelets, Tap water, Bottled water, Bananas
2. **cereal or oatmeal breakfast** - 21.8% weighted share; 286 participants
   - Typical groups: milk_dairy_drink, cereal_oatmeal, water
   - Typical foods: Ready-to-eat cereal, higher sugar (>21.2g/100g), Milk, whole
3. **coffee-first breakfast** - 13.2% weighted share; 164 participants
   - Typical groups: coffee_tea, condiment_fat, water
   - Typical foods: Coffee, Cream and cream substitutes, Sugars and honey
4. **breakfast sandwich or burrito** - 10.9% weighted share; 129 participants
   - Typical groups: sandwich, sweet_drink, condiment_fat, coffee_tea
   - Typical foods: Egg/breakfast sandwiches, Deli and cured meat sandwiches, Coffee, Soft drinks
5. **eggs with bread or meat** - 9.7% weighted share; 125 participants
   - Typical groups: condiment_fat, coffee_tea, bread, eggs
   - Typical foods: Tortillas, Bottled water, Eggs and omelets, Yeast breads
   - Remaining archetypes: 11.6% of breakfast weight

### Lunch

1. **other lunch** - 30.6% weighted share; 323 participants
   - Typical groups: water, sweet_drink, grain_starch, fruit
   - Typical foods: Bottled water, Soft drinks, Macaroni and cheese, Apple juice
2. **sandwich lunch** - 26.4% weighted share; 266 participants
   - Typical groups: sandwich, condiment_fat, sweet_drink, water
   - Typical foods: Peanut butter and jelly sandwiches, Mayonnaise, Deli and cured meat sandwiches, Vegetables on a sandwich
3. **plate lunch** - 11.6% weighted share; 130 participants
   - Typical groups: vegetables, meat_poultry, grain_starch, water
   - Typical foods: French fries and other fried white potatoes, Chicken patties, nuggets and tenders, Rice
4. **mixed entree lunch** - 7.8% weighted share; 86 participants
   - Typical groups: mixed_main, water, grain_starch, sweet_drink
   - Typical foods: Meat mixed dishes, Poultry mixed dishes, Fried rice and lo/chow mein, Pasta
5. **tortilla lunch** - 6.9% weighted share; 56 participants
   - Typical groups: tortilla, water, vegetables, condiment_fat
   - Typical foods: Burritos and tacos, Other Mexican mixed dishes, Tomato-based condiments, Lettuce and lettuce salads
   - Remaining archetypes: 16.7% of lunch weight

### Dinner

1. **other dinner** - 30.8% weighted share; 442 participants
   - Typical groups: grain_starch, water, meat_poultry, sweet_baked
   - Typical foods: Pasta mixed dishes, excludes macaroni and cheese, Chicken, whole pieces
2. **mixed entree dinner** - 13.5% weighted share; 179 participants
   - Typical groups: mixed_main, water, grain_starch
   - Typical foods: Meat mixed dishes, Poultry mixed dishes, Cheese, Pasta mixed dishes
3. **sandwich dinner** - 13.4% weighted share; 194 participants
   - Typical groups: sandwich, condiment_fat, water, sweet_drink
   - Typical foods: Burgers, Peanut butter and jelly sandwiches, Soft drinks, French fries and other fried white potatoes
4. **protein and starch dinner** - 11.5% weighted share; 156 participants
   - Typical groups: meat_poultry, grain_starch, sweet_drink, coffee_tea
   - Typical foods: Rice, Pork, Chicken, whole pieces
5. **tortilla dinner** - 10.1% weighted share; 122 participants
   - Typical groups: tortilla, sweet_drink, water
   - Typical foods: Other Mexican mixed dishes, Burritos and tacos, Soft drinks, Fruit drinks
   - Remaining archetypes: 20.7% of dinner weight

### Snack

1. **other snack** - 39.8% weighted share; 593 participants
   - Typical groups: fruit, water, sweet_drink, beans_nuts
   - Typical foods: Bottled water, Apples, Nuts and seeds, Citrus fruits
2. **sweet snack** - 34.1% weighted share; 578 participants
   - Typical groups: sweet_baked, water, sweet_drink
   - Typical foods: Cookies and brownies, Candy not containing chocolate, Ice cream and frozen dairy desserts, Candy containing chocolate
3. **salty snack** - 20.9% weighted share; 408 participants
   - Typical groups: salty_snack, water, sweet_baked
   - Typical foods: Tortilla, corn, other chips, Potato chips
4. **coffee or tea snack** - 2.4% weighted share; 49 participants
   - Typical groups: coffee_tea, condiment_fat, cereal_oatmeal
   - Typical foods: Sugars and honey, Coffee, Tea
5. **sandwich snack** - 2.1% weighted share; 38 participants
   - Typical groups: sandwich, condiment_fat, sweet_drink
   - Typical foods: Peanut butter and jelly sandwiches, Cheese sandwiches, Butter and animal fats, Yeast breads
   - Remaining archetypes: 0.7% of snack weight