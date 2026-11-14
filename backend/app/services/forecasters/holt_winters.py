from typing import Optional

import numpy as np
import pandas as pd
from backend.app.services.forecasters.base import Forecaster
from statsmodels.tsa.holtwinters import ExponentialSmoothing


class HoltWintersForecaster(Forecaster):
    """
    Holt-Winters Exponential Smoothing (statsmodels).
    Captures level, trend, and seasonal patterns.
    Falls back gracefully to Simple Exponential Smoothing or Naive if series length is short.
    """

    def __init__(self, seasonal_periods: int = 7):
        super().__init__(name="Holt-Winters")
        self.seasonal_periods = seasonal_periods
        self.fitted_model = None
        self.last_value: float = 0.0

    def fit(
        self,
        df: pd.DataFrame,
        date_col: str,
        target_col: str,
        regressor_cols: Optional[list[str]] = None,
    ) -> "HoltWintersForecaster":
        self.date_col = date_col
        self.target_col = target_col
        self.regressor_cols = regressor_cols or []

        y = pd.to_numeric(df[target_col], errors="coerce").fillna(0).values.astype(float)
        if len(y) == 0:
            self.last_value = 0.0
            self.is_fitted = True
            return self

        self.last_value = float(y[-1])

        try:
            # Need at least 2 * seasonal_periods to fit seasonal Holt-Winters
            if len(y) >= 2 * self.seasonal_periods:
                model = ExponentialSmoothing(
                    y,
                    trend="add",
                    seasonal="add",
                    seasonal_periods=self.seasonal_periods,
                    initialization_method="estimated",
                )
            elif len(y) >= 4:
                model = ExponentialSmoothing(
                    y,
                    trend="add",
                    seasonal=None,
                    initialization_method="estimated",
                )
            else:
                self.fitted_model = None
                self.is_fitted = True
                return self

            self.fitted_model = model.fit(optimized=True)
        except Exception:
            # Fallback to simple smoothing without trend/seasonal
            try:
                model = ExponentialSmoothing(y, trend=None, seasonal=None)
                self.fitted_model = model.fit(optimized=True)
            except Exception:
                self.fitted_model = None

        self.is_fitted = True
        return self

    def predict(
        self,
        horizon: int,
        future_df: Optional[pd.DataFrame] = None,
    ) -> np.ndarray:
        if not self.is_fitted or self.fitted_model is None:
            return np.full(horizon, max(0.0, self.last_value))

        try:
            preds = self.fitted_model.forecast(horizon)
            preds = np.asarray(preds, dtype=float)
            return np.maximum(0.0, preds)
        except Exception:
            return np.full(horizon, max(0.0, self.last_value))
