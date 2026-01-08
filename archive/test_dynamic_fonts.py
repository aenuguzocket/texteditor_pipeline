from font_normalizer_v2 import normalize_font_and_weight

# Test fonts NOT in the seed mapping
tests = [
    ("Pacifico", "", 700),        # Handwriting font
    ("Dancing Script", "", 600),   # Handwriting font  
    ("Abril Fatface", "", 800),    # Display font
    ("Cinzel", "", 900),           # Serif font
]

print("Testing Dynamic Font Fallback:")
print("-" * 50)

for primary, fallback, weight in tests:
    result = normalize_font_and_weight(primary, fallback, weight)
    print(f"{primary}({weight}) -> {result}")
