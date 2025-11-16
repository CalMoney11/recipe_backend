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

# Configure Flask to serve static files from the project root
app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')
CORS(app)

analyzer = IngredientAnalyzer()


@app.route("/", methods=["GET"])
def index():
    """Serve the existing `index.html` from the project root."""
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    """
    Accepts multipart form-data with optional `image` file and optional `prompt` text.
    Saves the uploaded image to `uploads/`, calls `IngredientAnalyzer.analyze`,
    and returns the analysis result as JSON.
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

        # Call the analyzer (now returns a list of ingredients)
        ingredients_list = analyzer.analyze(image_path=image_path, prompt=prompt)

        # Remove the temporary file after analysis to avoid storage buildup
        if image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
            except Exception:
                # Don't fail the request if cleanup fails
                pass

        return jsonify({"success": True, "ingredients": ingredients_list})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# Note: Serving uploaded files publicly is disabled in production for security.
# If you need to debug uploaded files locally, temporarily re-enable an endpoint
# or check the `uploads/` directory directly on the server.


@app.route('/get_recipes', methods=['POST'])
def get_recipes():
    """
    Get recipes based on stored ingredients list by asking Gemini to generate them.
    """
    try:
        # Get the stored ingredients from the analyzer
        ingredients = analyzer.get_stored_ingredients()
        
        if not ingredients:
            return jsonify({"success": False, "error": "No ingredients found. Please analyze ingredients first."}), 400
        
        print(f"Generating recipes using {len(ingredients)} ingredients...")
        
        # NEW: Call the Gemini generation method
        generated_recipes = analyzer.generate_recipes(ingredients, num_recipes=5)
        
        return jsonify({
            "success": True,
            "ingredients": ingredients,
            "recipes": generated_recipes,
            "total_found": len(generated_recipes) # Report how many were generated
        })
        
    except Exception as e:
        print(f"Error in get_recipes: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    # Run dev server: use the venv python and run `python app.py`.
    app.run()
