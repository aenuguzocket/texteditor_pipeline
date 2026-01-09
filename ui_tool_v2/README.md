# Canvas Editor - Pipeline V4 Frontend

React + TypeScript + Vite frontend with Fabric.js canvas for visual editing.

## Features

- **Image Upload**: Drag-and-drop image upload with processing
- **Fabric.js Canvas**: Interactive canvas for editing text and CTA boxes
- **Property Panel**: Edit text content, font, color, position, size
- **Export**: Generate final image with all edits

## Development

### Prerequisites

- Node.js 18+
- npm or yarn

### Setup

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The app runs at http://localhost:3000

### Environment Variables

Create `.env` file:

```env
# Leave empty for local development (uses Vite proxy)
VITE_API_URL=

# For production, set your Railway API URL
# VITE_API_URL=https://your-api.up.railway.app
```

## Build

```bash
npm run build
```

Output is in `dist/` folder.

## Deployment (Vercel)

1. Connect repository to Vercel
2. Set environment variable: `VITE_API_URL=https://your-railway-api.up.railway.app`
3. Deploy

## Project Structure

```
src/
├── App.tsx              # Main app component
├── main.tsx             # Entry point
├── index.css            # Global styles (Tailwind)
├── components/
│   ├── ImageUploader.tsx   # Upload component
│   ├── FabricCanvas.tsx    # Fabric.js canvas
│   └── PropertyPanel.tsx   # Edit controls
├── hooks/
│   └── useApi.ts        # API client hooks
└── types/
    └── pipeline.ts      # TypeScript types
```

## Tech Stack

- React 18
- TypeScript
- Vite
- Fabric.js 5
- Tailwind CSS
- Axios
