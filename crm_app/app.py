"""
app.py: the "switchboard". Each @app.route(...) connects a web address
to a Python function. The function gets data and hands it to an HTML template.
"""

import pymysql
from flask import Flask, render_template

from db import DatabaseConfigError, query

app = Flask(__name__)


@app.route("/")
def rooftops():
    """Home page: list every rooftop."""
    rows = query(
        """
        SELECT rooftop_id, name, brand, market, is_luxury, opened_date
        FROM rooftops
        ORDER BY rooftop_id
        """
    )
    # Fill templates/rooftops.html with the rows and send the page back.
    return render_template("rooftops.html", rooftops=rows)


# If the database can't be reached, or .env isn't filled in, show a friendly
# page that explains what to check instead of a wall of error text.
@app.errorhandler(DatabaseConfigError)
@app.errorhandler(pymysql.err.OperationalError)
def database_problem(error):
    return render_template("db_error.html", error=error), 500
