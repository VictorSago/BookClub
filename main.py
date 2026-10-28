
from fastapi import FastAPI

import database
from models import BookOut

app = FastAPI(title="Book Club Library")


@app.get("/books", response_model=list[BookOut])
def get_books():
    return database.list_books()
