"""menu_tab.py - add, update and delete food items."""

import ttkbootstrap as ttk

from app import db, validation
from app.gui.table import DataTable


class MenuTab(ttk.Frame):
    """The menu table on the left, the item form on the right."""

    def __init__(self, parent):
        super().__init__(parent, padding=10)
        self.table = DataTable(self, [("Food_Name", "Item", 160), ("Category_Name", "Category", 110),
                                      ("Selling_Price", "Price", 70), ("Preparation_Cost", "Cost", 70),
                                      ("Type", "Type", 80), ("Quantity_Available", "Stock", 60)],
                               search_key="Food_Name", height=25)
        self.table.pack(side="left", fill="both", expand=True)
        self.table.tree.bind("<<TreeviewSelect>>", lambda event: self.fill_form())

        form = ttk.Labelframe(self, text="Food item", padding=12)
        form.pack(side="right", fill="y", padx=(10, 0))
        self.name, self.category = ttk.StringVar(), ttk.StringVar()
        self.price, self.cost = ttk.StringVar(), ttk.StringVar()
        self.perishable = ttk.BooleanVar(value=True)
        for label, widget in [("Name", ttk.Entry(form, textvariable=self.name)),
                              ("Category", ttk.Combobox(form, textvariable=self.category)),
                              ("Selling price (Rs)", ttk.Entry(form, textvariable=self.price)),
                              ("Preparation cost (Rs)", ttk.Entry(form, textvariable=self.cost))]:
            ttk.Label(form, text=label).pack(anchor="w")
            widget.pack(fill="x", pady=(0, 8))
            if label == "Category":
                self.category_box = widget
        ttk.Checkbutton(form, text="Cooked daily (perishable)", variable=self.perishable).pack(anchor="w", pady=8)
        ttk.Button(form, text="Add new item", bootstyle="success", command=lambda: self.save(None)).pack(fill="x", pady=2)
        ttk.Button(form, text="Update selected", command=self.update_selected).pack(fill="x", pady=2)
        ttk.Button(form, text="Delete selected", bootstyle="danger", command=self.delete).pack(fill="x", pady=2)
        ttk.Button(form, text="Clear form", bootstyle="secondary", command=self.clear).pack(fill="x", pady=2)
        self.refresh()

    def refresh(self):
        """Reload the menu and the category list."""
        rows = db.list_items()
        for row in rows:
            row["Type"] = "Cooked" if row["Is_Perishable"] else "Packaged"
        self.table.set_rows(rows)
        self.category_box.configure(values=db.list_categories())

    def fill_form(self):
        """Copy the selected row into the form."""
        row = self.table.selected()
        if row:
            self.name.set(row["Food_Name"])
            self.category.set(row["Category_Name"])
            self.price.set(row["Selling_Price"])
            self.cost.set(row["Preparation_Cost"])
            self.perishable.set(bool(row["Is_Perishable"]))

    def save(self, food_id):
        """Validate the form, then add (food_id None) or update the item."""
        try:
            db.save_item(food_id, validation.check_text(self.name.get(), "Name"),
                         validation.check_text(self.category.get(), "Category", 50),
                         validation.check_price(self.price.get(), "Selling price"),
                         validation.check_price(self.cost.get(), "Preparation cost"), self.perishable.get())
        except (ValueError, db.DatabaseError) as err:
            ttk.Messagebox.show_error(str(err), "Cannot save")
            return
        self.refresh()
        self.clear()

    def update_selected(self):
        """Update the selected item with the values in the form."""
        row = self.table.selected()
        if row is None:
            ttk.Messagebox.show_warning("Select an item in the table first.", "Update")
        else:
            self.save(row["Food_ID"])

    def delete(self):
        """Delete the selected item after asking."""
        row = self.table.selected()
        if row and ttk.Messagebox.yesno(f"Delete {row['Food_Name']}?", "Delete") == "Yes":
            try:
                db.delete_item(row["Food_ID"])
                self.refresh()
            except db.DatabaseError as err:
                ttk.Messagebox.show_error(str(err), "Cannot delete")

    def clear(self):
        """Empty the form."""
        for var in (self.name, self.category, self.price, self.cost):
            var.set("")
        self.perishable.set(True)
