






# Functions needed for sprint 1:

# Show books (member)
# Borrow a book (member)
# Return a book (member)


# Add book from open library (librarian)
# Recieve and clearly display error-messeges from API if something goes wrong in the connection with Open Library (no crash)

# Register new member (librarian)

def exit_program():
    # Shutdown sequence
    print("Turning system off")

    exit()



def admin_ui():
        
    while True:
        try:
            user_input = int(input(f"Administrator functions: \n1) Add book to library\n2) Register new member\n9) Exit to main\n"))
    
        except ValueError:
            print("Please type a single number")

        if user_input == 1:
            print("add_book")
        elif user_input == 2:
            print("register_member")
        elif user_input == 9:
            main()
        else:
            print ("\nIncorrect command, try again")



def main():
    print("Welcome to your local library system!")

    while True:
        try:
            user_input = int(input(f"Type a single number: \n0) Administrative functions (librarian)\n1) Show books\n2) Borrow book\n3) Return book\n9) Exit program\n"))
    
        except ValueError:
            print("Please type a single number")

        if user_input == 0:
            admin_ui()
        elif user_input == 1:
            print("show_books")
        elif user_input == 2:
            print("borrow_book")
        elif user_input == 3:
            print("return_book")
        elif user_input == 9:
            exit_program()
        else:
            print ("\nIncorrect command, try again")



if __name__ == "__main__":
    main()