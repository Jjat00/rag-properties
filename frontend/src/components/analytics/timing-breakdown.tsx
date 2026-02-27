import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import type { SearchMetrics } from "@/types/api"

interface TimingBreakdownProps {
  metrics: SearchMetrics
}

const COLORS: Record<string, string> = {
  Parse: "#8B5CF6",
  Embed: "#3B82F6",
  Search: "#06B6D4",
}

export function TimingBreakdown({ metrics }: TimingBreakdownProps) {
  const data = [
    { name: "Parse", ms: Math.round(metrics.parse_time_ms) },
    { name: "Embed", ms: Math.round(metrics.embed_time_ms) },
    { name: "Search", ms: Math.round(metrics.search_time_ms) },
  ]

  return (
    <Card className="bg-card border-border">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Tiempos
          </CardTitle>
          <Badge variant="outline" className="bg-muted/50 text-muted-foreground border-border font-mono text-xs">
            {Math.round(metrics.total_time_ms)}ms total
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={120}>
          <BarChart data={data} layout="vertical" margin={{ left: 10, right: 10 }}>
            <XAxis type="number" hide />
            <YAxis
              type="category"
              dataKey="name"
              width={50}
              tick={{ fill: "#8C8C8C", fontSize: 12 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#0E0E0F",
                border: "1px solid #1F1F1F",
                borderRadius: "8px",
                color: "#F2F2F2",
                fontSize: 12,
              }}
              formatter={(value) => [`${value}ms`, "Tiempo"]}
            />
            <Bar dataKey="ms" radius={[0, 4, 4, 0]} barSize={16}>
              {data.map((entry) => (
                <Cell key={entry.name} fill={COLORS[entry.name]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <p className="text-[10px] text-muted-foreground/50 mt-2 text-center">
          De {metrics.candidates_before_filter.toLocaleString()} propiedades indexadas
        </p>
      </CardContent>
    </Card>
  )
}
