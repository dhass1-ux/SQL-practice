"""
links.py: finding and linking duplicate customer records.

Decisions are stored in the separate `crm` database (see sql/crm_schema.sql):
    crm.customer_links   "extra record #2847 belongs to main record #34"
    crm.not_duplicates   "#X and #Y were reviewed: different people"

The original rows in dealer_practice (customers, deals, service_ros) are
only ever READ here. The app's database user isn't even allowed to change them.

The shape of a group is kept simple on purpose: one MAIN record, plus any
number of EXTRA records pointing straight at it (never extra -> extra -> main).
"""

from db import in_list, query, transaction

ALLOWED_REASONS = {"same email", "same phone", "same email, same phone"}
MANUAL_REASON = "linked by hand"


class LinkError(Exception):
    """A request that breaks one of the linking rules. The message is shown to you."""


# ---------------------------------------------------------------- finding pairs

# Emails (ignoring case) and phones (digits only) shared by 2+ customers.
# GROUP BY + HAVING COUNT(*) > 1 reads the customers table once, which is
# far faster than comparing every customer with every other customer.
DUPLICATE_GROUPS_SQL = """
    SELECT 'email' AS how,
           GROUP_CONCAT(customer_id ORDER BY customer_id) AS ids
    FROM customers
    WHERE email IS NOT NULL
    GROUP BY LOWER(email)
    HAVING COUNT(*) > 1

    UNION ALL

    SELECT 'phone',
           GROUP_CONCAT(customer_id ORDER BY customer_id)
    FROM customers
    WHERE phone IS NOT NULL
    GROUP BY REGEXP_REPLACE(phone, '[^0-9]', '')
    HAVING COUNT(*) > 1
"""


def customer_summaries(ids):
    """Customer details plus purchase/service counts, as {customer_id: row}."""
    if not ids:
        return {}
    ids = list(ids)
    rows = query(
        f"""
        SELECT c.customer_id, c.first_name, c.last_name, c.email, c.phone,
               c.zip, c.created_date,
               (SELECT COUNT(*) FROM deals d
                 WHERE d.customer_id = c.customer_id) AS deal_count,
               (SELECT COUNT(*) FROM service_ros s
                 WHERE s.customer_id = c.customer_id) AS ro_count
        FROM customers c
        WHERE c.customer_id IN ({in_list(ids)})
        """,
        ids,
    )
    return {row["customer_id"]: row for row in rows}


def find_pairs_to_review():
    """Likely duplicate pairs that haven't been decided yet."""
    # 1. Turn each matching group into pairs: {(low_id, high_id): {"email", "phone"}}
    pairs = {}
    for group in query(DUPLICATE_GROUPS_SQL):
        ids = [int(x) for x in group["ids"].split(",")]
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                pairs.setdefault((a, b), set()).add(group["how"])

    # 2. Skip pairs already decided: linked into the same group, or marked different.
    main_of = {
        row["duplicate_id"]: row["primary_id"]
        for row in query("SELECT duplicate_id, primary_id FROM crm.customer_links")
    }
    different = {
        (row["customer_id_low"], row["customer_id_high"])
        for row in query("SELECT customer_id_low, customer_id_high FROM crm.not_duplicates")
    }
    open_pairs = [
        (a, b, hows)
        for (a, b), hows in pairs.items()
        if main_of.get(a, a) != main_of.get(b, b) and (a, b) not in different
    ]

    # 3. Look up both customers' details in one query.
    details = customer_summaries({cid for a, b, _ in open_pairs for cid in (a, b)})

    result = []
    for a, b, hows in sorted(open_pairs, key=lambda p: p[1]):
        first, second = details[a], details[b]
        # Suggest the OLDER record as the main one (usually the original).
        older = min(first, second, key=lambda c: (c["created_date"], c["customer_id"]))
        result.append({
            "a": first,
            "b": second,
            "same_email": "email" in hows,
            "same_phone": "phone" in hows,
            "reason": ", ".join(f"same {h}" for h in ("email", "phone") if h in hows),
            "suggested_main": older["customer_id"],
        })
    return result


# ---------------------------------------------------------------- reading decisions

def get_group(customer_id):
    """
    The group a customer belongs to:
        main_id  the main record's id (the customer's own id if not linked)
        links    one row per extra record linked to that main record
    """
    row = query(
        "SELECT primary_id FROM crm.customer_links WHERE duplicate_id = %s",
        (customer_id,),
    )
    main_id = row[0]["primary_id"] if row else customer_id
    links = query(
        """
        SELECT duplicate_id, match_reason, linked_at
        FROM crm.customer_links
        WHERE primary_id = %s
        ORDER BY duplicate_id
        """,
        (main_id,),
    )
    return main_id, links


def list_links():
    """Every link, with both customers' names, newest first."""
    return query(
        """
        SELECT l.duplicate_id, l.primary_id, l.match_reason, l.linked_at,
               CONCAT(m.first_name, ' ', m.last_name) AS main_name,
               CONCAT(x.first_name, ' ', x.last_name) AS extra_name
        FROM crm.customer_links l
        JOIN customers m ON m.customer_id = l.primary_id
        JOIN customers x ON x.customer_id = l.duplicate_id
        ORDER BY l.linked_at DESC, l.duplicate_id
        """
    )


def list_not_duplicates():
    """Every pair marked as different people, newest first."""
    return query(
        """
        SELECT n.customer_id_low, n.customer_id_high, n.decided_at,
               CONCAT(a.first_name, ' ', a.last_name) AS low_name,
               CONCAT(b.first_name, ' ', b.last_name) AS high_name
        FROM crm.not_duplicates n
        JOIN customers a ON a.customer_id = n.customer_id_low
        JOIN customers b ON b.customer_id = n.customer_id_high
        ORDER BY n.decided_at DESC, n.customer_id_low
        """
    )


def count_decisions():
    row = query(
        """
        SELECT (SELECT COUNT(*) FROM crm.customer_links) AS linked,
               (SELECT COUNT(*) FROM crm.not_duplicates) AS different
        """
    )
    return row[0]


# ---------------------------------------------------------------- writing decisions

def link_records(main_id, extra_id, reason):
    """
    Record that `extra_id` is the same person as `main_id`.
    Returns the main id actually used (see rule 3).
    """
    if reason not in ALLOWED_REASONS:
        reason = MANUAL_REASON
    if main_id == extra_id:
        raise LinkError("A record can't be linked to itself.")

    with transaction() as cursor:
        # Rule 1: both customers must exist.
        cursor.execute(
            "SELECT customer_id FROM customers WHERE customer_id IN (%s, %s)",
            (main_id, extra_id),
        )
        found = {row["customer_id"] for row in cursor.fetchall()}
        for cid in (main_id, extra_id):
            if cid not in found:
                raise LinkError(f"There's no customer #{cid}.")

        # Rule 2: the extra record can't already belong to a group...
        cursor.execute(
            "SELECT primary_id FROM crm.customer_links WHERE duplicate_id = %s",
            (extra_id,),
        )
        row = cursor.fetchone()
        if row:
            raise LinkError(
                f"#{extra_id} is already linked to #{row['primary_id']}. "
                "Unlink it first if that was a mistake."
            )
        # ...or be the main record of a group (that would make a chain).
        cursor.execute(
            "SELECT COUNT(*) AS n FROM crm.customer_links WHERE primary_id = %s",
            (extra_id,),
        )
        if cursor.fetchone()["n"]:
            raise LinkError(
                f"#{extra_id} is already the main record for other linked records. "
                f"Pick #{extra_id} as the main record instead."
            )

        # Rule 3: if the chosen main record is itself an extra record,
        # attach to ITS main record so the group stays one level deep.
        cursor.execute(
            "SELECT primary_id FROM crm.customer_links WHERE duplicate_id = %s",
            (main_id,),
        )
        row = cursor.fetchone()
        if row:
            main_id = row["primary_id"]
            if main_id == extra_id:
                raise LinkError("Those two records are already linked.")

        cursor.execute(
            """
            INSERT INTO crm.customer_links (duplicate_id, primary_id, match_reason)
            VALUES (%s, %s, %s)
            """,
            (extra_id, main_id, reason),
        )
        # If this pair was once marked "different people", that's no longer true.
        cursor.execute(
            """
            DELETE FROM crm.not_duplicates
            WHERE customer_id_low = %s AND customer_id_high = %s
            """,
            (min(main_id, extra_id), max(main_id, extra_id)),
        )
    return main_id


def unlink(extra_id):
    """Remove one extra record from its group. Returns True if a link was removed."""
    with transaction() as cursor:
        cursor.execute(
            "DELETE FROM crm.customer_links WHERE duplicate_id = %s", (extra_id,)
        )
        return cursor.rowcount == 1


def mark_not_duplicates(id_a, id_b):
    """Record that two customers were reviewed and are different people."""
    low, high = min(id_a, id_b), max(id_a, id_b)
    if low == high:
        raise LinkError("Pick two different customers.")
    # There are no foreign keys across the two databases, so check here.
    found = customer_summaries([low, high])
    for cid in (low, high):
        if cid not in found:
            raise LinkError(f"There's no customer #{cid}.")
    main_low, _ = get_group(low)
    main_high, _ = get_group(high)
    if main_low == main_high:
        raise LinkError(f"#{low} and #{high} are linked. Unlink them first.")
    with transaction() as cursor:
        # INSERT IGNORE: if this pair is already recorded, quietly do nothing.
        cursor.execute(
            """
            INSERT IGNORE INTO crm.not_duplicates (customer_id_low, customer_id_high)
            VALUES (%s, %s)
            """,
            (low, high),
        )


def undo_not_duplicates(id_a, id_b):
    """Put a pair back in the review list."""
    with transaction() as cursor:
        cursor.execute(
            """
            DELETE FROM crm.not_duplicates
            WHERE customer_id_low = %s AND customer_id_high = %s
            """,
            (min(id_a, id_b), max(id_a, id_b)),
        )
