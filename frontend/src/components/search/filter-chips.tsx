import { Badge } from "@/components/ui/badge"
import type { ParsedQuery } from "@/types/api"
import { formatPrice } from "@/lib/utils"

interface FilterChipsProps {
  filters: ParsedQuery
}

interface Chip {
  label: string
  variant: "location" | "type" | "numeric"
}

const VARIANT_CLASSES: Record<Chip["variant"], string> = {
  location: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  type: "bg-green-500/15 text-green-400 border-green-500/30",
  numeric: "bg-orange-500/15 text-orange-400 border-orange-500/30",
}

function buildChips(f: ParsedQuery): Chip[] {
  const chips: Chip[] = []

  if (f.city) chips.push({ label: `Ciudad: ${f.city}`, variant: "location" })
  if (f.state) chips.push({ label: `Estado: ${f.state}`, variant: "location" })
  if (f.neighborhood) chips.push({ label: `Zona: ${f.neighborhood}`, variant: "location" })

  if (f.property_type) chips.push({ label: `Tipo: ${f.property_type}`, variant: "type" })
  if (f.operation) {
    const op = f.operation === "sale" ? "Venta" : f.operation === "rent" ? "Renta" : f.operation
    chips.push({ label: `Operacion: ${op}`, variant: "type" })
  }
  if (f.condition) chips.push({ label: `Condicion: ${f.condition}`, variant: "type" })

  if (f.min_bedrooms != null || f.max_bedrooms != null) {
    const label = f.min_bedrooms != null && f.max_bedrooms != null
      ? `Recamaras: ${f.min_bedrooms}-${f.max_bedrooms}`
      : f.min_bedrooms != null
        ? `Recamaras: ${f.min_bedrooms}+`
        : `Recamaras: max ${f.max_bedrooms}`
    chips.push({ label, variant: "numeric" })
  }

  if (f.min_bathrooms != null || f.max_bathrooms != null) {
    const label = f.min_bathrooms != null && f.max_bathrooms != null
      ? `Banos: ${f.min_bathrooms}-${f.max_bathrooms}`
      : f.min_bathrooms != null
        ? `Banos: ${f.min_bathrooms}+`
        : `Banos: max ${f.max_bathrooms}`
    chips.push({ label, variant: "numeric" })
  }

  if (f.min_price != null || f.max_price != null) {
    const cur = f.currency
    const label = f.min_price != null && f.max_price != null
      ? `Precio: ${formatPrice(f.min_price, cur)} - ${formatPrice(f.max_price, cur)}`
      : f.min_price != null
        ? `Precio: desde ${formatPrice(f.min_price, cur)}`
        : `Precio: hasta ${formatPrice(f.max_price, cur)}`
    chips.push({ label, variant: "numeric" })
  }

  if (f.min_surface != null || f.max_surface != null) {
    const label = f.min_surface != null && f.max_surface != null
      ? `Superficie: ${f.min_surface}-${f.max_surface}m2`
      : f.min_surface != null
        ? `Superficie: ${f.min_surface}m2+`
        : `Superficie: max ${f.max_surface}m2`
    chips.push({ label, variant: "numeric" })
  }

  return chips
}

export function FilterChips({ filters }: FilterChipsProps) {
  const chips = buildChips(filters)

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
      <span className="text-xs text-muted-foreground">Filtros detectados:</span>
      {chips.map((chip) => (
        <Badge
          key={chip.label}
          variant="outline"
          className={VARIANT_CLASSES[chip.variant]}
        >
          {chip.label}
        </Badge>
      ))}
    </div>
  )
}
