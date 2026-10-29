
import requests

OPEN_LIBRARY_URL = "https://openlibrary.org/search.json"


class OpenLibraryError(Exception):
    """Raised when Open Library cannot provide results."""


def search_books(title: str, limit: int = 5) -> list[dict]:
    """Search Open Library for books by title."""

    if not title.strip():
        raise ValueError("Book title cannot be empty.")

    params = {
    "title": title.strip(),
    "limit": 5,
    "fields": "key,title,author_name,first_publish_year",
}

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
        })

    return books