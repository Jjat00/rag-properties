import { useEffect, useState } from "react"
import type { EmbeddingModelInfo } from "@/types/api"
import { fetchModels } from "@/lib/api"

export function useModels() {
  const [models, setModels] = useState<EmbeddingModelInfo[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchModels()
      .then(setModels)
      .catch(() => setModels([]))
      .finally(() => setLoading(false))
  }, [])

  const defaultModel = models.find((m) => m.is_default)?.id ?? models[0]?.id ?? "openai-small"

  return { models, loading, defaultModel }
}
