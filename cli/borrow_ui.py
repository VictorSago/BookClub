
import os
import requests
from dotenv import load_dotenv

from cli import user_session


load_dotenv(".env")

BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
BORROW_ENDPOINT = os.getenv("BORROW_ENDPOINT", "/loans")


def borrow_book():
    """Allow a logged-in member to borrow an available book."""

    # Step 1: Check the logged-in member
    user = user_session.get_userdata()

    if user is None:
        print("Please log in first.")
        return

    # Step 2: Get the member's card number
    card_number = (
        user.get("cardnumber")
        if isinstance(user, dict)
        else getattr(user, "cardnumber", None)
    )

    if not card_number:
        print("Member card number is missing.")
        return

    # Step 3: Read the API key
    api_key = os.getenv("API_KEY")

    if not api_key:
        print("API key is not configured.")
        return

    # Step 4: Ask for the Book ID
    print("\n===== BORROW A BOOK =====")

    try:
        book_id = int(input("Enter Book ID: ").strip())

        if book_id <= 0:
            print("Book ID must be a positive number.")
            return

    except ValueError:
        print("Invalid Book ID. Please enter a number.")
        return

    except (EOFError, KeyboardInterrupt):
        print("\nBorrowing cancelled.")
        return

    # Step 5: Prepare the request
    url = f"{BASE.rstrip('/')}/{BORROW_ENDPOINT.lstrip('/')}"

    headers = {
        "X-API-Key": api_key,
        "X-Card-Number": str(card_number),
    }

    payload = {
        "book_id": book_id
    }

    # Step 6: Send the POST request
    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=5
        )

        # Raise an error for unsuccessful responses
        response.raise_for_status()

        loan = response.json()

        # Step 7: Display the result
        print("\nBook borrowed successfully!")
        print(f"Book ID: {loan.get('book_id', book_id)}")
        print(f"Loan ID: {loan.get('loan_id', 'N/A')}")
        print(f"Borrowed on: {loan.get('loan_date', 'N/A')}")
        print(f"Due date: {loan.get('due_date', 'N/A')}")

    except requests.exceptions.Timeout:
        print("The server took too long to respond.")
        print("Check your borrowed books before trying again.")

    except requests.exceptions.ConnectionError:
        print("Could not connect to the library server.")

    except requests.exceptions.HTTPError as error:
        try:
            detail = error.response.json().get(
                "detail", "Unknown server error"
            )
        except ValueError:
            detail = "Server returned an invalid error response."

        if error.response.status_code == 401:
            print(f"Authentication failed: {detail}")

        elif error.response.status_code == 404:
            print(f"Book not found: {detail}")

        elif error.response.status_code == 409:
            print(f"Book unavailable: {detail}")

        else:
            print(f"Server error: {detail}")

    except requests.exceptions.RequestException as error:
        print(f"Request failed: {error}")

    except ValueError:
        print("The server returned invalid JSON.")