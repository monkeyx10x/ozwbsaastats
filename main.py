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

    grouped = df.groupby("sku").agg({
        "revenue": "sum",
        "profit": "sum"
    }).reset_index()

    return {
        "summary": {
            "total_profit": float(grouped["profit"].sum())
        },
        "products": grouped.to_dict(orient="records")
    }
