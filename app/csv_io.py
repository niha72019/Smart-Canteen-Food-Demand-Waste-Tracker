"""
csv_io.py - import past days from a CSV file and export reports to CSV
(using Python's csv module).

Import format (first line is the header):
    date,food,prepared,sold
    2026-08-01,Samosa,60,55
"""

import csv
from datetime import date

from app import validation
from app.db import DatabaseError, run_in_transaction, run_query


def import_days(path):
    """
    Import each valid row as a closed day (plus a waste record for unsold
    cooked food). Bad rows are skipped.
    Returns (number imported, list of error messages).
    """
    foods = {row["Food_Name"].lower(): row for row in
             run_query("SELECT Food_ID, Food_Name, Is_Perishable FROM food_item")}
    imported, errors = 0, []

    with open(path, newline="", encoding="utf-8") as f:
        for line_no, row in enumerate(csv.DictReader(f), start=2):   # line 1 is the header
            try:
                day = validation.check_date(row.get("date", ""))
                food = foods.get(validation.check_text(row.get("food", ""), "Food").lower())
                prepared = validation.check_quantity(row.get("prepared", ""), "Prepared")
                sold = validation.check_quantity(row.get("sold", ""), "Sold")
                validation.check_sold(prepared, sold)
                if food is None:
                    raise ValueError(f"unknown food item '{row['food']}'.")
                if day >= date.today():
                    raise ValueError("only past days can be imported.")

                # One transaction per row: the closed day first, then its waste.
                statements = [("INSERT INTO daily_demand (Food_ID, Demand_Date, Quantity_Prepared, "
                               "Quantity_Sold, Is_Closed) VALUES (%s, %s, %s, %s, TRUE)",
                               (food["Food_ID"], day, prepared, sold))]
                if food["Is_Perishable"] and prepared > sold:
                    statements.append(("INSERT INTO waste_record (Food_ID, Waste_Date, Quantity_Wasted) "
                                       "VALUES (%s, %s, %s)", (food["Food_ID"], day, prepared - sold)))
                run_in_transaction(statements)
                imported += 1
            except (ValueError, DatabaseError) as err:
                errors.append(f"Line {line_no}: {err}")
    return imported, errors


def export_rows(rows, path):
    """Write a list of dicts (e.g. a report) to a CSV file with a header row."""
    if not rows:
        raise ValueError("Nothing to export.")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
