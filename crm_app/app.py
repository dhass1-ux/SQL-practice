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


# One list of everything a customer has done: purchases from `deals` stacked
# on top of service visits from `service_ros` with UNION ALL (like Append
# Queries in Power Query). Both halves must return the same columns in the
# same order, so each half renames its columns to match.
TIMELINE_SQL = """
    SELECT d.sold_date AS event_date,
           'Purchase' AS kind,
           d.deal_id AS ref_id,
           r.name AS rooftop,
           CONCAT(v.model_year, ' ', v.make, ' ', v.model) AS vehicle,
           CONCAT(v.new_used, ' · ', d.deal_type) AS detail,
           d.sale_price AS amount
    FROM deals d
    JOIN rooftops r ON r.rooftop_id = d.rooftop_id
    JOIN vehicles v ON v.vin = d.vin
    WHERE d.customer_id = %s

    UNION ALL

    SELECT s.ro_date,
           'Service',
           s.ro_id,
           r.name,
           CONCAT(v.model_year, ' ', v.make, ' ', v.model),
           CONCAT(s.pay_type, ' pay'),
           s.labor_total + s.parts_total
    FROM service_ros s
    JOIN rooftops r ON r.rooftop_id = s.rooftop_id
    JOIN vehicles v ON v.vin = s.vin
    WHERE s.customer_id = %s

    ORDER BY event_date DESC, ref_id DESC
"""

# One row per rooftop the customer has used, built from the same stacked list.
ROOFTOPS_USED_SQL = """
    SELECT r.name AS rooftop,
           r.market,
           MIN(x.event_date) AS first_visit,
           MAX(x.event_date) AS last_visit,
           SUM(x.kind = 'Purchase') AS purchases,
           SUM(x.kind = 'Service') AS service_visits
    FROM (
        SELECT rooftop_id, sold_date AS event_date, 'Purchase' AS kind
        FROM deals WHERE customer_id = %s
        UNION ALL
        SELECT rooftop_id, ro_date, 'Service'
        FROM service_ros WHERE customer_id = %s
    ) AS x
    JOIN rooftops r ON r.rooftop_id = x.rooftop_id
    GROUP BY r.rooftop_id, r.name, r.market
    ORDER BY last_visit DESC
"""


# <int:customer_id> means Flask only accepts digits here, and hands the
# number to the function. /customers/abc never reaches this code.
@app.route("/customers/<int:customer_id>")
def customer(customer_id):
    """One customer: details, rooftops used, and a combined timeline."""
    found = query(
        """
        SELECT customer_id, first_name, last_name, email, phone, zip, created_date
        FROM customers
        WHERE customer_id = %s
        """,
        (customer_id,),
    )
    if not found:
        return render_template(
            "not_found.html", message=f"There's no customer #{customer_id}."
        ), 404

    # The same id fills both %s placeholders (one in each half of the UNION).
    timeline = query(TIMELINE_SQL, (customer_id, customer_id))
    rooftops_used = query(ROOFTOPS_USED_SQL, (customer_id, customer_id))

    # Summary numbers, counted from the timeline we already have
    # (no need to ask the database again).
    dates = [event["event_date"] for event in timeline]
    summary = {
        "purchases": sum(1 for e in timeline if e["kind"] == "Purchase"),
        "service_visits": sum(1 for e in timeline if e["kind"] == "Service"),
        "rooftops": len(rooftops_used),
        "first_activity": min(dates) if dates else None,
        "last_activity": max(dates) if dates else None,
    }

    return render_template(
        "customer.html",
        customer=found[0],
        timeline=timeline,
        rooftops_used=rooftops_used,
        summary=summary,
    )


# Any address the app doesn't know (including /customers/abc).
@app.errorhandler(404)
def page_not_found(error):
    return render_template(
        "not_found.html", message="That page doesn't exist."
    ), 404


# If the database can't be reached, or .env isn't filled in, show a friendly
# page that explains what to check instead of a wall of error text.
@app.errorhandler(DatabaseConfigError)
@app.errorhandler(pymysql.err.OperationalError)
def database_problem(error):
    return render_template("db_error.html", error=error), 500
