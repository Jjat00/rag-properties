import type { MultimodalSearchResult } from "@/types/api"

const BASE = "/api"

export interface MultimodalSearchParams {
  query: string
  top_k?: number
  city?: string
  state?: string
  house_type?: string
  operation?: string
  min_bedrooms?: number
  max_bedrooms?: number
  min_price?: number
  max_price?: number
}

export async function searchMultimodal(
  params: MultimodalSearchParams,
): Promise<MultimodalSearchResult> {
  const res = await fetch(`${BASE}/multimodal/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query: params.query,
      top_k: params.top_k ?? 10,
      city: params.city,
      state: params.state,
      house_type: params.house_type,
      operation: params.operation,
      min_bedrooms: params.min_bedrooms,
      max_bedrooms: params.max_bedrooms,
      min_price: params.min_price,
      max_price: params.max_price,
    }),
  })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`API error ${res.status}: ${body}`)
  }
  return res.json() as Promise<MultimodalSearchResult>
}

export async function searchByImage(
  file: File,
  topK: number = 10,
): Promise<MultimodalSearchResult> {
  const formData = new FormData()
  formData.append("file", file)

  const res = await fetch(`${BASE}/multimodal/search-by-image?top_k=${topK}`, {
    method: "POST",
    body: formData,
  })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`API error ${res.status}: ${body}`)
  }
  return res.json() as Promise<MultimodalSearchResult>
}
