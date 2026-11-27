"""
notes.py: your own notes and follow-ups on a customer.

Stored in crm.customer_notes (see sql/crm_notes.sql). A note with a
follow-up date is a follow-up; it's "open" until you mark it done.

What the app's database user is allowed to do here:
    add a note        INSERT
    mark done/reopen  UPDATE, but only the done_at column
    delete a note     DELETE
The text of a saved note can't be changed, by design.
"""

from datetime import date

import links
from db import in_list, query, transaction

MAX_LENGTH = 2000  # matches VARCHAR(2000) in the table


class NoteError(Exception):
    """A note that can't be saved as-is. The message is shown to you."""


def add_note(customer_id, body, follow_up_text):
    """
    Save a note on the person's MAIN record. Returns the main record id.

    Everything a browser sends can be altered, so check it all here
    even though the form also limits the length and offers a date picker.
    """
    body = body.replace("\r\n", "\n").strip()
    if not body:
        raise NoteError("Write something before saving.")
    if len(body) > MAX_LENGTH:
        raise NoteError(
            f"Notes can be up to {MAX_LENGTH:,} characters; that one is {len(body):,}."
        )

    follow_up = None
    if follow_up_text.strip():
        try:
            # Date pickers send dates as YYYY-MM-DD, e.g. 2026-12-01.
            follow_up = date.fromisoformat(follow_up_text.strip())
        except ValueError:
            raise NoteError("That follow-up date isn't a real date.")
        if not 2000 <= follow_up.year <= 2100:
            raise NoteError("Pick a follow-up date between 2000 and 2100.")

    # Notes belong to the PERSON: save them on the main record, so they still
    # show up if more records are linked later.
    main_id, _ = links.get_group(customer_id)
    if not links.customer_summaries([main_id]):
        raise NoteError(f"There's no customer #{customer_id}.")

    with transaction() as cursor:
        cursor.execute(
            """
            INSERT INTO crm.customer_notes (customer_id, body, follow_up_date)
            VALUES (%s, %s, %s)
            """,
            (main_id, body, follow_up),
        )
    return main_id


def set_done(note_id, done):
    """Mark a follow-up done (done=True) or open again (done=False)."""
    with transaction() as cursor:
        if done:
            cursor.execute(
                """
                UPDATE crm.customer_notes
                SET done_at = UTC_TIMESTAMP()
                WHERE note_id = %s AND follow_up_date IS NOT NULL AND done_at IS NULL
                """,
                (note_id,),
            )
        else:
            cursor.execute(
                """
                UPDATE crm.customer_notes
                SET done_at = NULL
                WHERE note_id = %s AND done_at IS NOT NULL
                """,
                (note_id,),
            )
        if cursor.rowcount != 1:
            raise NoteError("That follow-up has already changed. Refresh the page.")


def delete_note(note_id):
    with transaction() as cursor:
        cursor.execute("DELETE FROM crm.customer_notes WHERE note_id = %s", (note_id,))
        if cursor.rowcount != 1:
            raise NoteError("That note was already deleted.")


def notes_for(customer_ids):
    """
    Notes on any of these records (a person's main record plus linked ones),
    split into (open follow-ups, everything else).
    """
    ids = list(customer_ids)
    rows = query(
        f"""
        SELECT note_id, customer_id, body, follow_up_date, done_at, created_at
        FROM crm.customer_notes
        WHERE customer_id IN ({in_list(ids)})
        ORDER BY created_at DESC, note_id DESC
        """,
        ids,
    )
    open_items = sorted(
        (n for n in rows if n["follow_up_date"] and not n["done_at"]),
        key=lambda n: (n["follow_up_date"], n["note_id"]),
    )
    everything_else = [n for n in rows if not (n["follow_up_date"] and not n["done_at"])]
    return open_items, everything_else


def open_follow_ups():
    """Every open follow-up across all customers, soonest first."""
    return query(
        """
        SELECT n.note_id, n.customer_id, n.body, n.follow_up_date, n.created_at,
               c.first_name, c.last_name
        FROM crm.customer_notes n
        JOIN customers c ON c.customer_id = n.customer_id
        WHERE n.follow_up_date IS NOT NULL AND n.done_at IS NULL
        ORDER BY n.follow_up_date, n.note_id
        """
    )
