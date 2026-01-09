"""
Streamlit Demo for Pipeline V4
================================
A web interface for the image text removal and editing pipeline.

Pipeline Stages:
1. CRAFT Text Detection + Gemini Analysis + Qwen Layering + Layer Cleaning
2. Background Box Detection (CTA extraction)
3. Text Rendering (Final composition)
"""

import os
import sys
import time
import json
import tempfile
from pathlib import Path
from io import BytesIO
import streamlit as st
from PIL import Image
import numpy as np

# Add pipeline_v4 to path
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))
sys.path.append(str(current_dir / "pipeline_v4"))
sys.path.append(str(current_dir / "pipeline_v4" / "rendering"))

# Import pipeline modules
try:
    from pipeline_v4.run_pipeline_layered_v4 import run_pipeline_layered
    from pipeline_v4.run_pipeline_box_detection_v4 import run_box_detection_pipeline
    from pipeline_v4.run_pipeline_text_rendering_v4 import (
        composite_layers,
        draw_background_boxes,
        render_text_layer
    )
except ImportError as e:
    st.error(f"Failed to import pipeline modules: {e}")
    st.stop()

# Page config
st.set_page_config(
    page_title="Image Text Removal Pipeline",
    page_icon="🎨",
    layout="wide"
)

# Initialize session state
if 'pipeline_run_dir' not in st.session_state:
    st.session_state.pipeline_run_dir = None
if 'pipeline_complete' not in st.session_state:
    st.session_state.pipeline_complete = False
if 'uploaded_image' not in st.session_state:
    st.session_state.uploaded_image = None

def save_uploaded_file(uploaded_file):
    """Save uploaded file to temporary location"""
    temp_dir = Path(tempfile.gettempdir()) / "pipeline_uploads"
    temp_dir.mkdir(exist_ok=True)
    
    file_path = temp_dir / uploaded_file.name
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return str(file_path)

def run_full_pipeline(image_path: str, progress_container):
    """
    Run the complete pipeline V4:
    1. Layered pipeline (CRAFT + Gemini + Qwen + Cleaning)
    2. Box detection
    3. Text rendering
    """
    run_dir = None
    
    try:
        # Stage 1: Layered Pipeline
        progress_container.info("🔄 Stage 1: Text Detection & Layer Separation...")
        progress_bar = progress_container.progress(0.0)
        
        progress_bar.progress(0.1)
        run_dir = run_pipeline_layered(image_path, mock_layers_dir=None)
        progress_bar.progress(0.4)
        
        if not run_dir or not Path(run_dir).exists():
            raise Exception("Stage 1 failed: No output directory created")
        
        # Stage 2: Box Detection
        progress_container.info("🔄 Stage 2: Background Box Detection...")
        progress_bar.progress(0.5)
        
        run_box_detection_pipeline(run_dir)
        progress_bar.progress(0.7)
        
        # Stage 3: Text Rendering
        progress_container.info("🔄 Stage 3: Final Composition & Text Rendering...")
        progress_bar.progress(0.75)
        
        # Load report
        report_with_boxes = Path(run_dir) / "pipeline_report_with_boxes.json"
        report_orig = Path(run_dir) / "pipeline_report.json"
        report_file = report_with_boxes if report_with_boxes.exists() else report_orig
        
        if not report_file.exists():
            raise Exception("Pipeline report not found")
        
        with open(report_file, "r") as f:
            report = json.load(f)
        
        # Get original dimensions
        orig_w, orig_h = 1080, 1920  # Fallback
        if "original_size" in report:
            orig_w = report["original_size"]["width"]
            orig_h = report["original_size"]["height"]
        
        progress_bar.progress(0.8)
        
        # Composite layers
        final_img = composite_layers(run_dir, report)
        if final_img is None:
            raise Exception("Failed to composite layers")
        
        progress_bar.progress(0.85)
        
        # Draw background boxes
        final_img = draw_background_boxes(final_img, report, orig_w, orig_h, run_dir)
        
        progress_bar.progress(0.9)
        
        # Render text
        final_img = render_text_layer(final_img, report)
        
        # Save final image
        out_path = Path(run_dir) / "final_composed.png"
        final_img.save(out_path)
        
        progress_bar.progress(1.0)
        progress_container.success("✅ Pipeline completed successfully!")
        
        return run_dir, report
        
    except Exception as e:
        progress_container.error(f"❌ Pipeline failed: {str(e)}")
        import traceback
        st.error(f"Error details:\n```\n{traceback.format_exc()}\n```")
        return None, None

# Main UI
st.title("🎨 Image Text Removal & Editing Pipeline")
st.markdown("Upload an image to remove text and extract editable layers (like Canva/Adobe)")

# Sidebar for settings
with st.sidebar:
    st.header("⚙️ Settings")
    st.info("Upload an image to start processing")
    
    # Environment check
    st.subheader("Environment Check")
    
    # Check both env vars and Streamlit secrets
    def check_env_var(key):
        value = os.getenv(key)
        if not value:
            try:
                if hasattr(st, 'secrets') and key in st.secrets:
                    value = st.secrets[key]
            except:
                pass
        return value
    
    env_vars = {
        "FAL_KEY": check_env_var("FAL_KEY"),
        "GEMINI_API_KEY": check_env_var("GEMINI_API_KEY") or check_env_var("GOOGLE_API_KEY"),
        "GOOGLE_FONTS_API_KEY": check_env_var("GOOGLE_FONTS_API_KEY")
    }
    
    for key, value in env_vars.items():
        if value:
            st.success(f"✅ {key} set")
        else:
            st.warning(f"⚠️ {key} not set")

# Main content area
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📤 Upload Image")
    uploaded_file = st.file_uploader(
        "Choose an image file",
        type=['png', 'jpg', 'jpeg'],
        help="Upload an image with text to process"
    )
    
    if uploaded_file is not None:
        # Display uploaded image
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image", use_container_width=True)
        
        # Save to temp location
        if st.button("🚀 Run Pipeline", type="primary", use_container_width=True):
            with st.spinner("Saving uploaded image..."):
                image_path = save_uploaded_file(uploaded_file)
            
            # Create progress container
            progress_container = st.container()
            
            # Run pipeline
            run_dir, report = run_full_pipeline(image_path, progress_container)
            
            if run_dir:
                st.session_state.pipeline_run_dir = run_dir
                st.session_state.pipeline_complete = True
                st.rerun()

with col2:
    st.subheader("📊 Results")
    
    if st.session_state.pipeline_complete and st.session_state.pipeline_run_dir:
        run_dir = Path(st.session_state.pipeline_run_dir)
        
        # Display final image
        final_path = run_dir / "final_composed.png"
        if final_path.exists():
            final_img = Image.open(final_path)
            st.image(final_img, caption="Final Composed Image", use_container_width=True)
            
            # Download button
            with open(final_path, "rb") as f:
                st.download_button(
                    label="📥 Download Final Image",
                    data=f.read(),
                    file_name="final_composed.png",
                    mime="image/png",
                    use_container_width=True
                )
            
            # Link to editor
            st.markdown("---")
            st.info("💡 Want to edit text, move elements, or change fonts?")
            st.write("**To edit your image:**")
            st.write("1. Note the pipeline run directory above")
            st.write("2. Run: `streamlit run streamlit_editor.py`")
            st.write("3. Load the pipeline run in the editor")
            st.code(f"Pipeline Run: {run_dir.name}", language="text")
        
        # Show pipeline report summary
        report_path = run_dir / "pipeline_report_with_boxes.json"
        if not report_path.exists():
            report_path = run_dir / "pipeline_report.json"
        
        if report_path.exists():
            with open(report_path, "r") as f:
                report = json.load(f)
            
            st.subheader("📈 Pipeline Summary")
            
            # Text regions summary
            regions = report.get("text_detection", {}).get("regions", [])
            st.metric("Text Regions Detected", len(regions))
            
            # Role breakdown
            role_counts = {}
            for region in regions:
                gemini = region.get("gemini_analysis", {})
                role = gemini.get("role", "unknown")
                role_counts[role] = role_counts.get(role, 0) + 1
            
            if role_counts:
                st.write("**Text Roles:**")
                for role, count in sorted(role_counts.items()):
                    st.write(f"- {role}: {count}")
            
            # Box detection summary
            box_info = report.get("box_detection", {})
            if box_info:
                st.metric("Background Boxes Found", box_info.get("total_boxes_found", 0))
                st.metric("Regions with Boxes", box_info.get("regions_with_boxes", 0))
            
            # Layers summary
            layer_info = report.get("layer_cleaning", {}).get("layers_processed", [])
            st.metric("Layers Processed", len(layer_info))
            
            # Show layers
            layers_dir = run_dir / "layers"
            if layers_dir.exists():
                with st.expander("🔍 View Individual Layers"):
                    layer_files = sorted(layers_dir.glob("*_cleaned.png"))
                    for layer_file in layer_files:
                        layer_img = Image.open(layer_file)
                        st.image(layer_img, caption=layer_file.name, use_container_width=True)
            
            # Show extracted boxes
            extracted_dir = layers_dir / "extracted_boxes"
            if extracted_dir.exists():
                box_files = list(extracted_dir.glob("*.png"))
                if box_files:
                    with st.expander("📦 View Extracted Background Boxes"):
                        for box_file in sorted(box_files):
                            box_img = Image.open(box_file)
                            st.image(box_img, caption=box_file.name, use_container_width=True)
        
        # Reset button
        if st.button("🔄 Process New Image", use_container_width=True):
            st.session_state.pipeline_run_dir = None
            st.session_state.pipeline_complete = False
            st.session_state.uploaded_image = None
            st.rerun()
    
    else:
        st.info("👆 Upload an image and run the pipeline to see results here")

# Footer
st.markdown("---")
st.caption("Pipeline V4: CRAFT Text Detection → Gemini Analysis → Qwen Layering → Box Detection → Text Rendering")

