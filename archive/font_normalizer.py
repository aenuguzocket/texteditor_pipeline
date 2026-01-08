from google_fonts import load_google_fonts

GOOGLE_FONTS = load_google_fonts()

VISUAL_TO_NUMERIC = {
    "regular": 400,
    "medium": 500,
    "semibold": 600,
    "bold": 700,
    "extrabold": 800,
    "black": 900,
    "thin": 100
}

def closest_weight(requested, available):
    if not available:
        return 400
    return min(available, key=lambda w: abs(w - requested))

def normalize_font_and_weight(
    primary_font: str,
    fallback_font: str,
    visual_weight: str
):
    # Default to 400 if visual weight is unknown
    requested_weight = VISUAL_TO_NUMERIC.get(visual_weight.lower(), 400)

    # 1. Try primary font
    if primary_font in GOOGLE_FONTS:
        weights = GOOGLE_FONTS[primary_font]
        final_weight = closest_weight(requested_weight, weights)
        return primary_font, final_weight

    # 2. Try fallback font
    if fallback_font in GOOGLE_FONTS:
        weights = GOOGLE_FONTS[fallback_font]
        final_weight = closest_weight(requested_weight, weights)
        return fallback_font, final_weight

    # 3. Hard fallback
    return "Inter", 400
