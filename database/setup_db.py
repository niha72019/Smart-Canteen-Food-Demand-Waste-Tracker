"""
setup_db.py - (re)creates the database from the .sql files.

    python -m database.setup_db

WARNING: drops the whole database first, so all data is deleted.
"""

import mysql.connector

from app.config import DB_CONFIG

SQL_FILES = ["schema.sql", "triggers.sql", "views.sql", "procedures.sql"]


def split_statements(text):
    """
    Split a .sql file into single statements.
    mysql-connector runs one statement at a time and does not understand
    Workbench's 'DELIMITER $$' line, so we handle it here.
    """
    statements, current, delimiter = [], [], ";"
    for line in text.splitlines():
        if line.strip().startswith("--") or not line.strip():
            continue                                   # skip comments and blank lines
        if line.upper().startswith("DELIMITER"):
            delimiter = line.split()[1]                # e.g. $$ or ;
            continue
        current.append(line)
        if line.rstrip().endswith(delimiter):          # end of a statement
            statements.append("\n".join(current).rstrip()[: -len(delimiter)])
            current = []
    return statements


def main():
    """Drop and recreate the database, then run every .sql file in order."""
    name = DB_CONFIG["database"]
    if input(f"This deletes ALL data in '{name}'. Type YES to continue: ") != "YES":
        return
    login = {k: v for k, v in DB_CONFIG.items() if k != "database"}
    conn = mysql.connector.connect(**login)
    cur = conn.cursor()
    cur.execute(f"DROP DATABASE IF EXISTS `{name}`")     # name comes from .env, not a user
    cur.execute(f"CREATE DATABASE `{name}`")
    cur.execute(f"USE `{name}`")
    for file_name in SQL_FILES:
        with open(f"database/{file_name}", encoding="utf-8") as f:
            statements = split_statements(f.read())
        for statement in statements:
            cur.execute(statement)
        print(f"{file_name}: {len(statements)} statements")
    cur.execute("SHOW FULL TABLES")
    tables = cur.fetchall()
    print(f"Done: {sum(t[1] == 'BASE TABLE' for t in tables)} tables, "
          f"{sum(t[1] == 'VIEW' for t in tables)} views.")
    conn.close()


if __name__ == "__main__":
    main()
