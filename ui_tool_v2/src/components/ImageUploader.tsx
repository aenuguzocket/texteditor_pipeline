import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { useApi } from '../hooks/useApi'
import { ProcessedData } from '../types/pipeline'

interface ImageUploaderProps {
  onProcessed: (data: ProcessedData) => void
  isProcessing: boolean
  setIsProcessing: (v: boolean) => void
}

export default function ImageUploader({
  onProcessed,
  isProcessing,
  setIsProcessing,
}: ImageUploaderProps) {
  const { processImage, error } = useApi()

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (acceptedFiles.length === 0) return

      const file = acceptedFiles[0]
      setIsProcessing(true)

      try {
        const result = await processImage(file)
        if (result) {
          onProcessed(result)
        }
      } finally {
        setIsProcessing(false)
      }
    },
    [processImage, onProcessed, setIsProcessing]
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.png', '.jpg', '.jpeg'],
    },
    maxFiles: 1,
    disabled: isProcessing,
  })

  return (
    <div className="w-full max-w-2xl">
      <div
        {...getRootProps()}
        className={`
          relative border-2 border-dashed rounded-2xl p-12
          transition-all duration-200 cursor-pointer
          ${isDragActive
            ? 'border-blue-500 bg-blue-500/10'
            : 'border-slate-600 hover:border-slate-500 bg-slate-800/50'
          }
          ${isProcessing ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <input {...getInputProps()} />

        <div className="flex flex-col items-center text-center">
          {isProcessing ? (
            <>
              <div className="w-16 h-16 mb-6 relative">
                <div className="absolute inset-0 border-4 border-slate-600 rounded-full" />
                <div className="absolute inset-0 border-4 border-blue-500 rounded-full border-t-transparent animate-spin" />
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">
                Processing Image...
              </h3>
              <p className="text-slate-400">
                Running text detection and layer separation
              </p>
              <div className="mt-6 w-full max-w-xs">
                <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-blue-500 to-purple-500 animate-pulse" style={{ width: '60%' }} />
                </div>
              </div>
            </>
          ) : (
            <>
              <div className="w-16 h-16 mb-6 bg-slate-700 rounded-2xl flex items-center justify-center">
                <svg className="w-8 h-8 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">
                {isDragActive ? 'Drop your image here' : 'Upload an image'}
              </h3>
              <p className="text-slate-400 mb-4">
                Drag and drop or click to select
              </p>
              <p className="text-sm text-slate-500">
                Supports PNG, JPG, JPEG
              </p>
            </>
          )}
        </div>
      </div>

      {error && (
        <div className="mt-4 p-4 bg-red-500/10 border border-red-500/50 rounded-lg">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      <div className="mt-8 grid grid-cols-3 gap-4 text-center">
        <div className="p-4 bg-slate-800/50 rounded-xl">
          <div className="text-2xl font-bold text-blue-400">1</div>
          <div className="text-sm text-slate-400 mt-1">Upload Image</div>
        </div>
        <div className="p-4 bg-slate-800/50 rounded-xl">
          <div className="text-2xl font-bold text-purple-400">2</div>
          <div className="text-sm text-slate-400 mt-1">Edit on Canvas</div>
        </div>
        <div className="p-4 bg-slate-800/50 rounded-xl">
          <div className="text-2xl font-bold text-green-400">3</div>
          <div className="text-sm text-slate-400 mt-1">Download Result</div>
        </div>
      </div>
    </div>
  )
}
