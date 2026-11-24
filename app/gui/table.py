"""
table.py - a table widget used by several tabs.
Click a column heading to sort it (merge sort); type a name in the search
box to jump to that row (binary search).
"""

import ttkbootstrap as ttk

from app.algorithms import binary_search, merge_sort


def sort_value(value):
    """Sort key that puts empty (None) values last and works for numbers, text and dates."""
    return (value is None, value.lower() if isinstance(value, str) else value if value is not None else 0)


class DataTable(ttk.Frame):
    """A Treeview showing a list of dicts. columns = [(key, heading, width), ...] or None (automatic)."""

    def __init__(self, parent, columns=None, search_key=None, height=12):
        super().__init__(parent)
        self.columns, self.search_key, self.rows = columns, search_key, []
        self.automatic = columns is None                 # columns come from the rows (SQL Insights)
        self.sorted_by, self.reverse = None, False

        if search_key:                                   # search box above the table
            bar = ttk.Frame(self)
            bar.pack(fill="x", pady=(0, 6))
            self.search_text = ttk.StringVar()
            entry = ttk.Entry(bar, textvariable=self.search_text, width=30)
            entry.pack(side="left")
            entry.bind("<Return>", lambda event: self.search())
            ttk.Button(bar, text="Search", command=self.search).pack(side="left", padx=6)
            self.message = ttk.Label(bar, foreground="#52514e")
            self.message.pack(side="left")

        self.tree = ttk.Treeview(self, show="headings", height=height)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        if columns:
            self.set_columns(columns)

    def set_columns(self, columns):
        """Create the column headings; clicking one sorts by that column."""
        self.columns = columns
        self.tree.configure(columns=[key for key, _, _ in columns])
        for key, heading, width in columns:
            self.tree.heading(key, text=heading, command=lambda k=key: self.sort_by(k))
            self.tree.column(key, width=width, anchor="w")

    def set_rows(self, rows):
        """Show a new list of rows (dicts)."""
        self.rows = list(rows)
        if self.automatic and self.rows:                 # one column per key of the first row
            self.set_columns([(key, key, 120) for key in self.rows[0]])
        self.sorted_by = None
        self.show()

    def show(self):
        """Redraw the Treeview from self.rows (row i gets the id 'i')."""
        self.tree.delete(*self.tree.get_children())
        for i, row in enumerate(self.rows):
            values = ["" if row.get(key) is None else row[key] for key, _, _ in self.columns]
            self.tree.insert("", "end", iid=str(i), values=values)

    def sort_by(self, key):
        """Sort by a column with merge sort; clicking the same column again reverses it."""
        self.reverse = not self.reverse if self.sorted_by == key else False
        self.sorted_by = key
        self.rows = merge_sort(self.rows, key=lambda row: sort_value(row[key]), reverse=self.reverse)
        self.show()

    def search(self):
        """Find the row whose search column equals the text (binary search on a sorted copy)."""
        target = self.search_text.get().strip().lower()
        by_name = merge_sort(self.rows, key=lambda row: str(row[self.search_key]).lower())
        index = binary_search(by_name, target, key=lambda row: str(row[self.search_key]).lower())
        if index == -1:
            self.message.configure(text=f"'{target}' not found")
            return
        iid = str(self.rows.index(by_name[index]))
        self.tree.selection_set(iid)
        self.tree.see(iid)
        self.message.configure(text="")

    def selected(self):
        """The selected row as a dict, or None."""
        selection = self.tree.selection()
        return self.rows[int(selection[0])] if selection else None
