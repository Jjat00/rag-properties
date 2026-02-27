import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { PropertyResult } from "@/types/api"

interface ScoreDistributionProps {
  results: PropertyResult[]
}

function buildHistogram(results: PropertyResult[]) {
  const bins = Array.from({ length: 10 }, (_, i) => ({
    range: `${i * 10}-${(i + 1) * 10}%`,
    count: 0,
    bin: i,
  }))
  for (const r of results) {
    const pct = r.score * 100
    const idx = Math.min(Math.floor(pct / 10), 9)
    bins[idx].count++
  }
  return bins
}

function binColor(bin: number): string {
  const colors = [
    "#EF4444", "#F97316", "#F59E0B", "#EAB308",
    "#84CC16", "#22C55E", "#10B981", "#14B8A6",
    "#06B6D4", "#3B82F6",
  ]
  return colors[bin]
}

export function ScoreDistribution({ results }: ScoreDistributionProps) {
  const data = buildHistogram(results)

  return (
    <Card className="bg-card border-border">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Distribucion de Scores
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={120}>
          <BarChart data={data} margin={{ left: -10 }}>
            <XAxis
              dataKey="range"
              tick={{ fill: "#8C8C8C", fontSize: 9 }}
              axisLine={false}
              tickLine={false}
              interval={1}
            />
            <YAxis hide />
            <Tooltip
              contentStyle={{
                backgroundColor: "#0E0E0F",
                border: "1px solid #1F1F1F",
                borderRadius: "8px",
                color: "#F2F2F2",
                fontSize: 12,
              }}
              formatter={(value) => [`${value} propiedades`]}
            />
            <Bar dataKey="count" radius={[4, 4, 0, 0]} barSize={20}>
              {data.map((entry) => (
                <Cell key={entry.range} fill={binColor(entry.bin)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
