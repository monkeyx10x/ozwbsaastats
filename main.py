from fastapi import FastAPI, UploadFile, File
import pandas as pd
from io import StringIO
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
from yookassa import Configuration, Payment
from supabase import create_client
from fastapi import Request
from datetime import datetime, timedelta
import json

app = FastAPI(
    title="Marketplace SaaS",
    version="1.0.0"
)

Configuration.account_id = os.getenv(
    "YOOKASSA_SHOP_ID"
)

Configuration.secret_key = os.getenv(
    "YOOKASSA_SECRET_KEY"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "status": "ok",
        "service": "Marketplace SaaS"
    }

@app.post("/upload-csv")
async def upload_csv(
    file: UploadFile = File(...),
    user_id: str = None
):

    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    )

    profile = supabase.table("profiles") \
        .select("*") \
        .eq("id", user_id) \
        .single() \
        .execute()

    data = profile.data

    # ======================
    # PRO CHECK
    # ======================

    is_pro = (
        data.get("plan") == "pro"
        and data.get("pro_until")
        and datetime.fromisoformat(data["pro_until"]) > datetime.utcnow()
    )

    # ======================
    # LIMIT CHECK
    # ======================

    if not is_pro and data.get("uploads_used", 0) >= 5:
        return {
            "error": "Free limit reached"
        }

        # =========================
        # READ CSV
        # =========================

        content = await file.read()

        df = pd.read_csv(
            StringIO(content.decode("utf-8"))
        )

        # =========================
        # VALIDATION
        # =========================

        required_columns = [
            "quantity",
            "sale_price",
            "cost_price",
            "commission",
            "logistics",
            "storage",
            "return_cost",
            "ads_spend",
            "sku"
        ]

        missing_columns = [
            col for col in required_columns
            if col not in df.columns
        ]

        if missing_columns:
            return {
                "error": f"Missing columns: {missing_columns}"
            }

        # =========================
        # BUSINESS CALCULATIONS
        # =========================

        df["revenue"] = (
            df["quantity"] * df["sale_price"]
        )

        df["cost"] = (
            df["cost_price"] +
            df["commission"] +
            df["logistics"] +
            df["storage"] +
            df["return_cost"] +
            df["ads_spend"]
        )

        df["profit"] = (
            df["revenue"] - df["cost"]
        )

        df["margin"] = (
            (df["profit"] / df["revenue"]) * 100
        ).fillna(0).round(2)

        df["roi"] = (
            (df["profit"] / df["cost"]) * 100
        ).fillna(0).round(2)

        # =========================
        # GROUPING
        # =========================

        grouped = df.groupby("sku").agg({
            "revenue": "sum",
            "profit": "sum",
            "margin": "mean",
            "roi": "mean",
            "ads_spend": "sum"
        }).reset_index()

        # =========================
        # CLEAN TYPES
        # =========================

        grouped["revenue"] = grouped["revenue"].apply(float)
        grouped["profit"] = grouped["profit"].apply(float)
        grouped["margin"] = grouped["margin"].apply(float)
        grouped["roi"] = grouped["roi"].apply(float)
        grouped["ads_spend"] = grouped["ads_spend"].apply(float)

        # =========================
        # STATUS ENGINE
        # =========================

        def get_status(profit, margin):

            if profit < -500:
                return "CRITICAL"

            elif profit < 0:
                return "LOSS"

            elif margin < 15:
                return "WARNING"

            elif margin > 40:
                return "TOP"

            return "GOOD"

        grouped["status"] = grouped.apply(
            lambda row: get_status(
                row["profit"],
                row["margin"]
            ),
            axis=1
        )

        # =========================
        # SUMMARY
        # =========================

        total_revenue = float(
            grouped["revenue"].sum()
        )

        total_profit = float(
            grouped["profit"].sum()
        )

        avg_margin = float(
            grouped["margin"].mean()
        )

        avg_roi = float(
            grouped["roi"].mean()
        )

        total_loss = float(
            grouped[grouped["profit"] < 0]["profit"].sum()
        )

        # =========================
        # INSIGHTS
        # =========================

        best = grouped.sort_values(
            by="profit",
            ascending=False
        ).head(3)

        worst = grouped.sort_values(
            by="profit"
        ).head(3)

        # =========================
        # ACTION ENGINE
        # =========================

        actions = []

        for _, row in grouped.iterrows():
        
            if row["profit"] < 0:
        
                actions.append(
                    f"SKU {row['sku']} is losing money. Consider reducing ads spend or increasing product price."
                )
        
            elif row["margin"] < 15:
        
                actions.append(
                    f"SKU {row['sku']} has weak margin ({row['margin']}%). Optimize logistics or commission."
                )
        
            elif row["profit"] > 3000:
        
                actions.append(
                    f"SKU {row['sku']} performs extremely well. Consider scaling ads budget."
                )

        # =========================
        # RESPONSE
        # =========================

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

                "best_skus": best[
                    ["sku", "profit"]
                ].astype(object).to_dict(orient="records"),

                "worst_skus": worst[
                    ["sku", "profit"]
                ].astype(object).to_dict(orient="records")
            },

            "actions": actions,

            "products": grouped.astype(object).to_dict(
                orient="records"
            )
        }

    except Exception as e:

        return {
            "error": str(e)
        }

@app.post("/create-payment")
async def create_payment(payload: dict):

    user_id = payload.get("user_id")

    payment = Payment.create({
        "amount": {
            "value": "990.00",
            "currency": "RUB"
        },

        "capture": True,

        "confirmation": {
            "type": "redirect",
            "return_url": "http://localhost:3000/success"
        },

        "description": "Seller Pulse PRO",

        "metadata": {
            "user_id": user_id
        }

    }, uuid.uuid4())

    return {
        "payment_url": payment.confirmation.confirmation_url
    }

@app.post("/yookassa-webhook")
async def yookassa_webhook(request: Request):

    event = await request.json()

    if event.get("event") != "payment.succeeded":
        return {"ok": True}

    payment = event["object"]
    user_id = payment.get("metadata", {}).get("user_id")

    if not user_id:
        return {"error": "no user_id"}

    pro_until = datetime.utcnow() + timedelta(days=30)

    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    )

    supabase.table("profiles").update({
        "plan": "pro",
        "pro_until": pro_until.isoformat()
    }).eq("id", user_id).execute()

    return {"status": "pro_activated"}
