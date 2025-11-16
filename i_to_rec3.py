import os
import ast
import pandas as pd

# -----------------------------
#  KAGGLE CONFIG & AUTH
# -----------------------------
# Ensure kaggle.json is in same folder as this script
os.environ.setdefault('KAGGLE_CONFIG_DIR', os.path.dirname(__file__))

config_dir = os.environ.get('KAGGLE_CONFIG_DIR', os.path.expanduser('~/.kaggle'))
kaggle_json_path = os.path.join(config_dir, 'kaggle.json')

if not os.path.exists(kaggle_json_path):
    raise FileNotFoundError(
        f"kaggle.json not found at {kaggle_json_path}.\n"
        "Place kaggle.json in the same folder as this script."
    )

import kaggle


# -----------------------------
#  DOWNLOAD + LOAD DATASET
# -----------------------------
def load_recipes_from_kaggle():
    os.makedirs("data", exist_ok=True)

    print("Downloading dataset from Kaggle...")
    kaggle.api.dataset_download_files(
        "irkaal/foodcom-recipes-and-reviews",
        path="data",
        unzip=True
    )
    print("Download complete!")

    # The dataset contains multiple files. We want recipes.csv
    recipes_path = os.path.join("data", "recipes.csv")

    if not os.path.exists(recipes_path):
        raise FileNotFoundError("recipes.csv not found in downloaded dataset.")

    print("Loading recipes.csv into memory...")
    df = pd.read_csv(recipes_path)

    print(f"Loaded {len(df)} total recipes.")
    return df


# -----------------------------
#  NORMALIZE INGREDIENT STRINGS
# -----------------------------
def normalize_ingredient(i: str):
    if not isinstance(i, str):
        return None

    i = i.lower()

    remove_words = [
        "fresh", "organic", "large", "small", "raw",
        "diced", "chopped", "sliced", "minced",
        "tablespoon", "teaspoon", "cup", "cups", "tsp", "tbsp"
    ]
    for w in remove_words:
        i = i.replace(w, "")

    # Remove punctuation
    for ch in ",()[]{}":
        i = i.replace(ch, " ")

    return i.strip()


# -----------------------------
#  FILTER RECIPES BY INGREDIENTS
# -----------------------------
def find_valid_recipes(df, input_ingredients):
    """
    input_ingredients = list of ingredients the user has.
    Recipe is valid only if:
      - recipeingredientparts starts with 'c('
      - can be parsed as a list
      - none of the values are 'character(0)'
      - all recipe ingredients ⊆ input_ingredients
    """
    print("Filtering recipes...")

    normalized_input = {normalize_ingredient(i) for i in input_ingredients}

    valid_recipes = []

    for _, row in df.iterrows():

        raw = row.get("RecipeIngredientParts")
        title = row.get("Name", "Untitled Recipe")

        # Skip missing or invalid
        if not isinstance(raw, str):
            continue
        if not raw.startswith("c("):
            continue
        if "character(0)" in raw.lower():
            continue

        # Convert R format c("milk","eggs") -> Python list
        try:
            python_list_str = raw.replace("c(", "[").replace(")", "]")
            ingredients = ast.literal_eval(python_list_str)
            if not isinstance(ingredients, list):
                continue
        except Exception:
            continue

        # Normalize ingredients
        normalized_recipe_ingredients = {normalize_ingredient(i) for i in ingredients}
        normalized_recipe_ingredients = {i for i in normalized_recipe_ingredients if i}

        # Check if ALL ingredients are in user list
        if normalized_recipe_ingredients.issubset(normalized_input):
            valid_recipes.append({
                "title": title,
                "ingredients": ingredients
            })

    print(f"Found {len(valid_recipes)} matching recipes.")
    return valid_recipes


# -----------------------------
#  MAIN EXECUTION
# -----------------------------
if __name__ == "__main__":
    # Hard-coded ingredients for now
    user_ingredients = ["eggs", "milk", "flour", "sugar", "butter"]

    # Step 1 — Load dataset directly from Kaggle
    df = load_recipes_from_kaggle()

    # Step 2 — Filter matching recipes
    matches = find_valid_recipes(df, user_ingredients)

    # Step 3 — Print results
    print("\n=== VALID RECIPES ===\n")
    for r in matches:
        print(f"- {r['title']}  |  Ingredients: {r['ingredients']}")
