import React, { useEffect, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import {
  ArrowLeft,
  CheckCircle2,
  FileSpreadsheet,
  Printer,
  Trophy,
} from "lucide-react"
import { api } from "@/api/client"
import { ForecastChart } from "@/components/charts/ForecastChart"
import { Badge } from "@/components/ui/Badge"
import { Button } from "@/components/ui/Button"
import { Card } from "@/components/ui/Card"
import { formatNumber } from "@/lib/utils"
import { InventorySupportResponse, RunResult } from "@/types"

export const ReportPage: React.FC = () => {
  const { runId } = useParams<{ runId: string }>()
  const navigate = useNavigate()
  const [run, setRun] = useState<RunResult | null>(null)
  const [inventory, setInventory] = useState<InventorySupportResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (!runId) return
    setIsLoading(true)
    Promise.all([
      api.getRunResult(runId),
      api.getInventorySupport(runId).catch(() => null),
    ])
      .then(([runRes, invRes]) => {
        setRun(runRes)
        setInventory(invRes)
      })
      .catch(() => {})
      .finally(() => setIsLoading(false))
  }, [runId])

  if (isLoading || !run) {
    return (
      <div className="max-w-4xl mx-auto py-12 text-center text-xs text-muted-foreground">
        Loading executive forecast report...
      </div>
    )
  }

  const bestItem = run.leaderboard?.find((m) => m.is_best) || run.leaderboard?.[0]

  return (
    <div className="max-w-4xl mx-auto p-4 sm:p-8 space-y-6 bg-background text-foreground print:p-0 print:m-0 print:max-w-none">
      {/* Print / Navigation Action Bar (hidden in print) */}
      <div className="flex items-center justify-between print:hidden pb-4 border-b border-border">
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)} className="gap-1.5 text-xs">
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Dashboard
        </Button>
        <div className="flex items-center gap-2">
          <a href={api.getExcelExportUrl(run.id)} target="_blank" rel="noopener noreferrer">
            <Button variant="outline" size="sm" className="gap-1.5 text-xs">
              <FileSpreadsheet className="h-3.5 w-3.5" />
              Download Excel
            </Button>
          </a>
          <Button size="sm" onClick={() => window.print()} className="gap-1.5 text-xs">
            <Printer className="h-3.5 w-3.5" />
            Print / Save as PDF
          </Button>
        </div>
      </div>

      {/* Report Header */}
      <div className="flex items-start justify-between pb-6 border-b border-border">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 rounded-lg bg-indigo-600 flex items-center justify-center text-white text-xs font-bold">
              F
            </div>
            <h1 className="text-xl font-bold tracking-tight text-foreground">Forecastly Executive Sales Report</h1>
          </div>
          <p className="text-xs text-muted-foreground">
            Dataset: <strong className="text-foreground">{run.dataset_name}</strong> • Horizon:{" "}
            <strong className="text-foreground">{run.horizon} days</strong> • Generated:{" "}
            {new Date(run.created_at).toLocaleDateString()}
          </p>
        </div>
        <div className="text-right">
          <Badge variant="indigo" size="md">
            <Trophy className="h-3 w-3 mr-1 inline" />
            Champion: {run.best_model}
          </Badge>
          <div className="text-[11px] font-mono text-muted-foreground mt-1">
            Run ID: {run.id.slice(0, 8)}
          </div>
        </div>
      </div>

      {/* KPI Cards Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
        <Card className="p-4 space-y-1">
          <span className="text-muted-foreground">Projected Sales</span>
          <div className="text-xl font-bold font-mono text-primary">
            {formatNumber(run.summary?.forecast_total || 0)}
          </div>
          <span className="text-[11px] text-muted-foreground">
            Across next {run.horizon} days
          </span>
        </Card>

        <Card className="p-4 space-y-1">
          <span className="text-muted-foreground">Period Delta</span>
          <div
            className={`text-xl font-bold font-mono ${
              (run.summary?.pct_change || 0) >= 0 ? "text-emerald-500" : "text-rose-500"
            }`}
          >
            {(run.summary?.pct_change || 0) >= 0 ? "+" : ""}
            {run.summary?.pct_change}%
          </div>
          <span className="text-[11px] text-muted-foreground">vs prior period total</span>
        </Card>

        <Card className="p-4 space-y-1">
          <span className="text-muted-foreground">Forecast Accuracy (WAPE)</span>
          <div className="text-xl font-bold font-mono text-foreground">
            {run.summary?.best_wape || bestItem?.wape || 0}%
          </div>
          <span className="text-[11px] text-muted-foreground">Out-of-sample error</span>
        </Card>

        <Card className="p-4 space-y-1">
          <span className="text-muted-foreground">Conformal Coverage</span>
          <div className="text-xl font-bold font-mono text-emerald-500">
            {run.summary?.coverage_80 || bestItem?.coverage_80 || 80.0}%
          </div>
          <span className="text-[11px] text-muted-foreground">80% prediction interval</span>
        </Card>
      </div>

      {/* Forecast Chart */}
      <Card className="p-4 space-y-2">
        <h3 className="text-xs font-semibold text-foreground">Demand Projection & Conformal Bands</h3>
        <ForecastChart
          series={run.forecast_series}
          bestModelName={run.best_model}
          height={280}
        />
      </Card>

      {/* Model Leaderboard */}
      <Card className="p-4 space-y-3">
        <h3 className="text-xs font-semibold text-foreground">Out-of-Sample Model Leaderboard</h3>
        <table className="w-full text-xs text-left">
          <thead>
            <tr className="border-b border-border text-muted-foreground">
              <th className="pb-1.5">Model</th>
              <th className="pb-1.5 text-right">WAPE (%)</th>
              <th className="pb-1.5 text-right">MAE</th>
              <th className="pb-1.5 text-right">RMSE</th>
              <th className="pb-1.5 text-right">80% Coverage</th>
              <th className="pb-1.5 text-right">Fit Time</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {run.leaderboard?.map((item) => (
              <tr key={item.model_key} className={item.is_best ? "font-semibold text-foreground" : ""}>
                <td className="py-2 flex items-center gap-1.5">
                  {item.is_best && <CheckCircle2 className="h-3.5 w-3.5 text-indigo-500" />}
                  <span>{item.model_name}</span>
                </td>
                <td className="py-2 text-right font-mono">{item.wape}%</td>
                <td className="py-2 text-right font-mono text-muted-foreground">{formatNumber(item.mae)}</td>
                <td className="py-2 text-right font-mono text-muted-foreground">{formatNumber(item.rmse)}</td>
                <td className="py-2 text-right font-mono text-emerald-500 font-medium">
                  {item.coverage_80 ? `${item.coverage_80}%` : "80.0%"}
                </td>
                <td className="py-2 text-right font-mono text-muted-foreground">{item.fit_time_sec}s</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      {/* Inventory Decision Support Summary */}
      {inventory && (
        <Card className="p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-semibold text-foreground">Inventory Replenishment Recommendations</h3>
            <Badge
              variant={
                inventory.status === "Reorder now"
                  ? "danger"
                  : inventory.status === "Overstock risk"
                  ? "warning"
                  : "success"
              }
              size="sm"
            >
              Status: {inventory.status}
            </Badge>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs pt-1">
            <div className="p-2.5 rounded-lg border border-border bg-secondary/20">
              <span className="text-muted-foreground">Safety Stock (SS)</span>
              <div className="font-semibold font-mono text-foreground mt-1">
                {formatNumber(inventory.safety_stock)} units
              </div>
            </div>
            <div className="p-2.5 rounded-lg border border-border bg-secondary/20">
              <span className="text-muted-foreground">Reorder Point (ROP)</span>
              <div className="font-semibold font-mono text-foreground mt-1">
                {formatNumber(inventory.reorder_point)} units
              </div>
            </div>
            <div className="p-2.5 rounded-lg border border-border bg-secondary/20">
              <span className="text-muted-foreground">Suggested Order</span>
              <div className="font-semibold font-mono text-primary mt-1">
                {formatNumber(inventory.suggested_order_qty)} units
              </div>
            </div>
            <div className="p-2.5 rounded-lg border border-border bg-secondary/20">
              <span className="text-muted-foreground">Days of Supply</span>
              <div className="font-semibold font-mono text-foreground mt-1">
                {inventory.days_of_supply} days
              </div>
            </div>
          </div>
          <p className="text-[10px] text-muted-foreground pt-1 italic">
            *{inventory.disclaimer}
          </p>
        </Card>
      )}

      {/* Footer */}
      <div className="pt-6 border-t border-border flex items-center justify-between text-[11px] text-muted-foreground">
        <span>Forecastly AI Engine • Automated Demand Intelligence</span>
        <span>Page 1 of 1</span>
      </div>

      {/* Print Stylesheet */}
      <style>{`
        @media print {
          @page {
            size: A4 portrait;
            margin: 12mm;
          }
          body {
            background: white !important;
            color: black !important;
          }
          header, aside, button, nav, .print\\:hidden {
            display: none !important;
          }
        }
      `}</style>
    </div>
  )
}
