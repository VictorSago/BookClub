



_userdata:User = None


class User:
    def __init__(self, cardnumber):
        self.cardnumber = cardnumber


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

