from typing import Optional

import numpy as np


def mean_absolute_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    if len(y_true) == 0:
        return 0.0
    return float(np.mean(np.abs(y_true - y_pred)))


def root_mean_squared_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    if len(y_true) == 0:
        return 0.0
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def weighted_absolute_percentage_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    WAPE (Weighted Absolute Percentage Error), standard in supply chain / retail:
    sum(|y_true - y_pred|) / sum(y_true).
    Returns value as a percentage (e.g., 14.5 for 14.5%).
    If total actual volume is 0, returns 0 if errors are 0, else 100.
    """
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    if len(y_true) == 0:
        return 0.0
    abs_errors = np.sum(np.abs(y_true - y_pred))
    total_actual = np.sum(np.abs(y_true))
    if total_actual == 0:
        return 0.0 if abs_errors == 0 else 100.0
    return float((abs_errors / total_actual) * 100.0)


def symmetric_mean_absolute_percentage_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    sMAPE (Symmetric Mean Absolute Percentage Error), bounded between 0% and 200%:
    (100 / n) * sum( 2 * |y_true - y_pred| / (|y_true| + |y_pred| + 1e-8) )
    """
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    if len(y_true) == 0:
        return 0.0
    denominator = np.abs(y_true) + np.abs(y_pred)
    # Avoid zero division when both true and pred are zero
    mask = denominator != 0
    if not np.any(mask):
        return 0.0
    smape_vals = np.zeros_like(y_true, dtype=float)
    smape_vals[mask] = (2.0 * np.abs(y_true[mask] - y_pred[mask])) / denominator[mask]
    return float(np.mean(smape_vals) * 100.0)


def mean_absolute_scaled_error(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_train: np.ndarray,
    seasonality: int = 7,
) -> float:
    """
    MASE (Mean Absolute Scaled Error) from Hyndman & Koehler (2006).
    Compares the forecast's MAE against the in-sample seasonal naive MAE:
    MASE = MAE / ( (1 / (T - m)) * sum_{t=m+1}^T |y_t - y_{t-m}| )
    A value < 1 indicates the model outperforms the naive seasonal benchmark.
    """
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    y_train = np.asarray(y_train, dtype=float)

    mae = mean_absolute_error(y_true, y_pred)
    if mae == 0:
        return 0.0

    if len(y_train) <= seasonality:
        seasonality = 1
    if len(y_train) <= 1:
        return 1.0

    scale = np.mean(np.abs(y_train[seasonality:] - y_train[:-seasonality]))
    if scale == 0 or np.isnan(scale):
        return 1.0
    return float(mae / scale)


def calculate_all_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_train: Optional[np.ndarray] = None,
    seasonality: int = 7,
) -> dict[str, float]:
    """Calculates full metrics dictionary with rounded precision."""
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    if y_train is None or len(y_train) == 0:
        y_train = y_true

    return {
        "mae": round(mean_absolute_error(y_true, y_pred), 2),
        "rmse": round(root_mean_squared_error(y_true, y_pred), 2),
        "wape": round(weighted_absolute_percentage_error(y_true, y_pred), 2),
        "smape": round(symmetric_mean_absolute_percentage_error(y_true, y_pred), 2),
        "mase": round(mean_absolute_scaled_error(y_true, y_pred, y_train, seasonality), 3),
    }
