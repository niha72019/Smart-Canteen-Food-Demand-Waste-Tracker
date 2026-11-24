"""Tests for the triggers, views and sp_close_day; every test is rolled back."""

import mysql.connector
import pytest

from app.db import get_connection

DAY = "2000-01-03"


@pytest.fixture
def cur():
    """A cursor whose changes are rolled back after the test."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)
    yield cursor
    conn.rollback()
    conn.close()


def add_item(cur, name, perishable=True):
    """Create a test food item (price 20, cost 8) and return its id."""
    cur.execute("INSERT INTO category (Category_Name) VALUES (%s)", (name + " category",))
    cur.execute("INSERT INTO food_item (Food_Name, Category_ID, Selling_Price, Preparation_Cost, "
                "Is_Perishable) VALUES (%s, %s, 20, 8, %s)", (name, cur.lastrowid, perishable))
    return cur.lastrowid


def stock(cur, food_id):
    """Current stock of an item."""
    cur.execute("SELECT Quantity_Available FROM inventory WHERE Food_ID = %s", (food_id,))
    return cur.fetchone()["Quantity_Available"]


def sell(cur, food_id, quantity):
    """Make a one-line bill and return its Sale_ID."""
    cur.execute("INSERT INTO sale (Sale_Date) VALUES (%s)", (DAY,))
    sale_id = cur.lastrowid
    cur.execute("INSERT INTO sale_item VALUES (%s, %s, %s, 20)", (sale_id, food_id, quantity))
    return sale_id


def test_new_item_gets_inventory_row(cur):
    assert stock(cur, add_item(cur, "Test Samosa")) == 0


def test_purchase_adds_stock_and_total(cur):
    chips = add_item(cur, "Test Chips", perishable=False)
    cur.execute("INSERT INTO purchase (Supplier_ID, Purchase_Date) VALUES (1, %s)", (DAY,))
    purchase_id = cur.lastrowid
    cur.execute("INSERT INTO purchase_item VALUES (%s, %s, 24, 15)", (purchase_id, chips))
    cur.execute("SELECT Total_Amount FROM purchase WHERE Purchase_ID = %s", (purchase_id,))
    assert cur.fetchone()["Total_Amount"] == 24 * 15
    assert stock(cur, chips) == 24


def test_production_adds_stock_and_edit_moves_it(cur):
    samosa = add_item(cur, "Test Samosa")
    cur.execute("INSERT INTO daily_demand (Food_ID, Demand_Date, Quantity_Prepared) VALUES (%s, %s, 40)",
                (samosa, DAY))
    assert stock(cur, samosa) == 40
    cur.execute("UPDATE daily_demand SET Quantity_Prepared = 50 WHERE Food_ID = %s", (samosa,))
    assert stock(cur, samosa) == 50


def test_cannot_reduce_production_below_sold(cur):
    samosa = add_item(cur, "Test Samosa")
    cur.execute("INSERT INTO daily_demand (Food_ID, Demand_Date, Quantity_Prepared) VALUES (%s, %s, 10)",
                (samosa, DAY))
    sell(cur, samosa, 8)
    with pytest.raises(mysql.connector.Error, match="below what is already sold"):
        cur.execute("UPDATE daily_demand SET Quantity_Prepared = 5 WHERE Food_ID = %s", (samosa,))


def test_sale_reduces_stock_and_sets_total(cur):
    samosa = add_item(cur, "Test Samosa")
    cur.execute("INSERT INTO daily_demand (Food_ID, Demand_Date, Quantity_Prepared) VALUES (%s, %s, 10)",
                (samosa, DAY))
    sale_id = sell(cur, samosa, 3)
    cur.execute("SELECT Total_Amount FROM sale WHERE Sale_ID = %s", (sale_id,))
    assert cur.fetchone()["Total_Amount"] == 60
    assert stock(cur, samosa) == 7


def test_sale_refused_without_stock(cur):
    samosa = add_item(cur, "Test Samosa")
    with pytest.raises(mysql.connector.Error, match="Not enough stock: only 0 left"):
        sell(cur, samosa, 1)


def test_waste_loss_is_filled_in(cur):
    samosa = add_item(cur, "Test Samosa")
    cur.execute("INSERT INTO waste_record (Food_ID, Waste_Date, Quantity_Wasted) VALUES (%s, %s, 5)",
                (samosa, DAY))
    cur.execute("SELECT Estimated_Loss FROM waste_record WHERE Waste_ID = %s", (cur.lastrowid,))
    assert cur.fetchone()["Estimated_Loss"] == 5 * 8


def test_close_day(cur):
    samosa = add_item(cur, "Test Samosa")
    chips = add_item(cur, "Test Chips", perishable=False)
    cur.execute("INSERT INTO daily_demand (Food_ID, Demand_Date, Quantity_Prepared) VALUES (%s, %s, 40)",
                (samosa, DAY))
    cur.execute("UPDATE inventory SET Quantity_Available = 50 WHERE Food_ID = %s", (chips,))
    sell(cur, samosa, 30)
    sell(cur, chips, 12)

    cur.execute("CALL sp_close_day(%s)", (DAY,))
    while cur.nextset():
        pass

    cur.execute("SELECT * FROM v_daily_waste WHERE Demand_Date = %s ORDER BY Food_Name", (DAY,))
    chips_row, samosa_row = cur.fetchall()
    assert (samosa_row["Quantity_Sold"], samosa_row["Wasted"], samosa_row["Waste_Pct"]) == (30, 10, 25)
    assert samosa_row["Loss"] == 10 * 8
    assert (chips_row["Quantity_Prepared"], chips_row["Quantity_Sold"], chips_row["Wasted"]) == (50, 12, 0)
    assert stock(cur, samosa) == 0 and stock(cur, chips) == 38
    with pytest.raises(mysql.connector.Error, match="already closed"):
        cur.execute("CALL sp_close_day(%s)", (DAY,))
