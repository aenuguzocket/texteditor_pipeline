import { useState } from 'react'
import { TextRegion, BoxRegion } from '../types/pipeline'
import { useApi } from '../hooks/useApi'

interface PropertyPanelProps {
  selectedElement: { type: 'text' | 'box'; id: string } | null
  textRegions: TextRegion[]
  boxRegions: BoxRegion[]
  onTextUpdate: (id: string, updates: Partial<TextRegion>) => void
  onBoxUpdate: (id: string, updates: Partial<BoxRegion>) => void
  runId: string
}

const FONT_OPTIONS = [
  'Roboto',
  'Poppins',
  'Inter',
  'Manrope',
  'Plus Jakarta Sans',
  'Oswald',
  'Bebas Neue',
  'Anton',
]

const WEIGHT_OPTIONS = [300, 400, 500, 600, 700, 800]

const API_BASE = import.meta.env.VITE_API_URL || ''

export default function PropertyPanel({
  selectedElement,
  textRegions,
  boxRegions,
  onTextUpdate,
  onBoxUpdate,
  runId,
}: PropertyPanelProps) {
  const { renderImage, loading } = useApi()
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null)

  const selectedText = selectedElement?.type === 'text'
    ? textRegions.find((r) => r.id === selectedElement.id)
    : null

  const selectedBox = selectedElement?.type === 'box'
    ? boxRegions.find((r) => r.id === selectedElement.id)
    : null

  const handleExport = async () => {
    const result = await renderImage({
      run_id: runId,
      text_regions: textRegions,
      box_regions: boxRegions,
    })

    if (result?.success) {
      const fullUrl = result.image_url.startsWith('/')
        ? `${API_BASE}${result.image_url}`
        : result.image_url
      setDownloadUrl(fullUrl)
    }
  }

  return (
    <div className="p-4">
      <h2 className="text-lg font-semibold text-white mb-4">Properties</h2>

      {!selectedElement ? (
        <div className="text-slate-400 text-sm">
          Select an element on the canvas to edit its properties
        </div>
      ) : selectedText ? (
        <div className="space-y-4">
          {/* Text Content */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Text Content
            </label>
            <textarea
              value={selectedText.text}
              onChange={(e) => onTextUpdate(selectedText.id, { text: e.target.value })}
              className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              rows={3}
            />
          </div>

          {/* Position */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Position
            </label>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs text-slate-400 mb-1">X</label>
                <input
                  type="number"
                  value={selectedText.bbox.x}
                  onChange={(e) =>
                    onTextUpdate(selectedText.id, {
                      bbox: { ...selectedText.bbox, x: parseInt(e.target.value) || 0 },
                    })
                  }
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Y</label>
                <input
                  type="number"
                  value={selectedText.bbox.y}
                  onChange={(e) =>
                    onTextUpdate(selectedText.id, {
                      bbox: { ...selectedText.bbox, y: parseInt(e.target.value) || 0 },
                    })
                  }
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>

          {/* Size */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Size
            </label>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Width</label>
                <input
                  type="number"
                  value={selectedText.bbox.width}
                  onChange={(e) =>
                    onTextUpdate(selectedText.id, {
                      bbox: { ...selectedText.bbox, width: parseInt(e.target.value) || 0 },
                    })
                  }
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Height</label>
                <input
                  type="number"
                  value={selectedText.bbox.height}
                  onChange={(e) =>
                    onTextUpdate(selectedText.id, {
                      bbox: { ...selectedText.bbox, height: parseInt(e.target.value) || 0 },
                    })
                  }
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>

          {/* Font */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Font Family
            </label>
            <select
              value={selectedText.font}
              onChange={(e) => onTextUpdate(selectedText.id, { font: e.target.value })}
              className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500"
            >
              {FONT_OPTIONS.map((font) => (
                <option key={font} value={font}>
                  {font}
                </option>
              ))}
            </select>
          </div>

          {/* Weight */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Font Weight
            </label>
            <select
              value={selectedText.weight}
              onChange={(e) =>
                onTextUpdate(selectedText.id, { weight: parseInt(e.target.value) })
              }
              className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500"
            >
              {WEIGHT_OPTIONS.map((weight) => (
                <option key={weight} value={weight}>
                  {weight}
                </option>
              ))}
            </select>
          </div>

          {/* Color */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Text Color
            </label>
            <div className="flex gap-2">
              <input
                type="color"
                value={selectedText.color}
                onChange={(e) => onTextUpdate(selectedText.id, { color: e.target.value })}
                className="w-12 h-10 rounded cursor-pointer"
              />
              <input
                type="text"
                value={selectedText.color}
                onChange={(e) => onTextUpdate(selectedText.id, { color: e.target.value })}
                className="flex-1 px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Role Badge */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Role
            </label>
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-green-500/20 text-green-400 border border-green-500/30">
              {selectedText.role}
            </span>
          </div>
        </div>
      ) : selectedBox ? (
        <div className="space-y-4">
          {/* Box Position */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Position
            </label>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs text-slate-400 mb-1">X</label>
                <input
                  type="number"
                  value={selectedBox.bbox.x}
                  onChange={(e) =>
                    onBoxUpdate(selectedBox.id, {
                      bbox: { ...selectedBox.bbox, x: parseInt(e.target.value) || 0 },
                    })
                  }
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Y</label>
                <input
                  type="number"
                  value={selectedBox.bbox.y}
                  onChange={(e) =>
                    onBoxUpdate(selectedBox.id, {
                      bbox: { ...selectedBox.bbox, y: parseInt(e.target.value) || 0 },
                    })
                  }
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>

          {/* Box Size */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Size
            </label>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Width</label>
                <input
                  type="number"
                  value={selectedBox.bbox.width}
                  onChange={(e) =>
                    onBoxUpdate(selectedBox.id, {
                      bbox: { ...selectedBox.bbox, width: parseInt(e.target.value) || 0 },
                    })
                  }
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Height</label>
                <input
                  type="number"
                  value={selectedBox.bbox.height}
                  onChange={(e) =>
                    onBoxUpdate(selectedBox.id, {
                      bbox: { ...selectedBox.bbox, height: parseInt(e.target.value) || 0 },
                    })
                  }
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>

          {/* Box Color */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Background Color
            </label>
            <div className="flex gap-2">
              <input
                type="color"
                value={selectedBox.color}
                onChange={(e) => onBoxUpdate(selectedBox.id, { color: e.target.value })}
                className="w-12 h-10 rounded cursor-pointer"
              />
              <input
                type="text"
                value={selectedBox.color}
                onChange={(e) => onBoxUpdate(selectedBox.id, { color: e.target.value })}
                className="flex-1 px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Box Type Badge */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Type
            </label>
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-blue-500/20 text-blue-400 border border-blue-500/30">
              CTA Box
            </span>
          </div>
        </div>
      ) : null}

      {/* Export Section */}
      <div className="mt-8 pt-4 border-t border-slate-700">
        <h3 className="text-sm font-semibold text-white mb-3">Export</h3>
        
        <button
          onClick={handleExport}
          disabled={loading}
          className="w-full px-4 py-3 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white font-medium rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Rendering...' : 'Generate Final Image'}
        </button>

        {downloadUrl && (
          <a
            href={downloadUrl}
            download="edited_image.png"
            className="mt-3 flex items-center justify-center gap-2 w-full px-4 py-3 bg-green-600 hover:bg-green-700 text-white font-medium rounded-lg transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Download Image
          </a>
        )}
      </div>

      {/* Element List */}
      <div className="mt-6 pt-4 border-t border-slate-700">
        <h3 className="text-sm font-semibold text-white mb-3">All Elements</h3>
        
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {textRegions.map((region) => (
            <button
              key={`text-${region.id}`}
              onClick={() => onTextUpdate(region.id, {})} // Trigger selection
              className={`w-full text-left px-3 py-2 rounded-lg transition-colors ${
                selectedElement?.type === 'text' && selectedElement?.id === region.id
                  ? 'bg-green-500/20 border border-green-500/50'
                  : 'bg-slate-700/50 hover:bg-slate-700'
              }`}
            >
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-green-500" />
                <span className="text-sm text-slate-300 truncate">
                  {region.text.substring(0, 30)}...
                </span>
              </div>
            </button>
          ))}
          
          {boxRegions.map((box) => (
            <button
              key={`box-${box.id}`}
              onClick={() => onBoxUpdate(box.id, {})} // Trigger selection
              className={`w-full text-left px-3 py-2 rounded-lg transition-colors ${
                selectedElement?.type === 'box' && selectedElement?.id === box.id
                  ? 'bg-blue-500/20 border border-blue-500/50'
                  : 'bg-slate-700/50 hover:bg-slate-700'
              }`}
            >
              <div className="flex items-center gap-2">
                <div 
                  className="w-4 h-4 rounded" 
                  style={{ backgroundColor: box.color }}
                />
                <span className="text-sm text-slate-300">
                  CTA Box {box.id}
                </span>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
