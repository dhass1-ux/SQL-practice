"""
db.py: everything that talks to the database lives in this one file.

The rest of the app never opens a connection itself. It calls query()
and gets back a list of rows, which keeps the database details in one place.
"""

import os
from pathlib import Path

import certifi
import pymysql
from dotenv import load_dotenv

# Read the .env file that sits next to this file and load its values
# (DB_HOST, DB_USER, ...) so os.environ can see them.
load_dotenv(Path(__file__).parent / ".env")

REQUIRED_SETTINGS = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"]


class DatabaseConfigError(Exception):
    """Raised when .env is missing or incomplete, so we can show a clear message."""


def get_connection():
    """Open a new, encrypted connection to the Azure MySQL server."""
    missing = [name for name in REQUIRED_SETTINGS if not os.environ.get(name)]
    if missing:
        raise DatabaseConfigError(
            "These settings are missing from crm_app/.env: " + ", ".join(missing)
        )

    return pymysql.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "3306")),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
        # Azure requires SSL. Giving PyMySQL a list of trusted certificates
        # (from certifi) turns encryption on AND makes it check that the server
        # really is your Azure server, not an impostor.
        ssl={"ca": certifi.where()},
        # Return each row as a dictionary, e.g. row["name"], instead of row[1].
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10,
    )


def query(sql, params=()):
    """
    Run a SELECT and return all rows as a list of dictionaries.

    ALWAYS pass values through `params`, never by gluing them into `sql`:

        query("SELECT * FROM customers WHERE email = %s", (email,))   # safe
        query(f"SELECT * FROM customers WHERE email = '{email}'")      # NEVER

    With params, the database receives the SQL and the values separately,
    so a value can only ever be data, never extra SQL commands.
    This is what protects the app from "SQL injection".
    """
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()
    finally:
        # Always hang up, even if the query failed.
        connection.close()
