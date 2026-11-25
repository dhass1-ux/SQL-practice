"""
app.py: the "switchboard". Each @app.route(...) connects a web address
to a Python function. The function gets data and hands it to an HTML template.
"""

import re

import pymysql
from flask import Flask, render_template, request

from db import DatabaseConfigError, like_pattern, query

app = Flask(__name__)

SEARCH_LIMIT = 50  # most rows a search will show


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


@app.route("/search")
def search():
    """Customer search by name, email or phone."""
    # What you typed arrives in the web address: /search?q=rogers
    text = request.args.get("q", "").strip()

    if len(text) < 2:
        # Nothing (or too little) typed yet: just show the empty search box.
        return render_template("search.html", text=text, customers=None)

    # Each OR line is one way a customer can match.
    conditions = [
        "CONCAT(c.first_name, ' ', c.last_name) LIKE %s",
        "c.email LIKE %s",
    ]
    params = [like_pattern(text), like_pattern(text)]

    # Phone numbers are stored in different formats (315-555-2532,
    # (315) 555-2532, 3155552532), so compare digits only.
    # Only do this if at least 4 digits were typed; otherwise a name search
    # like "Rogers" (no digits) would match every phone number.
    digits = re.sub(r"\D", "", text)
    if len(digits) >= 4:
        conditions.append("REGEXP_REPLACE(c.phone, '[^0-9]', '') LIKE %s")
        params.append(like_pattern(digits))

    # Note: the SQL text is built only from our own fixed pieces above.
    # Everything you typed travels separately, in `params`.
    sql = f"""
        SELECT c.customer_id, c.first_name, c.last_name, c.email, c.phone,
               c.zip, c.created_date,
               (SELECT COUNT(*) FROM deals d
                 WHERE d.customer_id = c.customer_id) AS deal_count,
               (SELECT COUNT(*) FROM service_ros s
                 WHERE s.customer_id = c.customer_id) AS ro_count
        FROM customers c
        WHERE {" OR ".join(conditions)}
        ORDER BY c.last_name, c.first_name, c.customer_id
        LIMIT {SEARCH_LIMIT}
    """
    rows = query(sql, params)
    return render_template(
        "search.html", text=text, customers=rows, limit=SEARCH_LIMIT
    )


# If the database can't be reached, or .env isn't filled in, show a friendly
# page that explains what to check instead of a wall of error text.
@app.errorhandler(DatabaseConfigError)
@app.errorhandler(pymysql.err.OperationalError)
def database_problem(error):
    return render_template("db_error.html", error=error), 500
