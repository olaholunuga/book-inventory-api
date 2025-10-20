from api import ph
from argon2.exceptions import VerifyMismatchError

def hash_password(password):
    """password hasher
    """
    return ph.hash(password)

def check_password(hashed_password, password):
    """to verify password
    """
    try:
        return ph.verify(hashed_password, password)
    except VerifyMismatchError:
        raise ValueError("Incorrect Password")