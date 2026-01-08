import json
import os
import sys
from PIL import Image, ImageDraw, ImageFont

# Add current dir to path to find the sibling script if running from here
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from google_fonts_runtime_loader import get_font_path

OUTPUT_IMAGE = "rendered_final_padadjust9.png"


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def apply_text_case(text, case):
    if case == "uppercase":
        return text.upper()
    if case == "lowercase":
        return text.lower()
    if case == "titlecase":
        return text.title()
    return text


def render_from_json(json_path):
    if not os.path.exists(json_path):
        print(f"Error: JSON file not found: {json_path}")
        return

    with open(json_path, "r") as f:
        data = json.load(f)

    # Determine image path:
    # Priority order:
    # 1. inpainted.png (from remove_text_gemini.py)
    # 2. Gemini_Generated_Image*.png
    # 3. Any other local PNG (not crop)
    # 4. Fallback to original image in JSON
    
    json_dir = os.path.dirname(os.path.abspath(json_path))
    local_images = [
        f for f in os.listdir(json_dir) 
        if f.lower().endswith(".png") and "crop" not in f.lower() and "mask" not in f.lower() and os.path.isfile(os.path.join(json_dir, f))
    ]
    
    # Priority 1: inpainted.png (from remove_text_gemini.py)
    inpainted = [f for f in local_images if f == "inpainted.png"]
    
    # Priority 2: Gemini_Generated_Image
    gemini_generated = [f for f in local_images if "Gemini_Generated_Image" in f]
    
    if inpainted:
        img_path = os.path.join(json_dir, inpainted[0])
        print(f"Using inpainted background: {img_path}")
    elif gemini_generated:
        img_path = os.path.join(json_dir, gemini_generated[0])
        print(f"Using Gemini generated background: {img_path}")
    elif local_images:
        img_path = os.path.join(json_dir, local_images[0])
        print(f"Using found local image: {img_path}")
    else:
        img_path = data["image"]
        print(f"Using JSON-referenced image: {img_path}")

    if not os.path.exists(img_path):
        print(f"Error: Image path {img_path} not found.")
        return
        
    try:
        img = Image.open(img_path).convert("RGBA")
    except Exception as e:
        print(f"Error opening image {img_path}: {e}")
        return

    # Calculate scaling factors if image dimensions don't match JSON dimensions
    json_width = data["dimensions"]["width"]
    json_height = data["dimensions"]["height"]
    img_width, img_height = img.size
    
    scale_x = img_width / json_width
    scale_y = img_height / json_height
    
    if scale_x != 1.0 or scale_y != 1.0:
        print(f"Dimension mismatch detected. JSON: {json_width}x{json_height}, Image: {img_width}x{img_height}")
        print(f"Applying scale factors: x={scale_x:.2f}, y={scale_y:.2f}")

    draw = ImageDraw.Draw(img)

    for region in data["regions"]:
        bbox = region["bbox"]
        tc = region["text_content"]
        
        # Skip if no text content (e.g. font norm failed or no text)
        if not tc or "text" not in tc:
            continue

        # Use text exactly as stored in JSON (Gemini already extracted it correctly)
        text = tc["text"]
        color = hex_to_rgb(tc.get("color", "#000000"))

        # Resolve font path first
        try:
            font_path = get_font_path(
                tc["normalized_font"],
                tc["normalized_weight"]
            )
        except Exception as e:
            print(f"Font loading failed for {tc['normalized_font']}: {e}. Skipping.")
            continue

        # Scale the bbox dimensions
        scaled_bbox_height = bbox["height"] * scale_y
        scaled_bbox_width = bbox["width"] * scale_x

        # CRAFT padding logic (from text_detector_craft.py):
        # pad_y = h * padding_percentage (added to BOTH top and bottom)
        # So: bbox_height = original_text_height + 2 * (original_text_height * padding_percentage)
        #     bbox_height = original_text_height * (1 + 2 * padding_percentage)
        #     original_text_height = bbox_height / (1 + 2 * padding_percentage)
        
        CRAFT_PADDING_PERCENTAGE = 0.09  # From CraftTextDetector default
        padding_factor = 1 + (2.5 * CRAFT_PADDING_PERCENTAGE)  # 1.07
        
        # Calculate original text height by removing padding
        original_text_height = scaled_bbox_height / padding_factor
        target_height = original_text_height
        # Initial guess: font size = target height
        font_size = int(target_height)
        
        font = ImageFont.truetype(font_path, font_size)
        
        # Iterative refinement to match target height
        for _ in range(3):
            try:
                left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
                text_h = bottom - top
            except:
                text_w, text_h = draw.textsize(text, font=font)

            if text_h == 0: break
            
            # scaling factor
            font_scale = target_height / text_h
            font_size = int(font_size * font_scale)
            font = ImageFont.truetype(font_path, font_size)

        # Final measurement
        try:
            left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
            text_w = right - left
            text_h = bottom - top
            y_offset = top
        except:
             text_w, text_h = draw.textsize(text, font=font)
             y_offset = 0

        # LEFT-ALIGN text at the TOP-LEFT of the bounding box
        # Use polygon data if available for more precise positioning, else use bbox
        if "polygon" in region and len(region["polygon"]) >= 1:
            # Polygon gives us the actual corners of the detected text
            # polygon[0] is top-left corner [x, y]
            x = region["polygon"][0][0] * scale_x
            y = region["polygon"][0][1] * scale_y
        else:
            # Fallback to bbox top-left
            x = bbox["x"] * scale_x
            y = bbox["y"] * scale_y
        
        # Adjust y for font rendering offset (textbbox 'top' value)
        y = y - y_offset

        draw.text((x, y), text, fill=color, font=font)

    output_path = os.path.join(json_dir, OUTPUT_IMAGE)
    img.save(output_path)
    print(f"✅ Rendered image saved as {output_path}")


if __name__ == "__main__":
    # Expects validation json path as argument or defaults
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("json_path", nargs="?", default="pipeline_outputs/run_1766739537_pro/final_result_editable.json", help="Path to final_result.json (use final_result_editable.json after filtering)")
    args = parser.parse_args()
    
    render_from_json(args.json_path)
