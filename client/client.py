



# Functions needed for sprint 1:

# Show books (member)
# Borrow a book (member)
# Return a book (member)

# Register a new member (librarian)
# Add book from open library (librarian)

# General:
# Recieve and clearly display error-messeges from API if something goes wrong in the connection with Open Library (no crash).
# Likewise if something goes wrong when connecting to our database.




import os, requests, json, input_handlers, user_session
from dotenv import load_dotenv


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



def show_books():
    print("\nShow books:\n\nYou can search books by Title, Author, Publishing year or any combination.")
    print("If you do not want to use a specific search criteria you leave it blank.\n\n")

    query_string = "?"
    title = input("Type the Title or leave blank:\n").strip()
    author = input("Type the Author or leave blank:\n").strip()
    year = input("Type Publishing year (ex. 1992) or leave blank:\n").strip()           # Add input-constrains for int when this is done

    if title != "": query_string = query_string + "title=" + title + "&"
    if author != "": query_string = query_string + "author=" + author + "&"
    if year != "": query_string = query_string + "year=" + year + "&"

    books = get_json(f"{BASE}/books{query_string}")
    
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
    print("\nBorrow a book:\n")
    pass

def return_book():
    print("\nReturn a book:\n")
    pass

def add_book():
    print("\nAdd a book:\n")
    pass

def add_member():
    print("\nAdd new member:\n")
    name = ""
    email = ""
    phone = ""
    
    user_input = input_handlers.get_int_input("Are you sure you want to create a new member? 1) Yes, 0) No: ", 0, 1)

    if user_input == 1: # ADD: Checks for typing errors - phone number
        name = input_handlers.get_valid_text("Please type name of the new member: ", "Name cannot be empty.")
        email = input_handlers.get_valid_email("Please type e-mail of the new member: ", "Invalid email format.")
        phone = input_handlers.get_valid_text("Please type phonenumber of the new member: ", "Phone number cannot be empty.")
    else:
        return

    print(name, email, phone) # EXCHANGE: with something like below when API is online
'''
    member = {
    "name": name,
    "email": email,
    "phone": phone
    }

    response = requests.post(f"{BASE}/members", json=member, timeout=5, headers={"X-API-Key": api_key}) # CHECK: that setup matches our API
    return response.status_code
'''


def user_login():
    cardnumber = input_handlers.get_valid_text(
        "Please enter your library card number: ", # prompt for user input
        "Card number is your personal 12-digit number. Please try again."  #error message for empty input
    )
    user_session.set_userdata({"cardnumber": cardnumber}) # PLACEHOLDER for show without FastAPI connection
    print(user_session._userdata, "Welcome!")             # These three lines should be replaced with API query for cardnumber-check
    return None                                           # If cardnumber and API-Key is correct -> user_session.set_userdata({"cardnumber": cardnumber})

'''
    member = # query fastAPI requests.get(f"{BASE}/members/", timeout=5, headers={"X-API-Key": api_key}) # CHECK: that setup matches our API
    
'''


def exit_program():
    # Shutdown sequence
    print("Turning system off")

    exit()


def admin_ui():
    while True:
        user_input = input_handlers.get_int_input(
            f"\nAdministrator functions: \n1) Add book to library\n2) Register new member\n0) Exit to main menu\n",
            0, 2
        )
        
        if user_input == 1:
            add_book()
        elif user_input == 2:
            add_member()
        elif user_input == 0:
            break
            

def main():
    print("Welcome to your local library system!")

    if user_session.is_loggedin() == False:
        user_login()

    while user_session.is_loggedin() == True:
        user_input = input_handlers.get_int_input(
            f"\nType a single number: \n1) Administrative functions (librarian)\n2) Show books\n3) Borrow book\n4) Return book\n0) Exit program\n",
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


if __name__ == "__main__":
    main()