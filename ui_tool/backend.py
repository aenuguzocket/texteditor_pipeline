
import os
import json
from pathlib import Path
from PIL import Image
import cv2
import numpy as np

# Base path for pipeline outputs
PIPELINE_OUTPUTS_DIR = Path("pipeline_outputs")

def list_pipeline_runs():
    """
    List all available pipeline runs in the outputs directory.
    Returns a list of dicts with run details.
    """
    runs = []
    if not PIPELINE_OUTPUTS_DIR.exists():
        return []
    
    for entry in PIPELINE_OUTPUTS_DIR.iterdir():
        if entry.is_dir() and "run_" in entry.name:
            # Check for report
            report_path = entry / "pipeline_report.json"
            box_report_path = entry / "pipeline_report_with_boxes.json"
            
            has_report = report_path.exists() or box_report_path.exists()
            
            runs.append({
                "id": entry.name,
                "path": str(entry),
                "has_report": has_report,
                "timestamp": entry.stat().st_mtime
            })
    
    # Sort by new first
    runs.sort(key=lambda x: x["timestamp"], reverse=True)
    return runs

def load_run_data(run_id):
    """
    Load data for a specific run.
    - Loads JSON report
    - Composites background (cleaned layers)
    - Returns structured data for UI
    """
    run_dir = PIPELINE_OUTPUTS_DIR / run_id
    if not run_dir.exists():
        return None
        
    # 1. Load Report
    report_path = run_dir / "pipeline_report_with_boxes.json"
    if not report_path.exists():
        report_path = run_dir / "pipeline_report.json"
        
    if not report_path.exists():
        return {"error": "No report found"}
        
    with open(report_path, "r") as f:
        report = json.load(f)
        
    # 2. Composite Background (Cleaned Layers)
    # Logic: Merge all *_cleaned.png images in order
    layers_dir = run_dir / "layers"
    bg_image = None
    
    layer_files = sorted(list(layers_dir.glob("*_cleaned.png")))
    
    if not layer_files:
        # Fallback: Try loading 0_layer_0.png if no cleaned ones (unlikely for completed run)
        layer_files = sorted(list(layers_dir.glob("*.png")))
        # Filter out extracted boxes
        layer_files = [f for f in layer_files if "box_region" not in f.name and "layer" in f.name]
    
    if layer_files:
        # Composite
        base = Image.open(layer_files[0]).convert("RGBA")
        for layer_path in layer_files[1:]:
            overlay = Image.open(layer_path).convert("RGBA")
            if overlay.size != base.size:
                overlay = overlay.resize(base.size)
            base = Image.alpha_composite(base, overlay)
        bg_image = base
        
        # 3. "Erase" Detected Boxes from Background
        # The user wants movable buttons. The background shouldn't have them static.
        from PIL import ImageDraw
        draw = ImageDraw.Draw(bg_image)
        # Use simple "Erasure" mode (drawing transparent rectangle)
        # Note: 'fill' with (0,0,0,0) works if mode is RGBA, but we need to composite "Source" mode usually?
        # Actually ImageDraw on RGBA simple fill replaces pixels? No, it alpha blends by default.
        # To CUT OUT, we need to manipulate pixels or use mask. 
        # Easier way: Draw with operator to clear.
        
        text_regions = report.get("text_detection", {}).get("regions", [])
        for region in text_regions:
            bg_box = region.get("background_box", {})
            if bg_box.get("detected"):
                bbox = bg_box["bbox"]
                x, y, w, h = bbox["x"], bbox["y"], bbox["width"], bbox["height"]
                # In PIL, to erase, we can paste a transparent patch?
                # Or use ImageDraw with ink 0 and correct operator?
                # Simplest reliable way for rectangular cut:
                # bg_image.paste((0,0,0,0), (x, y, x+w, y+h))
                
                # Careful: 'paste' with 4-tuple color fills the region.
                bg_image.paste((0,0,0,0), (x, y, x + w, y + h))
                
    else:
        # Fallback if no layers found
        bg_image = Image.new("RGBA", (1080, 1920), (255, 255, 255, 255))
        
    # Valid Original Size Extraction
    original_size = report.get("original_size")
    if not original_size:
        # Fallback to Text Detection metadata or defaults
        # V1 sometimes puts it differently? For now default to bg_image size if missing (Legacy)
        original_size = {"width": bg_image.width, "height": bg_image.height}
    
    return {
        "report": report,
        "background_image": bg_image,
        "original_size": original_size,
        "run_dir": str(run_dir.resolve().absolute())
    }

def get_draggable_objects(report, canvas_width, canvas_height):
    """
    Convert report regions into canvas objects.
    Scales coordinates to canvas size.
    """
    objects = []
    
    # Get original dimensions from report or specific field
    # Usually we don't store orig size explicitly in V1/V2 reports, but V4 has it.
    # We can infer from background image size passed in UI, but here we need scale.
    # Let's assume the caller passes the original image size as reference.
    # BUT, the report coordinates are in Original Image Space.
    
    # We need the original dimensions to calculate scale.
    # In V4, 'original_size' is in report.
    # In V1/V2, it's not always there. We might need to rely on the background image size we just loaded.
    
    # This logic should be handled by the UI scaling, but let's prepare the raw objects here.
    # Actually, easy way: return raw objects and let UI handle scaling.
    
    text_regions = report.get("text_detection", {}).get("regions", [])
    
    # TEXT OBJECTS
    for region in text_regions:
        gemini = region.get("gemini_analysis", {})
        if not gemini: continue
        
        role = gemini.get("role", "body")
        # specific logic: skip product/logo usually
        if role in ["product_text", "logo"]:
             continue
             
        # Check if it has a background box (CTA)
        # If it has a detected background box, we render the BOX first, then TEXT.
        # But here we return a list. Order matters (z-index).
        pass

    return text_regions
