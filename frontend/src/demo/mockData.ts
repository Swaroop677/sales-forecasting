import {
  AuditLogEntry,
  Dataset,
  ExplainabilityResponse,
  ForecastPoint,
  InventorySupportResponse,
  QualityReport,
  RunResult,
} from "@/types"

export const MOCK_DATASET: Dataset = {
  id: "demo-dataset-retail",
  name: "Retail Sales (Precomputed Demo)",
  file_hash: "demo-hash-123456",
  row_count: 5475,
  col_count: 6,
  date_col: "date",
  target_col: "sales",
  group_cols: ["store", "product"],
  regressor_cols: ["promo", "price"],
  frequency: "D",
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  quality_report: {
    is_valid: true,
    frequency: "D",
    total_rows: 5475,
    date_range: {
      start: "2021-01-01",
      end: "2023-12-31",
      unique_dates: 1095,
    },
    target_summary: {
      mean: 140.5,
      std: 24.2,
      min: 15.0,
      max: 380.0,
      median: 138.0,
      zero_count: 0,
    },
    issues: [
      {
        id: "outlier-1",
        issue_type: "Outlier Spikes",
        severity: "warning",
        count: 14,
        percentage: 0.25,
        message: "14 holiday promotion spikes detected exceeding 3.0 IQR.",
        suggested_fix: "Bounded by automated cleaning.",
      },
    ],
    score: 96,
  } as QualityReport,
  audit_log: [
    {
      action: "System Initialization",
      timestamp: new Date().toISOString(),
      rows_affected: 0,
      details: "Precomputed synthetic retail dataset loaded.",
    } as AuditLogEntry,
  ],
}

// Generate realistic 30-day forecast with split-conformal intervals
const generateForecastSeries = (): ForecastPoint[] => {
  const points: ForecastPoint[] = []
  const baseDate = new Date("2023-10-03")
  // 60 days historical
  for (let i = 0; i < 60; i++) {
    const d = new Date(baseDate)
    d.setDate(baseDate.getDate() + i)
    const dayOfWeek = d.getDay()
    const weekendLift = (dayOfWeek === 0 || dayOfWeek === 6) ? 35 : 0
    const val = 120 + Math.sin(i / 3.5) * 20 + weekendLift + (i % 7 === 0 ? 15 : 0)
    points.push({
      date: d.toISOString().split("T")[0],
      actual: Math.round(val),
      predicted: null,
      models: {},
      lower_80: null,
      upper_80: null,
      lower_95: null,
      upper_95: null,
      lower_bound: null,
      upper_bound: null,
    })
  }
  // 30 days future forecast
  const forecastBase = new Date("2023-12-02")
  for (let i = 0; i < 30; i++) {
    const d = new Date(forecastBase)
    d.setDate(forecastBase.getDate() + i)
    const dayOfWeek = d.getDay()
    const weekendLift = (dayOfWeek === 0 || dayOfWeek === 6) ? 38 : 0
    const pred = Math.round(135 + Math.sin((60 + i) / 3.5) * 22 + weekendLift)
    const q80 = 14 + Math.sqrt(i + 1) * 2.2
    const q95 = 28 + Math.sqrt(i + 1) * 3.8
    points.push({
      date: d.toISOString().split("T")[0],
      actual: null,
      predicted: pred,
      models: {
        LightGBM: pred,
        XGBoost: pred - 3,
        "Holt-Winters": pred + 4,
        "Seasonal Naive": pred - 7,
      },
      lower_80: Math.max(0, Math.round(pred - q80)),
      upper_80: Math.round(pred + q80),
      lower_95: Math.max(0, Math.round(pred - q95)),
      upper_95: Math.round(pred + q95),
      lower_bound: Math.max(0, Math.round(pred - q80)),
      upper_bound: Math.round(pred + q80),
    })
  }
  return points
}

export const MOCK_RUN: RunResult = {
  id: "demo-run-champion",
  dataset_id: "demo-dataset-retail",
  dataset_name: "Retail Sales (Precomputed Demo)",
  series_id: "all",
  horizon: 30,
  metric: "wape",
  status: "completed",
  best_model: "LightGBM",
  leaderboard: [
    {
      model_key: "lightgbm",
      model_name: "LightGBM",
      mae: 11.42,
      rmse: 15.68,
      wape: 8.42,
      smape: 8.12,
      mase: 0.62,
      coverage_80: 82.5,
      coverage_95: 96.0,
      q_80: 14.2,
      q_95: 28.5,
      coverage_summary: "80% interval covered 82.5% of actuals (95% covered 96.0%)",
      fit_time_sec: 1.15,
      is_best: true,
    },
    {
      model_key: "xgboost",
      model_name: "XGBoost",
      mae: 12.85,
      rmse: 17.10,
      wape: 9.35,
      smape: 9.05,
      mase: 0.69,
      coverage_80: 81.0,
      coverage_95: 94.5,
      q_80: 15.8,
      q_95: 31.0,
      coverage_summary: "80% interval covered 81.0% of actuals (95% covered 94.5%)",
      fit_time_sec: 2.45,
      is_best: false,
    },
    {
      model_key: "holt_winters",
      model_name: "Holt-Winters",
      mae: 16.20,
      rmse: 21.45,
      wape: 12.10,
      smape: 11.85,
      mase: 0.88,
      coverage_80: 78.0,
      coverage_95: 93.0,
      q_80: 20.5,
      q_95: 39.0,
      coverage_summary: "80% interval covered 78.0% of actuals (95% covered 93.0%)",
      fit_time_sec: 0.42,
      is_best: false,
    },
    {
      model_key: "seasonal_naive",
      model_name: "Seasonal Naive",
      mae: 22.50,
      rmse: 28.90,
      wape: 16.80,
      smape: 15.90,
      mase: 1.0,
      coverage_80: 74.5,
      coverage_95: 91.0,
      q_80: 26.0,
      q_95: 47.0,
      coverage_summary: "80% interval covered 74.5% of actuals (95% covered 91.0%)",
      fit_time_sec: 0.08,
      is_best: false,
    },
  ],
  fold_metrics: [],
  forecast_series: generateForecastSeries(),
  backtest_overlay: [],
  summary: {
    last_period_total: 4120,
    forecast_total: 4680,
    pct_change: 13.6,
    best_model: "LightGBM",
    best_wape: 8.42,
    coverage_80: 82.5,
    coverage_95: 96.0,
    q_80: 14.2,
    q_95: 28.5,
    horizon: 30,
    n_folds: 3,
  },
  created_at: new Date().toISOString(),
  completed_at: new Date().toISOString(),
}

export const MOCK_EXPLAINABILITY: ExplainabilityResponse = {
  method: "tree_shap",
  selected_date: "2023-12-02",
  base_value: 124.5,
  global_drivers: [
    { feature: "lag_7", mean_abs_impact: 18.4, importance_pct: 32.5, category: "Recent Sales Momentum" },
    { feature: "dayofweek", mean_abs_impact: 14.2, importance_pct: 25.1, category: "Seasonality & Calendar" },
    { feature: "promo", mean_abs_impact: 11.5, importance_pct: 20.3, category: "Promotions & Pricing" },
    { feature: "rolling_mean_7", mean_abs_impact: 8.6, importance_pct: 15.2, category: "Recent Sales Momentum" },
  ],
  local_breakdown: [
    { feature: "dayofweek (Saturday)", contribution: 22.4, direction: "positive", category: "Seasonality & Calendar" },
    { feature: "promo (Active Discount)", contribution: 14.8, direction: "positive", category: "Promotions & Pricing" },
    { feature: "lag_7", contribution: 6.2, direction: "positive", category: "Recent Sales Momentum" },
    { feature: "price (Index higher)", contribution: -4.1, direction: "negative", category: "Promotions & Pricing" },
  ],
  category_summary: [
    { category: "Seasonality & Calendar", net_impact: 22.4 },
    { category: "Promotions & Pricing", net_impact: 10.7 },
    { category: "Recent Sales Momentum", net_impact: 6.2 },
  ],
  narrative: "On 2023-12-02, predicted demand starts from a baseline of 124.5 units, pushed higher by weekend shopping lift (+22.4 units) and active promotion (+14.8 units).",
}

export const MOCK_INVENTORY: InventorySupportResponse = {
  disclaimer: "Extension: decision support, not advice. Verify against supplier constraints and minimum order quantities.",
  status: "Reorder now",
  status_color: "red",
  lead_time_days: 7,
  service_level: "95%",
  z_factor: 1.645,
  current_stock: 450,
  days_of_supply: 2.9,
  daily_demand_mean: 156.0,
  lead_time_demand: 1092.0,
  safety_stock: 145.0,
  reorder_point: 1237.0,
  suggested_order_qty: 1879.0,
  estimated_order_cost: 46975.0,
  inventory_summary: [
    { parameter: "Daily Demand (Forecast Avg)", value: "156.0 units/day", description: "Mean predicted demand" },
    { parameter: "Lead Time", value: "7 days", description: "Replenishment delivery window" },
    { parameter: "Target Service Level", value: "95% (z = 1.645)", description: "Stockout protection probability" },
    { parameter: "Lead Time Demand (μ_LT)", value: "1,092 units", description: "Cumulative consumption during lead time" },
    { parameter: "Safety Stock (SS)", value: "145 units", description: "z × σ_error × √L buffer" },
    { parameter: "Reorder Point (ROP)", value: "1,237 units", description: "Replenishment trigger threshold" },
    { parameter: "Current Inventory", value: "450 units (2.9 days supply)", description: "Reported stock on hand" },
    { parameter: "Suggested Replenishment", value: "1,879 units", description: "Recommended order quantity" },
  ],
}
