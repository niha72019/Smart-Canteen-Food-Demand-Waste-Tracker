"""
generate_data.py - fills an EMPTY database with 90 days of canteen history.

    python -m database.setup_db         (first, to get an empty database)
    python -m database.generate_data

Each day is simulated through the same steps the app uses, so the triggers
and sp_close_day do the real work:
    restock packaged items -> cook perishable food -> sell in bills -> close day

Demand is random but realistic (numpy): busy on weekdays, quiet at weekends.
Staff cook each item's usual weekday amount, cut too little at weekends,
and always over-cook some items, so there is waste to find.
The last simulated day is yesterday, so today is free to try in the app.
"""

from datetime import date, timedelta

import numpy as np

from app.db import fetch_all, transaction

DAYS = 90
rng = np.random.default_rng(42)          # fixed seed: same data every run

# name, category, price, cost, perishable, average weekday sales, over-cooking
MENU = [
    ("Samosa",        "Snacks",    15,  7, True,   70, -0.10),
    ("Vada Pav",      "Snacks",    20,  9, True,   45, 0.00),
    ("Veg Sandwich",  "Snacks",    35, 18, True,   35, 0.05),
    ("Paneer Puff",   "Snacks",    25, 12, True,   30, 0.30),
    ("Veg Thali",     "Meals",     80, 45, True,   40, 0.35),
    ("Rajma Chawal",  "Meals",     60, 30, True,   25, 0.20),
    ("Masala Dosa",   "Meals",     50, 22, True,   35, 0.00),
    ("Masala Chai",   "Beverages", 15,  5, True,  110, 0.00),
    ("Cold Coffee",   "Beverages", 40, 18, True,   30, 0.05),
    ("Gulab Jamun",   "Desserts",  25, 10, True,   20, 0.15),
    ("Potato Chips",  "Packaged",  20, 15, False,  25, 0.00),
    ("Cola 250ml",    "Packaged",  40, 30, False,  30, 0.00),
    ("Bottled Water", "Packaged",  20, 12, False,  40, 0.00),
]
SUPPLIERS = [("FreshMart Wholesale", "9810011223", "Sector 62, Noida"),
             ("City Beverages", "9899044556", "Sector 18, Noida")]
WEEKDAY = [1.00, 1.05, 1.00, 1.05, 0.95, 0.55, 0.30]   # Mon..Sun: real demand
STAFF_CUT = [1, 1, 1, 1, 1, 0.70, 0.45]               # staff cut less than they should


def create_menu():
    """Insert categories, food items and suppliers. Returns a list of item dicts."""
    items = []
    with transaction() as cur:
        for name, contact, address in SUPPLIERS:
            cur.execute("INSERT INTO supplier (Supplier_Name, Contact, Address) VALUES (%s, %s, %s)",
                        (name, contact, address))
        for name, category, price, cost, perishable, base, extra in MENU:
            cur.execute("INSERT IGNORE INTO category (Category_Name) VALUES (%s)", (category,))
            cur.execute("SELECT Category_ID FROM category WHERE Category_Name = %s", (category,))
            category_id = cur.fetchone()["Category_ID"]
            cur.execute("INSERT INTO food_item (Food_Name, Category_ID, Selling_Price, "
                        "Preparation_Cost, Is_Perishable) VALUES (%s, %s, %s, %s, %s)",
                        (name, category_id, price, cost, perishable))
            items.append({"id": cur.lastrowid, "name": name, "price": price, "cost": cost, "perishable": perishable,
                          "base": base, "extra": extra, "stock": 0})
    return items


def simulate_day(cur, day, items):
    """Run one canteen day: restock, cook, sell, close. Returns the number of bills."""
    weekday = day.weekday()
    sold_units = []                                    # one food id per unit sold

    for item in items:
        if item["perishable"]:
            # Morning: cook the usual amount for this weekday, plus habitual extra.
            guess = item["base"] * STAFF_CUT[weekday] * (1 + item["extra"])
            available = max(5, round(guess * rng.normal(1, 0.08)))
            cur.execute("INSERT INTO daily_demand (Food_ID, Demand_Date, Quantity_Prepared) "
                        "VALUES (%s, %s, %s)", (item["id"], day, available))
        else:
            # Morning: buy ~10 days of stock (cartons of 12) when under 3 days are left.
            if item["stock"] < 3 * item["base"]:
                quantity = 12 * int(np.ceil(10 * item["base"] / 12))
                supplier = 1 if item["name"] == "Potato Chips" else 2    # drinks from City Beverages
                cur.execute("INSERT INTO purchase (Supplier_ID, Purchase_Date) VALUES (%s, %s)",
                            (supplier, day))
                cur.execute("INSERT INTO purchase_item (Purchase_ID, Food_ID, Quantity, Unit_Price) "
                            "VALUES (%s, %s, %s, %s)", (cur.lastrowid, item["id"], quantity, item["cost"]))
                item["stock"] += quantity
            available = item["stock"]

        # Customers: random demand, but nobody can buy more than is available.
        demand = rng.poisson(item["base"] * WEEKDAY[weekday] * rng.lognormal(0, 0.12))
        sold = int(min(demand, available))
        if not item["perishable"]:
            item["stock"] -= sold
        sold_units += [item["id"]] * sold

    # Day: shuffle the units and cut them into bills of 1-4 items.
    rng.shuffle(sold_units)
    price = {item["id"]: item["price"] for item in items}
    bills = 0
    while sold_units:
        size = int(rng.choice([1, 2, 3, 4], p=[0.45, 0.30, 0.15, 0.10]))
        bill, sold_units = sold_units[:size], sold_units[size:]
        cur.execute("INSERT INTO sale (Sale_Date) VALUES (%s)", (day,))
        sale_id = cur.lastrowid
        for food_id in set(bill):                      # same item twice -> one line, quantity 2
            cur.execute("INSERT INTO sale_item (Sale_ID, Food_ID, Quantity, Selling_Price) "
                        "VALUES (%s, %s, %s, %s)", (sale_id, food_id, bill.count(food_id), price[food_id]))
        bills += 1

    # Evening: close the day (sold totals, waste, packaged rows).
    cur.execute("CALL sp_close_day(%s)", (day,))
    cur.fetchall()
    while cur.nextset():
        pass
    return bills


def main():
    """Create the menu, then simulate DAYS days ending yesterday."""
    if fetch_all("SELECT 1 FROM food_item LIMIT 1"):
        print("The database already has data. Run  python -m database.setup_db  first.")
        return
    items = create_menu()
    first_day = date.today() - timedelta(days=DAYS)
    for n in range(DAYS):
        with transaction() as cur:                     # one transaction per day
            simulate_day(cur, first_day + timedelta(days=n), items)
    print(f"Simulated {DAYS} days. Rows per table:")
    for table in ["category", "food_item", "supplier", "purchase", "purchase_item", "inventory",
                  "sale", "sale_item", "waste_record", "daily_demand", "recommendation"]:
        print(f"  {table:<15}{fetch_all(f'SELECT COUNT(*) AS n FROM {table}')[0]['n']:>8,}")


if __name__ == "__main__":
    main()
