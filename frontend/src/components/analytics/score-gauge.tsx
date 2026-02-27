import { RadialBarChart, RadialBar, PolarAngleAxis } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { SearchMetrics } from "@/types/api"
import { formatScore } from "@/lib/utils"

interface ScoreGaugeProps {
  metrics: SearchMetrics
}

export function ScoreGauge({ metrics }: ScoreGaugeProps) {
  const avg = formatScore(metrics.score_avg)
  const min = formatScore(metrics.score_min)
  const max = formatScore(metrics.score_max)

  const fill = avg >= 75 ? "#22C55E" : avg >= 50 ? "#F59E0B" : "#EF4444"

  const data = [{ value: avg, fill }]

  return (
    <Card className="bg-card border-border">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">Score Promedio</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col items-center">
        <RadialBarChart
          width={160}
          height={100}
          cx={80}
          cy={90}
          innerRadius={60}
          outerRadius={80}
          barSize={12}
          data={data}
          startAngle={180}
          endAngle={0}
        >
          <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
          <RadialBar
            dataKey="value"
            cornerRadius={6}
            background={{ fill: "#1F1F1F" }}
          />
          <text
            x={80}
            y={75}
            textAnchor="middle"
            dominantBaseline="middle"
            className="fill-foreground text-2xl font-bold"
          >
            {avg}%
          </text>
        </RadialBarChart>
        <div className="flex gap-6 text-xs text-muted-foreground mt-1">
          <span>Min: {min}%</span>
          <span>Max: {max}%</span>
        </div>
      </CardContent>
    </Card>
  )
}
