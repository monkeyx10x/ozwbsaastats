import streamlit as st
import requests
import pandas as pd
import plotly.express as px

API_URL = "https://ozwbsaastats.onrender.com/upload-csv"

st.set_page_config(
    page_title="Marketplace SaaS",
    layout="wide"
)

st.title("📊 Marketplace Profit Dashboard")

st.markdown(
    "Upload WB/Ozon CSV and detect profit leaks instantly."
)

uploaded_file = st.file_uploader(
    "Upload marketplace CSV",
    type=["csv"]
)

if uploaded_file:

    files = {
        "file": uploaded_file.getvalue()
    }

    with st.spinner("Analyzing data..."):

        response = requests.post(
            API_URL,
            files=files
        )

    if response.status_code != 200:
        st.error("Backend error")
        st.stop()

    data = response.json()

    if "error" in data:
        st.error(data["error"])
        st.stop()

    summary = data["summary"]
    insights = data["insights"]
    actions = data["actions"]

    df = pd.DataFrame(data["products"])

    # =========================
    # KPI CARDS
    # =========================

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "💰 Revenue",
            f"{summary['total_revenue']:,.0f} ₽"
        )

    with col2:
        st.metric(
            "📈 Profit",
            f"{summary['total_profit']:,.0f} ₽"
        )

    with col3:
        st.metric(
            "📊 Avg Margin",
            f"{summary['avg_margin']:.1f}%"
        )

    with col4:
        st.metric(
            "🚀 Avg ROI",
            f"{summary['avg_roi']:.1f}%"
        )

    with col5:
        st.metric(
            "🔴 Total Loss",
            f"{summary['total_loss']:,.0f} ₽"
        )

    st.divider()

    # =========================
    # ALERTS
    # =========================

    if summary["total_loss"] < 0:

        st.error(
            f"⚠ You are losing "
            f"{abs(summary['total_loss']):,.0f} ₽ "
            f"on unprofitable products"
        )

    else:
        st.success("✅ No critical losses detected")

    # =========================
    # INSIGHTS
    # =========================

    col1, col2 = st.columns(2)

    with col1:

        st.subheader("🔥 Best Products")

        best_df = pd.DataFrame(
            insights["best_skus"]
        )

        st.dataframe(best_df)

    with col2:

        st.subheader("⚠ Worst Products")

        worst_df = pd.DataFrame(
            insights["worst_skus"]
        )

        st.dataframe(worst_df)

    st.divider()

    # =========================
    # ACTIONS
    # =========================

    st.subheader("🧠 Recommended Actions")

    for action in actions:
        st.warning(action)

    st.divider()

    # =========================
    # PRODUCT TABLE
    # =========================

    st.subheader("📦 Product Analytics")

    def color_status(val):

        if val == "CRITICAL":
            return "background-color: #ff0000"

        elif val == "LOSS":
            return "background-color: #ff4b4b"

        elif val == "WARNING":
            return "background-color: #ffa500"

        elif val == "TOP":
            return "background-color: #00cc66"

        return ""

    styled_df = df.style.map(
        color_status,
        subset=["status"]
    )

    st.dataframe(
        styled_df,
        use_container_width=True
    )

    st.divider()

    # =========================
    # CHARTS
    # =========================

    st.subheader("📈 Profit by SKU")

    fig = px.bar(
        df,
        x="sku",
        y="profit",
        color="status",
        text="profit"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.subheader("📊 Revenue vs Profit")

    fig2 = px.scatter(
        df,
        x="revenue",
        y="profit",
        color="status",
        size="revenue",
        hover_data=["sku"]
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )
