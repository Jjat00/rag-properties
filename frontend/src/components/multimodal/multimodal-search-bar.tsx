import { useRef, type KeyboardEvent } from "react"
import { Search, Loader2, ImagePlus, X } from "lucide-react"
import { Button } from "@/components/ui/button"

interface MultimodalSearchBarProps {
  value: string
  onChange: (value: string) => void
  onSearch: (query: string) => void
  onImageSearch: (file: File) => void
  imageFile: File | null
  imagePreview: string | null
  onClearImage: () => void
  loading: boolean
}

export function MultimodalSearchBar({
  value,
  onChange,
  onSearch,
  onImageSearch,
  imageFile,
  imagePreview,
  onClearImage,
  loading,
}: MultimodalSearchBarProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && value.trim()) {
      onSearch(value.trim())
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      onImageSearch(file)
    }
    // Reset so the same file can be selected again
    if (fileInputRef.current) fileInputRef.current.value = ""
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Buscar por texto o sube una imagen..."
            className="w-full h-12 pl-10 pr-4 rounded-lg border border-border bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
          />
        </div>

        {/* Image upload button */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={handleFileChange}
          className="hidden"
        />
        <Button
          variant="outline"
          onClick={() => fileInputRef.current?.click()}
          disabled={loading}
          className="h-12 px-4 gap-2 border-border"
          title="Buscar por imagen"
        >
          <ImagePlus className="h-4 w-4" />
          <span className="hidden sm:inline">Imagen</span>
        </Button>

        <Button
          onClick={() => value.trim() && onSearch(value.trim())}
          disabled={loading || !value.trim()}
          className="h-12 px-6"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Buscar"}
        </Button>
      </div>

      {/* Image preview */}
      {imagePreview && (
        <div className="flex items-center gap-3 p-3 rounded-lg border border-border bg-card/50">
          <img
            src={imagePreview}
            alt="Imagen de busqueda"
            className="w-16 h-16 rounded-md object-cover"
          />
          <div className="flex-1 min-w-0">
            <p className="text-sm text-foreground truncate">{imageFile?.name}</p>
            <p className="text-xs text-muted-foreground">
              {imageFile ? `${(imageFile.size / 1024).toFixed(0)} KB` : ""}
              {" · Busqueda por imagen"}
            </p>
          </div>
          <button
            onClick={onClearImage}
            className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  )
}
