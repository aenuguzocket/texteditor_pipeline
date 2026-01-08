# Text Rendering Layer (Pillow)

This folder contains a standalone rendering layer.
It does NOT modify or depend on the existing pipeline.

## Inputs
- Clean image (Nano Banana Pro output)
- final_result_batch.json (CRAFT + Gemini + normalization)

## What it does
- Downloads required Google Fonts automatically
- Renders text using Pillow
- Outputs a final composited image

## Run
```bash
python rendering/render_from_json_pillow.py path/to/final_result.json
```

## Editing
1. Change text or color in final_result_batch.json
2. Re-run the script
3. New image is generated

## Notes
- Fonts are cached locally in `/fonts`
- No Gemini calls here
- Safe to delete or replace independently
