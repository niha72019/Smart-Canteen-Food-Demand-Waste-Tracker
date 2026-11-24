"""Billing tab: build a bill line by line and save it."""

from datetime import date

import ttkbootstrap as ttk

from app import db, validation
from app.gui.table import DataTable


class BillingTab(ttk.Frame):
    """Pick an item and quantity, add it to the bill, then save the bill."""

    def __init__(self, parent):
        super().__init__(parent, padding=10)
        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Item").pack(side="left")
        self.item = ttk.StringVar()
        self.item_box = ttk.Combobox(top, textvariable=self.item, width=28, state="readonly")
        self.item_box.pack(side="left", padx=6)
        ttk.Label(top, text="Quantity").pack(side="left", padx=(12, 0))
        self.quantity = ttk.StringVar(value="1")
        ttk.Entry(top, textvariable=self.quantity, width=6).pack(side="left", padx=6)
        ttk.Button(top, text="Add to bill", command=self.add_line).pack(side="left", padx=6)

        self.table = DataTable(self, [("name", "Item", 200), ("quantity", "Qty", 60),
                                      ("price", "Price", 80), ("amount", "Amount", 90)], height=12)
        self.table.pack(fill="both", expand=True, pady=10)
        bottom = ttk.Frame(self)
        bottom.pack(fill="x")
        self.total = ttk.Label(bottom, text="Total: Rs 0", font=("Segoe UI", 14, "bold"))
        self.total.pack(side="left")
        ttk.Button(bottom, text="Save bill", bootstyle="success", command=self.save).pack(side="right")
        ttk.Button(bottom, text="Clear bill", bootstyle="secondary", command=self.clear).pack(side="right", padx=6)
        self.items, self.lines = {}, {}         # name -> item row;  Food_ID -> bill line
        self.refresh()

    def refresh(self):
        """Reload the items for the drop-down."""
        self.items = {row["Food_Name"]: row for row in db.list_items()}
        self.item_box.configure(values=[f"{name}" for name in self.items])

    def add_line(self):
        """Add the chosen item and quantity to the bill."""
        try:
            item = self.items.get(self.item.get())
            if item is None:
                raise ValueError("Choose an item.")
            quantity = validation.check_quantity(self.quantity.get(), "Quantity")
            if quantity == 0:
                raise ValueError("Quantity must be at least 1.")
        except ValueError as err:
            ttk.Messagebox.show_error(str(err), "Billing")
            return
        line = self.lines.setdefault(item["Food_ID"], {"name": item["Food_Name"], "quantity": 0,
                                                       "price": item["Selling_Price"]})
        line["quantity"] += quantity
        line["amount"] = line["quantity"] * line["price"]
        self.show()

    def show(self):
        """Redraw the bill lines and the total."""
        self.table.set_rows(self.lines.values())
        self.total.configure(text=f"Total: Rs {sum(l['amount'] for l in self.lines.values()):,.2f}")

    def save(self):
        """Save the bill."""
        if not self.lines:
            ttk.Messagebox.show_warning("The bill is empty.", "Billing")
            return
        try:
            sale_id, total = db.save_bill(date.today(), {food_id: (l["quantity"], l["price"])
                                                         for food_id, l in self.lines.items()})
        except db.DatabaseError as err:
            ttk.Messagebox.show_error(str(err), "Bill not saved")
            return
        ttk.Messagebox.show_info(f"Bill #{sale_id} saved. Total Rs {total}.", "Billing")
        self.clear()
        self.refresh()

    def clear(self):
        """Start a new empty bill."""
        self.lines = {}
        self.show()
