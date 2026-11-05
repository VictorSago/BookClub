"""Database access for members: cards, reading, creating,
changing, deleting and anonymising.
"""

import secrets
from datetime import date

from core.database import RuleViolation, connect, like_pattern


# Constants and card numbers

CARD_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ1234567890"
CARD_LENGTH = 12

ANONYMISED_NAME = "Anonymised member"

_MEMBER_COLUMNS = "member_id, name, email, phone, joined_at, anonymised_at"
_EDITABLE_MEMBER_COLUMNS = ("name", "email", "phone")


def new_card_number() -> str:
    """Return a random card number made of capital letters and digits."""
    return "".join(secrets.choice(CARD_ALPHABET) for _ in range(CARD_LENGTH))


def _new_unused_card_number(conn) -> str:
    """Return a card number that no member has. Callers pass an open
    connection."""
    while True:
        card_number = new_card_number()
        if conn.execute(
            "SELECT 1 FROM members WHERE card_number = ?", (card_number,)
        ).fetchone() is None:
            return card_number


# Helpers

def select_members(conn, where: str = "", params=()) -> list[dict]:
    """Return members ordered by name.

    The ``where`` is a fixed SQL fragment on the members table (or empty),
    and params are its values. Callers pass an open connection.
    """
    rows = conn.execute(
        "SELECT " + _MEMBER_COLUMNS + " FROM members" + where
        + " ORDER BY name COLLATE NOCASE, member_id",
        params
    ).fetchall()
    return [dict(row) for row in rows]


def _select_member(conn, member_id: int) -> dict | None:
    """Return one member, anonymised or not, or None. Callers pass an open
    connection."""
    members = select_members(conn, " WHERE member_id = ?", (member_id,))
    return members[0] if members else None


def _ensure_email_free(conn, email: str, *, own_member_id: int | None = None) -> None:
    """Raise RuleViolation if another member already has this email.

    The comparison ignores case, because the column is declared COLLATE NOCASE.
    A member's own email does not count as taken.
    """
    row = conn.execute(
        "SELECT member_id FROM members WHERE email = ?", (email,)
    ).fetchone()
    if row is not None and row["member_id"] != own_member_id:
        raise RuleViolation("Another member already has this email address.")


# Reading members

def find_member_by_card(card_number: str) -> dict | None:
    """Return the member who owns this card, or None.

    Anonymised members are ignored, so their old cards cannot log in.
    """
    with connect() as conn:
        row = conn.execute(
            "SELECT member_id, card_number, name FROM members "
            "WHERE card_number = ? AND anonymised_at IS NULL",
            (card_number,)
        ).fetchone()
    return dict(row) if row is not None else None


def list_members(*, name: str | None = None) -> list[dict]:
    """Return the members who are not anonymised, ordered by name.

    Args:
        name: if given, only members whose name contains this text
            (case-insensitive for ASCII).
    """
    conditions = ["anonymised_at IS NULL"]
    params = []
    if name is not None:
        conditions.append("name LIKE ? ESCAPE '\\'")
        params.append(like_pattern(name))
    with connect() as conn:
        return select_members(conn, " WHERE " + " AND ".join(conditions), params)


def get_member_by_id(member_id: int) -> dict | None:
    """Return one member by ID, or None if there is no such ID."""
    with connect() as conn:
        return _select_member(conn, member_id)


# Changing members

def create_member(name: str, email: str, *, phone: str | None = None) -> dict:
    """Register a member and return them, with their new card number.

    The card number is made here and the join date is the column default,
    so the caller chooses neither.

    Raises:
        RuleViolation: if another member already has this email.
    """
    with connect() as conn:
        # Take the write lock first, so the email check and the insert
        # cannot be interleaved with another request.
        conn.execute("BEGIN IMMEDIATE")
        _ensure_email_free(conn, email)
        card_number = _new_unused_card_number(conn)
        conn.execute(
            "INSERT INTO members (card_number, name, email, phone) "
            "VALUES (?, ?, ?, ?)",
            (card_number, name, email, phone)
        )
        row = conn.execute(
            "SELECT " + _MEMBER_COLUMNS + " FROM members WHERE card_number = ?",
            (card_number,)
        ).fetchone()
    return {**dict(row), "card_number": card_number}


def update_member(member_id: int, changes: dict) -> dict | None:
    """Change a member's name, email or phone and return the member, or None.

    Args:
        member_id: the member to change.
        changes: the new values, by column. Only the keys ``name``, ``email``
            and ``phone`` are used; the card number and join date cannot be
            changed. Columns that are not in ``changes`` stay as they are.

    Returns:
        The member after the change (same shape as ``get_member_by_id()``),
        or None if there is no such member.

    Raises:
        RuleViolation: if the member is anonymised, or another member
            already has the new email.
    """
    columns = [c for c in _EDITABLE_MEMBER_COLUMNS if c in changes]
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        member = _select_member(conn, member_id)
        if member is None:
            return None
        if member["anonymised_at"] is not None:
            raise RuleViolation("An anonymised member cannot be changed.")
        if "email" in columns:
            _ensure_email_free(conn, changes["email"], own_member_id=member_id)
        if columns:
            conn.execute(
                "UPDATE members SET "
                + ", ".join(column + " = ?" for column in columns)
                + " WHERE member_id = ?",
                [changes[column] for column in columns] + [member_id]
            )
            member = _select_member(conn, member_id)
    return member


def delete_member(member_id: int) -> dict | None:
    """Delete a member who has never borrowed a book and return them, or None.

    Returns:
        The deleted member (same shape as ``get_member_by_id()``), or None
        if there is no such member.

    Raises:
        RuleViolation: if the member has any loan, open or returned. The
            loan history must stay, so such a member is anonymised instead.
    """
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        member = _select_member(conn, member_id)
        if member is None:
            return None
        if conn.execute(
            "SELECT 1 FROM loans WHERE member_id = ?", (member_id,)
        ).fetchone():
            raise RuleViolation(
                "This member has borrowing history and cannot be deleted. "
                "Anonymise the member instead."
            )
        conn.execute("DELETE FROM members WHERE member_id = ?", (member_id,))
    return member


def anonymise_member(member_id: int) -> dict | None:
    """Remove a member's personal data but keep their loan history.

    The name and email are replaced by placeholders, the phone number is
    cleared, the card is replaced by a new random one (so the old card stops
    working) and ``anonymised_at`` is set to today. The loans stay, now
    attached to an anonymous member.

    Returns:
        The member afterwards (same shape as ``get_member_by_id()``), or
        None if there is no such member.

    Raises:
        RuleViolation: if the member is already anonymised or still has a
            book on loan.
    """
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        member = _select_member(conn, member_id)
        if member is None:
            return None
        if member["anonymised_at"] is not None:
            raise RuleViolation("This member is already anonymised.")
        if conn.execute(
            "SELECT 1 FROM loans WHERE member_id = ? AND return_date IS NULL",
            (member_id,)
        ).fetchone():
            raise RuleViolation(
                "This member still has a book on loan. Return all books first."
            )
        conn.execute(
            "UPDATE members SET name = ?, email = ?, phone = NULL, "
            "card_number = ?, anonymised_at = ? WHERE member_id = ?",
            (
                ANONYMISED_NAME,
                f"anonymised-{secrets.token_hex(4)}@example.invalid",
                _new_unused_card_number(conn),
                date.today().isoformat(),
                member_id,
            )
        )
        member = _select_member(conn, member_id)
    return member


def delete_or_anonymise_member(member_id: int) -> dict | None:
    """Remove a member: delete them if they never borrowed, else anonymise.

    A member without loans is deleted. A member with loan history is
    anonymised, so the history stays.

    Returns:
        The member as ``delete_member()`` or ``anonymise_member()`` returns
        them, or None if there is no such member.

    Raises:
        RuleViolation: if the member still has a book on loan.
    """
    try:
        return delete_member(member_id)
    except RuleViolation:  # Raised only because the member has loans.
        return anonymise_member(member_id)
