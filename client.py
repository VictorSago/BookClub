

import os, requests, json
from dotenv import load_dotenv

from cli.constants import MAIN_MENU_TEXT_LIBRARIAN, MAIN_MENU_TEXT_MEMBER
from cli import input_handlers, user_session, login_service
from cli.stats_service import show_statistics_menu
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


def post_json(url: str, json_data: dict, headers: dict | None = None, timeout: int = 10) -> tuple[dict | None, int | None]:
    """Send a POST request and handle exceptions safely without crashing the CLI."""
    try:
        response = requests.post(url, json=json_data, headers=headers, timeout=timeout)
        
        if response.status_code in (200, 201):
            return response.json(), response.status_code
        
        try:
            error_detail = response.json().get("detail", "Unknown error")
        except requests.exceptions.JSONDecodeError:
            error_detail = response.text or "Unknown error"

        if response.status_code == 400:
            print(f"\n[Client Error]: {error_detail}")
        elif response.status_code == 403:
            print("\n[Access Denied]: Only librarians can perform this action.")
        elif response.status_code == 404:
            print(f"\n[Not Found]: {error_detail}")
        elif response.status_code == 409:
            print(f"\n[Conflict]: {error_detail}")
        elif response.status_code == 502:
            print(f"\n[External API Error]: {error_detail}")
        else:
            print(f"\n[Error {response.status_code}]: {error_detail}")
            
        return None, response.status_code

    except requests.exceptions.Timeout:
        print("\n[Error] Connection timed out. Open Library is taking too long to respond.")
    except requests.exceptions.ConnectionError:
        print("\n[Error] Could not connect to the local library server.")
    except requests.exceptions.RequestException as error:
        print(f"\n[Network Error] {type(error).__name__}: {error}")
        
    return None, None


def main():
    print("Welcome to your local library system!")

    if not user_session.is_loggedin():
        login_service.user_login(get_json)

    while user_session.is_loggedin():
        if user_session.get_userdata().role == "librarian":
            user_input = input_handlers.get_int_range(
                MAIN_MENU_TEXT_LIBRARIAN,
                0, 9
                )
            if user_input == 1:
                admin_ui(get_json, post_json)
            elif user_input == 2:
                show_books(get_json)
            elif user_input == 3:
                borrow_book()
            elif user_input == 4:
                return_book()
            elif user_input == 5:
                show_statistics_menu(get_json)
            elif user_input == 6:
                pass  # Placeholder SHOW MY DATA functionality
            elif user_input == 7:
                pass  # Placeholder for future functionality
            elif user_input == 8:
                pass  # Placeholder for future functionality
            elif user_input == 9:
                pass  # Placeholder for future functionality
            elif user_input == 0:
                exit_program()

        else:
            user_input = input_handlers.get_int_range(
                MAIN_MENU_TEXT_MEMBER,
                0, 9
                )
            if user_input == 2:
                show_books(get_json)
            elif user_input == 3:
                borrow_book()
            elif user_input == 4:
                return_book()
            elif user_input == 5:
                show_statistics_menu(get_json)
            elif user_input == 6:
                pass  # Placeholder SHOW MY DATA functionality
            elif user_input == 7:
                pass  # Placeholder for future functionality
            elif user_input == 8:
                pass  # Placeholder for future functionality
            elif user_input == 9:
                pass  # Placeholder for future functionality
            elif user_input == 0:
                exit_program()


if __name__ == "__main__":
    main()