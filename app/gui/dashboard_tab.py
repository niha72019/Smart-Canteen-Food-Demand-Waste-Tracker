"""Dashboard tab: 4 KPI cards and 2 charts."""

from datetime import date

import ttkbootstrap as ttk

from app import analysis, charts, db


class DashboardTab(ttk.Frame):
    """Overview of today and the last 30 days."""

    def __init__(self, parent):
        super().__init__(parent, padding=20)
        self.cards = ttk.Frame(self)
        self.cards.pack(fill="x", pady=(0, 20))
        self.chart_area = ttk.Frame(self)
        self.chart_area.pack(fill="both", expand=True)
        self.refresh()

    def card(self, column, title, value):
        """One KPI card: a small title and a big number."""
        box = ttk.Frame(self.cards, bootstyle="light", padding=(18, 12))
        box.grid(row=0, column=column, padx=(0 if column == 0 else 16, 0), sticky="ew")
        self.cards.columnconfigure(column, weight=1)
        ttk.Label(box, text=title, bootstyle="inverse-light", foreground="#666666",
                  font=("Segoe UI", 10)).pack(anchor="w")
        ttk.Label(box, text=value, bootstyle="inverse-light", foreground="#222222",
                  font=("Segoe UI", 20)).pack(anchor="w")

    def refresh(self):
        """Reload all numbers and redraw the charts."""
        for widget in self.cards.winfo_children():
            widget.destroy()

        today = db.sales_on(date.today())
        summary = analysis.item_summary(analysis.load_days(30))
        cooked = [item for item in summary if item["perishable"]]
        prepared = sum(item["prepared"] for item in cooked)
        waste_pct = sum(item["wasted"] for item in cooked) * 100 / prepared if prepared else 0

        self.card(0, "Bills today", today["bills"])
        self.card(1, "Revenue today", f"Rs {today['revenue']:,.0f}")
        self.card(2, "Waste % (last 30 days)", f"{waste_pct:.1f}%")
        self.card(3, "Loss (last 30 days)", f"Rs {analysis.total_loss(summary):,.0f}")
        charts.show(charts.dashboard_charts(), self.chart_area)
