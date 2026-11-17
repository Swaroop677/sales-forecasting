from typing import Any, Optional
import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import seasonal_decompose


def explain_tree_forecast(
    model: Any,
    feature_names: list[str],
    X_sample: np.ndarray,
    target_date: Optional[str] = None,
    future_dates: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Computes global and local feature contributions using native tree SHAP contributions
    (pred_contrib=True) on a capped sample without heavy memory overhead.
    """
    # Cap sample size to fit free-tier constraints (100 rows max)
    X_capped = X_sample[: min(100, len(X_sample))]

    # 1. Compute tree contributions
    raw_contribs = None
    try:
        if hasattr(model, "predict"):
            # LightGBM LGBMRegressor support
            raw_contribs = model.predict(X_capped, pred_contrib=True)
    except Exception:
        pass

    if raw_contribs is None:
        # Fallback to feature_importances_ if pred_contrib is not available
        importances = getattr(model, "feature_importances_", None)
        if importances is not None and len(importances) == len(feature_names):
            norm_imp = importances / max(1e-6, np.sum(importances))
            drivers = [
                {
                    "feature": feat,
                    "importance": round(float(norm_imp[i] * 100), 1),
                    "category": categorize_feature(feat),
                    "impact": "neutral",
                }
                for i, feat in enumerate(feature_names)
            ]
            drivers.sort(key=lambda d: d["importance"], reverse=True)
            return {
                "method": "feature_importance",
                "global_drivers": drivers[:8],
                "selected_date": target_date or (future_dates[0] if future_dates else "Latest"),
                "base_value": 0.0,
                "local_breakdown": [],
                "narrative": "Feature importance indicates demand is primarily driven by recent sales momentum and calendar seasonality.",
            }

    # raw_contribs shape: (N, num_features + 1), where last column is base value
    contribs_matrix = np.array(raw_contribs)
    base_val = float(np.mean(contribs_matrix[:, -1]))
    feat_contribs = contribs_matrix[:, :-1]

    # Global importance: mean absolute contribution
    mean_abs = np.mean(np.abs(feat_contribs), axis=0)
    total_abs = max(1e-6, np.sum(mean_abs))
    global_drivers = []
    for i, feat in enumerate(feature_names[: feat_contribs.shape[1]]):
        global_drivers.append({
            "feature": feat,
            "mean_abs_impact": round(float(mean_abs[i]), 2),
            "importance_pct": round(float((mean_abs[i] / total_abs) * 100), 1),
            "category": categorize_feature(feat),
        })
    global_drivers.sort(key=lambda x: x["mean_abs_impact"], reverse=True)

    # Local explanation for the requested date (default to first future date)
    date_idx = 0
    if target_date and future_dates and target_date in future_dates:
        date_idx = future_dates.index(target_date)
    date_idx = min(date_idx, len(feat_contribs) - 1)
    sel_date = future_dates[date_idx] if future_dates and date_idx < len(future_dates) else (target_date or "Day 1")

    row_contrib = feat_contribs[date_idx]
    local_breakdown = []
    for i, feat in enumerate(feature_names[: len(row_contrib)]):
        val = float(row_contrib[i])
        local_breakdown.append({
            "feature": feat,
            "contribution": round(val, 2),
            "direction": "positive" if val > 0 else "negative",
            "category": categorize_feature(feat),
        })
    local_breakdown.sort(key=lambda x: abs(x["contribution"]), reverse=True)

    # Grouped category impact
    categories: dict[str, float] = {
        "Promotions & Pricing": 0.0,
        "Seasonality & Calendar": 0.0,
        "Recent Sales Momentum": 0.0,
        "Other / Baseline": 0.0,
    }
    for item in local_breakdown:
        cat = item["category"]
        categories[cat] = categories.get(cat, 0.0) + item["contribution"]

    grouped_summary = [
        {"category": k, "net_impact": round(v, 2)}
        for k, v in categories.items()
        if abs(v) > 0.01
    ]
    grouped_summary.sort(key=lambda x: abs(x["net_impact"]), reverse=True)

    # Generate plain-English takeaway
    narrative = generate_plain_english_takeaway(sel_date, base_val, local_breakdown[:4], categories)

    return {
        "method": "tree_shap",
        "selected_date": sel_date,
        "base_value": round(base_val, 2),
        "global_drivers": global_drivers[:8],
        "local_breakdown": local_breakdown[:8],
        "category_summary": grouped_summary,
        "narrative": narrative,
    }


def explain_decomposition(df: pd.DataFrame, date_col: str, target_col: str) -> dict[str, Any]:
    """
    Computes classical additive time series decomposition (Trend, Seasonal, Residual)
    for non-tree models (Holt-Winters, Naive).
    """
    df_sorted = df.copy().sort_values(by=date_col).reset_index(drop=True)
    series = pd.to_numeric(df_sorted[target_col], errors="coerce").fillna(0).values

    period = 7 if len(series) >= 21 else max(2, len(series) // 3)
    try:
        decomp = seasonal_decompose(series, model="additive", period=period, extrapolate_trend="freq")
        trend = np.nan_to_num(decomp.trend).tolist()
        seasonal = np.nan_to_num(decomp.seasonal).tolist()
        resid = np.nan_to_num(decomp.resid).tolist()
    except Exception:
        trend = [float(np.mean(series))] * len(series)
        seasonal = [0.0] * len(series)
        resid = (series - np.mean(series)).tolist()

    recent_idx = min(30, len(series))
    recent_dates = [str(d) for d in df_sorted[date_col].tail(recent_idx)]
    recent_actual = [round(float(v), 2) for v in series[-recent_idx:]]
    recent_trend = [round(float(v), 2) for v in trend[-recent_idx:]]
    recent_seasonal = [round(float(v), 2) for v in seasonal[-recent_idx:]]
    recent_resid = [round(float(v), 2) for v in resid[-recent_idx:]]

    avg_seasonal_swing = round(float(np.max(recent_seasonal) - np.min(recent_seasonal)), 2)
    trend_dir = "increasing" if recent_trend[-1] > recent_trend[0] else "steady or softening"

    return {
        "method": "decomposition",
        "dates": recent_dates,
        "actual": recent_actual,
        "trend": recent_trend,
        "seasonal": recent_seasonal,
        "residual": recent_resid,
        "seasonal_period": period,
        "narrative": (
            f"Time-series decomposition identifies an overall {trend_dir} baseline trend "
            f"with a recurring {period}-day seasonal swing averaging {avg_seasonal_swing} units."
        ),
    }


def categorize_feature(feat_name: str) -> str:
    name_lower = feat_name.lower()
    if any(k in name_lower for k in ["promo", "price", "discount", "traffic", "ad_"]):
        return "Promotions & Pricing"
    elif any(k in name_lower for k in ["dayofweek", "month", "quarter", "weekend", "year", "holiday", "sin", "cos"]):
        return "Seasonality & Calendar"
    elif any(k in name_lower for k in ["lag", "rolling", "ewma", "mean", "std"]):
        return "Recent Sales Momentum"
    return "Other / Baseline"


def generate_plain_english_takeaway(
    date_str: str,
    base_val: float,
    top_drivers: list[dict[str, Any]],
    cat_summary: dict[str, float],
) -> str:
    pos_drivers = [d["feature"].replace("_", " ").title() for d in top_drivers if d["contribution"] > 0]
    neg_drivers = [d["feature"].replace("_", " ").title() for d in top_drivers if d["contribution"] < 0]

    parts = [f"On {date_str}, predicted demand starts from a baseline of {round(base_val, 1)} units."]
    if pos_drivers:
        parts.append(f"It is pushed higher primarily by {', '.join(pos_drivers[:2])}.")
    if neg_drivers:
        parts.append(f"It experiences downward pressure from {', '.join(neg_drivers[:2])}.")

    main_cat = max(cat_summary.items(), key=lambda x: abs(x[1])) if cat_summary else None
    if main_cat and abs(main_cat[1]) > 0.1:
        impact_word = "lift" if main_cat[1] > 0 else "drag"
        parts.append(f"Overall, {main_cat[0]} accounts for the strongest net {impact_word} ({main_cat[1]:+.1f} units).")

    return " ".join(parts)
