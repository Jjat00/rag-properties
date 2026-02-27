import { useCallback, useState } from "react"
import type { SearchResult } from "@/types/api"
import { searchProperties } from "@/lib/api"

export type SearchStatus = "idle" | "loading" | "success" | "error"

interface SearchState {
  status: SearchStatus
  data: SearchResult | null
  error: string | null
}

export function useSearch() {
  const [state, setState] = useState<SearchState>({
    status: "idle",
    data: null,
    error: null,
  })

  const search = useCallback(async (query: string, model: string, topK: number) => {
    setState({ status: "loading", data: null, error: null })
    try {
      const result = await searchProperties(query, model, topK)
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

  return { ...state, search, reset }
}
