from fastapi import FastAPI, UploadFile, File
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
                    f"Reduce ads or increase price for SKU {row['sku']}"
                )

            elif row["margin"] < 15:
                actions.append(
                    f"Optimize logistics or commission for SKU {row['sku']}"
                )

            elif row["margin"] > 40:
                actions.append(
                    f"Scale SKU {row['sku']} with more ads"
                )

        # =========================
        # RESPONSE
        # =========================

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
