import { Badge } from "@/components/ui/badge"
import type { ParsedQuery } from "@/types/api"
import { formatPrice } from "@/lib/utils"

interface FilterChipsProps {
  filters: ParsedQuery
}

interface Chip {
  label: string
  variant: "location" | "type" | "numeric" | "hint"
}

const VARIANT_CLASSES: Record<Chip["variant"], string> = {
  location: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  type:     "bg-green-500/15 text-green-400 border-green-500/30",
  numeric:  "bg-orange-500/15 text-orange-400 border-orange-500/30",
  hint:     "bg-purple-500/15 text-purple-400 border-purple-500/30",
}

function rangeLabel(min: number | null, max: number | null, unit = "", fmt?: (n: number) => string): string {
  const f = fmt ?? ((n: number) => `${n}${unit}`)
  if (min != null && max != null) return `${f(min)} – ${f(max)}`
  if (min != null) return `${f(min)}+`
  return `máx ${f(max!)}`
}

function buildChips(f: ParsedQuery): Chip[] {
  const chips: Chip[] = []

  // Location — hard filters (azul)
  if (f.cities?.length)  chips.push({ label: `Ciudad: ${f.cities.join(", ")}`,  variant: "location" })
  if (f.state) chips.push({ label: `Estado: ${f.state}`, variant: "location" })

  // Neighborhood and street — soft filters (morado)
  if (f.neighborhoods?.length) chips.push({ label: `Zona: ${f.neighborhoods.join(", ")}`, variant: "hint" })
  if (f.street) chips.push({ label: `Calle: ${f.street}`, variant: "hint" })

  // Type / operation / condition — keyword filters (verde)
  if (f.property_types?.length) chips.push({ label: `Tipo: ${f.property_types.join(", ")}`, variant: "type" })
  if (f.operation) {
    const op = f.operation === "sale" ? "Venta" : f.operation === "rent" ? "Renta" : f.operation
    chips.push({ label: `Operación: ${op}`, variant: "type" })
  }
  if (f.condition) chips.push({ label: `Condición: ${f.condition}`, variant: "type" })
  if (f.currency) chips.push({ label: `Moneda: ${f.currency}`, variant: "type" })

  // Numeric range filters (naranja)
  if (f.min_bedrooms != null || f.max_bedrooms != null)
    chips.push({ label: `Recámaras: ${rangeLabel(f.min_bedrooms, f.max_bedrooms)}`, variant: "numeric" })

  if (f.min_bathrooms != null || f.max_bathrooms != null)
    chips.push({ label: `Baños: ${rangeLabel(f.min_bathrooms, f.max_bathrooms)}`, variant: "numeric" })

  if (f.min_price != null || f.max_price != null) {
    const cur = f.currency ?? undefined
    chips.push({
      label: `Precio: ${rangeLabel(f.min_price, f.max_price, "", (n) => formatPrice(n, cur))}`,
      variant: "numeric",
    })
  }

  if (f.min_surface != null || f.max_surface != null)
    chips.push({ label: `Superficie: ${rangeLabel(f.min_surface, f.max_surface, "m²")}`, variant: "numeric" })

  if (f.min_roofed_surface != null || f.max_roofed_surface != null)
    chips.push({ label: `Techada: ${rangeLabel(f.min_roofed_surface, f.max_roofed_surface, "m²")}`, variant: "numeric" })

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
