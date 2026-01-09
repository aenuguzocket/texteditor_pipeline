# Quick Start Guide

## Prerequisites
- Python 3.10+ installed
- Virtual environment set up in `venv` folder
- Environment variables configured in `.env` file

---

## 1. Running the Full Pipeline (CLI)

### Step 1: Navigate to Project Directory
```bash
cd c:\Users\harsh\Downloads\zocket\product_pipeline
```

### Step 2: Activate Virtual Environment
```bash
.\venv\Scripts\activate
```

### Step 3: Run the Pipeline
```bash
python pipeline_v4/run_pipeline_v4.py
```

### Optional: Specify a Custom Image
```bash
python pipeline_v4/run_pipeline_v4.py "image/your_image.png"
```

### Optional: Resume from Existing Run
```bash
python pipeline_v4/run_pipeline_v4.py "pipeline_outputs/run_1234567890_layered"
```

### Default Image
The default input image is configured in `pipeline_v4/run_pipeline_v4.py` (line 171):
```python
DEFAULT_INPUT = r"image/t1.jpg"
```

### Pipeline Stages
1. **Stage 1: Layering** - CRAFT detection, Gemini analysis, Qwen layer generation
2. **Stage 2: Box Detection** - CTA/background box extraction
3. **Stage 3: Text Rendering** - Final image composition

### Output
- Run directory: `pipeline_outputs/run_{timestamp}_layered/`
- Final image: `pipeline_outputs/run_{timestamp}_layered/final_composed.png`

---

## 2. Running Streamlit UI

### Step 1: Navigate to Project Directory
```bash
cd c:\Users\harsh\Downloads\zocket\product_pipeline
```

### Step 2: Activate Virtual Environment
```bash
.\venv\Scripts\activate
```

### Step 3: Run Streamlit
```bash
streamlit run ui_tool/app_p.py
```

### Access the UI
- **Local URL**: http://localhost:8501
- **Network URL**: http://your-ip:8501

### UI Features
- Select a pipeline run from the dropdown
- Edit text content in the sidebar
- Drag/reposition elements on the Canvas
- Click **"Update & Re-render 🚀"** to regenerate with changes
- Click **"🔄 Reload Fonts"** if Canvas fonts look incorrect

---

## Environment Variables (.env)

Required keys in `.env` file:
```
GOOGLE_API_KEY=your_google_api_key
GOOGLE_FONTS_API_KEY=your_fonts_api_key
FAL_KEY=your_fal_api_key
```

---

## Troubleshooting

### Pipeline Errors
- Ensure `.env` file has all required API keys
- Check if CRAFT model weights exist: `CRAFT-pytorch/craft_mlt_25k.pth`

### Streamlit Errors
- If fonts look wrong, click **"🔄 Reload Fonts"** button
- If canvas doesn't load, click **"Reset Layout"**

### Memory Issues
- Close other applications to free GPU/RAM
- Use smaller images for testing
