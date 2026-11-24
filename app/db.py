"""
db.py - the only module that talks to MySQL.

Every query uses %s placeholders, never string formatting with user input,
so values cannot be used for SQL injection.
"""

from contextlib import contextmanager

import mysql.connector

from app.config import DB_CONFIG


class DatabaseError(Exception):
    """A database problem, with a message that can be shown to the user."""


def get_connection():
    """Open a new connection to the canteen database."""
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except mysql.connector.Error as err:
        raise DatabaseError(f"Cannot connect to MySQL: {err.msg}") from err


@contextmanager
def transaction():
    """
    Give a cursor for one transaction:
    commit if everything works, roll back everything if anything fails.

        with transaction() as cur:
            cur.execute("INSERT ...", (value1, value2))
    """
    conn = get_connection()
    cur = conn.cursor(dictionary=True)   # each row comes back as a dict
    try:
        yield cur
        conn.commit()
    except mysql.connector.Error as err:
        conn.rollback()
        # err.msg is MySQL's message; for our triggers it is the SIGNAL text.
        raise DatabaseError(err.msg) from err
    finally:
        cur.close()
        conn.close()


def fetch_all(sql, params=()):
    """Run a SELECT (or CALL) and return the rows as a list of dicts."""
    with transaction() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
        while cur.nextset():      # a CALL also returns a status result; skip it
            pass
        return rows


def execute(sql, params=()):
    """Run one INSERT/UPDATE/DELETE and commit it. Returns the new row's id."""
    with transaction() as cur:
        cur.execute(sql, params)
        return cur.lastrowid


# ---------------------------------------------------------------------------
# Canteen operations used by the GUI (so the GUI itself contains no SQL)
# ---------------------------------------------------------------------------

def list_items():
    """All food items with category and current stock."""
    return fetch_all(
        "SELECT f.Food_ID, f.Food_Name, c.Category_Name, f.Selling_Price, f.Preparation_Cost, "
        "f.Is_Perishable, i.Quantity_Available FROM food_item f "
        "JOIN category c ON c.Category_ID = f.Category_ID "
        "JOIN inventory i ON i.Food_ID = f.Food_ID ORDER BY f.Food_Name")


def list_categories():
    """Category names, A to Z."""
    return [r["Category_Name"] for r in fetch_all("SELECT Category_Name FROM category ORDER BY Category_Name")]


def save_item(food_id, name, category, price, cost, perishable):
    """Add a new item (food_id None) or update an existing one. New categories are created."""
    with transaction() as cur:
        cur.execute("INSERT IGNORE INTO category (Category_Name) VALUES (%s)", (category,))
        cur.execute("SELECT Category_ID FROM category WHERE Category_Name = %s", (category,))
        category_id = cur.fetchone()["Category_ID"]
        if food_id is None:
            cur.execute("INSERT INTO food_item (Food_Name, Category_ID, Selling_Price, Preparation_Cost, "
                        "Is_Perishable) VALUES (%s, %s, %s, %s, %s)", (name, category_id, price, cost, perishable))
        else:
            cur.execute("UPDATE food_item SET Food_Name = %s, Category_ID = %s, Selling_Price = %s, "
                        "Preparation_Cost = %s, Is_Perishable = %s WHERE Food_ID = %s",
                        (name, category_id, price, cost, perishable, food_id))


def delete_item(food_id):
    """Delete an item. Refused (by the foreign keys) if it has any history."""
    try:
        execute("DELETE FROM food_item WHERE Food_ID = %s", (food_id,))
    except DatabaseError:
        raise DatabaseError("This item has sales or production history, so it cannot be deleted.") from None


def day_is_closed(day):
    """True if sp_close_day has already processed this day."""
    return bool(fetch_all("SELECT 1 FROM daily_demand WHERE Demand_Date = %s AND Is_Closed = TRUE LIMIT 1", (day,)))


def production_sheet(day):
    """Cooked items with the recommended quantity and anything already entered for the day."""
    return fetch_all(
        "SELECT f.Food_ID, f.Food_Name, r.Recommended_Quantity, d.Quantity_Prepared FROM food_item f "
        "LEFT JOIN recommendation r ON r.Food_ID = f.Food_ID AND r.Recommendation_Date = %s "
        "LEFT JOIN daily_demand d ON d.Food_ID = f.Food_ID AND d.Demand_Date = %s "
        "WHERE f.Is_Perishable = TRUE ORDER BY f.Food_Name", (day, day))


def save_production(day, quantities):
    """
    Save {Food_ID: quantity prepared} for the day. Estimated_Demand gets the
    recommendation in force; a second save updates the quantity (trigger moves stock).
    """
    if day_is_closed(day):
        raise DatabaseError("This day is already closed.")
    with transaction() as cur:
        for food_id, quantity in quantities.items():
            cur.execute(
                "INSERT INTO daily_demand (Food_ID, Demand_Date, Quantity_Prepared, Estimated_Demand) "
                "VALUES (%s, %s, %s, (SELECT Recommended_Quantity FROM recommendation "
                "WHERE Food_ID = %s AND Recommendation_Date = %s)) AS new "
                "ON DUPLICATE KEY UPDATE Quantity_Prepared = new.Quantity_Prepared",
                (food_id, day, quantity, food_id, day))


def save_bill(day, lines):
    """Save one bill. lines = {Food_ID: (quantity, price)}. Returns (Sale_ID, total)."""
    if day_is_closed(day):
        raise DatabaseError("This day is already closed.")
    with transaction() as cur:
        cur.execute("INSERT INTO sale (Sale_Date) VALUES (%s)", (day,))
        sale_id = cur.lastrowid
        for food_id, (quantity, price) in lines.items():
            cur.execute("INSERT INTO sale_item (Sale_ID, Food_ID, Quantity, Selling_Price) VALUES (%s, %s, %s, %s)",
                        (sale_id, food_id, quantity, price))
        cur.execute("SELECT Total_Amount FROM sale WHERE Sale_ID = %s", (sale_id,))
        return sale_id, cur.fetchone()["Total_Amount"]


def close_day(day):
    """Run sp_close_day in one transaction and return its summary rows."""
    return fetch_all("CALL sp_close_day(%s)", (day,))


def list_suppliers():
    """All suppliers with their purchase totals (v_supplier_summary)."""
    return fetch_all("SELECT * FROM v_supplier_summary ORDER BY Supplier_Name")


def save_purchase(supplier_id, day, food_id, quantity, unit_price):
    """Save a one-line purchase; the trigger adds the stock and the total."""
    with transaction() as cur:
        cur.execute("INSERT INTO purchase (Supplier_ID, Purchase_Date) VALUES (%s, %s)", (supplier_id, day))
        cur.execute("INSERT INTO purchase_item (Purchase_ID, Food_ID, Quantity, Unit_Price) VALUES (%s, %s, %s, %s)",
                    (cur.lastrowid, food_id, quantity, unit_price))


def low_stock():
    """Packaged items with under 3 days of stock (v_low_stock)."""
    return fetch_all("SELECT * FROM v_low_stock")


def latest_recommendations():
    """Recommendations for the most recent target day."""
    return fetch_all(
        "SELECT r.Recommendation_Date, f.Food_Name, r.Recommended_Quantity, r.Basis "
        "FROM recommendation r JOIN food_item f ON f.Food_ID = r.Food_ID "
        "WHERE r.Recommendation_Date = (SELECT MAX(Recommendation_Date) FROM recommendation) "
        "ORDER BY f.Food_Name")


def sales_on(day):
    """Number of bills and revenue for one day."""
    return fetch_all("SELECT COUNT(*) AS bills, COALESCE(SUM(Total_Amount), 0) AS revenue "
                     "FROM sale WHERE Sale_Date = %s", (day,))[0]


def monthly_loss():
    """Money lost to waste per month (v_monthly_loss)."""
    return fetch_all("SELECT * FROM v_monthly_loss ORDER BY Month")


def daily_waste(days=30):
    """v_daily_waste rows for the last `days` days."""
    return fetch_all("SELECT * FROM v_daily_waste WHERE Demand_Date >= CURDATE() - INTERVAL %s DAY "
                     "ORDER BY Demand_Date, Food_Name", (days,))
