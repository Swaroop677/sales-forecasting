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
  coverage_80?: number
  coverage_95?: number
  q_80?: number
  q_95?: number
  coverage_summary?: string
  fit_time_sec: number
  is_best: boolean
}

export interface ForecastPoint {
  date: string
  actual?: number | null
  predicted?: number | null
  models?: Record<string, number>
  lower_80?: number | null
  upper_80?: number | null
  lower_95?: number | null
  upper_95?: number | null
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
  coverage_80?: number
  coverage_95?: number
  q_80?: number
  q_95?: number
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

// ==========================================
// Phase 2: AI Agent Types
// ==========================================
export interface GroundingInfo {
  verified: boolean
  matched_count: number
  unverified_numbers: number[]
  badge_label: string
  disclaimer: string
}

export interface ToolCallItem {
  name: string
  args: Record<string, any>
  result?: Record<string, any>
}

export interface ChatMessage {
  id: string
  session_id?: string
  role: "user" | "assistant" | "system" | "tool"
  content: string
  tool_calls?: ToolCallItem[]
  chart_spec?: Record<string, any> | null
  grounding_info?: GroundingInfo | null
  created_at?: string
  isStreaming?: boolean
}

export interface ChatSession {
  id: string
  title: string
  dataset_id?: string | null
  run_id?: string | null
  created_at: string
  updated_at: string
  messages: ChatMessage[]
}

export interface LLMSettings {
  provider: "gemini" | "openai" | "fallback"
  apiKey: string
  baseUrl: string
  model: string
}

export interface AutopilotResponse {
  status: string
  dataset_name: string
  run_id: string
  validation: Record<string, any>
  cleaning: Record<string, any>
  forecast: Record<string, any>
  executive_summary: {
    outlook: string
    drivers: string
    risks: string
    recommended_actions: string
    confidence: string
  }
  chart_spec?: Record<string, any>
}

export interface ExplainabilityResponse {
  method: "tree_shap" | "feature_importance" | "decomposition"
  selected_date?: string
  base_value?: number
  global_drivers?: Array<{
    feature: string
    mean_abs_impact: number
    importance_pct: number
    category: string
  }>
  local_breakdown?: Array<{
    feature: string
    contribution: number
    direction: "positive" | "negative"
    category: string
  }>
  category_summary?: Array<{
    category: string
    net_impact: number
  }>
  narrative?: string
  // Decomposition specific fields
  dates?: string[]
  actual?: number[]
  trend?: number[]
  seasonal?: number[]
  residual?: number[]
}

export interface SegmentPerformanceResponse {
  season_performance: Array<{
    season: string
    total_sales: number
    avg_daily_sales: number
    volatility_pct: number
    row_count: number
  }>
  month_performance: Array<{
    month_num: number
    month: string
    total_sales: number
    avg_sales: number
    share_pct: number
  }>
  promo_performance: Array<{
    condition: string
    days: number
    avg_daily_sales: number
    total_sales: number
  }>
  promo_lift_pct: number
  group_segments: Array<{
    segment: string
    total_sales: number
    avg_daily_sales: number
    volatility_pct: number
    forecast_error_proxy_wape: number
    status: string
  }>
  worst_segments: Array<{
    segment: string
    total_sales: number
    avg_daily_sales: number
    volatility_pct: number
    forecast_error_proxy_wape: number
    status: string
  }>
  heatmap_matrix: Array<Record<string, any>>
  takeaway: string
}

export interface InventorySupportResponse {
  disclaimer: string
  status: "Reorder now" | "OK" | "Overstock risk"
  status_color: string
  lead_time_days: number
  service_level: string
  z_factor: number
  current_stock: number
  days_of_supply: number
  daily_demand_mean: number
  lead_time_demand: number
  safety_stock: number
  reorder_point: number
  suggested_order_qty: number
  estimated_order_cost: number
  inventory_summary: Array<{
    parameter: string
    value: string
    description: string
  }>
}

export interface DataDriftResponse {
  has_drift: boolean
  overall_status: string
  overall_psi: number
  reference_period?: string
  current_period?: string
  retrain_recommended: boolean
  banner_message?: string | null
  features: Array<{
    feature: string
    is_target: boolean
    psi: number
    ks_statistic: number
    p_value: number
    status: string
    badge: string
    reference_mean: number
    current_mean: number
    mean_shift_pct: number
  }>
}

