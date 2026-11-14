from typing import Optional

import numpy as np
import pandas as pd


def create_calendar_features(dates: pd.Series) -> pd.DataFrame:
    """Extracts cyclic and calendar features from a date series."""
    dt = pd.to_datetime(dates)
    features = pd.DataFrame(index=dates.index)
    features["day_of_week"] = dt.dt.day_of_week
    features["is_weekend"] = dt.dt.day_of_week.isin([5, 6]).astype(int)
    features["day_of_month"] = dt.dt.day
    features["month"] = dt.dt.month
    features["day_of_year"] = dt.dt.day_of_year
    features["week_of_year"] = dt.dt.isocalendar().week.astype(int)

    # Cyclical sin/cos encodings
    features["dow_sin"] = np.sin(2 * np.pi * features["day_of_week"] / 7.0)
    features["dow_cos"] = np.cos(2 * np.pi * features["day_of_week"] / 7.0)
    features["month_sin"] = np.sin(2 * np.pi * features["month"] / 12.0)
    features["month_cos"] = np.cos(2 * np.pi * features["month"] / 12.0)

    return features


def build_lag_features(
    y_series: pd.Series,
    lags: tuple[int, ...] = (1, 2, 3, 7, 14, 21, 28),
) -> pd.DataFrame:
    """
    Constructs lag features strictly shifted by >= 1 to prevent data leakage.
    lag_k at row t corresponds to y_{t - k}.
    """
    features = pd.DataFrame(index=y_series.index)
    for lag in lags:
        features[f"lag_{lag}"] = y_series.shift(lag)
    return features


def build_rolling_features(
    y_series: pd.Series,
    windows: tuple[int, ...] = (7, 14, 28),
) -> pd.DataFrame:
    """
    Constructs rolling mean and standard deviation features strictly from past data.
    Shift by 1 before calculating rolling window so observation y_t is never included in row t.
    """
    features = pd.DataFrame(index=y_series.index)
    # SHIFT BY 1 IS CRITICAL TO PREVENT LEAKAGE
    shifted = y_series.shift(1)

    for w in windows:
        features[f"rolling_mean_{w}"] = shifted.rolling(window=w, min_periods=1).mean()
        if w in (7, 14):
            features[f"rolling_std_{w}"] = shifted.rolling(window=w, min_periods=2).std().fillna(0)

    return features


def build_feature_matrix(
    df: pd.DataFrame,
    date_col: str,
    target_col: Optional[str] = None,
    regressor_cols: Optional[list[str]] = None,
    lags: tuple[int, ...] = (1, 2, 3, 7, 14, 21, 28),
    windows: tuple[int, ...] = (7, 14, 28),
) -> pd.DataFrame:
    """
    Combines calendar, lag, rolling, and external regressor features into one matrix.
    Rows with NaNs due to early lags are back-filled or imputed with early values.
    """
    regressor_cols = regressor_cols or []
    cal_df = create_calendar_features(df[date_col])

    feature_dfs = [cal_df]

    # Regressors (known contemporaneous features like promo, price, holiday flag)
    for reg in regressor_cols:
        if reg in df.columns:
            feature_dfs.append(df[[reg]].astype(float).fillna(0))

    if target_col and target_col in df.columns:
        y_series = pd.to_numeric(df[target_col], errors="coerce")
        lag_df = build_lag_features(y_series, lags=lags)
        roll_df = build_rolling_features(y_series, windows=windows)
        feature_dfs.extend([lag_df, roll_df])

    X = pd.concat(feature_dfs, axis=1)

    # Impute any remaining NaNs in early rows using backfill then 0
    X = X.bfill().fillna(0)
    return X
