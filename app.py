"""
Flask API for Ingredient Analyzer.
Handles image uploads and prompt submissions from the frontend and calls the
`IngredientAnalyzer` in `analyzer.py` to perform analysis.
"""
import os
from uuid import uuid4
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

from analyzer import IngredientAnalyzer

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Configure Flask
app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')
# 🎯 FIX 1: Explicitly configure CORS to allow all origins globally (for local dev/Cloud Run)
CORS(app, resources={r"/*": {"origins": "*"}})

analyzer = IngredientAnalyzer()


## --- Frontend Serving Routes ---
@app.route("/", methods=["GET"])
def index():
    """Serve the existing `index.html` from the project root."""
    return send_from_directory(BASE_DIR, "index.html")

# 🎯 FIX 2: Add a route to serve the script.js file directly
@app.route("/script.js", methods=["GET"])
def serve_script():
    """Serve the script.js file from the project root."""
    return send_from_directory(BASE_DIR, "script.js")

# 🎯 FIX 3: Add a route to serve the entire images folder
@app.route("/images/<path:filename>", methods=["GET"])
def serve_images(filename):
    """Serve files (like moon.png/sun.png) from the 'images' sub-directory."""
    # Note: BASE_DIR is your project root, 'images' is the subdirectory
    return send_from_directory(os.path.join(BASE_DIR, 'images'), filename)


## --- API Endpoints ---
@app.route("/analyze", methods=["POST"])
def analyze():
    """
    Accepts multipart form-data with optional `image` file and optional `prompt` text.
    Performs ingredient analysis and returns the analysis result.
    """
    try:
        image = request.files.get("image")
        prompt = request.form.get("prompt", "")

        image_path = None
        if image and image.filename:
            filename = secure_filename(image.filename)
            unique_name = f"{uuid4().hex}_{filename}"
            image_path = os.path.join(UPLOAD_DIR, unique_name)
            image.save(image_path)

        # Call the analyzer
        ingredients_list = analyzer.analyze(image_path=image_path, prompt=prompt)

        # Cleanup temporary file
        if image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
            except Exception:
                pass # Fail silently on cleanup

        return jsonify({"success": True, "ingredients": ingredients_list})
    except Exception as e:
        # Include detailed error logging for easier debugging
        print(f"Error during /analyze: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/get_recipes', methods=['POST'])
def get_recipes():
    """
    Get recipes based on provided ingredients list.
    """
    try:
        data = request.get_json()
        ingredients = data.get('ingredients', [])
        
        if not ingredients:
            return jsonify({
                "success": False, 
                "error": "No ingredients provided."
            }), 400
        
        print(f"Generating recipes using {len(ingredients)} ingredients: {ingredients}")
        
        generated_recipes = analyzer.generate_recipes(ingredients, num_recipes=5)
        
        return jsonify({
            "success": True,
            "ingredients": ingredients,
            "recipes": generated_recipes,
            "total_found": len(generated_recipes)
        })
        
    except Exception as e:
        print(f"Error in get_recipes: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    # Run dev server: use the venv python and run `python app.py`.
    # Setting host='0.0.0.0' is useful for Docker/Cloud Run local testing
    app.run(host='127.0.0.1', port=5000)