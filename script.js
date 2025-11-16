// --- Configuration ---
// PRODUCTION: Your Vercel backend URL
const API_URL = 'https://ingredient-analyzer-beta.vercel.app/api/analyze';
// LOCAL TESTING: Uncomment the line below when testing locally
// const API_URL = 'http://localhost:5000/analyze';

// --- Helper Functions ---

async function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = () => resolve(reader.result.split(',')[1]);
        reader.onerror = reject;
    });
}

function displayFileName(input) {
    const fileNameDisplay = document.getElementById('fileNameDisplay');
    const imageStatus = document.getElementById('imageStatus');
    const file = input.files[0];
    
    if (file) {
        fileNameDisplay.textContent = file.name;
        imageStatus.textContent = `File selected: ${file.name} (${(file.size / 1024).toFixed(2)} KB)`;
    } else {
        fileNameDisplay.textContent = 'Upload/Capture Photo';
        imageStatus.textContent = 'No image selected.';
    }
}

function simpleMarkdownToHtml(text) {
    return text
        // Headings
        .replace(/^### (.+)$/gm, '<h3 class="text-xl font-semibold mt-4 mb-2">$1</h3>')
        .replace(/^## (.+)$/gm, '<h2 class="text-2xl font-bold mt-6 mb-3 text-blue-800">$1</h2>')
        .replace(/^# (.+)$/gm, '<h1 class="text-3xl font-extrabold mt-8 mb-4">$1</h1>')
        // Lists
        .replace(/^\* (.+)$/gm, '<li class="ml-6">$1</li>')
        .replace(/(<li>.*<\/li>\n?)+/gs, '<ul class="list-disc my-2">$&</ul>')
        // Horizontal rules
        .replace(/^---$/gm, '<hr class="border-t-2 border-gray-200 my-6"/>')
        // Bold and italic
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        // Paragraphs (lines that aren't already wrapped)
        .split('\n')
        .map(line => line.trim() && !line.startsWith('<') ? `<p class="mb-2">${line}</p>` : line)
        .join('\n');
}

// Exponential backoff helper (optional, for rate limiting)
async function withExponentialBackoff(fn, maxRetries = 3) {
    for (let i = 0; i < maxRetries; i++) {
        try {
            return await fn();
        } catch (error) {
            if (i === maxRetries - 1) throw error;
            const delay = Math.pow(2, i) * 1000;
            await new Promise(resolve => setTimeout(resolve, delay));
        }
    }
}

// --- Main Function ---

async function getRecipes() {
    const prompt = document.getElementById('foodPrompt').value.trim();
    const imageInput = document.getElementById('imageInput');
    const imageFile = imageInput.files[0];
    const outputDiv = document.getElementById('recipeContent');
    const button = document.getElementById('recipeButton');
    const buttonText = document.getElementById('buttonText');

    // Validation
    if (!prompt && !imageFile) {
        outputDiv.innerHTML = '<p class="text-red-600 font-medium">⚠️ Please enter a prompt or upload an image.</p>';
        return;
    }

    // Set loading state
    button.disabled = true;
    buttonText.innerHTML = 'Analyzing<span class="loading-dot">.</span><span class="loading-dot">.</span><span class="loading-dot">.</span>';
    outputDiv.innerHTML = '<div class="text-center py-8"><p class="text-lg text-blue-600">🔍 Analyzing ingredients...</p></div>';

    // Prepare FormData for the backend
    const formData = new FormData();
    if (imageFile) {
        formData.append('image', imageFile);
    }
    if (prompt) {
        formData.append('prompt', prompt);
    }

    try {
        // Fetch from Vercel backend
        const response = await fetch(API_URL, {
            method: 'POST',
            body: formData
            // Note: Don't set Content-Type header - browser will set it automatically with boundary
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `Server error: ${response.status} ${response.statusText}`);
        }

        const result = await response.json();

        if (result.success && result.ingredients) {
            const ingredientsList = result.ingredients;
            
            if (ingredientsList.length === 0) {
                outputDiv.innerHTML = '<p class="text-yellow-600">No ingredients detected. Try a different image or prompt.</p>';
                return;
            }
            
            // Show detected ingredients
            const ingredientsHTML = ingredientsList.map(ingredient => 
                `<li class="py-2 px-3 bg-gray-50 rounded">${ingredient}</li>`
            ).join('');
            
            outputDiv.innerHTML = `
                <div class="space-y-4">
                    <h3 class="text-xl font-semibold text-gray-800">Detected Ingredients (${ingredientsList.length}):</h3>
                    <ul class="space-y-2">
                        ${ingredientsHTML}
                    </ul>
                    <p class="text-blue-600 font-medium">Finding recipes...</p>
                </div>
            `;
            
            // Now get recipes using those ingredients
            buttonText.innerHTML = 'Finding Recipes <span class="loading-dot"></span><span class="loading-dot"></span><span class="loading-dot"></span>';
            
            const recipesUrl = 'http://localhost:5000/get_recipes';
            const recipesResponse = await withExponentialBackoff(() =>
                fetch(recipesUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({})
                })
            );
            
            if (!recipesResponse.ok) {
                throw new Error(`Recipe fetch failed: ${recipesResponse.statusText}`);
            }
            
            const recipesResult = await recipesResponse.json();
            
            if (recipesResult.success && recipesResult.recipes) {
                const recipes = recipesResult.recipes;
                
                if (recipes.length === 0) {
                    outputDiv.innerHTML = `
                        <div class="space-y-4">
                            <h3 class="text-xl font-semibold text-gray-800">Detected Ingredients (${ingredientsList.length}):</h3>
                            <ul class="space-y-2">
                                ${ingredientsHTML}
                            </ul>
                            <p class="text-yellow-600 font-medium mt-4">No recipes found matching your ingredients. Try adding more common ingredients!</p>
                        </div>
                    `;
                } else {
                    // Display recipes
                    const recipesHTML = recipes.map((recipe, idx) => {
                        const recipeIngredients = recipe.ingredients || [];
                        const ingredientsListHTML = recipeIngredients.slice(0, 8).map(ing => 
                            `<li class="text-sm text-gray-600">• ${ing}</li>`
                        ).join('');
                        const moreCount = recipeIngredients.length > 8 ? recipeIngredients.length - 8 : 0;
                        
                        return `
                            <div class="border border-gray-200 rounded-lg p-4 bg-white shadow-sm">
                                <h4 class="text-lg font-semibold text-blue-700 mb-2">${idx + 1}. ${recipe.title}</h4>
                                <ul class="space-y-1">
                                    ${ingredientsListHTML}
                                    ${moreCount > 0 ? `<li class="text-sm text-gray-500 italic">+ ${moreCount} more ingredients</li>` : ''}
                                </ul>
                            </div>
                        `;
                    }).join('');
                    
                    outputDiv.innerHTML = `
                        <div class="space-y-4">
                            <h3 class="text-xl font-semibold text-gray-800">Your Ingredients (${ingredientsList.length}):</h3>
                            <ul class="space-y-2 mb-4">
                                ${ingredientsHTML}
                            </ul>
                            <h3 class="text-xl font-semibold text-green-700">Top 5 Recipes (from ${recipesResult.total_found} matches):</h3>
                            <div class="space-y-3">
                                ${recipesHTML}
                            </div>
                        </div>
                    `;
                }
            } else {
                throw new Error(recipesResult.error || 'Failed to get recipes');
            }
        } else {
            throw new Error(result.error || 'Unknown error from backend');
        }

    } catch (error) {
        console.error('Analysis error:', error);
        outputDiv.innerHTML = `
            <div class="text-red-600 p-4 bg-red-50 rounded-lg">
                <p class="font-medium mb-2">❌ Error: ${error.message}</p>
                <p class="text-sm">Troubleshooting tips:</p>
                <ul class="text-sm list-disc ml-4 mt-1">
                    <li>Make sure your Vercel backend is deployed</li>
                    <li>Check that API_URL points to the correct endpoint</li>
                    <li>Verify CORS is configured correctly in your backend</li>
                    <li>Check browser console for detailed error messages</li>
                </ul>
            </div>
        `;
    } finally {
        // Reset button
        button.disabled = false;
        buttonText.textContent = 'Get Recipes';
    }
}

// Optional: Test API connection on page load
window.addEventListener('DOMContentLoaded', async () => {
    try {
        const healthUrl = API_URL.replace('/analyze', '/health');
        const response = await fetch(healthUrl);
        if (response.ok) {
            console.log('✅ Backend API is reachable');
        }
    } catch (error) {
        console.warn('⚠️ Could not reach backend API:', error.message);
    }
});