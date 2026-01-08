import cv2
import numpy as np
from collections import Counter

# --------------------------------------------------
# COLOR DETECTION FROM TEXT CROPS
# --------------------------------------------------

def extract_dominant_text_color(image_path: str) -> str:
    """
    Extract the dominant color from a text crop image.
    
    Assumes the text is darker than the background.
    Returns the color as a hex string (e.g., "#FF5733").
    """
    # Read image
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")
    
    # Convert BGR to RGB for consistent color space
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Convert to HSV to better isolate darker pixels (text)
    img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Threshold to find dark pixels (low V in HSV = darker regions)
    # Assuming text is darker than background
    _, mask = cv2.threshold(img_hsv[:, :, 2], 200, 255, cv2.THRESH_BINARY_INV)
    
    # Apply morphological operations to clean up noise
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
    
    # Get pixels where mask is white (text regions)
    text_pixels = img_rgb[mask == 255]
    
    if len(text_pixels) == 0:
        # Fallback: use all pixels if mask is empty
        text_pixels = img_rgb.reshape(-1, 3)
    
    # Find the most common color in the text region
    # Quantize colors to reduce noise
    text_pixels_quantized = (text_pixels // 10) * 10  # Group similar colors
    
    # Flatten and count
    pixels_tuple = [tuple(p) for p in text_pixels_quantized]
    color_counts = Counter(pixels_tuple)
    
    # Get the most common color
    dominant_color_rgb = color_counts.most_common(1)[0][0]
    
    # Convert to hex
    hex_color = "#{:02X}{:02X}{:02X}".format(
        int(dominant_color_rgb[0]),
        int(dominant_color_rgb[1]),
        int(dominant_color_rgb[2])
    )
    
    return hex_color


def validate_color_against_model(image_path: str, model_color: str) -> dict:
    """
    Compare the detected color with the model's predicted color.
    
    Args:
        image_path: Path to the text crop image
        model_color: The hex color from Gemini model (e.g., "#FF5733")
    
    Returns:
        Dictionary with detected color and match confidence
    """
    detected_color = extract_dominant_text_color(image_path)
    
    # Simple comparison: exact match or close match
    is_exact_match = detected_color.upper() == model_color.upper()
    
    # Calculate rough similarity (R, G, B distance)
    if len(detected_color) == 7 and len(model_color) == 7:
        det_r, det_g, det_b = int(detected_color[1:3], 16), int(detected_color[3:5], 16), int(detected_color[5:7], 16)
        mod_r, mod_g, mod_b = int(model_color[1:3], 16), int(model_color[3:5], 16), int(model_color[5:7], 16)
        
        distance = ((det_r - mod_r)**2 + (det_g - mod_g)**2 + (det_b - mod_b)**2) ** 0.5
        similarity = max(0, 100 - (distance / 4.41))  # Max distance is ~441, so normalize
    else:
        similarity = 0 if not is_exact_match else 100
    
    return {
        "detected_color": detected_color,
        "model_color": model_color,
        "exact_match": is_exact_match,
        "similarity_percent": round(similarity, 1)
    }


if __name__ == "__main__":
    # Example usage
    test_crop = "outputs_all_line/run_1/1ce357b5-2293-4b66-8ea5-caed661ba3d6/crops/0.png"
    
    try:
        color = extract_dominant_text_color(test_crop)
        print(f"Detected text color: {color}")
    except Exception as e:
        print(f"Error: {e}")
