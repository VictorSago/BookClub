from cli import input_handlers
from cli.http_client import get_json, post_json , BASE


def show_statistics_menu() -> None:
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
            _show_top_borrowed_books()
        elif choice == 2:
            _show_never_borrowed_books()
        elif choice == 0:
            break


def _show_top_borrowed_books() -> None:
    print("\n--- Most Borrowed Books ---")


def _show_never_borrowed_books() -> None:
    print("\n--- Books Never Borrowed ---")