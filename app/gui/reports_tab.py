"""Reports & CSV tab: import past days and export reports."""

from tkinter import filedialog

import ttkbootstrap as ttk

from app import charts, csv_io, db, reports


class ReportsTab(ttk.Frame):
    """Import and export buttons, an output box and 2 report charts."""

    def __init__(self, parent):
        super().__init__(parent, padding=10)
        row = ttk.Frame(self)
        row.pack(fill="x")
        box = ttk.Labelframe(row, text="Import past days (CSV: date,food,prepared,sold)", padding=12)
        box.pack(side="left", fill="y")
        ttk.Button(box, text="Import CSV file...", command=self.import_csv).pack(anchor="w")

        box = ttk.Labelframe(row, text="Export", padding=12)
        box.pack(side="left", fill="both", expand=True, padx=(10, 0))
        self.report = ttk.StringVar(value=list(reports.REPORTS)[0])
        ttk.Combobox(box, textvariable=self.report, values=list(reports.REPORTS), state="readonly",
                     width=28).pack(side="left")
        ttk.Button(box, text="Export to CSV...", command=self.export_one).pack(side="left", padx=6)
        ttk.Button(box, text="Export full report", bootstyle="success",
                   command=self.export_all).pack(side="left", padx=6)

        self.output = ttk.Text(self, height=2, font=("Consolas", 10))
        self.output.pack(fill="x", pady=(10, 0))
        self.chart_area = ttk.Frame(self)
        self.chart_area.pack(fill="both", expand=True, pady=(10, 0))

    def refresh(self):
        """Redraw the 2 report charts."""
        charts.show(charts.report_charts(), self.chart_area)

    def write(self, text):
        """Show a message in the output box."""
        self.output.delete("1.0", "end")
        self.output.insert("end", text)

    def import_csv(self):
        """Import a CSV file chosen by the user and list the skipped rows."""
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
