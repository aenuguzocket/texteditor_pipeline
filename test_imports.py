
import sys
import os
from pathlib import Path

# Setup path like text_detector_craft.py
CRAFT_DIR = Path("CRAFT-pytorch").absolute()
sys.path.insert(0, str(CRAFT_DIR))

try:
    import torch
    print(f"Torch version: {torch.__version__}")
    
    import craft
    print("CRAFT module imported successfully")
    
    from craft_utils import getDetBoxes
    print("craft_utils imported successfully")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")
