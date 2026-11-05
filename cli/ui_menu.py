from cli.constants import ADMIN_MENU_TEXT
from cli import input_handlers, user_session, login_service
from cli.borrow_ui import borrow_book as borrow_book_cli
import requests

def show_books(get_json_func, base_url):
    print("\nShow books:\n\nYou can search books by Title, Author, Publishing year or any combination.")
    print("If you do not want to use a specific search criteria you leave it blank.\n\n")

    query_string = "?"
    title = input_handlers.get_valid_text("Type the Title or leave blank:\n", can_be_empty=True)
    author = input_handlers.get_valid_text("Type the Author or leave blank:\n", can_be_empty=True)
    year = input_handlers.get_valid_int("Type Publishing year (ex. 1992) or leave blank:\n", can_be_empty=True)
    available = input_handlers.get_valid_int("Type 1 for available books or leave blank for all books:\n", can_be_empty=True)

    if title: query_string = query_string + "title=" + title + "&"
    if author: query_string = query_string + "author=" + author + "&"
    if year is not None: query_string = query_string + "year=" + str(year) + "&"
    if available == 1: query_string = query_string + "available=" + str(True) + "&"

    books = get_json_func(f"{base_url}/books{query_string}")

    if books == None: return None   # HTTP failure, get_json() prints reason

    if len(books) == 0:
        print("No books found")
        return None
    else:
        print(f"We found {len(books)} books:")
        for index, book in enumerate(books, start=1):
            print(f"\n{book["title"]} ({book["first_publish_year"]})")
            for author in book["authors"]:
                print(f"{author}")
            print(f"Library book id: {book["book_id"]}")
            if book["isbn"] != None: print(f"(ISBN: {book["isbn"]})")
            if book["available"] == True: print(f"Book is available")
            else: print(f"Book is not available")

            if index % 5 == 0:
                user_input = input(f"\nPress Enter to show more books or type 0 then press Enter to quit: ")
                if user_input == "0":
                    break

    return None


def borrow_book():
    """Open the Borrow Book feature."""
    borrow_book_cli()

def return_book():
    print("\nReturn a book:\n")
    pass


def add_book(post_json_func, base_url: str, api_key: str | None = None, card_number: str | int | None = None) -> None:
    """Interactively prompts the user for an ISBN, checks length, and sends it to the API."""
    print("\nAdd Book from Open Library")

    while True:
        # Prompt user directly; pressing Enter on empty input cancels the action
        user_input = input("Enter book ISBN (10 or 13 digits) or press Enter to cancel: ").strip()

        # Exit to the menu if input is empty
        if not user_input:
            print("Action cancelled.")
            return

        # Strip hyphens and spaces before verifying length
        clean_isbn = user_input.replace("-", "").replace(" ", "")

        # Check only length on the client side; format rules are handled by the backend
        if len(clean_isbn) not in (10, 13):
            print("Invalid input. ISBN must be 10 or 13 characters long. Please try again.")
            continue

        print(f"Searching Open Library for ISBN: {clean_isbn}...")

        headers = {}
        if api_key:
            headers["X-API-Key"] = api_key

        # get current user data to include card number in the request if available
        current_user = user_session.get_userdata()
        if current_user and current_user.card_number:
            headers["X-Card-Number"] = str(current_user.card_number)

        payload = {"isbn": clean_isbn}
        url = f"{base_url}/books/import"

        # Send POST request to the API
        result, status_code = post_json_func(url, json_data=payload, headers=headers)

        if status_code == 201 and result:
            print(f"\nSuccess! Added new book '{result['title']}' (ID: {result['book_id']}).")
            break
        elif status_code == 409:
            # error message already printed inside post_json
            break
        elif status_code == 404:
            # error message already printed inside post_json
            retry = input("\nWould you like to try another ISBN? (y/n): ").strip().lower()
            if retry != "y":
                break
        else:
            retry = input("\nWould you like to try another ISBN? (y/n): ").strip().lower()
            if retry != "y":
                break


def add_member(post_json_func, base_url, api_key):

    if user_session.get_userdata().role != "librarian":
        print("You need to be a librarian to add new members.")
        return

    print("\nAdd new member:\n")
    name = ""
    email = ""
    phone = ""

    user_input = input_handlers.get_int_range("Are you sure you want to create a new member? 1) Yes, 0) No: ", 0, 1)

    if user_input == 1:
        name = input_handlers.get_valid_text("Please type name of the new member: ", "Name cannot be empty.")
        email = input_handlers.get_valid_email("Please type e-mail of the new member: ", "Invalid email format.")
        phone = input_handlers.get_valid_text("Please type phonenumber of the new member: ", "Phone number cannot be empty.")
    else:
        return None

    new_member = {
    "name": name,
    "email": email,
    "phone": phone
    }

    response, response_code = post_json_func(f"{base_url}/members", 
                             json_data=new_member, 
                             headers={"X-API-Key": api_key, 
                                      "X-Card-Number": user_session.get_userdata().card_number}) # CHECK: that setup matches our API

    if response_code == 201:       # Print the new member details if successfully added, else the post_json function already prints the error message
        print(f"\nNew member added!\n\nID: {response.get('member_id')}\nName: {response.get('name')}\nCard number: {response.get('card_number')}\nEmail: {response.get('email')}\nPhone: {response.get('phone')}")
    

def show_my_data(get_json_func, base_url):
    print("\nShow my data:\n")

    data = get_json_func(f"{base_url}/me/data", 
                         headers={"X-API-Key": login_service.api_key, 
                                  "X-Card-Number": user_session.get_userdata().card_number})
    
    if data is None:
        print("Failed to retrieve user data.")  # Print on failure to interact with the API, get_jason() prints reason
        return
    
    member = data.get("member", 0)
    del member["anonymised_at"]
    loans = data.get("loans", 0)

    for key, value in member.items():
        print(f"{key}: {value}")

    print(f"\nNumber of Loans: {len(loans)}\n")

    for loan in loans:
        print(f"Title: {loan['book']['title']}")
        print(f"Due date: {loan['due_date']}")
        print("")


def anonymize_member(post_json_func, base_url, api_key):
    print("\nAnonymize member data:\n")

    member_id = input_handlers.get_valid_int("Please type the member ID of the member you like to anonymize: ", "Member ID must be a valid integer.")

    response, response_code = post_json_func(f"{base_url}/members/{member_id}/anonymise",
                              json_data=member_id,
                              headers={"X-API-Key": api_key, 
                                    "X-Card-Number": user_session.get_userdata().card_number})

    if response_code == 200:
        print(f"Member anonymiziation of member {response['member_id']} successful")

    print("")


def delete_member(base_url, api_key):
    print("\nDelete member:\n")

    member_id = input_handlers.get_valid_int("Please type the member ID of the member you like to delete: ", "Member ID must be a valid integer.")

    response = requests.delete(f"{base_url}/members/{member_id}",
                                              headers={"X-API-Key": api_key, 
                                                       "X-Card-Number": user_session.get_userdata().card_number})
    try:
        print(response.json()['detail'])
    except requests.exceptions.JSONDecodeError:
        print(f"Member {member_id} successfully deleted")

    print("")




def show_one_member_data(get_json_func, base_url):
    print("\nShow member data:\n")

    member_id = input_handlers.get_valid_int("Please type the member ID of the member you want to see data for: ", "Member ID must be a valid integer.")

    member_data = get_json_func(f"{base_url}/members/{member_id}", 
                         headers={"X-API-Key": login_service.api_key, 
                                  "X-Card-Number": user_session.get_userdata().card_number})
    
    if member_data is None:
        print("Failed to retrieve member data.")  # Print on failure to interact with the API, get_jason() prints reason
        return

    for key, value in member_data.items():
        print(f"{key}: {value}")


def exit_program():
    # Shutdown sequence
    login_service.user_logout()
    print("Turning system off")
    exit()


def edit_members_ui(post_json_func, base_url, api_key):    # If we have time we can implement this function to edit member data, anonymize member data and delete member data.
        
    while True:
        user_input = input_handlers.get_int_range(
            "1) Update member data\n2) Anonymize member data\n3) Delete member data\n0) Back to menu\n",
            0, 3
        )

        if user_input == 1:
            print("\nUpdate member data:")
            pass  # Implement update logic here
        elif user_input == 2:
            anonymize_member(post_json_func, base_url, api_key)
        elif user_input == 3:
            delete_member(base_url, api_key)
        elif user_input == 0:
            break


def admin_ui(post_json_func, get_json_func, base_url, api_key):
    while True:
        user_input = input_handlers.get_int_range(
            ADMIN_MENU_TEXT,
            0, 9
        )
        
        if user_input == 1:
            add_book(post_json_func, base_url, api_key)
        elif user_input == 2:
            add_member(post_json_func, base_url, api_key)
        elif user_input == 3:
            pass  # PLACEHOLDER: 
        elif user_input == 4:
            edit_members_ui(post_json_func, base_url, api_key)
        elif user_input == 5:
            pass  # PLACEHOLDER: Update or delete book
        elif user_input == 6:
            pass  # PLACEHOLDER: Future functionality
        elif user_input == 7:
            pass  # PLACEHOLDER: Future functionality
        elif user_input == 8:
            pass  # PLACEHOLDER: Future functionality
        elif user_input == 9:
            pass  # PLACEHOLDER: Future functionality
        elif user_input == 0:
            break
            


