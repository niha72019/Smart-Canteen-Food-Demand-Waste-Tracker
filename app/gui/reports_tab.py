"""reports_tab.py - CSV import, CSV export of one report, and the full report export."""

from tkinter import filedialog

import ttkbootstrap as ttk

from app import csv_io, db, reports


class ReportsTab(ttk.Frame):
    """Import past days from CSV; export reports to CSV/PNG files."""

    def __init__(self, parent):
        super().__init__(parent, padding=10)
        box = ttk.Labelframe(self, text="Import past days (CSV: date,food,prepared,sold)", padding=12)
        box.pack(fill="x")
        ttk.Button(box, text="Import CSV file...", command=self.import_csv).pack(anchor="w")

        box = ttk.Labelframe(self, text="Export", padding=12)
        box.pack(fill="x", pady=10)
        self.report = ttk.StringVar(value=list(reports.REPORTS)[0])
        ttk.Combobox(box, textvariable=self.report, values=list(reports.REPORTS), state="readonly",
                     width=32).pack(side="left")
        ttk.Button(box, text="Export to CSV...", command=self.export_one).pack(side="left", padx=6)
        ttk.Button(box, text="Export full report (CSVs + charts)", bootstyle="success",
                   command=self.export_all).pack(side="left", padx=6)

        self.output = ttk.Text(self, height=20, font=("Consolas", 10))
        self.output.pack(fill="both", expand=True)

    def refresh(self):
        """Nothing to reload on this tab."""

    def write(self, text):
        """Show a message in the output box."""
        self.output.delete("1.0", "end")
        self.output.insert("end", text)

    def import_csv(self):
        """Ask for a CSV file and import it; list the rows that were skipped."""
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        try:
            imported, errors = csv_io.import_days(path)
        except (OSError, db.DatabaseError) as err:
            self.write(f"Import failed: {err}")
            return
        self.write(f"Imported {imported} rows.\nSkipped {len(errors)} rows:\n" + "\n".join(errors))

    def export_one(self):
        """Export the chosen report to a CSV file the user picks."""
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        try:
            csv_io.export_rows(reports.REPORTS[self.report.get()](), path)
        except (OSError, ValueError, db.DatabaseError) as err:
            self.write(f"Export failed: {err}")
            return
        self.write(f"Saved {path}")

    def export_all(self):
        """Save all reports and charts into the reports/ folder."""
        try:
            files = reports.export_full_report()
        except (OSError, db.DatabaseError) as err:
            self.write(f"Export failed: {err}")
            return
        self.write(f"Saved {len(files)} files in {reports.REPORTS_DIR}:\n" + "\n".join(f.name for f in files))
