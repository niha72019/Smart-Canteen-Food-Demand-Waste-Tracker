"""db.py - the only module that talks to MySQL. Every value is passed with %s (no SQL injection)."""

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


def run_query(sql, params=()):
    """Run one statement (SELECT or CALL), commit it, and return its rows as a list of dicts."""
    conn = get_connection()
    cur = conn.cursor(dictionary=True)        # each row comes back as a dict
    try:
        cur.execute(sql, params)
        rows = cur.fetchall()
        while cur.nextset():                  # a CALL sends one extra status result; read it
            pass
        conn.commit()
        return rows
    except mysql.connector.Error as err:
        conn.rollback()
        raise DatabaseError(err.msg) from err  # for our triggers err.msg is the SIGNAL text
    finally:
        cur.close()
        conn.close()


def run_in_transaction(statements):
    """Run a list of (sql, params) as ONE transaction (all saved or none). Returns the first new id."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        first_id = None
        for sql, params in statements:
            cur.execute(sql, params)
            if first_id is None:
                first_id = cur.lastrowid
        conn.commit()
        return first_id
    except mysql.connector.Error as err:
        conn.rollback()
        raise DatabaseError(err.msg) from err
    finally:
        cur.close()
        conn.close()


# ---------------------------------------------------------------------------
# Canteen operations used by the GUI (so the GUI itself contains no SQL)
# ---------------------------------------------------------------------------

def list_items():
    """All food items with category and current stock."""
    return run_query(
        "SELECT f.Food_ID, f.Food_Name, c.Category_Name, f.Selling_Price, f.Preparation_Cost, "
        "f.Is_Perishable, i.Quantity_Available FROM food_item f "
        "JOIN category c ON c.Category_ID = f.Category_ID "
        "JOIN inventory i ON i.Food_ID = f.Food_ID ORDER BY f.Food_Name")


def list_categories():
    """Category names, A to Z."""
    return [r["Category_Name"] for r in run_query("SELECT Category_Name FROM category ORDER BY Category_Name")]


def category_id(name):
    """Return the id of a category, creating the category if it does not exist yet."""
    rows = run_query("SELECT Category_ID FROM category WHERE Category_Name = %s", (name,))
    if rows:
        return rows[0]["Category_ID"]
    return run_in_transaction([("INSERT INTO category (Category_Name) VALUES (%s)", (name,))])


def save_item(food_id, name, category, price, cost, perishable):
    """Add a new item (food_id None) or update an existing one."""
    cat_id = category_id(category)
    if food_id is None:
        run_in_transaction([("INSERT INTO food_item (Food_Name, Category_ID, Selling_Price, Preparation_Cost, "
                             "Is_Perishable) VALUES (%s, %s, %s, %s, %s)", (name, cat_id, price, cost, perishable))])
    else:
        run_in_transaction([("UPDATE food_item SET Food_Name = %s, Category_ID = %s, Selling_Price = %s, "
                             "Preparation_Cost = %s, Is_Perishable = %s WHERE Food_ID = %s",
                             (name, cat_id, price, cost, perishable, food_id))])


def delete_item(food_id):
    """Delete an item. Refused (by the foreign keys) if it has any history."""
    try:
        run_in_transaction([("DELETE FROM food_item WHERE Food_ID = %s", (food_id,))])
    except DatabaseError:
        raise DatabaseError("This item has sales or production history, so it cannot be deleted.") from None


def day_is_closed(day):
    """True if sp_close_day has already processed this day."""
    return bool(run_query("SELECT 1 FROM daily_demand WHERE Demand_Date = %s AND Is_Closed = TRUE LIMIT 1", (day,)))


def production_sheet(day):
    """Cooked items with the recommended quantity and anything already entered for the day."""
    return run_query(
        "SELECT f.Food_ID, f.Food_Name, r.Recommended_Quantity, d.Quantity_Prepared FROM food_item f "
        "LEFT JOIN recommendation r ON r.Food_ID = f.Food_ID AND r.Recommendation_Date = %s "
        "LEFT JOIN daily_demand d ON d.Food_ID = f.Food_ID AND d.Demand_Date = %s "
        "WHERE f.Is_Perishable = TRUE ORDER BY f.Food_Name", (day, day))


def save_production(day, quantities):
    """Save {Food_ID: quantity prepared}: update existing entries, insert new ones (with Estimated_Demand)."""
    if day_is_closed(day):
        raise DatabaseError("This day is already closed.")
    existing = [r["Food_ID"] for r in run_query("SELECT Food_ID FROM daily_demand WHERE Demand_Date = %s", (day,))]
    statements = []
    for food_id, quantity in quantities.items():
        if food_id in existing:
            statements.append(("UPDATE daily_demand SET Quantity_Prepared = %s WHERE Food_ID = %s AND Demand_Date = %s",
                               (quantity, food_id, day)))
        else:
            statements.append(("INSERT INTO daily_demand (Food_ID, Demand_Date, Quantity_Prepared, Estimated_Demand) "
                               "VALUES (%s, %s, %s, (SELECT Recommended_Quantity FROM recommendation "
                               "WHERE Food_ID = %s AND Recommendation_Date = %s))",
                               (food_id, day, quantity, food_id, day)))
    run_in_transaction(statements)


def save_bill(day, lines):
    """Save one bill. lines = {Food_ID: (quantity, price)}. Returns (Sale_ID, total)."""
    if day_is_closed(day):
        raise DatabaseError("This day is already closed.")
    statements = [("INSERT INTO sale (Sale_Date) VALUES (%s)", (day,))]
    for food_id, (quantity, price) in lines.items():
        statements.append(("INSERT INTO sale_item (Sale_ID, Food_ID, Quantity, Selling_Price) "   # LAST_INSERT_ID()
                           "VALUES (LAST_INSERT_ID(), %s, %s, %s)", (food_id, quantity, price)))  # = the new Sale_ID
    sale_id = run_in_transaction(statements)
    total = run_query("SELECT Total_Amount FROM sale WHERE Sale_ID = %s", (sale_id,))[0]["Total_Amount"]
    return sale_id, total


def close_day(day):
    """Run sp_close_day (one transaction) and return its summary rows."""
    return run_query("CALL sp_close_day(%s)", (day,))


def list_suppliers():
    """All suppliers with their purchase totals (v_supplier_summary)."""
    return run_query("SELECT * FROM v_supplier_summary ORDER BY Supplier_Name")


def save_purchase(supplier_id, day, food_id, quantity, unit_price):
    """Save a one-line purchase; the trigger adds the stock and the total."""
    run_in_transaction([
        ("INSERT INTO purchase (Supplier_ID, Purchase_Date) VALUES (%s, %s)", (supplier_id, day)),
        ("INSERT INTO purchase_item (Purchase_ID, Food_ID, Quantity, Unit_Price) "
         "VALUES (LAST_INSERT_ID(), %s, %s, %s)", (food_id, quantity, unit_price)),
    ])


def low_stock():
    """Packaged items with under 3 days of stock (v_low_stock)."""
    return run_query("SELECT * FROM v_low_stock")


def latest_recommendations():
    """Recommendations for the most recent target day."""
    return run_query(
        "SELECT r.Recommendation_Date, f.Food_Name, r.Recommended_Quantity, r.Basis "
        "FROM recommendation r JOIN food_item f ON f.Food_ID = r.Food_ID "
        "WHERE r.Recommendation_Date = (SELECT MAX(Recommendation_Date) FROM recommendation) "
        "ORDER BY f.Food_Name")


def sales_on(day):
    """Number of bills and revenue for one day."""
    return run_query("SELECT COUNT(*) AS bills, COALESCE(SUM(Total_Amount), 0) AS revenue "
                     "FROM sale WHERE Sale_Date = %s", (day,))[0]


def monthly_loss():
    """Money lost to waste per month (v_monthly_loss)."""
    return run_query("SELECT * FROM v_monthly_loss ORDER BY Month")


def daily_waste(days=30):
    """v_daily_waste rows for the last `days` days."""
    return run_query("SELECT * FROM v_daily_waste WHERE Demand_Date >= CURDATE() - INTERVAL %s DAY "
                     "ORDER BY Demand_Date, Food_Name", (days,))
