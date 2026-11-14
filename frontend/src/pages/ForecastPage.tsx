import React, { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  BarChart3,
  ChevronDown,
  ChevronUp,
  Download,
  HelpCircle,
  Play,
  Sparkles,
  Trophy,
} from "lucide-react"
import { toast } from "sonner"
import { api } from "@/api/client"
import { ForecastChart } from "@/components/charts/ForecastChart"
import { Badge } from "@/components/ui/Badge"
import { Button } from "@/components/ui/Button"
import { Card } from "@/components/ui/Card"
import { Progress } from "@/components/ui/Progress"
import { Tooltip } from "@/components/ui/Tooltip"
import { formatNumber } from "@/lib/utils"
import { Dataset, ModelOption, RunResult, RunStatus, SeriesOption } from "@/types"

interface ForecastPageProps {
  currentDataset: Dataset | null
  activeRun: RunResult | null
  setActiveRun: (run: RunResult | null) => void
}

export const ForecastPage: React.FC<ForecastPageProps> = ({
  currentDataset,
  activeRun,
  setActiveRun,
}) => {
  const navigate = useNavigate()

  // Form parameters
  const [selectedSeries, setSelectedSeries] = useState("all")
  const [seriesList, setSeriesList] = useState<SeriesOption[]>([])
  const [horizon, setHorizon] = useState(30)
  const [availableModels, setAvailableModels] = useState<ModelOption[]>([])
  const [selectedModels, setSelectedModels] = useState<string[]>([
    "seasonal_naive",
    "holt_winters",
    "lightgbm",
    "xgboost",
  ])

  // Advanced settings
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [nFolds, setNFolds] = useState(3)
  const [targetMetric, setTargetMetric] = useState("wape")

  // Job execution state
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [currentJob, setCurrentJob] = useState<RunStatus | null>(null)

  useEffect(() => {
    // Fetch models
    api.getModels().then(setAvailableModels).catch(() => {})

    // Fetch series for active dataset
    if (currentDataset) {
      api.getSeries(currentDataset.id).then(setSeriesList).catch(() => {})
    }
  }, [currentDataset?.id])

  // Polling loop for active job
  useEffect(() => {
    let timer: NodeJS.Timeout
    if (currentJob && (currentJob.status === "pending" || currentJob.status === "running")) {
      timer = setTimeout(async () => {
        try {
          const status = await api.getRunStatus(currentJob.id)
          setCurrentJob(status)
          if (status.status === "completed") {
            const result = await api.getRunResult(status.id)
            setActiveRun(result)
            toast.success(`Forecast completed! Winning model: ${result.best_model}`)
          } else if (status.status === "failed") {
            toast.error(status.error_message || "Forecasting job failed")
          }
        } catch (e: any) {
          toast.error(e.message || "Failed to poll job status")
        }
      }, 1000)
    }
    return () => clearTimeout(timer)
  }, [currentJob?.id, currentJob?.status])

  const handleStartForecast = async () => {
    if (!currentDataset) {
      toast.error("Please select or upload a dataset first")
      return
    }

    if (selectedModels.length === 0) {
      toast.error("Please select at least one forecasting model")
      return
    }

    try {
      setIsSubmitting(true)
      const job = await api.createRun({
        dataset_id: currentDataset.id,
        series_id: selectedSeries,
        horizon,
        models: selectedModels,
        n_folds: nFolds,
        metric: targetMetric,
      })
      setCurrentJob(job)
      toast.info("Enqueued forecast job. Running expanding-window backtesting...")
    } catch (e: any) {
      toast.error(e.message || "Failed to start forecast")
    } finally {
      setIsSubmitting(false)
    }
  }

  const toggleModel = (id: string) => {
    if (selectedModels.includes(id)) {
      if (selectedModels.length === 1) {
        toast.warning("Keep at least one model selected")
        return
      }
      setSelectedModels(selectedModels.filter((m) => m !== id))
    } else {
      setSelectedModels([...selectedModels, id])
    }
  }

  if (!currentDataset) {
    return (
      <Card className="p-12 text-center max-w-lg mx-auto mt-12">
        <BarChart3 className="h-12 w-12 text-muted-foreground mx-auto mb-4 opacity-50" />
        <h2 className="text-lg font-semibold text-foreground">No Dataset Selected</h2>
        <p className="text-xs text-muted-foreground mt-1.5 mb-6">
          Upload historical data or click sample data to launch automated forecasting.
        </p>
        <Button variant="primary" onClick={() => navigate("/")}>
          <Sparkles className="h-4 w-4 mr-2" />
          Load Data
        </Button>
      </Card>
    )
  }

  const isRunning = currentJob && (currentJob.status === "pending" || currentJob.status === "running")

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Forecast Studio</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Configure series, horizon, and candidate algorithms. Automatically validated with rolling backtests.
          </p>
        </div>

        {activeRun && activeRun.status === "completed" && (
          <div className="flex items-center gap-3">
            <a href={api.getDownloadUrl(activeRun.id)} download>
              <Button variant="outline" size="sm">
                <Download className="h-4 w-4 mr-1.5" />
                Download Forecast (CSV)
              </Button>
            </a>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Config Panel (4 cols) */}
        <Card className="lg:col-span-4 p-6 space-y-6">
          <h2 className="text-base font-semibold text-foreground border-b border-border pb-3">
            Forecast Configuration
          </h2>

          {/* Series Picker */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-foreground block">Series / Target Aggregation</label>
            <select
              value={selectedSeries}
              onChange={(e) => setSelectedSeries(e.target.value)}
              className="w-full bg-secondary border border-border rounded-xl px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            >
              {seriesList.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.row_count} rows)
                </option>
              ))}
            </select>
          </div>

          {/* Horizon Presets */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-foreground block">Forecast Horizon (Days)</label>
            <div className="grid grid-cols-4 gap-1.5">
              {[7, 14, 30, 90].map((h) => (
                <button
                  key={h}
                  type="button"
                  onClick={() => setHorizon(h)}
                  className={`py-1.5 text-xs font-medium rounded-xl border transition-all ${
                    horizon === h
                      ? "bg-primary text-primary-foreground border-primary"
                      : "bg-secondary/60 text-muted-foreground border-border hover:text-foreground"
                  }`}
                >
                  {h}d
                </button>
              ))}
            </div>
            <input
              type="number"
              min="1"
              max="365"
              value={horizon}
              onChange={(e) => setHorizon(Math.max(1, parseInt(e.target.value) || 1))}
              className="w-full mt-2 bg-secondary border border-border rounded-xl px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          {/* Model Selection */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-foreground">Candidate Models</label>
              <span className="text-[11px] text-muted-foreground">{selectedModels.length} selected</span>
            </div>

            <div className="space-y-1.5">
              {availableModels.map((m) => (
                <div
                  key={m.id}
                  onClick={() => toggleModel(m.id)}
                  className={`p-2.5 rounded-xl border cursor-pointer transition-all flex items-start gap-2.5 ${
                    selectedModels.includes(m.id)
                      ? "bg-primary/5 border-primary/40 text-foreground"
                      : "bg-secondary/30 border-border text-muted-foreground opacity-75"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedModels.includes(m.id)}
                    onChange={() => {}}
                    className="mt-0.5 rounded text-primary focus:ring-primary pointer-events-none"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-foreground">{m.name}</span>
                      <span className="text-[10px] text-muted-foreground uppercase">{m.category}</span>
                    </div>
                    <p className="text-[11px] text-muted-foreground truncate mt-0.5">{m.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Collapsible Advanced Settings */}
          <div className="border-t border-border pt-4">
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center justify-between w-full text-xs font-medium text-muted-foreground hover:text-foreground"
            >
              <span>Advanced Backtest Settings</span>
              {showAdvanced ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>

            {showAdvanced && (
              <div className="mt-3 space-y-3 pt-2 text-xs">
                <div>
                  <label className="block text-muted-foreground mb-1">
                    Expanding Backtest Folds: <span className="font-semibold text-foreground">{nFolds}</span>
                  </label>
                  <input
                    type="range"
                    min="2"
                    max="5"
                    value={nFolds}
                    onChange={(e) => setNFolds(parseInt(e.target.value))}
                    className="w-full accent-primary"
                  />
                </div>

                <div>
                  <label className="block text-muted-foreground mb-1">Winning Model Metric</label>
                  <select
                    value={targetMetric}
                    onChange={(e) => setTargetMetric(e.target.value)}
                    className="w-full bg-secondary border border-border rounded-xl px-2.5 py-1.5 text-xs text-foreground"
                  >
                    <option value="wape">WAPE (Weighted Absolute % Error - Recommended)</option>
                    <option value="mae">MAE (Mean Absolute Error)</option>
                    <option value="rmse">RMSE (Root Mean Squared Error)</option>
                    <option value="smape">sMAPE (Symmetric MAPE)</option>
                    <option value="mase">MASE (Mean Absolute Scaled Error)</option>
                  </select>
                </div>
              </div>
            )}
          </div>

          {/* Launch Forecast Primary Action */}
          <Button
            variant="primary"
            size="lg"
            className="w-full"
            onClick={handleStartForecast}
            isLoading={Boolean(isSubmitting || isRunning)}
          >
            <Play className="h-4 w-4 mr-2 fill-current" />
            {isRunning ? "Backtesting & Forecasting..." : "Run Forecast"}
          </Button>
        </Card>

        {/* Right Results Panel (8 cols) */}
        <div className="lg:col-span-8 space-y-6">
          {/* Progress Stepper Banner (When job is executing) */}
          {isRunning && (
            <Card className="p-6 border-primary/30 bg-primary/[0.02] space-y-4 animate-in fade-in">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="h-2.5 w-2.5 rounded-full bg-primary animate-ping" />
                  <span className="text-sm font-semibold text-foreground">
                    {currentJob.current_step}
                  </span>
                </div>
                <span className="text-xs font-mono font-medium text-primary">
                  {currentJob.progress}%
                </span>
              </div>

              <Progress value={currentJob.progress} />

              {/* Step pills */}
              <div className="grid grid-cols-4 gap-2 text-center text-[11px] pt-1">
                <span className={currentJob.progress >= 10 ? "font-semibold text-primary" : "text-muted-foreground"}>
                  1. Validate
                </span>
                <span className={currentJob.progress >= 25 ? "font-semibold text-primary" : "text-muted-foreground"}>
                  2. Train Models
                </span>
                <span className={currentJob.progress >= 60 ? "font-semibold text-primary" : "text-muted-foreground"}>
                  3. Backtest Folds
                </span>
                <span className={currentJob.progress >= 90 ? "font-semibold text-primary" : "text-muted-foreground"}>
                  4. Forecast Horizon
                </span>
              </div>
            </Card>
          )}

          {/* Forecast Chart */}
          {activeRun && activeRun.forecast_series && activeRun.forecast_series.length > 0 ? (
            <Card className="p-6">
              <div className="flex items-center justify-between mb-4 pb-3 border-b border-border">
                <div>
                  <h2 className="text-base font-semibold text-foreground">
                    Forecast Timeline: {activeRun.dataset_name}
                  </h2>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Series: {activeRun.series_id === "all" ? "Combined Total" : activeRun.series_id} •{" "}
                    Horizon: {activeRun.horizon} days
                  </p>
                </div>
                {activeRun.best_model && (
                  <Badge variant="indigo" size="md">
                    <Trophy className="h-3 w-3 mr-1 inline" />
                    Winner: {activeRun.best_model}
                  </Badge>
                )}
              </div>

              <ForecastChart
                series={activeRun.forecast_series}
                backtestOverlay={activeRun.backtest_overlay}
                bestModelName={activeRun.best_model}
                height={400}
              />
            </Card>
          ) : !isRunning ? (
            <Card className="p-12 text-center">
              <BarChart3 className="h-10 w-10 text-muted-foreground mx-auto mb-3 opacity-40" />
              <h3 className="font-semibold text-sm text-foreground">Ready to Forecast</h3>
              <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
                Configure your horizon on the left and click "Run Forecast" to automatically backtest candidate models.
              </p>
            </Card>
          ) : null}

          {/* Model Leaderboard */}
          {activeRun && activeRun.leaderboard && activeRun.leaderboard.length > 0 && (
            <Card className="p-0 overflow-hidden">
              <div className="p-4 border-b border-border flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-foreground">Model Leaderboard</h3>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Evaluated across {activeRun.summary?.n_folds || 3} expanding test folds without data leakage.
                  </p>
                </div>
                <Badge variant="outline" size="sm">
                  Ranked by {activeRun.metric.toUpperCase()}
                </Badge>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead>
                    <tr className="bg-secondary/60 border-b border-border text-foreground font-semibold">
                      <th className="p-3">Rank / Model</th>
                      <th className="p-3 text-right">
                        <Tooltip content="Weighted Absolute Percentage Error (lower is better). Standard retail metric.">
                          <span className="cursor-help inline-flex items-center gap-1">
                            WAPE <HelpCircle className="h-3 w-3 text-muted-foreground" />
                          </span>
                        </Tooltip>
                      </th>
                      <th className="p-3 text-right">
                        <Tooltip content="Mean Absolute Error in native sales units (lower is better).">
                          <span className="cursor-help inline-flex items-center gap-1">
                            MAE <HelpCircle className="h-3 w-3 text-muted-foreground" />
                          </span>
                        </Tooltip>
                      </th>
                      <th className="p-3 text-right">
                        <Tooltip content="Root Mean Squared Error (penalizes large spike mistakes).">
                          <span className="cursor-help inline-flex items-center gap-1">
                            RMSE <HelpCircle className="h-3 w-3 text-muted-foreground" />
                          </span>
                        </Tooltip>
                      </th>
                      <th className="p-3 text-right">
                        <Tooltip content="Symmetric Mean Absolute Percentage Error (0% to 200%).">
                          <span className="cursor-help inline-flex items-center gap-1">
                            sMAPE <HelpCircle className="h-3 w-3 text-muted-foreground" />
                          </span>
                        </Tooltip>
                      </th>
                      <th className="p-3 text-right">
                        <Tooltip content="Mean Absolute Scaled Error vs Seasonal Naive benchmark (< 1 is superior).">
                          <span className="cursor-help inline-flex items-center gap-1">
                            MASE <HelpCircle className="h-3 w-3 text-muted-foreground" />
                          </span>
                        </Tooltip>
                      </th>
                      <th className="p-3 text-right">Fit Time</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {activeRun.leaderboard.map((item, idx) => (
                      <tr
                        key={item.model_key}
                        className={`transition-colors ${
                          item.is_best ? "bg-primary/[0.04] font-medium" : "hover:bg-secondary/30"
                        }`}
                      >
                        <td className="p-3">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-muted-foreground w-4">{idx + 1}</span>
                            <span className="text-foreground">{item.model_name}</span>
                            {item.is_best && (
                              <Badge variant="indigo" size="sm">
                                Best
                              </Badge>
                            )}
                          </div>
                        </td>
                        <td className="p-3 text-right font-mono tabular-nums text-foreground">
                          {item.wape}%
                        </td>
                        <td className="p-3 text-right font-mono tabular-nums text-muted-foreground">
                          {formatNumber(item.mae)}
                        </td>
                        <td className="p-3 text-right font-mono tabular-nums text-muted-foreground">
                          {formatNumber(item.rmse)}
                        </td>
                        <td className="p-3 text-right font-mono tabular-nums text-muted-foreground">
                          {item.smape}%
                        </td>
                        <td className="p-3 text-right font-mono tabular-nums text-muted-foreground">
                          {item.mase}
                        </td>
                        <td className="p-3 text-right font-mono tabular-nums text-muted-foreground">
                          {item.fit_time_sec}s
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
