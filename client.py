



# Functions needed for sprint 1:

# Show books (member)
# Borrow a book (member)
# Return a book (member)

# Register a new member (librarian)
# Add book from open library (librarian)

# General:
# Recieve and clearly display error-messeges from API if something goes wrong in the connection with Open Library (no crash).
# Likewise if something goes wrong when connecting to our database.




import os, requests, json
from dotenv import load_dotenv

from cli.constants import MAIN_MENU_TEXT
from cli import input_handlers, user_session, login_service
from cli.ui_menu import (
    show_books,
    borrow_book,
    return_book,
    admin_ui,
    exit_program,
)


load_dotenv(".env")


api_key = os.getenv("API_KEY")

BASE = "http://127.0.0.1:8000"


def get_json(url, params=None, headers=None, timeout=5):
    try:
        response = requests.get(url, params=params, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        print("The search timed out")
    except requests.exceptions.ConnectionError:
        print("Could not connect")
    except requests.exceptions.HTTPError as error:
        print(f"Server rejection: {error.response.status_code}")
    except requests.exceptions.JSONDecodeError:
        print("The answer was not JSON")
    except requests.exceptions.RequestException as error:
        print(f"Someting else went wrong: {type(error).__name__}")
    return None


def main():
    print("Welcome to your local library system!")

    if user_session.is_loggedin() == False:
        login_service.user_login(get_json, BASE)

    while user_session.is_loggedin() == True:
        user_input = input_handlers.get_int_range(
            MAIN_MENU_TEXT,
            0, 4
        )

        if user_input == 1:
            admin_ui()
        elif user_input == 2:
            show_books(get_json, BASE)
        elif user_input == 3:
            borrow_book()
        elif user_input == 4:
            return_book()
        elif user_input == 0:
            exit_program()


if __name__ == "__main__":
    main()