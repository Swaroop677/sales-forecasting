import React, { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  ArrowRight,
  Columns,
  Download,
  History,
  Sparkles,
  Trophy,
} from "lucide-react"
import { toast } from "sonner"
import { api } from "@/api/client"
import { Badge } from "@/components/ui/Badge"
import { Button } from "@/components/ui/Button"
import { Card } from "@/components/ui/Card"
import { Dialog } from "@/components/ui/Dialog"
import { Skeleton } from "@/components/ui/Skeleton"
import { RunResult, RunSummary } from "@/types"

interface RunsPageProps {
  onSelectRun: (run: RunResult) => void
}

export const RunsPage: React.FC<RunsPageProps> = ({ onSelectRun }) => {
  const navigate = useNavigate()
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)

  // Comparison State
  const [selectedRunIds, setSelectedRunIds] = useState<string[]>([])
  const [compareData, setCompareData] = useState<{ run1: RunResult; run2: RunResult } | null>(null)
  const [isCompareOpen, setIsCompareOpen] = useState(false)
  const [isComparing, setIsComparing] = useState(false)

  const loadRuns = async () => {
    try {
      setIsLoading(true)
      const list = await api.listRuns()
      setRuns(list)
    } catch (e: any) {
      toast.error(e.message || "Failed to load runs history")
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadRuns()
  }, [])

  const handleReopen = async (runId: string) => {
    try {
      const fullResult = await api.getRunResult(runId)
      onSelectRun(fullResult)
      navigate("/forecast")
      toast.success(`Loaded run ${runId.slice(0, 8)} into Forecast Studio`)
    } catch (e: any) {
      toast.error(e.message || "Failed to load run details")
    }
  }

  const toggleSelectForCompare = (id: string) => {
    if (selectedRunIds.includes(id)) {
      setSelectedRunIds(selectedRunIds.filter((r) => r !== id))
    } else {
      if (selectedRunIds.length >= 2) {
        setSelectedRunIds([selectedRunIds[1], id])
      } else {
        setSelectedRunIds([...selectedRunIds, id])
      }
    }
  }

  const handleOpenCompare = async () => {
    if (selectedRunIds.length !== 2) {
      toast.warning("Please select exactly 2 runs to compare side by side")
      return
    }
    try {
      setIsComparing(true)
      const [r1, r2] = await Promise.all([
        api.getRunResult(selectedRunIds[0]),
        api.getRunResult(selectedRunIds[1]),
      ])
      setCompareData({ run1: r1, run2: r2 })
      setIsCompareOpen(true)
    } catch (e: any) {
      toast.error(e.message || "Failed to load comparison data")
    } finally {
      setIsComparing(false)
    }
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Model Run Registry</h1>
          <p className="text-sm text-muted-foreground mt-1">
            "MLflow-lite" in-process registry tracking backtests, performance metrics, and joblib artifacts.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          {selectedRunIds.length === 2 && (
            <Button
              variant="primary"
              size="sm"
              onClick={handleOpenCompare}
              isLoading={isComparing}
            >
              <Columns className="h-4 w-4 mr-1.5" />
              Compare Selected Runs (2)
            </Button>
          )}
        </div>
      </div>

      {/* Runs Table */}
      <Card className="p-0 overflow-hidden">
        <div className="p-4 border-b border-border flex items-center justify-between">
          <h3 className="text-sm font-semibold text-foreground">Historical Forecast Runs</h3>
          <span className="text-xs text-muted-foreground">
            {selectedRunIds.length > 0
              ? `${selectedRunIds.length} of 2 selected for comparison`
              : "Select 2 runs to compare side by side"}
          </span>
        </div>

        {isLoading ? (
          <div className="p-6 space-y-3">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
          </div>
        ) : runs.length === 0 ? (
          <div className="p-12 text-center">
            <History className="h-10 w-10 text-muted-foreground mx-auto mb-3 opacity-40" />
            <h4 className="font-semibold text-sm text-foreground">No Historical Runs Found</h4>
            <p className="text-xs text-muted-foreground mt-1 mb-4">
              Train your first forecasting model to populate the registry.
            </p>
            <Button variant="primary" size="sm" onClick={() => navigate("/forecast")}>
              <Sparkles className="h-3.5 w-3.5 mr-1.5" />
              Launch Forecast Studio
            </Button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="bg-secondary/60 border-b border-border text-foreground font-semibold">
                  <th className="p-3 w-10 text-center">Select</th>
                  <th className="p-3">Run ID / Created</th>
                  <th className="p-3">Dataset Name</th>
                  <th className="p-3">Series</th>
                  <th className="p-3">Horizon</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Winning Model</th>
                  <th className="p-3 text-right">Best WAPE</th>
                  <th className="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {runs.map((r) => {
                  const isChecked = selectedRunIds.includes(r.id)
                  return (
                    <tr
                      key={r.id}
                      className={`hover:bg-secondary/30 transition-colors ${
                        isChecked ? "bg-primary/[0.04]" : ""
                      }`}
                    >
                      <td className="p-3 text-center">
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => toggleSelectForCompare(r.id)}
                          className="rounded border-border text-primary focus:ring-primary h-3.5 w-3.5"
                        />
                      </td>

                      <td className="p-3">
                        <span className="font-mono font-medium text-foreground block">
                          {r.id.slice(0, 8)}
                        </span>
                        <span className="text-[10px] text-muted-foreground">
                          {new Date(r.created_at).toLocaleString()}
                        </span>
                      </td>

                      <td className="p-3 font-medium text-foreground max-w-[150px] truncate">
                        {r.dataset_name}
                      </td>

                      <td className="p-3 text-muted-foreground">
                        {r.series_id === "all" ? "Combined Total" : r.series_id}
                      </td>

                      <td className="p-3 text-muted-foreground font-mono">
                        {r.horizon}d
                      </td>

                      <td className="p-3">
                        <Badge
                          variant={
                            r.status === "completed"
                              ? "success"
                              : r.status === "failed"
                              ? "danger"
                              : "warning"
                          }
                          size="sm"
                        >
                          {r.status}
                        </Badge>
                      </td>

                      <td className="p-3">
                        {r.best_model ? (
                          <span className="font-medium text-foreground inline-flex items-center gap-1">
                            <Trophy className="h-3 w-3 text-amber-500" />
                            {r.best_model}
                          </span>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </td>

                      <td className="p-3 text-right font-mono font-semibold text-foreground">
                        {r.best_wape !== null && r.best_wape !== undefined
                          ? `${r.best_wape}%`
                          : "—"}
                      </td>

                      <td className="p-3 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {r.status === "completed" && (
                            <a
                              href={api.getDownloadUrl(r.id)}
                              download
                              title="Download Forecast CSV"
                              className="p-1.5 rounded-lg text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
                            >
                              <Download className="h-3.5 w-3.5" />
                            </a>
                          )}
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleReopen(r.id)}
                          >
                            Open
                            <ArrowRight className="h-3 w-3 ml-1" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Side-by-Side Run Comparison Dialog */}
      <Dialog
        open={isCompareOpen}
        onClose={() => setIsCompareOpen(false)}
        title="Side-by-Side Model Comparison"
        description="Detailed comparison of backtest accuracy metrics and predictions between two historical runs."
        className="max-w-3xl"
      >
        {compareData && (
          <div className="space-y-6 text-xs">
            {/* Top comparison cards */}
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 rounded-xl border border-border bg-secondary/30 space-y-2">
                <div className="flex items-center justify-between">
                  <Badge variant="indigo" size="sm">Run A ({compareData.run1.id.slice(0, 8)})</Badge>
                  <span className="font-mono text-muted-foreground">
                    Horizon: {compareData.run1.horizon}d
                  </span>
                </div>
                <div className="font-semibold text-sm text-foreground">
                  Winner: {compareData.run1.best_model}
                </div>
                <div className="text-muted-foreground">
                  Dataset: {compareData.run1.dataset_name} ({compareData.run1.series_id})
                </div>
              </div>

              <div className="p-4 rounded-xl border border-border bg-secondary/30 space-y-2">
                <div className="flex items-center justify-between">
                  <Badge variant="indigo" size="sm">Run B ({compareData.run2.id.slice(0, 8)})</Badge>
                  <span className="font-mono text-muted-foreground">
                    Horizon: {compareData.run2.horizon}d
                  </span>
                </div>
                <div className="font-semibold text-sm text-foreground">
                  Winner: {compareData.run2.best_model}
                </div>
                <div className="text-muted-foreground">
                  Dataset: {compareData.run2.dataset_name} ({compareData.run2.series_id})
                </div>
              </div>
            </div>

            {/* Leaderboard comparison */}
            <div>
              <h4 className="font-semibold text-sm text-foreground mb-2">Model Leaderboard Metrics</h4>
              <div className="grid grid-cols-2 gap-4">
                <div className="border border-border rounded-xl p-3 bg-card">
                  <span className="font-semibold text-primary block mb-2">Run A Leaderboard</span>
                  <div className="space-y-2">
                    {compareData.run1.leaderboard.map((m) => (
                      <div key={m.model_key} className="flex justify-between border-b border-border/40 pb-1">
                        <span className="text-foreground">{m.model_name} {m.is_best && "⭐"}</span>
                        <span className="font-mono text-muted-foreground">WAPE: {m.wape}%</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="border border-border rounded-xl p-3 bg-card">
                  <span className="font-semibold text-primary block mb-2">Run B Leaderboard</span>
                  <div className="space-y-2">
                    {compareData.run2.leaderboard.map((m) => (
                      <div key={m.model_key} className="flex justify-between border-b border-border/40 pb-1">
                        <span className="text-foreground">{m.model_name} {m.is_best && "⭐"}</span>
                        <span className="font-mono text-muted-foreground">WAPE: {m.wape}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <div className="flex justify-end pt-3 border-t border-border">
              <Button variant="outline" size="sm" onClick={() => setIsCompareOpen(false)}>
                Close Comparison
              </Button>
            </div>
          </div>
        )}
      </Dialog>
    </div>
  )
}
