import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_FONTS_API_KEY = os.getenv("GOOGLE_FONTS_API_KEY")
GOOGLE_FONTS_URL = (
    "https://www.googleapis.com/webfonts/v1/webfonts"
    f"?key={GOOGLE_FONTS_API_KEY}"
)

CACHE_FILE = "google_fonts_cache.json"

VARIANT_TO_WEIGHT = {
    "thin": 100,
    "extralight": 200,
    "light": 300,
    "regular": 400,
    "medium": 500,
    "semibold": 600,
    "bold": 700,
    "extrabold": 800,
    "black": 900,
    "italic": 400, # Basic fallback for italic
    "regularitalic": 400,
}

def fetch_google_fonts():
    print("Fetching Google Fonts metadata...")
    if not GOOGLE_FONTS_API_KEY:
        raise ValueError("GOOGLE_FONTS_API_KEY not found in environment variables")
        
    res = requests.get(GOOGLE_FONTS_URL, timeout=15)
    res.raise_for_status()
    data = res.json()

    font_map = {}

    for item in data["items"]:
        family = item["family"]
        weights = []

        for v in item["variants"]:
            if v == "italic": 
                weights.append(400)
                continue
            
            # Handle standard weights (100, 200... 900)
            if v.isdigit():
                weights.append(int(v))
            # Handle italic weights (100italic, 700italic) - extract number
            elif v[:-6].isdigit() and v.endswith('italic'):
                weights.append(int(v[:-6]))
            # Handle named variants
            else:
                w = VARIANT_TO_WEIGHT.get(v)
                if w:
                    weights.append(w)

        font_map[family] = sorted(set(weights))

    with open(CACHE_FILE, "w") as f:
        json.dump(font_map, f, indent=2)

    return font_map


def load_google_fonts():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    try:
        return fetch_google_fonts() 
    except Exception as e:
        print(f"Warning: Could not fetch Google Fonts: {e}")
        return {}
