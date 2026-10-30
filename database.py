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
    from database import connect

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
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB = BASE_DIR / "library.db"

DB_PATH = Path(os.environ.get("LIBRARY_DB", DEFAULT_DB))

CARD_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ1234567890"
CARD_LENGTH = 12


def new_card_number() -> str:
    """Return a random card number made of capital letters and digits."""
    return "".join(secrets.choice(CARD_ALPHABET) for _ in range(CARD_LENGTH))


def get_connection(create: bool = False) -> sqlite3.Connection:
    """Open the library database and return the connection.

    Foreign keys are enabled and rows can be read like dictionaries. The
    caller is responsible for calling ``commit()`` after changes and
    ``close()`` when done.

    Args:
        create: if True, a missing database file is created (only
            ``seed.py`` should do this). If False, a missing file is an error,
            so a mistake does not silently give you an empty database.

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


def _select_books(conn, where: str = "", params=()) -> list[dict]:
    """Return books with authors and availability.

    The `where` is a fixed SQL fragment on the alias b (or empty), and params
    are its values. Callers pass an open connection.
    """
    book_rows = conn.execute(
        "SELECT b.book_id, b.title, b.first_publish_year, b.isbn, "
        "b.open_library_key, b.added_at, "
        "NOT EXISTS ("
        "    SELECT 1 FROM loans l "
        "    WHERE l.book_id = b.book_id AND l.return_date IS NULL"
        ") AS available "
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
    *, title: str | None = None, year: int | None = None, author: str | None
    ) -> list[dict]:
    """Return books, each with a list of its author names.

    Filters are optional and combine with AND:
        title: the title contains this text (case-insensitive for ASCII).
        year: the first publication year is exactly this.
        author: one of the book's authors has a name containing this text.
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
    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    
    with connect() as conn:
        return _select_books(conn, where, params)


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


def list_member_loans_old(member_id: int) -> list[dict]:
    """Return all loans of one member, still-open loans first."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT l.loan_id, l.book_id, b.title, l.loan_date, l.due_date, "
            "l.return_date, "
            "(l.return_date IS NULL "
            " AND l.due_date < date('now', 'localtime')) AS overdue "
            "FROM loans l JOIN books b ON b.book_id = l.book_id "
            "WHERE l.member_id = ? "
            "ORDER BY l.return_date IS NOT NULL, l.loan_date DESC, l.loan_id DESC",
            (member_id,)
        ).fetchall()
    return [dict(row) for row in rows]

def list_member_loans(member_id: int, *, active: bool | None = None) -> list[dict]:
    """Return all loans of one member, still-open loans first."""
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
