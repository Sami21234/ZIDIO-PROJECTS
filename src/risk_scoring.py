import numpy as np
import pandas as pd
import joblib

FEATURE_COLS = ["lag_1", "lag_2", "lag_4", "lag_8", "lag_52", "roll_mean_4", "roll_std_4",
                 "roll_mean_8", "promo_rate_lag1", "month", "is_holiday", "unit_cost", "list_price"]
CAT_COLS = ["category", "season"]


def score_risk(features_df: pd.DataFrame, inventory_df: pd.DataFrame,
               sku_master: pd.DataFrame, model) -> pd.DataFrame:
    """
    Combines the demand model's forecast with each SKU's current inventory
    position to produce a stockout/overstock risk score, quadrant, and the
    rupee value at stake - Section 08 of the brief.
    """
    latest = features_df.sort_values("week").groupby("sku_id").tail(1).copy()
    latest["weekly_demand_rate"] = np.clip(model.predict(latest[FEATURE_COLS + CAT_COLS]), 0, None)

    latest_inv = inventory_df.sort_values("date").groupby("sku_id").tail(1)

    risk = (latest[["sku_id", "weekly_demand_rate"]]
            .merge(latest_inv[["sku_id", "on_hand_units", "on_order_units",
                                "lead_time_days", "reorder_point"]], on="sku_id", how="inner")
            .merge(sku_master[["sku_id", "description", "unit_cost", "list_price"]],
                   on="sku_id", how="left"))

    # Stockout risk: demand expected during supplier lead time vs current position
    risk["lead_time_weeks"] = risk["lead_time_days"] / 7
    risk["demand_during_leadtime"] = risk["weekly_demand_rate"] * risk["lead_time_weeks"]
    risk["projected_position"] = (risk["on_hand_units"] + risk["on_order_units"]
                                    - risk["demand_during_leadtime"])
    risk["stockout_risk_score"] = np.clip(
        1 - (risk["projected_position"] / risk["reorder_point"].replace(0, np.nan)).fillna(1), 0, 1
    )

    # Overstock risk: on-hand vs 8-week forward demand
    risk["demand_8wk"] = risk["weekly_demand_rate"] * 8
    risk["overstock_ratio"] = risk["on_hand_units"] / risk["demand_8wk"].replace(0, np.nan)
    risk["overstock_risk_score"] = np.clip((risk["overstock_ratio"] - 1) / 3, 0, 1).fillna(0)

    # Quadrant classification (Section 08's decisioning grid)
    def quadrant(row):
        high_out = row["stockout_risk_score"] >= 0.5
        high_over = row["overstock_risk_score"] >= 0.5
        if high_out and not high_over:
            return "Reorder now"
        if high_over and not high_out:
            return "Markdown / clear"
        if high_out and high_over:
            return "Watch / volatile"
        return "Healthy"

    risk["quadrant"] = risk.apply(quadrant, axis=1)

    # Rupee value at stake
    risk["value_at_stake"] = np.where(
        risk["quadrant"] == "Reorder now", risk["demand_during_leadtime"] * risk["list_price"],
        np.where(risk["quadrant"] == "Markdown / clear", risk["on_hand_units"] * risk["unit_cost"], 0)
    ).round(2)

    return risk


if __name__ == "__main__":
    features = pd.read_csv("data/processed/features.csv", parse_dates=["week"], dtype={"sku_id": str})
    features = features.dropna(subset=["lag_1"]).copy()
    for c in CAT_COLS:
        features[c] = features[c].astype("category")

    inv = pd.read_csv("data/processed/inventory_snapshots.csv", parse_dates=["date"], dtype={"sku_id": str})
    sku = pd.read_csv("data/processed/sku_master.csv", dtype={"sku_id": str})
    model = joblib.load("models/demand_model.joblib")

    risk = score_risk(features, inv, sku, model)
    print(risk["quadrant"].value_counts())
    print()
    print(risk.sort_values("value_at_stake", ascending=False)
          [["sku_id", "description", "quadrant", "value_at_stake"]].head(8))

    risk.to_csv("data/processed/risk_scores.csv", index=False)
    print("\nSaved: data/processed/risk_scores.csv")