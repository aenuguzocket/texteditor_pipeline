# Product Pipeline & UI Tool

A generative AI pipeline for decomposing product images into editable layers (Product, Text, Background, UI Elements) and an interactive Streamlit UI for editing them.

## Features
- **Layering**: Splits images using Qwen-2.5 VL (via fal.ai).
- **Text Detection**: Uses CRAFT for robust text detection.
- **Analysis**: Uses Gemini 1.5 Pro to classify text roles (Heading, CTA, etc.).
- **Cleaning**: Automatically erases text from background layers.
- **UI Editor**: Streamlit-based drag-and-drop editor for text and layout.

---

## 🚀 Getting Started (Local)

### 1. Installation
```bash
# Clone repository
git clone <repo_url>
cd product_pipeline

# Create virtual env
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Setup
Create a `.env` file in the root directory:
```env
FAL_KEY=your_fal_ai_key
GEMINI_API_KEY=your_google_gemini_key
```

### 3. Run the UI
```bash
streamlit run ui_tool/app.py
```
- Navigate to `http://localhost:8501`
- Upload an image in the sidebar to process it.
- Edit text and layout in the canvas.

---

## ☁️ Deployment (Streamlit Cloud)

This project is ready for Streamlit Cloud.

1. **Push to GitHub**: Ensure this code is in a GitHub repository.
2. **New App**: Go to [share.streamlit.io](https://share.streamlit.io) and click "New App".
3. **Configuration**:
    - **Repository**: Select your repo.
    - **Branch**: `main` (or your branch).
    - **Main file path**: `ui_tool/app.py` 👈 **IMPORTANT**
4. **Secrets**:
    - Go to "Advanced Settings" -> "Secrets".
    - Add your keys:
    ```toml
    FAL_KEY = "your_fal_ai_key"
    GEMINI_API_KEY = "your_google_gemini_key"
    ```
5. **Deploy**: Click "Deploy". System dependencies (`packages.txt`) will be installed automatically.

---

## Folder Structure
- `pipeline_v4/`: Core pipeline logic (Layering, Detection, Cleaning).
- `ui_tool/`: Streamlit frontend application.
- `pipeline_outputs/`: Stores processed runs, layers, and reports.
- `requirements.txt`: Python dependencies.
- `packages.txt`: System dependencies (Linux libs for OpenCV).
