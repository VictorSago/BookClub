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
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB = BASE_DIR / "library.db"

DB_PATH = Path(os.environ.get("LIBRARY_DB", DEFAULT_DB))

CARD_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ1234567890"
CARD_LENGTH = 10


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
