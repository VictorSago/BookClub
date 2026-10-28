"""Build library.db from schema.sql and fill it with test data.

Usage:
    python seed.py

If library.db already exists, delete it first and run this script again.
"""

import sys
from pathlib import Path
from datetime import date, datetime, timedelta
import string
import secrets
import sqlite3
from database import DB_PATH, connect


BASE_DIR = Path(__file__).parent
SCHEMA_PATH = BASE_DIR / "schema.sql"

CARD_ALPHABET = string.ascii_uppercase + string.digits
CARD_LENGTH = 16

LOAN_DAYS = 21  # Keep in sync with the default loan length in the API.
ANONYMISED_NAME = "Anonymised member"

AUTHORS = [
    "J. R. R. Tolkien",
    "Ursula K. Le Guin",
    "Terry Pratchett",
    "Neil Gaiman",
    "Astrid Lindgren",
    "Douglas Adams",
    "Roger Zelazny"
]

# (title, first publish year, ISBN or None, authors)
# The ISBNs are made up for testing and are not real.
BOOKS = [
    ("The Hobbit", 1937, "9780000000011", ["J. R. R. Tolkien"]),
    ("The Fellowship of the Ring", 1954, None, ["J. R. R. Tolkien"]),
    ("A Wizard of Earthsea", 1968, "9780000000028", ["Ursula K. Le Guin"]),
    ("The Dispossessed", 1974, None, ["Ursula K. Le Guin"]),
    ("Guards! Guards!", 1989, None, ["Terry Pratchett"]),
    ("Good Omens", 1990, "9780000000035", ["Terry Pratchett", "Neil Gaiman"]),
    ("Pippi Longstocking", 1945, None, ["Astrid Lindgren"]),
    ("Neverwhere", 1996, None, ["Neil Gaiman"]),
    ("The Hitchhiker's Guide to the Galaxy", 1979, "0330258648", ["Douglas Adams"]),
    ("The Restaurant at the End of the Universe", 1980, "0345391810", ["Douglas Adams"]),
    ("Life, the Universe and Everything", 1982, "0330267388", ["Douglas Adams"]),
    ("So Long, and Thanks for All the Fish", 1984, "0330287001", ["Douglas Adams"]),
    ("Mostly Harmless", 1992, "0330323113", ["Douglas Adams"]),
    ("A Night in the Lonesome October", 1993, "0688125085", ["Roger Zelazny"]),
]

# (name, email, phone). All fake; example.com is reserved for examples.
MEMBERS = [
    ("Alice Andersson", "alice@example.com", "070-000 00 01"),
    ("Bo Berg", "bo@example.com", None),
    ("Cecilia Carlsson", "cecilia@example.com", "070-000 00 03"),
    ("David Dahl", "david@example.com", None),
    ("Arthur Dent", "arthur@example.com", "070-000 00 05"),
    ("Ford Prefect", "ford@example.com", None),
    ("Zaphod Beeblebrox", "zaphod@example.com", None),
]

# (book title, member name, days since loan, days since return or None)
# None means the book is still out. Dates are relative to today, so the
# overdue loan stays overdue whenever the script is run.
LOANS = [
    ("The Hobbit", "Alice Andersson", 60, 45),
    ("The Hobbit", "Bo Berg", 40, 25),
    ("The Hobbit", "David Dahl", 10, None),
    ("Good Omens", "Alice Andersson", 30, None),  # overdue
    ("A Wizard of Earthsea", "Cecilia Carlsson", 5, None),
    ("The Dispossessed", "Bo Berg", 20, 10),
    ("Guards! Guards!", ANONYMISED_NAME, 90, 80),
]


def new_card_number() -> str:
    """Return a random card number made of capital letters and digits."""
    return "".join(secrets.choice(CARD_ALPHABET) for _ in range(CARD_LENGTH))


def create_tables(conn: sqlite3.Connection) -> None:
    """Create all tables and indexes from schema.sql."""
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


def insert_authors(conn: sqlite3.Connection) -> dict[str, int]:
    """Insert the authors and return a map from name to author_id."""
    author_ids = {}
    for name in AUTHORS:
        cursor = conn.execute("INSERT INTO authors (name) VALUES (?)", (name,))
        author_ids[name] = cursor.lastrowid
    return author_ids


def insert_books(
    conn: sqlite3.Connection, author_ids: dict[str, int]
    ) -> dict[str, int]:
    """Insert the books and their authors. Return a map from title to book_id."""
    book_ids = {}
    for title, year, isbn, authors in BOOKS:
        cursor = conn.execute(
            "INSERT INTO books (title, first_publish_year, isbn) "
            "VALUES (?, ?, ?)",
            (title, year, isbn)
        )
        book_id = cursor.lastrowid
        book_ids[title] = book_id
        for author in authors:
            conn.execute(
                "INSERT INTO book_authors (book_id, author_id) VALUES (?, ?)",
                (book_id, author_ids[author])
            )
    return book_ids


def insert_member(
    conn: sqlite3.Connection, 
    name: str, email: str, 
    phone: str | None, 
    anonymised_at: str | None = None
    ) -> tuple[int, str]:
    """Insert one member with a random card number.

    Return the new member_id and the card number.
    """
    card_number = new_card_number()
    cursor = conn.execute(
        "INSERT INTO members "
        "(card_number, name, email, phone, anonymised_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (card_number, name, email, phone, anonymised_at),
    )
    member_id = cursor.lastrowid
    if member_id is None:
        raise RuntimeError("Inserting the member did not create a row.")
    return member_id, card_number


def insert_members(conn: sqlite3.Connection,) -> tuple[dict[str, int], dict[str, str]]:
    """Insert the test members, including one anonymised member.

    Return a map from name to member_id and a map from name to card number.
    """
    member_ids = {}
    cards = {}
    for name, email, phone in MEMBERS:
        member_ids[name], cards[name] = insert_member(conn, name, email, phone)

    anonymised_at = datetime.now().isoformat(sep=" ", timespec="seconds")
    email = f"anonymised-{secrets.token_hex(4)}@invalid.invalid"
    member_ids[ANONYMISED_NAME], cards[ANONYMISED_NAME] = insert_member(
        conn, ANONYMISED_NAME, email, None, anonymised_at
    )
    return member_ids, cards


def insert_loans(
    conn: sqlite3.Connection, book_ids: dict[str, int], member_ids: dict[str, int]
    ) -> None:
    """Insert the test loans, with dates counted back from today."""
    today = date.today()
    for title, member, days_since_loan, days_since_return in LOANS:
        loan_date = today - timedelta(days=days_since_loan)
        due_date = loan_date + timedelta(days=LOAN_DAYS)
        return_date = None
        if days_since_return is not None:
            return_date = (today - timedelta(days=days_since_return)).isoformat()
        conn.execute(
            "INSERT INTO loans (book_id, member_id, loan_date, due_date, "
            "return_date) VALUES (?, ?, ?, ?, ?)",
            (
                book_ids[title],
                member_ids[member],
                loan_date.isoformat(),
                due_date.isoformat(),
                return_date
            ),
        )


def print_summary(cards: dict[str, str]) -> None:
    """Tell the developer what was created and how to log in as a member."""
    print(f"Created {DB_PATH.name} with test data.")
    print("Test member cards (random, different on every run):")
    for name, card in cards.items():
        if name != ANONYMISED_NAME:
            print(f"  {name}: {card}")


def main() -> None:
    """Build and fill the database, or stop if it already exists."""
    if DB_PATH.exists():
        sys.exit(f"{DB_PATH.name} already exists. Delete it and run again.")

    conn = connect()
    try:
        with connect(create=True) as conn:
            create_tables(conn)
            author_ids = insert_authors(conn)
            book_ids = insert_books(conn, author_ids)
            member_ids, cards = insert_members(conn)
            insert_loans(conn, book_ids, member_ids)
    except sqlite3.Error:
        DB_PATH.unlink()
        raise
    print_summary(cards)


if __name__ == "__main__":
    main()
