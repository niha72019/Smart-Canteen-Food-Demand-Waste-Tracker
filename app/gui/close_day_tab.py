"""Close Day tab: close today and make tomorrow's recommendations."""

from datetime import date

import ttkbootstrap as ttk

from app import db, recommend
from app.gui.table import DataTable


class CloseDayTab(ttk.Frame):
    """Closes the day and shows its summary."""

    def __init__(self, parent):
        super().__init__(parent, padding=10)
        self.status = ttk.Label(self, font=("Segoe UI", 12, "bold"))
        self.status.pack(anchor="w")
        ttk.Label(self, text="Closing records what was sold, turns cooked leftovers into waste, "
                             "and then makes tomorrow's recommendations.").pack(anchor="w", pady=(0, 10))
        self.button = ttk.Button(self, text="Close today", bootstyle="danger", command=self.close)
        self.button.pack(anchor="w")
        self.table = DataTable(self, [("Food_Name", "Item", 180), ("Quantity_Prepared", "Prepared", 90),
                                      ("Quantity_Sold", "Sold", 80), ("Wasted", "Wasted", 80),
                                      ("Waste_Pct", "Waste %", 80), ("Loss", "Loss (Rs)", 90)], height=16)
        self.table.pack(fill="both", expand=True, pady=10)
        self.refresh()

    def refresh(self):
        """Show whether today is open or closed."""
        closed = db.day_is_closed(date.today())
        self.status.configure(text=f"{date.today():%A %d %B %Y}: " + ("closed" if closed else "open"))
        self.button.configure(state="disabled" if closed else "normal")

    def close(self):
        """Ask, then close the day and make tomorrow's recommendations."""
        if ttk.Messagebox.yesno("Close today? No more bills can be added after this.", "Close day") != "Yes":
            return
        try:
            self.table.set_rows(db.close_day(date.today()))
            new = recommend.generate_recommendations()
        except db.DatabaseError as err:
            ttk.Messagebox.show_error(str(err), "Cannot close")
            return
        target = new[0]["date"] if new else "-"
        ttk.Messagebox.show_info(f"Day closed. {len(new)} recommendations made for {target}.", "Close day")
        self.refresh()
