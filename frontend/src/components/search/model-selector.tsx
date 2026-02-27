import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import type { EmbeddingModelInfo } from "@/types/api"

interface ModelSelectorProps {
  models: EmbeddingModelInfo[]
  selectedModel: string
  onModelChange: (model: string) => void
  topK: number
  onTopKChange: (k: number) => void
}

const MODEL_LABELS: Record<string, string> = {
  "openai-small": "OpenAI Small (1536d)",
  "openai-large": "OpenAI Large (3072d)",
  gemini: "Gemini (3072d)",
}

export function ModelSelector({
  models,
  selectedModel,
  onModelChange,
  topK,
  onTopKChange,
}: ModelSelectorProps) {
  return (
    <div className="flex items-center gap-4 flex-wrap">
      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground whitespace-nowrap">Modelo:</span>
        <Select value={selectedModel} onValueChange={onModelChange}>
          <SelectTrigger className="w-[200px] bg-card border-border">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {models.map((m) => (
              <SelectItem key={m.id} value={m.id}>
                {MODEL_LABELS[m.id] ?? m.id}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex items-center gap-3">
        <span className="text-sm text-muted-foreground whitespace-nowrap">Top K:</span>
        <Slider
          value={[topK]}
          onValueChange={([v]) => onTopKChange(v)}
          min={1}
          max={50}
          step={1}
          className="w-[120px]"
        />
        <span className="text-sm font-mono text-foreground w-6 text-right">{topK}</span>
      </div>
    </div>
  )
}
