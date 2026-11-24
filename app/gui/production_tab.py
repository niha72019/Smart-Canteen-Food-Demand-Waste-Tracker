"""Production tab: enter how much of each cooked item was prepared today."""

from datetime import date

import ttkbootstrap as ttk

from app import db, validation


class ProductionTab(ttk.Frame):
    """One row per cooked item, pre-filled with today's recommendation."""

    def __init__(self, parent):
        super().__init__(parent, padding=10)
        self.title = ttk.Label(self, font=("Segoe UI", 12, "bold"))
        self.title.pack(anchor="w")
        ttk.Label(self, text="Quantities are pre-filled from today's recommendations. "
                             "Saving again changes the quantity (stock is adjusted).").pack(anchor="w", pady=(0, 10))
        self.grid_area = ttk.Frame(self)
        self.grid_area.pack(anchor="w")
        ttk.Button(self, text="Save production", bootstyle="success", command=self.save).pack(anchor="w", pady=12)
        self.entries = {}                       # Food_ID -> (name, StringVar)
        self.refresh()

    def refresh(self):
        """Rebuild the list of cooked items for today."""
        for widget in self.grid_area.winfo_children():
            widget.destroy()
        today = date.today()
        closed = db.day_is_closed(today)
        self.title.configure(text=f"Today's production - {today:%A %d %B %Y}" + ("  (day closed)" if closed else ""))
        for column, heading in enumerate(["Item", "Recommended", "Prepared"]):
            ttk.Label(self.grid_area, text=heading, font=("Segoe UI", 9, "bold")).grid(row=0, column=column, sticky="w", padx=8)
        self.entries = {}
        for row_no, row in enumerate(db.production_sheet(today), start=1):
            value = row["Quantity_Prepared"] if row["Quantity_Prepared"] is not None else row["Recommended_Quantity"]
            var = ttk.StringVar(value="" if value is None else value)
            ttk.Label(self.grid_area, text=row["Food_Name"]).grid(row=row_no, column=0, sticky="w", padx=8, pady=2)
            ttk.Label(self.grid_area, text=row["Recommended_Quantity"] or "-").grid(row=row_no, column=1, padx=8)
            ttk.Entry(self.grid_area, textvariable=var, width=10).grid(row=row_no, column=2, padx=8, pady=2)
            self.entries[row["Food_ID"]] = (row["Food_Name"], var)

    def save(self):
        """Validate and save the quantities prepared."""
        try:
            quantities = {food_id: validation.check_quantity(var.get(), name)
                          for food_id, (name, var) in self.entries.items() if var.get().strip()}
            db.save_production(date.today(), quantities)
        except (ValueError, db.DatabaseError) as err:
            ttk.Messagebox.show_error(str(err), "Cannot save")
            return
        ttk.Messagebox.show_info(f"Saved production for {len(quantities)} items.", "Production")
        self.refresh()
