from fastapi import FastAPI, UploadFile, File
import pandas as pd
from io import StringIO

app = FastAPI()


@app.get("/")
def home():
    return {"status": "ok"}


@app.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    content = await file.read()

    df = pd.read_csv(StringIO(content.decode("utf-8")))

    # =========================
    # BUSINESS CALCULATIONS
    # =========================

    df["revenue"] = df["quantity"] * df["sale_price"]

    df["cost"] = (
        df["cost_price"] +
        df["commission"] +
        df["logistics"] +
        df["storage"] +
        df["return_cost"] +
        df["ads_spend"]
    )

    df["profit"] = df["revenue"] - df["cost"]

    df["margin"] = (
        df["profit"] / df["revenue"] * 100
    ).round(2)

    # =========================
    # GROUP BY SKU
    # =========================

    grouped = df.groupby("sku").agg({
        "revenue": "sum",
        "profit": "sum",
        "margin": "mean",
        "ads_spend": "sum"
    }).reset_index()

    # =========================
    # STATUS ENGINE
    # =========================

    def get_status(profit, margin):
        if profit < 0:
            return "LOSS"
        elif margin < 15:
            return "WARNING"
        return "PROFIT"

    grouped["status"] = grouped.apply(
        lambda row: get_status(row["profit"], row["margin"]),
        axis=1
    )

    # =========================
    # SUMMARY
    # =========================

    total_revenue = round(grouped["revenue"].sum(), 2)
    total_profit = round(grouped["profit"].sum(), 2)

    avg_margin = round(
        grouped["margin"].mean(), 2
    )

    total_loss = round(
        grouped[grouped["profit"] < 0]["profit"].sum(), 2
    )

    # =========================
    # INSIGHTS ENGINE
    # =========================

    worst_products = grouped.sort_values(
        by="profit"
    ).head(3)

    best_products = grouped.sort_values(
        by="profit",
        ascending=False
    ).head(3)

    # =========================
    # ACTION ENGINE
    # =========================

    actions = []

    for _, row in grouped.iterrows():

        if row["profit"] < 0:
            actions.append(
                f"Reduce ads or increase price for SKU {row['sku']}"
            )

        elif row["margin"] < 15:
            actions.append(
                f"Optimize logistics or commission for SKU {row['sku']}"
            )

    # =========================
    # RESPONSE
    # =========================

    return {

        "summary": {
            "total_revenue": total_revenue,
            "total_profit": total_profit,
            "avg_margin": avg_margin,
            "total_loss": total_loss
        },

        "insights": {

            "worst_skus": worst_products[
                ["sku", "profit"]
            ].to_dict(orient="records"),

            "best_skus": best_products[
                ["sku", "profit"]
            ].to_dict(orient="records")
        },

        "actions": actions,

        "products": grouped.to_dict(
            orient="records"
        )
    }
