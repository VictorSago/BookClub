"""Database access for the Book Club Library.

Two ways to get a connection to the SQLite database:

* ``connect()``: a context manager. It commits when the ``with`` block ends
  normally, rolls back if an exception occurs, and always closes the
  connection.
* ``get_connection()``: returns a plain connection. The caller must commit
  and close it.

Both enable foreign key enforcement and return rows that can be turned into
dictionaries with ``dict(row)``. Open a new connection in each database
function; do not share one connection between requests.

The database file is ``library.db`` next to this file. Set the environment
variable ``LIBRARY_DB`` to use another file. This module never creates the
tables: that is the job of ``schema.sql`` and ``seed.py``.

Examples:
    from core.database import connect

    with connect() as conn:
        conn.execute(
            "UPDATE loans SET return_date = ? WHERE loan_id = ?",
            ("2026-11-02", 7),
        )

    with connect() as conn:
        rows = conn.execute("SELECT * FROM books").fetchall()
    books = [dict(row) for row in rows]
"""

import os
import secrets
import sqlite3
from collections import defaultdict
from collections.abc import Generator
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB = BASE_DIR / "library.db"

DB_PATH = Path(os.environ.get("LIBRARY_DB", DEFAULT_DB))

CARD_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ1234567890"
CARD_LENGTH = 12

LOAN_DAYS = 21  # Keep in sync with the default loan length in the API.

ANONYMISED_NAME = "Anonymised member"

_MEMBER_COLUMNS = "member_id, name, email, phone, joined_at, anonymised_at"
_EDITABLE_MEMBER_COLUMNS = ("name", "email", "phone")



class RuleViolation(Exception):
    """Raised when a request breaks a library rule.

    The message is meant for the user, for example "This book is already
    on loan." The API turns it into a 409 response.
    """


def get_connection(create: bool = False) -> sqlite3.Connection:
    """Open the library database and return the connection.

    Foreign keys are enabled and rows can be read like dictionaries. The
    caller is responsible for calling ``commit()`` after changes and
    ``close()`` when done.

    Args:
        create: if True, a missing database file is created (only ``seed.py`` 
            should do this). If False, a missing file is an error, so a 
            mistake does not silently result in an empty database.

    Raises:
        FileNotFoundError: if the file does not exist and ``create`` is False.
    """
    if not create and not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}\n"
            "Run seed.py first or set the LIBRARY_DB environment variable."
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def connect(create: bool = False) -> Generator[sqlite3.Connection]:
    """Open the library database as a context manager and yield the connection.

    If the block finishes normally, changes are committed; if it raises an
    exception, they are rolled back and the exception is re-raised. The
    connection is always closed at the end.

    Args:
        create: see ``get_connection()``.

    Raises:
        FileNotFoundError: if the file does not exist and ``create`` is False.
    """
    conn = get_connection(create)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _like_pattern(text: str) -> str:
    """Turn user text into a "contains" pattern for LIKE, with the
    wildcard characters % and _ treated as ordinary characters."""
    escaped = text.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
    return "%" + escaped + "%"


_ON_LOAN = (
    "EXISTS (SELECT 1 FROM loans l "
    "WHERE l.book_id = b.book_id AND l.return_date IS NULL)"
)


def _select_books(conn, where: str = "", params=()) -> list[dict]:
    """Return books with authors and availability.

    The ``where`` is a fixed SQL fragment on the alias b (or empty), and params
    are its values. Callers pass an open connection.
    """
    book_rows = conn.execute(
        "SELECT b.book_id, b.title, b.first_publish_year, b.isbn, "
        "b.open_library_key, b.added_at, "
        "NOT " + _ON_LOAN + " AS available "
        "FROM books b" 
        + where 
        + " ORDER BY b.title COLLATE NOCASE",
        params
    ).fetchall()
    author_rows = conn.execute(
        "SELECT ba.book_id, a.name "
        "FROM book_authors ba "
        "JOIN authors a ON a.author_id = ba.author_id "
        "WHERE ba.book_id IN (SELECT b.book_id FROM books b" + where + ") "
        "ORDER BY ba.rowid",
        params
    ).fetchall()
    
    authors_by_book = defaultdict(list)
    for row in author_rows:
        authors_by_book[row["book_id"]].append(row["name"])
    return [
        {**dict(row), "authors": authors_by_book[row["book_id"]]} for row in book_rows
    ]


def list_books(
    *, 
    title: str | None = None, 
    year: int | None = None, 
    author: str | None = None, 
    available: bool | None = None
    ) -> list[dict]:
    """Return books, each with a list of its author names.

    Filters are optional and combine with AND:
        title: the title contains this text (case-insensitive for ASCII).
        year: the first publication year is exactly this.
        author: one of the book's authors has a name containing this text.
        available: True gives only books that are not on loan, False only
            books that are.
    """
    conditions = []
    params = []
    if title is not None:
        conditions.append("b.title LIKE ? ESCAPE '\\'")
        params.append(_like_pattern(title))
    if year is not None:
        conditions.append("b.first_publish_year = ?")
        params.append(year)
    if author is not None:
        conditions.append(
            "EXISTS ("
            "    SELECT 1 FROM book_authors ba "
            "    JOIN authors a ON a.author_id = ba.author_id "
            "    WHERE ba.book_id = b.book_id AND a.name LIKE ? ESCAPE '\\'"
            ")"
        )
        params.append(_like_pattern(author))
    if available is not None:
        conditions.append(("NOT " + _ON_LOAN) if available else _ON_LOAN)
    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    
    with connect() as conn:
        return _select_books(conn, where, params)


def get_book_by_id(book_id: int) -> dict | None:
    """Return one book with its authors and availability, or None."""
    with connect() as conn:
        books = _select_books(conn, " WHERE b.book_id = ?", (book_id,))
    return books[0] if books else None


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


def list_member_loans(member_id: int, *, active: bool | None = None) -> list[dict]:
    """Return the loans of one member, with the book of each loan 
    and still-open loans first.
    
    Loans that are still out come first, then returned loans. Within each 
    group the newest loan comes first.
    
    Args:
        member_id: the member whose loans to list.
        active: filter by loan status. True gives only loans that have not 
            been returned yet, False only returned loans, and None (the
            default) the whole history.

    Returns:
        A list of dicts with the keys ``loan_id``, ``loan_date``,
        ``due_date``, ``return_date`` (None while the book is out),
        ``overdue`` (True if the book is out and past its due date) and
        ``book``, a dict in the same shape as the items of ``list_books()``.
        The list is empty if the member has no matching loans or does not
        exist.
    """
    conditions = ["l.member_id = ?"]
    if active is not None:
        conditions.append(
            "l.return_date IS NULL" if active else "l.return_date IS NOT NULL"
        )
    with connect() as conn:
        loan_rows = conn.execute(
            "SELECT l.loan_id, l.book_id, l.loan_date, l.due_date, l.return_date, "
            "(l.return_date IS NULL "
            " AND l.due_date < date('now', 'localtime')) AS overdue "
            "FROM loans l WHERE " + " AND ".join(conditions) + " "
            "ORDER BY l.return_date IS NOT NULL, l.loan_date DESC, l.loan_id DESC",
            (member_id,)
        ).fetchall()
        if not loan_rows:
            return []
        book_ids = list({row["book_id"] for row in loan_rows})
        books = _select_books(
            conn, 
            " WHERE b.book_id IN (" + ",".join("?" * len(book_ids)) + ")", 
            book_ids
            )
    by_id = {book["book_id"]: book for book in books}
    loans = []
    for row in loan_rows:
        loan = dict(row)
        loan["book"] = by_id[loan.pop("book_id")]
        loans.append(loan)
    return loans


def borrow_book(member_id: int, book_id: int) -> dict | None:
    """Lend a book to a member and return the new loan, or None.

    The loan date is today and the due date is ``LOAN_DAYS`` later. The
    caller cannot choose either.

    Returns:
        The loan as a dict in the shape of the items of
        ``list_member_loans()``, or None if the book does not exist.

    Raises:
        RuleViolation: if the member is anonymised or the book is already
            on loan.
    
    Authors:
        Mohana Muruganandham, Victor Sago.
    """
    today = date.today()
    due = today + timedelta(days=LOAN_DAYS)
    with connect() as conn:
        # Take the write lock first, so that checking availability and
        # inserting the loan cannot be interleaved with another request.
        conn.execute("BEGIN IMMEDIATE")
        member = conn.execute(
            "SELECT 1 FROM members WHERE member_id = ? AND anonymised_at IS NULL",
            (member_id,)
        ).fetchone()
        if member is None:
            raise RuleViolation("This member account cannot borrow books.")
        books = _select_books(conn, " WHERE b.book_id = ?", (book_id,))
        if not books:
            return None
        book = books[0]
        if not book["available"]:
            raise RuleViolation("This book is already on loan.")
        cursor = conn.execute(
            "INSERT INTO loans (member_id, book_id, loan_date, due_date) "
            "VALUES (?, ?, ?, ?)",
            (member_id, book_id, today.isoformat(), due.isoformat())
        )
        loan_id = cursor.lastrowid
        if loan_id is None:
            raise RuntimeError("Inserting the loan did not create a row.")
    book["available"] = False
    return {
        "loan_id": loan_id,
        "loan_date": today.isoformat(),
        "due_date": due.isoformat(),
        "return_date": None,
        "overdue": False,
        "book": book,
    }


def return_book(member_id: int, loan_id: int) -> dict | None:
    """Mark one of the member's loans as returned today and return it.

    Returns:
        The loan as a dict in the shape of the items of
        ``list_member_loans()``, or None if there is no such loan or it
        belongs to another member.

    Raises:
        RuleViolation: if the loan has already been returned.
    """
    today = date.today().isoformat()
    with connect() as conn:
        # Take the write lock first, so two requests cannot both return
        # the same loan.
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT loan_id, book_id, loan_date, due_date, return_date "
            "FROM loans WHERE loan_id = ? AND member_id = ?",
            (loan_id, member_id)
        ).fetchone()
        if row is None:
            return None
        if row["return_date"] is not None:
            raise RuleViolation("This book has already been returned.")
        conn.execute(
            "UPDATE loans SET return_date = ? WHERE loan_id = ?",
            (today, loan_id)
        )
        # Read the book after the update, so ``available`` is already True.
        book = _select_books(conn, " WHERE b.book_id = ?", (row["book_id"],))[0]
    return {
        "loan_id": row["loan_id"],
        "loan_date": row["loan_date"],
        "due_date": row["due_date"],
        "return_date": today,
        "overdue": False,
        "book": book,
    }


def get_member_data(member_id: int) -> dict | None:
    """Return everything stored about a member, with their loans, or None."""
    with connect() as conn:
        row = conn.execute(
            "SELECT member_id, card_number, name, email, phone, "
            "joined_at, anonymised_at FROM members WHERE member_id = ?",
            (member_id,)
        ).fetchone()
    if row is None:
        return None
    return {"member": dict(row), "loans": list_member_loans(member_id)}


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
        params.append(_like_pattern(name))
    with connect() as conn:
        rows = conn.execute(
            "SELECT " + _MEMBER_COLUMNS + " FROM members "
            "WHERE " + " AND ".join(conditions) + " "
            "ORDER BY name COLLATE NOCASE, member_id",
            params
        ).fetchall()
    return [dict(row) for row in rows]


def _select_member(conn, member_id: int) -> dict | None:
    """Return one member by ID, or None. Callers pass an open connection."""
    row = conn.execute(
        "SELECT " + _MEMBER_COLUMNS + " FROM members WHERE member_id = ?", (member_id,)
    ).fetchone()
    return dict(row) if row is not None else None


def get_member_by_id(member_id: int) -> dict | None:
    """Return one member by ID, or None if there is no such ID."""
    with connect() as conn:
        return _select_member(conn, member_id)


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
