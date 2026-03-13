import { useState } from "react"
import { MapPin, Bed, Bath, Ruler, Car, ChevronLeft, ChevronRight, ChevronDown, ChevronUp, ImageIcon, Type } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import type { MultimodalPropertyResult } from "@/types/api"
import { cn, formatPrice } from "@/lib/utils"
import { motion } from "framer-motion"

interface MultimodalPropertyCardProps {
  property: MultimodalPropertyResult
  index: number
}

export function MultimodalPropertyCard({ property, index }: MultimodalPropertyCardProps) {
  // Start carousel on the matched image when the best point was an image point
  const matchedIdx = property.matched_point_type === "image" && property.matched_image_url
    ? Math.max(0, (property.pictures ?? []).indexOf(property.matched_image_url))
    : 0
  const [currentImage, setCurrentImage] = useState(matchedIdx)
  const [expanded, setExpanded] = useState(false)
  const pictures = property.pictures ?? []
  const hasPictures = pictures.length > 0
  const isImageMatch = property.matched_point_type === "image"

  const nextImage = () => {
    if (hasPictures) setCurrentImage((prev) => (prev + 1) % pictures.length)
  }
  const prevImage = () => {
    if (hasPictures) setCurrentImage((prev) => (prev - 1 + pictures.length) % pictures.length)
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.3 }}
    >
      <Card className="bg-card border-border hover:border-primary/30 transition-colors overflow-hidden">
        {/* Image carousel */}
        {hasPictures && (
          <div className="relative aspect-[16/10] bg-muted">
            <img
              src={pictures[currentImage]}
              alt={property.title ?? "Propiedad"}
              className="w-full h-full object-cover"
              loading="lazy"
            />
            {pictures.length > 1 && (
              <>
                <button
                  onClick={prevImage}
                  className="absolute left-2 top-1/2 -translate-y-1/2 bg-black/50 hover:bg-black/70 text-white rounded-full p-1 transition-colors"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <button
                  onClick={nextImage}
                  className="absolute right-2 top-1/2 -translate-y-1/2 bg-black/50 hover:bg-black/70 text-white rounded-full p-1 transition-colors"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
                <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex gap-1">
                  {pictures.map((_, i) => (
                    <button
                      key={i}
                      onClick={() => setCurrentImage(i)}
                      className={cn(
                        "w-1.5 h-1.5 rounded-full transition-colors",
                        i === currentImage ? "bg-white" : "bg-white/40"
                      )}
                    />
                  ))}
                </div>
              </>
            )}
            {/* Score + match type badges */}
            <div className="absolute top-2 right-2 flex items-center gap-1">
              {isImageMatch && (
                <div className="bg-purple-600/80 text-white text-[10px] px-1.5 py-0.5 rounded flex items-center gap-1">
                  <ImageIcon className="h-3 w-3" />
                  imagen
                </div>
              )}
              <div className="bg-black/60 text-white text-xs font-mono px-2 py-1 rounded">
                {(property.score * 100).toFixed(1)}%
              </div>
            </div>
          </div>
        )}

        <CardContent className="p-4">
          {/* Title */}
          <h3 className="text-sm font-medium text-foreground line-clamp-2 leading-snug">
            {property.title ?? "Sin titulo"}
          </h3>

          {/* Location */}
          <div className="flex items-center gap-1 mt-1.5 text-xs text-muted-foreground">
            <MapPin className="h-3 w-3 flex-shrink-0" />
            <span className="truncate">
              {[property.suburb, property.city, property.state]
                .filter(Boolean)
                .join(", ") || "Ubicacion no disponible"}
            </span>
          </div>

          {/* Stats */}
          <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
            {property.bedroom != null && (
              <span className="flex items-center gap-1">
                <Bed className="h-3 w-3" /> {property.bedroom}
              </span>
            )}
            {property.bathroom != null && (
              <span className="flex items-center gap-1">
                <Bath className="h-3 w-3" /> {property.bathroom}
              </span>
            )}
            {property.construction_area != null && (
              <span className="flex items-center gap-1">
                <Ruler className="h-3 w-3" /> {property.construction_area}m2
              </span>
            )}
            {property.parking_lot != null && property.parking_lot > 0 && (
              <span className="flex items-center gap-1">
                <Car className="h-3 w-3" /> {property.parking_lot}
              </span>
            )}
            {property.house_type && (
              <span className="text-primary/70">{property.house_type}</span>
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
              className="mt-3 pt-3 border-t border-border text-xs text-muted-foreground space-y-1.5"
            >
              {property.description && (
                <p className="line-clamp-4">{property.description}</p>
              )}
              {property.address && <p>Direccion: {property.address}</p>}
              {property.condition && <p>Condicion: {property.condition}</p>}
              {property.antiquity && <p>Antiguedad: {property.antiquity}</p>}
              {property.operation && <p>Operacion: {property.operation}</p>}
              {property.land_area != null && <p>Terreno: {property.land_area}m2</p>}
              {property.amenities.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-1">
                  {property.amenities.map((a) => (
                    <span key={a} className="px-1.5 py-0.5 rounded bg-primary/10 text-primary text-[10px]">
                      {a}
                    </span>
                  ))}
                </div>
              )}
              {property.exterior_selected.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {property.exterior_selected.map((a) => (
                    <span key={a} className="px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 text-[10px]">
                      {a}
                    </span>
                  ))}
                </div>
              )}
              {property.general_selected.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {property.general_selected.map((a) => (
                    <span key={a} className="px-1.5 py-0.5 rounded bg-green-500/10 text-green-400 text-[10px]">
                      {a}
                    </span>
                  ))}
                </div>
              )}
              <p className="font-mono text-[10px] text-muted-foreground/50">
                Score: {property.score.toFixed(4)}
              </p>
            </motion.div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  )
}
