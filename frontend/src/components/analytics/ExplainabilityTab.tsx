import React, { useEffect, useState } from "react"
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  Calendar,
  Layers,
  Sparkles,
  TrendingUp,
} from "lucide-react"
import { api } from "@/api/client"
import { Badge } from "@/components/ui/Badge"
import { Card } from "@/components/ui/Card"
import { formatNumber } from "@/lib/utils"
import { ExplainabilityResponse, RunResult } from "@/types"

interface ExplainabilityTabProps {
  activeRun: RunResult
}

export const ExplainabilityTab: React.FC<ExplainabilityTabProps> = ({ activeRun }) => {
  const [data, setData] = useState<ExplainabilityResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [selectedDate, setSelectedDate] = useState<string>("")

  const forecastDates = activeRun.forecast_series
    .filter((pt) => pt.predicted !== null)
    .map((pt) => pt.date)

  useEffect(() => {
    if (forecastDates.length > 0 && !selectedDate) {
      setSelectedDate(forecastDates[0])
    }
  }, [activeRun.id])

  useEffect(() => {
    if (!activeRun.id) return
    setIsLoading(true)
    api
      .getExplainability(activeRun.id, selectedDate)
      .then(setData)
      .catch(() => {})
      .finally(() => setIsLoading(false))
  }, [activeRun.id, selectedDate])

  if (isLoading && !data) {
    return (
      <Card className="p-8 text-center text-xs text-muted-foreground animate-pulse">
        Calculating feature contributions and TreeSHAP attribution...
      </Card>
    )
  }

  if (!data) return null

  return (
    <div className="space-y-6">
      {/* Date Selector & Method Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-border">
        <div className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold text-foreground">
            {data.method === "tree_shap"
              ? "TreeSHAP Driver Attribution"
              : data.method === "feature_importance"
              ? "Global Feature Importance"
              : "Time Series Seasonal Decomposition"}
          </h3>
          <Badge variant="outline" size="sm">
            {data.method.replace("_", " ").toUpperCase()}
          </Badge>
        </div>

        {forecastDates.length > 0 && (
          <div className="flex items-center gap-2 text-xs">
            <Calendar className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-muted-foreground">Explain Date:</span>
            <select
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="text-xs bg-background border border-border rounded-lg px-2.5 py-1 text-foreground focus:ring-1 focus:ring-primary font-mono"
            >
              {forecastDates.slice(0, 30).map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Narrative Takeaway Callout */}
      {data.narrative && (
        <div className="p-4 rounded-xl border border-indigo-500/20 bg-indigo-500/5 text-xs text-foreground leading-relaxed flex items-start gap-3">
          <Sparkles className="h-4 w-4 text-indigo-500 flex-shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold text-indigo-500">Why this number? </span>
            {data.narrative}
          </div>
        </div>
      )}

      {/* Breakdown Grid */}
      {data.local_breakdown && data.local_breakdown.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Local Attribution Waterfall */}
          <Card className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                <Activity className="h-3.5 w-3.5 text-primary" />
                <span>Local Feature Drivers on {data.selected_date}</span>
              </h4>
              {data.base_value !== undefined && (
                <span className="text-[11px] font-mono text-muted-foreground">
                  Base: {formatNumber(data.base_value)} units
                </span>
              )}
            </div>

            <div className="space-y-2 pt-1">
              {data.local_breakdown.map((item, idx) => {
                const isPos = item.contribution > 0
                return (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-2 rounded-lg bg-secondary/30 hover:bg-secondary/60 transition-colors text-xs"
                  >
                    <div className="space-y-0.5">
                      <div className="font-medium text-foreground">{item.feature}</div>
                      <div className="text-[10px] text-muted-foreground">{item.category}</div>
                    </div>
                    <div
                      className={`font-mono font-semibold flex items-center gap-1 ${
                        isPos ? "text-emerald-500" : "text-rose-500"
                      }`}
                    >
                      {isPos ? (
                        <ArrowUpRight className="h-3.5 w-3.5" />
                      ) : (
                        <ArrowDownRight className="h-3.5 w-3.5" />
                      )}
                      <span>
                        {isPos ? "+" : ""}
                        {item.contribution}
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          </Card>

          {/* Category Net Impact & Global Drivers */}
          <div className="space-y-4">
            {data.category_summary && (
              <Card className="p-4 space-y-3">
                <h4 className="text-xs font-semibold text-foreground">Category Net Impact</h4>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  {data.category_summary.map((cat, i) => (
                    <div key={i} className="p-2.5 rounded-lg border border-border bg-card">
                      <div className="text-[11px] text-muted-foreground">{cat.category}</div>
                      <div
                        className={`text-sm font-semibold font-mono mt-1 ${
                          cat.net_impact >= 0 ? "text-emerald-500" : "text-rose-500"
                        }`}
                      >
                        {cat.net_impact >= 0 ? "+" : ""}
                        {cat.net_impact} units
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            )}

            {data.global_drivers && (
              <Card className="p-4 space-y-3">
                <h4 className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                  <TrendingUp className="h-3.5 w-3.5 text-primary" />
                  <span>Global Feature Importance</span>
                </h4>
                <div className="space-y-2">
                  {data.global_drivers.slice(0, 4).map((gd, idx) => (
                    <div key={idx} className="space-y-1">
                      <div className="flex justify-between text-[11px]">
                        <span className="font-medium text-foreground">{gd.feature}</span>
                        <span className="font-mono text-muted-foreground">{gd.importance_pct}%</span>
                      </div>
                      <div className="h-1.5 w-full bg-secondary rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary rounded-full"
                          style={{ width: `${Math.min(100, gd.importance_pct * 2)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </div>
        </div>
      ) : data.trend && data.dates ? (
        /* Classical Decomposition Preview */
        <Card className="p-4 space-y-4">
          <h4 className="text-xs font-semibold text-foreground">Recent 30-Day Trend & Seasonality</h4>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
            <div className="p-3 rounded-lg border border-border bg-secondary/20">
              <span className="text-muted-foreground">Baseline Trend</span>
              <div className="text-base font-semibold font-mono text-foreground mt-1">
                {formatNumber(data.trend[data.trend.length - 1])}
              </div>
            </div>
            <div className="p-3 rounded-lg border border-border bg-secondary/20">
              <span className="text-muted-foreground">Seasonal Amplitude</span>
              <div className="text-base font-semibold font-mono text-foreground mt-1">
                ±{formatNumber(Math.max(...(data.seasonal || [0])))}
              </div>
            </div>
            <div className="p-3 rounded-lg border border-border bg-secondary/20">
              <span className="text-muted-foreground">Cycle Cadence</span>
              <div className="text-base font-semibold font-mono text-foreground mt-1">
                7 Days (Weekly)
              </div>
            </div>
          </div>
        </Card>
      ) : null}
    </div>
  )
}
