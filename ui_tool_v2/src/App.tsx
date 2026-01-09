import { useState } from 'react'
import ImageUploader from './components/ImageUploader'
import FabricCanvas from './components/FabricCanvas'
import PropertyPanel from './components/PropertyPanel'
import { ProcessedData, TextRegion, BoxRegion } from './types/pipeline'

function App() {
  const [processedData, setProcessedData] = useState<ProcessedData | null>(null)
  const [selectedElement, setSelectedElement] = useState<{
    type: 'text' | 'box'
    id: string
  } | null>(null)
  const [textRegions, setTextRegions] = useState<TextRegion[]>([])
  const [boxRegions, setBoxRegions] = useState<BoxRegion[]>([])
  const [isProcessing, setIsProcessing] = useState(false)

  const handleProcessed = (data: ProcessedData) => {
    setProcessedData(data)
    setTextRegions(data.text_regions)
    setBoxRegions(data.box_regions)
  }

  const handleSelect = (type: 'text' | 'box', id: string) => {
    setSelectedElement({ type, id })
  }

  const handleTextUpdate = (id: string, updates: Partial<TextRegion>) => {
    setTextRegions(prev =>
      prev.map(r => (r.id === id ? { ...r, ...updates } : r))
    )
  }

  const handleBoxUpdate = (id: string, updates: Partial<BoxRegion>) => {
    setBoxRegions(prev =>
      prev.map(r => (r.id === id ? { ...r, ...updates } : r))
    )
  }

  const handleReset = () => {
    setProcessedData(null)
    setSelectedElement(null)
    setTextRegions([])
    setBoxRegions([])
  }

  return (
    <div className="min-h-screen bg-slate-900">
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
              <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
            <div>
              <h1 className="text-xl font-semibold text-white">Canvas Editor</h1>
              <p className="text-sm text-slate-400">Pipeline V4</p>
            </div>
          </div>
          
          {processedData && (
            <button
              onClick={handleReset}
              className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
            >
              New Image
            </button>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="flex h-[calc(100vh-73px)]">
        {!processedData ? (
          <div className="flex-1 flex items-center justify-center p-8">
            <ImageUploader
              onProcessed={handleProcessed}
              isProcessing={isProcessing}
              setIsProcessing={setIsProcessing}
            />
          </div>
        ) : (
          <>
            {/* Canvas Area */}
            <div className="flex-1 p-6 overflow-auto">
              <FabricCanvas
                backgroundUrl={processedData.background_url}
                originalSize={processedData.original_size}
                textRegions={textRegions}
                boxRegions={boxRegions}
                onSelect={handleSelect}
                onTextUpdate={handleTextUpdate}
                onBoxUpdate={handleBoxUpdate}
              />
            </div>

            {/* Property Panel */}
            <div className="w-80 bg-slate-800 border-l border-slate-700 overflow-y-auto">
              <PropertyPanel
                selectedElement={selectedElement}
                textRegions={textRegions}
                boxRegions={boxRegions}
                onTextUpdate={handleTextUpdate}
                onBoxUpdate={handleBoxUpdate}
                runId={processedData.run_id}
              />
            </div>
          </>
        )}
      </main>
    </div>
  )
}

export default App
