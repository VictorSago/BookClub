
from typing import Annotated

from fastapi import FastAPI, Query, Depends, HTTPException

import database
from auth import get_current_member
from models import BookOut, WhoAmIOut, LoanOut, MyDataOut


app = FastAPI(title="Book Club Library")


@app.get("/books", response_model=list[BookOut])
def get_books(
    title: Annotated[str | None, Query(description="Title contains this text")] = None,
    year: Annotated[int | None, Query(description="First publication year")] = None,
    author: Annotated[str | None, Query(description="An author's name contains this text")] = None
    ):
    return database.list_books(title=title, year=year, author=author)


@app.get("/whoami", response_model=WhoAmIOut)
def whoami(member: Annotated[dict, Depends(get_current_member)]):
    return member


@app.get("/me/loans", response_model=list[LoanOut])
def get_my_loans(
    member: Annotated[dict, Depends(get_current_member)], 
    active: Annotated[
        bool | None, 
        Query(description="true: not yet returned; false: returned; omit: all")
        ] = None
    ):
    return database.list_member_loans(member["member_id"], active=active)


@app.get("/me/data", response_model=MyDataOut)
def get_my_data(member: Annotated[dict, Depends(get_current_member)]):
    data = database.get_member_data(member["member_id"])
    if data is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return data
