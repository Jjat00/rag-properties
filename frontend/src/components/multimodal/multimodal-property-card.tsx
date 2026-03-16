import { useState } from "react"
import { MapPin, Bed, Bath, Ruler, Car, ChevronLeft, ChevronRight, Images } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import type { MultimodalPropertyResult } from "@/types/api"
import { cn, formatPrice } from "@/lib/utils"
import { motion } from "framer-motion"
import { PropertyDetailModal } from "./property-detail-modal"

interface MultimodalPropertyCardProps {
  property: MultimodalPropertyResult
  index: number
}

export function MultimodalPropertyCard({ property, index }: MultimodalPropertyCardProps) {
  const [currentImage, setCurrentImage] = useState(0)
  const [detailOpen, setDetailOpen] = useState(false)
  const pictures = property.pictures ?? []
  const hasPictures = pictures.length > 0

  const nextImage = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (hasPictures) setCurrentImage((prev) => (prev + 1) % pictures.length)
  }
  const prevImage = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (hasPictures) setCurrentImage((prev) => (prev - 1 + pictures.length) % pictures.length)
  }

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: index * 0.05, duration: 0.3 }}
      >
        <Card
          className="bg-card border-border hover:border-primary/30 transition-colors overflow-hidden flex flex-col cursor-pointer"
          onClick={() => setDetailOpen(true)}
        >
          {/* Image — fixed aspect ratio */}
          <div className="relative aspect-[16/10] bg-muted flex-shrink-0">
            {hasPictures ? (
              <img
                src={pictures[currentImage]}
                alt={property.title ?? "Propiedad"}
                className="absolute inset-0 w-full h-full object-cover"
                loading="lazy"
              />
            ) : (
              <div className="absolute inset-0 flex items-center justify-center text-muted-foreground/30">
                <Images className="h-12 w-12" />
              </div>
            )}
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
                  {pictures.slice(0, 8).map((_, i) => (
                    <button
                      key={i}
                      onClick={(e) => { e.stopPropagation(); setCurrentImage(i) }}
                      className={cn(
                        "w-1.5 h-1.5 rounded-full transition-colors",
                        i === currentImage ? "bg-white" : "bg-white/40"
                      )}
                    />
                  ))}
                  {pictures.length > 8 && (
                    <span className="text-white/60 text-[9px] ml-0.5">+{pictures.length - 8}</span>
                  )}
                </div>
              </>
            )}
            {/* Score badge */}
            <div className="absolute top-2 right-2">
              <div className="bg-black/60 text-white text-xs font-mono px-2 py-1 rounded">
                {(property.score * 100).toFixed(1)}%
              </div>
            </div>
            {/* Photo count */}
            {pictures.length > 1 && (
              <div className="absolute top-2 left-2">
                <div className="bg-black/60 text-white text-[10px] px-1.5 py-0.5 rounded">
                  {pictures.length} fotos
                </div>
              </div>
            )}
          </div>

          <CardContent className="p-4 flex flex-col flex-1">
            {/* Title */}
            <h3 className="text-sm font-medium text-foreground line-clamp-2 leading-snug min-h-[2.5rem]">
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
            </div>

            {/* Price + type */}
            <div className="mt-auto pt-2 flex items-center justify-between">
              <span className="text-lg font-semibold text-foreground">
                {formatPrice(property.price, property.currency)}
              </span>
              {property.house_type && (
                <span className="text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                  {property.house_type}
                </span>
              )}
            </div>
          </CardContent>
        </Card>
      </motion.div>

      <PropertyDetailModal
        property={property}
        open={detailOpen}
        onOpenChange={setDetailOpen}
      />
    </>
  )
}
