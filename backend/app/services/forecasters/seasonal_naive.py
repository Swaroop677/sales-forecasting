from typing import Optional

import numpy as np
import pandas as pd
from backend.app.services.forecasters.base import Forecaster


class SeasonalNaiveForecaster(Forecaster):
    """
    Seasonal Naive baseline forecaster.
    Repeats the last observed seasonal cycle (default period = 7 for daily sales).
    Acts as the standard benchmark model in retail demand forecasting.
    """

    def __init__(self, season_length: int = 7):
        super().__init__(name="Seasonal Naive")
        self.season_length = season_length
        self.last_season: np.ndarray = np.array([])
        self.last_value: float = 0.0

    def fit(
        self,
        df: pd.DataFrame,
        date_col: str,
        target_col: str,
        regressor_cols: Optional[list[str]] = None,
    ) -> "SeasonalNaiveForecaster":
        self.date_col = date_col
        self.target_col = target_col
        self.regressor_cols = regressor_cols or []

        y = pd.to_numeric(df[target_col], errors="coerce").fillna(0).values
        if len(y) == 0:
            self.last_season = np.array([0.0])
            self.last_value = 0.0
        else:
            self.last_value = float(y[-1])
            if len(y) >= self.season_length:
                self.last_season = y[-self.season_length :].astype(float)
            else:
                self.last_season = y.astype(float)

        self.is_fitted = True
        return self

    def predict(
        self,
        horizon: int,
        future_df: Optional[pd.DataFrame] = None,
    ) -> np.ndarray:
        if not self.is_fitted or len(self.last_season) == 0:
            return np.zeros(horizon)

        # Tile seasonal pattern to cover horizon
        reps = int(np.ceil(horizon / len(self.last_season)))
        tiled = np.tile(self.last_season, reps)
        preds = tiled[:horizon]
        return np.maximum(0.0, preds)
