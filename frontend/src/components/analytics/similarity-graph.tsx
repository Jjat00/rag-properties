import { useEffect, useRef, useState, useCallback } from "react"
import {
  forceSimulation,
  forceLink,
  forceManyBody,
  forceCenter,
  forceCollide,
  type Simulation,
  type SimulationNodeDatum,
  type SimulationLinkDatum,
} from "d3-force"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { X } from "lucide-react"
import type { PropertyResult } from "@/types/api"

interface SimilarityGraphProps {
  results: PropertyResult[]
}

interface GraphNode extends SimulationNodeDatum {
  idx: number
  id: string
  label: string
  score: number
  price: number
  type: string
  radius: number
  property: PropertyResult
}

interface GraphLink extends SimulationLinkDatum<GraphNode> {
  strength: number
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

function hitTest(nodes: GraphNode[], x: number, y: number): GraphNode | null {
  for (let i = nodes.length - 1; i >= 0; i--) {
    const n = nodes[i]
    if (n.x == null || n.y == null) continue
    const dx = n.x - x
    const dy = n.y - y
    if (dx * dx + dy * dy < (n.radius + 3) * (n.radius + 3)) return n
  }
  return null
}

export function SimilarityGraph({ results }: SimilarityGraphProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const simRef = useRef<Simulation<GraphNode, GraphLink> | null>(null)
  const nodesRef = useRef<GraphNode[]>([])
  const linksRef = useRef<GraphLink[]>([])
  const dragRef = useRef<{ node: GraphNode; offsetX: number; offsetY: number } | null>(null)
  const hoveredRef = useRef<GraphNode | null>(null)

  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)

  const draw = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext("2d")
    if (!ctx) return
    const { width, height } = canvas
    const hovered = hoveredRef.current
    const selected = nodesRef.current.find((n) => n.id === selectedNode?.id) ?? null

    ctx.clearRect(0, 0, width, height)

    // Draw links
    for (const link of linksRef.current) {
      const source = link.source as GraphNode
      const target = link.target as GraphNode
      if (source.x == null || source.y == null || target.x == null || target.y == null) continue

      const isHighlighted =
        hovered && (source.id === hovered.id || target.id === hovered.id) ||
        selected && (source.id === selected.id || target.id === selected.id)

      ctx.beginPath()
      ctx.moveTo(source.x, source.y)
      ctx.lineTo(target.x, target.y)
      ctx.strokeStyle = isHighlighted
        ? `rgba(255,255,255,${0.4 + link.strength * 0.4})`
        : `rgba(255,255,255,${0.06 + link.strength * 0.12})`
      ctx.lineWidth = isHighlighted ? 2 : 1
      ctx.stroke()
    }

    // Draw nodes
    for (const node of nodesRef.current) {
      if (node.x == null || node.y == null) continue
      const color = getTypeColor(node.type)
      const isHovered = hovered?.id === node.id
      const isSelected = selected?.id === node.id
      const isActive = isHovered || isSelected

      // Glow for active nodes
      if (isActive) {
        ctx.beginPath()
        ctx.arc(node.x, node.y, node.radius + 8, 0, Math.PI * 2)
        const grad = ctx.createRadialGradient(node.x, node.y, node.radius, node.x, node.y, node.radius + 8)
        grad.addColorStop(0, `${color}66`)
        grad.addColorStop(1, `${color}00`)
        ctx.fillStyle = grad
        ctx.fill()
      }

      // Node circle
      ctx.beginPath()
      ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2)
      ctx.fillStyle = isActive ? color : `${color}CC`
      ctx.fill()

      // Border
      if (isSelected) {
        ctx.strokeStyle = "#FFFFFF"
        ctx.lineWidth = 3
      } else if (isHovered) {
        ctx.strokeStyle = "#FFFFFF"
        ctx.lineWidth = 2
      } else {
        ctx.strokeStyle = `${color}55`
        ctx.lineWidth = 1.5
      }
      ctx.stroke()

      // Score text
      ctx.fillStyle = "#FFFFFF"
      ctx.font = `bold ${Math.max(9, node.radius * 0.65)}px monospace`
      ctx.textAlign = "center"
      ctx.textBaseline = "middle"
      ctx.fillText(`${Math.round(node.score * 100)}`, node.x, node.y)
    }

    // Cursor
    if (canvas) {
      canvas.style.cursor = hovered ? "grab" : "default"
      if (dragRef.current) canvas.style.cursor = "grabbing"
    }
  }, [selectedNode])

  // Build simulation
  useEffect(() => {
    if (results.length === 0) return

    const canvas = canvasRef.current
    if (!canvas) return
    const width = canvas.parentElement?.clientWidth ?? 700
    const height = 400
    canvas.width = width
    canvas.height = height

    const maxPrice = Math.max(...results.map((r) => r.price ?? 0), 1)
    const nodes: GraphNode[] = results.map((r, i) => ({
      idx: i,
      id: r.id ?? `${i}`,
      label: r.title ?? "Sin titulo",
      score: r.score,
      price: r.price ?? 0,
      type: r.property_type ?? "",
      radius: 12 + Math.sqrt((r.price ?? 0) / maxPrice) * 18,
      property: r,
    }))

    // Links: connect all pairs, strength based on score similarity
    const links: GraphLink[] = []
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const diff = Math.abs(nodes[i].score - nodes[j].score)
        if (diff < 0.08) {
          links.push({
            source: nodes[i],
            target: nodes[j],
            strength: 1 - diff / 0.08,
          })
        }
      }
    }

    nodesRef.current = nodes
    linksRef.current = links

    const sim = forceSimulation(nodes)
      .force("link", forceLink<GraphNode, GraphLink>(links).distance(100).strength((l) => l.strength * 0.3))
      .force("charge", forceManyBody().strength(-200))
      .force("center", forceCenter(width / 2, height / 2))
      .force("collide", forceCollide<GraphNode>().radius((d) => d.radius + 6).strength(0.8))
      .on("tick", draw)

    simRef.current = sim

    return () => {
      sim.stop()
      simRef.current = null
    }
  }, [results, draw])

  // Mouse events for drag & click
  const getCanvasPos = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = canvasRef.current!.getBoundingClientRect()
    return { x: e.clientX - rect.left, y: e.clientY - rect.top }
  }

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const { x, y } = getCanvasPos(e)
    const node = hitTest(nodesRef.current, x, y)
    if (node && node.x != null && node.y != null) {
      dragRef.current = { node, offsetX: node.x - x, offsetY: node.y - y }
      node.fx = node.x
      node.fy = node.y
      simRef.current?.alphaTarget(0.3).restart()
    }
  }

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const { x, y } = getCanvasPos(e)

    if (dragRef.current) {
      const { node, offsetX, offsetY } = dragRef.current
      node.fx = x + offsetX
      node.fy = y + offsetY
      return
    }

    const node = hitTest(nodesRef.current, x, y)
    if (node !== hoveredRef.current) {
      hoveredRef.current = node
      draw()
    }
  }

  const handleMouseUp = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (dragRef.current) {
      const { node } = dragRef.current
      // If barely moved, treat as click
      const { x, y } = getCanvasPos(e)
      const movedDist = Math.sqrt(
        (node.fx! - (x + dragRef.current.offsetX)) ** 2 +
        (node.fy! - (y + dragRef.current.offsetY)) ** 2,
      )
      node.fx = null
      node.fy = null
      dragRef.current = null
      simRef.current?.alphaTarget(0)

      if (movedDist < 3) {
        setSelectedNode((prev) => (prev?.id === node.id ? null : node))
      }
      return
    }

    // Click on empty space → deselect
    const { x, y } = getCanvasPos(e)
    const node = hitTest(nodesRef.current, x, y)
    if (!node) setSelectedNode(null)
  }

  const handleMouseLeave = () => {
    if (dragRef.current) {
      dragRef.current.node.fx = null
      dragRef.current.node.fy = null
      dragRef.current = null
      simRef.current?.alphaTarget(0)
    }
    hoveredRef.current = null
    draw()
  }

  if (results.length === 0) return null

  const uniqueTypes = [...new Set(results.map((r) => r.property_type).filter(Boolean))] as string[]
  const sel = selectedNode?.property

  return (
    <Card className="bg-card border-border">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Grafo de Similitud
          <span className="text-[10px] ml-2 font-normal">
            Arrastra nodos. Click para ver payload.
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex gap-4">
          {/* Canvas */}
          <div className="flex-1 relative">
            <canvas
              ref={canvasRef}
              className="w-full rounded-lg bg-[#060607]"
              style={{ height: 400 }}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseLeave}
            />

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
          </div>

          {/* Payload panel (like Qdrant) */}
          {sel && (
            <div className="w-72 flex-shrink-0 bg-[#060607] border border-border rounded-lg overflow-hidden">
              <div className="flex items-center justify-between px-3 py-2 border-b border-border">
                <span className="text-xs font-medium text-foreground">Payload</span>
                <button
                  onClick={() => setSelectedNode(null)}
                  className="text-muted-foreground hover:text-foreground transition-colors"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
              <ScrollArea className="h-[380px]">
                <pre className="p-3 text-[11px] leading-relaxed font-mono">
                  <span className="text-muted-foreground">{"{"}</span>
                  {"\n"}
                  {renderPayloadField("id", sel.id)}
                  {renderPayloadField("title", sel.title)}
                  {renderPayloadField("property_type", sel.property_type)}
                  {renderPayloadField("operation", sel.operation)}
                  {renderPayloadField("price", sel.price)}
                  {renderPayloadField("currency", sel.currency)}
                  {renderPayloadField("city", sel.city)}
                  {renderPayloadField("state", sel.state)}
                  {renderPayloadField("neighborhood", sel.neighborhood)}
                  {renderPayloadField("address", sel.address)}
                  {renderPayloadField("bedrooms", sel.bedrooms)}
                  {renderPayloadField("bathrooms", sel.bathrooms)}
                  {renderPayloadField("surface", sel.surface)}
                  {renderPayloadField("roofed_surface", sel.roofed_surface)}
                  {renderPayloadField("condition", sel.condition)}
                  {renderPayloadField("internal_id", sel.internal_id)}
                  {renderPayloadField("agent_first_name", sel.agent_first_name)}
                  {renderPayloadField("agent_last_name", sel.agent_last_name)}
                  {renderPayloadField("agent_company", sel.agent_company)}
                  {renderPayloadField("agent_phone", sel.agent_phone)}
                  {renderPayloadField("score", sel.score)}
                  <span className="text-muted-foreground">{"}"}</span>
                </pre>
              </ScrollArea>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

function renderPayloadField(key: string, value: string | number | null | undefined) {
  if (value == null) return null
  const isString = typeof value === "string"
  return (
    <span>
      {"  "}
      <span className="text-red-400">"{key}"</span>
      <span className="text-muted-foreground">: </span>
      {isString ? (
        <span className="text-green-400">"{value}"</span>
      ) : (
        <span className="text-yellow-400">{value}</span>
      )}
      {"\n"}
    </span>
  )
}
