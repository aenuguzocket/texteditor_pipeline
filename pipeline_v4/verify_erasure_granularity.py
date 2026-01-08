
import cv2
import numpy as np
import json
from pathlib import Path

def check_granularity(run_id):
    base_dir = Path("pipeline_outputs") / run_id
    report_path = base_dir / "pipeline_report.json"
    
    with open(report_path) as f:
        report = json.load(f)
        
    orig_w = report["original_size"]["width"]
    orig_h = report["original_size"]["height"]
    
    # Load Cleaned Layer 1
    l1_path = base_dir / "layers" / "1_layer_1_cleaned.png"
    if not l1_path.exists():
        print("Layer 1 cleaned not found")
        return
        
    img = cv2.imread(str(l1_path), cv2.IMREAD_UNCHANGED)
    alpha = img[:, :, 3]
    h, w = alpha.shape
    
    sx = w / orig_w
    sy = h / orig_h
    
    print(f"Checking Run: {run_id}")
    print(f"Layer Size: {w}x{h} (Scale: {sx:.3f}, {sy:.3f})")
    
    regions = report["text_detection"]["regions"]
    
    print(f"\n{'Role':<15} | {'Text':<20} | {'Fill Ratio':<10} | {'Status'}")
    print("-" * 60)
    
    for r in regions:
        role = r.get("gemini_analysis", {}).get("role", "body")
        text = r.get("gemini_analysis", {}).get("text", "")[:20]
        
        if role in ["product_text", "logo"]: continue
        
        bbox = r["bbox"]
        bx = int(bbox["x"] * sx)
        by = int(bbox["y"] * sy)
        bw = int(bbox["width"] * sx)
        bh = int(bbox["height"] * sy)
        
        # Crop alpha
        # Note: In V4.1 we pad by 10px. 
        # But let's check the strict bbox area. 
        # If it's fully erased, alpha mean will be 0. 
        # Wait, erased pixels have alpha=0. Original have alpha=255.
        # Fill Ratio = (Count of Alpha=0 inside Raw Alpha>0 area) / Total Area?
        # Actually simplest: 
        # Count pixels with Alpha=0 inside the bbox.
        # This assumes the original layer HAD content there.
        # Since we don't have original layer easily here, let's assume content was mostly opaque.
        
        crop_a = alpha[by:by+bh, bx:bx+bw]
        if crop_a.size == 0: continue
        
        total_pixels = crop_a.size
        erased_pixels = np.sum(crop_a == 0)
        
        ratio = erased_pixels / total_pixels
        
        status = "BLOCKY" if ratio > 0.8 else "GRANULAR" if ratio > 0.1 else "MISSED"
        
        print(f"{role:<15} | {text:<20} | {ratio:.2f}       | {status}")

if __name__ == "__main__":
    # Check the V4.2 run
    check_granularity("run_1767700621_layered")
