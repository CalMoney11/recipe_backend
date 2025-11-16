"""
Image and prompt analyzer for ingredient analysis.
Handles image processing and prompt-based ingredient detection using Gemini API.
"""

from typing import Optional
import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI_MODEL
import json


class IngredientAnalyzer:
    """Analyzes ingredients from images and prompts using Google Gemini API."""

    def __init__(self):
        """Initialize the IngredientAnalyzer with Gemini API."""
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable not set. Please configure it in .env file.")
        
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(GEMINI_MODEL)
        self.vision_model = genai.GenerativeModel(GEMINI_MODEL)
        self.ingredients_list = []  # Store the last analyzed ingredients

    def analyze_image(self, image_path: str) -> list:
        """
        Analyze an image to detect ingredients.

        Args:
            image_path: Path to the image file

        Returns:
            List of ingredient names as strings
        """
        try:
            # Upload image file
            image_file = genai.upload_file(image_path)
            
            # Create prompt for ingredient analysis - request JSON array
            prompt = """Analyze this image and identify all visible ingredients or food items. 
            Return ONLY a JSON array of ingredient names, like this:
            ["ingredient1", "ingredient2", "ingredient3"]
            
            Do not include any other text, explanations, or formatting. Just the JSON array of ingredient names."""
            
            # Generate response
            response = self.vision_model.generate_content([prompt, image_file])
            
            # Parse JSON response
            try:
                ingredients_list = json.loads(response.text.strip())
                return ingredients_list if isinstance(ingredients_list, list) else []
            except json.JSONDecodeError:
                # Fallback: return empty list if parsing fails
                print(f"Warning: Could not parse JSON from image analysis. Raw response: {response.text}")
                return []
        except Exception as e:
            print(f"Error analyzing image: {str(e)}")
            return []

    def analyze_prompt(self, prompt: str) -> list:
        """
        Analyze a text prompt to extract ingredient information.

        Args:
            prompt: Text prompt containing ingredient information

        Returns:
            List of ingredient names as strings
        """
        try:
            # Create system instruction for ingredient parsing - request JSON array
            system_prompt = """You are an ingredient parser. Extract all ingredients from the user's input.
            Return ONLY a JSON array of ingredient names, like this:
            ["ingredient1", "ingredient2", "ingredient3"]
            
            Do not include quantities, units, explanations, or any other text. Just the ingredient names in a JSON array."""
            
            # Generate response
            response = self.model.generate_content(system_prompt + "\n\nUser input: " + prompt)
            
            # Parse JSON response
            try:
                ingredients_list = json.loads(response.text.strip())
                return ingredients_list if isinstance(ingredients_list, list) else []
            except json.JSONDecodeError:
                # Fallback: return empty list if parsing fails
                print(f"Warning: Could not parse JSON from prompt analysis. Raw response: {response.text}")
                return []
        except Exception as e:
            print(f"Error analyzing prompt: {str(e)}")
            return []

    def analyze(self, image_path: Optional[str] = None, prompt: Optional[str] = None) -> list:
        """
        Analyze ingredients from either an image or prompt.

        Args:
            image_path: Optional path to an image file
            prompt: Optional text prompt

        Returns:
            Combined list of all detected ingredients (deduplicated)
        """
        all_ingredients = []

        if image_path:
            image_ingredients = self.analyze_image(image_path)
            all_ingredients.extend(image_ingredients)

        if prompt:
            prompt_ingredients = self.analyze_prompt(prompt)
            all_ingredients.extend(prompt_ingredients)

        # Remove duplicates while preserving order
        seen = set()
        unique_ingredients = []
        for ingredient in all_ingredients:
            ingredient_lower = ingredient.lower()
            if ingredient_lower not in seen:
                seen.add(ingredient_lower)
                unique_ingredients.append(ingredient)

        # Store the ingredients for later use
        self.ingredients_list = unique_ingredients

        return unique_ingredients
    
    def get_stored_ingredients(self) -> list:
        """
        Get the last analyzed ingredients list.
        
        Returns:
            List of ingredients from the last analysis
        """
        return self.ingredients_list
    
    def filter_top_recipes(self, ingredients: list, recipes: list, top_n: int = 5) -> list:
        """
        Use Gemini to rank and filter recipes based on ingredients.
        
        Args:
            ingredients: List of available ingredients
            recipes: List of recipe dictionaries with 'title' and 'ingredients' keys
            top_n: Number of top recipes to return (default 5)
            
        Returns:
            List of top N recipes ranked by Gemini
        """
        try:
            # Limit recipes to first 20 to avoid token limits
            recipes_subset = recipes[:20] if len(recipes) > 20 else recipes
            
            # Format recipes for prompt
            recipe_list = []
            for i, recipe in enumerate(recipes_subset):
                title = recipe.get('title', 'Untitled')
                recipe_ingredients = recipe.get('ingredients', [])
                ingredients_str = ', '.join(recipe_ingredients[:10])  # Limit to 10 ingredients shown
                recipe_list.append(f"{i}. {title}\n   Ingredients: {ingredients_str}")
            
            recipes_formatted = '\n\n'.join(recipe_list)
            
            # Create prompt for Gemini
            prompt = f"""Given these available ingredients: {', '.join(ingredients)}

And these recipe options:
{recipes_formatted}

Analyze each recipe and return ONLY a JSON array of the indices (0-based) of the top {top_n} recipes that:
1. Use the most available ingredients
2. Are most practical and appealing
3. Have good variety

Return ONLY the JSON array of indices, no other text. Example: [0, 3, 5, 7, 9]"""

            response = self.model.generate_content(prompt)
            
            # Parse the indices
            top_indices = json.loads(response.text.strip())
            
            # Return the filtered recipes
            filtered = []
            for i in top_indices:
                if i < len(recipes_subset):
                    filtered.append(recipes_subset[i])
                if len(filtered) >= top_n:
                    break
            
            return filtered
            
        except Exception as e:
            # Fallback: return first top_n recipes if filtering fails
            print(f"Recipe filtering error: {e}. Returning first {top_n} recipes.")
            return recipes[:top_n]

    def run(self):
        """Run the analyzer with interactive mode or default behavior."""
        print("Ingredient Analyzer initialized and ready to analyze!")
        print(f"Using Gemini model: {GEMINI_MODEL}")
        
        # TODO: Implement interactive CLI or API mode
        # Example usage:
        # 1. Image analysis: analyzer.analyze_image("path/to/image.jpg")
        # 2. Prompt analysis: analyzer.analyze_prompt("I have 2 cups of flour and 3 eggs")
        # 3. Combined: analyzer.analyze(image_path="...", prompt="...")


if __name__ == "__main__":
    analyzer = IngredientAnalyzer()
    analyzer.run()
