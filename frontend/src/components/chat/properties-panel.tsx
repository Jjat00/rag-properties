import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { PropertyCard } from "@/components/results/property-card";
import type {
  PropertyResult,
  ParsedQuery,
  DisambiguationInfo,
  SearchMetrics,
} from "@/types/api";
import { Building2, Clock, Filter, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";

interface PropertiesPanelProps {
  results: PropertyResult[];
  filters: ParsedQuery | null;
  disambiguation: DisambiguationInfo[];
  metrics: SearchMetrics | null;
  isSearching: boolean;
}

function FilterChip({ label, value }: { label: string; value: string }) {
  return (
    <Badge
      variant="outline"
      className="text-xs bg-primary/10 text-primary border-primary/20"
    >
      {label}: {value}
    </Badge>
  );
}

export function PropertiesPanel({
  results,
  filters,
  disambiguation,
  metrics,
  isSearching,
}: PropertiesPanelProps) {
  const [debugOpen, setDebugOpen] = useState(false);

  return (
    <div className="flex flex-col h-full border-l border-border bg-background/50">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <div className="flex items-center gap-2">
          <Building2 className="h-4 w-4 text-primary" />
          <span className="text-sm font-medium text-foreground">
            Propiedades
          </span>
          {results.length > 0 && (
            <Badge variant="secondary" className="text-xs">
              {results.length}
            </Badge>
          )}
        </div>
        {isSearching && (
          <span className="text-xs text-muted-foreground animate-pulse">
            Buscando...
          </span>
        )}
      </div>

      <ScrollArea className="flex-1 overflow-y-auto">
        <div className="p-4 space-y-4">
          {/* Active filters */}
          {filters && (
            <div className="flex flex-wrap gap-1.5">
              {filters.cities.map((c) => (
                <FilterChip key={c} label="Ciudad" value={c} />
              ))}
              {filters.state && (
                <FilterChip label="Estado" value={filters.state} />
              )}
              {filters.neighborhoods.map((n) => (
                <FilterChip key={n} label="Colonia" value={n} />
              ))}
              {filters.property_types.map((t) => (
                <FilterChip key={t} label="Tipo" value={t} />
              ))}
              {filters.operation && (
                <FilterChip
                  label="Op"
                  value={filters.operation === "sale" ? "Venta" : "Renta"}
                />
              )}
              {filters.street && (
                <FilterChip label="Calle" value={filters.street} />
              )}
              {(filters.min_bedrooms != null || filters.max_bedrooms != null) && (
                <FilterChip
                  label="Rec"
                  value={
                    filters.min_bedrooms != null && filters.max_bedrooms != null
                      ? `${filters.min_bedrooms}-${filters.max_bedrooms}`
                      : filters.min_bedrooms != null
                        ? `${filters.min_bedrooms}+`
                        : `max ${filters.max_bedrooms}`
                  }
                />
              )}
              {(filters.min_price != null || filters.max_price != null) && (
                <FilterChip
                  label="Precio"
                  value={
                    filters.min_price != null && filters.max_price != null
                      ? `$${(filters.min_price / 1e6).toFixed(1)}M - $${(filters.max_price / 1e6).toFixed(1)}M`
                      : filters.min_price != null
                        ? `desde $${(filters.min_price / 1e6).toFixed(1)}M`
                        : `hasta $${(filters.max_price! / 1e6).toFixed(1)}M`
                  }
                />
              )}
            </div>
          )}

          {/* Disambiguation badges */}
          {disambiguation.length > 0 && (
            <div className="space-y-2">
              {disambiguation.map((d) => (
                <div key={d.field} className="flex flex-wrap gap-1.5">
                  {d.buckets.map((b) => (
                    <Badge
                      key={b.value}
                      variant="outline"
                      className="text-xs bg-amber-500/10 text-amber-400 border-amber-500/20"
                    >
                      {b.value} ({b.count})
                    </Badge>
                  ))}
                </div>
              ))}
            </div>
          )}

          {/* Results */}
          {results.length > 0 ? (
            <div className="space-y-3">
              {results.map((r, i) => (
                <PropertyCard key={r.id ?? i} property={r} index={i} />
              ))}
            </div>
          ) : !isSearching ? (
            <div className="text-center py-12 text-muted-foreground">
              <Filter className="h-8 w-8 mx-auto mb-2 opacity-30" />
              <p className="text-xs">
                Las propiedades apareceran aqui cuando busques
              </p>
            </div>
          ) : null}

          {/* Debug section */}
          {(filters || metrics) && (
            <div className="border-t border-border pt-3">
              <button
                onClick={() => setDebugOpen(!debugOpen)}
                className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                {debugOpen ? (
                  <ChevronUp className="h-3 w-3" />
                ) : (
                  <ChevronDown className="h-3 w-3" />
                )}
                Debug
              </button>

              {debugOpen && (
                <div className="mt-2 space-y-2 text-xs font-mono text-muted-foreground bg-muted/30 rounded-lg p-3">
                  {metrics && (
                    <div className="space-y-1">
                      <div className="flex items-center gap-1 text-foreground/70 font-sans">
                        <Clock className="h-3 w-3" /> Tiempos
                      </div>
                      <p>Parse: {metrics.parse_time_ms.toFixed(0)}ms</p>
                      <p>Embed: {metrics.embed_time_ms.toFixed(0)}ms</p>
                      <p>Search: {metrics.search_time_ms.toFixed(0)}ms</p>
                      <p>Total: {metrics.total_time_ms.toFixed(0)}ms</p>
                      <p>
                        Scores: {metrics.score_min.toFixed(3)} -{" "}
                        {metrics.score_max.toFixed(3)} (avg{" "}
                        {metrics.score_avg.toFixed(3)})
                      </p>
                    </div>
                  )}
                  {filters && (
                    <div>
                      <p className="text-foreground/70 font-sans mb-1">Filtros</p>
                      <pre className="text-[10px] whitespace-pre-wrap break-all">
                        {JSON.stringify(filters, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
