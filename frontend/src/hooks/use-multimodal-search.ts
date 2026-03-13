import { useCallback, useState } from "react"
import type { MultimodalSearchResult } from "@/types/api"
import { searchMultimodal, searchByImage, type MultimodalSearchParams } from "@/lib/multimodal-api"

export type MultimodalSearchStatus = "idle" | "loading" | "success" | "error"

interface MultimodalSearchState {
  status: MultimodalSearchStatus
  data: MultimodalSearchResult | null
  error: string | null
}

export function useMultimodalSearch() {
  const [state, setState] = useState<MultimodalSearchState>({
    status: "idle",
    data: null,
    error: null,
  })

  const search = useCallback(async (params: MultimodalSearchParams) => {
    setState({ status: "loading", data: null, error: null })
    try {
      const result = await searchMultimodal(params)
      setState({ status: "success", data: result, error: null })
      return result
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error"
      setState({ status: "error", data: null, error: message })
      return null
    }
  }, [])

  const searchImage = useCallback(async (file: File, topK?: number) => {
    setState({ status: "loading", data: null, error: null })
    try {
      const result = await searchByImage(file, topK)
      setState({ status: "success", data: result, error: null })
      return result
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error"
      setState({ status: "error", data: null, error: message })
      return null
    }
  }, [])

  const reset = useCallback(() => {
    setState({ status: "idle", data: null, error: null })
  }, [])

  return { ...state, search, searchImage, reset }
}
