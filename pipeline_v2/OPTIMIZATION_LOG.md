# Optimization & Refactoring Log

This document tracks identified optimization opportunities and code improvements for the Product Pipeline V2.

## Text Detector (CRAFT) - `text_detector_craft.py`

### 1. Optimize Base64 Conversion
**Location:** `_image_to_base64` method (Line 169)
**Priority:** Low (Performance optimization)
**Description:** 
Currently, the code converts a NumPy array (OpenCV image) to a PIL Image solely to save it to a buffer for Base64 encoding. This conversion is unnecessary overhead. We can use `cv2.imencode` directly.

**Suggested Implementation:**
```python
def _image_to_base64(self, image: np.ndarray, format: str = "PNG") -> str:
    """
    Convert numpy image to base64 data URI using OpenCV directly for better performance.
    """
    # OpenCV uses .ext for format, e.g., '.png'
    ext = '.' + format.lower()
    
    # cv2.imencode returns (success, encoded_image)
    success, buffer = cv2.imencode(ext, image)
    
    if not success:
        raise ValueError(f"Failed to encode image to {format}")
    
    # Encode directly from the buffer
    img_base64 = base64.b64encode(buffer).decode('utf-8')
    
    return f"data:image/{format.lower()};base64,{img_base64}"
```


