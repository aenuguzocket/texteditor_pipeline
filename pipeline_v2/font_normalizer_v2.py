"""
Font Normalizer V2 - Smart Fallback for Font Weights
=====================================================
Handles cases where the detected font doesn't have the required weight
by finding similar fonts that DO have the weight.
"""

import json
import os

# --------------------------------------------------
# FONT WEIGHT MAPPINGS
# --------------------------------------------------

# Standard CSS weight names to numeric values
WEIGHT_NAME_TO_NUMERIC = {
    "thin": 100,
    "hairline": 100,
    "extralight": 200,
    "extra-light": 200,
    "ultralight": 200,
    "light": 300,
    "regular": 400,
    "normal": 400,
    "medium": 500,
    "semibold": 600,
    "semi-bold": 600,
    "demibold": 600,
    "bold": 700,
    "extrabold": 800,
    "extra-bold": 800,
    "ultrabold": 800,
    "black": 900,
    "heavy": 900,
}

# Fonts that are visually similar (for fallback when weight not available)
# This is a SEED mapping - will be extended dynamically from Google Fonts API
SIMILAR_FONTS_SEED = {
    # Display/Bold fonts
    "Bebas Neue": ["Oswald", "Anton", "Teko", "Fjalla One"],
    "Anton": ["Bebas Neue", "Oswald", "Black Ops One"],
    "Oswald": ["Bebas Neue", "Anton", "Teko"],
    
    # Sans-serif
    "Roboto": ["Open Sans", "Lato", "Montserrat", "Inter"],
    "Open Sans": ["Roboto", "Lato", "Source Sans Pro"],
    "Lato": ["Roboto", "Open Sans", "Nunito"],
    "Montserrat": ["Poppins", "Raleway", "Roboto"],
    "Poppins": ["Montserrat", "Inter", "Nunito Sans"],
    "Inter": ["Roboto", "Poppins", "Open Sans"],
    
    # Serif
    "Playfair Display": ["Libre Baskerville", "Lora", "Merriweather"],
    "Merriweather": ["Lora", "Playfair Display", "PT Serif"],
    "Lora": ["Merriweather", "Playfair Display", "Libre Baskerville"],
}

# Fonts that only have limited weights (from Google Fonts)
LIMITED_WEIGHT_FONTS = {
    "Bebas Neue": [400],
    "Anton": [400],
    "Black Ops One": [400],
    "Fjalla One": [400],
    "Bangers": [400],
    "Lobster": [400],
}


def find_similar_fonts_by_category(font_name: str, target_weight: int, fonts_cache: dict) -> list:
    """
    Dynamically find similar fonts using Google Fonts API metadata.
    Matches by category and checks if they have the required weight.
    
    Returns list of (font_name, available_weight) tuples sorted by weight proximity.
    """
    if font_name not in fonts_cache:
        return []
    
    source_font = fonts_cache[font_name]
    source_category = source_font.get("category", "sans-serif")
    
    candidates = []
    
    for other_name, other_info in fonts_cache.items():
        if other_name == font_name:
            continue
            
        # Match by category
        if other_info.get("category") != source_category:
            continue
        
        # Check available weights
        files = other_info.get("files", {})
        available_weights = []
        
        for variant in files.keys():
            if variant == "regular":
                available_weights.append(400)
            elif variant.isdigit():
                available_weights.append(int(variant))
            elif "italic" in variant:
                weight_str = variant.replace("italic", "")
                if weight_str.isdigit():
                    available_weights.append(int(weight_str))
        
        if not available_weights:
            continue
        
        # Find closest weight to target
        closest = min(available_weights, key=lambda x: abs(x - target_weight))
        diff = abs(closest - target_weight)
        
        # Only consider if reasonably close (within 200)
        if diff <= 200:
            candidates.append((other_name, closest, diff))
    
    # Sort by weight proximity, then by font name (for consistency)
    candidates.sort(key=lambda x: (x[2], x[0]))
    
    # Return top 5 candidates
    return [(name, weight) for name, weight, _ in candidates[:5]]


def load_google_fonts_cache(cache_path: str = None) -> dict:
    """Load the Google Fonts cache."""
    if cache_path is None:
        # Default to file in the same directory as this script
        cache_path = os.path.join(os.path.dirname(__file__), "google_fonts_full_cache.json")
        
    if os.path.exists(cache_path):
        with open(cache_path, "r") as f:
            return json.load(f)
    return {}


def get_available_weights(font_name: str, fonts_cache: dict) -> list:
    """Get list of available numeric weights for a font."""
    if font_name in LIMITED_WEIGHT_FONTS:
        return LIMITED_WEIGHT_FONTS[font_name]
    
    if font_name not in fonts_cache:
        return [400]  # Default fallback
    
    font_info = fonts_cache[font_name]
    files = font_info.get("files", {})
    
    weights = []
    for variant in files.keys():
        if variant == "regular":
            weights.append(400)
        elif variant == "italic":
            continue  # Skip italic-only entries
        elif variant.isdigit():
            weights.append(int(variant))
        elif "italic" in variant:
            # Extract weight from variants like "700italic"
            weight_str = variant.replace("italic", "")
            if weight_str.isdigit():
                weights.append(int(weight_str))
    
    return sorted(set(weights)) if weights else [400]


def find_closest_weight(target: int, available: list) -> int:
    """Find the closest available weight to the target."""
    if not available:
        return 400
    if target in available:
        return target
    return min(available, key=lambda x: abs(x - target))


def normalize_font_and_weight(
    primary_font: str,
    fallback_font: str,
    weight_input,  # Can be string ("bold") or int (700)
    fonts_cache: dict = None
) -> tuple:
    """
    Normalize font and weight, finding alternatives if needed.
    
    Returns:
        (font_name, numeric_weight)
    """
    if fonts_cache is None:
        fonts_cache = load_google_fonts_cache()
    
    # Convert weight to numeric if string
    if isinstance(weight_input, str):
        weight_key = weight_input.lower().replace(" ", "")
        target_weight = WEIGHT_NAME_TO_NUMERIC.get(weight_key, 400)
    else:
        target_weight = int(weight_input)
    
    # Clamp to valid range
    target_weight = max(100, min(900, target_weight))
    # Round to nearest 100
    target_weight = round(target_weight / 100) * 100
    
    # Check if primary font has the weight
    primary_weights = get_available_weights(primary_font, fonts_cache)
    
    if target_weight in primary_weights:
        return primary_font, target_weight
    
    # Check if closest weight is acceptable (within 100)
    closest_primary = find_closest_weight(target_weight, primary_weights)
    if abs(closest_primary - target_weight) <= 100:
        return primary_font, closest_primary
    
    # Try fallback font
    if fallback_font and fallback_font in fonts_cache:
        fallback_weights = get_available_weights(fallback_font, fonts_cache)
        if target_weight in fallback_weights:
            print(f"Switching from {primary_font} to {fallback_font} for weight {target_weight}")
            return fallback_font, target_weight
        closest_fallback = find_closest_weight(target_weight, fallback_weights)
        if abs(closest_fallback - target_weight) < abs(closest_primary - target_weight):
            return fallback_font, closest_fallback
    
    # Try similar fonts from SEED mapping first
    similar = SIMILAR_FONTS_SEED.get(primary_font, [])
    best_similar = None
    best_similar_weight = None
    best_similar_diff = float('inf')
    
    for sim_font in similar:
        if sim_font in fonts_cache:
            sim_weights = get_available_weights(sim_font, fonts_cache)
            if target_weight in sim_weights:
                # Exact match found - use it immediately
                print(f"Switching from {primary_font} to similar font {sim_font} for weight {target_weight}")
                return sim_font, target_weight
            else:
                # Check for closest weight
                closest = find_closest_weight(target_weight, sim_weights)
                diff = abs(closest - target_weight)
                if diff < best_similar_diff:
                    best_similar = sim_font
                    best_similar_weight = closest
                    best_similar_diff = diff
    
    # Use best seed font if it's closer than primary's closest
    if best_similar and best_similar_diff < abs(closest_primary - target_weight):
        print(f"Switching from {primary_font} to similar font {best_similar} (weight {best_similar_weight} for target {target_weight})")
        return best_similar, best_similar_weight
    
    # DYNAMIC FALLBACK: Search Google Fonts by category if seed fonts didn't help
    dynamic_candidates = find_similar_fonts_by_category(primary_font, target_weight, fonts_cache)
    if dynamic_candidates:
        best_dynamic, best_dynamic_weight = dynamic_candidates[0]
        dynamic_diff = abs(best_dynamic_weight - target_weight)
        
        if dynamic_diff < abs(closest_primary - target_weight):
            print(f"Dynamic fallback: {primary_font} -> {best_dynamic} (weight {best_dynamic_weight} for target {target_weight})")
            return best_dynamic, best_dynamic_weight
    
    # Last resort: use primary with closest available weight
    return primary_font, closest_primary


# --------------------------------------------------
# TEST
# --------------------------------------------------

if __name__ == "__main__":
    # Test cases
    tests = [
        ("Bebas Neue", "Oswald", 700),
        ("Bebas Neue", "Oswald", 400),
        ("Roboto", "Open Sans", 700),
        ("Anton", "Oswald", 800),
        ("Montserrat", "", "bold"),
        ("Poppins", "Inter", "semibold"),
    ]
    
    print("Font Normalizer V2 Test Results:")
    print("-" * 50)
    
    for primary, fallback, weight in tests:
        result_font, result_weight = normalize_font_and_weight(primary, fallback, weight)
        print(f"{primary} ({weight}) -> {result_font} ({result_weight})")
