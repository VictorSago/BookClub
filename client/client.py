



# Functions needed for sprint 1:

# Show books (member)
# Borrow a book (member)
# Return a book (member)

# Register a new member (librarian)
# Add book from open library (librarian)

# General:
# Recieve and clearly display error-messeges from API if something goes wrong in the connection with Open Library (no crash).
# Likewise if something goes wrong when connecting to our database.



import os, requests
import user_session
import utils
from dotenv import load_dotenv

load_dotenv(".env")


api_key = os.getenv("API_KEY")

BASE = "http://127.0.0.1:8000"


def show_books():
    print("\nShow books:\n")
    pass

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
    
    user_input = utils.get_int_input("Are you sure you want to create a new member? 1) Yes, 0) No: ", 0, 1)

    if user_input == 1: # ADD: Checks for typing errors - phone number
        name = utils.get_not_empty_text("Please type name of the new member: ", "Name cannot be empty.")
        email = utils.get_valid_email("Please type e-mail of the new member: ", "Invalid email format.")
        phone = utils.get_not_empty_text("Please type phonenumber of the new member: ", "Phone number cannot be empty.")
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
    cardnumber = utils.get_not_empty_text(
        "Please enter your library card number: ", # prompt for user input
        "Card number is your personal 16-digit number. Please try again."  #error message for empty input
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
        user_input = utils.get_int_input(
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
        user_input = utils.get_int_input(
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