"""
Filter Regions by Re-Detection on Inpainted Image
===================================================
Runs CRAFT on the inpainted image to detect what text STILL exists.
Regions that are no longer detected after inpainting → KEEP (successfully removed, need to re-render)
Regions that are still detected after inpainting → DROP (preserved by Gemini, e.g., logos)

Pipeline position:
    CRAFT → Gemini Inpainting → [THIS STEP] → Pillow Rendering

Usage:
    python filter_by_redetection.py pipeline_outputs/run_XXXX_pro
"""

import os
import json
import argparse
from pathlib import Path
import numpy as np

# Import CRAFT detector
from text_detector_craft import CraftTextDetector


def calculate_iou(box1: dict, box2: dict) -> float:
    """
    Calculate Intersection over Union (IoU) between two bounding boxes.
    
    Args:
        box1, box2: Dicts with x, y, width, height
    
    Returns:
        IoU value (0.0 to 1.0)
    """
    # Convert to (x1, y1, x2, y2) format
    x1_1, y1_1 = box1["x"], box1["y"]
    x2_1, y2_1 = x1_1 + box1["width"], y1_1 + box1["height"]
    
    x1_2, y1_2 = box2["x"], box2["y"]
    x2_2, y2_2 = x1_2 + box2["width"], y1_2 + box2["height"]
    
    # Calculate intersection
    xi1 = max(x1_1, x1_2)
    yi1 = max(y1_1, y1_2)
    xi2 = min(x2_1, x2_2)
    yi2 = min(y2_1, y2_2)
    
    if xi2 <= xi1 or yi2 <= yi1:
        return 0.0  # No intersection
    
    intersection = (xi2 - xi1) * (yi2 - yi1)
    
    # Calculate union
    area1 = box1["width"] * box1["height"]
    area2 = box2["width"] * box2["height"]
    union = area1 + area2 - intersection
    
    if union <= 0:
        return 0.0
    
    return intersection / union


def filter_by_redetection(pipeline_dir: str, iou_threshold: float = 0.3):
    """
    Filter regions by running CRAFT on inpainted image.
    
    Logic:
    - Run CRAFT on inpainted.png
    - For each original region, check if it overlaps with any detected region
    - If overlaps (IoU >= threshold) → DROP (text still exists, wasn't inpainted)
    - If no overlap → KEEP (text was removed, needs re-rendering)
    
    Args:
        pipeline_dir: Path to pipeline output directory
        iou_threshold: IoU threshold to consider a match (default: 0.3)
    """
    pipeline_dir = Path(pipeline_dir)
    
    # Input files
    json_path = pipeline_dir / "final_result_pro.json"
    inpainted_path = pipeline_dir / "inpainted.png"
    
    # Output file
    output_path = pipeline_dir / "final_result_editable.json"
    
    # Validate inputs
    if not json_path.exists():
        print(f"Error: {json_path} not found")
        return
    
    if not inpainted_path.exists():
        print(f"Error: {inpainted_path} not found")
        print("Run remove_text_gemini.py first to generate inpainted.png")
        return
    
    # Load original JSON
    with open(json_path, "r") as f:
        data = json.load(f)
    
    print(f"Original JSON: {json_path}")
    print(f"Inpainted image: {inpainted_path}")
    print(f"IoU threshold: {iou_threshold}")
    print("-" * 60)
    
    # Run CRAFT on inpainted image
    print("\n[STEP 1] Running CRAFT on inpainted image...")
    detector = CraftTextDetector(
        text_threshold=0.7,
        link_threshold=0.4,
        cuda=False,
        merge_lines=True
    )
    
    redetection_result = detector.detect(str(inpainted_path))
    redetected_regions = redetection_result.get("text_regions", [])
    
    print(f"  > Detected {len(redetected_regions)} regions in inpainted image")
    
    # Get dimension info for scaling
    from PIL import Image
    inpainted_img = Image.open(inpainted_path)
    inpainted_w, inpainted_h = inpainted_img.size
    
    original_dims = data.get("dimensions", {})
    original_w = original_dims.get("width", inpainted_w)
    original_h = original_dims.get("height", inpainted_h)
    
    # Calculate scale factors
    scale_x = original_w / inpainted_w
    scale_y = original_h / inpainted_h
    
    print(f"  > Original: {original_w}x{original_h}, Inpainted: {inpainted_w}x{inpainted_h}")
    print(f"  > Scale factors: x={scale_x:.2f}, y={scale_y:.2f}")
    
    # Save redetection visualization for debugging
    vis_path = pipeline_dir / "redetection_boxes.png"
    detector.visualize(str(inpainted_path), str(vis_path))
    print(f"  > Visualization saved: {vis_path}")
    
    # Extract bboxes from redetection and SCALE to original coordinates
    redetected_bboxes = []
    for r in redetected_regions:
        bbox = r["bbox"]
        scaled_bbox = {
            "x": int(bbox["x"] * scale_x),
            "y": int(bbox["y"] * scale_y),
            "width": int(bbox["width"] * scale_x),
            "height": int(bbox["height"] * scale_y)
        }
        redetected_bboxes.append(scaled_bbox)
    
    # Filter original regions
    print("\n[STEP 2] Filtering original regions...")
    original_regions = data.get("regions", [])
    kept_regions = []
    dropped_regions = []
    
    for region in original_regions:
        original_bbox = region.get("bbox", {})
        text_content = region.get("text_content", {})
        text = text_content.get("text", "")
        
        # Check overlap with any redetected region
        max_iou = 0.0
        for redetected_bbox in redetected_bboxes:
            iou = calculate_iou(original_bbox, redetected_bbox)
            max_iou = max(max_iou, iou)
        
        if max_iou >= iou_threshold:
            # Text still exists in inpainted image → DROP (was preserved)
            dropped_regions.append(region)
            status = "❌ DROP (still exists)"
        else:
            # Text was removed → KEEP (needs re-rendering)
            kept_regions.append(region)
            status = "✅ KEEP (was removed)"
        
        print(f"{status} [IoU: {max_iou*100:5.1f}%] {text[:50]}")
    
    print("-" * 60)
    print(f"Kept for rendering: {len(kept_regions)} regions")
    print(f"Dropped (preserved): {len(dropped_regions)} regions")
    
    # Create filtered JSON
    filtered_data = data.copy()
    filtered_data["regions"] = kept_regions
    filtered_data["redetection_filtering"] = {
        "iou_threshold": iou_threshold,
        "original_region_count": len(original_regions),
        "redetected_region_count": len(redetected_regions),
        "kept_region_count": len(kept_regions),
        "dropped_region_count": len(dropped_regions),
        "dropped_texts": [r.get("text_content", {}).get("text", "") for r in dropped_regions]
    }
    
    # Save filtered JSON
    with open(output_path, "w") as f:
        json.dump(filtered_data, f, indent=2)
    
    print(f"\n✅ Filtered JSON saved: {output_path}")
    print("Use this file for Pillow rendering.")
    
    return str(output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Filter regions by running CRAFT on inpainted image"
    )
    parser.add_argument(
        "pipeline_dir",
        nargs="?",
        default="pipeline_outputs/run_1766739537_pro",
        help="Path to pipeline output directory"
    )
    parser.add_argument(
        "--iou-threshold",
        type=float,
        default=0.3,
        help="IoU threshold to consider a match (0.0-1.0). Default: 0.3"
    )
    
    args = parser.parse_args()
    
    filter_by_redetection(args.pipeline_dir, args.iou_threshold)
