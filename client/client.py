



# Functions needed for sprint 1:

# Show books (member)
# Borrow a book (member)
# Return a book (member)

# Register a new member (librarian)
# Add book from open library (librarian)

# General:
# Recieve and clearly display error-messeges from API if something goes wrong in the connection with Open Library (no crash).
# Likewise if something goes wrong when connecting to our database.


# import requests

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
    
    user_input = int(input("Are you sure you want to create a new member? 1) Yes, 0) No: "))

    if user_input == 1: # MAYBE ADD: Checks for typing errors
        try:
            name = str(input("Please type name of the new member: "))
            email = str(input("Please type e-mail of the new member: "))
            phone = str(input("Please type phonenumber of the new member: "))

        except ValueError:
            print("Please try again and type the requested information")
    else:
        admin_ui()


    print(name, email, phone) # EXCHANGE: with something like below when API is online
'''
    member = {
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


def admin_ui():     # Do we need some kind of credentials to enter admin UI?
        
    while True:
        try:
            user_input = int(input(f"\nAdministrator functions: \n1) Add book to library\n2) Register new member\n0) Exit to main menu\n"))
        except ValueError:
            print("Please type a single number")

        if user_input == 1:
            add_book()
        elif user_input == 2:
            add_member()
        elif user_input == 0:
            main()
        else:
            print ("\nIncorrect command, try again")


def main():
    print("Welcome to your local library system!")

    while True:
        try:
            user_input = int(input(f"\nType a single number: \n1) Administrative functions (librarian)\n2) Show books\n3) Borrow book\n4) Return book\n0) Exit program\n"))
        except ValueError:
            print("Please type a single number")

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
            print ("\nIncorrect command, try again")



if __name__ == "__main__":
    main()
