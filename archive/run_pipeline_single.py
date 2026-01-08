import os
import json
import time
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Import stages
from text_detector_craft import CraftTextDetector
from gemini_text_analysis import analyze_text_crop
from font_normalizer import normalize_font_and_weight

# Load env for Gemini/Google Fonts
load_dotenv()

def run_pipeline(image_path: str, output_base: str = "pipeline_outputs"):
    """
    Run the full text analysis pipeline on a single image.
    1. CRAFT Detection (BBox + Cropping)
    2. Gemini Analysis (Text + Font + Style)
    3. Font Normalization (Standardize weights)
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
    run_dir = Path(output_base) / f"run_{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    
    timing_stats = {}
    print(f"Starting pipeline for: {image_path.name}")
    print(f"Output directory: {run_dir}")

    # ------------------------------------------------------------------
    # STEP 1: CRAFT Text Detection
    # ------------------------------------------------------------------
    print("\n[STEP 1] Running CRAFT Text Detection...")
    t0 = time.time()
    
    detector = CraftTextDetector(
        text_threshold=0.7,
        link_threshold=0.4,
        cuda=False,  # Set True if GPU available
        merge_lines=True 
    )
    
    # Detect
    craft_result = detector.detect(str(image_path))
    
    # Save Crops
    crops_dir = run_dir / "crops"
    crops_dir.mkdir(parents=True, exist_ok=True)
    
    import base64
    for region in craft_result["text_regions"]:
        # Decode base64
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

    # ------------------------------------------------------------------
    # STEP 2: Gemini Text Analysis
    # ------------------------------------------------------------------
    print("\n[STEP 2] Running Gemini Text Analysis...")
    t2_start = time.time()
    
    gemini_results = []
    crop_files = sorted(list(crops_dir.glob("*.png")))
    
    for crop_file in crop_files:
        print(f"  > Analyzing {crop_file.name}...")
        try:
            # Call Gemini
            analysis = analyze_text_crop(str(crop_file))
            
            gemini_results.append({
                "region_id": crop_file.stem.split("_")[-1], # region_1 -> 1
                "crop_path": str(crop_file),
                "analysis": analysis
            })
        except Exception as e:
            print(f"    ! Failed on {crop_file.name}: {e}")
            gemini_results.append({
                "region_id": crop_file.stem.split("_")[-1],
                "error": str(e)
            })
            
    t2_end = time.time()
    timing_stats["step_2_gemini_analysis"] = round(t2_end - t2_start, 4)
    print(f"  > Analyzed {len(crop_files)} crops")
    print(f"  > Time: {timing_stats['step_2_gemini_analysis']} s")

    # ------------------------------------------------------------------
    # STEP 3: Font Normalization
    # ------------------------------------------------------------------
    print("\n[STEP 3] Running Font Normalization...")
    t3_start = time.time()
    
    final_output_regions = []
    
    # Merge CRAFT bbox with Gemini text + Norm fonts
    # Map gemini result by region_id
    gemini_map = {str(res["region_id"]): res for res in gemini_results}
    
    for craft_region in craft_result["text_regions"]:
        rid = str(craft_region["id"])
        
        combined_data = {
            "id": craft_region["id"],
            "bbox": craft_region["bbox"],
            "polygon": craft_region["polygon"],
            # Default empty analysis
            "text_content": {},
        }
        
        if rid in gemini_map and "analysis" in gemini_map[rid]:
            g_data = gemini_map[rid]["analysis"]
            
            # Normalize
            primary = g_data.get("primary_font", "")
            fallback = g_data.get("fallback_font", "")
            weight = g_data.get("font_weight", "regular")
            
            norm_font, norm_weight = normalize_font_and_weight(primary, fallback, weight)
            
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
    
    # Save Final JSON
    final_json = {
        "image": str(image_path),
        "dimensions": craft_result["image_dimensions"],
        "pipeline_timing": timing_stats,
        "regions": final_output_regions
    }
    
    output_json_path = run_dir / "final_result.json"
    with open(output_json_path, "w") as f:
        json.dump(final_json, f, indent=2)
        
    print("\n" + "="*50)
    print("PIPELINE SUMMARY")
    print("="*50)
    print(f"Image: {image_path.name}")
    print(f"Total Time: {timing_stats['total_pipeline_time']} s")
    print("-" * 30)
    print(f"CRAFT Detection : {timing_stats['step_1_craft_detection']} s")
    print(f"Gemini Analysis : {timing_stats['step_2_gemini_analysis']} s")
    print(f"Font Norm       : {timing_stats['step_3_font_normalization']} s")
    print("="*50)
    print(f"\n✅ Results saved to: {output_json_path}")


if __name__ == "__main__":
    # Change this path to test a different image
    TEST_IMAGE_PATH = "image/382314b2-f5d7-4158-9b37-f8830d7dc0f4_detected.png" 
    
    # Or use argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", default=TEST_IMAGE_PATH, help="Path to image file")
    args = parser.parse_args()
    
    run_pipeline(args.image)
