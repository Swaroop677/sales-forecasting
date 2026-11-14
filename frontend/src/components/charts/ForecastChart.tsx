import React, { useState } from "react"
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { BacktestPoint, ForecastPoint } from "@/types"
import { formatNumber } from "@/lib/utils"

interface ForecastChartProps {
  series: ForecastPoint[]
  backtestOverlay?: BacktestPoint[]
  showBacktestDefault?: boolean
  bestModelName?: string
  height?: number
}

const MODEL_COLORS: Record<string, string> = {
  "Seasonal Naive": "#f59e0b", // amber
  "Holt-Winters": "#10b981", // emerald
  "LightGBM": "#6366f1", // indigo
  "XGBoost": "#ec4899", // pink
  "Prophet": "#8b5cf6", // violet
}

export const ForecastChart: React.FC<ForecastChartProps> = ({
  series,
  backtestOverlay = [],
  showBacktestDefault = false,
  bestModelName = "Best Model",
  height = 420,
}) => {
  const [showBacktest, setShowBacktest] = useState(showBacktestDefault)
  const [showConfidenceBands, setShowConfidenceBands] = useState(true)

  // Merge backtest overlay into chart data if toggled
  const backtestMap = new Map<string, Record<string, number>>()
  if (showBacktest) {
    backtestOverlay.forEach((pt) => {
      backtestMap.set(pt.date, pt.predictions)
    })
  }

  // Find where forecast begins for reference shading
  let forecastStartDate = ""
  const chartData = series.map((pt) => {
    const isForecast = pt.actual === null && pt.predicted !== null
    if (isForecast && !forecastStartDate) {
      forecastStartDate = pt.date
    }

    const item: Record<string, any> = {
      date: pt.date,
      actual: pt.actual,
      predicted: pt.predicted,
      lower_bound: pt.lower_bound,
      upper_bound: pt.upper_bound,
      band_range:
        pt.upper_bound !== undefined && pt.lower_bound !== undefined
          ? (pt.upper_bound ?? 0) - (pt.lower_bound ?? 0)
          : null,
    }

    // Attach individual model backtest values if active
    if (showBacktest && backtestMap.has(pt.date)) {
      const preds = backtestMap.get(pt.date)!
      Object.keys(preds).forEach((mName) => {
        item[`backtest_${mName}`] = preds[mName]
      })
    }

    return item
  })

  return (
    <div className="w-full space-y-4">
      {/* Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-muted-foreground pb-2">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-slate-900 dark:bg-slate-100" />
            <span className="font-medium text-foreground">Actual Sales</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-indigo-500" />
            <span className="font-medium text-foreground">{bestModelName} (Forecast)</span>
          </div>
          {forecastStartDate && (
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-4 rounded-sm bg-indigo-500/10 border border-indigo-500/20" />
              <span>Forecast Horizon</span>
            </div>
          )}
        </div>

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-1.5 cursor-pointer hover:text-foreground transition-colors select-none">
            <input
              type="checkbox"
              checked={showBacktest}
              onChange={(e) => setShowBacktest(e.target.checked)}
              className="rounded border-border text-primary focus:ring-primary h-3.5 w-3.5"
            />
            <span>Overlay Backtest Predictions</span>
          </label>

          <label className="flex items-center gap-1.5 cursor-pointer hover:text-foreground transition-colors select-none">
            <input
              type="checkbox"
              checked={showConfidenceBands}
              onChange={(e) => setShowConfidenceBands(e.target.checked)}
              className="rounded border-border text-primary focus:ring-primary h-3.5 w-3.5"
            />
            <span>80% Confidence Band</span>
          </label>
        </div>
      </div>

      {/* Chart Canvas */}
      <div style={{ width: "100%", height }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="forecastAreaGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0.0} />
              </linearGradient>
              <linearGradient id="confidenceBandGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#6366f1" stopOpacity={0.12} />
                <stop offset="100%" stopColor="#6366f1" stopOpacity={0.04} />
              </linearGradient>
            </defs>

            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" opacity={0.7} />

            <XAxis
              dataKey="date"
              stroke="hsl(var(--muted-foreground))"
              fontSize={11}
              tickLine={false}
              tickFormatter={(d: string) => {
                const parts = d.split("-")
                return parts.length >= 3 ? `${parts[1]}/${parts[2]}` : d
              }}
              minTickGap={24}
            />

            <YAxis
              stroke="hsl(var(--muted-foreground))"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v: number) => (v >= 1000 ? `${(v / 1000).toFixed(0)}k` : `${v}`)}
            />

            <Tooltip
              content={({ active, payload, label }) => {
                if (!active || !payload || !payload.length) return null
                return (
                  <div className="rounded-xl border border-border bg-card p-3 shadow-lg text-xs space-y-1.5 min-w-[180px]">
                    <div className="font-semibold text-foreground border-b border-border pb-1">{label}</div>
                    {payload.map((entry: any, i: number) => {
                      if (entry.dataKey === "lower_bound" || entry.dataKey === "band_range") return null
                      return (
                        <div key={i} className="flex items-center justify-between gap-3">
                          <div className="flex items-center gap-1.5">
                            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: entry.color }} />
                            <span className="text-muted-foreground">{entry.name}:</span>
                          </div>
                          <span className="font-medium text-foreground tabular-nums">
                            {formatNumber(entry.value)}
                          </span>
                        </div>
                      )
                    })}
                  </div>
                )
              }}
            />

            {/* Shaded Forecast Horizon Background */}
            {forecastStartDate && (
              <ReferenceArea
                x1={forecastStartDate}
                strokeOpacity={0.3}
                fill="#6366f1"
                fillOpacity={0.05}
                label={{
                  value: "FORECAST HORIZON",
                  position: "insideTopRight",
                  fill: "#6366f1",
                  fontSize: 10,
                  fontWeight: 600,
                  opacity: 0.6,
                }}
              />
            )}

            {/* Confidence Band (Phase 3 foundation) */}
            {showConfidenceBands && (
              <>
                <Area
                  type="monotone"
                  dataKey="lower_bound"
                  stackId="band"
                  stroke="none"
                  fill="transparent"
                  isAnimationActive={false}
                />
                <Area
                  type="monotone"
                  dataKey="band_range"
                  stackId="band"
                  stroke="none"
                  fill="url(#confidenceBandGrad)"
                  name="80% Confidence Band"
                  isAnimationActive={false}
                />
              </>
            )}

            {/* Historical Actual Line */}
            <Line
              type="monotone"
              dataKey="actual"
              name="Actual Sales"
              stroke="#0f172a"
              className="dark:stroke-slate-100"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
              connectNulls={false}
            />

            {/* Forecast Projection Line */}
            <Line
              type="monotone"
              dataKey="predicted"
              name={bestModelName}
              stroke="#6366f1"
              strokeWidth={2.5}
              strokeDasharray="4 4"
              dot={{ r: 2, fill: "#6366f1" }}
              activeDot={{ r: 5 }}
            />

            {/* Backtest Overlays */}
            {showBacktest &&
              Object.keys(MODEL_COLORS).map((modelName) => (
                <Line
                  key={modelName}
                  type="monotone"
                  dataKey={`backtest_${modelName}`}
                  name={`Backtest: ${modelName}`}
                  stroke={MODEL_COLORS[modelName] || "#94a3b8"}
                  strokeWidth={1.5}
                  dot={false}
                  opacity={0.8}
                />
              ))}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
