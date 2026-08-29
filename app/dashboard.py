
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import joblib

st.set_page_config(page_title="Project FORESIGHT", page_icon="🔮", layout="wide")


# STYLING - visual polish only. Every number below still comes
# from our own real pipeline/model/risk_scoring output.

st.markdown("""
<style>
    .stApp { background: #0d1117; color: #e6edf3; }
    .main-title {
        font-size: 2.2rem; font-weight: 800;
        background: linear-gradient(135deg, #00c6ff 0%, #7b68ee 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0.1rem;
    }
    .sub-title { color: #8b949e; font-size: 1rem; margin-bottom: 1.2rem; }
    .metric-card {
        background: linear-gradient(145deg, rgba(22,27,34,0.9), rgba(13,17,23,0.95));
        border: 1px solid rgba(123,104,238,0.25); border-radius: 12px;
        padding: 1rem; text-align: center; box-shadow: 0 6px 18px rgba(0,0,0,0.3);
    }
    .metric-label { font-size: 0.75rem; color: #8b949e; text-transform: uppercase; letter-spacing: 0.4px; }
    .metric-value { font-size: 1.5rem; font-weight: 800; color: #fff; margin-top: 0.2rem; }
</style>
""", unsafe_allow_html=True)



# LOAD DATA - all real, all produced by our own pipeline/model/risk code

@st.cache_data
def load_data():
    sales = pd.read_csv("data/processed/sales_daily.csv", parse_dates=["date"], dtype={"sku_id": str})
    sku = pd.read_csv("data/processed/sku_master.csv", dtype={"sku_id": str})
    risk = pd.read_csv("data/processed/risk_scores.csv", dtype={"sku_id": str})
    features = pd.read_csv("data/processed/features.csv", parse_dates=["week"], dtype={"sku_id": str})
    return sales, sku, risk, features

sales, sku, risk, features = load_data()


def metric_card(label, value, col):
    col.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
    </div>
    """, unsafe_allow_html=True)



# SIDEBAR NAVIGATION

st.sidebar.markdown("## 🔮 Project FORESIGHT")
st.sidebar.caption("NorthBay Living - Demand & Inventory Intelligence")
page = st.sidebar.radio("Navigate", [
    "🚀 Executive Overview", "📊 Sales & Demand Insights", "🔮 Forecast Performance",
    "⚠️ Risk & Decisioning", "🔍 SKU Explorer", "📝 Methodology & Limitations"
])
st.sidebar.divider()
st.sidebar.caption(f"📦 Catalog: **{sku.shape[0]:,} SKUs**")
st.sidebar.caption(f"📅 History: **{sales.date.min().date()} → {sales.date.max().date()}**")
st.sidebar.caption("🤖 Model: **Gradient-Boosted Trees**")
st.sidebar.caption("📉 WAPE: **0.745** (vs 1.217 baseline)")


# PAGE 1: EXECUTIVE OVERVIEW

if page == "🚀 Executive Overview":
    st.markdown('<div class="main-title">Executive Overview</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Current inventory position, checked against real demand patterns</div>', unsafe_allow_html=True)

    reorder_value = risk.loc[risk.quadrant == "Reorder now", "value_at_stake"].sum()
    markdown_value = risk.loc[risk.quadrant == "Markdown / clear", "value_at_stake"].sum()
    n_reorder = (risk.quadrant == "Reorder now").sum()
    n_markdown = (risk.quadrant == "Markdown / clear").sum()

    c1, c2, c3, c4 = st.columns(4)
    metric_card("SKUs to reorder now", f"{n_reorder}", c1)
    metric_card("Sales at risk", f"£{reorder_value:,.0f}", c2)
    metric_card("SKUs to markdown", f"{n_markdown:,}", c3)
    metric_card("Capital locked", f"£{markdown_value:,.0f}", c4)

    st.write("")
    fig = px.pie(risk, names="quadrant", title="Portfolio risk breakdown", hole=0.5,
                 color="quadrant",
                 color_discrete_map={"Reorder now": "#f85149", "Markdown / clear": "#d29922",
                                      "Watch / volatile": "#a371f7", "Healthy": "#3fb950"})
    fig.update_layout(template="plotly_dark", height=400)
    fig.update_traces(
        textposition = "outside",
        textfont_size = 15,
    )
    st.plotly_chart(fig, use_container_width=True)


# PAGE 2: SALES & DEMAND INSIGHTS

elif page == "📊 Sales & Demand Insights":
    st.markdown('<div class="main-title">Sales & Demand Insights</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        cat_rev = (sales.merge(sku[["sku_id", "category"]], on="sku_id")
                   .groupby("category")["revenue"].sum().sort_values().reset_index())
        fig = px.bar(cat_rev, x="revenue", y="category", orientation="h",
                     title="Revenue by category", color="revenue", color_continuous_scale="Purples")
        fig.update_layout(template="plotly_dark", height=380, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        weekly = sales.groupby(pd.Grouper(key="date", freq="W"))["units_sold"].sum().reset_index()
        fig = px.line(weekly, x="date", y="units_sold", title="Weekly demand trend")
        fig.update_layout(template="plotly_dark", height=380)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    rev_by_sku = sales.groupby("sku_id")["revenue"].sum().sort_values(ascending=False)
    cum_share = (rev_by_sku.cumsum() / rev_by_sku.sum() * 100).reset_index(drop=True)
    sku_share = (np.arange(1, len(rev_by_sku) + 1) / len(rev_by_sku) * 100)
    fig = go.Figure(go.Scatter(x=sku_share, y=cum_share, line=dict(color="#00c6ff", width=3)))
    fig.add_hline(y=80, line_dash="dash", line_color="grey")
    fig.update_layout(template="plotly_dark", title="Revenue concentration (Pareto)",
                       xaxis_title="% of SKUs", yaxis_title="Cumulative % revenue", height=350)
    st.plotly_chart(fig, use_container_width=True)

    top20_pct = int(len(rev_by_sku) * 0.20)
    top20_share = rev_by_sku.head(top20_pct).sum() / rev_by_sku.sum() * 100
    st.info(f"**{top20_pct:,} SKUs (top 20%) drive {top20_share:.1f}% of total revenue.**")


# PAGE 3: FORECAST PERFORMANCE

elif page == "🔮 Forecast Performance":
    st.markdown('<div class="main-title">Forecast Performance</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    metric_card("Model WAPE (backtested)", "0.745", c1)
    metric_card("Baseline WAPE", "1.217", c2)
    st.caption("Rolling-origin cross-validation, 4 folds, no data leakage - model beats baseline by 38.8%.")

    st.divider()
    sku_labels = sku.sort_values("description")["sku_id"] + " - " + sku.sort_values("description")["description"]
    selected = st.selectbox("Select a SKU:", sku_labels)
    selected_id = selected.split(" - ")[0]

    hist = features[features.sku_id == selected_id].sort_values("week")
    if len(hist):
        fig = px.line(hist, x="week", y="units_sold", title=f"Weekly demand history - {selected_id}")
        fig.update_layout(template="plotly_dark", height=400)
        st.plotly_chart(fig, use_container_width=True)


# PAGE 4: RISK & DECISIONING

elif page == "⚠️ Risk & Decisioning":
    st.markdown('<div class="main-title">Risk & Decisioning</div>', unsafe_allow_html=True)

    quadrant_filter = st.selectbox("Filter:", ["All", "Reorder now", "Markdown / clear", "Watch / volatile", "Healthy"])
    view = risk if quadrant_filter == "All" else risk[risk.quadrant == quadrant_filter]

    fig = px.scatter(view, x="overstock_risk_score", y="stockout_risk_score", color="quadrant",
                      size="value_at_stake", size_max=30 , hover_data=["sku_id", "description"],
                      color_discrete_map={"Reorder now": "#f85149", "Markdown / clear": "#d29922",
                                           "Watch / volatile": "#a371f7", "Healthy": "#3fb950"},
                      title="Decisioning grid (sized by £ at stake)")
    fig.add_hline(y=0.5, line_dash="dash", line_color="grey")
    fig.add_vline(x=0.5, line_dash="dash", line_color="grey")
    fig.update_layout(template="plotly_dark", height=500, legend = dict(itemsizing = "constant"))
    fig.update_traces(marker = dict(sizemin = 6))
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        view.sort_values("value_at_stake", ascending=False)
        [["sku_id", "description", "quadrant", "on_hand_units", "weekly_demand_rate", "value_at_stake"]].head(20),
        use_container_width=True, hide_index=True
    )


# PAGE 5: SKU EXPLORER

elif page == "🔍 SKU Explorer":
    st.markdown('<div class="main-title">SKU Explorer</div>', unsafe_allow_html=True)
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
    st.markdown('<div class="main-title">Methodology & Limitations</div>', unsafe_allow_html=True)
    st.markdown("""
    **Forecast model**: Gradient-boosted trees, trained on lag/rolling/calendar/promo features.
    Beats a seasonal-naive baseline by **38.8%** (WAPE 0.745 vs 1.217), validated via 4-fold
    rolling-origin backtesting.

    **Risk scoring**: stockout risk compares forecasted lead-time demand against current stock
    position; overstock risk compares on-hand stock against 8-week forward demand.

    **Known limitations**: `unit_cost` and `inventory_snapshots` are estimated/simulated, not
    observed in the source data. Low-volume, intermittent SKUs have materially higher forecast
    error (WAPE ~2.6) than high-volume SKUs (WAPE ~0.57). Category classification is
    keyword-derived and imperfect.
    """)