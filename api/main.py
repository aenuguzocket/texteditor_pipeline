"""
FastAPI Backend for Pipeline V4
================================
REST API for image processing and canvas editing.

Endpoints:
- POST /api/process - Upload image, run full pipeline
- GET /api/runs/{run_id} - Get pipeline run data
- POST /api/render - Render final image with edits
- GET /api/image/{run_id}/{filename} - Serve images
"""

import os
import sys
import json
import time
import shutil
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any
from io import BytesIO

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

# Add pipeline paths
API_DIR = Path(__file__).parent
ROOT_DIR = API_DIR.parent

# Add paths for imports
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "pipeline_v4"))
sys.path.insert(0, str(ROOT_DIR / "pipeline_v4" / "rendering"))

# Load environment variables (try both locations)
load_dotenv(ROOT_DIR / ".env")
load_dotenv(API_DIR / ".env")

# Import pipeline modules
try:
    from pipeline_v4.run_pipeline_layered_v4 import run_pipeline_layered
    from pipeline_v4.run_pipeline_v4 import run_pipeline_v4
    from pipeline_v4.run_pipeline_text_rendering_v4 import (
        composite_layers,
        draw_background_boxes,
        render_text_layer
    )
    from pipeline_v4.rendering.google_fonts_runtime_loader import get_font_path
except ImportError as e:
    print(f"Warning: Could not import pipeline modules: {e}")
    print("Some endpoints may not work correctly.")

# Initialize FastAPI
app = FastAPI(
    title="Pipeline V4 API",
    description="Image text detection and editing API",
    version="1.0.0"
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory for pipeline outputs
PIPELINE_OUTPUTS = ROOT_DIR / "pipeline_outputs"
PIPELINE_OUTPUTS.mkdir(exist_ok=True)

# Temporary upload directory
UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


# ============================================================================
# Pydantic Models
# ============================================================================

class BBox(BaseModel):
    x: int
    y: int
    width: int
    height: int


class TextRegion(BaseModel):
    id: str
    text: str
    bbox: BBox
    font: str = "Roboto"
    weight: int = 400
    color: str = "#000000"
    role: str = "body"


class BoxRegion(BaseModel):
    id: str
    bbox: BBox
    color: str = "#000000"


class ProcessResponse(BaseModel):
    run_id: str
    status: str
    original_size: Dict[str, int]
    background_url: str
    text_regions: List[TextRegion]
    box_regions: List[BoxRegion]


class RenderRequest(BaseModel):
    run_id: str
    text_regions: List[TextRegion]
    box_regions: List[BoxRegion]


class RenderResponse(BaseModel):
    success: bool
    image_url: str
    message: str


# ============================================================================
# Helper Functions
# ============================================================================

def extract_editable_regions(report: dict) -> tuple[List[dict], List[dict]]:
    """Extract text and box regions from pipeline report."""
    regions = report.get("text_detection", {}).get("regions", [])
    
    text_regions = []
    box_regions = []
    
    print(f"[DEBUG] Total regions in report: {len(regions)}")
    
    for region in regions:
        gemini = region.get("gemini_analysis")
        
        # Handle missing gemini_analysis
        if not gemini:
            print(f"[DEBUG] Region {region.get('id')} has no gemini_analysis, skipping")
            continue
        
        role = gemini.get("role", "").lower()
        
        # Skip non-editable roles
        if role not in ["heading", "subheading", "body", "cta", "usp"]:
            print(f"[DEBUG] Region {region.get('id')} has role '{role}', skipping (not editable)")
            continue
        
        # Skip residue
        if region.get("layer_residue", False):
            print(f"[DEBUG] Region {region.get('id')} is residue, skipping")
            continue
        
        # For USP, only include if extracted
        if role == "usp":
            bg_box = region.get("background_box", {})
            if not bg_box.get("detected", False):
                print(f"[DEBUG] Region {region.get('id')} is USP but not extracted, skipping")
                continue
        
        # Validate bbox exists
        bbox = region.get("bbox")
        if not bbox:
            print(f"[DEBUG] Region {region.get('id')} has no bbox, skipping")
            continue
        
        # Create text region
        text_data = {
            "id": str(region["id"]),
            "text": gemini.get("text", ""),
            "bbox": bbox,
            "font": gemini.get("primary_font", "Roboto"),
            "weight": gemini.get("font_weight", 400),
            "color": gemini.get("text_color", "#000000"),
            "role": role
        }
        
        print(f"[DEBUG] Adding text region: {text_data['id']} - '{text_data['text'][:30]}...'")
        text_regions.append(text_data)
        
        # Check for background box
        bg_box = region.get("background_box", {})
        if bg_box.get("detected", False):
            box_bbox = bg_box.get("bbox", bbox)
            if not box_bbox:
                print(f"[DEBUG] Box region {region.get('id')} has no bbox, skipping")
                continue
            box_data = {
                "id": str(region["id"]),
                "bbox": box_bbox,
                "color": bg_box.get("color", "#000000")
            }
            print(f"[DEBUG] Adding box region: {box_data['id']}")
            box_regions.append(box_data)
    
    print(f"[DEBUG] Extracted {len(text_regions)} text regions, {len(box_regions)} box regions")
    return text_regions, box_regions


def render_custom_image(
    base_image: Image.Image,
    text_regions: List[TextRegion],
    box_regions: List[BoxRegion]
) -> Image.Image:
    """Render image with custom text and box edits."""
    img = base_image.copy()
    draw = ImageDraw.Draw(img)
    
    # Draw boxes first (background)
    for box in box_regions:
        bbox = box.bbox
        color = box.color
        
        try:
            if color.startswith('#'):
                r = int(color[1:3], 16)
                g = int(color[3:5], 16)
                b = int(color[5:7], 16)
            else:
                r, g, b = 0, 0, 0
        except:
            r, g, b = 0, 0, 0
        
        x, y = bbox.x, bbox.y
        w, h = bbox.width, bbox.height
        draw.rectangle([x, y, x + w, y + h], fill=(r, g, b, 200))
    
    # Draw text on top
    for region in text_regions:
        text = region.text
        if not text.strip():
            continue
        
        bbox = region.bbox
        x, y = bbox.x, bbox.y
        w, h = bbox.width, bbox.height
        
        font_size = int(h * 0.7)
        color = region.color
        
        try:
            font_path = get_font_path(region.font, region.weight)
            font = ImageFont.truetype(font_path, font_size)
        except:
            font = ImageFont.load_default()
        
        try:
            text_bbox = font.getbbox(text)
            text_w = text_bbox[2] - text_bbox[0]
            text_h = text_bbox[3] - text_bbox[1]
            
            text_x = x + (w - text_w) / 2 - text_bbox[0]
            text_y = y + (h - text_h) / 2 - text_bbox[1]
            
            if color.startswith('#'):
                r = int(color[1:3], 16)
                g = int(color[3:5], 16)
                b = int(color[5:7], 16)
            else:
                r, g, b = 0, 0, 0
            
            draw.text((text_x, text_y), text, fill=(r, g, b), font=font)
        except Exception as e:
            print(f"Failed to render text: {e}")
    
    return img


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "Pipeline V4 API"}


@app.post("/api/process", response_model=ProcessResponse)
async def process_image(file: UploadFile = File(...)):
    """
    Upload an image and run the full pipeline.
    Returns processed regions for canvas editing.
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Save uploaded file
    timestamp = int(time.time())
    filename = f"{timestamp}_{file.filename}"
    upload_path = UPLOAD_DIR / filename
    
    try:
        with open(upload_path, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")
    
        # Run pipeline Stage 1: Layered pipeline
        try:
            run_dir = run_pipeline_layered(str(upload_path), mock_layers_dir=None)
            
            if not run_dir or not Path(run_dir).exists():
                raise Exception("Pipeline Stage 1 failed")
            
            # Run pipeline Stage 2 & 3: Box detection + Text rendering (using proper wrapper)
            # This ensures the exact same logic as the command-line pipeline
            run_pipeline_v4(run_dir)
            
            # Load report (with boxes)
            run_path = Path(run_dir)
            report_with_boxes = run_path / "pipeline_report_with_boxes.json"
            report_orig = run_path / "pipeline_report.json"
            report_file = report_with_boxes if report_with_boxes.exists() else report_orig
            
            if not report_file.exists():
                raise Exception("Pipeline report not found")
            
            with open(report_file, "r") as f:
                report = json.load(f)
            
            # Get original dimensions
            orig_w = report.get("original_size", {}).get("width", 1080)
            orig_h = report.get("original_size", {}).get("height", 1920)
            
            # Verify final_composed.png exists (created by run_pipeline_v4)
            final_path = run_path / "final_composed.png"
            if not final_path.exists():
                print(f"[WARNING] final_composed.png not found, pipeline may have failed")
                raise Exception("Final composed image not created by pipeline")
            
            print(f"[DEBUG] Using final_composed.png from pipeline: {final_path}")
            
            # Extract editable regions
            text_regions, box_regions = extract_editable_regions(report)
            
            run_id = run_path.name
            
            return ProcessResponse(
                run_id=run_id,
                status="success",
                original_size={"width": orig_w, "height": orig_h},
                background_url=f"/api/image/{run_id}/final_composed.png",
                text_regions=[TextRegion(**r) for r in text_regions],
                box_regions=[BoxRegion(**r) for r in box_regions]
            )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")
    
    finally:
        # Cleanup uploaded file
        if upload_path.exists():
            upload_path.unlink()


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str):
    """Get pipeline run data including report and image URLs."""
    run_path = PIPELINE_OUTPUTS / run_id
    
    if not run_path.exists():
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    
    # Load report
    report_with_boxes = run_path / "pipeline_report_with_boxes.json"
    report_orig = run_path / "pipeline_report.json"
    report_file = report_with_boxes if report_with_boxes.exists() else report_orig
    
    if not report_file.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    
    with open(report_file, "r") as f:
        report = json.load(f)
    
    # Extract regions
    text_regions, box_regions = extract_editable_regions(report)
    
    orig_w = report.get("original_size", {}).get("width", 1080)
    orig_h = report.get("original_size", {}).get("height", 1920)
    
    # Check for final composed image
    final_path = run_path / "final_composed.png"
    if not final_path.exists():
        # Run the proper pipeline to create it
        print(f"[INFO] final_composed.png not found, running pipeline_v4 to create it...")
        try:
            run_pipeline_v4(str(run_path))
        except Exception as e:
            print(f"[WARNING] Failed to create final image in get_run: {e}")
            import traceback
            traceback.print_exc()
    
    return {
        "run_id": run_id,
        "status": "success",
        "original_size": {"width": orig_w, "height": orig_h},
        "background_url": f"/api/image/{run_id}/final_composed.png",
        "text_regions": text_regions,
        "box_regions": box_regions
    }


@app.get("/api/runs")
async def list_runs():
    """List all available pipeline runs."""
    runs = []
    
    for run_dir in sorted(PIPELINE_OUTPUTS.iterdir(), reverse=True):
        if run_dir.is_dir() and "layered" in run_dir.name:
            report_file = run_dir / "pipeline_report_with_boxes.json"
            if not report_file.exists():
                report_file = run_dir / "pipeline_report.json"
            
            if report_file.exists():
                with open(report_file, "r") as f:
                    report = json.load(f)
                
                runs.append({
                    "run_id": run_dir.name,
                    "input_image": report.get("input_image", ""),
                    "created_at": run_dir.stat().st_mtime
                })
    
    return {"runs": runs}


@app.post("/api/render", response_model=RenderResponse)
async def render_image(request: RenderRequest):
    """Render final image with edited text and box regions."""
    run_path = PIPELINE_OUTPUTS / request.run_id
    
    if not run_path.exists():
        raise HTTPException(status_code=404, detail=f"Run not found: {request.run_id}")
    
    # Load report to get base image
    report_file = run_path / "pipeline_report_with_boxes.json"
    if not report_file.exists():
        report_file = run_path / "pipeline_report.json"
    
    if not report_file.exists():
        raise HTTPException(status_code=404, detail="Pipeline report not found")
    
    with open(report_file, "r") as f:
        report = json.load(f)
    
    orig_w = report.get("original_size", {}).get("width", 1080)
    orig_h = report.get("original_size", {}).get("height", 1920)
    
    try:
        # Create base image: cleaned layers + extracted boxes (without text)
        # This matches the pipeline logic exactly
        base_img = composite_layers(str(run_path), report)
        if not base_img:
            raise Exception("Failed to composite layers")
        
        # Add extracted background boxes (these already have text filled with box color)
        base_img = draw_background_boxes(base_img, report, orig_w, orig_h, str(run_path))
        
        # Now render custom text and boxes on top
        final_img = render_custom_image(
            base_img,
            request.text_regions,
            request.box_regions
        )
        
        # Save
        output_filename = f"edited_{int(time.time())}.png"
        output_path = run_path / output_filename
        final_img.save(output_path)
        
        return RenderResponse(
            success=True,
            image_url=f"/api/image/{request.run_id}/{output_filename}",
            message="Image rendered successfully"
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Render failed: {str(e)}")


@app.get("/api/image/{run_id}/{filename}")
async def get_image(run_id: str, filename: str):
    """Serve images from pipeline runs."""
    # Sanitize filename to prevent path traversal
    filename = Path(filename).name
    
    # Check in run directory
    image_path = PIPELINE_OUTPUTS / run_id / filename
    
    # Check in layers subdirectory
    if not image_path.exists():
        image_path = PIPELINE_OUTPUTS / run_id / "layers" / filename
    
    if not image_path.exists():
        raise HTTPException(status_code=404, detail=f"Image not found: {filename}")
    
    return FileResponse(
        image_path,
        media_type="image/png",
        headers={"Cache-Control": "max-age=3600"}
    )


# ============================================================================
# Run Server
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    # Run without reload to avoid module path issues
    uvicorn.run(app, host="0.0.0.0", port=8000)
