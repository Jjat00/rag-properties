import { useEffect, useRef, useState, useCallback } from "react"
import {
  forceSimulation,
  forceLink,
  forceManyBody,
  forceCenter,
  forceCollide,
  type SimulationNodeDatum,
  type SimulationLinkDatum,
} from "d3-force"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { PropertyResult } from "@/types/api"

interface SimilarityGraphProps {
  results: PropertyResult[]
}

interface GraphNode extends SimulationNodeDatum {
  id: string
  label: string
  score: number
  price: number
  type: string
  radius: number
}

interface GraphLink extends SimulationLinkDatum<GraphNode> {
  opacity: number
}

const TYPE_COLORS: Record<string, string> = {
  Casa: "#3B82F6",
  "Casa en condominio": "#3B82F6",
  "Casa uso de suelo": "#3B82F6",
  Departamento: "#22C55E",
  Terreno: "#F97316",
  "Terreno residencial": "#F97316",
  "Terreno comercial": "#F97316",
  "Terreno industrial": "#F97316",
  Oficina: "#8B5CF6",
  Local: "#06B6D4",
  PH: "#E11D48",
  Bodega: "#EAB308",
  Edificio: "#14B8A6",
  Finca: "#A855F7",
}

function getTypeColor(type: string | null): string {
  if (!type) return "#8C8C8C"
  return TYPE_COLORS[type] ?? "#8C8C8C"
}

export function SimilarityGraph({ results }: SimilarityGraphProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [tooltip, setTooltip] = useState<{ x: number; y: number; node: GraphNode } | null>(null)
  const nodesRef = useRef<GraphNode[]>([])
  const linksRef = useRef<GraphLink[]>([])

  const draw = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext("2d")
    if (!ctx) return
    const { width, height } = canvas

    ctx.clearRect(0, 0, width, height)

    // Draw links
    for (const link of linksRef.current) {
      const source = link.source as GraphNode
      const target = link.target as GraphNode
      if (source.x == null || source.y == null || target.x == null || target.y == null) continue
      ctx.beginPath()
      ctx.moveTo(source.x, source.y)
      ctx.lineTo(target.x, target.y)
      ctx.strokeStyle = `rgba(255,255,255,${link.opacity * 0.3})`
      ctx.lineWidth = 1
      ctx.stroke()
    }

    // Draw nodes
    for (const node of nodesRef.current) {
      if (node.x == null || node.y == null) continue
      const color = getTypeColor(node.type)

      // Glow
      const glowIntensity = node.score * 0.6
      ctx.beginPath()
      ctx.arc(node.x, node.y, node.radius + 4, 0, Math.PI * 2)
      ctx.fillStyle = `${color}${Math.round(glowIntensity * 255).toString(16).padStart(2, "0")}`
      ctx.fill()

      // Node
      ctx.beginPath()
      ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2)
      ctx.fillStyle = color
      ctx.fill()
      ctx.strokeStyle = `${color}88`
      ctx.lineWidth = 1.5
      ctx.stroke()

      // Score text
      ctx.fillStyle = "#FFFFFF"
      ctx.font = `${Math.max(8, node.radius * 0.7)}px monospace`
      ctx.textAlign = "center"
      ctx.textBaseline = "middle"
      ctx.fillText(`${Math.round(node.score * 100)}`, node.x, node.y)
    }
  }, [])

  useEffect(() => {
    if (results.length === 0) return

    const canvas = canvasRef.current
    if (!canvas) return
    const width = canvas.parentElement?.clientWidth ?? 600
    const height = 350
    canvas.width = width
    canvas.height = height

    // Build nodes
    const maxPrice = Math.max(...results.map((r) => r.price ?? 0), 1)
    const nodes: GraphNode[] = results.map((r, i) => ({
      id: r.id ?? `${i}`,
      label: r.title ?? "Sin titulo",
      score: r.score,
      price: r.price ?? 0,
      type: r.property_type ?? "",
      radius: 8 + Math.sqrt((r.price ?? 0) / maxPrice) * 20,
    }))

    // Build links — connect nodes with close scores
    const links: GraphLink[] = []
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const diff = Math.abs(nodes[i].score - nodes[j].score)
        if (diff < 0.05) {
          links.push({
            source: nodes[i],
            target: nodes[j],
            opacity: 1 - diff / 0.05,
          })
        }
      }
    }

    nodesRef.current = nodes
    linksRef.current = links

    const sim = forceSimulation(nodes)
      .force("link", forceLink<GraphNode, GraphLink>(links).distance(80))
      .force("charge", forceManyBody().strength(-120))
      .force("center", forceCenter(width / 2, height / 2))
      .force("collide", forceCollide<GraphNode>().radius((d) => d.radius + 4))
      .on("tick", draw)

    return () => { sim.stop() }
  }, [results, draw])

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top

    const found = nodesRef.current.find((n) => {
      if (n.x == null || n.y == null) return false
      const dx = n.x - x
      const dy = n.y - y
      return Math.sqrt(dx * dx + dy * dy) < n.radius + 4
    })

    if (found) {
      setTooltip({ x: e.clientX - rect.left, y: e.clientY - rect.top - 40, node: found })
    } else {
      setTooltip(null)
    }
  }

  if (results.length === 0) return null

  // Build legend from unique types
  const uniqueTypes = [...new Set(results.map((r) => r.property_type).filter(Boolean))] as string[]

  return (
    <Card className="bg-card border-border">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Grafo de Similitud
        </CardTitle>
      </CardHeader>
      <CardContent className="relative">
        <canvas
          ref={canvasRef}
          className="w-full rounded-lg"
          style={{ height: 350 }}
          onMouseMove={handleMouseMove}
          onMouseLeave={() => setTooltip(null)}
        />

        {/* Tooltip */}
        {tooltip && (
          <div
            className="absolute pointer-events-none bg-popover border border-border rounded-md px-3 py-2 text-xs shadow-lg z-10"
            style={{ left: tooltip.x, top: tooltip.y, transform: "translateX(-50%)" }}
          >
            <p className="font-medium text-foreground truncate max-w-[200px]">{tooltip.node.label}</p>
            <p className="text-muted-foreground">
              Score: {Math.round(tooltip.node.score * 100)}% | {tooltip.node.type}
            </p>
          </div>
        )}

        {/* Legend */}
        <div className="flex items-center gap-3 mt-3 flex-wrap">
          {uniqueTypes.map((t) => (
            <div key={t} className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: getTypeColor(t) }} />
              {t}
            </div>
          ))}
          <span className="text-[10px] text-muted-foreground/50 ml-auto">
            Tamano = precio relativo
          </span>
        </div>
      </CardContent>
    </Card>
  )
}
