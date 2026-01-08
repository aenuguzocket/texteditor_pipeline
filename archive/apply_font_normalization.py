import json
from font_normalizer import normalize_font_and_weight

INPUT_FILE = "gemini_text_analysis5.json"
OUTPUT_FILE = "text_analysis_normalized.json"

def main():
    print(f"Loading {INPUT_FILE}...")
    try:
        with open(INPUT_FILE, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {INPUT_FILE} not found. Please run gemini_text_analysis.py first.")
        return

    normalized_data = []
    
    for item in data:
        analysis = item.get("analysis", {})
        
        primary_font = analysis.get("primary_font", "")
        fallback_font = analysis.get("fallback_font", "")
        visual_weight = analysis.get("font_weight", "regular")
        
        # Normalize
        final_font, final_weight = normalize_font_and_weight(
            primary_font, 
            fallback_font, 
            visual_weight
        )
        
        # Create new entry with normalized fields
        new_item = item.copy()
        new_item["analysis"]["normalized_font"] = final_font
        new_item["analysis"]["normalized_weight"] = final_weight
        
        normalized_data.append(new_item)
        
        print(f"Processed {item.get('crop')}: {primary_font} ({visual_weight}) -> {final_font} ({final_weight})")

    with open(OUTPUT_FILE, "w") as f:
        json.dump(normalized_data, f, indent=2)
    
    print(f"Saved normalized data to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
