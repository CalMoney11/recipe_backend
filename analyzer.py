"""
Image and prompt analyzer for ingredient analysis and recipe generation.
Handles image processing, prompt-based ingredient detection, and recipe generation 
using the Google Gemini API.
"""

from typing import Optional
import json
import google.generativeai as genai
# Assuming 'config' exists and contains GEMINI_API_KEY and GEMINI_MODEL
from config import GEMINI_API_KEY, GEMINI_MODEL 
# The second import of json is redundant, removed below.


class IngredientAnalyzer:
    """Analyzes ingredients from images/prompts and generates recipes using Google Gemini API."""

    def __init__(self):
        """Initialize the IngredientAnalyzer with Gemini API."""
        if not GEMINI_API_KEY:
            # Note: For Cloud Run deployment, this should be set as an environment variable, 
            # and the .env file reliance should be removed from config.py.
            raise ValueError("GEMINI_API_KEY environment variable not set. Please configure it.")
        
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(GEMINI_MODEL)
        self.vision_model = genai.GenerativeModel(GEMINI_MODEL) # Use a specific model if needed, or stick to the main model
        self.ingredients_list = []  # Store the last analyzed ingredients

    # ----------------------------------------------------------------------
    # Ingredient Analysis Methods (analyze_image, analyze_prompt, analyze)
    # These methods remain unchanged from your original request.
    # ----------------------------------------------------------------------
    
    def analyze_image(self, image_path: str) -> list:
        """
        Analyze an image to detect ingredients.
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
            
            # Clean up the image file after use
            genai.delete_file(image_file.name)
            
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
        """
        return self.ingredients_list
    
    # ----------------------------------------------------------------------
    # NEW: Recipe Generation Method (Replaces filter_top_recipes)
    # ----------------------------------------------------------------------

    def generate_recipes(self, ingredients: list, num_recipes: int = 5) -> list:
        """
        Use Gemini to generate a list of N recipes based on the available ingredients.
        
        Args:
            ingredients: List of available ingredient names
            num_recipes: Number of recipes to generate
            
        Returns:
            List of generated recipe dictionaries (title, ingredients, instructions)
        """
        try:
            available_ingredients = ', '.join(ingredients)
            
            # Use a robust system instruction for structured output
            system_prompt = f"""You are a professional chef and recipe generator. Your task is to generate {num_recipes} creative and practical recipes using the available ingredients provided by the user.

            For each recipe, you must provide:
            1. 'title': A creative and appealing title.
            2. 'ingredients': A list of all ingredients required (including quantity/unit).
            3. 'instructions': A list of step-by-step cooking instructions.

            Return ONLY a JSON array of recipe objects. The structure must be:
            [
              {{
                "title": "Recipe Title 1",
                "ingredients": ["1 cup ingredient A", "2 tbsp ingredient B", ...],
                "instructions": ["Step 1", "Step 2", ...]
              }},
              {{
                "title": "Recipe Title 2",
                "ingredients": ["...", ...],
                "instructions": ["...", ...]
              }}
            ]
            Do not include any pre-amble, explanation, or text outside of the JSON array."""

            # Create user prompt
            user_prompt = f"Generate {num_recipes} recipes using these available ingredients: {available_ingredients}"

            # Generate response
            response = self.model.generate_content(
                contents=user_prompt, 
                system_instruction=system_prompt
            )
            
            # Parse the JSON response
            raw_text = response.text.strip()
            
            # Clean up the response text (sometimes models wrap JSON in ```json)
            if raw_text.startswith('```json'):
                raw_text = raw_text.strip('`json').strip('`')
            
            recipes_list = json.loads(raw_text)
            
            # Ensure the output is a list before returning
            return recipes_list if isinstance(recipes_list, list) else []
            
        except Exception as e:
            print(f"Recipe generation error: {e}. Returning empty list.")
            return []

    # The old filter_top_recipes method is REMOVED
    
    def run(self):
        """Run the analyzer with interactive mode or default behavior."""
        print("Ingredient Analyzer initialized and ready to analyze!")
        print(f"Using Gemini model: {GEMINI_MODEL}")
        
        # TODO: Implement interactive CLI or API mode


if __name__ == "__main__":
    analyzer = IngredientAnalyzer()
    analyzer.run()