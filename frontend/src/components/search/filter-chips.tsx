import { Badge } from "@/components/ui/badge"
import type { DisambiguationInfo, ParsedQuery, PropertyResult } from "@/types/api"
import { formatPrice } from "@/lib/utils"

interface FilterChipsProps {
  filters: ParsedQuery
  results?: PropertyResult[]
  disambiguation?: DisambiguationInfo[]
  activeDisambig?: Record<string, string>
  onDisambigClick?: (field: string, value: string) => void
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

const FIELD_LABELS: Record<string, string> = {
  property_type: "Tipo",
  city: "Ciudad",
}

// Maps DisambiguationInfo field name to PropertyResult key
const FIELD_TO_RESULT_KEY: Record<string, keyof PropertyResult> = {
  property_type: "property_type",
  city: "city",
}

function countByValue(results: PropertyResult[], field: keyof PropertyResult): Record<string, number> {
  const counts: Record<string, number> = {}
  for (const r of results) {
    const val = r[field]
    if (val != null) {
      const key = String(val)
      counts[key] = (counts[key] ?? 0) + 1
    }
  }
  return counts
}

function rangeLabel(min: number | null, max: number | null, unit = "", fmt?: (n: number) => string): string {
  const f = fmt ?? ((n: number) => `${n}${unit}`)
  if (min != null && max != null) return `${f(min)} – ${f(max)}`
  if (min != null) return `${f(min)}+`
  return `máx ${f(max!)}`
}

function buildChips(f: ParsedQuery): Chip[] {
  const chips: Chip[] = []

  if (f.cities?.length)  chips.push({ label: `Ciudad: ${f.cities.join(", ")}`,  variant: "location" })
  if (f.state) chips.push({ label: `Estado: ${f.state}`, variant: "location" })

  if (f.neighborhoods?.length) chips.push({ label: `Zona: ${f.neighborhoods.join(", ")}`, variant: "hint" })
  if (f.street) chips.push({ label: `Calle: ${f.street}`, variant: "hint" })

  if (f.property_types?.length) chips.push({ label: `Tipo: ${f.property_types.join(", ")}`, variant: "type" })
  if (f.operation) {
    const op = f.operation === "sale" ? "Venta" : f.operation === "rent" ? "Renta" : f.operation
    chips.push({ label: `Operación: ${op}`, variant: "type" })
  }
  if (f.condition) chips.push({ label: `Condición: ${f.condition}`, variant: "type" })
  if (f.currency) chips.push({ label: `Moneda: ${f.currency}`, variant: "type" })

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

export function FilterChips({
  filters,
  results = [],
  disambiguation,
  activeDisambig = {},
  onDisambigClick,
}: FilterChipsProps) {
  const chips = buildChips(filters)
  const hasActiveFilter = Object.values(activeDisambig).some(Boolean)

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
    <div className="space-y-2">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs text-muted-foreground">Filtros detectados:</span>
        {chips.map((chip) => (
          <Badge key={chip.label} variant="outline" className={VARIANT_CLASSES[chip.variant]}>
            {chip.label}
          </Badge>
        ))}
      </div>

      {/* Disambiguation breakdown — counts from current results, clickable */}
      {disambiguation && disambiguation.length > 0 && (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-muted-foreground">Desglose:</span>
          {disambiguation.map((info) => {
            const resultKey = FIELD_TO_RESULT_KEY[info.field]
            const counts = resultKey ? countByValue(results, resultKey) : {}

            return info.buckets
              .map((bucket) => {
                const count = counts[bucket.value] ?? 0
                if (count === 0) return null
                const isActive = activeDisambig[info.field] === bucket.value
                return (
                  <Badge
                    key={`${info.field}-${bucket.value}`}
                    variant="outline"
                    onClick={() => onDisambigClick?.(info.field, bucket.value)}
                    className={
                      isActive
                        ? "bg-amber-500/40 text-amber-300 border-amber-400/60 cursor-pointer"
                        : "bg-amber-500/15 text-amber-400 border-amber-500/30 cursor-pointer hover:bg-amber-500/25"
                    }
                  >
                    {FIELD_LABELS[info.field] ?? info.field}: {bucket.value} ({count})
                  </Badge>
                )
              })
              .filter(Boolean)
          })}
          {hasActiveFilter && (
            <button
              onClick={() => {
                for (const [field, value] of Object.entries(activeDisambig)) {
                  if (value) onDisambigClick?.(field, value)
                }
              }}
              className="text-xs text-muted-foreground hover:text-foreground underline underline-offset-2"
            >
              ver todos
            </button>
          )}
        </div>
      )}
    </div>
  )
}
