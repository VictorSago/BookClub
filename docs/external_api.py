
import requests

OPEN_LIBRARY_URL = "https://openlibrary.org/search.json?title=harry+potter"


class OpenLibraryError(Exception):
    """Raised when Open Library cannot provide results."""


def search_books(title: str) -> list[dict]:
    """Search Open Library for books by title."""

    params = {
        "title": title,
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

    except (requests.RequestException, ValueError) as error:
        raise OpenLibraryError(
            "Unable to retrieve books from Open Library."
        ) from error

    books = []

    for book in data.get("docs", []):
        books.append({
            "title": book.get("title"),
            "authors": book.get("author_name", []),
            "first_publish_year": book.get("first_publish_year"),
            "open_library_key": book.get("key"),
        })

    return books
