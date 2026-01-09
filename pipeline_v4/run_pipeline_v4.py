"""
Combined Pipeline V4 (End-to-End)
==================================
Runs the full pipeline from Layering -> Box Detection -> Text Rendering.
Can take either an Image Path (starts fresh) or a Run Directory (resumes).
"""

import os
import sys
import json
import argparse
from pathlib import Path
from PIL import Image

# -----------------------------------------------------------------------------
# SETUP PATHS
# -----------------------------------------------------------------------------
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

# Add 'rendering' to path for font loader
sys.path.append(os.path.join(os.path.dirname(__file__), "rendering"))

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------
try:
    from run_pipeline_layered_v4 import run_pipeline_layered
    from run_pipeline_box_detection_v4 import run_box_detection_pipeline
    from run_pipeline_text_rendering_v4 import (
        composite_layers, 
        draw_background_boxes, 
        render_text_layer
    )
except ImportError as e:
    print(f"Error importing pipeline modules: {e}")
    print("Ensure all v4 pipeline scripts are in the same directory.")
    sys.exit(1)

# -----------------------------------------------------------------------------
# MAIN PIPELINE LOGIC
# -----------------------------------------------------------------------------

def run_full_pipeline(input_path: str):
    """
    Executes the COMPLETE pipeline sequence.
    """
    path_obj = Path(input_path)
    run_dir = None
    
    # ---------------------------------------------------------
    # STAGE 1: LAYERING & ANALYSIS
    # ---------------------------------------------------------
    if path_obj.is_file() and path_obj.suffix.lower() in ['.png', '.jpg', '.jpeg']:
        print(f"\n************************************************************")
        print(f"STAGE 1: STARTING LAYERING PIPELINE")
        print(f"Input Image: {input_path}")
        print(f"************************************************************")
        
        try:
            # run_pipeline_layered returns the new run directory
            run_dir = run_pipeline_layered(str(path_obj))
            print(f"Stage 1 Complete. Run Directory: {run_dir}")
        except Exception as e:
            print(f"!! CRITICAL: Stage 1 Failed: {e}")
            import traceback
            traceback.print_exc()
            return
            
    elif path_obj.is_dir() and "run_" in path_obj.name:
        print(f"\n[INFO] Resuming from existing run directory: {path_obj}")
        run_dir = str(path_obj)
        
    else:
        print(f"Error: Invalid input. Must be an image file (.png/.jpg) or a run directory.")
        return

    if not run_dir:
        print("Error: No valid run directory established.")
        return

    # ---------------------------------------------------------
    # STAGE 2: BOX DETECTION
    # ---------------------------------------------------------
    print(f"\n************************************************************")
    print(f"STAGE 2: BOX DETECTION")
    print(f"************************************************************")
    try:
        run_box_detection_pipeline(run_dir)
    except Exception as e:
        print(f"!! Box Detection Failed: {e}")
    
    # ---------------------------------------------------------
    # STAGE 3: TEXT RENDERING
    # ---------------------------------------------------------
    print(f"\n************************************************************")
    print(f"STAGE 3: TEXT RENDERING")
    print(f"************************************************************")
    
    run_path = Path(run_dir)
    
    # Load the updated report
    report_with_boxes = run_path / "pipeline_report_with_boxes.json"
    report_orig = run_path / "pipeline_report.json"
    
    report_file = report_with_boxes if report_with_boxes.exists() else report_orig
    
    if not report_file.exists():
        print(f"Error: No pipeline report found in {run_dir}")
        return
        
    print(f"Loading report: {report_file.name}")
    with open(report_file, "r") as f:
        report = json.load(f)
        
    # Get original image dimensions
    input_filename = report.get("input_image", "")
    orig_w, orig_h = 1080, 1920  # Fallback
    
    if input_filename:
        # Try to resolve absolute path of input image
        possible_paths = [
            Path(input_filename),
            Path(run_dir).parent.parent / "image" / Path(input_filename).name,
            Path("c:/Users/harsh/Downloads/zocket/product_pipeline/image") / Path(input_filename).name
        ]
        
        for p in possible_paths:
            if p.exists():
                try:
                    with Image.open(p) as orig_img:
                        orig_w, orig_h = orig_img.size
                    print(f"Original image size detected: {orig_w}x{orig_h}")
                    break
                except:
                    continue
    
    try:
        # 1. Composite Layers
        print(" -> Compositing layers...")
        final_img = composite_layers(run_dir, report)
        if final_img is None:
            print("Error: Failed to composite layers.")
            return

        # 2. Composite Background Boxes (CTAs)
        print(" -> Drawing background boxes...")
        final_img = draw_background_boxes(final_img, report, orig_w, orig_h, run_dir)

        # 3. Render Text
        print(" -> Rendering text...")
        final_img = render_text_layer(final_img, report)

        # 4. Save Final Output
        out_path = run_path / "final_composed.png"
        final_img.save(out_path)
        print(f"\n>>> SUCCESS! Final combined image saved to:")
        print(f"{out_path}")
        
    except Exception as e:
        print(f"!! Text Rendering Failed: {e}")
        import traceback
        traceback.print_exc()

# -----------------------------------------------------------------------------
# ENTRY POINT
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    # --- CONFIGURATION: SET YOUR IMAGE PATH HERE ---
    DEFAULT_INPUT = r"image/t1.jpg" 
    # Example: "image/test_image.png" OR "pipeline_outputs/run_123..."
    
    target = None
    
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        # Use default if no arg provided
        target = DEFAULT_INPUT
        if "YOUR_IMAGE_HERE" in target:
            print("Usage: python run_pipeline_v4.py <IMAGE_PATH_OR_RUN_DIR>")
            print(f"OR update 'DEFAULT_INPUT' in {__file__}")
            sys.exit(1)
            
    print(f"Running pipeline on: {target}")
    run_full_pipeline(target)
