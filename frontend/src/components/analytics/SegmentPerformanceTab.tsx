import React, { useEffect, useState } from "react"
import {
  Calendar,
  Grid,
  Sparkles,
  Tag,
  TrendingDown,
} from "lucide-react"
import { api } from "@/api/client"
import { Badge } from "@/components/ui/Badge"
import { Card } from "@/components/ui/Card"
import { formatNumber } from "@/lib/utils"
import { RunResult, SegmentPerformanceResponse } from "@/types"

interface SegmentPerformanceTabProps {
  activeRun: RunResult
}

export const SegmentPerformanceTab: React.FC<SegmentPerformanceTabProps> = ({ activeRun }) => {
  const [data, setData] = useState<SegmentPerformanceResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (!activeRun.id) return
    setIsLoading(true)
    api
      .getSegmentPerformance(activeRun.id)
      .then(setData)
      .catch(() => {})
      .finally(() => setIsLoading(false))
  }, [activeRun.id])

  if (isLoading && !data) {
    return (
      <Card className="p-8 text-center text-xs text-muted-foreground animate-pulse">
        Aggregating cross-sectional segments and seasonal performance...
      </Card>
    )
  }

  if (!data) return null

  return (
    <div className="space-y-6">
      {/* Narrative Takeaway */}
      {data.takeaway && (
        <div className="p-4 rounded-xl border border-indigo-500/20 bg-indigo-500/5 text-xs text-foreground leading-relaxed flex items-start gap-3">
          <Sparkles className="h-4 w-4 text-indigo-500 flex-shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold text-indigo-500">Cross-Sectional Takeaway: </span>
            {data.takeaway}
          </div>
        </div>
      )}

      {/* Seasonal Performance Cards */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-semibold text-foreground flex items-center gap-1.5">
            <Calendar className="h-3.5 w-3.5 text-primary" />
            <span>Seasonal Demand & Volatility</span>
          </h4>
          {data.promo_lift_pct !== 0 && (
            <Badge variant="indigo" size="sm">
              <Tag className="h-3 w-3 mr-1 inline" />
              Promo Lift: {data.promo_lift_pct > 0 ? "+" : ""}
              {data.promo_lift_pct}%
            </Badge>
          )}
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          {data.season_performance.map((s, idx) => (
            <Card key={idx} className="p-3.5 space-y-1">
              <div className="font-semibold text-foreground">{s.season}</div>
              <div className="text-base font-bold font-mono text-primary">
                {formatNumber(s.total_sales)}
              </div>
              <div className="text-[11px] text-muted-foreground flex justify-between pt-1 border-t border-border/50">
                <span>Avg: {formatNumber(s.avg_daily_sales)}/d</span>
                <span className="font-mono">CV: {s.volatility_pct}%</span>
              </div>
            </Card>
          ))}
        </div>
      </div>

      {/* Worst Performing Segments & Heatmap Matrix */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Worst Performing Segments */}
        <Card className="p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <TrendingDown className="h-3.5 w-3.5 text-rose-500" />
              <span>Highest Forecast Risk Segments</span>
            </h4>
            <span className="text-[10px] text-muted-foreground">Ranked by error proxy</span>
          </div>

          {data.worst_segments.length > 0 ? (
            <div className="divide-y divide-border text-xs">
              {data.worst_segments.map((seg, idx) => (
                <div key={idx} className="py-2.5 flex items-center justify-between">
                  <div className="space-y-0.5">
                    <div className="font-medium text-foreground">{seg.segment}</div>
                    <div className="text-[11px] text-muted-foreground">
                      Sales: {formatNumber(seg.total_sales)} • Volatility: {seg.volatility_pct}%
                    </div>
                  </div>
                  <div className="text-right">
                    <Badge
                      variant={
                        seg.status === "High Risk"
                          ? "danger"
                          : seg.status === "Moderate Risk"
                          ? "warning"
                          : "secondary"
                      }
                      size="sm"
                    >
                      {seg.forecast_error_proxy_wape}% WAPE
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-4 text-center text-xs text-muted-foreground">
              No distinct segment breakdown available for this series.
            </div>
          )}
        </Card>

        {/* Heatmap Matrix */}
        <Card className="p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <Grid className="h-3.5 w-3.5 text-primary" />
              <span>Segment vs Season Intensity</span>
            </h4>
            <span className="text-[10px] text-muted-foreground">Daily average units</span>
          </div>

          {data.heatmap_matrix && data.heatmap_matrix.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead>
                  <tr className="border-b border-border text-muted-foreground">
                    <th className="pb-2">Segment</th>
                    <th className="pb-2 text-right">Spring</th>
                    <th className="pb-2 text-right">Summer</th>
                    <th className="pb-2 text-right">Fall</th>
                    <th className="pb-2 text-right">Winter</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {data.heatmap_matrix.slice(0, 6).map((row, i) => (
                    <tr key={i} className="hover:bg-secondary/20">
                      <td className="py-2 font-medium text-foreground">{row.segment}</td>
                      <td className="py-2 text-right font-mono text-muted-foreground">
                        {row.Spring || 0}
                      </td>
                      <td className="py-2 text-right font-mono text-muted-foreground">
                        {row.Summer || 0}
                      </td>
                      <td className="py-2 text-right font-mono text-muted-foreground">
                        {row.Fall || 0}
                      </td>
                      <td className="py-2 text-right font-mono text-muted-foreground">
                        {row.Winter || 0}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-4 text-center text-xs text-muted-foreground">
              Segment heatmap requires store or product group columns in dataset.
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}
