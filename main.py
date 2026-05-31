from fastapi import FastAPI, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from io import StringIO
import os
import uuid
from datetime import datetime, timedelta
from yookassa import Configuration, Payment
from supabase import create_client

app = FastAPI(title="Marketplace SaaS", version="1.0.0")

Configuration.account_id = os.getenv("YOOKASSA_SHOP_ID")
Configuration.secret_key = os.getenv("YOOKASSA_SECRET_KEY")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# HOME
# =========================
@app.get("/")
def home():
    return {"status": "ok", "service": "Marketplace SaaS"}


# =========================
# UPLOAD CSV
# =========================
@app.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...), user_id: str = None):

    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    )

    profile = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
    data = profile.data

    # PRO CHECK
    is_pro = (
        data.get("plan") == "pro"
        and data.get("pro_until")
        and datetime.fromisoformat(data["pro_until"]) > datetime.utcnow()
    )

    # LIMIT CHECK
    if not is_pro and data.get("uploads_used", 0) >= 5:
        return {"error": "Free limit reached"}

    # READ CSV
    content = await file.read()
    df = pd.read_csv(StringIO(content.decode("utf-8")))

    required_columns = [
        "quantity", "sale_price", "cost_price", "commission",
        "logistics", "storage", "return_cost", "ads_spend", "sku"
    ]

    missing = [c for c in required_columns if c not in df.columns]
    if missing:
        return {"error": f"Missing columns: {missing}"}

    # CALC
    df["revenue"] = df["quantity"] * df["sale_price"]
    df["cost"] = (
        df["cost_price"] + df["commission"] +
        df["logistics"] + df["storage"] +
        df["return_cost"] + df["ads_spend"]
    )
    df["profit"] = df["revenue"] - df["cost"]
    df["margin"] = ((df["profit"] / df["revenue"]) * 100).fillna(0).round(2)
    df["roi"] = ((df["profit"] / df["cost"]) * 100).fillna(0).round(2)

    grouped = df.groupby("sku").agg({
        "revenue": "sum",
        "profit": "sum",
        "margin": "mean",
        "roi": "mean",
        "ads_spend": "sum"
    }).reset_index()

    grouped = grouped.astype(object)

    # INSIGHTS
    best = grouped.sort_values(by="profit", ascending=False).head(3)
    worst = grouped.sort_values(by="profit").head(3)

    def status(p, m):
        if p < -500:
            return "CRITICAL"
        if p < 0:
            return "LOSS"
        if m < 15:
            return "WARNING"
        if m > 40:
            return "TOP"
        return "GOOD"

    grouped["status"] = grouped.apply(
        lambda r: status(r["profit"], r["margin"]),
        axis=1
    )

    # ACTIONS
    actions = []
    for _, row in grouped.iterrows():
        if row["profit"] < 0:
            actions.append(f"SKU {row['sku']} is losing money")
        elif row["margin"] < 15:
            actions.append(f"SKU {row['sku']} low margin")
        elif row["profit"] > 3000:
            actions.append(f"SKU {row['sku']} scaling opportunity")

    total_revenue = float(grouped["revenue"].sum())
    total_profit = float(grouped["profit"].sum())
    avg_margin = float(grouped["margin"].mean())
    avg_roi = float(grouped["roi"].mean())
    total_loss = float(grouped[grouped["profit"] < 0]["profit"].sum())

    # SAVE REPORT
    supabase.table("reports").insert({
        "user_id": user_id,
        "summary": {
            "total_revenue": total_revenue,
            "total_profit": total_profit,
            "avg_margin": avg_margin,
            "avg_roi": avg_roi,
            "total_loss": total_loss
        },
        "report_json": {
            "best": best.to_dict(orient="records"),
            "worst": worst.to_dict(orient="records"),
            "products": grouped.to_dict(orient="records"),
            "actions": actions
        }
    }).execute()

    # UPDATE USAGE
    if user_id:
        supabase.table("profiles").update({
            "uploads_used": data.get("uploads_used", 0) + 1
        }).eq("id", user_id).execute()

    return {
        "summary": {
            "total_revenue": total_revenue,
            "total_profit": total_profit,
            "avg_margin": avg_margin,
            "avg_roi": avg_roi,
            "total_loss": total_loss
        },
        "insights": {
            "best_skus": best.to_dict(orient="records"),
            "worst_skus": worst.to_dict(orient="records")
        },
        "actions": actions,
        "products": grouped.to_dict(orient="records")
    }


# =========================
# PAYMENT
# =========================
@app.post("/create-payment")
async def create_payment(payload: dict):

    payment = Payment.create({
        "amount": {"value": "990.00", "currency": "RUB"},
        "capture": True,
        "confirmation": {
            "type": "redirect",
            "return_url": "http://localhost:3000/success"
        },
        "description": "Seller Pulse PRO",
        "metadata": {"user_id": payload.get("user_id")}
    }, uuid.uuid4())

    return {"payment_url": payment.confirmation.confirmation_url}


# =========================
# WEBHOOK
# =========================
@app.post("/yookassa-webhook")
async def webhook(request: Request):

    event = await request.json()

    if event.get("event") != "payment.succeeded":
        return {"ok": True}

    payment = event["object"]
    user_id = payment.get("metadata", {}).get("user_id")

    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    )

    supabase.table("profiles").update({
        "plan": "pro",
        "pro_until": (datetime.utcnow() + timedelta(days=30)).isoformat()
    }).eq("id", user_id).execute()

    return {"status": "ok"}


# =========================
# PROFILE
# =========================
@app.get("/profile/{user_id}")
async def profile(user_id: str):

    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    )

    profile = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
    payments = supabase.table("payments").select("*").eq("user_id", user_id).order("created_at").execute()
    reports = supabase.table("reports").select("*").eq("user_id", user_id).order("created_at").execute()

    return {
        "profile": profile.data,
        "payments": payments.data,
        "reports": reports.data
    }
