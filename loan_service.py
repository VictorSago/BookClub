"""Borrowing business logic for the BookClub library.

This module does not collect CLI input or authenticate users. The FastAPI layer
must authenticate the member and pass the authenticated member_id to borrow_book.

Only books owned by the local library can be borrowed. Open Library search is
handled separately by external_api.py; it cannot establish local availability.

Dates use ISO 8601 format (YYYY-MM-DD). Loans start today, and the default due
 date is 21 days later. A client may supply an explicit due date after today;
confirm with the team whether to restrict this to the default loan period.
"""

import sqlite3
from datetime import date, timedelta

from database import connect, list_books

DEFAULT_LOAN_DAYS = 21


class LoanError(Exception):
    """Base class for expected borrowing business-rule failures."""


class BookNotFoundError(LoanError):
    """The requested book does not exist in the local library."""


class BookUnavailableError(LoanError):
    """The requested physical book already has an active loan."""


class InvalidLoanRequestError(LoanError):
    """The borrowing request contains invalid information."""


def _positive_id(value: int, label: str) -> None:
    if type(value) is not int or value <= 0:
        raise InvalidLoanRequestError(f"{label} must be a positive integer.")


def find_books(title: str) -> list[dict]:
    """Find locally owned books by title, including availability."""
    if not isinstance(title, str) or not title.strip():
        raise InvalidLoanRequestError("Enter a book title.")
    return list_books(title=title.strip())


def check_book_available(book_id: int) -> dict:
    """Return local book information and its current availability.

    This is informational: borrow_book checks again inside a write transaction.
    """
    _positive_id(book_id, "Book ID")
    with connect() as conn:
        book = conn.execute(
            "SELECT book_id, title FROM books WHERE book_id = ?", (book_id,)
        ).fetchone()
        if book is None:
            raise BookNotFoundError(f"Book {book_id} was not found in our library.")
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
    """Require canonical ISO dates, loan starting today, and due date after today.

    The client handles user input and converts dates to YYYY-MM-DD before calling
    this service.
    """
    try:
        start = date.fromisoformat(loan_date)
        due = date.fromisoformat(due_date)
    except (TypeError, ValueError) as exc:
        raise InvalidLoanRequestError("Dates must use YYYY-MM-DD format.") from exc
    if start.isoformat() != loan_date or due.isoformat() != due_date:
        raise InvalidLoanRequestError("Dates must use YYYY-MM-DD format.")
    if start != date.today():
        raise InvalidLoanRequestError("Borrowing must start today.")
    if due <= start:
        raise InvalidLoanRequestError("Due date must be after the loan date.")
    return start.isoformat(), due.isoformat()


def borrow_book(
    member_id: int,
    book_id: int,
    *,
    loan_date: str | None = None,
    due_date: str | None = None,
) -> dict:
    """Create a loan for an authenticated member and a locally available book.

    Returns loan_id, member_id, book_id, loan_date and due_date.
    Raises LoanError for expected business-rule failures. The API layer must
    authenticate and authorize the member before calling this function.
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
        # Lock writes before checking availability to prevent racing borrowers.
        conn.execute("BEGIN IMMEDIATE")

        member = conn.execute(
            "SELECT member_id, anonymised_at FROM members WHERE member_id = ?",
            (member_id,),
        ).fetchone()
        if member is None or member["anonymised_at"] is not None:
            raise InvalidLoanRequestError("Member is not eligible to borrow books.")

        book = conn.execute(
            "SELECT book_id FROM books WHERE book_id = ?", (book_id,)
        ).fetchone()
        if book is None:
            raise BookNotFoundError(f"Book {book_id} was not found in our library.")

        active = conn.execute(
            "SELECT 1 FROM loans WHERE book_id = ? AND return_date IS NULL",
            (book_id,),
        ).fetchone()
        if active is not None:
            raise BookUnavailableError(f"Book {book_id} is currently on loan.")

        try:
            cursor = conn.execute(
                "INSERT INTO loans (member_id, book_id, loan_date, due_date) "
                "VALUES (?, ?, ?, ?)",
                (member_id, book_id, loan_date, due_date),
            )
        except sqlite3.IntegrityError as exc:
            # The schema's active-loan unique index is a final safeguard.
            if "UNIQUE constraint failed: loans.book_id" in str(exc):
                raise BookUnavailableError(
                    f"Book {book_id} is currently on loan."
                ) from exc
            raise InvalidLoanRequestError(
                "The loan could not be saved because it violates a database rule."
            ) from exc

        return {
            "loan_id": cursor.lastrowid,
            "member_id": member_id,
            "book_id": book_id,
            "loan_date": loan_date,
            "due_date": due_date,
        }