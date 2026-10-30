
import requests

OPEN_LIBRARY_URL = "https://openlibrary.org/search.json"


class OpenLibraryError(Exception):
    """Raised when Open Library cannot provide results."""


def search_books(
    title: str | None = None,
    author: str | None = None,
    isbn: str | None = None,
    limit: int = 5,
) -> list[dict]:
    """Search Open Library by title, author, or ISBN."""

    # At least one search field must be provided
    if not any(
        isinstance(value, str) and value.strip()
        for value in (title, author, isbn)
    ):
        raise ValueError("Enter a title, author, or ISBN.")

    if type(limit) is not int or limit < 1:
        raise ValueError("Limit must be a positive integer.")

    params = {
        "limit": limit,
        "fields": "key,title,author_name,first_publish_year,isbn",
    }

    if title and title.strip():
        params["title"] = title.strip()

    if author and author.strip():
        params["author"] = author.strip()

    if isbn and isbn.strip():
        params["q"] = f"isbn:{isbn.strip()}"

    try:
        response = requests.get(
            OPEN_LIBRARY_URL,
            params=params,
            timeout=10,
            headers={
                "User-Agent": "BookClubLibrary/1.0 (educational project)"
            },
        )

        response.raise_for_status()
        data = response.json()

        if not isinstance(data, dict):
            raise ValueError("Invalid API response")

        docs = data.get("docs")

        if not isinstance(docs, list):
            raise ValueError("Missing search results")

    except (requests.RequestException, ValueError) as error:
        raise OpenLibraryError(
            "Unable to retrieve books from Open Library."
        ) from error

    books = []

    for book in docs:
        if not isinstance(book, dict) or not book.get("title"):
            continue

        books.append({
            "title": book["title"],
            "authors": book.get("author_name") or [],
            "first_publish_year": book.get("first_publish_year"),
            "open_library_key": book.get("key"),
            "isbn": book.get("isbn") or [],
        })

    return books
