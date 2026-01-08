import os
import json
from PIL import Image
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

MODEL_NAME = "gemini-2.5-flash"   # Fallback from gemini-3-pro
API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=API_KEY)

# --------------------------------------------------
# SCHEMA (same as your existing one)
# --------------------------------------------------

TEXT_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "text": {"type": "string"},
        "role": {
            "type": "string",
            "enum": ["heading", "subheading", "body", "usp", "cta", "label"]
        },
        "primary_font": {"type": "string"},
        "fallback_font": {"type": "string"},
        "font_weight": {
            "type": "string",
            "enum": ["regular", "medium", "semibold", "bold", "extrabold"]
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

MULTI_TEXT_SCHEMA = {
    "type": "array",
    "items": TEXT_ANALYSIS_SCHEMA
}

# --------------------------------------------------
# PROMPT (locked, production-safe)
# --------------------------------------------------

MULTI_CROP_PROMPT = """
You are given multiple image regions extracted from a single advertisement.
Each image contains exactly one text block.

Tasks for EACH image:
- Read the exact visible text
- Identify the semantic role of the text
- Choose a PRIMARY FONT from Google Fonts that visually matches the text
- Choose a FALLBACK FONT from Google Fonts that is visually similar
- Choose a font weight: regular, medium, semibold, bold, or extrabold
- Determine text case
- Determine the primary text color in hex format
- Determine CTA intent if applicable

Rules:
- Return a JSON ARRAY
- One object per image
- Order must match input image order
- Use ONLY Google Fonts
- Do NOT include explanations
- Do NOT include layout or position data
- Do NOT add extra fields
- Return ONLY valid JSON
"""

# --------------------------------------------------
# MAIN FUNCTION (THIS IS WHAT YOU CALL)
# --------------------------------------------------

def analyze_text_crops_batch(crop_image_paths):
    """
    Single Gemini call for multiple text crops.
    """
    images = [Image.open(p) for p in crop_image_paths]

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[MULTI_CROP_PROMPT] + images,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=MULTI_TEXT_SCHEMA,
            temperature=0
        )
    )

    try:
        data = json.loads(response.text)
        # Ensure we return a list, even if API returns single object or weird wrapper
        if isinstance(data, list):
            return data
        else:
            return [data]
    except Exception as e:
        print(f"Error parsing Gemini response: {e}")
        return []


# --------------------------------------------------
# OPTIONAL TEST RUN
# --------------------------------------------------

if __name__ == "__main__":
    # Pointing to a known valid directory from previous runs
    crops_dir = "outputs_all_line/run_1/7015ce93-81f5-405c-a514-979c91689be7/crops"

    if not os.path.exists(crops_dir):
        print(f"Error: Directory not found: {crops_dir}")
        exit(1)

    crop_files = sorted([
        os.path.join(crops_dir, f)
        for f in os.listdir(crops_dir)
        if f.lower().endswith((".png", ".jpg", ".jpeg"))
    ])

    if not crop_files:
        print("No crop images found.")
        exit(1)

    print(f"Sending {len(crop_files)} crops in ONE Gemini call...")

    try:
        result = analyze_text_crops_batch(crop_files)
        
        with open("gemini_batch_result.json", "w") as f:
            json.dump(result, f, indent=2)

        print("Done. Output saved to gemini_batch_result.json")
    except Exception as e:
        print(f"Batch analysis failed: {e}")
