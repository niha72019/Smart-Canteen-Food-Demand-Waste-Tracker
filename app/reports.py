"""reports.py - report tables for export and the "full report" export."""

from datetime import date
from pathlib import Path

from app import analysis, charts, csv_io, db

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"


def item_report():
    """Per-item totals for the last 30 days, rounded for reading."""
    rows = []
    for item in analysis.item_summary(analysis.load_days(30)):
        rows.append({"Item": item["name"], "Days": item["days"], "Prepared": item["prepared"],
                     "Sold": item["sold"], "Wasted": item["wasted"], "Waste %": round(item["waste_pct"], 1),
                     "Avg sold/day": item["avg_sold"], "Sold-out days": item["sold_out_days"],
                     "Loss (Rs)": item["loss"]})
    return rows


# Report name -> function that returns its rows (used by the Reports tab).
REPORTS = {
    "Item performance (30 days)": item_report,
    "Daily waste (30 days)": lambda: db.daily_waste(30),
    "Monthly loss": db.monthly_loss,
    "Latest recommendations": db.latest_recommendations,
}


def export_full_report():
    """
    Save every report as CSV and every chart as PNG into reports/
    (the folder is created only now). Returns the list of files written.
    """
    REPORTS_DIR.mkdir(exist_ok=True)
    stamp = date.today().isoformat()
    files = []
    for name, get_rows in REPORTS.items():
        rows = get_rows()
        if rows:
            path = REPORTS_DIR / f"{stamp}_{name.split(' (')[0].lower().replace(' ', '_')}.csv"
            csv_io.export_rows(rows, path)
            files.append(path)
    for name, fig in charts.all_charts().items():
        path = REPORTS_DIR / f"{stamp}_{name}.png"
        fig.savefig(path, dpi=150)
        files.append(path)
    return files
