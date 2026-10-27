"""Build library.db from schema.sql and fill it with test data.

Usage:
    python seed.py

If library.db already exists, delete it first and run this script again.
"""

import sys
import secrets
from pathlib import Path
from datetime import date, datetime, timedelta
import sqlite3
from database import DB_PATH, connect, new_card_number


BASE_DIR = Path(__file__).parent
SCHEMA_PATH = BASE_DIR / "schema.sql"

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
    ("A Night in the Lonesome October", 1993, "0688125085", ["Roger Zelazny"])
]

# (name, email, phone, card number, joined). All fake test data.
MEMBERS = [
    ("Alice Primary", "alice@example.com", "070-000 00 01", "DEMOCARD00000001", "2025-09-14"),
    ("Bob Companion", "bob@example.com", None, "DEMOCARD00000002", "2025-11-03"),
    ("Cecilia Tertison", "cecilia@example.com", "070-000 00 03", "DEMOCARD00000003", "2026-01-20"),
    ("David Friendly", "david@example.com", None, "DEMOCARD00000004", "2026-03-08"),
    ("Eve Mallory", "eve.m@example.com", None, "DEMOCARD00000005", "2026-03-08"),
    ("Arthur Dent", "arthur@example.com", "070-000 00 05", "DEMOCARD00000006", "2026-04-02"),
    ("Ford Prefect", "ford@example.com", None, "DEMOCARD00000007", "2026-05-17"),
    ("Zaphod Beeblebrox", "zaphod@example.com", "070-000 00 07", "DEMOCARD00000008", "2026-06-09"),
    ("Random Frequent Flyer Dent", "random.ffd@example.com", None, "DEMOCARD00000009", "2026-08-09")
]

# (book title, member name, days since loan, days since return or None)
# None means the book is still out. Dates are relative to today, so the
# overdue loan stays overdue whenever the script is run.
LOANS = [
    ("The Hobbit", "Alice Primary", 60, 45),
    ("Good Omens", "Alice Primary", 30, None),  # overdue
    ("The Hobbit", "Bob Companion", 40, 25),
    ("The Dispossessed", "Bob Companion", 20, 10),
    ("The Dispossessed", "Cecilia Tertison", 70, 40),  # returned late
    ("A Wizard of Earthsea", "Cecilia Tertison", 5, None),
    ("Guards! Guards!", "David Friendly", 35, 28),
    ("The Hobbit", "David Friendly", 10, None),
    ("The Hitchhiker's Guide to the Galaxy", "Arthur Dent", 120, 105),
    ("The Restaurant at the End of the Universe", "Arthur Dent", 100, 88),
    ("Life, the Universe and Everything", "Arthur Dent", 85, 70),
    ("Neverwhere", "Bob Companion", 25, None),  # overdue
    ("The Hobbit", "Ford Prefect", 150, 135),
    ("The Hitchhiker's Guide to the Galaxy", "Ford Prefect", 95, 80),
    ("A Night in the Lonesome October", "Ford Prefect", 20, None),  # due tomorrow
    ("Pippi Longstocking", "Random Frequent Flyer Dent", 66, 55),
    ("The Hitchhiker's Guide to the Galaxy", "Random Frequent Flyer Dent", 50, 38),
    ("A Wizard of Earthsea", "Random Frequent Flyer Dent", 30, 20),
    ("Guards! Guards!", ANONYMISED_NAME, 90, 80),
]


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
    name: str, 
    email: str, 
    phone: str | None, 
    card_number: str, 
    joined_at: str, 
    *,
    anonymised_at: str | None = None
    ) -> tuple[int, str]:
    """Insert one member.

    Return the new member_id and the card number.
    """
    #card_number = new_card_number()
    cursor = conn.execute(
        "INSERT INTO members "
        "(card_number, name, email, phone, joined_at, anonymised_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (card_number, name, email, phone, joined_at, anonymised_at)
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
    for name, email, phone, card, joined_at in MEMBERS:
        member_ids[name], cards[name] = insert_member(conn, name, email, phone, card, joined_at)

    anonymised_at = (date.today() - timedelta(days=30)).isoformat()
    email = f"anonymised-{secrets.token_hex(4)}@invalid.invalid"
    member_ids[ANONYMISED_NAME], cards[ANONYMISED_NAME] = insert_member(
        conn, 
        ANONYMISED_NAME, 
        email, 
        None, 
        new_card_number(),
        "2025-06-01",
        anonymised_at=anonymised_at)
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
    print("Test member cards:")
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
