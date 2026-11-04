

import os, requests, json
from dotenv import load_dotenv

from cli.constants import MAIN_MENU_TEXT_LIBRARIAN, MAIN_MENU_TEXT_MEMBER
from cli import input_handlers, user_session, login_service
from cli.ui_menu import (
    show_books,
    borrow_book,
    return_book,
    admin_ui,
    exit_program,
)


def main():
    print("Welcome to your local library system!")

    if not user_session.is_loggedin():
        login_service.user_login()

    while user_session.is_loggedin():
        if user_session.get_userdata().role == "librarian":
            user_input = input_handlers.get_int_range(
                MAIN_MENU_TEXT_LIBRARIAN,
                0, 4
                )
            if user_input == 1:
                admin_ui()
            elif user_input == 2:
                show_books()
            elif user_input == 3:
                borrow_book()
            elif user_input == 4:
                return_book()
            elif user_input == 0:
                exit_program()

        else:
            user_input = input_handlers.get_int_range(
                MAIN_MENU_TEXT_MEMBER,
                0, 4
                )
            if user_input == 2:
                show_books()
            elif user_input == 3:
                borrow_book()
            elif user_input == 4:
                return_book()
            elif user_input == 0:
                exit_program()


if __name__ == "__main__":
    main()