def calculate_metrics(df):
    """
    Ожидаемые колонки:
    sku, quantity, sale_price, cost_price, commission, logistics, ads
    """

    df["revenue"] = df["quantity"] * df["sale_price"]

    df["total_cost"] = (
        df["cost_price"] +
        df["commission"] +
        df["logistics"] +
        df["ads"]
    )

    df["profit"] = df["revenue"] - df["total_cost"]

    df["margin"] = df["profit"] / df["revenue"] * 100

    grouped = df.groupby("sku").agg({
        "revenue": "sum",
        "profit": "sum",
        "margin": "mean"
    }).reset_index()

    # статус товара
    def status(profit):
        if profit < 0:
            return "LOSS"
        elif profit < 1000:
            return "WARNING"
        return "PROFIT"

    grouped["status"] = grouped["profit"].apply(status)

    # общий инсайт
    total_loss = grouped[grouped["profit"] < 0]["profit"].sum()

    return {
        "summary": {
            "total_loss": float(total_loss)
        },
        "products": grouped.to_dict(orient="records")
    }
