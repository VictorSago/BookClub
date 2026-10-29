
from typing import Annotated

from fastapi import FastAPI, Query

import database
from models import BookOut

app = FastAPI(title="Book Club Library")


@app.get("/books", response_model=list[BookOut])
def get_books(
    title: Annotated[str | None, Query(description="Title contains this text")] = None,
    year: Annotated[int | None, Query(description="First publication year")] = None,
    author: Annotated[str | None, Query(description="An author's name contains this text")] = None
    ):
    return database.list_books(title=title, year=year, author=author)
