# src/baseline.py
import pandas as pd
import numpy as np


def build_weekly_grid(sales_daily: pd.DataFrame) -> pd.DataFrame:
    """Aggregate daily sales to a complete SKU x week grid (zero-filled)."""
    sales_daily = sales_daily.copy()
    # Monday of each date's week, computed directly - avoids the
    # to_period("W-MON") vs date_range(freq="W-MON") anchor mismatch
    # that caused the NaN bug (they don't agree on which day a "week" starts).
    sales_daily["week"] = sales_daily["date"] - pd.to_timedelta(sales_daily["date"].dt.dayofweek, unit="D")
    weekly = sales_daily.groupby(["sku_id", "week"])["units_sold"].sum().reset_index()

    all_weeks = pd.date_range(weekly["week"].min(), weekly["week"].max(), freq="7D")
    all_skus = weekly["sku_id"].unique()
    full_index = pd.MultiIndex.from_product([all_skus, all_weeks], names=["sku_id", "week"])

    return (weekly.set_index(["sku_id", "week"])
                   .reindex(full_index, fill_value=0)
                   .reset_index()
                   .sort_values(["sku_id", "week"]))


def add_seasonal_naive(weekly_full: pd.DataFrame, season_length: int = 52) -> pd.DataFrame:
    """
    Forecast = same week, one season-cycle ago, WITH a fallback:
    if that exact week is unavailable/zero (common with intermittent
    demand + only ~2 years of history), fall back to a trailing 4-week
    average instead of blindly forecasting 0 for a SKU that's still active.
    """
    weekly_full = weekly_full.copy()
    grp = weekly_full.groupby("sku_id")["units_sold"]

    pure_seasonal = grp.shift(season_length)
    trailing_avg = grp.transform(lambda s: s.shift(1).rolling(4, min_periods=1).mean())

    weekly_full["seasonal_naive_forecast"] = pure_seasonal  # kept for reporting, unmodified
    weekly_full["baseline_forecast"] = pure_seasonal.where(
        pure_seasonal.notna() & (pure_seasonal > 0), trailing_avg
    )
    return weekly_full


def wape(actual, forecast) -> float:
    actual = np.asarray(actual)
    forecast = np.asarray(forecast)
    return np.sum(np.abs(actual - forecast)) / np.sum(actual)


if __name__ == "__main__":
    sales = pd.read_csv("data/processed/sales_daily.csv", parse_dates=["date"], dtype={"sku_id": str})
    weekly_full = build_weekly_grid(sales)
    weekly_full = add_seasonal_naive(weekly_full)

    eval_set = weekly_full.dropna(subset=["seasonal_naive_forecast"])
    pure_wape = wape(eval_set["units_sold"], eval_set["seasonal_naive_forecast"])
    blended_wape = wape(eval_set["units_sold"], eval_set["baseline_forecast"])

    print(f"Pure seasonal-naive WAPE:        {pure_wape:.3f}  (reported honestly, weak due to intermittency)")
    print(f"Seasonal-naive + fallback WAPE:  {blended_wape:.3f}  (this is the bar Week 3 must beat)")

    weekly_full.to_csv("data/processed/weekly_demand_with_baseline.csv", index=False)
    print("Saved: data/processed/weekly_demand_with_baseline.csv")

    """

    Seasonal-naive baseline WAPE = 1.235 (all SKUs), driven by two distinct causes found through investigation: (1) demand intermittency - many SKUs have no sales in the exact comparison week a year prior, and (2) per-SKU trend - some top sellers decline in popularity over the 2-year window even as total company revenue grows, which a naive "repeat last year" forecast cannot capture. Both motivate a feature-based model for Week 3.

    """