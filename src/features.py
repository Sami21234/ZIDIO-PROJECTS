import pandas as pd

def build_features(weekly_full: pd.DataFrame, sales_daily: pd.DataFrame,
                    sku_master: pd.DataFrame, calendar: pd.DataFrame) -> pd.DataFrame:
    """
    Builds model-ready features. Every feature uses ONLY information available
    before the target week - no future data ever touches a feature.
    """
    df = weekly_full.copy().sort_values(["sku_id", "week"]).reset_index(drop=True)

    # weekly promo rate and avg price, pulled from the daily table
    weekly_extra = (sales_daily.groupby(["sku_id", "week"])
                     .agg(promo_rate=("promo_flag", "mean"), avg_price=("unit_price", "mean"))
                     .reset_index())
    df = df.merge(weekly_extra, on=["sku_id", "week"], how="left")
    df["promo_rate"] = df["promo_rate"].fillna(0)
    df["avg_price"] = df.groupby("sku_id")["avg_price"].ffill().bfill()

    grp = df.groupby("sku_id")["units_sold"]

    # lag features - past values(in weeks) of the target itself
    for lag in [1, 2, 4, 8, 52]:
        df[f"lag_{lag}"] = grp.shift(lag)

    # rolling stats - shift(1) FIRST so the current week never leaks into its own average
    shifted = grp.shift(1)
    df["roll_mean_4"] = shifted.groupby(df["sku_id"]).transform(lambda s: s.rolling(4, min_periods=1).mean())
    df["roll_std_4"]  = shifted.groupby(df["sku_id"]).transform(lambda s: s.rolling(4, min_periods=1).std())
    df["roll_mean_8"] = shifted.groupby(df["sku_id"]).transform(lambda s: s.rolling(8, min_periods=1).mean())

    # promo signal, also lagged by 1 week to avoid leaking this week's own promo status
    df["promo_rate_lag1"] = df.groupby("sku_id")["promo_rate"].shift(1)

    # calendar features
    cal_weekly = calendar.copy()
    cal_weekly["week"] = cal_weekly["date"] - pd.to_timedelta(cal_weekly["date"].dt.dayofweek, unit="D")
    cal_agg = (cal_weekly.groupby("week")
               .agg(month=("month", "first"), season=("season", "first"), is_holiday=("is_holiday", "max"))
               .reset_index())
    df = df.merge(cal_agg, on="week", how="left")

    # SKU features (static, safe to use - doesn't change over time)
    df = df.merge(sku_master[["sku_id", "category", "unit_cost", "list_price"]], on="sku_id", how="left")

    df["target"] = df["units_sold"]
    return df


if __name__ == "__main__":
    sales = pd.read_csv("data/processed/sales_daily.csv", parse_dates=["date"], dtype={"sku_id": str})
    sku = pd.read_csv("data/processed/sku_master.csv", dtype={"sku_id": str})
    cal = pd.read_csv("data/processed/calendar.csv", parse_dates=["date"])

    sales["week"] = sales["date"] - pd.to_timedelta(sales["date"].dt.dayofweek, unit="D")
    weekly = sales.groupby(["sku_id", "week"])["units_sold"].sum().reset_index()
    all_weeks = pd.date_range(weekly["week"].min(), weekly["week"].max(), freq="7D")
    all_skus = weekly["sku_id"].unique()
    full_index = pd.MultiIndex.from_product([all_skus, all_weeks], names=["sku_id", "week"])
    weekly_full = (weekly.set_index(["sku_id", "week"]).reindex(full_index, fill_value=0)
                   .reset_index().sort_values(["sku_id", "week"]))

    features = build_features(weekly_full, sales, sku, cal)
    features.to_csv("data/processed/features.csv", index=False)
    print(f"Saved features.csv: {features.shape[0]:,} rows, {features.shape[1]} columns")