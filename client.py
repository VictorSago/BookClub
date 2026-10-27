



# Functions needed for sprint 1:

# Show books (member)
# Borrow a book (member)
# Return a book (member)

# Register a new member (librarian)
# Add book from open library (librarian)

# General:
# Recieve and clearly display error-messeges from API if something goes wrong in the connection with Open Library (no crash).
# Likewise if something goes wrong when connecting to our database.

import random, requests

BASE = "http://127.0.0.1:8000"




def show_books():
    pass

def borrow_book():
    pass

def return_book():
    pass

def add_book():
    pass

def add_member():
    print("\nAdd new member:\n")
    card_number = str(random.randrange(100000, 999999)) # ADD: Check with API so that number is not already in use.
    name = ""
    email = ""
    phone = ""

    while True:         # MAYBE ADD: Checks for typing errors
        try:
            name = str(input("Please type name of the new member: "))
            email = str(input("Please type e-mail of the new member: "))
            phone = str(input("Please type phonenumber of the new member: "))
            break

        except ValueError:
            print("Please type the requested information")


    print(card_number, name, email, phone) # Exchange with something like below when API is online
'''
    member = {
    "card_number": card_number,
    "name": name,
    "email": email,
    "phone": phone
    }

    result = requests.post(f"{BASE}/members", json=member, timeout=5) # Add key if we should have it
    return result.status_code
'''


def exit_program():
    # Shutdown sequence
    print("Turning system off")

    exit()



def admin_ui():
        
    while True:
        try:
            user_input = int(input(f"\nAdministrator functions: \n1) Add book to library\n2) Register new member\n9) Exit to main\n"))
        except ValueError:
            print("Please type a single number")

        if user_input == 1:
            add_book()
        elif user_input == 2:
            add_member()
        elif user_input == 9:
            main()
        else:
            print ("\nIncorrect command, try again")



def main():
    print("Welcome to your local library system!")

    while True:
        try:
            user_input = int(input(f"\nType a single number: \n0) Administrative functions (librarian)\n1) Show books\n2) Borrow book\n3) Return book\n9) Exit program\n"))
        except ValueError:
            print("Please type a single number")

        if user_input == 0:
            admin_ui()
        elif user_input == 1:
            show_books()
        elif user_input == 2:
            borrow_book()
        elif user_input == 3:
            return_book()
        elif user_input == 9:
            exit_program()
        else:
            print ("\nIncorrect command, try again")



if __name__ == "__main__":
    main()