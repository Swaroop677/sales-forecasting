from typing import Any
import numpy as np
import pandas as pd
from scipy import stats


def calculate_psi(reference: np.ndarray, current: np.ndarray, num_buckets: int = 10) -> float:
    """
    Computes Population Stability Index (PSI) between reference and current distribution.
    PSI = sum((Actual% - Expected%) * ln(Actual% / Expected%))
    """
    ref = reference[np.isfinite(reference)]
    cur = current[np.isfinite(current)]

    if len(ref) < 5 or len(cur) < 5:
        return 0.0

    # Determine quantile bin edges from reference distribution
    percentiles = np.linspace(0, 100, num_buckets + 1)
    bin_edges = np.percentile(ref, percentiles)
    bin_edges[0] -= 1e-5
    bin_edges[-1] += 1e-5
    bin_edges = np.unique(bin_edges)

    if len(bin_edges) < 2:
        return 0.0

    # Counts in each bucket
    ref_counts, _ = np.histogram(ref, bins=bin_edges)
    cur_counts, _ = np.histogram(cur, bins=bin_edges)

    # Fractions with Laplace smoothing to avoid division by zero
    ref_pct = (ref_counts + 1e-4) / (len(ref) + 1e-4 * len(ref_counts))
    cur_pct = (cur_counts + 1e-4) / (len(cur) + 1e-4 * len(cur_counts))

    psi_val = np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct))
    return max(0.0, float(psi_val))


def compute_drift_report(
    df: pd.DataFrame,
    date_col: str,
    target_col: str,
    regressor_cols: list[str] = None,
    split_ratio: float = 0.70,
) -> dict[str, Any]:
    """
    Evaluates distribution drift between historical baseline and recent data:
    1. Splits timeline into Reference (first 70%) and Current (last 30%).
    2. Computes PSI and KS 2-sample test for target and numeric regressors.
    3. Categorizes drift severity and flags whether model retraining is advised.
    """
    df_sorted = df.copy().sort_values(by=date_col).reset_index(drop=True)
    n = len(df_sorted)
    if n < 20:
        return {
            "has_drift": False,
            "overall_status": "insufficient_data",
            "overall_psi": 0.0,
            "features": [],
            "retrain_recommended": False,
            "banner_message": None,
        }

    split_idx = int(n * split_ratio)
    ref_df = df_sorted.iloc[:split_idx]
    cur_df = df_sorted.iloc[split_idx:]

    cols_to_check = [target_col]
    if regressor_cols:
        cols_to_check.extend([c for c in regressor_cols if c in df_sorted.columns])

    feature_drifts = []
    max_psi = 0.0

    for col in cols_to_check:
        ref_vals = pd.to_numeric(ref_df[col], errors="coerce").dropna().values
        cur_vals = pd.to_numeric(cur_df[col], errors="coerce").dropna().values

        if len(ref_vals) < 5 or len(cur_vals) < 5:
            continue

        psi = calculate_psi(ref_vals, cur_vals)
        ks_stat, p_val = stats.ks_2samp(ref_vals, cur_vals)

        if psi > max_psi:
            max_psi = psi

        if psi < 0.10:
            status = "Stable"
            badge = "emerald"
        elif psi <= 0.25:
            status = "Moderate Drift"
            badge = "amber"
        else:
            status = "Significant Drift"
            badge = "red"

        feature_drifts.append({
            "feature": col,
            "is_target": (col == target_col),
            "psi": round(psi, 3),
            "ks_statistic": round(float(ks_stat), 3),
            "p_value": round(float(p_val), 4),
            "status": status,
            "badge": badge,
            "reference_mean": round(float(np.mean(ref_vals)), 1),
            "current_mean": round(float(np.mean(cur_vals)), 1),
            "mean_shift_pct": round(float(((np.mean(cur_vals) - np.mean(ref_vals)) / max(1e-5, np.mean(ref_vals))) * 100), 1),
        })

    retrain_recommended = max_psi > 0.25 or any(
        f["is_target"] and f["psi"] > 0.15 for f in feature_drifts
    )

    banner_msg = None
    if retrain_recommended:
        banner_msg = (
            f"Model may be stale — significant distribution shift detected (Target PSI = {feature_drifts[0]['psi'] if feature_drifts else max_psi:.2f}). "
            "Recent sales dynamics diverge from training conditions. Retraining is recommended."
        )

    return {
        "has_drift": retrain_recommended,
        "overall_status": "Drift Alert" if retrain_recommended else ("Moderate Drift" if max_psi > 0.10 else "Stable"),
        "overall_psi": round(max_psi, 3),
        "reference_period": f"{ref_df[date_col].iloc[0]} to {ref_df[date_col].iloc[-1]}",
        "current_period": f"{cur_df[date_col].iloc[0]} to {cur_df[date_col].iloc[-1]}",
        "retrain_recommended": retrain_recommended,
        "banner_message": banner_msg,
        "features": feature_drifts,
    }
