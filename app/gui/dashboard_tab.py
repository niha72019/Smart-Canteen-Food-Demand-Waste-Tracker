"""dashboard_tab.py - KPI cards, waste alerts and the 4 charts."""

from datetime import date

import ttkbootstrap as ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from app import analysis, charts, db


class DashboardTab(ttk.Frame):
    """Overview of today and the last 30 days."""

    def __init__(self, parent):
        super().__init__(parent, padding=10)
        self.cards = ttk.Frame(self)
        self.cards.pack(fill="x")
        self.alerts = ttk.Label(self, foreground="#b3261e", font=("Segoe UI", 10, "bold"))
        self.alerts.pack(anchor="w", pady=8)
        self.chart_area = ttk.Frame(self)
        self.chart_area.pack(fill="both", expand=True)
        self.refresh()

    def card(self, column, title, value):
        """One KPI card: a framed title around a big number."""
        box = ttk.Labelframe(self.cards, text=title, padding=(12, 2))
        box.grid(row=0, column=column, padx=(0, 10), sticky="ew")
        self.cards.columnconfigure(column, weight=1)
        ttk.Label(box, text=value, font=("Segoe UI", 16, "bold")).pack(anchor="w")

    def refresh(self):
        """Reload all numbers and redraw the charts."""
        for widget in self.cards.winfo_children() + self.chart_area.winfo_children():
            widget.destroy()

        today = db.sales_on(date.today())
        summary = analysis.item_summary(analysis.load_days(30))
        cooked = [item for item in summary if item["perishable"]]
        prepared = sum(item["prepared"] for item in cooked)
        waste_pct = sum(item["wasted"] for item in cooked) * 100 / prepared if prepared else 0
        alerts = analysis.waste_alerts(summary)

        self.card(0, "Bills today", today["bills"])
        self.card(1, "Revenue today", f"Rs {today['revenue']:,.0f}")
        self.card(2, "Waste (last 30 days)", f"{waste_pct:.1f}%")
        self.card(3, "Loss (last 30 days)", f"Rs {analysis.total_loss(summary):,.0f}")
        self.card(4, "Waste alerts", len(alerts))
        names = ", ".join(f"{a['name']} ({a['waste_pct']:.0f}%)" for a in alerts)
        self.alerts.configure(text=f"Waste alert (over {analysis.WASTE_ALERT_PCT}%): {names}" if alerts
                              else "No waste alerts.")

        for i, fig in enumerate(charts.all_charts().values()):
            canvas = FigureCanvasTkAgg(fig, master=self.chart_area)
            canvas.draw()
            canvas.get_tk_widget().grid(row=i // 2, column=i % 2, padx=4, pady=4, sticky="nsew")
        self.chart_area.columnconfigure((0, 1), weight=1)
