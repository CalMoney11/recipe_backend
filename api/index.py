"""
Vercel serverless function for Ingredient Analyzer API.
Handles analyze and get_recipes endpoints.
"""
import os
import json
from werkzeug.datastructures import FileStorage
from io import BytesIO

# Import your existing modules
from analyzer import IngredientAnalyzer
from i_to_rec3 import load_recipes_from_kaggle, find_valid_recipes

# Initialize analyzer globally (will persist across warm invocations)
analyzer = IngredientAnalyzer()

def handler(request):
    """Main handler for Vercel serverless function."""
    
    # Add CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
    }
    
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    # Get the path
    path = request.path.replace('/api', '')
    
    # Health check endpoint
    if path == '/health' and request.method == 'GET':
        return {
            'statusCode': 200,
            'headers': {**headers, 'Content-Type': 'application/json'},
            'body': json.dumps({"status": "ok"})
        }
    
    # Analyze endpoint
    if path == '/analyze' and request.method == 'POST':
        try:
            # Get form data
            form = request.form
            files = request.files
            
            prompt = form.get('prompt', '')
            image_file = files.get('image')
            
            image_path = None
            if image_file:
                # Save temporarily
                temp_path = f"/tmp/{image_file.filename}"
                image_file.save(temp_path)
                image_path = temp_path
            
            # Analyze ingredients
            ingredients_list = analyzer.analyze(image_path=image_path, prompt=prompt)
            
            # Clean up temp file
            if image_path and os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except:
                    pass
            
            return {
                'statusCode': 200,
                'headers': {**headers, 'Content-Type': 'application/json'},
                'body': json.dumps({
                    "success": True,
                    "ingredients": ingredients_list
                })
            }
            
        except Exception as e:
            return {
                'statusCode': 500,
                'headers': {**headers, 'Content-Type': 'application/json'},
                'body': json.dumps({
                    "success": False,
                    "error": str(e)
                })
            }
    
    # Get recipes endpoint
    if path == '/get_recipes' and request.method == 'POST':
        try:
            # Get stored ingredients
            ingredients = analyzer.get_stored_ingredients()
            
            if not ingredients:
                return {
                    'statusCode': 400,
                    'headers': {**headers, 'Content-Type': 'application/json'},
                    'body': json.dumps({
                        "success": False,
                        "error": "No ingredients found. Please analyze ingredients first."
                    })
                }
            
            # Load and find recipes
            df = load_recipes_from_kaggle()
            valid_recipes = find_valid_recipes(df, ingredients)
            
            if not valid_recipes:
                return {
                    'statusCode': 200,
                    'headers': {**headers, 'Content-Type': 'application/json'},
                    'body': json.dumps({
                        "success": True,
                        "ingredients": ingredients,
                        "recipes": [],
                        "total_found": 0,
                        "message": "No recipes found matching your ingredients."
                    })
                }
            
            # Filter top recipes
            top_recipes = analyzer.filter_top_recipes(ingredients, valid_recipes, top_n=5)
            
            return {
                'statusCode': 200,
                'headers': {**headers, 'Content-Type': 'application/json'},
                'body': json.dumps({
                    "success": True,
                    "ingredients": ingredients,
                    "recipes": top_recipes,
                    "total_found": len(valid_recipes)
                })
            }
            
        except Exception as e:
            return {
                'statusCode': 500,
                'headers': {**headers, 'Content-Type': 'application/json'},
                'body': json.dumps({
                    "success": False,
                    "error": str(e)
                })
            }
    
    # 404 for unknown routes
    return {
        'statusCode': 404,
        'headers': {**headers, 'Content-Type': 'application/json'},
        'body': json.dumps({"error": "Not found"})
    }