
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "qwen_layered_runner"))

from qwen_layered_runner.run_qwen_layered import run_qwen_layered
from pipeline_v2.run_pipeline_layered import run_pipeline_layered
from pipeline_v2.run_pipeline_box_detection import run_box_detection_pipeline
from pipeline_v2.run_pipeline_text_rendering import run_text_rendering_pipeline

def run_full_pipeline(image_path_str: str, use_mock_qwen=True):
    print("="*60)
    print("STARTING FULL INTEGRATED PIPELINE")
    print(f"Target: {image_path_str}")
    print("="*60)
    
    # 1. Qwen Layering
    # For this verification, we use the EXISTING mock output to save time/cost 
    # and because the user just wants to verify logic integration.
    # But I will structure the code to allow real Qwen run.
    
    img_name = Path(image_path_str).stem
    # Convention: outputs/PARENT_FOLDER/ImageName
    # Parent folder of input is IMAGE_CTA_BOX
    parent_folder = Path(image_path_str).parent.name
    mock_dir = f"outputs/{parent_folder}/{img_name}"
    
    if use_mock_qwen and Path(mock_dir).exists():
        print(f"[Step 1] Using Pre-Generated Qwen Layers from: {mock_dir}")
        layers_source = mock_dir
    else:
        print(f"[Step 1] Mock layers not found or disabled. Running Qwen Layered (Fal.ai)...")
        # Ensure output directory exists
        qwen_output_path = Path("outputs") / parent_folder / img_name
        qwen_output_path.mkdir(parents=True, exist_ok=True)
        
        # Run Real Qwen
        # run_qwen_layered returns list of saved paths
        saved_paths = run_qwen_layered(image_path_str, output_dir=qwen_output_path)
        layers_source = str(qwen_output_path)
        print(f"Generated {len(saved_paths)} layers in {layers_source}")

    # 2. Layered Pipeline (Cleaning, Detection, etc.)
    print("\n[Step 2] Running Layered Pipeline (Cleaning & Logic)...")
    # This now returns path list, report list, AND removed_ids
    # But usually it saves to a timestamped RUN_ID folder.
    # Note: run_pipeline_layered now returns the cleaned paths etc, 
    # but the important part is it creates a "pipeline_outputs/run_..." folder.
    # and returns... wait, I need the RUN ID.
    
    # Run Pipeline Layered
    run_dir_str = run_pipeline_layered(image_path_str=image_path_str, mock_dir_str=mock_dir)
    print(f"\n[Step 2 Result] Run Directory: {run_dir_str}")
    
    if not run_dir_str:
        print("Error: Pipeline Layered failed to return valid run directory.")
        return

    # Extract Run ID from path (pipeline_outputs/RUN_ID)
    run_id = Path(run_dir_str).name
    
    # 3. Box Detection
    print("\n[Step 3] Running Background Box Detection...")
    run_box_detection_pipeline(run_dir_str)
    
    # 4. Text Rendering
    print("\n[Step 4] Running Text Rendering...")
    run_text_rendering_pipeline(run_id)
    
    print("\n" + "="*60)
    print("FULL PIPELINE EXECUTION COMPLETE")
    print(f"Final Output: {Path(run_dir_str) / 'final_composed.png'}")
    print("="*60)

if __name__ == "__main__":
    # Test on the target image
    run_full_pipeline("image/nano-banana-no-bg-2025-08-29T18-35-57.jpg", use_mock_qwen=True)
