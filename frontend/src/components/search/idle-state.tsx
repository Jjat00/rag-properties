import { Building2, Cpu, Zap, Lightbulb, Sparkles, SlidersHorizontal } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"

const SUGGESTIONS = [
  "casa de 4 habitaciones con 2 baños en Cancún menos de 5 millones",
  "departamento en CDMX menos de 3 MDP con 2 recámaras",
  "terreno comercial en Monterrey",
  "casa en condominio con alberca en Playa del Carmen",
  "oficina en renta en Guadalajara",
]

const FEATURES = [
  {
    icon: Sparkles,
    title: "Búsqueda semántica",
    description: "Dense vectors + cosine similarity. Entiende sinónimos, contexto y variantes ortográficas.",
  },
  {
    icon: SlidersHorizontal,
    title: "Filtros automáticos",
    description: "LLM extrae ciudad, recámaras y rango de precio directamente de tu lenguaje natural.",
  },
]

interface IdleStateProps {
  modelCount: number
  onSuggestion: (query: string) => void
}

export function IdleState({ modelCount, onSuggestion }: IdleStateProps) {
  return (
    <div className="space-y-3 animate-in fade-in duration-500">
      {/* Stats row */}
      <div className="grid grid-cols-3 gap-3">
        <Card className="bg-card border-border">
          <CardContent className="p-4 flex items-center gap-3">
            <div className="flex-shrink-0 w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center">
              <Building2 className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-xl font-bold text-foreground font-mono leading-none">8,803</p>
              <p className="text-xs text-muted-foreground mt-0.5">propiedades indexadas</p>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card border-border">
          <CardContent className="p-4 flex items-center gap-3">
            <div className="flex-shrink-0 w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center">
              <Cpu className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-xl font-bold text-foreground font-mono leading-none">
                {modelCount > 0 ? modelCount : 3}
              </p>
              <p className="text-xs text-muted-foreground mt-0.5">modelos de embedding</p>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card border-border">
          <CardContent className="p-4 flex items-center gap-3">
            <div className="flex-shrink-0 w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center">
              <Zap className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-xl font-bold text-foreground font-mono leading-none">~50ms</p>
              <p className="text-xs text-muted-foreground mt-0.5">latencia promedio</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Examples card */}
      <Card className="bg-card border-border">
        <CardContent className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <Lightbulb className="h-4 w-4 text-primary" />
            <span className="text-sm font-medium text-foreground">Ejemplos de búsqueda</span>
            <span className="text-xs text-muted-foreground ml-1">— haz click para buscar</span>
          </div>
          <div className="space-y-1">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => onSuggestion(s)}
                className="w-full text-left px-3 py-2 rounded-md text-sm text-muted-foreground hover:text-foreground hover:bg-muted/40 transition-colors group"
              >
                <span className="text-primary/50 mr-2 group-hover:text-primary transition-colors">→</span>
                {s}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Feature cards */}
      <div className="grid grid-cols-2 gap-3">
        {FEATURES.map(({ icon: Icon, title, description }) => (
          <Card key={title} className="bg-card border-border">
            <CardContent className="p-4">
              <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center mb-3">
                <Icon className="h-4 w-4 text-primary" />
              </div>
              <p className="text-sm font-medium text-foreground">{title}</p>
              <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{description}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
