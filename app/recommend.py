"""
recommend.py - rule-based preparation recommendations for cooked items.

Rule (the reason is saved in RECOMMENDATION.Basis):
  1. base   = weighted average sold over the last 7 days (recent days count more)
  2. waste  : average waste over the last 7 days > 20 %  -> 10 % less
  3. demand : sold out on 3 or more of the last 7 days   -> 10 % more
  4. weekday: x (average sold on that weekday / overall average), using pandas
  5. round up to a whole number, never below 0
"""

import math
from datetime import timedelta

import pandas as pd

from app.db import run_in_transaction, run_query


def recommend_quantity(history, target_date):
    """
    history: list of dicts {date, prepared, sold} for ONE item, oldest first.
    Returns (quantity, basis text).
    """
    if not history:
        return 0, "No sales history."
    last7 = history[-7:]

    # 1. Weighted average: oldest day weight 1, newest day weight 7.
    weights = range(1, len(last7) + 1)
    base = sum(w * day["sold"] for w, day in zip(weights, last7)) / sum(weights)
    quantity = base
    reasons = [f"7-day weighted avg {base:.1f}"]

    # 2. High waste -> reduce.
    prepared = sum(day["prepared"] for day in last7)
    waste_pct = (prepared - sum(day["sold"] for day in last7)) * 100 / prepared if prepared else 0
    if waste_pct > 20:
        quantity *= 0.9
        reasons.append(f"waste {waste_pct:.0f}% > 20% so -10%")

    # 3. Frequently sold out -> increase.
    sold_out_days = sum(1 for day in last7 if day["sold"] == day["prepared"])
    if sold_out_days >= 3:
        quantity *= 1.1
        reasons.append(f"sold out {sold_out_days}/7 days so +10%")

    # 4. Weekday adjustment from all history (pandas groups by weekday).
    df = pd.DataFrame(history)
    df["weekday"] = pd.to_datetime(df["date"]).dt.day_of_week      # 0 = Monday
    weekday_avg = df[df["weekday"] == target_date.weekday()]["sold"].mean()
    if df["sold"].mean() > 0 and not pd.isna(weekday_avg):
        factor = weekday_avg / df["sold"].mean()
        quantity *= factor
        reasons.append(f"{target_date:%A} factor {factor:.2f}")

    # 5. Round up, never negative.
    quantity = max(0, math.ceil(quantity))
    return quantity, "; ".join(reasons) + f" -> {quantity}"


def generate_recommendations():
    """
    Recommend quantities for every cooked item for the day after the last
    closed day, save them in RECOMMENDATION, and return them as a list.
    """
    rows = run_query(
        "SELECT d.Food_ID, f.Food_Name, d.Demand_Date, d.Quantity_Prepared, d.Quantity_Sold "
        "FROM daily_demand d JOIN food_item f ON f.Food_ID = d.Food_ID "
        "WHERE d.Is_Closed = TRUE AND f.Is_Perishable = TRUE ORDER BY d.Demand_Date")
    if not rows:
        return []
    target_date = rows[-1]["Demand_Date"] + timedelta(days=1)

    histories = {}                     # (Food_ID, Food_Name) -> list of days
    for row in rows:
        histories.setdefault((row["Food_ID"], row["Food_Name"]), []).append(
            {"date": row["Demand_Date"], "prepared": row["Quantity_Prepared"], "sold": row["Quantity_Sold"]})

    # Items that already have a recommendation for that day are updated, the rest inserted.
    existing = [r["Food_ID"] for r in run_query(
        "SELECT Food_ID FROM recommendation WHERE Recommendation_Date = %s", (target_date,))]
    results, statements = [], []
    for (food_id, name), history in histories.items():
        quantity, basis = recommend_quantity(history, target_date)
        if food_id in existing:
            statements.append(("UPDATE recommendation SET Recommended_Quantity = %s, Basis = %s "
                               "WHERE Food_ID = %s AND Recommendation_Date = %s",
                               (quantity, basis, food_id, target_date)))
        else:
            statements.append(("INSERT INTO recommendation (Food_ID, Recommendation_Date, "
                               "Recommended_Quantity, Basis) VALUES (%s, %s, %s, %s)",
                               (food_id, target_date, quantity, basis)))
        results.append({"date": target_date, "name": name, "quantity": quantity, "basis": basis})
    run_in_transaction(statements)
    return results
