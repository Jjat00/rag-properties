import type { SearchResult, EmbeddingModelInfo, HealthStatus } from "@/types/api"

const BASE = "/api"

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`API error ${res.status}: ${body}`)
  }
  return res.json() as Promise<T>
}

export async function searchProperties(
  query: string,
  model: string,
  topK: number,
): Promise<SearchResult> {
  return request<SearchResult>("/search", {
    method: "POST",
    body: JSON.stringify({ query, model, top_k: topK }),
  })
}

export async function fetchModels(): Promise<EmbeddingModelInfo[]> {
  return request<EmbeddingModelInfo[]>("/models")
}

export async function fetchHealth(): Promise<HealthStatus> {
  return request<HealthStatus>("/health")
}
