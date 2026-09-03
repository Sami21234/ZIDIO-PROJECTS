# Project FORESIGHT - Demand & Inventory Intelligence
**Zidio Internship · Data Science & Analytics · Client: NorthBay Living**

A 4-week engagement to build a demand forecasting and stockout/overstock risk system for
NorthBay Living, a D2C home & lifestyle brand. Full brief: `Zidio_Project_Data_1_1.pdf`.

---

## Cohort submission form with all links

| | |
|---|---|
| 💻 **Source Code** | https://github.com/Sami21234/ZIDIO-PROJECTS |
| 📊 **Dashboard** | https://zidio-foresight.streamlit.app/ |
| 🔌 **Scoring API** | https://foresight-scoring-api-xz0j.onrender.com |
| 📄 **API docs** | https://foresight-scoring-api-xz0j.onrender.com/docs |
| ◀️ **Demo Video** | https://www.youtube.com/watch?v=5pBaBf9y710 |
| 📝 **[Project Report](reports\FORESIGHT_Final_Report.pdf)** 

---

## The Problem

NorthBay Living plans inventory by gut feel. Best-sellers stock out (lost sales); slow
movers pile up (locked-up cash, eventual markdowns). This project builds a system that
tells the operations team, for every product, every week: how much will it sell, is it
about to run out, and is there too much of it sitting in the warehouse.

## The Data

Source: [Online Retail II (UCI)](https://archive.ics.uci.edu/dataset/502/online+retail+ii)
- real UK online retailer transactions, Dec 2009 – Dec 2011, ~1.07M raw rows.

Reshaped into a 4-table star schema per the brief's spec:
- `sales_daily` (fact) - one row per SKU per day
- `sku_master` (dim) - one row per SKU
- `calendar` (dim) - one row per date
- `inventory_snapshots` (dim) - periodic stock position per SKU

## Setup & Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the pipeline (raw data -> 4 processed tables)
python -m src.pipeline --input data/raw/online_retail_II_combined.csv --outdir data/processed

# 3. Build features
python -m src.features

# 4. Train the model (saves to models/demand_model.joblib)
python -m src.model

# 5. Run the backtest (prints model WAPE vs baseline WAPE)
python -m src.rolling_cv

# 6. Score risk for every SKU
python -m src.risk_scoring

# 7. Launch the dashboard
streamlit run app/dashboard.py

# 8. Launch the scoring API
uvicorn service.main:app --reload
```

**Note on scikit-learn version**: `models/demand_model.joblib` is pickled with the
scikit-learn version in `requirements.txt`. If you're on a different version, re-run
step 4 to regenerate the model file - loading a model pickled by a different
scikit-learn version can fail.

## Backtest Result (the headline number)

| | WAPE |
|---|---|
| Seasonal-naive baseline | 1.217 |
| **Our model (gradient-boosted trees)** | **0.745** |
| **Improvement** | **38.8%** |

Validated via 4-fold rolling-origin cross-validation (never a random split - that would
leak future data into training). Full detail in `reports/eda_insight_memo.md` and the
model beat the baseline consistently across every single fold, not just on average.

**Where accuracy is strongest**: high-volume SKUs (WAPE ~0.57). **Where it's weakest**:
low-volume, intermittent SKUs (WAPE ~2.6) - reported honestly, not hidden.

## Key Assumptions

| Field | Assumption |
|---|---|
| `unit_cost` | Not in source data - estimated from list price using an assumed category-level gross margin (45–55%) |
| `inventory_snapshots` | Not in source data at all - simulated via an (s, S) reorder policy driven by each SKU's own observed demand |
| `promo_flag` | Inferred from a ≥15% price drop vs. the SKU's own 30-day rolling median, since no promotion field exists in source data |
| `category` / `subcategory` | Derived from keyword matching on free-text product descriptions (no product hierarchy in source data); ~52% fall into a "General Merchandise" catch-all |

Full cleaning decisions and rationale: `reports/data_cleaning_report.md`.

## Repository Structure

```
foresight_demand_&_inventory_intelligence/
        app/dashboard.py         # Streamlit dashboard (6 pages)
        service/main.py          # FastAPI scoring service
        src/
          pipeline.py             # raw data -> 4-table schema
          features.py             # lag/rolling/calendar/promo feature engineering
          model.py                 # train/predict the demand model
          rolling_cv.py            # rolling-origin backtest vs baseline
          error_analysis.py        # WAPE breakdown by category/volume tier
          risk_scoring.py           # stockout/overstock risk + decisioning grid
        data/
          raw/                       # source extract (gitignored, regenerable)
          processed/                 # 4 schema tables + features + risk_scores
        models/demand_model.joblib  # trained model
        reports/
          data_cleaning_report.md   # D1 - cleaning steps + before/after evidence
          eda_insight_memo.md        # D2 - full EDA, univariate/bivariate/multivariate
          executive_readout.md       # D7 - stakeholder-facing summary
          figures/                    # all EDA charts
        requirements.txt
```

## Tech Stack

Python, pandas, numpy, scikit-learn (HistGradientBoostingRegressor), Streamlit, FastAPI,
matplotlib/Plotly.

## Deliverables Checklist (per brief Section 13)

- [x] Git repository - pipeline, notebooks, model code
- [x] Live dashboard URL
- [x] Live scoring-service URL
- [x] This README - problem, data, setup, backtest result, assumptions
- [x] Executive readout + data-quality/EDA memo
- [x] 3–5 minute demo video (unlisted link)
- [x] Cohort submission form with all links
