


import os, requests, json
from cli import input_handlers, user_session, login_service, constants
from dotenv import load_dotenv


load_dotenv(".env", override=True)


api_key = os.getenv("API_KEY", "")

BASE = "http://127.0.0.1:800"



def user_login(get_json_func, base_url):
    while True:
        cardnumber = input_handlers.get_valid_text(
            "Please enter your library card number: ", # prompt for user input
            "Card number is your personal 12-digit number. Please try again."  #error message for empty input
        )

        member = get_json_func(f"{base_url}/whoami", 
                            params=None, 
                            headers={"X-API-Key": api_key, "X-Card-Number": cardnumber}, 
                            timeout=5)

        if member == None:  
            print("Login failed. Please check your card number and API key.")
        else:
            user_session.set_userdata(member)
            print(f"\nLogin successful. Welcome {member.get('name')}!\nYou are logged in as a {member.get('role')}")
            return None


def user_logout():
    user_session.set_userdata(None)
    print("\nYou have been logged out.")
    return None