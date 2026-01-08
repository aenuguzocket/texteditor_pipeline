"""
Run Post-Processing Pipeline
=============================
Orchestrates the refined text removal and rendering workflow.
1. Refines mask based on JSON semantics (excludes logos/UI).
2. Runs Gemini inpainting with the refined mask.
3. Filters JSON to drop regions that weren't masked (preserved elements).
4. Renders the final result.

Usage:
    python run_post_processing.py pipeline_outputs/run_XXXX_pro
"""

import os
import argparse
import sys
import subprocess
from pathlib import Path

def run_step(script_name, args, description):
    print(f"\n{'='*60}")
    print(f"STEP: {description}")
    print(f"Running: {script_name} {' '.join(args)}")
    print(f"{'='*60}\n")
    
    cmd = [sys.executable, script_name] + args
    result = subprocess.run(cmd)
    
    if result.returncode != 0:
        print(f"❌ Error in {script_name}")
        sys.exit(result.returncode)

def main():
    parser = argparse.ArgumentParser(description="Run complete post-processing pipeline")
    parser.add_argument("pipeline_dir", help="Path to pipeline output directory")
    args = parser.parse_args()
    
    pipeline_dir = args.pipeline_dir
    
    # Get the directory where THIS script is located
    base_dir = Path(__file__).parent
    
    # helper to make path absolute/correct
    def get_script_path(name):
        return str(base_dir / name)
    
    # 1. Refine Mask
    run_step(
        get_script_path("refine_mask_by_semantics.py"), 
        [pipeline_dir],
        "Refining mask to exclude logos/UI elements"
    )
    
    # 2. Inpaint
    run_step(
        get_script_path("remove_text_gemini_pro.py"),
        [pipeline_dir],
        "Inpainting text using refined mask with exclusion handling"
    )
    
    # 3. Filter JSON
    run_step(
        get_script_path("filter_text_regions_after_inpaint.py"),
        [pipeline_dir],
        "Filtering JSON to remove preserved regions"
    )
    
    # 4. Render
    json_path = os.path.join(pipeline_dir, "final_result_editable.json")
    run_step(
        get_script_path("rendering/render_from_json_pillow.py"),
        [json_path],
        "Rendering final image"
    )
    
    print(f"\n✅ Post-processing complete for {pipeline_dir}")

if __name__ == "__main__":
    main()
