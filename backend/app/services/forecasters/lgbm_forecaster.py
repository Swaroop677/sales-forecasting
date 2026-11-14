from typing import Optional

import lightgbm as lgb
import numpy as np
import pandas as pd
from backend.app.config import settings
from backend.app.services.feature_builder import (
    build_feature_matrix,
)
from backend.app.services.forecasters.base import Forecaster


class LightGBMForecaster(Forecaster):
    """
    LightGBM Gradient Boosted Decision Tree forecaster.
    Engineered features:
    - Calendar / cyclical time encodings (day of week, month, weekend)
    - Lag features (1, 2, 3, 7, 14, 21, 28)
    - Rolling window statistics (mean 7/14/28, std 7)
    - External dynamic regressors (promo, price, traffic)
    Generates multi-step predictions via iterative autoregressive recursion.
    """

    def __init__(self, n_estimators: int = 120, learning_rate: float = 0.05):
        super().__init__(name="LightGBM")
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.model: Optional[lgb.LGBMRegressor] = None
        self.feature_columns: list[str] = []
        self.history_df: Optional[pd.DataFrame] = None

    def fit(
        self,
        df: pd.DataFrame,
        date_col: str,
        target_col: str,
        regressor_cols: Optional[list[str]] = None,
    ) -> "LightGBMForecaster":
        self.date_col = date_col
        self.target_col = target_col
        self.regressor_cols = regressor_cols or []
        self.history_df = df.copy().sort_values(by=date_col).reset_index(drop=True)

        X = build_feature_matrix(
            df=self.history_df,
            date_col=date_col,
            target_col=target_col,
            regressor_cols=self.regressor_cols,
        )
        y = pd.to_numeric(self.history_df[target_col], errors="coerce").fillna(0).values

        self.feature_columns = list(X.columns)

        self.model = lgb.LGBMRegressor(
            n_estimators=self.n_estimators,
            learning_rate=self.learning_rate,
            num_leaves=31,
            max_depth=6,
            n_jobs=settings.N_JOBS,
            random_state=42,
            verbosity=-1,
        )
        self.model.fit(X, y)
        self.is_fitted = True
        return self

    def predict(
        self,
        horizon: int,
        future_df: Optional[pd.DataFrame] = None,
    ) -> np.ndarray:
        if not self.is_fitted or self.model is None or self.history_df is None:
            return np.zeros(horizon)

        # Build future dates
        last_date = pd.to_datetime(self.history_df[self.date_col].iloc[-1])
        future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=horizon, freq="D")

        # Create working history for recursive forecasting
        working_df = self.history_df.copy()
        predictions = []

        for step in range(horizon):
            curr_date = future_dates[step]

            # If future regressors are provided in future_df, use them; otherwise use recent values
            curr_regressors = {}
            for reg in self.regressor_cols:
                if future_df is not None and reg in future_df.columns and len(future_df) > step:
                    curr_regressors[reg] = future_df[reg].iloc[step]
                else:
                    curr_regressors[reg] = working_df[reg].iloc[-1] if reg in working_df.columns else 0.0

            # Row to predict: combine calendar + regressors + lags from working_df
            temp_row = pd.DataFrame([{
                self.date_col: curr_date.strftime("%Y-%m-%d"),
                self.target_col: np.nan,
                **curr_regressors,
            }])

            combined_df = pd.concat([working_df, temp_row], ignore_index=True)
            X_full = build_feature_matrix(
                df=combined_df,
                date_col=self.date_col,
                target_col=self.target_col,
                regressor_cols=self.regressor_cols,
            )

            # Extract features for current row
            X_curr = X_full.iloc[[-1]][self.feature_columns]

            # Predict next step
            pred_val = float(self.model.predict(X_curr)[0])
            pred_val = max(0.0, pred_val)
            predictions.append(pred_val)

            # Update working_df with the predicted value for recursive steps
            temp_row[self.target_col] = pred_val
            working_df = pd.concat([working_df, temp_row], ignore_index=True)

        return np.array(predictions)
