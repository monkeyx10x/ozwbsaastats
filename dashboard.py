import streamlit as st
import requests
import pandas as pd
import plotly.express as px

API_URL = "https://YOUR-RENDER-URL.onrender.com/upload-csv"

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
    )
