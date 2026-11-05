"""Database access for loans: borrowing, returning, loan
histories and the overdue report.
"""

from datetime import date, timedelta

from core.database import RuleViolation, connect, in_list, select_books
from core.db_members import get_member_by_id, select_members

# Constants and helpers

LOAN_DAYS = 21  # Keep in sync with the default loan length in the API.

_OVERDUE = "(l.return_date IS NULL AND l.due_date < date('now', 'localtime'))"
_LOANS_ORDER = (
    " ORDER BY l.return_date IS NOT NULL, l.loan_date DESC, l.loan_id DESC"
)

def _loan_where(column: str, active: bool | None) -> str:
    """Return the WHERE clause for the loans (alias l) whose ``column`` is
    the value of one ``?``, optionally only the open or only the returned.

    ``column`` is a fixed column name such as "member_id", never user input.
    """
    where = " WHERE l." + column + " = ?"
    if active is not None:
        where += " AND l.return_date IS " + ("NULL" if active else "NOT NULL")
    return where


def _attach_books(conn, loan_rows) -> list[dict]:
    """Turn loan rows into loan dicts, each with its book.

    Every row needs a ``book_id`` column. In the dict it is replaced by
    ``book``, in the same shape as the items of ``list_books()``. Callers
    pass an open connection.
    """
    if not loan_rows:
        return []
    book_ids = list({row["book_id"] for row in loan_rows})
    books = select_books(
        conn, " WHERE b.book_id IN " + in_list(book_ids), book_ids
    )
    by_id = {book["book_id"]: book for book in books}
    loans = []
    for row in loan_rows:
        loan = dict(row)
        loan["book"] = by_id[loan.pop("book_id")]
        loans.append(loan)
    return loans


def _attach_members(conn, loans: list[dict]) -> list[dict]:
    """Give each loan dict its borrower, and return the same list.

    Every loan needs a ``member_id`` key. In the dict it is replaced by
    ``member``, in the shape of ``get_member_by_id()``. Callers pass an open
    connection.
    """
    if not loans:
        return loans
    member_ids = list({loan["member_id"] for loan in loans})
    members = select_members(
        conn, " WHERE member_id IN " + in_list(member_ids), member_ids
    )
    by_id = {member["member_id"]: member for member in members}
    for loan in loans:
        loan["member"] = by_id[loan.pop("member_id")]
    return loans


# Reading loans

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
    with connect() as conn:
        loan_rows = conn.execute(
            "SELECT l.loan_id, l.book_id, l.loan_date, l.due_date, "
            "l.return_date, " + _OVERDUE + " AS overdue "
            "FROM loans l" + _loan_where("member_id", active) + _LOANS_ORDER,
            (member_id,)
        ).fetchall()
        return _attach_books(conn, loan_rows)


def list_book_loans(book_id: int, *, active: bool | None = None) -> list[dict] | None:
    """Return the loans of one book, each with its borrower.

    Loans that are still out come first, then returned loans. Within each
    group the newest loan comes first.

    Args:
        book_id: the book whose loans to list.
        active: True gives only the loan that has not been returned yet
            (who has the book now), False only returned loans, and None
            (the default) the whole history.

    Returns:
        A list of dicts with the keys ``loan_id``, ``loan_date``,
        ``due_date``, ``return_date``, ``overdue`` (as in
        ``list_member_loans()``) and ``member``, a dict in the shape of
        ``get_member_by_id()``. The list is empty if the book has no
        matching loans. The result is None if there is no such book.
    """
    with connect() as conn:
        if conn.execute(
            "SELECT 1 FROM books WHERE book_id = ?", (book_id,)
        ).fetchone() is None:
            return None
        loan_rows = conn.execute(
            "SELECT l.loan_id, l.member_id, l.loan_date, l.due_date, "
            "l.return_date, " + _OVERDUE + " AS overdue "
            "FROM loans l" + _loan_where("book_id", active) + _LOANS_ORDER,
            (book_id,)
        ).fetchall()
        return _attach_members(conn, [dict(row) for row in loan_rows])


def list_overdue_loans() -> list[dict]:
    """Return the loans that are overdue, the one due longest ago first.

    A loan is overdue if it has not been returned and its due date is
    before today.

    Returns:
        A list of dicts with the keys ``loan_id``, ``book_id``, ``title``,
        ``member_id``, ``member_name``, ``email``, ``phone``, ``loan_date``,
        ``due_date`` and ``days_overdue``.
    """
    with connect() as conn:
        rows = conn.execute(
            "SELECT l.loan_id, l.book_id, b.title, l.member_id, "
            "m.name AS member_name, m.email, m.phone, l.loan_date, "
            "l.due_date, CAST(julianday(date('now', 'localtime')) "
            "- julianday(l.due_date) AS INTEGER) AS days_overdue "
            "FROM loans l "
            "JOIN books b ON b.book_id = l.book_id "
            "JOIN members m ON m.member_id = l.member_id "
            "WHERE " + _OVERDUE + " "
            "ORDER BY l.due_date, l.loan_id"
        ).fetchall()
    return [dict(row) for row in rows]


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


def get_member_with_loans(member_id: int) -> dict | None:
    """Return one member, anonymised or not, with their loans, or None.

    The member is in the shape of ``get_member_by_id()``, plus ``loans``:
    the whole loan history, in the shape of ``list_member_loans()``.
    """
    member = get_member_by_id(member_id)
    if member is None:
        return None
    return {**member, "loans": list_member_loans(member_id)}


# Lending and returning


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
        books = select_books(conn, " WHERE b.book_id = ?", (book_id,))
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
        book = select_books(conn, " WHERE b.book_id = ?", (row["book_id"],))[0]
    return {
        "loan_id": row["loan_id"],
        "loan_date": row["loan_date"],
        "due_date": row["due_date"],
        "return_date": today,
        "overdue": False,
        "book": book,
    }
