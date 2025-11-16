"""
Main entry point for the Ingredient Analyzer application.
"""

from analyzer import IngredientAnalyzer


def main():
    """Main function to run the Ingredient Analyzer."""
    analyzer = IngredientAnalyzer()
    analyzer.run()


if __name__ == "__main__":
    main()
