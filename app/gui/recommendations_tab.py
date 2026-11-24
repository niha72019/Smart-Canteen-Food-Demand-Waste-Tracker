"""Recommendations tab: the latest recommended quantities and their reasons."""

import ttkbootstrap as ttk

from app import db, recommend
from app.gui.table import DataTable


class RecommendationsTab(ttk.Frame):
    """Table of recommended quantities and their reasons."""

    def __init__(self, parent):
        super().__init__(parent, padding=10)
        ttk.Button(self, text="Generate recommendations now", command=self.generate).pack(anchor="w")
        self.table = DataTable(self, [("Recommendation_Date", "For date", 100), ("Food_Name", "Item", 150),
                                      ("Recommended_Quantity", "Quantity", 80), ("Basis", "Reason", 620)],
                               search_key="Food_Name", height=20)
        self.table.pack(fill="both", expand=True, pady=10)
        self.refresh()

    def refresh(self):
        """Reload the latest recommendations."""
        self.table.set_rows(db.latest_recommendations())

    def generate(self):
        """Make new recommendations and show them."""
        try:
            new = recommend.generate_recommendations()
        except db.DatabaseError as err:
            ttk.Messagebox.show_error(str(err), "Recommendations")
            return
        self.refresh()
        ttk.Messagebox.show_info(f"{len(new)} recommendations saved.", "Recommendations")
