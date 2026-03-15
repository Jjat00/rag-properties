import type { MultimodalSearchResult } from "@/types/api"

const BASE = "/api"

export interface MultimodalSearchParams {
  query: string
  top_k?: number
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
