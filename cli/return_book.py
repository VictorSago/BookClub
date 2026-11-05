"""CLI workflow for returning a borrowed BookClub library book."""

import os

import requests
from dotenv import load_dotenv

from . import input_handlers

load_dotenv(".env", override=True)

BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
TIMEOUT = 5

def return_book(card_number):
    """Display a member's active loans and return the selected loan."""
    api_key = os.getenv("API_KEY")
    if not api_key:
        print("\nAPI key is not configured.")
        return

    headers = {
        "X-API-Key": api_key,
        "X-Card-Number": str(card_number),
    }

    print("\n===== BOOKCLUB - RETURN A BOOK =====")

    try:
        print("\nFetching your borrowed books...")
        response = requests.get(
            f"{BASE}/me/loans",
            params={"active": "true"},
            headers=headers,
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        loans = response.json()

        if not isinstance(loans, list):
            print("The server returned an invalid loan list.")
            return

        if not loans:
            print("You have no active borrowed books.")
            return

        print("\n===== YOUR BORROWED BOOKS =====")
        for loan in loans:
            book = loan["book"]
            print(f"\nLoan ID:  {loan['loan_id']}")
            print(f"Title:    {book['title']}")
            print(f"Book ID:  {book['book_id']}")
            print(f"Due date: {loan['due_date']}")

        valid_loan_ids = {loan["loan_id"] for loan in loans}

        while True:
            loan_id = input_handlers.get_valid_int(
                "\nEnter Loan ID to return (0 to cancel): "
            )

            if loan_id == 0:
                print("Return cancelled.")
                return

            if loan_id not in valid_loan_ids:
                print("Please select a Loan ID from the list.")
                continue

            selected_loan = next(
                loan for loan in loans if loan["loan_id"] == loan_id
            )
            print(f"\nTitle: {selected_loan['book']['title']}")
            print(f"Loan ID: {loan_id}")

            confirm = input("\nConfirm return? (y/n): ").strip().lower()
            if confirm != "y":
                print("Return cancelled.")
                return
            
            # Update the loan through the backend's PATCH endpoint.
            response = requests.patch(
                f"{BASE}/me/loans/{loan_id}/return",
                headers=headers,
                timeout=TIMEOUT,
            )

            if response.status_code >= 400:
                try:
                    err_detail = response.json().get("detail", "Unknown error")
                except Exception:
                    err_detail = response.text
                print(f"\nError: {err_detail}")
                return

            response.raise_for_status()
            returned_loan = response.json()

            print("\n===== BOOK RETURNED SUCCESSFULLY =====")
            print(f"Loan ID: {loan_id}")
            print(f"Title: {selected_loan['book']['title']}")
            print(f"Returned on: {returned_loan['return_date']}")
            print("The book is now available for borrowing.")
            return

    except requests.exceptions.RequestException as error:
        print(f"\nReturn request failed: {error}")
    except (ValueError, KeyError, TypeError):
        print("The server returned an invalid response.")
    except (EOFError, KeyboardInterrupt):
        print("\nReturn cancelled.")