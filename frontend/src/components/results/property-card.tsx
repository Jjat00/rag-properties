import { useState } from "react"
import { MapPin, Bed, Bath, Ruler, ChevronDown, ChevronUp } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import type { PropertyResult } from "@/types/api"
import { cn, formatPrice, formatScore, scoreBgColor, scoreColor } from "@/lib/utils"
import { motion } from "framer-motion"

interface PropertyCardProps {
  property: PropertyResult
  index: number
}

export function PropertyCard({ property, index }: PropertyCardProps) {
  const [expanded, setExpanded] = useState(false)
  const pct = formatScore(property.score)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.3 }}
    >
      <Card className="bg-card border-border hover:border-primary/30 transition-colors">
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            {/* Score badge */}
            <div
              className={cn(
                "flex-shrink-0 w-12 h-12 rounded-full border flex items-center justify-center font-mono text-sm font-bold",
                scoreBgColor(property.score),
                scoreColor(property.score),
              )}
            >
              {pct}
            </div>

            <div className="flex-1 min-w-0">
              {/* Title */}
              <h3 className="text-sm font-medium text-foreground line-clamp-2 leading-snug">
                {property.title ?? "Sin titulo"}
              </h3>

              {/* Location */}
              <div className="flex items-center gap-1 mt-1 text-xs text-muted-foreground">
                <MapPin className="h-3 w-3 flex-shrink-0" />
                <span className="truncate">
                  {[property.neighborhood, property.city, property.state]
                    .filter(Boolean)
                    .join(", ") || "Ubicacion no disponible"}
                </span>
              </div>

              {/* Stats */}
              <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                {property.bedrooms != null && (
                  <span className="flex items-center gap-1">
                    <Bed className="h-3 w-3" /> {property.bedrooms}
                  </span>
                )}
                {property.bathrooms != null && (
                  <span className="flex items-center gap-1">
                    <Bath className="h-3 w-3" /> {property.bathrooms}
                  </span>
                )}
                {property.surface != null && (
                  <span className="flex items-center gap-1">
                    <Ruler className="h-3 w-3" /> {property.surface}m2
                  </span>
                )}
                {property.property_type && (
                  <span className="text-primary/70">{property.property_type}</span>
                )}
              </div>

              {/* Price */}
              <div className="mt-2 flex items-center justify-between">
                <span className="text-lg font-semibold text-foreground">
                  {formatPrice(property.price, property.currency)}
                </span>
                <button
                  onClick={() => setExpanded(!expanded)}
                  className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors"
                >
                  {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                  {expanded ? "Menos" : "Mas"}
                </button>
              </div>

              {/* Expanded details */}
              {expanded && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  className="mt-3 pt-3 border-t border-border text-xs text-muted-foreground space-y-1"
                >
                  {property.address && <p>Direccion: {property.address}</p>}
                  {property.condition && <p>Condicion: {property.condition}</p>}
                  {property.operation && (
                    <p>Operacion: {property.operation === "sale" ? "Venta" : "Renta"}</p>
                  )}
                  {property.internal_id && <p>ID: {property.internal_id}</p>}
                  {(property.agent_first_name || property.agent_last_name) && (
                    <p>
                      Agente: {property.agent_first_name} {property.agent_last_name}
                      {property.agent_company && ` - ${property.agent_company}`}
                    </p>
                  )}
                  <p className="font-mono text-[10px] text-muted-foreground/50">
                    Score: {property.score.toFixed(4)}
                  </p>
                </motion.div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}
