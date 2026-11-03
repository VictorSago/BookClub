
from pydantic import BaseModel, Field

from typing import Literal


class BookOut(BaseModel):
    book_id: int
    title: str
    first_publish_year: int | None = None
    isbn: str | None = None
    open_library_key: str | None = None
    added_at: str
    authors: list[str]
    available: bool


class WhoAmIOut(BaseModel):
    role: Literal["member", "librarian"]
    member_id: int
    name: str


class LoanOut(BaseModel):
    loan_id: int
    loan_date: str
    due_date: str
    return_date: str | None = None
    overdue: bool
    book: BookOut


class MemberOut(BaseModel):
    member_id: int
    name: str
    email: str
    phone: str | None = None
    joined_at: str


class MemberDataOut(MemberOut):
    card_number: str
    anonymised_at: str | None = None


class MyDataOut(BaseModel):
    member: MemberDataOut
    loans: list[LoanOut]


class LoanCreate(BaseModel):
    book_id: int = Field(gt=0)
