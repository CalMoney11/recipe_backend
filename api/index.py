"""
Vercel Python Serverless Function for Ingredient Analyzer
File: api/index.py
"""
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse
import json
import os
import sys

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Global variables for lazy loading
_analyzer = None
_init_error = None

def get_analyzer():
    """Lazy load the analyzer to catch initialization errors."""
    global _analyzer, _init_error
    
    if _analyzer is not None:
        return _analyzer
    
    if _init_error is not None:
        raise Exception(f"Analyzer failed to initialize: {_init_error}")
    
    try:
        from analyzer import IngredientAnalyzer
        _analyzer = IngredientAnalyzer()
        return _analyzer
    except Exception as e:
        _init_error = str(e)
        raise Exception(f"Failed to initialize analyzer: {e}")

class handler(BaseHTTPRequestHandler):
    """Vercel serverless handler."""
    
    def _set_cors_headers(self):
        """Set CORS headers for all responses."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-Type', 'application/json')
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path.replace('/api', '') or '/'
        
        # Health check endpoint
        if path == '/health':
            self.send_response(200)
            self._set_cors_headers()
            self.end_headers()
            
            response = {
                "status": "ok",
                "message": "Backend is running",
                "path": self.path
            }
            self.wfile.write(json.dumps(response).encode())
            return
        
        # 404 for other GET requests
        self.send_response(404)
        self._set_cors_headers()
        self.end_headers()
        
        response = {
            "error": "Not found",
            "path": path,
            "available_endpoints": ["/api/health", "/api/analyze", "/api/get_recipes"]
        }
        self.wfile.write(json.dumps(response).encode())
    
    def do_POST(self):
        """Handle POST requests."""
        parsed = urlparse(self.path)
        path = parsed.path.replace('/api', '') or '/'
        
        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b''
        
        try:
            # Analyze endpoint
            if path == '/analyze':
                response = self._handle_analyze(body)
            
            # Get recipes endpoint
            elif path == '/get_recipes':
                response = self._handle_get_recipes(body)
            
            else:
                self.send_response(404)
                self._set_cors_headers()
                self.end_headers()
                response = {"error": "Endpoint not found"}
                self.wfile.write(json.dumps(response).encode())
                return
            
            # Send successful response
            self.send_response(200)
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            # Send error response
            self.send_response(500)
            self._set_cors_headers()
            self.end_headers()
            
            error_response = {
                "success": False,
                "error": str(e),
                "type": type(e).__name__
            }
            self.wfile.write(json.dumps(error_response).encode())
    
    def _handle_analyze(self, body):
        """Handle /api/analyze endpoint."""
        try:
            analyzer = get_analyzer()
        except Exception as e:
            return {
                "success": False,
                "error": f"Analyzer initialization failed: {str(e)}"
            }
        
        # Parse multipart form data (simplified - only handles prompt for now)
        # For full image support, you'd need a proper multipart parser
        prompt = ""
        
        try:
            # Try to parse as JSON first
            data = json.loads(body.decode('utf-8'))
            prompt = data.get('prompt', '')
        except:
            # If not JSON, try to extract prompt from form data
            body_str = body.decode('utf-8')
            if 'prompt=' in body_str:
                for part in body_str.split('&'):
                    if part.startswith('prompt='):
                        prompt = part.split('=', 1)[1]
                        break
        
        # Analyze (without image for now - will add image support next)
        ingredients_list = analyzer.analyze(image_path=None, prompt=prompt)
        
        return {
            "success": True,
            "ingredients": ingredients_list
        }
    
    def _handle_get_recipes(self, body):
        """Handle /api/get_recipes endpoint."""
        try:
            analyzer = get_analyzer()
        except Exception as e:
            return {
                "success": False,
                "error": f"Analyzer initialization failed: {str(e)}"
            }
        
        # Get stored ingredients
        ingredients = analyzer.get_stored_ingredients()
        
        if not ingredients:
            return {
                "success": False,
                "error": "No ingredients found. Please analyze ingredients first."
            }
        
        # Import recipe functions
        from i_to_rec3 import load_recipes_from_kaggle, find_valid_recipes
        
        # Load recipes
        df = load_recipes_from_kaggle()
        valid_recipes = find_valid_recipes(df, ingredients)
        
        if not valid_recipes:
            return {
                "success": True,
                "ingredients": ingredients,
                "recipes": [],
                "total_found": 0,
                "message": "No recipes found matching your ingredients."
            }
        
        # Filter top recipes
        top_recipes = analyzer.filter_top_recipes(ingredients, valid_recipes, top_n=5)
        
        return {
            "success": True,
            "ingredients": ingredients,
            "recipes": top_recipes,
            "total_found": len(valid_recipes)
        }