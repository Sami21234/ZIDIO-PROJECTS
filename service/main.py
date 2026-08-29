# service/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
import numpy as np
import joblib

app = FastAPI(title="Project FORESIGHT Scoring Service",
              description="Returns demand forecast and stockout/overstock risk for NorthBay Living SKUs.")

# Load everything once at startup, not per-request
model = joblib.load("models/demand_model.joblib")
risk_df = pd.read_csv("data/processed/risk_scores.csv", dtype={"sku_id": str})
sku_df = pd.read_csv("data/processed/sku_master.csv", dtype={"sku_id": str})


class BatchRequest(BaseModel):
    sku_ids: list[str]


@app.get("/health")
def health():
    return {"status": "ok", "skus_loaded": len(risk_df)}


@app.get("/score/{sku_id}")
def score_sku(sku_id: str):
    """Returns forecast + risk for a single SKU."""
    row = risk_df[risk_df["sku_id"] == sku_id]
    if row.empty:
        # graceful handling of bad input - the brief explicitly requires this
        raise HTTPException(status_code=404, detail=f"SKU '{sku_id}' not found in catalog.")

    r = row.iloc[0]
    return {
        "sku_id": sku_id,
        "description": r["description"],
        "weekly_demand_forecast": round(r["weekly_demand_rate"], 2),
        "on_hand_units": int(r["on_hand_units"]),
        "quadrant": r["quadrant"],
        "value_at_stake_gbp": round(r["value_at_stake"], 2),
    }


@app.post("/batch_score")
def batch_score(request: BatchRequest):
    """Returns forecast + risk for multiple SKUs at once."""
    results = []
    not_found = []
    for sku_id in request.sku_ids:
        row = risk_df[risk_df["sku_id"] == sku_id]
        if row.empty:
            not_found.append(sku_id)
            continue
        r = row.iloc[0]
        results.append({
            "sku_id": sku_id,
            "quadrant": r["quadrant"],
            "value_at_stake_gbp": round(r["value_at_stake"], 2),
        })
    return {"results": results, "not_found": not_found}