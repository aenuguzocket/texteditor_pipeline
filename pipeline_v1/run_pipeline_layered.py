"""
Layered Pipeline with Qwen + CRAFT + Gemini
===========================================
1. CRAFT: Detect text regions
2. Gemini: Classify regions (Keep vs Remove)
3. Qwen: Split image into layers (Text, Logo, UI, Base)
4. Cleanup: Erase "Remove" text pixels from Qwen layers deterministically
"""

import os
import sys
import time
import cv2
import json
import argparse
import numpy as np
from pathlib import Path
from dotenv import load_dotenv

# Add necessary paths
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "qwen_layered_runner"))

# Import stages
from text_detector_craft import CraftTextDetector
from gemini_text_analysis_pro import analyze_text_crops_batch
from run_qwen_layered import run_qwen_layered

load_dotenv()

def create_removable_mask(image_shape, craft_result, gemini_results):
    """
    Creates a binary mask (white = remove) based on CRAFT boxes 
    that Gemini identified as removable logic.
    """
    height, width = image_shape[:2]
    mask = np.zeros((height, width), dtype=np.uint8)
    
    gemini_map = {str(res["region_id"]): res["analysis"] for res in gemini_results}
    
    for region in craft_result["text_regions"]:
        rid = str(region["id"])
        
        # Default decision: keep if unknown, but usually we want to remove text
        # If Gemini says it's Product Text or Logo -> KEEP (do not mask)
        # Else (Headline, Body, CTA) -> REMOVE (mask = 255)
        
        role = "body" # default
        if rid in gemini_map:
            role = gemini_map[rid].get("role", "body").lower().strip()
            
        # Decision Logic
        # roles to KEEP: product_text, logo
        if role in ["product_text", "logo"]:
            continue
            
        # Draw on mask
        poly = np.array(region["polygon"]).astype(np.int32)
        cv2.fillPoly(mask, [poly], 255)
        
    return mask

def clean_layers(layer_paths, output_dir, global_craft_result, gemini_results, orig_size):
    """
    Refined Layer Cleaning Logic with Coordinate Scaling:
    1. Detect text on layer.
    2. Scale Global Regions to match Layer Dimensions.
    3. Check Global Context via Center-Point Containment.
    4. Priority Rule: If overlapping "product_text"/"logo" -> PRESERVE.
    5. Cleanup: Dilate mask to remove halos.
    """
    cleaned_paths = []
    cleaning_report = []
    
    # Initialize detector for layers
    detector = CraftTextDetector(cuda=False, merge_lines=True)
    
    # Map global region IDs to "role"
    global_roles = {}
    gemini_map = {str(res["region_id"]): res["analysis"] for res in gemini_results}
    
    for region in global_craft_result["text_regions"]:
        rid = str(region["id"])
        role = "body" # default
        if rid in gemini_map:
            role = gemini_map[rid].get("role", "body").lower().strip()
        global_roles[rid] = role

    print("\n  [DEBUG] Global Roles Mapping:")
    for rid, role in global_roles.items():
        print(f"    Region {rid}: {role}")

    print("\n  [Layer Cleaning Logic - Enhanced]")
    print("  - Strategy: Coordinate Scaling + Center-Point Containment + Semantic Priority + Dilation")
    
    orig_h, orig_w = orig_size[:2]
    
    for layer_path in layer_paths:
        path = Path(layer_path)
        if not path.exists():
            continue
            
        print(f"  > Processing layer: {path.name}")
        
        # 1. Detect text on this layer (Handling Transparency)
        # CRAFT might miss black text on transparent background (loaded as black).
        # We composite on white for detection.
        detection_target_path = str(path)
        temp_det_path = None
        
        try:
            raw_img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
            if raw_img is not None and raw_img.shape[2] == 4:
                # Composite on White
                b, g, r, a = cv2.split(raw_img)
                overlay = cv2.merge((b, g, r))
                mask = a / 255.0
                white = np.ones_like(overlay, dtype=np.uint8) * 255
                
                det_composite = (overlay * mask[:, :, None] + white * (1 - mask[:, :, None])).astype(np.uint8)
                
                # Save temp
                temp_det_path = path.parent / f"temp_det_{path.name}"
                cv2.imwrite(str(temp_det_path), det_composite)
                detection_target_path = str(temp_det_path)
        except Exception as e:
            print(f"    ! Warning: Transparency handling failed: {e}")

        try:
            layer_result = detector.detect(detection_target_path)
        except Exception as e:
            print(f"    ! Detection failed for layer (skipping clean): {e}")
            if temp_det_path and temp_det_path.exists():
                try: os.remove(temp_det_path)
                except: pass
            continue
            
        # Cleanup temp
        if temp_det_path and temp_det_path.exists():
            try: os.remove(temp_det_path)
            except: pass
            
        # 2. Build Mask for THIS layer
        h, w = layer_result["image_dimensions"]["height"], layer_result["image_dimensions"]["width"]
        
        # Calculate Scale Factor
        sx = w / orig_w
        sy = h / orig_h
        print(f"    @ Scale Factors: x={sx:.3f}, y={sy:.3f}")
        
        layer_mask = np.zeros((h, w), dtype=np.uint8)
        
        removable_regions_count = 0
        
        for local_region in layer_result["text_regions"]:
            local_bbox = local_region["bbox"]
            
            # Center Point of local text
            cx = local_bbox["x"] + local_bbox["width"] / 2
            cy = local_bbox["y"] + local_bbox["height"] / 2
            
            is_protected = False
            is_removable = False
            
            # Check against ALL global regions
            for global_region in global_craft_result["text_regions"]:
                g_bbox = global_region["bbox"]
                g_rid = str(global_region["id"])
                role = global_roles.get(g_rid, "body")
                
                # SCALE GLOBAL BBOX TO LAYER COORDS
                gx = g_bbox["x"] * sx
                gy = g_bbox["y"] * sy
                gw = g_bbox["width"] * sx
                gh = g_bbox["height"] * sy
                
                # Extract content
                analysis = gemini_map.get(g_rid, {})
                text_content = analysis.get("text", "").strip()
                
                # ADAPTIVE PADDING (handle resolution loss/jitter)
                # Max buffer (15px + 10%) to forcefully protect shifted product text
                pad_x = 15 + (gw * 0.10)
                pad_y = 15 + (gh * 0.10)
                
                gx_pad = gx - pad_x
                gy_pad = gy - pad_y
                gw_pad = gw + (2 * pad_x)
                gh_pad = gh + (2 * pad_y)
                
                # Check 1: Protection (ANY Overlap with PADDED Product Region)
                # Intersection logic
                x_left = max(local_bbox["x"], gx_pad)
                y_top = max(local_bbox["y"], gy_pad)
                x_right = min(local_bbox["x"] + local_bbox["width"], gx_pad + gw_pad)
                y_bottom = min(local_bbox["y"] + local_bbox["height"], gy_pad + gh_pad)
                
                if x_right > x_left and y_bottom > y_top:
                    # There is an intersection
                    if role in ["product_text", "ui_element", "logo"]:
                        is_protected = True
                        print(f"      [DEBUG] PROTECTING local {cx:.0f},{cy:.0f} due to Global {g_rid} ({role})")
                        break # Absolute priority
                
                # Check 2: Removal (Center Containment in PADDED Removable Region)
                if (gx_pad <= cx <= gx_pad + gw_pad and
                    gy_pad <= cy <= gy_pad + gh_pad):
                    
                    if role not in ["product_text", "ui_element", "logo"]:
                        # Only remove if Gemini actually found text
                        # (Prevents erasing UI elements/graphics that were false positives)
                        if text_content: 
                            is_removable = True
                            print(f"      [DEBUG] REMOVING local {cx:.0f},{cy:.0f} due to Global {g_rid} ({role})")
            
            # Decision Time
            if is_protected:
                continue
            elif is_removable:
                poly = np.array(local_region["polygon"]).astype(np.int32)
                cv2.fillPoly(layer_mask, [poly], 255)
                removable_regions_count += 1
        
        # 3. Apply Dilation & Erase
        should_clean = removable_regions_count > 0
        
        # Read layer (RGBA)
        img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if img is None: continue
        
        # Ensure RGBA
        if img.shape[2] == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
            
        cleaned_filename = path.stem + "_cleaned.png"
        cleaned_path = output_dir / cleaned_filename
        
        status = "preserved"
        action = "none"
        
        if should_clean:
            # DILATION: Expand mask slightly to catch halos
            kernel = np.ones((5, 5), np.uint8)
            layer_mask = cv2.dilate(layer_mask, kernel, iterations=1)
            
            # Erase pixels
            img[:, :, 3] = np.where(layer_mask == 255, 0, img[:, :, 3])
            print(f"    -> Erased {removable_regions_count} text regions from {path.name}")
            status = "cleaned"
            action = "erased_text"
        else:
            print(f"    -> No removable text found in {path.name}")
            
        cv2.imwrite(str(cleaned_path), img)
        cleaned_paths.append(str(cleaned_path))
        
        # Add to report
        cleaning_report.append({
            "original_layer": path.name,
            "cleaned_layer": cleaned_filename,
            "status": status,
            "action": action,
            "regions_removed": removable_regions_count
        })
        
    return cleaned_paths, cleaning_report

def run_pipeline_layered():
    # HARDCODED INPUTS
    IMAGE_PATH = r"image\IMAGE_CTA_BOX\Summit Clarity (1).png"
    MOCK_LAYERS_DIR = r"outputs\IMAGE_CTA_BOX\Summit Clarity (1)_2"
    
    image_path = Path(IMAGE_PATH)
    output_base = "pipeline_outputs"
    
    if not image_path.exists():
        print(f"Error: {image_path} not found")
        return

    # Setup run dir
    run_id = int(time.time())
    run_dir = Path(output_base) / f"run_{run_id}_layered"
    run_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Starting LAYERED pipeline for: {image_path.name}")
    print(f"Output directory: {run_dir}")
    print(f"Mock Layers: {MOCK_LAYERS_DIR}")
    
    # ------------------------------------------------------------------
    # STEP 1: CRAFT
    # ------------------------------------------------------------------
    print("\n[STEP 1] Running CRAFT (Global)...")
    detector = CraftTextDetector(cuda=False, merge_lines=True)
    craft_result = detector.detect(str(image_path))
    
    # Save crops for Gemini
    crops_dir = run_dir / "crops"
    crops_dir.mkdir(parents=True, exist_ok=True)
    import base64
    for region in craft_result["text_regions"]:
        b64 = region["cropped_base64"]
        if "base64," in b64: b64 = b64.split("base64,")[1]
        with open(crops_dir / f"region_{region['id']}.png", "wb") as f:
            f.write(base64.b64decode(b64))

    # ------------------------------------------------------------------
    # STEP 2: Gemini
    # ------------------------------------------------------------------
    print("\n[STEP 2] Running Gemini Analysis...")
    crop_files = sorted(list(crops_dir.glob("*.png")))
    gemini_results = []
    if crop_files:
        crop_paths_str = [str(p) for p in crop_files]
        try:
            analysis_list = analyze_text_crops_batch(crop_paths_str)
            # Safe loop
            count = min(len(crop_files), len(analysis_list))
            for i in range(count):
                crop = crop_files[i]
                gemini_results.append({
                    "region_id": crop.stem.split("_")[-1],
                    "analysis": analysis_list[i]
                })
        except Exception as e:
            print(f"Gemini failed: {e}")

    # ------------------------------------------------------------------
    # STEP 3: Qwen Layering (Mocked)
    # ------------------------------------------------------------------
    print("\n[STEP 3] Running Qwen Layering (Mocked)...")
    layers_dir = run_dir / "layers"
    layers_dir.mkdir(parents=True, exist_ok=True)
    
    layer_paths = []
    
    if MOCK_LAYERS_DIR and Path(MOCK_LAYERS_DIR).exists():
        print(f"Using pre-generated layers from: {MOCK_LAYERS_DIR}")
        import shutil
        mock_path = Path(MOCK_LAYERS_DIR)
        # Copy png files
        for f in sorted(mock_path.glob("*.png")):
            dest = layers_dir / f.name
            shutil.copy2(f, dest)
            layer_paths.append(str(dest))
            print(f"  > Copied layer: {dest}")
            
    else:
        print("Model usage disabled. Please check MOCK_LAYERS_DIR path.")
        return

    # ------------------------------------------------------------------
    # STEP 4: Layer Cleaning
    # ------------------------------------------------------------------
    print("\n[STEP 4] Cleaning Layers (Layer-Aware Pixel Erasure)...")
    
    # Load original image for dimensions
    orig_img = cv2.imread(str(image_path))
    
    # clean
    cleaned_layers, cleaning_report = clean_layers(layer_paths, layers_dir, craft_result, gemini_results, orig_img.shape)
    
    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------
    print("\n[Step 5] Generating JSON Report...")
    
    # Merge Gemini analysis into text regions for cleaner output
    gemini_map = {str(res["region_id"]): res["analysis"] for res in gemini_results}
    enriched_regions = []
    
    for region in craft_result["text_regions"]:
        rid = str(region["id"])
        r_data = region.copy()
        # Remove base64 to keep JSON small
        if "cropped_base64" in r_data:
            del r_data["cropped_base64"]
            
        if rid in gemini_map:
            r_data["gemini_analysis"] = gemini_map[rid]
        else:
            r_data["gemini_analysis"] = None
        
        enriched_regions.append(r_data)
        
    final_report = {
        "input_image": str(image_path.name),
        "pipeline_run_id": run_id,
        "text_detection": {
            "total_regions": craft_result["total_regions"],
            "regions": enriched_regions
        },
        "layer_cleaning": {
            "mock_source": MOCK_LAYERS_DIR,
            "layers_processed": cleaning_report
        }
    }
    
    report_path = run_dir / "pipeline_report.json"
    with open(report_path, "w") as f:
        json.dump(final_report, f, indent=2)
    
    print("\n" + "="*50)
    print("LAYERED PIPELINE COMPLETE")
    print(f"Report saved to: {report_path}")
    print(f"Cleaned layers saved to: {layers_dir}")
    print("="*50)

if __name__ == "__main__":
    run_pipeline_layered()
