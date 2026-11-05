
import re
from typing import Annotated

from fastapi import FastAPI, Query, HTTPException, Response, status

from core import database, models, external_api
from core.auth import CurrentMember, CurrentLibrarian


app = FastAPI(title="Book Club Library")


@app.get("/books", response_model=list[models.BookOut])
def get_books(
    title: Annotated[str | None, Query(description="Title contains this text")] = None,
    year: Annotated[int | None, Query(description="First publication year")] = None,
    author: Annotated[str | None, Query(description="An author's name contains this text")] = None,
    available: Annotated[
        bool | None, 
        Query(description="True: only books in the library. False: only books on loan")
        ] = None
    ):
    return database.list_books(title=title, year=year, author=author, available=available)

<<<<<<< HEAD

@app.get("/books/{book_id}", response_model=models.BookOut)
=======
@app.get("/books/{book_id}", response_model=BookOut)
>>>>>>> feature/borrow_ui
def get_book(book_id: int):
    book = database.get_book_by_id(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

<<<<<<< HEAD

@app.get("/books/{book_id}/loans", response_model=list[models.LoanWithMemberOut])
def get_book_loans(
    book_id: int,
    _librarian: CurrentLibrarian,
    active: Annotated[
        bool | None,
        Query(description="true: out now; false: returned; omit: all")
        ] = None
    ):
    loans = database.list_book_loans(book_id, active=active)
    if loans is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return loans


@app.post("/books/import", response_model=models.BookOut, status_code=201)
def import_book(
    payload: models.BookImportCreate,
    librarian: CurrentLibrarian,
    response: Response,
):
    """Import a book by ISBN from Open Library or return existing local copy."""
    # Clean and validate ISBN format
    clean_isbn = re.sub(r"[-\s]", "", payload.isbn.strip())
    if len(clean_isbn) not in (10, 13):
        raise HTTPException(
            status_code=400,
            detail="ISBN must be 10 or 13 characters long without hyphens.",
        )
    # Check local SQLite database first
    existing_book = database.find_book_by_isbn(clean_isbn)
    if existing_book:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Book with ISBN {clean_isbn} already exists in the library catalog."
        )

    # Query Open Library API
    try:
        results = external_api.search_books(isbn=clean_isbn, limit=1)
    except external_api.OpenLibraryError as error:
        raise HTTPException(status_code=502, detail=str(error))

    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with ISBN {clean_isbn} not found in Open Library.",
        )

    book_data = results[0]

    # Save into SQLite and return created record
    return database.create_book(
        title=book_data["title"],
        first_publish_year=book_data.get("first_publish_year"),
        open_library_key=book_data.get("open_library_key"),
        isbn=clean_isbn,
        authors=book_data.get("authors", []),
    )


@app.get("/whoami", response_model=models.WhoAmIOut)
def whoami(member: CurrentMember):
    return member


@app.get("/me/loans", response_model=list[models.LoanOut])
=======
@app.get("/whoami", response_model=WhoAmIOut)
def whoami(member: CurrentMember):
    return member

@app.get("/me/loans", response_model=list[LoanOut])
>>>>>>> feature/borrow_ui
def get_my_loans(
    member: CurrentMember, 
    active: Annotated[
        bool | None, 
        Query(description="true: not yet returned; false: returned; omit: all")
        ] = None
    ):
    return database.list_member_loans(member["member_id"], active=active)


@app.post("/me/loans", response_model=models.LoanOut, status_code=201)
def create_my_loan(body: models.LoanCreate, member: CurrentMember):
    try:
        loan = database.borrow_book(member["member_id"], body.book_id)
    except database.RuleViolation as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if loan is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return loan


@app.post("/me/loans/{loan_id}/return", response_model=models.LoanOut)
def return_my_loan(loan_id: int, member: CurrentMember):
    try:
        loan = database.return_book(member["member_id"], loan_id)
    except database.RuleViolation as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if loan is None:
        raise HTTPException(status_code=404, detail="Loan not found")
    return loan


@app.get("/me/data", response_model=models.MyDataOut)
def get_my_data(member: CurrentMember):
    data = database.get_member_data(member["member_id"])
    if data is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return data


@app.delete("/me", status_code=204)
def delete_me(member: CurrentMember):
    if member["role"] == "librarian":
        raise HTTPException(
            status_code=403, detail="Librarian accounts cannot remove themselves"
        )
    try:
        removed = database.delete_or_anonymise_member(member["member_id"])
    except database.RuleViolation as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if removed is None:
        raise HTTPException(status_code=404, detail="Member not found")


@app.get("/members", response_model=list[models.MemberOut])
def get_members(
    _librarian: CurrentLibrarian, 
    name: Annotated[str | None, Query(description="Name contains this text")] = None
    ):
    return database.list_members(name=name)


@app.get("/members/{member_id}", response_model=models.MemberDetailOut)
def get_member(member_id: int, _librarian: CurrentLibrarian):
    member = database.get_member_with_loans(member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return member


@app.post("/members", response_model=models.MemberDataOut, status_code=201)
def create_member(body: models.MemberCreate, _librarian: CurrentLibrarian):
    try:
        return database.create_member(body.name, body.email, phone=body.phone)
    except database.RuleViolation as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


def _apply_member_update(member_id: int, changes: dict) -> dict:
    try:
        member = database.update_member(member_id, changes)
    except database.RuleViolation as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return member


@app.put("/members/{member_id}", response_model=models.MemberOut)
def replace_member(member_id: int, body: models.MemberCreate, _librarian: CurrentLibrarian):
    return _apply_member_update(member_id, body.model_dump())


@app.patch("/members/{member_id}", response_model=models.MemberOut)
def patch_member(member_id: int, body: models.MemberUpdate, _librarian: CurrentLibrarian):
    return _apply_member_update(member_id, body.model_dump(exclude_unset=True))


@app.delete("/members/{member_id}", status_code=204)
def delete_member(member_id: int, _librarian: CurrentLibrarian):
    try:
        member = database.delete_member(member_id)
    except database.RuleViolation as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")


@app.post("/members/{member_id}/anonymise", response_model=models.MemberOut)
def anonymise_member(member_id: int, _librarian: CurrentLibrarian):
    try:
        member = database.anonymise_member(member_id)
    except database.RuleViolation as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return member


@app.get("/loans/overdue", response_model=list[models.OverdueLoanOut])
def get_overdue_loans(_librarian: CurrentLibrarian):
    return database.list_overdue_loans()


@app.get("/stats/most-borrowed", response_model=list[models.MostBorrowedOut])
def get_most_borrowed_books(
    _librarian: CurrentLibrarian,
    limit: Annotated[
        int, Query(ge=1, le=50, description="The most books to return")
    ] = 5,
):
    return database.most_borrowed_books(limit=limit)


@app.get("/stats/never-borrowed", response_model=list[models.BookOut])
def get_never_borrowed_books(_librarian: CurrentLibrarian):
    return database.never_borrowed_books()
