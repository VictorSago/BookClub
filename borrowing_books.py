"""Borrowing business logic for the BookClub library.

The FastAPI layer authenticates members and passes the authenticated member ID.
The client asks users to confirm a loan BEFORE calling the borrowing endpoint.
Only locally owned books can be borrowed; Open Library search is separate.

Dates are canonical ISO strings (YYYY-MM-DD). Loans begin today. The default
loan period is 21 days; custom future due dates are allowed until the team
agrees on a stricter policy.
"""

import sqlite3
from datetime import date, timedelta

from database import connect, list_books

DEFAULT_LOAN_DAYS = 21

def _positive_id(value: int, label: str) -> None:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{label} must be a positive integer.")


def find_books(title: str) -> list[dict]:
    """Search locally owned books; results include their availability."""
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Enter a book title.")
    return list_books(title=title.strip())


def check_book_available(book_id: int) -> dict:
    """Return book details and availability (informational only).

    Availability can change after this read, so borrow_book checks it again
    inside a write transaction.
    """
    _positive_id(book_id, "Book ID")
    with connect() as conn:
        book = conn.execute(
            "SELECT book_id, title FROM books WHERE book_id = ?", (book_id,)
        ).fetchone()
        if book is None:
            raise LookupError(f"Book {book_id} was not found in our library.")
        active = conn.execute(
            "SELECT 1 FROM loans WHERE book_id = ? AND return_date IS NULL",
            (book_id,),
        ).fetchone()
        return {
            "book_id": book["book_id"],
            "title": book["title"],
            "available": active is None,
        }


def validate_loan_dates(loan_date: str, due_date: str) -> tuple[str, str]:
    """Require canonical ISO dates, borrowing today, and a later due date."""
    try:
        start = date.fromisoformat(loan_date)
        due = date.fromisoformat(due_date)
    except (TypeError, ValueError) as exc:
        raise ValueError("Dates must use YYYY-MM-DD format.") from exc

    if start.isoformat() != loan_date or due.isoformat() != due_date:
        raise ValueError("Dates must use YYYY-MM-DD format.")
    if start != date.today():
        raise ValueError("Borrowing must start today.")
    if due <= start:
        raise ValueError("Due date must be after the loan date.")
    return start.isoformat(), due.isoformat()


def borrow_book(
    member_id: int,
    book_id: int,
    *,
    loan_date: str | None = None,
    due_date: str | None = None,
) -> dict:

    """Create a loan after the client has confirmed and the API authenticated.

    Returns a dict with loan_id, member_id, book_id, loan_date and due_date.
    Raises ValueError or LookupError for expected borrowing-rule failures.
    """
    _positive_id(member_id, "Member ID")
    _positive_id(book_id, "Book ID")

    today = date.today()
    if loan_date is None:
        loan_date = today.isoformat()
    if due_date is None:
        due_date = (today + timedelta(days=DEFAULT_LOAN_DAYS)).isoformat()
    loan_date, due_date = validate_loan_dates(loan_date, due_date)

    with connect() as conn:
        # Obtain the SQLite write lock before checking availability.
        conn.execute("BEGIN IMMEDIATE")

        member = conn.execute(
            "SELECT member_id, anonymised_at FROM members WHERE member_id = ?",
            (member_id,),
        ).fetchone()
        if member is None or member["anonymised_at"] is not None:
            raise ValueError("Member is not eligible to borrow books.")

        book = conn.execute(
            "SELECT book_id FROM books WHERE book_id = ?", (book_id,)
        ).fetchone()
        if book is None:
            raise LookupError(f"Book {book_id} was not found in our library.")

        active = conn.execute(
            "SELECT 1 FROM loans WHERE book_id = ? AND return_date IS NULL",
            (book_id,),
        ).fetchone()
        if active is not None:
            raise ValueError(f"Book {book_id} is currently on loan.")

        try:
            cursor = conn.execute(
                "INSERT INTO loans (member_id, book_id, loan_date, due_date) "
                "VALUES (?, ?, ?, ?)",
                (member_id, book_id, loan_date, due_date),
            )
        except sqlite3.IntegrityError as exc:
            if "UNIQUE constraint failed: loans.book_id" in str(exc):
                raise ValueError(
                    f"Book {book_id} is currently on loan."
                ) from exc
            raise ValueError(
                "The loan could not be saved because it violates a database rule."
            ) from exc

        return {
            "loan_id": cursor.lastrowid,
            "member_id": member_id,
            "book_id": book_id,
            "loan_date": loan_date,
            "due_date": due_date,
        }
