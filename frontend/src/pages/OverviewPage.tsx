import React, { useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  ArrowRight,
  BarChart3,
  Database,
  FileSpreadsheet,
  History,
  Sparkles,
  TrendingDown,
  TrendingUp,
  UploadCloud,
} from "lucide-react"
import { toast } from "sonner"
import { api } from "@/api/client"
import { ForecastChart } from "@/components/charts/ForecastChart"
import { Badge } from "@/components/ui/Badge"
import { Button } from "@/components/ui/Button"
import { Card } from "@/components/ui/Card"
import { formatNumber } from "@/lib/utils"
import { Dataset, RunResult } from "@/types"

interface OverviewPageProps {
  currentDataset: Dataset | null
  setCurrentDataset: (d: Dataset) => void
  latestRun: RunResult | null
  isLoadingLatestRun?: boolean
}

export const OverviewPage: React.FC<OverviewPageProps> = ({
  currentDataset,
  setCurrentDataset,
  latestRun,
}) => {
  const navigate = useNavigate()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [isDragging, setIsDragging] = useState(false)

  const handleSampleData = async () => {
    try {
      setIsUploading(true)
      const ds = await api.createSampleDataset()
      setCurrentDataset(ds)
      toast.success("Loaded realistic retail sample dataset (3 stores × 5 products)!")
    } catch (e: any) {
      toast.error(e.message || "Failed to load sample dataset")
    } finally {
      setIsUploading(false)
    }
  }

  const handleFileUpload = async (file: File) => {
    if (!file) return
    try {
      setIsUploading(true)
      const ds = await api.uploadDataset(file)
      setCurrentDataset(ds)
      toast.success(`Uploaded ${file.name} successfully!`)
      navigate("/data")
    } catch (e: any) {
      toast.error(e.message || "Failed to upload dataset")
    } finally {
      setIsUploading(false)
    }
  }

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0])
    }
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Top Banner / Welcome */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Sales Forecasting Studio</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Automated ML forecasting, backtesting, and model leaderboard comparison in 3 clicks.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          {currentDataset && (
            <Button variant="outline" size="sm" onClick={() => navigate("/forecast")}>
              <BarChart3 className="h-4 w-4 mr-1.5" />
              Forecast Studio
            </Button>
          )}
          <Button
            variant="primary"
            size="sm"
            onClick={handleSampleData}
            isLoading={isUploading}
          >
            <Sparkles className="h-4 w-4 mr-1.5" />
            Try Sample Data
          </Button>
        </div>
      </div>

      {/* Hero Upload Card (if no dataset or user wants to upload) */}
      {!currentDataset && (
        <Card className="border-dashed border-2 border-primary/20 bg-primary/[0.02] p-10 text-center">
          <div
            onDragOver={(e) => {
              e.preventDefault()
              setIsDragging(true)
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={onDrop}
            className={`max-w-md mx-auto flex flex-col items-center justify-center p-6 rounded-2xl transition-all ${
              isDragging ? "bg-primary/10 border-primary" : ""
            }`}
          >
            <div className="h-16 w-16 rounded-2xl bg-primary/10 text-primary flex items-center justify-center mb-4">
              <UploadCloud className="h-8 w-8" />
            </div>

            <h2 className="text-lg font-semibold text-foreground">Upload your historical sales data</h2>
            <p className="text-xs text-muted-foreground mt-1.5 mb-6 text-center leading-relaxed">
              Drag & drop CSV or Excel file here, or click to browse. Max 10 MB / 200,000 rows.
              Dates, products, and metrics are auto-detected.
            </p>

            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.xlsx,.xls"
              className="hidden"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  handleFileUpload(e.target.files[0])
                }
              }}
            />

            <div className="flex flex-col sm:flex-row gap-3 w-full justify-center">
              <Button
                variant="primary"
                onClick={() => fileInputRef.current?.click()}
                isLoading={isUploading}
              >
                <FileSpreadsheet className="h-4 w-4 mr-2" />
                Select CSV / Excel File
              </Button>
              <Button
                variant="secondary"
                onClick={handleSampleData}
                isLoading={isUploading}
              >
                <Sparkles className="h-4 w-4 mr-2" />
                Use Sample Data
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* KPI Summary Cards (When a forecast run is available) */}
      {latestRun && latestRun.summary && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="p-5">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Last Period Actual
            </span>
            <div className="text-2xl font-bold tracking-tight text-foreground mt-1 tabular-nums">
              {formatNumber(latestRun.summary.last_period_total, 0)}
            </div>
            <span className="text-xs text-muted-foreground mt-1 block">
              Prior {latestRun.summary.horizon} days sales
            </span>
          </Card>

          <Card className="p-5">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Forecast Total
            </span>
            <div className="text-2xl font-bold tracking-tight text-indigo-600 dark:text-indigo-400 mt-1 tabular-nums">
              {formatNumber(latestRun.summary.forecast_total, 0)}
            </div>
            <span className="text-xs text-muted-foreground mt-1 block">
              Next {latestRun.summary.horizon} days projected
            </span>
          </Card>

          <Card className="p-5">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Projected Change
            </span>
            <div className="flex items-center gap-2 mt-1">
              <div
                className={`text-2xl font-bold tracking-tight tabular-nums ${
                  latestRun.summary.pct_change >= 0
                    ? "text-emerald-600 dark:text-emerald-400"
                    : "text-rose-600 dark:text-rose-400"
                }`}
              >
                {latestRun.summary.pct_change >= 0 ? "+" : ""}
                {latestRun.summary.pct_change}%
              </div>
              <Badge
                variant={latestRun.summary.pct_change >= 0 ? "success" : "danger"}
                size="sm"
              >
                {latestRun.summary.pct_change >= 0 ? (
                  <TrendingUp className="h-3 w-3 mr-1 inline" />
                ) : (
                  <TrendingDown className="h-3 w-3 mr-1 inline" />
                )}
                vs prior
              </Badge>
            </div>
            <span className="text-xs text-muted-foreground mt-1 block">
              Volume trajectory shift
            </span>
          </Card>

          <Card className="p-5">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Winning Model
            </span>
            <div className="text-xl font-bold tracking-tight text-foreground mt-1 truncate">
              {latestRun.summary.best_model}
            </div>
            <div className="flex items-center gap-1.5 mt-1">
              <Badge variant="indigo" size="sm">
                WAPE: {latestRun.summary.best_wape}%
              </Badge>
              <span className="text-xs text-muted-foreground">lowest error</span>
            </div>
          </Card>
        </div>
      )}

      {/* Main Forecast Chart Card */}
      {latestRun && latestRun.forecast_series && latestRun.forecast_series.length > 0 && (
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-border">
            <div>
              <h2 className="text-base font-semibold text-foreground">Sales Forecast Overview</h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Historical trend and automated forward-looking projection by {latestRun.best_model}.
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate("/forecast")}
            >
              Configure & Backtest
              <ArrowRight className="h-3.5 w-3.5 ml-1.5" />
            </Button>
          </div>

          <ForecastChart
            series={latestRun.forecast_series}
            backtestOverlay={latestRun.backtest_overlay}
            bestModelName={latestRun.best_model}
            height={380}
          />
        </Card>
      )}

      {/* Quick Launchpad when Dataset exists but no forecast yet */}
      {currentDataset && !latestRun && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card hoverable onClick={() => navigate("/data")} className="p-6">
            <div className="h-10 w-10 rounded-xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center mb-4">
              <Database className="h-5 w-5" />
            </div>
            <h3 className="font-semibold text-sm text-foreground">1. Inspect & Clean Data</h3>
            <p className="text-xs text-muted-foreground mt-1.5 leading-relaxed">
              Verify detected dates, target metrics, group categories, and execute automated quality fixes.
            </p>
            <div className="flex items-center text-xs font-medium text-primary mt-4">
              View data quality report <ArrowRight className="h-3.5 w-3.5 ml-1" />
            </div>
          </Card>

          <Card hoverable onClick={() => navigate("/forecast")} className="p-6">
            <div className="h-10 w-10 rounded-xl bg-violet-500/10 text-violet-600 dark:text-violet-400 flex items-center justify-center mb-4">
              <BarChart3 className="h-5 w-5" />
            </div>
            <h3 className="font-semibold text-sm text-foreground">2. Train & Backtest Models</h3>
            <p className="text-xs text-muted-foreground mt-1.5 leading-relaxed">
              Compare Seasonal Naive, Holt-Winters, LightGBM, and XGBoost using rolling-origin cross-validation.
            </p>
            <div className="flex items-center text-xs font-medium text-primary mt-4">
              Launch forecast studio <ArrowRight className="h-3.5 w-3.5 ml-1" />
            </div>
          </Card>

          <Card hoverable onClick={() => navigate("/runs")} className="p-6">
            <div className="h-10 w-10 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mb-4">
              <History className="h-5 w-5" />
            </div>
            <h3 className="font-semibold text-sm text-foreground">3. Model Registry & Audit</h3>
            <p className="text-xs text-muted-foreground mt-1.5 leading-relaxed">
              Access serialized models (joblib), compare historical runs, and download forecasts as CSV.
            </p>
            <div className="flex items-center text-xs font-medium text-primary mt-4">
              View run registry <ArrowRight className="h-3.5 w-3.5 ml-1" />
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}
