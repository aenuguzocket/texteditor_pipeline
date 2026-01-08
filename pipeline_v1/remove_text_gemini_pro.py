"""
Advanced Text Removal with Exclusion Handling
==============================================
Inpaints text based on a semantic mask, with explicit instructions 
to PRESERVE specific regions like logs, UI, and product text.

This script expects:
- The original image
- A "Refined Mask" (text_mask.png) where:
    - WHITE = Text to remove (Headings, Body, etc.)
    - BLACK = Areas to preserve (Logos, Product Text, UI)

It uses a prompt that explicitly tells Gemini to attend to the mask 
and ignore unmasked text.
"""

import os
import argparse
import json
from pathlib import Path
import cv2
import numpy as np
from google import genai
from google.genai import types
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

MODEL_NAME = "gemini-3-pro-image-preview"  # Using preview model for 2 input images
API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=API_KEY)

# --------------------------------------------------
# ENHANCED PROMPT
# --------------------------------------------------

PROMPT = """
You are performing strict, pixel-level image inpainting.

You are given:
1) An original image
2) A binary mask image

MASK RULE (ABSOLUTE, NON-NEGOTIABLE):
- WHITE pixels represent areas that MUST be removed completely
- BLACK pixels represent areas that MUST NOT be altered in any way

You must treat the mask as a hard pixel constraint, not a suggestion.

TASK:
- Remove ALL visual text content inside WHITE areas
- Fill WHITE areas using surrounding background so that no trace remains
- Do NOT modify any pixel outside WHITE areas

CRITICAL:
- Do not use semantic judgment
- Do not decide importance


OUTPUT:
Return ONLY the final edited image.
No explanations.

"""

def remove_text_pro(pipeline_output_dir: str, output_name: str = "inpainted.png"):
    """
    Remove text using Gemini with strict mask adherence.
    """
    pipeline_dir = Path(pipeline_output_dir)
    json_path = pipeline_dir / "final_result_pro.json"
    mask_path = pipeline_dir / "text_mask.png"
    
    if not json_path.exists():
        print(f"Error: {json_path} not found")
        return
        
    with open(json_path, "r") as f:
        data = json.load(f)
        
    original_image_path = data["image"]
    
    if not Path(original_image_path).exists():
        print(f"Error: Original image not found at {original_image_path}")
        return
        
    if not mask_path.exists():
        print(f"Error: Mask not found at {mask_path}")
        return
        
    print(f"Original: {original_image_path}")
    print(f"Refined Mask: {mask_path}")
    
    # Load images
    image = Image.open(original_image_path).convert("RGBA")
    
    # Load mask and ensure it's properly formatted
    # We load it as grayscale for processing if needed, but pass as Image to Gemini
    mask_val = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
    
    # Optional: Verify mask content
    white_pixels = np.sum(mask_val > 127)
    total_pixels = mask_val.size
    coverage = white_pixels / total_pixels
    print(f"Mask Coverage: {coverage*100:.2f}% of image will be removed")
    
    mask_pil = Image.fromarray(mask_val)
    
    print(f"\nCalling {MODEL_NAME}...")
    
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[
                PROMPT,
                image,
                mask_pil # Correctly passing mask as second image
            ],
            config=types.GenerateContentConfig(
                temperature=0,
                response_modalities=["image"]
            )
        )
        
        # Save result
        result_image = None
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                import base64
                from io import BytesIO
                image_data = part.inline_data.data
                result_image = Image.open(BytesIO(image_data))
                break
            elif hasattr(part, 'image'):
                result_image = part.image
                break
                
        if result_image:
            output_path = pipeline_dir / output_name
            result_image.save(output_path)
            print(f"\n✅ Inpainting complete: {output_path}")
            return str(output_path)
        else:
            print("Error: No image returned.")
            return None
            
    except Exception as e:
        print(f"Error during inpainting: {e}")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inpaint text with exclusion handling")
    parser.add_argument(
        "pipeline_dir",
        nargs="?",
        default="pipeline_outputs/run_1766739537_pro",
        help="Path to pipeline output directory"
    )
    
    args = parser.parse_args()
    remove_text_pro(args.pipeline_dir)
