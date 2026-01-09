import { useState, useCallback } from 'react'
import axios from 'axios'
import {
  ProcessedData,
  RenderRequest,
  RenderResponse,
  RunsResponse,
} from '../types/pipeline'

const API_BASE = import.meta.env.VITE_API_URL || ''

export function useApi() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const processImage = useCallback(async (file: File): Promise<ProcessedData | null> => {
    setLoading(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await axios.post<ProcessedData>(
        `${API_BASE}/api/process`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          timeout: 300000, // 5 minutes for processing
        }
      )

      return response.data
    } catch (err) {
      const message = axios.isAxiosError(err)
        ? err.response?.data?.detail || err.message
        : 'Unknown error'
      setError(message)
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  const getRun = useCallback(async (runId: string): Promise<ProcessedData | null> => {
    setLoading(true)
    setError(null)

    try {
      const response = await axios.get<ProcessedData>(
        `${API_BASE}/api/runs/${runId}`
      )
      return response.data
    } catch (err) {
      const message = axios.isAxiosError(err)
        ? err.response?.data?.detail || err.message
        : 'Unknown error'
      setError(message)
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  const listRuns = useCallback(async (): Promise<RunsResponse | null> => {
    setLoading(true)
    setError(null)

    try {
      const response = await axios.get<RunsResponse>(`${API_BASE}/api/runs`)
      return response.data
    } catch (err) {
      const message = axios.isAxiosError(err)
        ? err.response?.data?.detail || err.message
        : 'Unknown error'
      setError(message)
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  const renderImage = useCallback(async (
    request: RenderRequest
  ): Promise<RenderResponse | null> => {
    setLoading(true)
    setError(null)

    try {
      const response = await axios.post<RenderResponse>(
        `${API_BASE}/api/render`,
        request
      )
      return response.data
    } catch (err) {
      const message = axios.isAxiosError(err)
        ? err.response?.data?.detail || err.message
        : 'Unknown error'
      setError(message)
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  const getImageUrl = useCallback((runId: string, filename: string): string => {
    return `${API_BASE}/api/image/${runId}/${filename}`
  }, [])

  return {
    loading,
    error,
    processImage,
    getRun,
    listRuns,
    renderImage,
    getImageUrl,
  }
}
