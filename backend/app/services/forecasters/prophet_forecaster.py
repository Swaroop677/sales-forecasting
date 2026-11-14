from typing import Optional

import numpy as np
import pandas as pd
from backend.app.config import settings
from backend.app.services.forecasters.base import Forecaster


class ProphetForecaster(Forecaster):
    """
    Facebook Prophet forecaster (OPTIONAL).
    Lazy-loads Prophet only when invoked and ENABLE_PROPHET is set to True.
    """

    def __init__(self):
        super().__init__(name="Prophet")
        if not settings.ENABLE_PROPHET:
            raise RuntimeError(
                "Prophet is disabled by default to stay within free-host memory limits. "
                "Set ENABLE_PROPHET=true in your environment to enable."
            )
        try:
            from prophet import Prophet
            self.Prophet = Prophet
        except ImportError:
            raise ImportError(
                "Prophet is not installed. Run `pip install prophet` or set ENABLE_PROPHET=false."
            )

        self.model = None

    def fit(
        self,
        df: pd.DataFrame,
        date_col: str,
        target_col: str,
        regressor_cols: Optional[list[str]] = None,
    ) -> "ProphetForecaster":
        self.date_col = date_col
        self.target_col = target_col
        self.regressor_cols = regressor_cols or []

        prophet_df = pd.DataFrame()
        prophet_df["ds"] = pd.to_datetime(df[date_col])
        prophet_df["y"] = pd.to_numeric(df[target_col], errors="coerce").fillna(0)

        # Initialize Prophet with modest computation settings
        self.model = self.Prophet(
            daily_seasonality=False,
            weekly_seasonality=True,
            yearly_seasonality=True,
        )

        for reg in self.regressor_cols:
            if reg in df.columns:
                prophet_df[reg] = pd.to_numeric(df[reg], errors="coerce").fillna(0)
                self.model.add_regressor(reg)

        self.model.fit(prophet_df)
        self.is_fitted = True
        return self

    def predict(
        self,
        horizon: int,
        future_df: Optional[pd.DataFrame] = None,
    ) -> np.ndarray:
        if not self.is_fitted or self.model is None:
            return np.zeros(horizon)

        future = self.model.make_future_dataframe(periods=horizon, freq="D", include_history=False)
        for reg in self.regressor_cols:
            if future_df is not None and reg in future_df.columns and len(future_df) >= horizon:
                future[reg] = future_df[reg].iloc[:horizon].values
            else:
                future[reg] = 0.0

        forecast = self.model.predict(future)
        preds = forecast["yhat"].values.astype(float)
        return np.maximum(0.0, preds)
