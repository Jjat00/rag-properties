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
import { useState, useMemo, useEffect } from "react";

interface PropertiesPanelProps {
  results: PropertyResult[];
  totalResults: number;
  filters: ParsedQuery | null;
  disambiguation: DisambiguationInfo[];
  stateResults: Record<string, PropertyResult[]>;
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
  totalResults,
  filters,
  disambiguation,
  stateResults,
  metrics,
  isSearching,
}: PropertiesPanelProps) {
  const [debugOpen, setDebugOpen] = useState(false);
  const [selectedState, setSelectedState] = useState<string | null>(null);

  // Reset state filter when new results come in (new search)
  useEffect(() => {
    setSelectedState(null);
  }, [results]);

  const stateDisambiguation = disambiguation.find((d) => d.field === "state");
  const hasStateResults = stateDisambiguation && Object.keys(stateResults).length > 0;

  // Sum of all state bucket counts as fallback for total
  const stateBucketsTotal = stateDisambiguation
    ? stateDisambiguation.buckets.reduce((sum, b) => sum + b.count, 0)
    : 0;
  const effectiveTotal = totalResults || stateBucketsTotal;

  // Determine which results to display
  const displayResults = useMemo(() => {
    if (selectedState && stateResults[selectedState]) {
      return stateResults[selectedState];
    }
    return results;
  }, [results, stateResults, selectedState]);

  const displayTotal = useMemo(() => {
    if (selectedState && stateDisambiguation) {
      const bucket = stateDisambiguation.buckets.find((b) => b.value === selectedState);
      return bucket?.count ?? displayResults.length;
    }
    return effectiveTotal;
  }, [effectiveTotal, selectedState, stateDisambiguation, displayResults.length]);

  return (
    <div className="flex flex-col h-full border-l border-border bg-background/50">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <div className="flex items-center gap-2">
          <Building2 className="h-4 w-4 text-primary" />
          <span className="text-sm font-medium text-foreground">
            Propiedades
          </span>
          {displayResults.length > 0 && (
            <Badge variant="secondary" className="text-xs">
              {displayTotal > displayResults.length
                ? `${displayResults.length} de ${displayTotal}`
                : displayResults.length}
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

          {/* Disambiguation badges — clickable for state */}
          {disambiguation.length > 0 && (
            <div className="space-y-2">
              {disambiguation.map((d) => (
                <div key={d.field} className="flex flex-wrap gap-1.5">
                  {d.field === "state" && hasStateResults && (
                    <Badge
                      variant="outline"
                      className={`text-xs cursor-pointer transition-colors ${
                        selectedState === null
                          ? "bg-amber-500/20 text-amber-300 border-amber-500/40"
                          : "bg-amber-500/10 text-amber-400 border-amber-500/20 hover:bg-amber-500/15"
                      }`}
                      onClick={() => setSelectedState(null)}
                    >
                      Todas ({effectiveTotal})
                    </Badge>
                  )}
                  {d.buckets.map((b) => (
                    <Badge
                      key={b.value}
                      variant="outline"
                      className={`text-xs ${
                        d.field === "state" && hasStateResults
                          ? `cursor-pointer transition-colors ${
                              selectedState === b.value
                                ? "bg-amber-500/20 text-amber-300 border-amber-500/40"
                                : "bg-amber-500/10 text-amber-400 border-amber-500/20 hover:bg-amber-500/15"
                            }`
                          : "bg-amber-500/10 text-amber-400 border-amber-500/20"
                      }`}
                      onClick={
                        d.field === "state" && hasStateResults
                          ? () => setSelectedState(selectedState === b.value ? null : b.value)
                          : undefined
                      }
                    >
                      {b.value} ({b.count})
                    </Badge>
                  ))}
                </div>
              ))}
            </div>
          )}

          {/* Results */}
          {displayResults.length > 0 ? (
            <div className="space-y-3">
              {displayResults.map((r, i) => (
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
