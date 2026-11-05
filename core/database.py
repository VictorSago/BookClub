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

The queries about members are in ``core/db_members.py`` and the queries
about loans in ``core/db_loans.py``. Both use ``connect()`` and ``RuleViolation``
from this module.
"""

import os
import sqlite3
from collections import defaultdict
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

# Connection and errors

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB = BASE_DIR / "library.db"

DB_PATH = Path(os.environ.get("LIBRARY_DB", DEFAULT_DB))


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


# Helpers shared by all query modules

def like_pattern(text: str) -> str:
    """Turn user text into a "contains" pattern for LIKE, with the
    wildcard characters % and _ treated as ordinary characters."""
    escaped = text.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
    return "%" + escaped + "%"


def in_list(values) -> str:
    """Return the SQL text "(?,?,?)" with one placeholder for each value."""
    return "(" + ",".join("?" * len(values)) + ")"


# Books

_ON_LOAN = (
    "EXISTS (SELECT 1 FROM loans l "
    "WHERE l.book_id = b.book_id AND l.return_date IS NULL)"
)


def select_books(conn, where: str = "", params=()) -> list[dict]:
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
        params.append(like_pattern(title))
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
        params.append(like_pattern(author))
    if available is not None:
        conditions.append(("NOT " + _ON_LOAN) if available else _ON_LOAN)
    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    
    with connect() as conn:
        return select_books(conn, where, params)


def get_book_by_id(book_id: int) -> dict | None:
    """Return one book with its authors and availability, or None."""
    with connect() as conn:
        books = select_books(conn, " WHERE b.book_id = ?", (book_id,))
    return books[0] if books else None


def find_book_by_isbn(isbn: str) -> dict | None:
    """Return a single book by its ISBN from the local database, or None.
    
    Reuses select_books to automatically attach author names and calculate
    availability status.
    """
    with connect() as conn:
        books = select_books(conn, " WHERE b.isbn = ?", (isbn,))
        return books[0] if books else None


def create_book(
    *,
    title: str,
    first_publish_year: int | None = None,
    open_library_key: str | None = None,
    isbn: str | None = None,
    authors: list[str] | None = None,
) -> dict:
    """Insert a new book and its authors into the database.

    Args:
        title: Book title (cannot be empty).
        first_publish_year: Publication year (between 1400 and 2200, or None).
        open_library_key: Work or edition key from Open Library (or None).
        isbn: Clean ISBN-10 or ISBN-13 without hyphens (or None).
        authors: List of author names to associate with this book.

    Returns:
        A dictionary representation of the newly created book matching BookOut.
    """
    # Normalize empty strings to None to satisfy schema UNIQUE and CHECK constraints
    clean_isbn = isbn.strip() if isbn and isbn.strip() else None
    clean_ol_key = (
        open_library_key.strip()
        if open_library_key and open_library_key.strip()
        else None
    )

    with connect() as conn:
        # 1. Insert the book record into the books table
        cursor = conn.execute(
            "INSERT INTO books (title, first_publish_year, isbn, open_library_key) "
            "VALUES (?, ?, ?, ?)",
            (title.strip(), first_publish_year, clean_isbn, clean_ol_key),
        )
        book_id = cursor.lastrowid

        # 2. Link authors via the junction table book_authors
        for author_name in authors or []:
            name = author_name.strip()
            if not name:
                continue

            # Case-insensitive check to prevent duplicate author records
            author_row = conn.execute(
                "SELECT author_id FROM authors WHERE name = ? COLLATE NOCASE",
                (name,),
            ).fetchone()

            if author_row:
                author_id = author_row["author_id"]
            else:
                author_cursor = conn.execute(
                    "INSERT INTO authors (name) VALUES (?)",
                    (name,),
                )
                author_id = author_cursor.lastrowid

            # Create relation in book_authors junction table
            conn.execute(
                "INSERT OR IGNORE INTO book_authors (book_id, author_id) VALUES (?, ?)",
                (book_id, author_id),
            )

        # 3. Retrieve and return the populated book dictionary
        return select_books(conn, " WHERE b.book_id = ?", (book_id,))[0]


# Statistics on books

def most_borrowed_books(*, limit: int) -> list[dict]:
    """Return the most borrowed books, the most borrowed first.

    Every loan counts, returned or not. Books that were never borrowed are
    left out, and books with the same count are ordered by title.

    Args:
        limit: the largest number of books to return.

    Returns:
        A list of dicts in the shape of the items of ``list_books()``, each
        with one more key, ``loan_count``.
    """
    with connect() as conn:
        count_rows = conn.execute(
            "SELECT b.book_id, COUNT(*) AS loan_count "
            "FROM loans l JOIN books b ON b.book_id = l.book_id "
            "GROUP BY b.book_id "
            "ORDER BY loan_count DESC, b.title COLLATE NOCASE "
            "LIMIT ?",
            (limit,)
        ).fetchall()
        if not count_rows:
            return []
        book_ids = [row["book_id"] for row in count_rows]
        books = select_books(
            conn, " WHERE b.book_id IN " + in_list(book_ids), book_ids
        )
    by_id = {book["book_id"]: book for book in books}
    return [
        {**by_id[row["book_id"]], "loan_count": row["loan_count"]}
        for row in count_rows
    ]


def never_borrowed_books() -> list[dict]:
    """Return the books that have never been borrowed, ordered by title, in
    the same shape as ``list_books()``."""
    with connect() as conn:
        return select_books(
            conn,
            " LEFT JOIN loans l ON l.book_id = b.book_id"
            " WHERE l.loan_id IS NULL"
        )
