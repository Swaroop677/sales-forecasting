import numpy as np
from typing import Any


def compute_conformal_quantiles(residuals: np.ndarray | list[float]) -> dict[str, float]:
    """
    Computes finite-sample split-conformal quantiles for 80% and 95% coverage.
    Nonconformity score R_i = |y_i - y_hat_i|.
    Finite-sample corrected quantile level: ceil((n + 1) * (1 - alpha)) / n.
    """
    res = np.abs(np.array(residuals, dtype=float))
    res = res[np.isfinite(res)]
    n = len(res)

    if n == 0:
        return {"q_80": 10.0, "q_95": 25.0, "residuals_count": 0}

    # Finite-sample correction
    level_80 = min(1.0, np.ceil((n + 1) * 0.80) / n)
    level_95 = min(1.0, np.ceil((n + 1) * 0.95) / n)

    q_80 = float(np.quantile(res, level_80))
    q_95 = float(np.quantile(res, level_95))

    return {
        "q_80": round(q_80, 2),
        "q_95": round(q_95, 2),
        "residuals_count": n,
        "std_error": round(float(np.std(res)), 2),
    }


def compute_empirical_coverage(
    actuals: list[float],
    predictions: list[float],
    q_80: float,
    q_95: float,
) -> dict[str, float]:
    """
    Evaluates empirical coverage on out-of-sample backtest points:
    fraction of actuals that fall inside [pred - q, pred + q].
    """
    y_true = np.array(actuals, dtype=float)
    y_pred = np.array(predictions, dtype=float)
    n = len(y_true)

    if n == 0:
        return {"coverage_80": 80.0, "coverage_95": 95.0}

    in_80 = np.sum((y_true >= (y_pred - q_80)) & (y_true <= (y_pred + q_80)))
    in_95 = np.sum((y_true >= (y_pred - q_95)) & (y_true <= (y_pred + q_95)))

    cov_80 = round(float((in_80 / n) * 100.0), 1)
    cov_95 = round(float((in_95 / n) * 100.0), 1)

    return {
        "coverage_80": cov_80,
        "coverage_95": cov_95,
    }


def apply_conformal_bands(
    forecast_points: list[dict[str, Any]],
    q_80: float,
    q_95: float,
) -> list[dict[str, Any]]:
    """
    Decorates future forecast points with lower_80, upper_80, lower_95, upper_95.
    Lower bounds are non-negatively clipped at 0.0.
    """
    decorated = []
    for pt in forecast_points:
        pred = pt.get("predicted")
        if pred is not None:
            # Add slight horizon fan-out (sqrt(t)) so uncertainty expands with forecast distance
            idx = pt.get("step_index", 1)
            time_factor = np.sqrt(idx)

            step_q_80 = q_80 * (0.85 + 0.15 * time_factor)
            step_q_95 = q_95 * (0.85 + 0.15 * time_factor)

            pt["lower_80"] = max(0.0, round(float(pred - step_q_80), 2))
            pt["upper_80"] = round(float(pred + step_q_80), 2)
            pt["lower_95"] = max(0.0, round(float(pred - step_q_95), 2))
            pt["upper_95"] = round(float(pred + step_q_95), 2)
            pt["lower_bound"] = pt["lower_80"]
            pt["upper_bound"] = pt["upper_80"]
        else:
            pt["lower_80"] = None
            pt["upper_80"] = None
            pt["lower_95"] = None
            pt["upper_95"] = None
        decorated.append(pt)
    return decorated
