
from typing import Annotated

from fastapi import FastAPI, Query, HTTPException

from core import database
from core.auth import CurrentMember, CurrentLibrarian
from core.models import (
    BookOut, LoanOut, MemberCreate, MemberDataOut, MemberOut, MemberUpdate,
    MyDataOut, WhoAmIOut, LoanCreate
    )


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


@app.post("/me/loans/{loan_id}/return", response_model=LoanOut)
def return_my_loan(loan_id: int, member: CurrentMember):
    try:
        loan = database.return_book(member["member_id"], loan_id)
    except database.RuleViolation as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if loan is None:
        raise HTTPException(status_code=404, detail="Loan not found")
    return loan


@app.get("/me/data", response_model=MyDataOut)
def get_my_data(member: CurrentMember):
    data = database.get_member_data(member["member_id"])
    if data is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return data


@app.get("/members", response_model=list[MemberOut])
def get_members(
    _librarian: CurrentLibrarian, 
    name: Annotated[str | None, Query(description="Name contains this text")] = None
    ):
    return database.list_members(name=name)


@app.get("/members/{member_id}", response_model=MemberOut)
def get_member(member_id: int, _librarian: CurrentLibrarian):
    member = database.get_member_by_id(member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return member


@app.post("/members", response_model=MemberDataOut, status_code=201)
def create_member(body: MemberCreate, _librarian: CurrentLibrarian):
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


@app.put("/members/{member_id}", response_model=MemberOut)
def replace_member(member_id: int, body: MemberCreate, _librarian: CurrentLibrarian):
    return _apply_member_update(member_id, body.model_dump())


@app.patch("/members/{member_id}", response_model=MemberOut)
def patch_member(member_id: int, body: MemberUpdate, _librarian: CurrentLibrarian):
    return _apply_member_update(member_id, body.model_dump(exclude_unset=True))


@app.delete("/members/{member_id}", status_code=204)
def delete_member(member_id: int, _librarian: CurrentLibrarian):
    try:
        member = database.delete_member(member_id)
    except database.RuleViolation as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")


@app.post("/members/{member_id}/anonymise", response_model=MemberOut)
def anonymise_member(member_id: int, _librarian: CurrentLibrarian):
    try:
        member = database.anonymise_member(member_id)
    except database.RuleViolation as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return member
