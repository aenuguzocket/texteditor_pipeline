"""
Debug Erasure Overlay V4
========================
Visualizes exactly what pixels were erased by the V4 "Pixel Gating" strategy.

Outputs:
- `debug_erasure_overlay.png`: 
    - Original Image (Faded)
    - RED pixels = Erased/Transparent in cleaned layers
    - GREEN outline = Global CRAFT Boxes (Targeted)
    - BLUE outline = Preserved Roles (Logo, Product Text)

Usage:
    python pipeline_v4/debug_erasure_overlay_v4.py --run_id <RUN_ID>
"""

import sys
import argparse
import json
import cv2
import numpy as np
from pathlib import Path

# Config
ALPHA_FADE = 0.5  # How much to fade original image
ERASE_COLOR = (0, 0, 255) # Red for erased pixels (BGR)
BOX_COLOR_REMOVED = (0, 255, 0) # Green for targeted boxes
BOX_COLOR_PRESERVED = (255, 0, 0) # Blue for preserved boxes

def generate_overlay(run_id, base_dir="pipeline_outputs"):
    run_path = Path(base_dir) / run_id
    if not run_path.exists():
        print(f"Error: Run path not found: {run_path}")
        return

    # 1. Load Original Image from Report reference
    report_path = run_path / "pipeline_report.json"
    if not report_path.exists():
        print("Error: Report not found.")
        return
        
    with open(report_path, "r") as f:
        report = json.load(f)
        
    input_filename = report.get("input_image", "")
    # Robust Path Finding
    # Sometimes input_filename already contains "image/" prefix or is absolute
    candidates = [
        Path(input_filename),
        Path("image") / input_filename,
        Path("image") / Path(input_filename).name,
        Path(str(Path("image") / input_filename).replace("image\\image", "image"))
    ]
    
    orig_img_path = None
    for c in candidates:
        if c.exists():
            orig_img_path = c
            break
            
    if not orig_img_path:
        print(f"Warning: Original image not found. Checked: {[str(c) for c in candidates]}")
        return

    print(f"Loading Original: {orig_img_path}")
    orig_img = cv2.imread(str(orig_img_path))
    h, w = orig_img.shape[:2]
    
    # 2. Create Visualization Canvas (Faded Original)
    vis_img = orig_img.copy()
    overlay = orig_img.copy()
    cv2.addWeighted(overlay, ALPHA_FADE, vis_img, 1 - ALPHA_FADE, 0, vis_img)
    
    # 3. Identify Erased Pixels from Layers
    # We compare Original Layer vs Cleaned Layer or use Alpha channel of Cleaned Layer
    # Since V4 cleaning makes pixels transparent (Alpha=0), we can detect that.
    
    layers_dir = run_path / "layers"
    layer_info = report.get("layer_cleaning", {}).get("layers_processed", [])
    
    erasure_mask_accum = np.zeros((h, w), dtype=np.uint8)
    
    for l_info in layer_info:
        cleaned_name = l_info.get("cleaned_layer")
        orig_name = l_info.get("original_layer")
        
        if "layer_0" in cleaned_name: continue # Layer 0 is protected
        
        c_path = layers_dir / cleaned_name
        if not c_path.exists(): continue
        
        # Load Cleaned Layer (RGBA)
        cleaned_img = cv2.imread(str(c_path), cv2.IMREAD_UNCHANGED)
        if cleaned_img.shape[2] != 4: continue
        
        # Resize to original if needed (should match if standard pipeline)
        if cleaned_img.shape[:2] != (h, w):
            cleaned_img = cv2.resize(cleaned_img, (w, h), interpolation=cv2.INTER_NEAREST)
            
        # Find pixels where Alpha < 255 (Transparent/Erased)
        # Note: Qwen layers might have natural transparency. 
        # But our "Pixel Gating" explicitly sets alpha to 0 for text.
        # To distinguish natural alpha from erased, we might need the original layer?
        # Simpler proxy: If it overlaps with a Global Text Box AND is transparent, it's likely erased text.
        
        # Better: We trusted "Action Log" said "verified=X".
        # Let's just visualize the Alpha=0 holes that *overlap* with Remove Roles.
        
        alpha = cleaned_img[:, :, 3]
        erased_pixels = (alpha == 0).astype(np.uint8)
        
        # Accumulate
        erasure_mask_accum = cv2.bitwise_or(erasure_mask_accum, erased_pixels)

    # 4. Draw Erased Pixels in RED
    # Where mask is 1, set color to Red
    vis_img[erasure_mask_accum == 1] = ERASE_COLOR
    
    # 5. Draw Global Boxes (Context)
    text_regions = report.get("text_detection", {}).get("regions", [])
    
    for region in text_regions:
        bbox = region["bbox"]
        role = region.get("gemini_analysis", {}).get("role", "body")
        
        x, y = int(bbox["x"]), int(bbox["y"])
        w_b, h_b = int(bbox["width"]), int(bbox["height"])
        
        color = BOX_COLOR_PRESERVED
        if role in ["heading", "subheading", "body", "cta", "usp", "hero_text"]:
            color = BOX_COLOR_REMOVED
            
        cv2.rectangle(vis_img, (x, y), (x+w_b, y+h_b), color, 2)
        cv2.putText(vis_img, f"{role}", (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    # Save
    out_path = run_path / "debug_erasure_overlay.png"
    cv2.imwrite(str(out_path), vis_img)
    print(f"Saved Debug Overlay: {out_path}")
    return str(out_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_id", type=str, required=True, help="Run ID to visualize")
    args = parser.parse_args()
    
    generate_overlay(args.run_id)
