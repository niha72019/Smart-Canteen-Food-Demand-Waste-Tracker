"""The 4 charts (2 on the Dashboard, 2 on the Reports tab), drawn with matplotlib and seaborn."""

from datetime import date

import matplotlib
import pandas as pd
import seaborn as sns
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from app import analysis, db
from app.algorithms import merge_sort

BLUE = "#2a78d6"
GREY_BLUE = "#9fb3c8"
ALERT = "#e0582b"            # orange-red, used only for waste alerts
RED = "#c62828"
TEXT = "#444444"
LIGHT = "#d0d0d0"
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# One style for every chart: same font, small text, no bold titles.
matplotlib.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 9,
                            "text.color": TEXT, "axes.labelcolor": TEXT,
                            "xtick.color": TEXT, "ytick.color": TEXT})


def new_chart(title, grid_axis="y"):
    """A blank chart: title, light gridlines, only a light bottom axis."""
    fig = Figure(figsize=(6, 3.7), dpi=100, layout="constrained")
    ax = fig.add_subplot()
    ax.set_title(title, loc="left", fontsize=11, pad=12)
    sns.despine(ax=ax, left=True)                      # remove the box, keep the bottom axis
    ax.spines["bottom"].set_color(LIGHT)
    ax.tick_params(length=0, pad=6)
    ax.grid(axis=grid_axis, color="#ececec")
    ax.set_axisbelow(True)
    return fig, ax


def prepared_vs_sold(rows):
    """Line chart: total cooked food prepared vs sold per day."""
    fig, ax = new_chart("Prepared vs sold (last 14 days)")
    days = {}                                         # date -> [prepared, sold]
    for row in rows:
        if row["Is_Perishable"]:
            totals = days.setdefault(row["Demand_Date"], [0, 0])
            totals[0] += row["Quantity_Prepared"]
            totals[1] += row["Quantity_Sold"]
    dates = merge_sort(list(days))
    x = range(len(dates))
    ax.plot(x, [days[d][0] for d in dates], color=GREY_BLUE, linewidth=2, label="Prepared")
    ax.plot(x, [days[d][1] for d in dates], color=BLUE, linewidth=2, label="Sold")
    ax.set_xticks(x[::3], [f"{d.day} {d:%b}" for d in dates[::3]])     # about 5 labels, e.g. "25 Oct"
    ax.set_ylim(0, max(days[d][0] for d in dates) * 1.25)              # room above the lines for the legend
    ax.legend(frameon=False, loc="upper left", ncols=2)
    ax.set_ylabel("Units")
    return fig


def waste_by_item(summary):
    """Bar chart: waste % per cooked item; items over the alert level in orange-red."""
    fig, ax = new_chart("Waste % by item (last 30 days)", grid_axis="x")
    items = merge_sort([i for i in summary if i["perishable"]], key=lambda i: i["waste_pct"])
    limit = analysis.WASTE_ALERT_PCT
    colours = [ALERT if i["waste_pct"] > limit else GREY_BLUE for i in items]
    ax.barh([i["name"] for i in items], [i["waste_pct"] for i in items], color=colours, height=0.6)
    for y, item in enumerate(items):
        ax.text(item["waste_pct"] + 0.6, y, f"{item['waste_pct']:.0f}%", va="center",
                bbox={"facecolor": "white", "edgecolor": "none", "pad": 1})   # white box so the line does not cross it
    ax.axvline(limit, color=RED, linestyle="--", linewidth=1)
    ax.text(limit + 0.6, len(items) - 0.35, f"{limit}% alert", color=RED)   # in the empty row above the bars
    ax.set_ylim(-0.6, len(items) + 0.2)
    ax.set_xlim(0, max(max(i["waste_pct"] for i in items), limit) * 1.2)    # room for the % labels
    ax.xaxis.set_major_formatter("{x:.0f}%")
    return fig


def weekday_sales(rows):
    """Bar chart: average cooked units sold on each day of the week."""
    fig, ax = new_chart("Average cooked food sold by weekday")
    df = pd.DataFrame(rows)
    df = df[df["Is_Perishable"] == 1]
    per_day = df.groupby("Demand_Date")["Quantity_Sold"].sum().reset_index()       # total sold each day
    per_day["Weekday"] = pd.to_datetime(per_day["Demand_Date"]).dt.day_of_week
    averages = per_day.groupby("Weekday")["Quantity_Sold"].mean()
    ax.bar([WEEKDAYS[d] for d in averages.index], averages.values, color=BLUE, width=0.6)
    ax.set_ylabel("Units")
    return fig


def monthly_loss_chart(rows, first_day):
    """Bar chart: money lost to waste in each complete month."""
    fig, ax = new_chart("Money lost to waste per month")
    start = f"{first_day:%Y-%m}"                # complete only if the data starts on the 1st
    this_month = f"{date.today():%Y-%m}"        # still running, so not complete
    rows = [r for r in rows if this_month > r["Month"] > start or (r["Month"] == start and first_day.day == 1)]
    labels = [pd.Timestamp(r["Month"] + "-01").strftime("%b %Y") for r in rows]
    losses = [float(r["Loss"]) for r in rows]
    ax.bar(labels, losses, color=BLUE, width=0.5)
    for x, loss in enumerate(losses):
        ax.text(x, loss, f"Rs {loss:,.0f}", ha="center", va="bottom")
    ax.set_ylim(0, max(losses, default=1) * 1.2)       # room above the bars for the numbers
    ax.yaxis.set_major_formatter("{x:,.0f}")
    ax.set_ylabel("Rs")
    return fig


def dashboard_charts():
    """The 2 Dashboard charts as {name: Figure}."""
    return {"prepared_vs_sold": prepared_vs_sold(analysis.load_days(14)),
            "waste_by_item": waste_by_item(analysis.item_summary(analysis.load_days(30)))}


def report_charts():
    """The 2 Reports-tab charts as {name: Figure}."""
    return {"weekday_sales": weekday_sales(analysis.load_days(90)),
            "monthly_loss": monthly_loss_chart(db.monthly_loss(), db.first_closed_day())}


def show(figures, frame):
    """Draw the figures side by side inside a Tkinter frame."""
    for widget in frame.winfo_children():
        widget.destroy()
    for column, fig in enumerate(figures.values()):
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=column, padx=10, pady=10, sticky="nsew")
        frame.columnconfigure(column, weight=1)
