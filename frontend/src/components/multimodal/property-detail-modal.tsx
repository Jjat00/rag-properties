import { useState } from "react"
import {
  MapPin, Bed, Bath, Ruler, Car, Calendar, Shield,
  X, ChevronLeft, ChevronRight, Maximize2,
} from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import type { MultimodalPropertyResult } from "@/types/api"
import { cn, formatPrice } from "@/lib/utils"

interface PropertyDetailModalProps {
  property: MultimodalPropertyResult
  open: boolean
  onOpenChange: (open: boolean) => void
}

function ImageLightbox({
  src,
  alt,
  onClose,
  onPrev,
  onNext,
  hasPrev,
  hasNext,
}: {
  src: string
  alt: string
  onClose: () => void
  onPrev: () => void
  onNext: () => void
  hasPrev: boolean
  hasNext: boolean
}) {
  return (
    <div className="fixed inset-0 z-[100] bg-black/90 flex items-center justify-center" onClick={onClose}>
      <button
        onClick={onClose}
        className="absolute top-4 right-4 text-white/70 hover:text-white p-2 rounded-full bg-white/10 hover:bg-white/20 transition-colors z-10"
      >
        <X className="h-5 w-5" />
      </button>
      {hasPrev && (
        <button
          onClick={(e) => { e.stopPropagation(); onPrev() }}
          className="absolute left-4 top-1/2 -translate-y-1/2 text-white/70 hover:text-white p-2 rounded-full bg-white/10 hover:bg-white/20 transition-colors z-10"
        >
          <ChevronLeft className="h-6 w-6" />
        </button>
      )}
      {hasNext && (
        <button
          onClick={(e) => { e.stopPropagation(); onNext() }}
          className="absolute right-4 top-1/2 -translate-y-1/2 text-white/70 hover:text-white p-2 rounded-full bg-white/10 hover:bg-white/20 transition-colors z-10"
        >
          <ChevronRight className="h-6 w-6" />
        </button>
      )}
      <img
        src={src}
        alt={alt}
        className="max-h-[90vh] max-w-[90vw] object-contain rounded-lg"
        onClick={(e) => e.stopPropagation()}
      />
    </div>
  )
}

export function PropertyDetailModal({ property, open, onOpenChange }: PropertyDetailModalProps) {
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null)
  const pictures = property.pictures ?? []

  const openLightbox = (i: number) => setLightboxIndex(i)
  const closeLightbox = () => setLightboxIndex(null)

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-4xl max-h-[90vh] p-0 gap-0 overflow-hidden bg-card border-border">
          <DialogTitle className="sr-only">{property.title ?? "Detalle de propiedad"}</DialogTitle>

          <ScrollArea className="max-h-[90vh]">
            <div className="p-6 space-y-6">
              {/* Header */}
              <div className="space-y-2">
                <div className="flex items-start justify-between gap-4">
                  <h2 className="text-xl font-semibold text-foreground leading-tight">
                    {property.title ?? "Sin titulo"}
                  </h2>
                  <Badge variant="outline" className="bg-primary/10 text-primary border-primary/30 shrink-0 font-mono">
                    {(property.score * 100).toFixed(1)}%
                  </Badge>
                </div>
                <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                  <MapPin className="h-4 w-4 flex-shrink-0" />
                  {[property.address, property.suburb, property.city, property.state]
                    .filter(Boolean)
                    .join(", ") || "Ubicacion no disponible"}
                </div>
              </div>

              {/* Price + key stats */}
              <div className="flex flex-wrap items-center gap-4">
                <span className="text-2xl font-bold text-foreground">
                  {formatPrice(property.price, property.currency)}
                </span>
                {property.operation && (
                  <Badge variant="outline" className="bg-green-500/10 text-green-400 border-green-500/30">
                    {property.operation}
                  </Badge>
                )}
                {property.house_type && (
                  <Badge variant="outline" className="bg-blue-500/10 text-blue-400 border-blue-500/30">
                    {property.house_type}
                  </Badge>
                )}
              </div>

              {/* Image gallery */}
              {pictures.length > 0 && (
                <div className="space-y-2">
                  {/* Main image */}
                  <div
                    className="relative aspect-[16/9] rounded-lg overflow-hidden bg-muted cursor-pointer group"
                    onClick={() => openLightbox(0)}
                  >
                    <img
                      src={pictures[0]}
                      alt={property.title ?? "Propiedad"}
                      className="absolute inset-0 w-full h-full object-cover"
                    />
                    <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center">
                      <Maximize2 className="h-8 w-8 text-white opacity-0 group-hover:opacity-70 transition-opacity" />
                    </div>
                  </div>

                  {/* Thumbnail grid */}
                  {pictures.length > 1 && (
                    <div className="grid grid-cols-4 sm:grid-cols-5 md:grid-cols-6 gap-2">
                      {pictures.slice(1).map((url, i) => (
                        <div
                          key={i}
                          className="relative aspect-square rounded-md overflow-hidden bg-muted cursor-pointer group"
                          onClick={() => openLightbox(i + 1)}
                        >
                          <img
                            src={url}
                            alt={`Foto ${i + 2}`}
                            className="absolute inset-0 w-full h-full object-cover"
                            loading="lazy"
                          />
                          <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors" />
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Stats grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                {property.bedroom != null && (
                  <StatItem icon={Bed} label="Recamaras" value={String(property.bedroom)} />
                )}
                {property.bathroom != null && (
                  <StatItem icon={Bath} label="Banos" value={String(property.bathroom)} />
                )}
                {property.half_bathroom != null && property.half_bathroom > 0 && (
                  <StatItem icon={Bath} label="Medio bano" value={String(property.half_bathroom)} />
                )}
                {property.construction_area != null && (
                  <StatItem icon={Ruler} label="Construccion" value={`${property.construction_area} m2`} />
                )}
                {property.land_area != null && (
                  <StatItem icon={Ruler} label="Terreno" value={`${property.land_area} m2`} />
                )}
                {property.parking_lot != null && property.parking_lot > 0 && (
                  <StatItem icon={Car} label="Estacionamiento" value={String(property.parking_lot)} />
                )}
                {property.condition && (
                  <StatItem icon={Shield} label="Condicion" value={property.condition} />
                )}
                {property.antiquity && (
                  <StatItem icon={Calendar} label="Antiguedad" value={property.antiquity} />
                )}
              </div>

              {/* Description */}
              {property.description && (
                <div className="space-y-1.5">
                  <h3 className="text-sm font-medium text-foreground">Descripcion</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed whitespace-pre-line">
                    {property.description}
                  </p>
                </div>
              )}

              {/* Amenities, exterior, general */}
              {property.amenities.length > 0 && (
                <TagSection title="Amenidades" tags={property.amenities} color="bg-primary/10 text-primary" />
              )}
              {property.exterior_selected.length > 0 && (
                <TagSection title="Exterior" tags={property.exterior_selected} color="bg-blue-500/10 text-blue-400" />
              )}
              {property.general_selected.length > 0 && (
                <TagSection title="General" tags={property.general_selected} color="bg-green-500/10 text-green-400" />
              )}
              {property.near_places.length > 0 && (
                <TagSection title="Cerca de" tags={property.near_places} color="bg-orange-500/10 text-orange-400" />
              )}

              {/* Ad copy */}
              {property.ad_copy && (
                <div className="space-y-1.5">
                  <h3 className="text-sm font-medium text-foreground">Texto del anuncio</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed whitespace-pre-line">
                    {property.ad_copy}
                  </p>
                </div>
              )}

              {/* Footer meta */}
              <div className="pt-3 border-t border-border flex items-center gap-4 text-xs text-muted-foreground/60">
                <span className="font-mono">Score: {property.score.toFixed(4)}</span>
                {property.firebase_id && <span className="font-mono">ID: {property.firebase_id}</span>}
                {pictures.length > 0 && <span>{pictures.length} fotos</span>}
              </div>
            </div>
          </ScrollArea>
        </DialogContent>
      </Dialog>

      {/* Lightbox */}
      {lightboxIndex !== null && pictures[lightboxIndex] && (
        <ImageLightbox
          src={pictures[lightboxIndex]}
          alt={`Foto ${lightboxIndex + 1}`}
          onClose={closeLightbox}
          onPrev={() => setLightboxIndex((prev) => Math.max(0, (prev ?? 0) - 1))}
          onNext={() => setLightboxIndex((prev) => Math.min(pictures.length - 1, (prev ?? 0) + 1))}
          hasPrev={lightboxIndex > 0}
          hasNext={lightboxIndex < pictures.length - 1}
        />
      )}
    </>
  )
}

function StatItem({ icon: Icon, label, value }: { icon: typeof Bed; label: string; value: string }) {
  return (
    <div className="flex items-center gap-2.5 p-2.5 rounded-lg bg-muted/50 border border-border/50">
      <Icon className="h-4 w-4 text-muted-foreground flex-shrink-0" />
      <div className="min-w-0">
        <p className="text-[10px] text-muted-foreground uppercase tracking-wide">{label}</p>
        <p className="text-sm font-medium text-foreground truncate">{value}</p>
      </div>
    </div>
  )
}

function TagSection({ title, tags, color }: { title: string; tags: string[]; color: string }) {
  return (
    <div className="space-y-1.5">
      <h3 className="text-sm font-medium text-foreground">{title}</h3>
      <div className="flex flex-wrap gap-1.5">
        {tags.map((tag) => (
          <span key={tag} className={cn("px-2 py-0.5 rounded-md text-xs", color)}>
            {tag}
          </span>
        ))}
      </div>
    </div>
  )
}
