
from typing import Annotated

from fastapi import FastAPI, Query, HTTPException

from core import database
from auth import CurrentMember, CurrentLibrarian
from core.models import BookOut, LoanOut, MyDataOut, WhoAmIOut, LoanCreate


app = FastAPI(title="Book Club Library")


@app.get("/books", response_model=list[BookOut])
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


@app.get("/books/{book_id}", response_model=BookOut)
def get_book(book_id: int):
    book = database.get_book_by_id(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@app.get("/whoami", response_model=WhoAmIOut)
def whoami(member: CurrentMember):
    return member


@app.get("/me/loans", response_model=list[LoanOut])
def get_my_loans(
    member: CurrentMember, 
    active: Annotated[
        bool | None, 
        Query(description="true: not yet returned; false: returned; omit: all")
        ] = None
    ):
    return database.list_member_loans(member["member_id"], active=active)


@app.post("/me/loans", response_model=LoanOut, status_code=201)
def create_my_loan(body: LoanCreate, member: CurrentMember):
    try:
        loan = database.borrow_book(member["member_id"], body.book_id)
    except database.RuleViolation as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if loan is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return loan


@app.get("/me/data", response_model=MyDataOut)
def get_my_data(member: CurrentMember):
    data = database.get_member_data(member["member_id"])
    if data is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return data
