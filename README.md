# Canteen Food Demand & Waste Tracker

A desktop app for a college canteen that records how much food is cooked and sold each day,
finds which items are wasted or sell out, estimates the money lost, and recommends how much
to cook tomorrow.

Built as one project for two 3rd-semester labs:
**DBMS Lab** (*Smart Canteen Management & Food Waste Reduction System*) and
**Python Lab** (*Canteen Food Demand & Waste Tracker*).

## Features

- **Menu management**: add, edit and delete food items and their price and cost.
- **Daily production**: enter what was cooked each morning, pre-filled from recommendations.
- **Billing**: build a bill line by line. The database blocks sales when stock runs out.
- **Close day**: one click records sales, turns cooked leftovers into waste records, and makes tomorrow's recommendations.
- **Waste analysis**: waste %, unsold quantity, money lost, popular and low-demand items, and alerts for items wasting over 20%.
- **Recommendations**: rule-based and explainable, with the reason stored for each item.
- **Stock & purchases**: stock levels, low-stock warning, suppliers, purchase entry.
- **CSV import & export**: import past days (bad rows are skipped and reported), export any report, or export a full report of CSVs and chart PNGs.
- **Dashboard**: 4 KPI cards and 2 charts (prepared vs sold, waste % by item). The Reports tab shows 2 more (sales by weekday, monthly loss).
- **SQL Insights**: run any of the 20 analytical queries from inside the app.

## Tech stack

| Part | Tools |
|---|---|
| Database | MySQL 8: constraints, 7 triggers, 5 views, 2 stored procedures |
| App | Python 3, Tkinter + ttkbootstrap |
| Database access | mysql-connector-python (parameterised queries only) |
| Analysis & charts | pandas, numpy, matplotlib, seaborn |
| Files | Python `csv` module |
| Tests | pytest |

Core Python concepts are written by hand: merge sort and binary search (used for table sorting
and search), a 2D list items × days demand matrix, lists and dictionaries for the analysis, and
input validation with exceptions.

## Architecture

```mermaid
flowchart LR
    U([Canteen staff]) --> GUI["Tkinter GUI<br/>app/gui/ — 9 tabs"]
    GUI --> V["validation.py"]
    GUI --> A["analysis.py<br/>recommend.py"]
    GUI --> C["charts.py<br/>reports.py · csv_io.py"]
    V --> DB["db.py<br/>(only module with SQL for the GUI)"]
    A --> DB
    C --> DB
    DB -->|"parameterised queries"| M[("MySQL<br/>tables · triggers · views · procedures")]
    CSV[/"CSV files"/] <--> C
    C --> R[/"reports/ CSV + PNG"/]
```

**Daily workflow:** Production (morning) → Billing (day) → Close Day (evening: `sp_close_day` + next-day recommendations).

## ER diagram

```mermaid
erDiagram
    CATEGORY ||--o{ FOOD_ITEM : has
    FOOD_ITEM ||--|| INVENTORY : "stock of"
    SUPPLIER ||--o{ PURCHASE : supplies
    PURCHASE ||--o{ PURCHASE_ITEM : contains
    FOOD_ITEM ||--o{ PURCHASE_ITEM : "bought as"
    SALE ||--o{ SALE_ITEM : contains
    FOOD_ITEM ||--o{ SALE_ITEM : "sold as"
    FOOD_ITEM ||--o{ WASTE_RECORD : generates
    FOOD_ITEM ||--o{ DAILY_DEMAND : "recorded daily"
    FOOD_ITEM ||--o{ RECOMMENDATION : "recommended for"

    CATEGORY {
        int Category_ID PK
        string Category_Name
    }
    FOOD_ITEM {
        int Food_ID PK
        string Food_Name
        int Category_ID FK
        decimal Selling_Price
        decimal Preparation_Cost
        bool Is_Perishable
    }
    INVENTORY {
        int Inventory_ID PK
        int Food_ID FK
        int Quantity_Available
        datetime Last_Updated
    }
    SUPPLIER {
        int Supplier_ID PK
        string Supplier_Name
        string Contact
        string Address
    }
    PURCHASE {
        int Purchase_ID PK
        int Supplier_ID FK
        date Purchase_Date
        decimal Total_Amount
    }
    PURCHASE_ITEM {
        int Purchase_ID PK, FK
        int Food_ID PK, FK
        int Quantity
        decimal Unit_Price
    }
    SALE {
        int Sale_ID PK
        date Sale_Date
        decimal Total_Amount
    }
    SALE_ITEM {
        int Sale_ID PK, FK
        int Food_ID PK, FK
        int Quantity
        decimal Selling_Price
    }
    WASTE_RECORD {
        int Waste_ID PK
        int Food_ID FK
        date Waste_Date
        int Quantity_Wasted
        string Reason
        decimal Estimated_Loss
    }
    DAILY_DEMAND {
        int Demand_ID PK
        int Food_ID FK
        date Demand_Date
        int Quantity_Prepared
        int Quantity_Sold
        int Estimated_Demand
        bool Is_Closed
    }
    RECOMMENDATION {
        int Recommendation_ID PK
        int Food_ID FK
        date Recommendation_Date
        int Recommended_Quantity
        string Basis
    }
```

`PURCHASE_ITEM` and `SALE_ITEM` have composite primary keys and resolve the many-to-many
relationships between purchases/sales and food items.

## Setup

You need Python 3.11+ and MySQL 8 or newer.

```powershell
git clone https://github.com/niha72019/Canteen-Food-Demand-Waste-Tracker.git
cd Canteen-Food-Demand-Waste-Tracker
py -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env        # then put your MySQL password in .env
```

Create the database and fill it with 90 days of sample data:

```powershell
python -m database.setup_db         # type YES (drops and recreates the database)
python -m database.generate_data    # about 1 minute
```

## Run

```powershell
python main.py
```

Run the tests:

```powershell
python -m pytest
```

A sample file for the CSV import is in `database/sample_import.csv`. It includes a few bad
rows on purpose, to show how they are reported.

## Screenshots

**Dashboard**: 4 KPIs, prepared vs sold, and waste % by item (items over the 20% alert in orange)
![Dashboard](screenshots/dashboard.png)

**Billing**
![Billing](screenshots/billing.png)

**Recommendations**: quantity for tomorrow and the reason for each
![Recommendations](screenshots/recommendations.png)

**Reports & CSV**: CSV import/export, sales by weekday and monthly loss
![Reports & CSV](screenshots/reports.png)

**SQL Insights**: analytical queries run from the app (here: `RANK()` window function)
![SQL Insights](screenshots/sql_insights.png)

## Project structure

```
app/            Python application: db access, validation, analysis, recommendations,
                CSV import/export, charts, reports
app/gui/        one file per tab + main window
database/       schema, triggers, views, procedures, analytical queries,
                setup and sample-data scripts, sample CSV
tests/          pytest tests (database, analysis, algorithms, validation, recommendations)
main.py         starts the app
```
