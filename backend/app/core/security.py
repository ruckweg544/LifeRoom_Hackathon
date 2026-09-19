"""
Lightweight MVP security helpers: room code generation and password hashing.

Room codes are short, human-shareable, and generated from an alphabet that
excludes visually ambiguous characters (0/O, 1/I/L) so they're easy to read
aloud and type. Passwords are optional per-household and are always hashed
with bcrypt before storage - plaintext is never persisted.
"""
import hashlib
import secrets
import string

from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_CODE_ALPHABET = "".join(c for c in string.ascii_uppercase + string.digits if c not in "0O1IL")


def generate_room_code(length: int = 6) -> str:
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(length))


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_password(raw_password: str) -> str:
    return _pwd_context.hash(raw_password)


def verify_password(raw_password: str, password_hash: str) -> bool:
    return _pwd_context.verify(raw_password, password_hash)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
