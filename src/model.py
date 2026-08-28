import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

FEATURE_COLS = ["lag_1", "lag_2", "lag_4", "lag_8", "lag_52", "roll_mean_4", "roll_std_4",
                 "roll_mean_8", "promo_rate_lag1", "month", "is_holiday", "unit_cost", "list_price"]
CAT_COLS = ["category", "season"]


def wape(actual, forecast) -> float:
    actual = np.asarray(actual)
    forecast = np.asarray(forecast)
    return np.sum(np.abs(actual - forecast)) / np.sum(actual)


def prepare_model_data(features_df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows with no lag_1 history (first week per SKU) and set categorical dtypes."""
    df = features_df.dropna(subset=["lag_1"]).copy()
    for c in CAT_COLS:
        df[c] = df[c].astype("category")
    return df


def train_model(train_df: pd.DataFrame) -> HistGradientBoostingRegressor:
    X_train = train_df[FEATURE_COLS + CAT_COLS]
    y_train = train_df["target"]
    model = HistGradientBoostingRegressor(categorical_features=CAT_COLS, random_state=42, max_iter=200)
    model.fit(X_train, y_train)
    return model


def predict(model, df: pd.DataFrame) -> np.ndarray:
    X = df[FEATURE_COLS + CAT_COLS]
    return np.clip(model.predict(X), 0, None)  # demand can't be negative