# Streamlit Demo for Pipeline V4

A web-based interface for the Image Text Removal & Editing Pipeline.

## Features

- **Upload Images**: Simple drag-and-drop interface
- **Full Pipeline Execution**: Automatically runs all 3 stages:
  1. Text Detection & Layer Separation (CRAFT + Gemini + Qwen)
  2. Background Box Detection (CTA extraction)
  3. Final Composition & Text Rendering
- **Progress Tracking**: Real-time progress indicators
- **Results Display**: View final image, layers, and extracted boxes
- **Download**: Download the final editable image

## Quick Start

### Local Development

1. **Install dependencies** (if not already installed):
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables**:
   Create a `.env` file in the root directory:
   ```env
   FAL_KEY=your_fal_ai_key
   GEMINI_API_KEY=your_google_gemini_key
   GOOGLE_FONTS_API_KEY=your_google_fonts_api_key
   ```

3. **Run the Streamlit app**:
   ```bash
   streamlit run streamlit_app.py
   ```

4. **Open in browser**:
   Navigate to `http://localhost:8501`

### Streamlit Cloud Deployment

1. **Push to GitHub**: Ensure your code is in a GitHub repository

2. **Create Streamlit Cloud App**:
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Click "New App"
   - Connect your GitHub repository
   - Set **Main file path**: `streamlit_app.py`

3. **Configure Secrets**:
   - Go to "Advanced Settings" → "Secrets"
   - Add your API keys:
   ```toml
   FAL_KEY = "your_fal_ai_key"
   GEMINI_API_KEY = "your_google_gemini_key"
   GOOGLE_FONTS_API_KEY = "your_google_fonts_api_key"
   ```

4. **Deploy**: Click "Deploy"

## Pipeline Stages

### Stage 1: Text Detection & Layer Separation
- **CRAFT**: Detects all text regions in the image
- **Gemini**: Classifies text roles (heading, CTA, body, etc.)
- **Qwen**: Splits image into layers (background, text, UI elements)
- **Cleaning**: Removes text from background layers

### Stage 2: Background Box Detection
- Detects background boxes/containers behind text (CTAs, buttons)
- Extracts box images with proper cleaning
- Maps boxes to text regions

### Stage 3: Final Composition
- Composites cleaned layers
- Places extracted background boxes
- Renders text with proper fonts, sizes, and alignment

## Usage

### Basic Pipeline

1. **Upload Image**: Click "Browse files" and select an image (PNG, JPG, JPEG)
2. **Run Pipeline**: Click "🚀 Run Pipeline" button
3. **Wait for Processing**: Monitor progress in the progress bar
4. **View Results**: 
   - See the final composed image
   - View individual layers
   - Check extracted background boxes
   - Download the final image

### Canvas Editor (Advanced Editing)

1. **Run the Editor**: 
   ```bash
   streamlit run streamlit_editor.py
   ```

2. **Load Pipeline Result**: 
   - Select a pipeline run from the sidebar
   - Click "Load Run" to load the data

3. **Edit Text Elements**:
   - **Select Region**: Choose a text region from the dropdown
   - **Edit Text**: Change text content in the text area
   - **Move**: Adjust X/Y position with number inputs or arrow buttons
   - **Resize**: Change width/height or use resize buttons
   - **Font**: Change font family, weight, and size
   - **Color**: Pick a new text color
   - **Preview**: See changes in real-time on the canvas

4. **Save**: Click "Save Edited Image" to export your changes

## Output Structure

The pipeline creates a run directory in `pipeline_outputs/run_<timestamp>_layered/` containing:
- `final_composed.png`: Final editable image
- `layers/`: Individual layer images
- `layers/extracted_boxes/`: Extracted background box images
- `pipeline_report_with_boxes.json`: Complete pipeline report
- `crops/`: Text region crops for analysis

## Requirements

- Python 3.8+
- All dependencies from `requirements.txt`
- API keys for:
  - FAL.ai (for Qwen image layering)
  - Google Gemini (for text analysis)
  - Google Fonts (for font downloading)

## Troubleshooting

### Environment Variables Not Found
- Ensure `.env` file exists in root directory
- For Streamlit Cloud, add secrets in the dashboard
- Check that variable names match exactly

### Import Errors
- Ensure `pipeline_v4/` directory is present
- Check that all required modules are in place
- Verify Python path includes project root

### Pipeline Fails
- Check API keys are valid
- Verify image format is supported (PNG, JPG, JPEG)
- Check console output for detailed error messages

## Notes

- The pipeline uses the same logic as the command-line version
- All changes are reversible via git
- Processing time depends on image size and complexity
- Large images may take several minutes to process

