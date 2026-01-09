# Pipeline V4 API

FastAPI backend for image text detection and editing pipeline.

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/process` | Upload image and run full pipeline |
| GET | `/api/runs` | List all pipeline runs |
| GET | `/api/runs/{run_id}` | Get specific run data |
| POST | `/api/render` | Render final image with edits |
| GET | `/api/image/{run_id}/{filename}` | Serve images |

## Development

### Prerequisites

- Python 3.11+
- pip

### Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your API keys

# Run server
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

API runs at http://localhost:8000

API docs at http://localhost:8000/docs

## Environment Variables

```env
FAL_KEY=your_fal_ai_key
GEMINI_API_KEY=your_gemini_api_key
GOOGLE_FONTS_API_KEY=your_google_fonts_api_key
```

## Deployment (Railway)

1. Connect repository to Railway
2. Set environment variables in Railway dashboard
3. Deploy using the Dockerfile

## API Response Format

### POST /api/process

Request: `multipart/form-data` with `file` field

Response:
```json
{
  "run_id": "run_1234567890_layered",
  "status": "success",
  "original_size": {"width": 1080, "height": 1920},
  "background_url": "/api/image/run_id/base_canvas.png",
  "text_regions": [...],
  "box_regions": [...]
}
```

### POST /api/render

Request:
```json
{
  "run_id": "run_1234567890_layered",
  "text_regions": [...],
  "box_regions": [...]
}
```

Response:
```json
{
  "success": true,
  "image_url": "/api/image/run_id/edited_123.png",
  "message": "Image rendered successfully"
}
```
