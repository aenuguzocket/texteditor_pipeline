import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image
from pathlib import Path
import json
import backend_p as backend # V4.17: Use backend_p for updated render_with_pipeline

def main():
    st.set_page_config(layout="wide", page_title="Pipeline Interaction Test")
    
    # --- PIPELINE IMPORTS ---
    import sys
    import os
    # Add root to path to find pipeline_v4
    root_dir = Path(__file__).parent.parent
    if str(root_dir) not in sys.path:
        sys.path.append(str(root_dir))
        
    try:
        from pipeline_v4.run_pipeline_layered_v4 import run_pipeline_layered
        from pipeline_v4.run_pipeline_box_detection_v4 import run_box_detection_pipeline
    except ImportError as e:
        st.error(f"Pipeline Import Error: {e}")
        return

    st.sidebar.title("Pipeline Interaction Lab 🧪")
    
    # 0. NEW IMAGE UPLOAD
    uploaded_file = st.sidebar.file_uploader("Upload New Image", type=["png", "jpg", "jpeg"])
    if uploaded_file:
        # Check if already processed to avoid re-running on every interactions
        # We use a simple hash or name check
        if st.sidebar.button("🚀 Run Pipeline on Upload"):
            with st.spinner("Saving image..."):
                # Save to temp
                uploads_dir = root_dir / "image" / "uploads"
                uploads_dir.mkdir(parents=True, exist_ok=True)
                file_path = uploads_dir / uploaded_file.name
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                    
            status_container = st.empty()
            
            try:
                # 1. Layering
                status_container.info("⏳ Running Layered Pipeline (CRAFT + Gemini + Qwen)... this takes ~30s")
                run_dir = run_pipeline_layered(str(file_path))
                
                # 2. Box Detection
                status_container.info("📦 Detecting Background Boxes...")
                run_box_detection_pipeline(run_dir)
                
                # 3. Complete
                status_container.success("✅ Pipeline Complete!")
                import time
                time.sleep(1)
                status_container.empty()
                
                # 4. Auto-Select
                run_id = Path(run_dir).name.split("_")[1] # run_123_layered -> 123
                # We need to refresh the list, backend.list_pipeline_runs() is called below
                # Force reload by rerun
                # st.session_state.current_run_id = f"run_{run_id}_layered" # REMOVED: Proactive set causes skip of reset logic
                # Actually main() re-reads runs. We just need to ensure selectbox defaults to new one.
                # Store preference in session state
                st.session_state.auto_select_run = f"run_{run_id}_layered"
                st.rerun()
                
            except Exception as e:
                st.error(f"Pipeline Failed: {e}")
                import traceback
                st.code(traceback.format_exc())

    st.sidebar.markdown("---")
    
    # 1. Select Run
    runs = backend.list_pipeline_runs()
    if not runs:
        st.error("No pipeline runs found in `pipeline_outputs/`.")
        return
        
    run_options = {r["id"]: r for r in runs}
    
    # Auto-select logic
    default_idx = 0
    if "auto_select_run" in st.session_state and st.session_state.auto_select_run in run_options:
        keys = list(run_options.keys())
        default_idx = keys.index(st.session_state.auto_select_run)
        
    selected_run_id = st.sidebar.selectbox("Select Pipeline Run", list(run_options.keys()), index=default_idx)
    
    run_details = run_options[selected_run_id]
    st.sidebar.info(f"Path: {run_details['path']}")
    
    # 2. Load Data
    data = backend.load_run_data(selected_run_id)
    if not data or "error" in data:
        st.error(f"Failed to load run data: {data.get('error')}")
        return
        
    # Inject Fonts for Canvas (V4.18: WebFontLoader for proper Fabric.js rendering)
    if "fonts" in data and data["fonts"]:
        font_families = data["fonts"]
        
        # Create WebFontLoader script that loads fonts BEFORE page renders
        # This uses a blocking approach with CSS Font Loading API
        font_css_links = ""
        for f in font_families:
            safe_f = f.replace(" ", "+")
            font_css_links += f'<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family={safe_f}:wght@100;200;300;400;500;600;700;800;900&display=swap" rel="stylesheet">'
        
        st.markdown(font_css_links, unsafe_allow_html=True)
        
        # Debug: Show which fonts are being loaded
        st.caption(f"📝 Canvas Fonts: {', '.join(font_families)}")
        
    report = data["report"]
    bg_image = data["background_image"]
    
    # 3. Canvas Config
    # Sidebar width override
    # 3. Canvas Config
    st.sidebar.markdown("---")
    
    # Split controls: Image Scale vs Canvas Size
    col_s1, col_s2 = st.sidebar.columns(2)
    with col_s1:
        img_display_width = st.number_input("Image Width", 300, 1200, 480, step=20)
    with col_s2:
        canvas_width = st.number_input("Canvas Width", 500, 2500, 1400, step=50) # Large default
    
    # Calculate scale based on ORIGINAL image dimensions vs Target Display Width
    orig_w = data.get("original_size", {}).get("width", 1080)
    orig_h = data.get("original_size", {}).get("height", 1920)
    
    # Aspect Ratio
    aspect_ratio = orig_h / orig_w
    
    # Image Display Dimensions
    img_display_height = int(img_display_width * aspect_ratio)
    
    # Canvas Dimensions (Workspace)
    canvas_height = st.sidebar.number_input("Canvas Height", 500, 2500, 1000, step=50)
    
    scale_x = img_display_width / orig_w
    scale_y = img_display_height / orig_h
    
    st.sidebar.markdown(f"**Original**: {orig_w}x{orig_h}")
    st.sidebar.markdown(f"**Display**: {img_display_width}x{img_display_height}")
    st.sidebar.markdown(f"**Scale**: {scale_x:.4f}")

    # --- HELPERS ---
    import base64
    from io import BytesIO
    from PIL import ImageFont, ImageDraw
    import time # Imported for sleep above

    def image_to_base64(img):
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()

    # Use a default font path that exists on Windows
    FONT_PATH = "arial.ttf" 

    def calculate_font_size(text, box_h, box_w):
        low, high = 1, 500
        best = 10 # Default minimum
        target_h = box_h * 0.90 
        target_w = box_w * 0.98 # Enforce width limit

        try:
             ImageFont.truetype(FONT_PATH, 10)
        except:
             return int(box_h * 0.5)

        while low <= high:
            mid = (low + high) // 2
            try:
                font = ImageFont.truetype(FONT_PATH, mid)
                left, top, right, bottom = font.getbbox(text)
                h = bottom - top
                w = right - left
                
                # Check BOTH dimensions
                if h <= target_h and w <= target_w:
                    best = mid
                    low = mid + 1
                else:
                    high = mid - 1
            except:
                break
        return best

    # --- PREPARE BACKGROUND OBJECT ---
    # Resized BG for display (Needed for Base64 injection) relative to Image Display Size
    bg_display = bg_image.resize((img_display_width, img_display_height))
    
    buffered = BytesIO()
    bg_display.save(buffered, format="PNG")
    bg_b64 = base64.b64encode(buffered.getvalue()).decode()
    
    bg_object = {
        "type": "image",
        "version": "4.4.0",
        "originX": "left",
        "originY": "top",
        "left": 0,
        "top": 0,
        "width": img_display_width,
        "height": img_display_height,
        "fill": "rgb(0,0,0)",
        "stroke": None,
        "strokeWidth": 0,
        "strokeDashArray": None,
        "strokeLineCap": "butt",
        "strokeDashOffset": 0,
        "strokeLineJoin": "miter",
        "strokeMiterLimit": 4,
        "scaleX": 1,
        "scaleY": 1,
        "angle": 0,
        "flipX": False,
        "flipY": False,
        "opacity": 1,
        "shadow": None,
        "visible": True,
        "clipTo": None,
        "backgroundColor": "",
        "fillRule": "nonzero",
        "paintFirst": "fill",
        "globalCompositeOperation": "source-over",
        "transformMatrix": None,
        "skewX": 0,
        "skewY": 0,
        "src": f"data:image/png;base64,{bg_b64}",
        "crossOrigin": None,
        "selectable": False, # Lock background
        "evented": False     # Ignore clicks
    }

    # ... (After Sidebar Config) ...
    
    # State Management for Re-renders
    if "canvas_version" not in st.session_state:
        st.session_state.canvas_version = 0
    
    # --- PREPARE BASE OBJECTS (From Report) ---
    base_objects = []
    
    # 1. Background
    bg_object["u_id"] = "background"
    base_objects.append(bg_object)
    
    text_regions = report.get("text_detection", {}).get("regions", [])
    
    # 2. Extracted Boxes
    for i, region in enumerate(text_regions):
        rid = region.get("id", i)
        bg_box = region.get("background_box", {})
        
        # ... [Existing Box Logic] ...
        if bg_box.get("detected"):
            bbox = bg_box["bbox"]
            # ... (Box Path Resolution) ...
            extracted_path = bg_box.get("extracted_image")
            
            final_obj = None
            if extracted_path:
                full_path = Path(data["run_dir"]) / extracted_path
                if full_path.exists():
                    # ... (Load Image) ...
                    box_img = Image.open(full_path).convert("RGBA")
                    box_b64 = image_to_base64(box_img)
                    
                    if "layer_bbox" in bg_box:
                        lb = bg_box["layer_bbox"]
                        bg_w, bg_h = bg_image.size
                        sx_layer = img_display_width / bg_w
                        sy_layer = img_display_height / bg_h
                        f_l, f_t = lb["x"]*sx_layer, lb["y"]*sy_layer
                        f_w, f_h = lb["width"]*sx_layer, lb["height"]*sy_layer
                    else:
                        f_l, f_t = bbox["x"]*scale_x, bbox["y"]*scale_y
                        f_w, f_h = bbox["width"]*scale_x, bbox["height"]*scale_y

                    final_obj = {
                        "type": "image",
                        "version": "4.4.0",
                        "originX": "left", "originY": "top",
                        "left": f_l, "top": f_t, "width": f_w, "height": f_h,
                        "src": f"data:image/png;base64,{box_b64}",
                        "scaleX": 1, "scaleY": 1,
                        "opacity": 1, "selectable": True 
                    }
            
            if not final_obj:
                # Fallback Rect
                color = bg_box.get("color", "#000000")
                final_obj = {
                    "type": "rect",
                    "left": bbox["x"]*scale_x, "top": bbox["y"]*scale_y,
                    "width": bbox["width"]*scale_x, "height": bbox["height"]*scale_y,
                    "fill": color
                }
            
            final_obj["u_id"] = f"box_{rid}"
            base_objects.append(final_obj)

    # 3. Text Objects & Editor Form
    text_updates = {}
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("")
    with st.sidebar.form("text_editor_form"):
        for i, region in enumerate(text_regions):
            gemini = region.get("gemini_analysis", {})
            role = gemini.get("role", "body")
            # V4.17 FIX: Match CLI filter - only render these roles
            if role not in ["heading", "subheading", "body", "cta", "usp"]:
                continue
                
            rid = region.get("id", i)
            orig_text = gemini.get("text", "")
            
            # Text Input
            new_text = st.text_area(f"Text {rid} ({role})", value=orig_text, height=70)
            text_updates[f"text_{rid}"] = new_text
            
            # Base Object Creation
            bbox = region["bbox"]
            color = gemini.get("text_color", "#000000")
            canvas_box_h = bbox["height"] * scale_y
            canvas_box_w = bbox["width"] * scale_x
            font_size = calculate_font_size(orig_text, canvas_box_h, canvas_box_w)
            
            # Get font info from Gemini for Canvas rendering
            canvas_font = gemini.get("primary_font", "sans-serif")
            font_weight = gemini.get("font_weight", 400)
            
            # DEBUG: Print font info
            print(f"[Canvas Debug] Region {rid}: font='{canvas_font}', weight={font_weight}")
            
            base_objects.append({
                "type": "textbox",
                "u_id": f"text_{rid}", # Unique ID for matching
                "text": orig_text, # Initial text
                "left": bbox["x"] * scale_x,
                "top": bbox["y"] * scale_y,
                "width": bbox["width"] * scale_x,
                "fontSize": font_size,
                "fontFamily": canvas_font,  # V4.17: Use actual font from Gemini
                "fontWeight": font_weight,   # V4.17: Apply font weight
                "fill": color,
                "backgroundColor": "transparent"
            })
            
        update_clicked = st.form_submit_button("Update Text")

    # --- STATE MANAGEMENT ---
    
    # Check if run changed, reset state
    if "current_run_id" not in st.session_state or st.session_state.current_run_id != selected_run_id:
        st.session_state.current_run_id = selected_run_id
        st.session_state.canvas_version = 0
        st.session_state.active_objects = base_objects # Initialize with defaults
        st.session_state.last_canvas_state = None
    else:
        # V4.17 FIX: Always sync fontFamily/fontWeight from base_objects to active_objects
        # This fixes stale session state with wrong fonts
        base_font_map = {obj.get("u_id"): obj for obj in base_objects if obj.get("type") == "textbox"}
        for obj in st.session_state.active_objects:
            if obj.get("type") == "textbox" and obj.get("u_id") in base_font_map:
                base_obj = base_font_map[obj["u_id"]]
                obj["fontFamily"] = base_obj.get("fontFamily", "sans-serif")
                obj["fontWeight"] = base_obj.get("fontWeight", 400)
        
    # Manual Reset Button
    col_btn1, col_btn2 = st.sidebar.columns(2)
    with col_btn1:
        if st.button("Reset Layout"):
            st.session_state.active_objects = base_objects
            st.session_state.canvas_version += 1
            st.session_state.last_canvas_state = None
            st.success("Layout reset!")
            st.rerun()
    
    with col_btn2:
        # V4.18: Reload Fonts - Forces Canvas re-render AFTER fonts are loaded
        if st.button("🔄 Reload Fonts"):
            st.session_state.canvas_version += 1
            st.toast("Canvas re-rendered with loaded fonts!", icon="🔄")
            st.rerun()

    
    # ----------------------------------------------------
    # UPDATE BUTTON & ACTIONS
    # ----------------------------------------------------
    update_clicked = st.sidebar.button("Update & Re-render 🚀", type="primary", use_container_width=True)

    final_drawing_objects = st.session_state.active_objects
    
    # --- MERGE POSITIONS ON CLICK ---
    # Only run if we have a valid previous state
    if update_clicked and st.session_state.last_canvas_state is not None:
        current_objects = st.session_state.last_canvas_state["objects"]
        merged = []
        
        # Base schema is st.session_state.active_objects
        base_list = st.session_state.active_objects
        
        # Robust Merging: Match by u_id if possible
        # Map current objects by u_id
        curr_map = {o.get("u_id"): o for o in current_objects if o.get("u_id")}
        
        for base_obj in base_list:
            uid = base_obj.get("u_id")
            new_obj = base_obj.copy()
            
            if uid and uid in curr_map:
                 curr_obj = curr_map[uid]
                 # Copy Positions
                 preserved_props = ["left", "top", "width", "height", "scaleX", "scaleY", "angle"]
                 for p in preserved_props:
                     if p in curr_obj:
                         new_obj[p] = curr_obj[p]
            
            merged.append(new_obj)
            
        st.session_state.active_objects = merged
        st.session_state.canvas_version += 1
        st.success(f"Positions synced! (v{st.session_state.canvas_version})")

    # --- APPLY TEXT UPDATES (ALWAYS) ---
    updated_objects = []
    final_text_updates = {} # Store for backend
    for obj in st.session_state.active_objects:
        obj_copy = obj.copy()
        uid = obj_copy.get("u_id")
        
        if uid and uid in text_updates and obj_copy["type"] == "textbox":
             # Use text from Sidebar Input (Priority)
             obj_copy["text"] = text_updates[uid]
             
             # Store for Backend
             rid = uid.replace("text_", "")
             final_text_updates[rid] = text_updates[uid]
        
        updated_objects.append(obj_copy)
    
    final_drawing_objects = updated_objects
    
    # ----------------------------------------------------
    # PIPELINE PREVIEW & TRIGGER
    # ----------------------------------------------------
    st.markdown("### 🎨 Pipeline Preview")
    preview_placeholder = st.empty()
    
    # Determine Path
    run_dir = data.get("run_dir")
    run_dir_path = Path(run_dir) if run_dir else None
    
    final_path = run_dir_path / "final_composed.png" if run_dir_path else None
    
    # 1. TRIGGER RE-RENDER
    if update_clicked:
         with st.spinner("Running Backend Pipeline (Rendering)..."):
             # Calc BBox Updates
             bbox_updates = {}
             for obj in final_drawing_objects:
                 if obj["type"] == "textbox":
                     rid = obj["u_id"].replace("text_", "")
                     
                     # Canvas -> Original Conversion
                     s_x = scale_x
                     s_y = scale_y
                     
                     c_w = obj["width"] * obj.get("scaleX", 1)
                     c_h = obj.get("height", obj.get("fontSize", 20) * 1.5) * obj.get("scaleY", 1)
                     c_left = obj["left"]
                     c_top = obj["top"]
                     
                     bbox_updates[rid] = {
                         "x": int(c_left / s_x),
                         "y": int(c_top / s_y),
                         "width": int(c_w / s_x),
                         "height": int(c_h / s_y)
                     }
             
             # Call Backend
             new_img = backend.render_with_pipeline(str(run_dir), final_text_updates, bbox_updates)
             if new_img:
                 st.toast("Pipeline Render Complete!", icon="✅")
                 # Force reload image
                 preview_placeholder.image(new_img, caption="Updated Pipeline Output", use_container_width=True)
             else:
                 st.error("Pipeline failed to render.")
    
    # 2. DEFAULT VIEW
    elif final_path and final_path.exists():
         # timestamp to bust cache if just updated
         ts = int(time.time())
         preview_placeholder.image(str(final_path), caption="Current Pipeline Output", use_container_width=True)
    
    st.markdown("---")
    # Canvas follows below...

    
    col1, col2 = st.columns([5, 1])
    
    with col1:
        st.subheader("Interactive Editor")
        st.caption("ℹ️ Note: Canvas mimics the layout but fonts are browser-approximations. See 'Pipeline Preview' above for the pixel-perfect final result.")
        # Dynamic Key to force update when needed
        c_key = f"canvas_{selected_run_id}_v{st.session_state.canvas_version}"
        
        canvas_result = st_canvas(
            fill_color="rgba(255, 165, 0, 0.3)",
            stroke_width=2,
            stroke_color="#000000",
            background_color="#ffffff",
            update_streamlit=True,
            height=canvas_height,
            width=canvas_width,
            drawing_mode="transform",
            initial_drawing={"version": "4.4.0", "objects": final_drawing_objects},
            key=c_key,
        )
        
        # Save state for next run
        if canvas_result.json_data:
            st.session_state.last_canvas_state = canvas_result.json_data
            
    with col2:
        st.subheader("Data Inspector")
        if canvas_result.json_data:
            objects = canvas_result.json_data["objects"]
            # Filter out the background image from inspector
            editable_objects = [o for o in objects if o.get("type") != "image"]
            
            st.write(f"Active Objects: {len(editable_objects)}")
            # Show modified objects
            for i, obj in enumerate(editable_objects):
                st.caption(f"Object {i} ({obj['type']})")
                st.json({
                    "u_id": obj.get("u_id", "MISSING"),
                    "text": obj.get("text", "N/A"),
                    "left": int(obj["left"]),
                    "top": int(obj["top"]),
                    "width": int(obj["width"] * obj.get("scaleX", 1)),
                    "height": int(obj["height"] * obj.get("scaleY", 1)),
                    "fill": obj["fill"]
                })

if __name__ == "__main__":
    main()
