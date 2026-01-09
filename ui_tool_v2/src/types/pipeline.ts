// Pipeline API Types

export interface BBox {
  x: number
  y: number
  width: number
  height: number
}

export interface TextRegion {
  id: string
  text: string
  bbox: BBox
  font: string
  weight: number
  color: string
  role: string
}

export interface BoxRegion {
  id: string
  bbox: BBox
  color: string
}

export interface ProcessedData {
  run_id: string
  status: string
  original_size: {
    width: number
    height: number
  }
  background_url: string
  text_regions: TextRegion[]
  box_regions: BoxRegion[]
}

export interface RenderRequest {
  run_id: string
  text_regions: TextRegion[]
  box_regions: BoxRegion[]
}

export interface RenderResponse {
  success: boolean
  image_url: string
  message: string
}

export interface RunInfo {
  run_id: string
  input_image: string
  created_at: number
}

export interface RunsResponse {
  runs: RunInfo[]
}
