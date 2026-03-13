import { useState } from "react"
import { RotateCcw, Clock, Zap, Database, ImageIcon, Type } from "lucide-react"
import { Button } from "@/components/ui/button"
import { MultimodalSearchBar } from "./multimodal-search-bar"
import { MultimodalResultsGrid } from "./multimodal-results-grid"
import { LoadingSkeleton } from "@/components/results/loading-skeleton"
import { useMultimodalSearch } from "@/hooks/use-multimodal-search"

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

      {/* Metrics */}
      {data && (
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
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
          <span className="flex items-center gap-1">
            <Zap className="h-3 w-3" />
            Embed: {data.metrics.embed_time_ms.toFixed(0)}ms
          </span>
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            Total: {data.metrics.total_time_ms.toFixed(0)}ms
          </span>
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
            Busca propiedades por texto o sube una imagen. Cada propiedad tiene un embedding
            fusionado (texto + imagenes) en el mismo espacio vectorial de Gemini Embedding 2.
          </p>
          <div className="flex flex-wrap justify-center gap-2 mt-4">
            {[
              "departamento con alberca en Guadalajara",
              "casa moderna con roof garden",
              "terreno en zona residencial",
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
