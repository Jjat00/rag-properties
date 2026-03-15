import type { MultimodalPropertyResult } from "@/types/api"
import { MultimodalPropertyCard } from "./multimodal-property-card"

interface MultimodalResultsGridProps {
  results: MultimodalPropertyResult[]
}

export function MultimodalResultsGrid({ results }: MultimodalResultsGridProps) {
  if (results.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        No se encontraron propiedades para esta busqueda.
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {results.map((property, i) => (
        <MultimodalPropertyCard key={property.id ?? i} property={property} index={i} />
      ))}
    </div>
  )
}
