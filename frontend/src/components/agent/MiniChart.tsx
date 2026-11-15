import React from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { Card } from "@/components/ui/Card"
import { formatNumber } from "@/lib/utils"

interface MiniChartProps {
  spec: Record<string, any>
}

export const MiniChart: React.FC<MiniChartProps> = ({ spec }) => {
  if (!spec || !spec.data || spec.data.length === 0) return null

  const chartType = spec.type || "bar"
  const title = spec.title || "Chart"

  return (
    <Card className="p-3 my-3 bg-card border border-border/80 shadow-sm max-w-lg">
      <div className="text-xs font-semibold text-foreground mb-2 flex items-center justify-between border-b border-border/50 pb-1.5">
        <span>{title}</span>
        {spec.unit && <span className="text-[10px] text-muted-foreground uppercase">{spec.unit}</span>}
      </div>

      <div className="h-44 w-full">
        <ResponsiveContainer width="100%" height="100%">
          {chartType === "bar" || chartType === "comparison_bars" || chartType === "top_movers_bar" ? (
            <BarChart data={spec.data} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" opacity={0.6} />
              <XAxis dataKey={spec.xKey || "name"} fontSize={10} stroke="hsl(var(--muted-foreground))" tickLine={false} />
              <YAxis fontSize={10} stroke="hsl(var(--muted-foreground))" tickLine={false} axisLine={false} />
              <Tooltip
                content={({ active, payload }) => {
                  if (!active || !payload?.length) return null
                  const d = payload[0]
                  return (
                    <div className="bg-slate-900 text-white rounded-lg p-2 text-xs shadow-md">
                      <span className="text-muted-foreground">{d.name || d.payload[spec.xKey || "name"]}: </span>
                      <span className="font-semibold">{formatNumber(Number(d.value))}</span>
                      {spec.unit && ` ${spec.unit}`}
                    </div>
                  )
                }}
              />
              <Bar dataKey={spec.yKey || "value"} radius={[4, 4, 0, 0]}>
                {spec.data.map((entry: any, index: number) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.is_best ? "#6366f1" : (entry.change_pct !== undefined && entry.change_pct < 0 ? "#f43f5e" : "#8b5cf6")}
                  />
                ))}
              </Bar>
            </BarChart>
          ) : (
            <LineChart data={spec.data} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" opacity={0.6} />
              <XAxis dataKey={spec.xKey || "date"} fontSize={10} stroke="hsl(var(--muted-foreground))" tickLine={false} minTickGap={20} />
              <YAxis fontSize={10} stroke="hsl(var(--muted-foreground))" tickLine={false} axisLine={false} />
              <Tooltip
                content={({ active, payload }) => {
                  if (!active || !payload?.length) return null
                  return (
                    <div className="bg-slate-900 text-white rounded-lg p-2 text-xs shadow-md space-y-1">
                      {payload.map((p, idx) => (
                        <div key={idx} className="flex justify-between gap-2">
                          <span className="text-slate-400">{p.name}:</span>
                          <span className="font-semibold">{formatNumber(Number(p.value))}</span>
                        </div>
                      ))}
                    </div>
                  )
                }}
              />
              {spec.type === "scenario_comparison" ? (
                <>
                  <Line type="monotone" dataKey="baseline" name="Baseline" stroke="#94a3b8" strokeWidth={1.5} dot={false} />
                  <Line type="monotone" dataKey="simulated" name="Simulated" stroke="#6366f1" strokeWidth={2} strokeDasharray="3 3" dot={false} />
                </>
              ) : (
                <>
                  <Line type="monotone" dataKey="actual" name="Actual" stroke="#0f172a" className="dark:stroke-slate-100" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="predicted" name="Forecast" stroke="#6366f1" strokeWidth={2} strokeDasharray="3 3" dot={false} />
                </>
              )}
            </LineChart>
          )}
        </ResponsiveContainer>
      </div>
    </Card>
  )
}
