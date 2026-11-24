"""The 4 dashboard charts, drawn with matplotlib and seaborn."""

import pandas as pd
import seaborn as sns
from matplotlib.figure import Figure

from app import analysis, db
from app.algorithms import merge_sort

BLUE = "#2a78d6"
ORANGE = "#eb6834"
GREY = "#52514e"
HEATMAP_COLOURS = ["#eef4fc", "#c4dbf5", "#8fbbec", "#4f93df", "#2a78d6", "#1d5aa6", "#0d3c73"]   # light -> dark
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def new_chart(title):
    """A blank chart with a title and a light grid."""
    fig = Figure(figsize=(5.6, 2.05), dpi=100, layout="constrained")
    ax = fig.add_subplot()
    ax.set_title(title, loc="left", fontsize=10, fontweight="bold")
    ax.tick_params(labelsize=7)
    ax.grid(axis="y", alpha=0.3)
    return fig, ax


def prepared_vs_sold(rows):
    """Line chart: total cooked food prepared vs sold per day."""
    fig, ax = new_chart("Cooked food: prepared vs sold per day")
    days = {}                                         # date -> [prepared, sold]
    for row in rows:
        if row["Is_Perishable"]:
            totals = days.setdefault(row["Demand_Date"], [0, 0])
            totals[0] += row["Quantity_Prepared"]
            totals[1] += row["Quantity_Sold"]
    dates = merge_sort(list(days))
    ax.plot(dates, [days[d][0] for d in dates], color=BLUE, linewidth=2, label="Prepared")
    ax.plot(dates, [days[d][1] for d in dates], color=ORANGE, linewidth=2, label="Sold")
    ax.set_ylim(0, max(days[d][0] for d in dates) * 1.3)     # room above the lines for the legend
    ax.legend(frameon=False, fontsize=8, loc="upper left", ncols=2)
    ax.set_ylabel("Units", fontsize=8)
    ax.tick_params(axis="x", rotation=30)              # tilted so the dates do not overlap
    return fig


def waste_by_item(summary):
    """Bar chart: waste % per cooked item, with the alert level."""
    fig, ax = new_chart("Waste % by item")
    items = merge_sort([i for i in summary if i["perishable"]], key=lambda i: i["waste_pct"])
    ax.barh([i["name"] for i in items], [i["waste_pct"] for i in items], color=BLUE, height=0.6)
    ax.axvline(analysis.WASTE_ALERT_PCT, color=GREY, linestyle="--", linewidth=1)
    ax.text(analysis.WASTE_ALERT_PCT, len(items) - 0.4, " alert level", color=GREY, fontsize=8)
    ax.set_ylim(-0.6, len(items) + 0.3)                 # room above the top bar for the label
    for y, item in enumerate(items):
        ax.text(item["waste_pct"] + 0.5, y, f"{item['waste_pct']:.0f}%", va="center", fontsize=8)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", alpha=0.3)
    return fig


def weekday_heatmap(rows):
    """Heatmap: average units sold of each item on each day of the week."""
    fig, ax = new_chart("Average sold: item x weekday")
    df = pd.DataFrame(rows)
    df["Weekday"] = pd.to_datetime(df["Demand_Date"]).dt.day_of_week
    table = df.pivot_table(index="Food_Name", columns="Weekday", values="Quantity_Sold", aggfunc="mean")
    table.columns = [WEEKDAYS[d] for d in table.columns]
    sns.heatmap(table, ax=ax, cmap=HEATMAP_COLOURS, annot=True, fmt=".0f", annot_kws={"fontsize": 7},
                linewidths=1, linecolor="white", cbar=False)
    ax.set_xlabel("")
    ax.set_ylabel("")
    return fig


def monthly_loss_chart(rows):
    """Bar chart: money lost to waste each month."""
    fig, ax = new_chart("Money lost to waste per month (Rs)")
    months = [r["Month"] for r in rows]
    losses = [float(r["Loss"]) for r in rows]
    ax.bar(months, losses, color=BLUE, width=0.55)
    ax.set_ylim(0, max(losses) * 1.2)                   # room above the bars for the numbers
    for x, loss in enumerate(losses):
        ax.text(x, loss, f"{loss:,.0f}", ha="center", va="bottom", fontsize=8)
    return fig


def all_charts():
    """All 4 charts as {name: Figure}."""
    rows_30 = analysis.load_days(30)
    return {
        "prepared_vs_sold": prepared_vs_sold(rows_30),
        "waste_by_item": waste_by_item(analysis.item_summary(rows_30)),
        "weekday_heatmap": weekday_heatmap(analysis.load_days(90)),
        "monthly_loss": monthly_loss_chart(db.monthly_loss()),
    }
