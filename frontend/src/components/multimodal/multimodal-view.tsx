import { useState } from "react"
import { RotateCcw, Clock, Zap, Database, ImageIcon, Type, Filter } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { MultimodalSearchBar } from "./multimodal-search-bar"
import { MultimodalResultsGrid } from "./multimodal-results-grid"
import { LoadingSkeleton } from "@/components/results/loading-skeleton"
import { useMultimodalSearch } from "@/hooks/use-multimodal-search"
import type { ParsedQuery } from "@/types/api"
import { formatPrice } from "@/lib/utils"

function rangeLabel(min: number | null, max: number | null, unit = "", fmt?: (n: number) => string): string {
  const f = fmt ?? ((n: number) => `${n}${unit}`)
  if (min != null && max != null) return `${f(min)} – ${f(max)}`
  if (min != null) return `${f(min)}+`
  return `max ${f(max!)}`
}

function MultimodalFilterChips({ filters }: { filters: ParsedQuery }) {
  const chips: { label: string; color: string }[] = []

  if (filters.cities?.length)
    chips.push({ label: `Ciudad: ${filters.cities.join(", ")}`, color: "bg-blue-500/15 text-blue-400 border-blue-500/30" })
  if (filters.state)
    chips.push({ label: `Estado: ${filters.state}`, color: "bg-blue-500/15 text-blue-400 border-blue-500/30" })
  if (filters.neighborhoods?.length)
    chips.push({ label: `Zona: ${filters.neighborhoods.join(", ")}`, color: "bg-purple-500/15 text-purple-400 border-purple-500/30" })
  if (filters.street)
    chips.push({ label: `Calle: ${filters.street}`, color: "bg-purple-500/15 text-purple-400 border-purple-500/30" })
  if (filters.property_types?.length)
    chips.push({ label: `Tipo: ${filters.property_types.join(", ")}`, color: "bg-green-500/15 text-green-400 border-green-500/30" })
  if (filters.operation) {
    const op = filters.operation === "sale" ? "Venta" : filters.operation === "rent" ? "Renta" : filters.operation
    chips.push({ label: `Operacion: ${op}`, color: "bg-green-500/15 text-green-400 border-green-500/30" })
  }
  if (filters.condition)
    chips.push({ label: `Condicion: ${filters.condition}`, color: "bg-green-500/15 text-green-400 border-green-500/30" })
  if (filters.currency)
    chips.push({ label: `Moneda: ${filters.currency}`, color: "bg-green-500/15 text-green-400 border-green-500/30" })
  if (filters.min_bedrooms != null || filters.max_bedrooms != null)
    chips.push({ label: `Recamaras: ${rangeLabel(filters.min_bedrooms, filters.max_bedrooms)}`, color: "bg-orange-500/15 text-orange-400 border-orange-500/30" })
  if (filters.min_bathrooms != null || filters.max_bathrooms != null)
    chips.push({ label: `Banos: ${rangeLabel(filters.min_bathrooms, filters.max_bathrooms)}`, color: "bg-orange-500/15 text-orange-400 border-orange-500/30" })
  if (filters.min_price != null || filters.max_price != null) {
    const cur = filters.currency ?? undefined
    chips.push({
      label: `Precio: ${rangeLabel(filters.min_price, filters.max_price, "", (n) => formatPrice(n, cur))}`,
      color: "bg-orange-500/15 text-orange-400 border-orange-500/30",
    })
  }
  if (filters.min_surface != null || filters.max_surface != null)
    chips.push({ label: `Superficie: ${rangeLabel(filters.min_surface, filters.max_surface, "m2")}`, color: "bg-orange-500/15 text-orange-400 border-orange-500/30" })

  if (chips.length === 0) {
    return (
      <div className="flex items-center gap-2">
        <Badge variant="outline" className="bg-muted/50 text-muted-foreground border-border">
          Busqueda puramente semantica
        </Badge>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <Filter className="h-3 w-3 text-muted-foreground" />
      <span className="text-xs text-muted-foreground">Filtros:</span>
      {chips.map((chip) => (
        <Badge key={chip.label} variant="outline" className={chip.color}>
          {chip.label}
        </Badge>
      ))}
    </div>
  )
}

export function MultimodalView() {
  const [query, setQuery] = useState("")
  const [imageFile, setImageFile] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const { status, data, error, search, searchImage, reset } = useMultimodalSearch()

  const handleSearch = (q: string) => {
    clearImage()
    search({ query: q })
  }

  const handleImageSearch = (file: File) => {
    setImageFile(file)
    const url = URL.createObjectURL(file)
    setImagePreview(url)
    searchImage(file)
  }

  const clearImage = () => {
    if (imagePreview) URL.revokeObjectURL(imagePreview)
    setImageFile(null)
    setImagePreview(null)
  }

  const handleReset = () => {
    setQuery("")
    clearImage()
    reset()
  }

  return (
    <main className="max-w-7xl mx-auto px-4 py-8 space-y-6">
      {/* Search */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-start gap-3">
        <div className="flex-1">
          <MultimodalSearchBar
            value={query}
            onChange={setQuery}
            onSearch={handleSearch}
            onImageSearch={handleImageSearch}
            imageFile={imageFile}
            imagePreview={imagePreview}
            onClearImage={clearImage}
            loading={status === "loading"}
          />
        </div>
        {(status === "success" || status === "error") && (
          <Button
            variant="outline"
            onClick={handleReset}
            className="h-12 shrink-0 gap-2 border-border text-muted-foreground hover:text-foreground"
          >
            <RotateCcw className="h-4 w-4" />
            Nueva busqueda
          </Button>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
          Error: {error}
        </div>
      )}

      {/* Loading */}
      {status === "loading" && <LoadingSkeleton />}

      {/* Filter chips */}
      {data?.parsed_filters && data.search_mode === "text" && (
        <MultimodalFilterChips filters={data.parsed_filters} />
      )}

      {/* Metrics */}
      {data && (
        <div className="flex items-center gap-4 text-xs text-muted-foreground flex-wrap">
          <span className="flex items-center gap-1">
            {data.search_mode === "image" ? (
              <ImageIcon className="h-3 w-3" />
            ) : (
              <Type className="h-3 w-3" />
            )}
            {data.search_mode === "image" ? "Busqueda por imagen" : "Busqueda por texto"}
          </span>
          <span className="flex items-center gap-1">
            <Database className="h-3 w-3" />
            {data.results.length} de {data.total} resultados
          </span>
          {data.metrics.parse_time_ms > 0 && (
            <span className="flex items-center gap-1">
              Parse: {data.metrics.parse_time_ms.toFixed(0)}ms
            </span>
          )}
          <span className="flex items-center gap-1">
            <Zap className="h-3 w-3" />
            Embed: {data.metrics.embed_time_ms.toFixed(0)}ms
          </span>
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            Total: {data.metrics.total_time_ms.toFixed(0)}ms
          </span>
          {data.metrics.score_avg > 0 && (
            <span>
              Score: {(data.metrics.score_avg * 100).toFixed(1)}% avg
            </span>
          )}
        </div>
      )}

      {/* Results */}
      {data && <MultimodalResultsGrid results={data.results} />}

      {/* Idle state */}
      {status === "idle" && (
        <div className="text-center py-16 space-y-4">
          <div className="text-4xl">🏠</div>
          <h2 className="text-lg font-medium text-foreground">Busqueda Multimodal</h2>
          <p className="text-sm text-muted-foreground max-w-md mx-auto">
            Busca propiedades por texto o sube una imagen. El query se parsea con IA
            para extraer filtros (ciudad, tipo, precio, etc.) y busca semanticamente
            contra embeddings fusionados (texto + imagenes) de Gemini Embedding 2.
          </p>
          <div className="flex flex-wrap justify-center gap-2 mt-4">
            {[
              "departamento con alberca en Guadalajara",
              "casa en venta en Puebla menos de 3 millones",
              "terreno en Tulum",
            ].map((suggestion) => (
              <button
                key={suggestion}
                onClick={() => {
                  setQuery(suggestion)
                  handleSearch(suggestion)
                }}
                className="px-3 py-1.5 rounded-full border border-border text-xs text-muted-foreground hover:text-foreground hover:border-primary/30 transition-colors"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      )}
    </main>
  )
}
