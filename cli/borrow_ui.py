import os
import requests
from dotenv import load_dotenv

from cli import input_handlers, user_session

load_dotenv(".env")

BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


def borrow_book() -> None:
    """Borrow an available library book for the logged-in member."""

    user = user_session.get_userdata()

    if user is None:
        print("\nPlease log in first.")
        return

    card_number = (
        user.get("cardnumber")
        if isinstance(user, dict)
        else getattr(user, "cardnumber", None)
    )

    if not card_number:
        print("\nMember card number is missing.")
        return

    api_key = os.getenv("API_KEY")

    if not api_key:
        print("\nAPI key is not configured.")
        return

    headers = {
        "X-API-Key": api_key,
        "X-Card-Number": str(card_number),
    }

    print("\n===== BORROW A BOOK =====")

    try:
        # 1. Fetch library catalog and sort by book_id numerically
        print("\nFetching library catalog...")
        response = requests.get(f"{BASE.rstrip('/')}/books", timeout=5)
        response.raise_for_status()
        books = response.json()

        if not books:
            print("No books available in the library.")
            return

        # Sort books by book_id in ascending order
        books = sorted(books, key=lambda x: x.get("book_id", 0))

        print(f"\nWe found {len(books)} books in the catalog:")
        for book in books:
            status = "Available" if book.get("available") else "Not available"
            isbn_str = f" | ISBN: {book['isbn']}" if book.get("isbn") else ""
            print(f"[{book['book_id']}] {book['title']} ({book.get('first_publish_year', 'N/A')}){isbn_str} - {status}")

        print("-" * 50)

        # 2. Loop for selecting a book (allows retrying if book is unavailable)
        while True:
            book_id = input_handlers.get_valid_int("\nEnter Book ID you want to borrow: ")

            if book_id <= 0:
                print("Book ID must be a positive number.")
                continue

            # Verify the specific book's status and details
            response = requests.get(
                f"{BASE.rstrip('/')}/books/{book_id}",
                timeout=5,
            )
            response.raise_for_status()

            book = response.json()

            print(f"\nTitle: {book.get('title', 'N/A')}")
            print(f"Book ID: {book.get('book_id', 'N/A')}")

            isbn = book.get("isbn")
            print(f"ISBN: {isbn if isbn else 'Not available'}")

            if not book.get("available", False):
                print("Availability: Not available")
                print("This book is already borrowed.")
                
                retry = input("\nWould you like to select another book? (y/n): ").strip().lower()
                if retry == "y":
                    print("-" * 50)
                    continue
                else:
                    print("Borrowing cancelled.")
                    return
            else:
                print("Availability: Available")
                break

        # 3. Default loan duration (set to 21 days automatically)
        loan_days = 21

        print(f"Loan period: {loan_days} days")
        

        confirm = input(
            "\nConfirm borrowing? (y/n): "
        ).strip().lower()

        if confirm != "y":
            print("Borrowing cancelled.")
            return

        # 4. Send the borrowing request to FastAPI with the chosen days
        response = requests.post(
            f"{BASE.rstrip('/')}/me/loans",
            json={"book_id": book_id, "days": loan_days},
            headers=headers,
            timeout=5,
        )
        response.raise_for_status()

        loan = response.json()
        borrowed_book = loan.get("book", {})

        # 5. Display success summary
        print("\n===== BORROWING SUCCESSFUL =====")
        print(f"Title:       {borrowed_book.get('title', 'N/A')}")
        print(f"Book ID:     {borrowed_book.get('book_id', 'N/A')}")
        print(f"ISBN:        {borrowed_book.get('isbn') or 'Not available'}")
        print(f"Loan ID:     {loan.get('loan_id', 'N/A')}")
        print(f"Borrowed on: {loan.get('loan_date', 'N/A')}")
        print(f"Due date:    {loan.get('due_date', 'N/A')}")

    except (EOFError, KeyboardInterrupt):
        print("\nBorrowing cancelled.")

    except requests.exceptions.Timeout:
        print("\nRequest timed out.")
        print("Check your active loans before trying again.")

    except requests.exceptions.ConnectionError:
        print("\nCould not connect to the library server.")

    except requests.exceptions.HTTPError as error:
        status = error.response.status_code

        try:
            detail = error.response.json().get(
                "detail", "Unknown server error"
            )
        except ValueError:
            detail = error.response.text or "Unknown server error"

        print(f"\nBorrowing failed ({status}): {detail}")

    except requests.exceptions.RequestException as error:
        print(f"\nRequest failed: {error}")

    except (ValueError, KeyError, TypeError):
        print("\nThe server returned an invalid response.")