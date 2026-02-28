import { type FormEvent } from "react"
import { Search, Loader2 } from "lucide-react"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"

interface SearchBarProps {
  value: string
  onChange: (v: string) => void
  onSearch: (query: string) => void
  loading: boolean
}

export function SearchBar({ value, onChange, onSearch, loading }: SearchBarProps) {
  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    const trimmed = value.trim()
    if (trimmed) onSearch(trimmed)
  }

  return (
    <form onSubmit={handleSubmit} className="relative w-full">
      <div className="relative">
        {loading ? (
          <Loader2 className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground animate-spin" />
        ) : (
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
        )}
        <Input
          type="text"
          placeholder='Busca en lenguaje natural: "casa de 4 habitaciones con 2 baños en Cancún"'
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={cn(
            "h-12 pl-12 pr-4 bg-card border-border rounded-lg text-foreground placeholder:text-muted-foreground",
            "focus-visible:ring-primary/50 focus-visible:border-primary/50",
            loading && "animate-pulse",
          )}
        />
      </div>
      <p className="mt-2 text-xs text-muted-foreground">
        Presiona Enter para buscar. Los filtros se extraen automáticamente del texto.
      </p>
    </form>
  )
}
