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
  const objectsRef = useRef<Map<string, fabric.Object>>(new Map())
  const [canvasReady, setCanvasReady] = useState(false)
  const [scale, setScale] = useState(1)
  const isUpdatingRef = useRef(false)

  // Debug logging
  useEffect(() => {
    console.log('[FabricCanvas] Props updated:', {
      backgroundUrl,
      textRegionsCount: textRegions.length,
      boxRegionsCount: boxRegions.length,
      textRegions,
      boxRegions
    })
  }, [backgroundUrl, textRegions, boxRegions])

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
      objectsRef.current.clear()
    }
  }, [originalSize])

  // Load background image
  useEffect(() => {
    if (!canvasReady || !fabricRef.current) return

    const canvas = fabricRef.current
    const fullUrl = backgroundUrl.startsWith('/') 
      ? `${API_BASE}${backgroundUrl}` 
      : backgroundUrl

    console.log('[FabricCanvas] Loading background:', fullUrl)

    fabric.Image.fromURL(
      fullUrl,
      (img) => {
        if (!img) {
          console.error('[FabricCanvas] Failed to load background image')
          return
        }
        
        console.log('[FabricCanvas] Background loaded successfully')
        
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

  // Add or update box regions
  useEffect(() => {
    if (!canvasReady || !fabricRef.current || isUpdatingRef.current) return

    const canvas = fabricRef.current
    console.log('[FabricCanvas] Processing box regions:', boxRegions.length)

    boxRegions.forEach((box) => {
      const existingObj = objectsRef.current.get(`box-${box.id}`)
      
      if (existingObj && existingObj instanceof fabric.Rect) {
        // Update existing object only if properties changed externally
        const currentLeft = existingObj.left || 0
        const currentTop = existingObj.top || 0
        const currentWidth = (existingObj.width || 0) * (existingObj.scaleX || 1)
        const currentHeight = (existingObj.height || 0) * (existingObj.scaleY || 1)

        if (
          Math.abs(currentLeft - box.bbox.x) > 1 ||
          Math.abs(currentTop - box.bbox.y) > 1 ||
          Math.abs(currentWidth - box.bbox.width) > 1 ||
          Math.abs(currentHeight - box.bbox.height) > 1
        ) {
          // Only update if significantly different (external change)
          existingObj.set({
            left: box.bbox.x,
            top: box.bbox.y,
            width: box.bbox.width,
            height: box.bbox.height,
            scaleX: 1,
            scaleY: 1,
            fill: box.color + 'CC',
            stroke: box.color,
          })
          canvas.renderAll()
        }
      } else {
        // Create new box
        console.log('[FabricCanvas] Creating new box:', box.id)
        const rect = new fabric.Rect({
          left: box.bbox.x,
          top: box.bbox.y,
          width: box.bbox.width,
          height: box.bbox.height,
          fill: box.color + 'CC',
          stroke: box.color,
          strokeWidth: 2,
          cornerColor: '#3b82f6',
          cornerStyle: 'circle',
          transparentCorners: false,
          cornerSize: 10,
          borderColor: '#3b82f6',
          borderScaleFactor: 2,
          selectable: true,
          hasControls: true,
          hasBorders: true,
          lockMovementX: false,
          lockMovementY: false,
          lockRotation: false,
          lockScalingX: false,
          lockScalingY: false,
        })

        rect.data = { type: 'box', id: box.id }

        rect.on('selected', () => {
          onSelect('box', box.id)
        })

        rect.on('moving', () => {
          canvas.renderAll()
        })

        rect.on('scaling', () => {
          canvas.renderAll()
        })

        rect.on('modified', () => {
          isUpdatingRef.current = true
          const newBbox: BBox = {
            x: Math.round(rect.left || 0),
            y: Math.round(rect.top || 0),
            width: Math.round((rect.width || 0) * (rect.scaleX || 1)),
            height: Math.round((rect.height || 0) * (rect.scaleY || 1)),
          }
          onBoxUpdate(box.id, { bbox: newBbox })
          // Reset scale after update
          rect.set({ scaleX: 1, scaleY: 1 })
          rect.setCoords()
          isUpdatingRef.current = false
        })

        objectsRef.current.set(`box-${box.id}`, rect)
        canvas.add(rect)
      }
    })

    // Remove boxes that no longer exist
    const currentBoxIds = new Set(boxRegions.map(b => `box-${b.id}`))
    objectsRef.current.forEach((obj, key) => {
      if (key.startsWith('box-') && !currentBoxIds.has(key)) {
        canvas.remove(obj)
        objectsRef.current.delete(key)
      }
    })

    canvas.renderAll()
  }, [boxRegions, canvasReady, onSelect, onBoxUpdate])

  // Add or update text regions
  useEffect(() => {
    if (!canvasReady || !fabricRef.current || isUpdatingRef.current) return

    const canvas = fabricRef.current
    console.log('[FabricCanvas] Processing text regions:', textRegions.length)

    textRegions.forEach((region) => {
      const existingObj = objectsRef.current.get(`text-${region.id}`)
      
      if (existingObj && existingObj instanceof fabric.IText) {
        // Update existing text only if properties changed externally
        const currentLeft = existingObj.left || 0
        const currentTop = existingObj.top || 0
        const currentWidth = (existingObj.width || 0) * (existingObj.scaleX || 1)
        const currentHeight = (existingObj.height || 0) * (existingObj.scaleY || 1)

        if (
          existingObj.text !== region.text ||
          existingObj.fontFamily !== region.font ||
          existingObj.fontWeight !== String(region.weight) ||
          existingObj.fill !== region.color ||
          Math.abs(currentLeft - region.bbox.x) > 1 ||
          Math.abs(currentTop - region.bbox.y) > 1 ||
          Math.abs(currentWidth - region.bbox.width) > 1 ||
          Math.abs(currentHeight - region.bbox.height) > 1
        ) {
          // Update if changed externally
          const fontSize = Math.round(region.bbox.height * 0.7)
          existingObj.set({
            text: region.text,
            left: region.bbox.x,
            top: region.bbox.y,
            width: region.bbox.width,
            height: region.bbox.height,
            scaleX: 1,
            scaleY: 1,
            fontSize: fontSize,
            fontFamily: region.font,
            fontWeight: region.weight,
            fill: region.color,
          })
          existingObj.setCoords()
          canvas.renderAll()
        }
      } else {
        // Create new text
        console.log('[FabricCanvas] Creating new text:', region.id, region.text.substring(0, 30))
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
          selectable: true,
          hasControls: true,
          hasBorders: true,
          lockMovementX: false,
          lockMovementY: false,
          lockRotation: false,
          lockScalingX: false,
          lockScalingY: false,
        })

        text.data = { type: 'text', id: region.id }

        text.on('selected', () => {
          onSelect('text', region.id)
        })

        text.on('moving', () => {
          canvas.renderAll()
        })

        text.on('scaling', () => {
          canvas.renderAll()
        })

        text.on('modified', () => {
          isUpdatingRef.current = true
          const newBbox: BBox = {
            x: Math.round(text.left || 0),
            y: Math.round(text.top || 0),
            width: Math.round((text.width || 0) * (text.scaleX || 1)),
            height: Math.round((text.height || 0) * (text.scaleY || 1)),
          }
          onTextUpdate(region.id, { bbox: newBbox })
          // Reset scale after update
          text.set({ scaleX: 1, scaleY: 1 })
          text.setCoords()
          isUpdatingRef.current = false
        })

        text.on('editing:exited', () => {
          isUpdatingRef.current = true
          onTextUpdate(region.id, { text: text.text || '' })
          isUpdatingRef.current = false
        })

        objectsRef.current.set(`text-${region.id}`, text)
        canvas.add(text)
      }
    })

    // Remove text that no longer exists
    const currentTextIds = new Set(textRegions.map(r => `text-${r.id}`))
    objectsRef.current.forEach((obj, key) => {
      if (key.startsWith('text-') && !currentTextIds.has(key)) {
        canvas.remove(obj)
        objectsRef.current.delete(key)
      }
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
          <span className="text-sm text-slate-400">Text (drag, resize, edit)</span>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 rounded-lg">
          <div className="w-3 h-3 rounded-full bg-blue-500" />
          <span className="text-sm text-slate-400">CTA Box (drag, resize)</span>
        </div>
      </div>

      <div className="mt-2 text-xs text-slate-500">
        💡 Click to select • Drag to move • Use corners to resize • Double-click text to edit
      </div>
    </div>
  )
}
