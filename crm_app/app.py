"""
app.py: the "switchboard". Each @app.route(...) connects a web address
to a Python function. The function gets data and hands it to an HTML template.

Pages that only LOOK at data use GET (the normal kind of link).
Actions that CHANGE something use POST (a form button), then redirect
back to a normal page, so pressing Refresh can't repeat the action.
"""

import os
import re
from datetime import date, timezone
from zoneinfo import ZoneInfo

import pymysql
from flask import Flask, flash, redirect, render_template, request, url_for
from flask_wtf.csrf import CSRFError, CSRFProtect

import links
import notes
from db import (
    DatabaseConfigError,
    close_request_connection,
    in_list,
    like_pattern,
    query,
)

app = Flask(__name__)

# SECRET_KEY (from .env) is used to sign the hidden token on every form.
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
if not app.config["SECRET_KEY"]:
    raise RuntimeError(
        "SECRET_KEY is missing from crm_app/.env. Make one with:\n"
        '  python -c "import secrets; print(secrets.token_hex(32))"'
    )

# Every POST form must carry a valid token, or Flask-WTF rejects it.
# This stops other websites from submitting forms to your app.
CSRFProtect(app)

# Hang up the page's database connection when each request finishes.
app.teardown_appcontext(close_request_connection)

SEARCH_LIMIT = 50  # most rows a search will show

# The Azure server keeps time in UTC (5 hours ahead of Buffalo in winter).
# Times are stored in UTC and converted to this time zone only for display.
LOCAL_TIMEZONE = ZoneInfo("America/New_York")


@app.template_filter("local_time")
def local_time(value, fmt="%b %d, %Y %I:%M %p"):
    """In a template: {{ note.created_at | local_time }} -> "Nov 26, 2026 10:05 PM"."""
    if value is None:
        return ""
    utc_time = value.replace(tzinfo=timezone.utc)  # the database gives it without a zone
    return utc_time.astimezone(LOCAL_TIMEZONE).strftime(fmt)


@app.context_processor
def add_today():
    """Makes `today` (your computer's date, not the server's) available in every template."""
    return {"today": date.today()}


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
    # The LEFT JOIN adds which main record (if any) each customer is linked to.
    sql = f"""
        SELECT c.customer_id, c.first_name, c.last_name, c.email, c.phone,
               c.zip, c.created_date,
               (SELECT COUNT(*) FROM deals d
                 WHERE d.customer_id = c.customer_id) AS deal_count,
               (SELECT COUNT(*) FROM service_ros s
                 WHERE s.customer_id = c.customer_id) AS ro_count,
               l.primary_id AS linked_to
        FROM customers c
        LEFT JOIN crm.customer_links l ON l.duplicate_id = c.customer_id
        WHERE {" OR ".join(conditions)}
        ORDER BY c.last_name, c.first_name, c.customer_id
        LIMIT {SEARCH_LIMIT}
    """
    rows = query(sql, params)
    return render_template(
        "search.html", text=text, customers=rows, limit=SEARCH_LIMIT
    )


# One list of everything a person has done: purchases from `deals` stacked
# on top of service visits from `service_ros` with UNION ALL (like Append
# Queries in Power Query). Both halves must return the same columns in the
# same order, so each half renames its columns to match.
# {ids} becomes "%s, %s, ..." (one per customer record in the group).
TIMELINE_SQL = """
    SELECT d.sold_date AS event_date,
           'Purchase' AS kind,
           d.deal_id AS ref_id,
           d.customer_id AS record_id,
           r.name AS rooftop,
           CONCAT(v.model_year, ' ', v.make, ' ', v.model) AS vehicle,
           CONCAT(v.new_used, ' · ', d.deal_type) AS detail,
           d.sale_price AS amount
    FROM deals d
    JOIN rooftops r ON r.rooftop_id = d.rooftop_id
    JOIN vehicles v ON v.vin = d.vin
    WHERE d.customer_id IN ({ids})

    UNION ALL

    SELECT s.ro_date,
           'Service',
           s.ro_id,
           s.customer_id,
           r.name,
           CONCAT(v.model_year, ' ', v.make, ' ', v.model),
           CONCAT(s.pay_type, ' pay'),
           s.labor_total + s.parts_total
    FROM service_ros s
    JOIN rooftops r ON r.rooftop_id = s.rooftop_id
    JOIN vehicles v ON v.vin = s.vin
    WHERE s.customer_id IN ({ids})

    ORDER BY event_date DESC, ref_id DESC
"""

# One row per rooftop the person has used, built from the same stacked list.
ROOFTOPS_USED_SQL = """
    SELECT r.name AS rooftop,
           r.market,
           MIN(x.event_date) AS first_visit,
           MAX(x.event_date) AS last_visit,
           SUM(x.kind = 'Purchase') AS purchases,
           SUM(x.kind = 'Service') AS service_visits
    FROM (
        SELECT rooftop_id, sold_date AS event_date, 'Purchase' AS kind
        FROM deals WHERE customer_id IN ({ids})
        UNION ALL
        SELECT rooftop_id, ro_date, 'Service'
        FROM service_ros WHERE customer_id IN ({ids})
    ) AS x
    JOIN rooftops r ON r.rooftop_id = x.rooftop_id
    GROUP BY r.rooftop_id, r.name, r.market
    ORDER BY last_visit DESC
"""


# <int:customer_id> means Flask only accepts digits here, and hands the
# number to the function. /customers/abc never reaches this code.
@app.route("/customers/<int:customer_id>")
def customer(customer_id):
    """One PERSON: their main record plus any linked records, combined."""
    main_id, group_links = links.get_group(customer_id)
    ids = [main_id] + [link["duplicate_id"] for link in group_links]

    records = links.customer_summaries(ids)  # {id: details}
    if customer_id not in records:
        return render_template(
            "not_found.html", message=f"There's no customer #{customer_id}."
        ), 404

    # Every id appears twice in the SQL (once in each half of the UNION),
    # so the list of values is repeated: ids + ids.
    placeholders = in_list(ids)
    timeline = query(TIMELINE_SQL.format(ids=placeholders), ids + ids)
    rooftops_used = query(ROOFTOPS_USED_SQL.format(ids=placeholders), ids + ids)

    # Summary numbers, counted from the timeline we already have.
    dates = [event["event_date"] for event in timeline]
    summary = {
        "purchases": sum(1 for e in timeline if e["kind"] == "Purchase"),
        "service_visits": sum(1 for e in timeline if e["kind"] == "Service"),
        "rooftops": len(rooftops_used),
        "first_activity": min(dates) if dates else None,
        "last_activity": max(dates) if dates else None,
    }

    open_follow_ups, other_notes = notes.notes_for(ids)

    return render_template(
        "customer.html",
        customer=records[main_id],
        opened_id=customer_id,
        open_follow_ups=open_follow_ups,
        other_notes=other_notes,
        note_max_length=notes.MAX_LENGTH,
        records=[records[i] for i in ids],
        group_links={link["duplicate_id"]: link for link in group_links},
        timeline=timeline,
        rooftops_used=rooftops_used,
        summary=summary,
    )


# ---------------------------------------------------------------- duplicates

@app.route("/duplicates")
def duplicates():
    """Review page with three tabs: to review, linked, different people."""
    tab = request.args.get("tab", "review")
    pairs = links.find_pairs_to_review()
    counts = dict(links.count_decisions(), review=len(pairs))

    if tab == "linked":
        rows = links.list_links()
    elif tab == "different":
        rows = links.list_not_duplicates()
    else:
        tab, rows = "review", pairs

    return render_template("duplicates.html", tab=tab, rows=rows, counts=counts)


def form_id(name):
    """Read a customer number from the submitted form."""
    value = request.form.get(name, "").strip().lstrip("#")
    if not value.isdigit():
        raise links.LinkError("Customer numbers must be whole numbers, like 2847.")
    return int(value)


def back_to(tab):
    return redirect(url_for("duplicates", tab=tab))


@app.post("/duplicates/link")
def link_pair():
    """'Same person' button on a review pair."""
    try:
        a, b, main_id = form_id("a"), form_id("b"), form_id("main")
        if main_id not in (a, b):
            raise links.LinkError("Pick one of the two records as the main record.")
        extra_id = b if main_id == a else a
        used = links.link_records(main_id, extra_id, request.form.get("reason", ""))
        flash(f"Linked #{extra_id} to main record #{used}.", "ok")
    except links.LinkError as problem:
        flash(str(problem), "error")
    return back_to("review")


@app.post("/duplicates/link-by-number")
def link_by_number():
    """The 'Link by customer number' box, for pairs the review list can't find."""
    try:
        main_id, extra_id = form_id("main_id"), form_id("extra_id")
        used = links.link_records(main_id, extra_id, links.MANUAL_REASON)
        note = "" if used == main_id else f" (#{main_id} was already part of #{used})"
        flash(f"Linked #{extra_id} to main record #{used}{note}.", "ok")
        return back_to("linked")
    except links.LinkError as problem:
        flash(str(problem), "error")
        return back_to("review")


@app.post("/duplicates/unlink")
def unlink():
    try:
        extra_id = form_id("extra_id")
        if links.unlink(extra_id):
            flash(f"Unlinked #{extra_id}. Its original record was never changed.", "ok")
        else:
            flash(f"#{extra_id} wasn't linked.", "error")
    except links.LinkError as problem:
        flash(str(problem), "error")
    return back_to("linked")


@app.post("/duplicates/different")
def mark_different():
    """'Different people' button on a review pair."""
    try:
        a, b = form_id("a"), form_id("b")
        links.mark_not_duplicates(a, b)
        flash(f"Marked #{a} and #{b} as different people.", "ok")
    except links.LinkError as problem:
        flash(str(problem), "error")
    return back_to("review")


@app.post("/duplicates/undo-different")
def undo_different():
    try:
        a, b = form_id("a"), form_id("b")
        links.undo_not_duplicates(a, b)
        flash(f"#{a} and #{b} are back in the review list.", "ok")
    except links.LinkError as problem:
        flash(str(problem), "error")
    return back_to("different")


# ---------------------------------------------------------------- notes and follow-ups

@app.route("/follow-ups")
def follow_ups():
    """Every open follow-up across all customers: your to-do list."""
    return render_template("follow_ups.html", items=notes.open_follow_ups())


def go_back():
    """
    After a note action, return to where the form was: the Follow-ups page,
    or a customer page. `back` is checked to be digits, so it can only ever
    lead to a page inside this app.
    """
    back = request.form.get("back", "")
    if back.isdigit():
        return redirect(url_for("customer", customer_id=int(back)))
    return redirect(url_for("follow_ups"))


def form_note_id():
    value = request.form.get("note_id", "")
    if not value.isdigit():
        raise notes.NoteError("Missing note number. Refresh the page and try again.")
    return int(value)


@app.post("/notes/add")
def add_note():
    try:
        customer_id = form_id("customer_id")
        notes.add_note(
            customer_id,
            request.form.get("body", ""),
            request.form.get("follow_up_date", ""),
        )
        flash("Note saved.", "ok")
    except (notes.NoteError, links.LinkError) as problem:
        flash(str(problem), "error")
    return go_back()


@app.post("/notes/done")
def note_done():
    try:
        notes.set_done(form_note_id(), done=True)
        flash("Follow-up marked done.", "ok")
    except notes.NoteError as problem:
        flash(str(problem), "error")
    return go_back()


@app.post("/notes/reopen")
def note_reopen():
    try:
        notes.set_done(form_note_id(), done=False)
        flash("Follow-up reopened.", "ok")
    except notes.NoteError as problem:
        flash(str(problem), "error")
    return go_back()


@app.post("/notes/delete")
def note_delete():
    try:
        notes.delete_note(form_note_id())
        flash("Note deleted.", "ok")
    except notes.NoteError as problem:
        flash(str(problem), "error")
    return go_back()


# ---------------------------------------------------------------- error pages

# Any address the app doesn't know (including /customers/abc).
@app.errorhandler(404)
def page_not_found(error):
    return render_template(
        "not_found.html", message="That page doesn't exist."
    ), 404


# A form arrived without a valid token: an old page, or another website.
@app.errorhandler(CSRFError)
def form_expired(error):
    return render_template(
        "not_found.html",
        title="Form expired",
        message="That form was out of date or didn't come from this app, so nothing "
        "was changed. Go back, refresh the page, and try again.",
    ), 400


# If the database can't be reached, a table is missing, or .env isn't filled
# in, show a friendly page that explains what to check.
@app.errorhandler(DatabaseConfigError)
@app.errorhandler(pymysql.err.OperationalError)
@app.errorhandler(pymysql.err.ProgrammingError)
def database_problem(error):
    return render_template("db_error.html", error=error), 500
