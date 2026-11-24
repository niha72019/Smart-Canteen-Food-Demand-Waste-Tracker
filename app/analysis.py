"""
analysis.py - waste, loss and demand analysis done in Python
(lists, dicts and a 2D list) from rows fetched from the database.
The same waste numbers are calculated in SQL by v_daily_waste;
tests/test_analysis.py checks that both agree.
"""

from app.algorithms import merge_sort
from app.db import run_query

WASTE_ALERT_PCT = 20       # items wasting more than this % are flagged


def load_days(days=30):
    """Fetch every closed item-day of the last `days` days, oldest first."""
    return run_query(
        "SELECT d.Demand_Date, d.Food_ID, f.Food_Name, f.Is_Perishable, f.Preparation_Cost, "
        "       d.Quantity_Prepared, d.Quantity_Sold "
        "FROM daily_demand d JOIN food_item f ON f.Food_ID = d.Food_ID "
        "WHERE d.Is_Closed = TRUE AND d.Demand_Date >= CURDATE() - INTERVAL %s DAY "
        "ORDER BY d.Demand_Date, f.Food_Name", (days,))


def day_figures(row):
    """
    Unsold, wasted, waste % and loss for one item on one day.
    Unsold cooked food is waste; unsold packaged food is kept, so not waste.
    """
    unsold = row["Quantity_Prepared"] - row["Quantity_Sold"]
    wasted = unsold if row["Is_Perishable"] else 0
    prepared = row["Quantity_Prepared"]
    waste_pct = wasted * 100 / prepared if prepared > 0 else None    # rounded only when shown
    return {"unsold": unsold, "wasted": wasted, "waste_pct": waste_pct,
            "loss": wasted * row["Preparation_Cost"]}


def item_summary(rows):
    """Add up the rows per item. Returns a list of dicts, one per item."""
    items = {}                                    # Food_Name -> running totals
    for row in rows:
        name = row["Food_Name"]
        if name not in items:
            items[name] = {"name": name, "perishable": bool(row["Is_Perishable"]), "days": 0,
                           "prepared": 0, "sold": 0, "wasted": 0, "loss": 0, "sold_out_days": 0}
        totals = items[name]
        figures = day_figures(row)
        totals["days"] += 1
        totals["prepared"] += row["Quantity_Prepared"]
        totals["sold"] += row["Quantity_Sold"]
        totals["wasted"] += figures["wasted"]
        totals["loss"] += figures["loss"]
        if row["Quantity_Sold"] == row["Quantity_Prepared"]:
            totals["sold_out_days"] += 1

    for totals in items.values():
        totals["waste_pct"] = round(totals["wasted"] * 100 / totals["prepared"], 2) if totals["prepared"] else 0
        totals["avg_sold"] = round(totals["sold"] / totals["days"], 1)
    return list(items.values())


def popular_and_low_demand(summary, count=3):
    """Return (the `count` best-selling items, the `count` worst-selling items)."""
    ranked = merge_sort(summary, key=lambda item: item["avg_sold"], reverse=True)
    return ranked[:count], ranked[-count:]


def waste_alerts(summary):
    """Cooked items whose waste % is above WASTE_ALERT_PCT, worst first."""
    flagged = [item for item in summary if item["perishable"] and item["waste_pct"] > WASTE_ALERT_PCT]
    return merge_sort(flagged, key=lambda item: item["waste_pct"], reverse=True)


def total_loss(summary):
    """Total money lost to waste."""
    return sum(item["loss"] for item in summary)


def demand_matrix(rows):
    """
    Build the items x days demand matrix as a 2D list.
    matrix[i][j] = units of item i sold on day j (0 if no record).
    Returns (item names, dates, matrix).
    """
    names = merge_sort(list({row["Food_Name"] for row in rows}))
    dates = merge_sort(list({row["Demand_Date"] for row in rows}))
    matrix = [[0] * len(dates) for _ in names]    # start with all zeros
    name_index = {name: i for i, name in enumerate(names)}
    date_index = {day: j for j, day in enumerate(dates)}
    for row in rows:
        matrix[name_index[row["Food_Name"]]][date_index[row["Demand_Date"]]] = row["Quantity_Sold"]
    return names, dates, matrix
