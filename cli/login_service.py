


import os
from cli import input_handlers, user_session
from dotenv import load_dotenv
from cli.http_client import get_json, post_json, BASE, api_key


def user_login():
    while True:
        cardnumber = input_handlers.get_valid_text(
            "Please enter your library card number: ", # prompt for user input
            "Card number is your personal 12-digit number. Please try again."  #error message for empty input
        )

        member = get_json(f"{BASE}/whoami", 
                            params=None, 
                            headers={"X-API-Key": api_key, "X-Card-Number": cardnumber}, 
                            timeout=5)

        if member == None:  
            print("Login failed. Please check your card number and API key.")
        else:
            user = user_session.User(
                role=member.get("role"),
                member_id=member.get("member_id"),
                name=member.get("name"),
                card_number=cardnumber
            )
            user_session.set_userdata(user)
            print(f"\nLogin successful. Welcome {user.name}!\nYou are logged in as a {user.role}")
            return None


def user_logout():
    user_session.set_userdata(None)
    print("\nYou have been logged out.")
    return None