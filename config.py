# Configuration settings for the Ingredient Analyzer.
import os

# Gemini API Configuration
# Read directly from OS environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Application Settings
DEBUG = os.getenv("DEBUG", "False").lower() == "true"