"""
Refine Mask by Semantics
=========================
Regenerates the inpainting mask using semantic data from final_result_pro.json.

Problem: 
The raw CRAFT mask covers EVERYTHING including logos, UI elements, and product text.
We want to remove ONLY editable text (headings, body, CTA) while preserving logos and UI.

Solution:
1. Read final_result_pro.json (which contains 'role' and 'text').
2. Filter regions:
   - INCLUDE: 'heading', 'body', 'cta', 'usp', 'subheading'
   - EXCLUDE: 'logo', 'time', 'date', 'ui', or text matching specific patterns
3. Generate a NEW mask ('refined_mask.png') from the filtered regions.
4. Replace 'text_mask.png' with this new mask (backing up the original).

Usage:
    python refine_mask_by_semantics.py pipeline_outputs/run_XXXX_pro
"""

import os
import json
import argparse
import shutil
import re
from pathlib import Path
import cv2
import numpy as np


def is_safe_to_remove(region: dict) -> bool:
    """
    Determine if a text region should be removed (masked) based on semantics.
    Returns True if it's editable text (Heading, Body, etc.).
    Returns False if it's a Logo, UI element, or preserved text.
    """
    content = region.get("text_content", {})
    text = content.get("text", "").strip()
    role = content.get("role", "unknown").lower()
    
    # 1. Role-based filtering
    # Roles that are definitely editable text
    editable_roles = {
        "heading", "headline", "subheading", "title",
        "body", "paragraph", "description", "text",
        "cta", "button", "usp", "caption"
    }
    
    # Roles that are definitely preserved elements
    preserved_roles = {
        "logo", "brand", "icon", 
        "time", "date", "timestamp",
        "ui", "ui_element", "navigation",
        "product_text", "label"
    }
    
    if role in preserved_roles:
        return False
        
    # 2. Heuristic filtering (Text Content)
    
    # Pattern: Time (e.g., "9:00", "10:00 AM", "12 PM")
    time_pattern = r'^\d{1,2}:\d{2}\s*(am|pm)?$|^\d{1,2}\s*(am|pm)$'
    if re.match(time_pattern, text.lower()):
        return False
        
    # Pattern: Brand names (Add specific brands if known, e.g., "fastrack", "zocket")
    # if text.lower() in ["flexslot", "zocket"]:
    #     return False
        
    # Default: If role is known editable, or unknown but looks like text
    if role in editable_roles:
        return True
        
    # If role is unknown, default to removing it (assuming it's text detected by CRAFT)
    # UNLESS it's very short/special characters
    if len(text) < 2 and not text.isalnum():
        return False
        
    return True


def refine_mask(pipeline_dir: str):
    pipeline_dir = Path(pipeline_dir)
    json_path = pipeline_dir / "final_result_pro.json"
    raw_mask_path = pipeline_dir / "text_mask.png"
    
    if not json_path.exists():
        print(f"Error: {json_path} not found")
        return
        
    # Load JSON
    with open(json_path, "r") as f:
        data = json.load(f)
        
    # Get dimensions
    dims = data.get("dimensions", {})
    width = dims.get("width")
    height = dims.get("height")
    
    # If dimensions missing, try to read from raw mask
    if (not width or not height) and raw_mask_path.exists():
        img = cv2.imread(str(raw_mask_path), cv2.IMREAD_GRAYSCALE)
        height, width = img.shape
        
    if not width or not height:
        print("Error: Could not determine image dimensions")
        return
        
    print(f"Processing {json_path}")
    print(f"Dimensions: {width}x{height}")
    
    # Create new blank mask (Black = Preserve)
    refined_mask = np.zeros((height, width), dtype=np.uint8)
    
    regions = data.get("regions", [])
    included_count = 0
    excluded_count = 0
    
    print("-" * 50)
    for region in regions:
        text = region.get("text_content", {}).get("text", "N/A")
        role = region.get("text_content", {}).get("role", "unknown")
        
        if is_safe_to_remove(region):
            # Draw on mask (White = Remove)
            polygon = region.get("polygon")
            
            if polygon:
                pts = np.array(polygon, np.int32)
                pts = pts.reshape((-1, 1, 2))
                cv2.fillPoly(refined_mask, [pts], 255)
            else:
                # Fallback to bbox
                bbox = region.get("bbox", {})
                x, y, w, h = bbox["x"], bbox["y"], bbox["width"], bbox["height"]
                cv2.rectangle(refined_mask, (x, y), (x+w, y+h), 255, -1)
                
            print(f"✅ MASKED: {role} | {text[:40]}")
            included_count += 1
        else:
            print(f"❌ SKIPPED: {role} | {text[:40]}")
            excluded_count += 1
            
    print("-" * 50)
    print(f"Total Regions: {len(regions)}")
    print(f"Masked (to remove): {included_count}")
    print(f"Skipped (preserve): {excluded_count}")
    
    # --------------------------------------------------
    # DILATION (Important for Inpainting)
    # --------------------------------------------------
    # Dilate the refined mask slightly to ensure edges are covered
    kernel = np.ones((5, 5), np.uint8)
    refined_mask = cv2.dilate(refined_mask, kernel, iterations=2)
    print("Applied dilation (5x5 kernel, 2 iterations)")
    
    # --------------------------------------------------
    # SAVE & REPLACE
    # --------------------------------------------------
    
    # Backup raw mask if it exists and hasn't been backed up
    raw_backup_path = pipeline_dir / "text_mask_raw_craft.png"
    if raw_mask_path.exists() and not raw_backup_path.exists():
        shutil.copy2(raw_mask_path, raw_backup_path)
        print(f"Backed up raw CRAFT mask to: {raw_backup_path}")
        
    # Save refined mask
    cv2.imwrite(str(raw_mask_path), refined_mask)
    print(f"✅ Saved REFINED mask to: {raw_mask_path}")
    print("(This replaces the original mask so remove_text_gemini.py will use it automatically)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Refine inpainting mask using JSON semantics")
    parser.add_argument(
        "pipeline_dir",
        nargs="?",
        default="pipeline_outputs/run_1766739537_pro",
        help="Path to pipeline output directory"
    )
    
    args = parser.parse_args()
    refine_mask(args.pipeline_dir)
