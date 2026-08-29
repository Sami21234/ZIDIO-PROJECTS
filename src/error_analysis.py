import pandas as pd
import numpy as np
import joblib

FEATURE_COLS = ["lag_1","lag_2","lag_4","lag_8","lag_52","roll_mean_4","roll_std_4",
                 "roll_mean_8","promo_rate_lag1","month","is_holiday","unit_cost","list_price"]
CAT_COLS = ["category","season"]


def wape(a, f):
    a, f = np.asarray(a), np.asarray(f)
    return np.sum(np.abs(a - f)) / np.sum(a) if np.sum(a) > 0 else np.nan


def analyze_errors(model, test_df: pd.DataFrame) -> dict:
    test_df = test_df.copy()
    test_df["pred"] = np.clip(model.predict(test_df[FEATURE_COLS + CAT_COLS]), 0, None)

    by_category = test_df.groupby("category").apply(lambda g: wape(g.target, g.pred), include_groups=False)

    sku_vol = test_df.groupby("sku_id")["target"].sum()
    active = sku_vol[sku_vol > 0]
    tiers = pd.qcut(active, 3, labels=["Low volume", "Mid volume", "High volume"], duplicates="drop")
    test_df["vol_tier"] = test_df["sku_id"].map(tiers)
    by_volume = test_df[test_df.vol_tier.notna()].groupby("vol_tier", observed=True).apply(
        lambda g: wape(g.target, g.pred), include_groups=False)

    return {"by_category": by_category.sort_values(), "by_volume": by_volume}


if __name__ == "__main__":
    df = pd.read_csv("data/processed/features.csv", parse_dates=["week"], dtype={"sku_id": str})
    model_df = df.dropna(subset=["lag_1"]).copy()
    for c in CAT_COLS:
        model_df[c] = model_df[c].astype("category")

    model = joblib.load("models/demand_model.joblib")
    all_weeks = sorted(model_df["week"].unique())
    test = model_df[model_df["week"].isin(all_weeks[-8:])]

    results = analyze_errors(model, test)
    print("WAPE by category:\n", results["by_category"])
    print("\nWAPE by volume tier:\n", results["by_volume"])