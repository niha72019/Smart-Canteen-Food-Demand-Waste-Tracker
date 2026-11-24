"""main_window.py - the main window: one notebook tab per screen."""

import ttkbootstrap as ttk

from app.gui.billing_tab import BillingTab
from app.gui.close_day_tab import CloseDayTab
from app.gui.dashboard_tab import DashboardTab
from app.gui.insights_tab import InsightsTab
from app.gui.menu_tab import MenuTab
from app.gui.production_tab import ProductionTab
from app.gui.recommendations_tab import RecommendationsTab
from app.gui.reports_tab import ReportsTab
from app.gui.stock_tab import StockTab

TABS = [("Dashboard", DashboardTab), ("Menu", MenuTab), ("Production", ProductionTab),
        ("Billing", BillingTab), ("Close Day", CloseDayTab), ("Stock & Purchases", StockTab),
        ("Recommendations", RecommendationsTab), ("Reports & CSV", ReportsTab),
        ("SQL Insights", InsightsTab)]


def build_window():
    """Create the window and its tabs. Returns (window, notebook, list of tabs)."""
    window = ttk.Window(title="Smart Canteen - Food Demand & Waste Tracker", themename="flatly",
                        size=(1280, 860))
    notebook = ttk.Notebook(window)
    notebook.pack(fill="both", expand=True, padx=10, pady=10)
    tabs = []
    for title, tab_class in TABS:
        tab = tab_class(notebook)
        notebook.add(tab, text=f"  {title}  ")
        tabs.append(tab)
    # Each tab reloads its data from the database when it is opened.
    notebook.bind("<<NotebookTabChanged>>", lambda event: tabs[notebook.index("current")].refresh())
    return window, notebook, tabs


def run():
    """Start the app."""
    window, _, _ = build_window()
    window.mainloop()
