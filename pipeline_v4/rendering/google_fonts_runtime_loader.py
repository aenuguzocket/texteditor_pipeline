import os
import json
import requests
from dotenv import load_dotenv

# Folder to store downloaded fonts
# Folder to store downloaded fonts (In this directory)
FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
os.makedirs(FONT_DIR, exist_ok=True)

# Cache file path
# Cache file path (In parent directory)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Shared cache with v2 to avoid re-fetching
# Just point to the cache in the project root if possible, or share.
# Original logic: os.path.dirname(os.path.dirname(...)) would be pipeline_v4.
# Then cache is pipeline_v4/google_fonts_full_cache.json.
# This means v4 will have its own cache. That is fine.
GOOGLE_FONTS_CACHE = os.path.join(BASE_DIR, "google_fonts_full_cache.json")

def fetch_full_google_fonts_cache():
    """
    Fetches the full Google Fonts metadata (including file URLs) and saves it.
    """
    load_dotenv()
    api_key = os.getenv("GOOGLE_FONTS_API_KEY")
    if not api_key:
        print("Warning: GOOGLE_FONTS_API_KEY not found. Cannot fetch fonts.")
        return

    url = f"https://www.googleapis.com/webfonts/v1/webfonts?key={api_key}"
    print("Fetching full Google Fonts cache...")
    try:
        res = requests.get(url, timeout=20)
        res.raise_for_status()
        data = res.json()
        
        # Transform to dict keyed by family for easy lookup
        fonts_map = {item["family"]: item for item in data["items"]}
        
        with open(GOOGLE_FONTS_CACHE, "w") as f:
            json.dump(fonts_map, f, indent=2)
        print(f"Saved full font cache to {GOOGLE_FONTS_CACHE}")
    except Exception as e:
        print(f"Error fetching Google Fonts: {e}")

def get_font_path(font_name: str, font_weight: int) -> str:
    """
    Returns a local .ttf path for (font_name, font_weight).
    Downloads from Google Fonts if not present.
    """
    # Ensure cache exists
    if not os.path.exists(GOOGLE_FONTS_CACHE):
        fetch_full_google_fonts_cache()

    safe_name = font_name.replace(" ", "")
    local_path = f"{FONT_DIR}/{safe_name}-{font_weight}.ttf"

    if os.path.exists(local_path):
        return local_path

    if not os.path.exists(GOOGLE_FONTS_CACHE):
        raise ValueError(f"Google Fonts cache missing: {GOOGLE_FONTS_CACHE}")

    with open(GOOGLE_FONTS_CACHE, "r") as f:
        fonts_data = json.load(f)

    if font_name not in fonts_data:
        # Try fetching fresh cache if font not found (maybe new font?)
        print(f"Font {font_name} not in cache. Refreshing cache...")
        fetch_full_google_fonts_cache()
        with open(GOOGLE_FONTS_CACHE, "r") as f:
            fonts_data = json.load(f)
        
        if font_name not in fonts_data:
            # Fallback to Roboto or raise error?
            # For now, let's raise to be safe, or fallback to a known available font like Roboto
            print(f"Warning: {font_name} not found in Google Fonts. Falling back to Roboto.")
            if "Roboto" in fonts_data:
                font_name = "Roboto"
                font_info = fonts_data["Roboto"]
            else:
                raise ValueError(f"Font not found in Google Fonts cache: {font_name}")
        else:
            font_info = fonts_data[font_name]
    else:
        font_info = fonts_data[font_name]

    files = font_info["files"]

    # Map numeric weight to Google Fonts variant
    # Google Fonts API uses: "regular", "italic", "700", "700italic"
    if font_weight == 400:
        variant = "regular"
    else:
        variant = str(font_weight)

    if variant not in files:
        # Smart Weight Fallback with Threshold
        MAX_WEIGHT_DIFF = 200  # Max acceptable difference from requested weight
        
        # Parse available weights from file keys
        available_weights = []
        for key in files.keys():
            if key == "regular":
                available_weights.append(400)
            elif key.isdigit():
                available_weights.append(int(key))
        
        best_weight = None
        best_diff = float('inf')
        
        if available_weights:
            for w in available_weights:
                diff = abs(w - font_weight)
                if diff < best_diff:
                    best_diff = diff
                    best_weight = w
        
        # Check if best match is within threshold
        if best_weight is not None and best_diff <= MAX_WEIGHT_DIFF:
            if best_weight == 400:
                variant = "regular"
            else:
                variant = str(best_weight)
            print(f"  [Font] Requested {font_name} {font_weight}. Using closest: {best_weight} (diff: {best_diff})")
        else:
            # Weight difference too large - fallback to Roboto with appropriate weight
            print(f"  [Font] {font_name} weight {font_weight} not available (closest was {best_weight}, diff {best_diff} > {MAX_WEIGHT_DIFF})")
            print(f"  [Font] Falling back to Roboto...")
            
            # Determine Roboto weight category
            if font_weight >= 600:
                # Bold range - use Roboto 700
                fallback_path = os.path.join(os.path.dirname(os.path.dirname(FONT_DIR)), "fonts", "Roboto-700.ttf")
                if not os.path.exists(fallback_path):
                    # Try to download Roboto 700
                    return get_font_path("Roboto", 700)
            else:
                # Regular range - use Roboto 400
                fallback_path = os.path.join(os.path.dirname(os.path.dirname(FONT_DIR)), "fonts", "Roboto-400.ttf")
                if not os.path.exists(fallback_path):
                    return get_font_path("Roboto", 400)
            
            if os.path.exists(fallback_path):
                print(f"  [Font] Using bundled fallback: {fallback_path}")
                return fallback_path
            else:
                # Last resort: download from Roboto
                return get_font_path("Roboto", font_weight if font_weight in [400, 500, 700] else (700 if font_weight >= 600 else 400))

    font_url = files[variant]

    print(f"⬇ Downloading font: {font_name} ({variant})")
    try:
        response = requests.get(font_url, timeout=20)
        response.raise_for_status()

        with open(local_path, "wb") as f:
            f.write(response.content)
    except Exception as e:
        print(f"Failed to download font {font_name}: {e}")
        # Last resort fallback if download fails?
        raise e

    return local_path
