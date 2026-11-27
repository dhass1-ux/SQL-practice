"""
db.py: everything that talks to the database lives in this one file.

The rest of the app never opens a connection itself. It calls:
    query(...)          to READ rows
    transaction()       to WRITE (everything saved together, or nothing)
"""

import os
from contextlib import contextmanager
from pathlib import Path

import certifi
import pymysql
from dotenv import load_dotenv
from flask import g, has_app_context

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
        # Each statement counts on its own unless we start a transaction
        # ourselves (see transaction() below).
        autocommit=True,
    )


def _connection():
    """
    Opening a connection to Azure takes about half a second, so each page
    request opens ONE connection the first time it needs it and reuses it
    for every query on that page. close_request_connection() hangs up
    when the page is finished.

    Outside a page request (for example a quick test script), each call
    just gets its own new connection.
    """
    if not has_app_context():
        return get_connection(), True  # (connection, close it when done?)
    if "db" not in g:
        g.db = get_connection()
    return g.db, False


def close_request_connection(error=None):
    """Called by Flask automatically at the end of every page request."""
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


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
    connection, close_after = _connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()
    finally:
        if close_after:
            connection.close()


@contextmanager
def transaction():
    """
    Use this for anything that WRITES:

        with transaction() as cursor:
            cursor.execute("INSERT ...", (...))
            cursor.execute("DELETE ...", (...))

    Everything inside the `with` block is saved together when the block
    finishes ("commit"). If anything goes wrong partway, including one of
    our own rule checks raising an error, NOTHING is saved ("rollback").
    Like a bank transfer: the money leaves one account and arrives in the
    other, or neither happens.
    """
    connection, close_after = _connection()
    connection.begin()
    try:
        with connection.cursor() as cursor:
            yield cursor
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        if close_after:
            connection.close()


def in_list(values):
    """
    Placeholders for an IN (...) list: in_list([4, 8, 15]) -> "%s, %s, %s".

    We generate one %s per value (never the values themselves), and the
    values still travel separately as params:

        ids = [34, 2847]
        query(f"SELECT * FROM customers WHERE customer_id IN ({in_list(ids)})", ids)
    """
    return ", ".join(["%s"] * len(values))


def like_pattern(text):
    """
    Turn search text into a LIKE pattern meaning "contains this text".

    In LIKE, % means "any characters" and _ means "any one character".
    If someone searches for a literal % or _, we put a backslash in front
    so MySQL treats it as an ordinary character, not a wildcard.

        like_pattern("rogers")  ->  "%rogers%"
        like_pattern("50%")     ->  "%50\\%%"   (finds the text "50%", not everything)
    """
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return "%" + escaped + "%"
