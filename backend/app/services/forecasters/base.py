from abc import ABC, abstractmethod
from typing import Optional

import numpy as np
import pandas as pd


class Forecaster(ABC):
    """
    Abstract base forecaster interface.
    All models must implement:
    - fit(df, date_col, target_col, regressor_cols)
    - predict(horizon, future_df) -> np.ndarray
    """

    def __init__(self, name: str):
        self.name = name
        self.is_fitted = False
        self.date_col = ""
        self.target_col = ""
        self.regressor_cols: list[str] = []

    @abstractmethod
    def fit(
        self,
        df: pd.DataFrame,
        date_col: str,
        target_col: str,
        regressor_cols: Optional[list[str]] = None,
    ) -> "Forecaster":
        """Fits the model onto historical training data."""
        pass

    @abstractmethod
    def predict(
        self,
        horizon: int,
        future_df: Optional[pd.DataFrame] = None,
    ) -> np.ndarray:
        """
        Forecasts forward by `horizon` time steps.
        Returns 1D numpy array of forecasted values of length `horizon`.
        """
        pass
