"""
Post-Inpaint JSON Filtering
============================
Filters text regions AFTER Gemini inpainting but BEFORE Pillow rendering.

Purpose:
- Remove non-editable regions (logos, UI elements) that Gemini correctly preserved
- Keep only regions that were actually inpainted (removed by Gemini)

Decision rule:
- If a region's bounding box has >= 20% overlap with the text mask → KEEP (was inpainted)
- If a region's bounding box has < 20% overlap with the text mask → DROP (was preserved)

Usage:
    python filter_text_regions_after_inpaint.py pipeline_outputs/run_XXXX_pro

Pipeline position:
    CRAFT → Gemini Inpainting → [THIS STEP] → Pillow Rendering
"""

import os
import json
import argparse
from pathlib import Path
import cv2
import numpy as np


def calculate_mask_overlap(bbox: dict, mask: np.ndarray) -> float:
    """
    Calculate what fraction of the bounding box overlaps with the white mask.
    
    Args:
        bbox: Dict with x, y, width, height
        mask: Grayscale mask image (white=255 for text areas)
    
    Returns:
        Overlap ratio (0.0 to 1.0)
    """
    x, y, w, h = bbox["x"], bbox["y"], bbox["width"], bbox["height"]
    
    # Clamp to image boundaries
    img_h, img_w = mask.shape
    x = max(0, x)
    y = max(0, y)
    x2 = min(img_w, x + w)
    y2 = min(img_h, y + h)
    
    # Check for valid region
    if x2 <= x or y2 <= y:
        return 0.0
    
    # Extract mask region
    mask_region = mask[y:y2, x:x2]
    
    # Count white pixels (value > 127 considered white)
    white_pixels = np.sum(mask_region > 127)
    total_pixels = mask_region.size
    
    if total_pixels == 0:
        return 0.0
    
    return white_pixels / total_pixels


def filter_regions(pipeline_dir: str, overlap_threshold: float = 0.20):
    """
    Filter text regions based on mask overlap.
    
    Creates final_result_editable.json containing only regions that were
    actually inpainted (have sufficient mask overlap).
    
    Args:
        pipeline_dir: Path to pipeline output directory
        overlap_threshold: Minimum overlap ratio to keep a region (default: 0.20 = 20%)
    """
    pipeline_dir = Path(pipeline_dir)
    
    # Input files
    json_path = pipeline_dir / "final_result_pro.json"
    mask_path = pipeline_dir / "text_mask.png"
    
    # Output file
    output_path = pipeline_dir / "final_result_editable.json"
    
    # Validate inputs
    if not json_path.exists():
        print(f"Error: {json_path} not found")
        return
    
    if not mask_path.exists():
        print(f"Error: {mask_path} not found")
        return
    
    # Load JSON
    with open(json_path, "r") as f:
        data = json.load(f)
    
    # Load mask
    mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
    if mask is None:
        print(f"Error: Could not read mask from {mask_path}")
        return
    
    print(f"Input JSON: {json_path}")
    print(f"Mask: {mask_path} ({mask.shape[1]}x{mask.shape[0]})")
    print(f"Overlap threshold: {overlap_threshold * 100:.0f}%")
    print("-" * 50)
    
    # Filter regions
    original_regions = data.get("regions", [])
    kept_regions = []
    dropped_regions = []
    
    for region in original_regions:
        bbox = region.get("bbox", {})
        text_content = region.get("text_content", {})
        text = text_content.get("text", "")
        
        # Calculate overlap
        overlap = calculate_mask_overlap(bbox, mask)
        
        if overlap >= overlap_threshold:
            # Keep - was inpainted
            kept_regions.append(region)
            status = "✅ KEEP"
        else:
            # Drop - was preserved by Gemini (logo, UI element, etc.)
            dropped_regions.append(region)
            status = "❌ DROP"
        
        print(f"{status} [{overlap*100:5.1f}%] {text[:40]}")
    
    print("-" * 50)
    print(f"Kept: {len(kept_regions)} regions")
    print(f"Dropped: {len(dropped_regions)} regions")
    
    # Create filtered JSON
    filtered_data = data.copy()
    filtered_data["regions"] = kept_regions
    filtered_data["filtering"] = {
        "overlap_threshold": overlap_threshold,
        "original_region_count": len(original_regions),
        "kept_region_count": len(kept_regions),
        "dropped_region_count": len(dropped_regions),
        "dropped_texts": [r.get("text_content", {}).get("text", "") for r in dropped_regions]
    }
    
    # Save filtered JSON
    with open(output_path, "w") as f:
        json.dump(filtered_data, f, indent=2)
    
    print(f"\n✅ Filtered JSON saved: {output_path}")
    print("Use this file for Pillow rendering instead of final_result_pro.json")
    
    return str(output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Filter text regions after inpainting based on mask overlap"
    )
    parser.add_argument(
        "pipeline_dir",
        nargs="?",
        default="pipeline_outputs/run_1766739537_pro",
        help="Path to pipeline output directory"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.20,
        help="Overlap threshold (0.0-1.0). Default: 0.20 (20%%)"
    )
    
    args = parser.parse_args()
    
    filter_regions(args.pipeline_dir, args.threshold)
