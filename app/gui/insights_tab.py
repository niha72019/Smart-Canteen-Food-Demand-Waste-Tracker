"""SQL Insights tab: run an analytical query and show its result."""

import ttkbootstrap as ttk

from app import db
from app.gui.table import DataTable
from app.queries import QUERIES


class InsightsTab(ttk.Frame):
    """Drop-down of the analytical queries and a table for the result."""

    def __init__(self, parent):
        super().__init__(parent, padding=10)
        self.queries = QUERIES
        top = ttk.Frame(self)
        top.pack(fill="x")
        self.choice = ttk.StringVar(value=list(QUERIES)[0])
        ttk.Combobox(top, textvariable=self.choice, values=list(QUERIES), state="readonly",
                     width=90).pack(side="left")
        ttk.Button(top, text="Run", bootstyle="success", command=self.run).pack(side="left", padx=6)
        self.sql = ttk.Label(self, font=("Consolas", 9), foreground="#52514e", wraplength=1150)
        self.sql.pack(anchor="w", pady=8)
        self.table = DataTable(self, height=20)
        self.table.pack(fill="both", expand=True)

    def refresh(self):
        """Nothing to reload until a query is run."""

    def run(self):
        """Run the chosen query and show its SQL and its rows."""
        sql = QUERIES[self.choice.get()]
        self.sql.configure(text=sql)
        try:
            rows = db.run_query(sql)
        except db.DatabaseError as err:
            ttk.Messagebox.show_error(str(err), "Query failed")
            return
        self.table.set_rows(rows if rows else [{"Result": "No rows"}])
