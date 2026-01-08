import os
import json
from PIL import Image
from google import genai
from google.genai import types
from dotenv import load_dotenv

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = "gemini-2.5-flash"

# --------------------------------------------------
# JSON SCHEMA
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

# --------------------------------------------------
# PROMPT
# --------------------------------------------------

PROMPT = """
Analyze the text shown in this advertisement image.

Tasks:
- Read the exact visible text
- Identify the semantic role of the text
- Select a PRIMARY FONT that exists in Google Fonts and visually matches the text
- Select a FALLBACK FONT that exists in Google Fonts and is visually similar
- Select a font weight supported by Google Fonts
- Determine text case
- Determine the primary text color in hex format
- Determine CTA intent if applicable

Rules:
- Choose fonts ONLY from Google Fonts
- Use ONLY the following font weights:
  regular, medium, semibold, bold, extrabold
- If the visual weight appears extremely heavy, use extrabold
- Do not use black or numeric weights
- Return ONLY valid JSON
- Do not include explanations
- Do not include layout or position information
- Do not add extra fields
"""

# --------------------------------------------------
# GEMINI CALL
# --------------------------------------------------

def analyze_text_crop(image_path: str) -> dict:
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
# PROCESS ALL CRAFT CROPS
# --------------------------------------------------

def analyze_all_crops(crops_dir: str):
    results = []

    for file in sorted(os.listdir(crops_dir)):
        if not file.lower().endswith((".png", ".jpg", ".jpeg")):
            continue

        crop_path = os.path.join(crops_dir, file)
        print(f"Processing {file}")

        try:
            analysis = analyze_text_crop(crop_path)
            results.append({
                "crop": file,
                "analysis": analysis
            })
        except Exception as e:
            print(f"Gemini failed on {file}: {e}")

    return results

# --------------------------------------------------
# MAIN
# --------------------------------------------------

if __name__ == "__main__":
    # CRAFT_CROPS_DIR = "outputs_all_line/run_1/7a28326f-bf66-4008-97b4-abba4dfedd3a/crops"
    CRAFT_CROPS_DIR = "outputs_all_line/run_1/9aa8f004-7003-412e-a4b0-c17b42319229/crops"
    output = analyze_all_crops(CRAFT_CROPS_DIR)

    with open("gemini_text_analysis5.json", "w") as f:
        json.dump(output, f, indent=2)

    print("Done. Gemini analysis saved.")
