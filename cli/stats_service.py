import os

from cli import input_handlers, user_session
from cli.constants import BASE


def _get_headers() -> dict:
    headers = {"X-API-Key": os.getenv("API_KEY", "")}
    user = user_session.get_userdata()
    if user and user.card_number:
        headers["X-Card-Number"] = str(user.card_number)
    return headers


def show_statistics_menu(get_json_func) -> None:
    """Entry point for the statistics submenu."""
    while True:
        menu_text = (
            "\nLibrary Statistics:\n"
            "1) Most borrowed books\n"
            "2) Books never borrowed\n"
            "0) Back to main menu\n"
        )
        choice = input_handlers.get_int_range(menu_text, 0, 2)

        if choice == 1:
            _show_top_borrowed_books(get_json_func)
        elif choice == 2:
            _show_never_borrowed_books(get_json_func)
        elif choice == 0:
            break


def _show_top_borrowed_books(get_json_func) -> None:
    base_url = BASE
    
    print("\n--- Most Borrowed Books ---")

    headers = _get_headers()
    books = get_json_func(f"{base_url}/stats/most-borrowed", headers=headers, timeout=10)
    if books is None:
        return

    if not books:
        print("No borrowing history found.")
    else:
        for index, book in enumerate(books, start=1): #TODO: sync with backend
            title = book.get("title", "Unknown")
            authors = book.get("authors") or []
            authors_str = ", ".join(authors) if authors else "Unknown Author"
            count = book.get("borrow_count", 0)
            print(f"{index}. {title}  by {authors_str} — borrowed {count} time(s)")


def _show_never_borrowed_books(get_json_func) -> None:
    base_url = BASE

    print("\n--- Books Never Borrowed ---")

    headers = _get_headers()
    books = get_json_func(f"{base_url}/stats/never-borrowed", headers=headers,timeout=10)
    if books is None:
        return

    if not books:
        print("All books in the catalog have been borrowed at least once.")
    else:
        print(f"Found {len(books)} unborrowed book(s):")
        for index, book in enumerate(books, start=1):  #TODO: sync with backend
            title = book.get("title", "Unknown")
            authors = book.get("authors") or []
            authors_str = ", ".join(authors) if authors else "Unknown Author"
            year = book.get("first_publish_year")
            year_str = f" ({year})" if year else ""
            print(f"{index}. {title}{year_str} by {authors_str}")