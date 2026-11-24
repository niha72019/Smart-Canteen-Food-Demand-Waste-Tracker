"""Stock & Purchases tab: stock levels, suppliers and new purchases."""

from datetime import date

import ttkbootstrap as ttk

from app import db, validation
from app.gui.table import DataTable


class StockTab(ttk.Frame):
    """Stock and supplier tables with a purchase form."""

    def __init__(self, parent):
        super().__init__(parent, padding=10)
        left = ttk.Frame(self)
        left.pack(side="left", fill="both", expand=True)
        self.low = ttk.Label(left)
        self.low.pack(anchor="w", pady=(0, 6))
        self.stock = DataTable(left, [("Food_Name", "Item", 180), ("Type", "Type", 90),
                                      ("Quantity_Available", "In stock", 80)], search_key="Food_Name", height=15)
        self.stock.pack(fill="both", expand=True)
        ttk.Label(left, text="Suppliers", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10, 4))
        self.suppliers = DataTable(left, [("Supplier_Name", "Supplier", 200), ("Purchases", "Orders", 80),
                                          ("Total_Spent", "Spent (Rs)", 120), ("Last_Purchase", "Last order", 120)],
                                   height=4)
        self.suppliers.pack(fill="x")

        right = ttk.Frame(self)
        right.pack(side="right", fill="both", padx=(10, 0))
        form = ttk.Labelframe(right, text="New purchase (packaged items)", padding=12)
        form.pack(fill="x")
        self.supplier, self.item = ttk.StringVar(), ttk.StringVar()
        self.quantity, self.price = ttk.StringVar(), ttk.StringVar()
        self.supplier_box = ttk.Combobox(form, textvariable=self.supplier, state="readonly")
        self.item_box = ttk.Combobox(form, textvariable=self.item, state="readonly")
        for label, widget in [("Supplier", self.supplier_box), ("Item", self.item_box),
                              ("Quantity", ttk.Entry(form, textvariable=self.quantity)),
                              ("Unit price (Rs)", ttk.Entry(form, textvariable=self.price))]:
            ttk.Label(form, text=label).pack(anchor="w")
            widget.pack(fill="x", pady=(0, 8))
        ttk.Button(form, text="Save purchase", bootstyle="success", command=self.save).pack(fill="x")
        self.refresh()

    def refresh(self):
        """Reload stock, low-stock items, suppliers and the drop-downs."""
        items = db.list_items()
        for row in items:
            row["Type"] = "Cooked" if row["Is_Perishable"] else "Packaged"
        self.stock.set_rows(items)
        low = db.low_stock()
        self.low.configure(text="Low stock: " + ", ".join(r["Food_Name"] for r in low) if low
                           else "No packaged item is running low.", foreground="#b3261e" if low else "")
        suppliers = db.list_suppliers()
        self.suppliers.set_rows(suppliers)
        self.supplier_ids = {s["Supplier_Name"]: s["Supplier_ID"] for s in suppliers}
        self.item_ids = {r["Food_Name"]: r["Food_ID"] for r in items if not r["Is_Perishable"]}
        self.supplier_box.configure(values=list(self.supplier_ids))
        self.item_box.configure(values=list(self.item_ids))

    def save(self):
        """Validate and save the purchase."""
        try:
            if self.supplier.get() not in self.supplier_ids or self.item.get() not in self.item_ids:
                raise ValueError("Choose a supplier and an item.")
            quantity = validation.check_quantity(self.quantity.get(), "Quantity")
            if quantity == 0:
                raise ValueError("Quantity must be at least 1.")
            db.save_purchase(self.supplier_ids[self.supplier.get()], date.today(),
                             self.item_ids[self.item.get()], quantity,
                             validation.check_price(self.price.get(), "Unit price"))
        except (ValueError, db.DatabaseError) as err:
            ttk.Messagebox.show_error(str(err), "Cannot save")
            return
        ttk.Messagebox.show_info("Purchase saved and stock updated.", "Purchase")
        self.quantity.set("")
        self.price.set("")
        self.refresh()
