
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import joblib

st.set_page_config(page_title="Project FORESIGHT", layout="wide")

# LOAD DATA (cached so switching pages doesn't reload every time)
@st.cache_data
def load_data():
    sales = pd.read_csv("data/processed/sales_daily.csv", parse_dates=["date"], dtype={"sku_id": str})
    sku = pd.read_csv("data/processed/sku_master.csv", dtype={"sku_id": str})
    risk = pd.read_csv("data/processed/risk_scores.csv", dtype={"sku_id": str})
    features = pd.read_csv("data/processed/features.csv", parse_dates=["week"], dtype={"sku_id": str})
    return sales, sku, risk, features

sales, sku, risk, features = load_data()

# SIDEBAR NAVIGATION
st.sidebar.title("🔮 Project FORESIGHT")
st.sidebar.caption("NorthBay Living - Demand & Inventory Intelligence")

page = st.sidebar.radio(
    "Navigate",
    ["🚀 Executive Overview", "📊 Sales & Demand Insights", "🔮 Forecast Performance",
     "⚠️ Risk & Decisioning", "🔍 SKU Explorer", "📝 Methodology & Limitations"]
)

# PAGE 1: EXECUTIVE OVERVIEW
if page == "🚀 Executive Overview":
    st.title("Executive Overview")

    reorder_value = risk.loc[risk.quadrant == "Reorder now", "value_at_stake"].sum()
    markdown_value = risk.loc[risk.quadrant == "Markdown / clear", "value_at_stake"].sum()
    n_reorder = (risk.quadrant == "Reorder now").sum()
    n_markdown = (risk.quadrant == "Markdown / clear").sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("SKUs to reorder now", n_reorder)
    c2.metric("Sales at risk (stockout)", f"£{reorder_value:,.0f}")
    c3.metric("SKUs to markdown/clear", n_markdown)
    c4.metric("Capital locked (overstock)", f"£{markdown_value:,.0f}")

    st.divider()
    st.subheader("Quadrant breakdown")
    st.bar_chart(risk["quadrant"].value_counts())

# PAGE 2: SALES & DEMAND INSIGHTS (the EDA findings, presented for a stakeholder)
elif page == "📊 Sales & Demand Insights":
    st.title("Sales & Demand Insights")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Revenue by category")
        cat_rev = sales.merge(sku[["sku_id", "category"]], on="sku_id").groupby("category")["revenue"].sum().sort_values()
        st.bar_chart(cat_rev)
    with col2:
        st.subheader("Weekly demand trend")
        weekly_total = sales.groupby(pd.Grouper(key="date", freq="W"))["units_sold"].sum()
        st.line_chart(weekly_total)

    st.divider()
    rev_by_sku = sales.groupby("sku_id")["revenue"].sum().sort_values(ascending=False)
    top20_pct = int(len(rev_by_sku) * 0.20)
    top20_share = rev_by_sku.head(top20_pct).sum() / rev_by_sku.sum() * 100
    st.info(f"**{top20_pct:,} SKUs (top 20%) drive {top20_share:.1f}% of total revenue** - "
            f"forecast accuracy and inventory attention should prioritize this group.")

# PAGE 3: FORECAST PERFORMANCE
elif page == "🔮 Forecast Performance":
    st.title("Forecast Performance")

    st.metric("Model WAPE (backtested)", "0.745", delta="-38.8% vs baseline", delta_color="normal")
    st.caption("Baseline (seasonal-naive) WAPE: 1.217 - validated via rolling-origin cross-validation, 4 folds, no data leakage.")

    st.divider()
    sku_labels = (sku.sort_values("description")["sku_id"] + " - " + sku.sort_values("description")["description"])
    selected = st.selectbox("Select a SKU:", sku_labels)
    selected_id = selected.split(" - ")[0]

    hist = features[features.sku_id == selected_id].sort_values("week")
    if len(hist):
        st.line_chart(hist.set_index("week")["units_sold"])
    else:
        st.info("No history for this SKU.")

# PAGE 4: RISK & DECISIONING (the brief's Section 08 quadrant grid)
elif page == "⚠️ Risk & Decisioning":
    st.title("Risk & Decisioning")

    quadrant_filter = st.selectbox("Filter:", ["All", "Reorder now", "Markdown / clear", "Watch / volatile", "Healthy"])
    view = risk if quadrant_filter == "All" else risk[risk.quadrant == quadrant_filter]

    st.subheader("Decisioning grid")
    fig, ax = plt.subplots(figsize=(8, 6))
    colors = {"Reorder now": "#d62728", "Markdown / clear": "#7b68ee",
              "Watch / volatile": "#ff9800", "Healthy": "#2ca02c"}
    for q, color in colors.items():
        sub = risk[risk.quadrant == q]
        ax.scatter(sub["overstock_risk_score"], sub["stockout_risk_score"],
                   s=np.clip(sub["value_at_stake"] / 200, 10, 300), alpha=0.5, color=color, label=q)
    ax.axhline(0.5, color="grey", ls="--", lw=0.8)
    ax.axvline(0.5, color="grey", ls="--", lw=0.8)
    ax.set_xlabel("Overstock risk"); ax.set_ylabel("Stockout risk")
    ax.legend()
    st.pyplot(fig)

    st.subheader("Priority list")
    st.dataframe(
        view.sort_values("value_at_stake", ascending=False)
        [["sku_id", "description", "quadrant", "on_hand_units", "weekly_demand_rate", "value_at_stake"]].head(20),
        use_container_width=True, hide_index=True
    )

# PAGE 5: SKU EXPLORER
elif page == "🔍 SKU Explorer":
    st.title("SKU Explorer")

    categories = st.multiselect("Filter by category:", sku["category"].unique())
    explorer = risk.merge(sku[["sku_id", "category"]], on="sku_id", how="left")
    if categories:
        explorer = explorer[explorer["category"].isin(categories)]

    st.dataframe(
        explorer[["sku_id", "description", "category", "quadrant", "on_hand_units",
                  "weekly_demand_rate", "value_at_stake"]].sort_values("value_at_stake", ascending=False),
        use_container_width=True, hide_index=True
    )

# PAGE 6: METHODOLOGY & LIMITATIONS
elif page == "📝 Methodology & Limitations":
    st.title("Methodology & Limitations")
    st.markdown("""
    **Forecast model**: HistGradientBoostingRegressor trained on lag (1/2/4/8/52 week), rolling-average,
    calendar, and promo features. Beats a seasonal-naive baseline by **38.8%** (WAPE 0.745 vs 1.217),
    validated via 4-fold rolling-origin backtesting - never a random split, which would leak future data.

    **Risk scoring**: stockout risk compares forecasted lead-time demand against current stock position
    (on-hand + on-order); overstock risk compares on-hand stock against an 8-week forward demand estimate.

    **Known limitations**:
    - `unit_cost` and `inventory_snapshots` are estimated/simulated, not observed in the source data
    - Low-volume, intermittent SKUs have materially higher forecast error (WAPE ~2.6) than high-volume SKUs (WAPE ~0.57)
    - Category classification is keyword-derived and imperfect (~52% fall into "General Merchandise")

    See `reports/data_cleaning_report.md` and `reports/eda_insight_memo.md` for full detail.
    """)