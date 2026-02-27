import { useState, useCallback } from "react"
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Loader2, GitCompare } from "lucide-react"
import type { EmbeddingModelInfo, SearchResult } from "@/types/api"
import { searchProperties } from "@/lib/api"
import { formatScore } from "@/lib/utils"

interface ModelComparisonProps {
  models: EmbeddingModelInfo[]
  currentQuery: string
  topK: number
}

const MODEL_COLORS: Record<string, string> = {
  "openai-small": "#3B82F6",
  "openai-large": "#8B5CF6",
  gemini: "#22C55E",
}

const MODEL_LABELS: Record<string, string> = {
  "openai-small": "OpenAI Small",
  "openai-large": "OpenAI Large",
  gemini: "Gemini",
}

export function ModelComparison({ models, currentQuery, topK }: ModelComparisonProps) {
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [results, setResults] = useState<Map<string, SearchResult>>(new Map())
  const [loading, setLoading] = useState(false)

  const toggleModel = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const runComparison = useCallback(async () => {
    if (selected.size === 0) return
    setLoading(true)
    try {
      const entries = await Promise.all(
        [...selected].map(async (modelId) => {
          const result = await searchProperties(currentQuery, modelId, topK)
          return [modelId, result] as const
        }),
      )
      setResults(new Map(entries))
    } finally {
      setLoading(false)
    }
  }, [selected, currentQuery, topK])

  // Build score-by-position chart data
  const chartData = Array.from({ length: topK }, (_, i) => {
    const row: Record<string, number | string> = { position: `#${i + 1}` }
    for (const [modelId, result] of results) {
      const r = result.results[i]
      row[modelId] = r ? formatScore(r.score) : 0
    }
    return row
  }).filter((row) => {
    // Only show rows that have at least one non-zero value
    return [...results.keys()].some((k) => (row[k] as number) > 0)
  })

  // Compute overlap
  const modelIds = [...results.keys()]
  let overlapText = ""
  if (modelIds.length === 2) {
    const idsA = new Set(results.get(modelIds[0])?.results.map((r) => r.id) ?? [])
    const idsB = new Set(results.get(modelIds[1])?.results.map((r) => r.id) ?? [])
    const overlap = [...idsA].filter((id) => idsB.has(id)).length
    const total = Math.max(idsA.size, idsB.size)
    overlapText = `${overlap} de ${total} resultados aparecen en ambos modelos`
  }

  return (
    <Card className="bg-card border-border">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Comparacion de Modelos
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Model selection */}
        <div className="flex items-center gap-2 flex-wrap">
          {models.map((m) => (
            <Button
              key={m.id}
              variant={selected.has(m.id) ? "default" : "outline"}
              size="sm"
              onClick={() => toggleModel(m.id)}
              style={
                selected.has(m.id)
                  ? { backgroundColor: MODEL_COLORS[m.id], borderColor: MODEL_COLORS[m.id] }
                  : undefined
              }
            >
              {MODEL_LABELS[m.id] ?? m.id}
            </Button>
          ))}
          <Button
            size="sm"
            variant="outline"
            onClick={runComparison}
            disabled={selected.size === 0 || loading}
            className="ml-auto"
          >
            {loading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" />
            ) : (
              <GitCompare className="h-3.5 w-3.5 mr-1" />
            )}
            Comparar
          </Button>
        </div>

        {/* Results chart */}
        {results.size > 0 && chartData.length > 0 && (
          <>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={chartData}>
                <XAxis
                  dataKey="position"
                  tick={{ fill: "#8C8C8C", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  domain={[0, 100]}
                  tick={{ fill: "#8C8C8C", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  width={35}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0E0E0F",
                    border: "1px solid #1F1F1F",
                    borderRadius: "8px",
                    color: "#F2F2F2",
                    fontSize: 12,
                  }}
                  formatter={(value, name) => [
                    `${value}%`,
                    MODEL_LABELS[name as string] ?? name,
                  ]}
                />
                <Legend
                  formatter={(value: string) => MODEL_LABELS[value] ?? value}
                  wrapperStyle={{ fontSize: 12, color: "#8C8C8C" }}
                />
                {modelIds.map((id) => (
                  <Bar key={id} dataKey={id} fill={MODEL_COLORS[id] ?? "#8C8C8C"} radius={[4, 4, 0, 0]} barSize={20} />
                ))}
              </BarChart>
            </ResponsiveContainer>

            {/* Summary stats */}
            <div className="flex items-center gap-4 flex-wrap text-xs">
              {modelIds.map((id) => {
                const r = results.get(id)!
                return (
                  <Badge key={id} variant="outline" className="font-mono" style={{ borderColor: MODEL_COLORS[id], color: MODEL_COLORS[id] }}>
                    {MODEL_LABELS[id]}: avg {formatScore(r.metrics.score_avg)}% | {Math.round(r.metrics.total_time_ms)}ms
                  </Badge>
                )
              })}
            </div>

            {overlapText && (
              <p className="text-xs text-muted-foreground text-center">{overlapText}</p>
            )}
          </>
        )}

        {results.size === 0 && (
          <p className="text-sm text-muted-foreground text-center py-8">
            Selecciona modelos y presiona "Comparar" para ver resultados lado a lado
          </p>
        )}
      </CardContent>
    </Card>
  )
}
