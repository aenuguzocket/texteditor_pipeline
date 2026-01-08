"""
Enhanced Gemini Text Analysis with Better Font Weight Detection
================================================================
Uses gemini-2.5-pro for more accurate visual analysis
Returns numeric font weights (100-900) instead of text labels
"""

import os
import json
from PIL import Image
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# --------------------------------------------------
# CONFIGURATION - EDIT THIS SECTION
# --------------------------------------------------

# Input directory containing image crops to analyze
INPUT_DIR = r"pipeline_outputs/run_1767361025_layered/crops"

# Output JSON file path
OUTPUT_FILE = r"pipeline_outputs/run_1767361025_layered/layers/playground_output.json"

# Model selection
MODEL_NAME = "gemini-2.5-flash-lite" 

# --------------------------------------------------
# API SETUP
# --------------------------------------------------

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# --------------------------------------------------
# ENHANCED JSON SCHEMA with numeric weight
# --------------------------------------------------

TEXT_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "text": {"type": "string"},
        "role": {
            "type": "string",
            "enum": ["heading", "subheading", "body", "usp", "cta", "label", "product_text", "logo", "icon", "ui_element"]
        },
        "primary_font": {"type": "string"},
        "fallback_font": {"type": "string"},
        "font_weight": {
            "type": "integer",
            "description": "Numeric font weight from 100 to 900"
        },
        "text_case": {
            "type": "string",
            "enum": ["uppercase", "lowercase", "titlecase", "sentencecase"]
        },
        "text_color": {"type": "string"},
        "cta_intent": {
            "type": "string",
            "enum": ["shop_now", "learn_more", "buy_now", "explore", "sign_up", "none"]
        }
    },
    "required": [
        "text",
        "role",
        "primary_font",
        "fallback_font",
        "font_weight",
        "text_case",
        "text_color",
        "cta_intent"
    ]
}

# --------------------------------------------------
# ENHANCED PROMPT for numeric weight detection
# --------------------------------------------------

PROMPT = """
Analyze the text shown in this advertisement image with extreme precision.

Tasks:
1. Read the exact visible text (preserve original casing)
2. Identify the semantic role. CRITICAL: Detect "product_text" (text ON the product itself, e.g. sunscreen bottle label), "logo", "ui_element".
3. Identify the font family - must be available in Google Fonts
4. Estimate the NUMERIC font weight using this visual guide:
   - 100 = Thin (hairline)
   - 200 = Extra Light
   - 300 = Light
   - 400 = Regular (normal weight)
   - 500 = Medium
   - 600 = Semi Bold
   - 700 = Bold
   - 800 = Extra Bold
   - 900 = Black (heaviest)
   
   Look at stroke thickness relative to letter height:
   - Thin strokes (barely visible) = 100-200
   - Light strokes = 300
   - Normal/regular strokes = 400
   - Slightly thick strokes = 500-600
   - Thick, bold strokes = 700
   - Very thick strokes = 800-900

5. Determine text case
6. Determine the primary text color in hex format
7. Determine CTA intent if applicable

Critical Rules:
- font_weight MUST be a NUMBER between 100 and 900 (multiples of 100)
- Choose fonts ONLY from Google Fonts
- Return ONLY valid JSON
- Do not include explanations
"""

# --------------------------------------------------
# GEMINI CALL
# --------------------------------------------------

def analyze_text_crop(image_path: str) -> dict:
    """Analyze single text crop with enhanced weight detection."""
    image = Image.open(image_path)
    
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[PROMPT, image],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=TEXT_ANALYSIS_SCHEMA,
            temperature=0
        )
    )

    return json.loads(response.text)


# --------------------------------------------------
# BATCH ANALYSIS
# --------------------------------------------------

MULTI_TEXT_SCHEMA = {
    "type": "array",
    "items": TEXT_ANALYSIS_SCHEMA
}

BATCH_PROMPT = """
You are given multiple image regions extracted from a single advertisement.
Each image contains exactly one text block.

For EACH image, analyze with extreme precision:

1. Read the exact visible text (preserve original casing)
2. Identify the semantic role. CRITICAL:
   - "product_text": text appearing ON a physical object/product (e.g. shampoo bottle label, book cover)
   - "logo": brand logos or wordmarks
   - "ui_element": interface buttons, icons, or navigation
   - "label": small descriptive labels (e.g. "New", "50% Off")
   - "heading/body/cta": standard ad text overlay
3. Identify the font family from Google Fonts
4. Estimate the NUMERIC font weight (100-900):
   - 100 = Thin (hairline strokes)
   - 200 = Extra Light
   - 300 = Light
   - 400 = Regular
   - 500 = Medium
   - 600 = Semi Bold
   - 700 = Bold
   - 800 = Extra Bold
   - 900 = Black (heaviest strokes)
   
   Judge by stroke thickness relative to letter height.
   
5. Determine text case
6. Determine text color in hex
7. Determine CTA intent if applicable

Rules:
- Return a JSON ARRAY with one object per image
- Order must match input image order
- font_weight MUST be a NUMBER (100-900)
- Use ONLY Google Fonts
- Return ONLY valid JSON
"""


# --------------------------------------------------
# COST TRACKING
# --------------------------------------------------

def print_call_cost(usage):
    """Print estimated cost for the API call."""
    # Gemini 2.5-Flash-Lite pricing
    input_cost_per_million = 0.10
    output_cost_per_million = 0.40

    if not usage:
        return

    # Handle different SDK versions or response objects
    in_tokens = getattr(usage, 'input_tokens', getattr(usage, 'prompt_token_count', 0))
    out_tokens = getattr(usage, 'output_tokens', getattr(usage, 'candidates_token_count', 0))

    cost = (in_tokens / 1_000_000) * input_cost_per_million \
         + (out_tokens / 1_000_000) * output_cost_per_million

    print("==== COST ESTIMATE ====")
    print(f"Input tokens: {in_tokens}")
    print(f"Output tokens: {out_tokens}")
    print(f"Estimated cost: ${cost:.6f}")


def analyze_text_crops_batch(crop_image_paths: list) -> list:
    """Analyze multiple crops in one call with enhanced weight detection."""
    images = [Image.open(p) for p in crop_image_paths]

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[BATCH_PROMPT] + images,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=MULTI_TEXT_SCHEMA,
            temperature=0
        )
    )
    
    # Calculate cost
    if hasattr(response, 'usage_metadata'):
        print_call_cost(response.usage_metadata)

    try:
        data = json.loads(response.text)
        if isinstance(data, list):
            return data
        else:
            return [data]
    except Exception as e:
        print(f"Error parsing Gemini response: {e}")
        return []


# --------------------------------------------------
# TEST
# --------------------------------------------------

# --------------------------------------------------
# TEST
# --------------------------------------------------

if __name__ == "__main__":
    print(f"--- Text Analysis Playground ---")
    print(f"Model: {MODEL_NAME}")
    print(f"Input: {INPUT_DIR}")
    
    # 1. Validate Input Directory
    if not os.path.exists(INPUT_DIR):
        print(f"Error: Input directory not found: {INPUT_DIR}")
        exit(1)
        
    # 2. Collect Image Files
    supported_exts = ('.png', '.jpg', '.jpeg', '.webp')
    image_files = []
    
    for filename in os.listdir(INPUT_DIR):
        if filename.lower().endswith(supported_exts):
            image_files.append(os.path.join(INPUT_DIR, filename))
            
    # Sort for consistency
    image_files.sort()
    
    if not image_files:
        print(f"No images found in {INPUT_DIR}")
        exit(1)
        
    print(f"Found {len(image_files)} images. Starting batch analysis...")
    
    # 3. Run Analysis
    try:
        results = analyze_text_crops_batch(image_files)
        
        # 4. Save Output
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
            
        print(f"\nSuccess! Results saved to:")
        print(f"{OUTPUT_FILE}")
        
    except Exception as e:
        print(f"\nError during analysis: {e}")
