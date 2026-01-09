import { useEffect, useRef, useState } from 'react'
import { fabric } from 'fabric'
import { TextRegion, BoxRegion, BBox } from '../types/pipeline'

interface FabricCanvasProps {
  backgroundUrl: string
  originalSize: { width: number; height: number }
  textRegions: TextRegion[]
  boxRegions: BoxRegion[]
  onSelect: (type: 'text' | 'box', id: string) => void
  onTextUpdate: (id: string, updates: Partial<TextRegion>) => void
  onBoxUpdate: (id: string, updates: Partial<BoxRegion>) => void
}

const API_BASE = import.meta.env.VITE_API_URL || ''

export default function FabricCanvas({
  backgroundUrl,
  originalSize,
  textRegions,
  boxRegions,
  onSelect,
  onTextUpdate,
  onBoxUpdate,
}: FabricCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const fabricRef = useRef<fabric.Canvas | null>(null)
  const [canvasReady, setCanvasReady] = useState(false)
  const [scale, setScale] = useState(1)

  // Initialize canvas
  useEffect(() => {
    if (!canvasRef.current) return

    const canvas = new fabric.Canvas(canvasRef.current, {
      backgroundColor: '#1e293b',
      selection: true,
      preserveObjectStacking: true,
    })

    fabricRef.current = canvas

    // Calculate scale to fit in viewport
    const containerWidth = 800
    const containerHeight = 700
    const scaleX = containerWidth / originalSize.width
    const scaleY = containerHeight / originalSize.height
    const newScale = Math.min(scaleX, scaleY, 1)
    setScale(newScale)

    // Set canvas dimensions
    canvas.setWidth(originalSize.width * newScale)
    canvas.setHeight(originalSize.height * newScale)
    canvas.setZoom(newScale)

    setCanvasReady(true)

    return () => {
      canvas.dispose()
      fabricRef.current = null
    }
  }, [originalSize])

  // Load background image
  useEffect(() => {
    if (!canvasReady || !fabricRef.current) return

    const canvas = fabricRef.current
    const fullUrl = backgroundUrl.startsWith('/') 
      ? `${API_BASE}${backgroundUrl}` 
      : backgroundUrl

    fabric.Image.fromURL(
      fullUrl,
      (img) => {
        if (!img) return
        
        img.set({
          selectable: false,
          evented: false,
          originX: 'left',
          originY: 'top',
        })

        // Remove existing background
        const objects = canvas.getObjects()
        const existingBg = objects.find((o) => o.data?.type === 'background')
        if (existingBg) canvas.remove(existingBg)

        img.data = { type: 'background' }
        canvas.add(img)
        canvas.sendToBack(img)
        canvas.renderAll()
      },
      { crossOrigin: 'anonymous' }
    )
  }, [backgroundUrl, canvasReady])

  // Add box regions
  useEffect(() => {
    if (!canvasReady || !fabricRef.current) return

    const canvas = fabricRef.current

    // Remove existing boxes
    const objects = canvas.getObjects()
    objects
      .filter((o) => o.data?.type === 'box')
      .forEach((o) => canvas.remove(o))

    // Add box regions
    boxRegions.forEach((box) => {
      const rect = new fabric.Rect({
        left: box.bbox.x,
        top: box.bbox.y,
        width: box.bbox.width,
        height: box.bbox.height,
        fill: box.color + 'CC', // Add transparency
        stroke: box.color,
        strokeWidth: 2,
        cornerColor: '#3b82f6',
        cornerStyle: 'circle',
        transparentCorners: false,
        cornerSize: 10,
        borderColor: '#3b82f6',
        borderScaleFactor: 2,
      })

      rect.data = { type: 'box', id: box.id }

      rect.on('selected', () => {
        onSelect('box', box.id)
      })

      rect.on('modified', () => {
        const newBbox: BBox = {
          x: Math.round(rect.left || 0),
          y: Math.round(rect.top || 0),
          width: Math.round((rect.width || 0) * (rect.scaleX || 1)),
          height: Math.round((rect.height || 0) * (rect.scaleY || 1)),
        }
        onBoxUpdate(box.id, { bbox: newBbox })
      })

      canvas.add(rect)
    })

    canvas.renderAll()
  }, [boxRegions, canvasReady, onSelect, onBoxUpdate])

  // Add text regions
  useEffect(() => {
    if (!canvasReady || !fabricRef.current) return

    const canvas = fabricRef.current

    // Remove existing text
    const objects = canvas.getObjects()
    objects
      .filter((o) => o.data?.type === 'text')
      .forEach((o) => canvas.remove(o))

    // Add text regions
    textRegions.forEach((region) => {
      const fontSize = Math.round(region.bbox.height * 0.7)
      
      const text = new fabric.IText(region.text, {
        left: region.bbox.x,
        top: region.bbox.y,
        fontSize: fontSize,
        fontFamily: region.font,
        fontWeight: region.weight,
        fill: region.color,
        cornerColor: '#10b981',
        cornerStyle: 'circle',
        transparentCorners: false,
        cornerSize: 10,
        borderColor: '#10b981',
        borderScaleFactor: 2,
        editable: true,
      })

      text.data = { type: 'text', id: region.id }

      text.on('selected', () => {
        onSelect('text', region.id)
      })

      text.on('modified', () => {
        const newBbox: BBox = {
          x: Math.round(text.left || 0),
          y: Math.round(text.top || 0),
          width: Math.round((text.width || 0) * (text.scaleX || 1)),
          height: Math.round((text.height || 0) * (text.scaleY || 1)),
        }
        onTextUpdate(region.id, { bbox: newBbox })
      })

      text.on('editing:exited', () => {
        onTextUpdate(region.id, { text: text.text || '' })
      })

      canvas.add(text)
    })

    canvas.renderAll()
  }, [textRegions, canvasReady, onSelect, onTextUpdate])

  return (
    <div className="flex flex-col items-center">
      <div 
        className="border border-slate-700 rounded-lg overflow-hidden shadow-2xl"
        style={{ 
          width: originalSize.width * scale,
          height: originalSize.height * scale,
        }}
      >
        <canvas ref={canvasRef} />
      </div>

      <div className="mt-4 flex items-center gap-4 text-sm text-slate-400">
        <span>Size: {originalSize.width} × {originalSize.height}</span>
        <span>•</span>
        <span>Scale: {Math.round(scale * 100)}%</span>
        <span>•</span>
        <span>{textRegions.length} text regions</span>
        <span>•</span>
        <span>{boxRegions.length} CTA boxes</span>
      </div>

      <div className="mt-4 flex gap-2">
        <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 rounded-lg">
          <div className="w-3 h-3 rounded-full bg-green-500" />
          <span className="text-sm text-slate-400">Text</span>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 rounded-lg">
          <div className="w-3 h-3 rounded-full bg-blue-500" />
          <span className="text-sm text-slate-400">CTA Box</span>
        </div>
      </div>
    </div>
  )
}
