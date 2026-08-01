import bcrypt
import secrets


def hash_password(password: str) -> str:
    """
    Hashes a plain-text password using bcrypt.
    Truncates to 72 bytes if needed (bcrypt standard max length).
    """
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against a stored bcrypt hash.
    """
    try:
        plain_bytes = plain_password.encode("utf-8")[:72]
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(plain_bytes, hash_bytes)
    except Exception:
        return False


def generate_session_token() -> str:
    """
    Generates a secure random session token string.
    """
    return f"shopsense_token_{secrets.token_hex(16)}"
