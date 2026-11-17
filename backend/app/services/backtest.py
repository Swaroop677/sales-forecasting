import time
from typing import Any, Callable, Optional

import numpy as np
import pandas as pd
from backend.app.services.forecasters import get_forecaster
from backend.app.services.metrics import calculate_all_metrics
from backend.app.services.ml.conformal import (
    compute_conformal_quantiles,
    compute_empirical_coverage,
)


def run_rolling_origin_backtest(
    df: pd.DataFrame,
    date_col: str,
    target_col: str,
    regressor_cols: list[str],
    horizon: int = 30,
    models: list[str] = None,
    n_folds: int = 3,
    metric_to_optimize: str = "wape",
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> dict[str, Any]:
    """
    Executes a strict rolling-origin expanding-window backtest across n_folds:
    For each fold k:
      - Train window: from start up to (total_len - (n_folds - k) * horizon)
      - Test window: next `horizon` days
      - Fit each model ONLY on train data
      - Predict on test window
      - Compute MAE, RMSE, WAPE, sMAPE, MASE
    Averages metrics across folds, picks the best model, refits on 100% of the dataset,
    and produces forward-looking forecast for the specified horizon.
    """
    models = models or ["seasonal_naive", "holt_winters", "lightgbm", "xgboost"]
    df_sorted = df.copy().sort_values(by=date_col).reset_index(drop=True)
    total_len = len(df_sorted)

    # Validate that we have enough points for n_folds * horizon
    min_required = (n_folds + 1) * horizon
    if total_len < min_required:
        # Adjust n_folds or horizon if dataset is too small
        n_folds = max(2, min(n_folds, (total_len - horizon) // max(1, horizon)))
        if n_folds < 2:
            n_folds = 2
            horizon = max(7, total_len // 4)

    if progress_callback:
        progress_callback(10, f"Configured {n_folds} backtest folds with horizon={horizon}")

    # Build fold cutoffs
    test_size = horizon
    fold_splits = []
    for k in range(n_folds):
        # The last fold ends at total_len
        test_end = total_len - (n_folds - 1 - k) * test_size
        test_start = test_end - test_size
        train_end = test_start
        if train_end >= horizon:  # Ensure training set has at least horizon length
            fold_splits.append((0, train_end, test_start, test_end))

    if not fold_splits:
        # Fallback to single split if data is constrained
        split_idx = int(total_len * 0.8)
        fold_splits = [(0, split_idx, split_idx, total_len)]

    fold_metrics_list = []
    model_fold_results: dict[str, list[dict[str, float]]] = {m: [] for m in models}
    model_residuals: dict[str, list[float]] = {m: [] for m in models}
    model_actuals: dict[str, list[float]] = {m: [] for m in models}
    model_preds: dict[str, list[float]] = {m: [] for m in models}
    backtest_overlay_map: dict[str, dict[str, Any]] = {}

    total_steps = len(fold_splits) * len(models)
    current_step = 0

    # Backtesting loop
    for fold_idx, (train_start, train_end, test_start, test_end) in enumerate(fold_splits):
        train_df = df_sorted.iloc[train_start:train_end].copy()
        test_df = df_sorted.iloc[test_start:test_end].copy()

        y_train = pd.to_numeric(train_df[target_col], errors="coerce").fillna(0).values
        y_test = pd.to_numeric(test_df[target_col], errors="coerce").fillna(0).values
        test_dates = test_df[date_col].values

        for model_key in models:
            step_pct = 15 + int((current_step / total_steps) * 60)
            if progress_callback:
                progress_callback(
                    step_pct,
                    f"Backtesting {model_key} on Fold {fold_idx + 1}/{len(fold_splits)}",
                )

            start_t = time.perf_counter()
            forecaster = get_forecaster(model_key)
            forecaster.fit(
                df=train_df,
                date_col=date_col,
                target_col=target_col,
                regressor_cols=regressor_cols,
            )

            # Predict horizon length
            preds = forecaster.predict(horizon=len(test_df), future_df=test_df)
            fit_time = time.perf_counter() - start_t

            # Calculate fold metrics
            metrics = calculate_all_metrics(
                y_true=y_test,
                y_pred=preds,
                y_train=y_train,
                seasonality=7,
            )
            metrics["fit_time_sec"] = round(fit_time, 3)

            model_fold_results[model_key].append(metrics)
            model_residuals[model_key].extend([abs(float(yt) - float(yp)) for yt, yp in zip(y_test, preds)])
            model_actuals[model_key].extend([float(yt) for yt in y_test])
            model_preds[model_key].extend([float(yp) for yp in preds])

            fold_metrics_list.append({
                "fold_idx": fold_idx + 1,
                "model_name": forecaster.name,
                "model_key": model_key,
                "train_range": f"{train_df[date_col].iloc[0]} to {train_df[date_col].iloc[-1]}",
                "test_range": f"{test_df[date_col].iloc[0]} to {test_df[date_col].iloc[-1]}",
                **metrics,
            })

            # Store predictions for chart backtest overlay
            for d_idx, d_str in enumerate(test_dates):
                if d_str not in backtest_overlay_map:
                    backtest_overlay_map[d_str] = {
                        "date": str(d_str),
                        "actual": float(y_test[d_idx]),
                        "predictions": {},
                    }
                backtest_overlay_map[d_str]["predictions"][forecaster.name] = round(float(preds[d_idx]), 2)

            current_step += 1

    if progress_callback:
        progress_callback(78, "Calculating aggregate model performance")

    # Aggregate leaderboard metrics across folds
    leaderboard = []
    for model_key in models:
        forecaster_instance = get_forecaster(model_key)
        results = model_fold_results[model_key]
        if not results:
            continue

        avg_mae = float(np.mean([r["mae"] for r in results]))
        avg_rmse = float(np.mean([r["rmse"] for r in results]))
        avg_wape = float(np.mean([r["wape"] for r in results]))
        avg_smape = float(np.mean([r["smape"] for r in results]))
        avg_mase = float(np.mean([r["mase"] for r in results]))
        total_time = float(np.sum([r["fit_time_sec"] for r in results]))

        # Split-conformal calibration on backtest residuals
        conformal_info = compute_conformal_quantiles(model_residuals.get(model_key, []))
        cov_info = compute_empirical_coverage(
            actuals=model_actuals.get(model_key, []),
            predictions=model_preds.get(model_key, []),
            q_80=conformal_info["q_80"],
            q_95=conformal_info["q_95"],
        )

        leaderboard.append({
            "model_key": model_key,
            "model_name": forecaster_instance.name,
            "mae": round(avg_mae, 2),
            "rmse": round(avg_rmse, 2),
            "wape": round(avg_wape, 2),
            "smape": round(avg_smape, 2),
            "mase": round(avg_mase, 3),
            "coverage_80": cov_info["coverage_80"],
            "coverage_95": cov_info["coverage_95"],
            "q_80": conformal_info["q_80"],
            "q_95": conformal_info["q_95"],
            "coverage_summary": f"80% interval covered {cov_info['coverage_80']}% of actuals (95% covered {cov_info['coverage_95']}%)",
            "fit_time_sec": round(total_time, 2),
            "is_best": False,
        })

    # Pick the best model based on chosen metric (lower is better for MAE, RMSE, WAPE, sMAPE, MASE)
    sort_key = metric_to_optimize if metric_to_optimize in ["mae", "rmse", "wape", "smape", "mase"] else "wape"
    leaderboard.sort(key=lambda item: item[sort_key])
    if leaderboard:
        leaderboard[0]["is_best"] = True
        best_model_key = leaderboard[0]["model_key"]
        best_model_name = leaderboard[0]["model_name"]
    else:
        best_model_key = "seasonal_naive"
        best_model_name = "Seasonal Naive"

    if progress_callback:
        progress_callback(85, f"Refitting winner ({best_model_name}) on full history")

    # Refit all requested models on full 100% data to generate forward predictions
    all_future_forecasts = {}
    fitted_forecasters = {}

    last_date = pd.to_datetime(df_sorted[date_col].iloc[-1])
    future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=horizon, freq="D")
    future_date_strings = [d.strftime("%Y-%m-%d") for d in future_dates]

    for model_key in models:
        m = get_forecaster(model_key)
        m.fit(
            df=df_sorted,
            date_col=date_col,
            target_col=target_col,
            regressor_cols=regressor_cols,
        )
        preds = m.predict(horizon=horizon)
        all_future_forecasts[m.name] = preds
        fitted_forecasters[model_key] = m

    # Construct unified forecast points
    best_preds = all_future_forecasts[best_model_name]
    best_q_80 = float(leaderboard[0].get("q_80", 15.0)) if leaderboard else 15.0
    best_q_95 = float(leaderboard[0].get("q_95", 30.0)) if leaderboard else 30.0

    forecast_points = []
    for step_i in range(horizon):
        date_str = future_date_strings[step_i]
        point_models = {
            m_name: round(float(all_future_forecasts[m_name][step_i]), 2)
            for m_name in all_future_forecasts
        }
        val = round(float(best_preds[step_i]), 2)

        # Split-conformal prediction intervals (80% and 95%) with horizon fan-out
        time_factor = np.sqrt(step_i + 1)
        step_q_80 = best_q_80 * (0.85 + 0.15 * time_factor)
        step_q_95 = best_q_95 * (0.85 + 0.15 * time_factor)

        lower_80 = max(0.0, round(val - step_q_80, 2))
        upper_80 = round(val + step_q_80, 2)
        lower_95 = max(0.0, round(val - step_q_95, 2))
        upper_95 = round(val + step_q_95, 2)

        forecast_points.append({
            "date": date_str,
            "actual": None,
            "predicted": val,
            "models": point_models,
            "lower_80": lower_80,
            "upper_80": upper_80,
            "lower_95": lower_95,
            "upper_95": upper_95,
            "lower_bound": lower_80,
            "upper_bound": upper_80,
        })

    # Historical points (last 90 days for smooth chart display)
    history_subset = df_sorted.tail(min(90, len(df_sorted)))
    history_points = []
    for _, row in history_subset.iterrows():
        history_points.append({
            "date": str(row[date_col]),
            "actual": round(float(row[target_col]), 2),
            "predicted": None,
            "models": {},
            "lower_80": None,
            "upper_80": None,
            "lower_95": None,
            "upper_95": None,
            "lower_bound": None,
            "upper_bound": None,
        })

    combined_series = history_points + forecast_points

    # Backtest overlay list sorted by date
    backtest_overlay = sorted(list(backtest_overlay_map.values()), key=lambda x: x["date"])

    # High-level summary metrics for KPI cards
    last_period_actual = float(df_sorted[target_col].tail(horizon).sum())
    forecast_period_total = float(np.sum(best_preds))
    pct_change = (
        round(((forecast_period_total - last_period_actual) / max(1.0, last_period_actual)) * 100.0, 1)
        if last_period_actual > 0
        else 0.0
    )

    summary = {
        "last_period_total": round(last_period_actual, 2),
        "forecast_total": round(forecast_period_total, 2),
        "pct_change": pct_change,
        "best_model": best_model_name,
        "best_wape": leaderboard[0]["wape"] if leaderboard else 0.0,
        "coverage_80": leaderboard[0].get("coverage_80", 80.0) if leaderboard else 80.0,
        "coverage_95": leaderboard[0].get("coverage_95", 95.0) if leaderboard else 95.0,
        "q_80": leaderboard[0].get("q_80", 0.0) if leaderboard else 0.0,
        "q_95": leaderboard[0].get("q_95", 0.0) if leaderboard else 0.0,
        "horizon": horizon,
        "n_folds": len(fold_splits),
    }

    if progress_callback:
        progress_callback(100, "Forecast complete")

    return {
        "leaderboard": leaderboard,
        "fold_metrics": fold_metrics_list,
        "forecast_series": combined_series,
        "backtest_overlay": backtest_overlay,
        "summary": summary,
        "best_model_instance": fitted_forecasters[best_model_key],
        "best_model_key": best_model_key,
        "best_model_name": best_model_name,
    }
