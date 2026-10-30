
from pydantic import BaseModel

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
