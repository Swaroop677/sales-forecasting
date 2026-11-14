export interface QualityIssue {
  id: string
  column?: string
  issue_type: string
  severity: "critical" | "warning" | "info"
  count: number
  percentage: number
  message: string
  suggested_fix: string
}

export interface QualityReport {
  is_valid: boolean
  frequency: string
  total_rows: number
  date_range: {
    start: string
    end: string
    unique_dates: number
  }
  target_summary: {
    mean: number
    std: number
    min: number
    max: number
    median: number
    zero_count: number
  }
  issues: QualityIssue[]
  score: number
}

export interface AuditLogEntry {
  action: string
  timestamp: string
  rows_affected: number
  details: string
}

export interface Dataset {
  id: string
  name: string
  file_hash: string
  row_count: number
  col_count: number
  date_col: string
  target_col: string
  group_cols: string[]
  regressor_cols: string[]
  frequency: string
  quality_report?: QualityReport
  audit_log: AuditLogEntry[]
  created_at: string
  updated_at: string
}

export interface DatasetPreview {
  columns: string[]
  dtypes: Record<string, string>
  total_rows: number
  page: number
  page_size: number
  rows: Record<string, any>[]
}

export interface SeriesOption {
  id: string
  name: string
  row_count: number
  date_start: string
  date_end: string
}

export interface ColumnMappingUpdate {
  date_col: string
  target_col: string
  group_cols: string[]
  regressor_cols: string[]
}

export interface LeaderboardItem {
  model_key: string
  model_name: string
  mae: number
  rmse: number
  wape: number
  smape: number
  mase: number
  fit_time_sec: number
  is_best: boolean
}

export interface ForecastPoint {
  date: string
  actual?: number | null
  predicted?: number | null
  models?: Record<string, number>
  lower_bound?: number | null
  upper_bound?: number | null
}

export interface BacktestPoint {
  date: string
  actual: number
  predictions: Record<string, number>
}

export interface ForecastSummary {
  last_period_total: number
  forecast_total: number
  pct_change: number
  best_model: string
  best_wape: number
  horizon: number
  n_folds: number
}

export interface RunResult {
  id: string
  dataset_id: string
  dataset_name: string
  series_id: string
  horizon: number
  metric: string
  status: "pending" | "running" | "completed" | "failed"
  best_model?: string
  leaderboard: LeaderboardItem[]
  fold_metrics: any[]
  forecast_series: ForecastPoint[]
  backtest_overlay: BacktestPoint[]
  summary: ForecastSummary
  created_at: string
  completed_at?: string
}

export interface RunStatus {
  id: string
  dataset_id: string
  dataset_name: string
  series_id: string
  status: "pending" | "running" | "completed" | "failed"
  progress: number
  current_step: string
  error_message?: string
  created_at: string
  completed_at?: string
}

export interface RunSummary {
  id: string
  dataset_id: string
  dataset_name: string
  series_id: string
  horizon: number
  status: string
  best_model?: string
  best_wape?: number
  created_at: string
  completed_at?: string
}

export interface ModelOption {
  id: string
  name: string
  category: string
  description: string
  is_default: boolean
}
