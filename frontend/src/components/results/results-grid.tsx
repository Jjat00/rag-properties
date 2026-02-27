import type { PropertyResult } from "@/types/api"
import { PropertyCard } from "./property-card"

interface ResultsGridProps {
  results: PropertyResult[]
}

export function ResultsGrid({ results }: ResultsGridProps) {
  if (results.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        No se encontraron propiedades para esta busqueda.
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {results.map((property, i) => (
        <PropertyCard key={property.id ?? i} property={property} index={i} />
      ))}
    </div>
  )
}
