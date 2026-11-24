"""
Checks that the waste figures calculated in Python (app/analysis.py)
match the same figures calculated in SQL (the v_daily_waste view).
Read-only: uses the generated data and changes nothing.
"""

from app import analysis
from app.db import fetch_all


def test_python_waste_matches_sql_view():
    rows = analysis.load_days(30)
    sql = {(r["Food_ID"], r["Demand_Date"]): r for r in fetch_all(
        "SELECT * FROM v_daily_waste WHERE Demand_Date >= CURDATE() - INTERVAL 30 DAY")}
    assert rows and len(rows) == len(sql)
    for row in rows:
        python = analysis.day_figures(row)
        view = sql[(row["Food_ID"], row["Demand_Date"])]
        assert python["unsold"] == view["Unsold"]
        assert python["wasted"] == view["Wasted"]
        if view["Waste_Pct"] is None:
            assert python["waste_pct"] is None
        else:   # SQL rounds to 2 decimals, so allow a difference below 0.01
            assert abs(python["waste_pct"] - float(view["Waste_Pct"])) < 0.01
        assert python["loss"] == view["Loss"]


def test_item_totals_match_sql():
    summary = {item["name"]: item for item in analysis.item_summary(analysis.load_days(30))}
    for row in fetch_all("SELECT Food_Name, SUM(Wasted) AS wasted, SUM(Loss) AS loss FROM v_daily_waste "
                         "WHERE Demand_Date >= CURDATE() - INTERVAL 30 DAY GROUP BY Food_Name"):
        assert summary[row["Food_Name"]]["wasted"] == row["wasted"]
        assert summary[row["Food_Name"]]["loss"] == row["loss"]


def test_demand_matrix_shape():
    rows = analysis.load_days(7)
    names, dates, matrix = analysis.demand_matrix(rows)
    assert len(matrix) == len(names) and all(len(line) == len(dates) for line in matrix)
    assert sum(sum(line) for line in matrix) == sum(r["Quantity_Sold"] for r in rows)
