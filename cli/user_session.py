



_userdata:User = None


class User:
    def __init__(self, role, member_id, name, card_number):
        self.role = role
        self.member_id = member_id
        self.name = name
        self.card_number = card_number

def set_userdata(user:User):
    global _userdata
    _userdata = user

def get_userdata():
    return _userdata

def is_loggedin():
    if _userdata is not None:
        return True
    else:
        return False

