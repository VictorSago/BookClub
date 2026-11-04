
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

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


class BookImportCreate(BaseModel):
    isbn: str


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
    anonymised_at: str | None = None


class MemberDataOut(MemberOut):
    card_number: str


class MyDataOut(BaseModel):
    member: MemberDataOut
    loans: list[LoanOut]


class LoanCreate(BaseModel):
    book_id: int = Field(gt=0)


class MemberCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: str | None = Field(default=None, min_length=1, max_length=30)


class MemberUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, min_length=1, max_length=30)

    @model_validator(mode="after")
    def check_fields_sent(self):
        if not self.model_fields_set:
            raise ValueError("Send at least one field to change.")
        for field in ("name", "email"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        return self
