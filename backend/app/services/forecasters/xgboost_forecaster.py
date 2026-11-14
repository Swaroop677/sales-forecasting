from typing import Optional

import numpy as np
import pandas as pd
import xgboost as xgb
from backend.app.config import settings
from backend.app.services.feature_builder import build_feature_matrix
from backend.app.services.forecasters.base import Forecaster


class XGBoostForecaster(Forecaster):
    """
    XGBoost Gradient Boosted Trees forecaster.
    Engineered features:
    - Cyclical calendar attributes
    - Multi-horizon lag variables
    - Rolling window summary statistics
    - Dynamic promotional and pricing regressors
    Generates multi-step forecasts iteratively.
    """

    def __init__(self, n_estimators: int = 100, learning_rate: float = 0.05):
        super().__init__(name="XGBoost")
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.model: Optional[xgb.XGBRegressor] = None
        self.feature_columns: list[str] = []
        self.history_df: Optional[pd.DataFrame] = None

    def fit(
        self,
        df: pd.DataFrame,
        date_col: str,
        target_col: str,
        regressor_cols: Optional[list[str]] = None,
    ) -> "XGBoostForecaster":
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

        self.model = xgb.XGBRegressor(
            n_estimators=self.n_estimators,
            learning_rate=self.learning_rate,
            max_depth=5,
            n_jobs=settings.N_JOBS,
            random_state=42,
            verbosity=0,
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

        last_date = pd.to_datetime(self.history_df[self.date_col].iloc[-1])
        future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=horizon, freq="D")

        working_df = self.history_df.copy()
        predictions = []

        for step in range(horizon):
            curr_date = future_dates[step]

            curr_regressors = {}
            for reg in self.regressor_cols:
                if future_df is not None and reg in future_df.columns and len(future_df) > step:
                    curr_regressors[reg] = future_df[reg].iloc[step]
                else:
                    curr_regressors[reg] = working_df[reg].iloc[-1] if reg in working_df.columns else 0.0

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

            X_curr = X_full.iloc[[-1]][self.feature_columns]

            pred_val = float(self.model.predict(X_curr)[0])
            pred_val = max(0.0, pred_val)
            predictions.append(pred_val)

            temp_row[self.target_col] = pred_val
            working_df = pd.concat([working_df, temp_row], ignore_index=True)

        return np.array(predictions)
