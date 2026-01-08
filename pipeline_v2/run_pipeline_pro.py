"""
Enhanced Pipeline with Pro Model and Smart Font Normalization
==============================================================
Uses:
- gemini-2.5-pro for better font weight detection
- Numeric weights (100-900)
- Smart font fallback when weight not available
"""

import os
import json
import time
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Import stages
from text_detector_craft import CraftTextDetector
from gemini_text_analysis_pro import analyze_text_crops_batch
from font_normalizer_v2 import normalize_font_and_weight, load_google_fonts_cache

# Load env for Gemini/Google Fonts
load_dotenv()

def run_pipeline(image_path: str, output_base: str = "pipeline_outputs"):
    """
    Run enhanced pipeline with better font weight detection.
    1. CRAFT Detection (BBox + Cropping)
    2. Gemini Pro Analysis (Better weight detection)
    3. Smart Font Normalization (Fallback to similar fonts)
    """
    
    # ------------------------------------------------------------------
    # SETUP
    # ------------------------------------------------------------------
    image_path = Path(image_path)
    if not image_path.exists():
        print(f"Error: Image not found at {image_path}")
        return

    # Create run folder
    run_id = int(time.time())
    run_dir = Path(output_base) / f"run_{run_id}_pro"
    run_dir.mkdir(parents=True, exist_ok=True)
    
    timing_stats = {}
    print(f"Starting ENHANCED pipeline for: {image_path.name}")
    print(f"Output directory: {run_dir}")
    print(f"Using: gemini-2.5-pro + numeric weights + smart fallback")

    # ------------------------------------------------------------------
    # STEP 1: CRAFT Text Detection
    # ------------------------------------------------------------------
    print("\n[STEP 1] Running CRAFT Text Detection...")
    t0 = time.time()
    
    detector = CraftTextDetector(
        text_threshold=0.7,
        link_threshold=0.4,
        cuda=False,
        merge_lines=True 
    )
    
    craft_result = detector.detect(str(image_path))
    
    # Save Crops
    crops_dir = run_dir / "crops"
    crops_dir.mkdir(parents=True, exist_ok=True)
    
    import base64
    for region in craft_result["text_regions"]:
        b64 = region["cropped_base64"]
        if "base64," in b64:
            b64 = b64.split("base64,")[1]
        img_data = base64.b64decode(b64)
        
        crop_path = crops_dir / f"region_{region['id']}.png"
        with open(crop_path, "wb") as f:
            f.write(img_data)
    
    t1 = time.time()
    timing_stats["step_1_craft_detection"] = round(t1 - t0, 4)
    print(f"  > Detected {craft_result['total_regions']} regions")
    print(f"  > Time: {timing_stats['step_1_craft_detection']} s")
    
    # Generate visualization with bounding boxes
    import cv2
    vis_image = cv2.imread(str(image_path))
    for region in craft_result["text_regions"]:
        bbox = region["bbox"]
        x, y, w, h = bbox["x"], bbox["y"], bbox["width"], bbox["height"]
        
        # Draw rectangle (green)
        cv2.rectangle(vis_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
        
        # Draw region ID
        cv2.putText(
            vis_image, 
            f"#{region['id']}", 
            (x, y - 5),
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.6, 
            (0, 255, 0), 
            2
        )
    
    vis_path = run_dir / "segmentation_boxes.png"
    cv2.imwrite(str(vis_path), vis_image)
    print(f"  > Segmentation visualization: {vis_path}")
    
    # Generate binary mask for inpainting
    # White (255) = text regions to REMOVE
    # Black (0) = areas to PRESERVE
    import numpy as np
    img_height = craft_result["image_dimensions"]["height"]
    img_width = craft_result["image_dimensions"]["width"]
    binary_mask = np.zeros((img_height, img_width), dtype=np.uint8)
    
    for region in craft_result["text_regions"]:
        bbox = region["bbox"]
        x, y, w, h = bbox["x"], bbox["y"], bbox["width"], bbox["height"]
        
        # Clamp to image boundaries
        x = max(0, x)
        y = max(0, y)
        x2 = min(img_width, x + w)
        y2 = min(img_height, y + h)
        
        # Fill text region with white (255)
        binary_mask[y:y2, x:x2] = 255
    
    mask_path = run_dir / "text_mask.png"
    cv2.imwrite(str(mask_path), binary_mask)
    print(f"  > Binary mask (for inpainting): {mask_path}")

    # ------------------------------------------------------------------
    # STEP 2: Gemini Pro BATCH Text Analysis
    # ------------------------------------------------------------------
    print("\n[STEP 2] Running Gemini Pro BATCH Analysis...")
    t2_start = time.time()
    
    crop_files = sorted(list(crops_dir.glob("*.png")))
    
    if not crop_files:
        print("  > No crops to analyze.")
        gemini_results_list = []
    else:
        print(f"  > Sending {len(crop_files)} crops to gemini-2.5-pro...")
        try:
            crop_paths_str = [str(p) for p in crop_files]
            analysis_list = analyze_text_crops_batch(crop_paths_str)
            
            gemini_results_list = []
            count = min(len(crop_files), len(analysis_list))
            
            for i in range(count):
                crop_file = crop_files[i]
                analysis = analysis_list[i]
                
                gemini_results_list.append({
                    "region_id": crop_file.stem.split("_")[-1], 
                    "crop_path": str(crop_file),
                    "analysis": analysis
                })
                
            if len(analysis_list) < len(crop_files):
                print(f"    ! Warning: Received fewer results ({len(analysis_list)}) than crops ({len(crop_files)})")
                
        except Exception as e:
            print(f"    ! Batch Analysis Failed: {e}")
            gemini_results_list = []

    t2_end = time.time()
    timing_stats["step_2_gemini_pro_analysis"] = round(t2_end - t2_start, 4)
    print(f"  > Analyzed {len(crop_files)} crops")
    print(f"  > Time: {timing_stats['step_2_gemini_pro_analysis']} s")

    # ------------------------------------------------------------------
    # STEP 3: Smart Font Normalization
    # ------------------------------------------------------------------
    print("\n[STEP 3] Running Smart Font Normalization...")
    t3_start = time.time()
    
    # Load fonts cache once
    fonts_cache = load_google_fonts_cache()
    
    final_output_regions = []
    gemini_map = {str(res["region_id"]): res for res in gemini_results_list}
    
    for craft_region in craft_result["text_regions"]:
        rid = str(craft_region["id"])
        
        combined_data = {
            "id": craft_region["id"],
            "bbox": craft_region["bbox"],
            "polygon": craft_region["polygon"],
            "text_content": {},
        }
        
        if rid in gemini_map and "analysis" in gemini_map[rid]:
            g_data = gemini_map[rid]["analysis"]
            
            # Get values (font_weight is now numeric from pro model)
            primary = g_data.get("primary_font", "")
            fallback = g_data.get("fallback_font", "")
            weight = g_data.get("font_weight", 400)
            
            # Smart normalization with fallback
            norm_font, norm_weight = normalize_font_and_weight(
                primary, fallback, weight, fonts_cache
            )
            
            combined_data["text_content"] = {
                "text": g_data.get("text", ""),
                "role": g_data.get("role", "body"),
                "raw_font": primary,
                "raw_weight": weight,
                "normalized_font": norm_font,
                "normalized_weight": norm_weight,
                "text_case": g_data.get("text_case", "sentencecase"),
                "color": g_data.get("text_color", "#000000")
            }
            
        final_output_regions.append(combined_data)

    t3_end = time.time()
    timing_stats["step_3_font_normalization"] = round(t3_end - t3_start, 4)
    timing_stats["total_pipeline_time"] = round(t3_end - t0, 4)
    print(f"  > Time: {timing_stats['step_3_font_normalization']} s")

    # ------------------------------------------------------------------
    # REPORTING
    # ------------------------------------------------------------------
    
    final_json = {
        "image": str(image_path),
        "dimensions": craft_result["image_dimensions"],
        "pipeline_timing": timing_stats,
        "model_used": "gemini-2.5-pro",
        "regions": final_output_regions
    }
    
    output_json_path = run_dir / "final_result_pro.json"
    with open(output_json_path, "w") as f:
        json.dump(final_json, f, indent=2)
        
    print("\n" + "="*50)
    print("ENHANCED PIPELINE SUMMARY")
    print("="*50)
    print(f"Image: {image_path.name}")
    print(f"Model: gemini-2.5-pro")
    print(f"Total Time: {timing_stats['total_pipeline_time']} s")
    print("-" * 30)
    print(f"CRAFT Detection : {timing_stats['step_1_craft_detection']} s")
    print(f"Gemini Pro      : {timing_stats['step_2_gemini_pro_analysis']} s")
    print(f"Font Norm       : {timing_stats['step_3_font_normalization']} s")
    print("="*50)
    print(f"\n✅ Results saved to: {output_json_path}")
    
    return output_json_path


if __name__ == "__main__":
    TEST_IMAGE_PATH = "image/t4.png" 
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", default=TEST_IMAGE_PATH, help="Path to image file")
    args = parser.parse_args()
    
    run_pipeline(args.image)
