"""Password hashing and API token hashing."""

import hashlib
import logging
import secrets

import bcrypt

logger = logging.getLogger(__name__)

# Bcrypt accepts at most 72 bytes. Truncate to avoid ValueError (and passlib init bug).
_BCRYPT_MAX_BYTES = 72
_BCRYPT_ROUNDS = 10


def _to_bcrypt_secret(value: str | bytes) -> bytes:
    """Return value as bytes, truncated to 72 bytes for bcrypt."""
    if isinstance(value, bytes):
        return value[:_BCRYPT_MAX_BYTES]
    return value.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    secret = _to_bcrypt_secret(password)
    return bcrypt.hashpw(secret, bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    if not hashed or not hashed.startswith("$2"):
        return False
    try:
        return bcrypt.checkpw(_to_bcrypt_secret(plain), hashed.encode("ascii"))
    except ValueError:
        return False


def hash_api_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_api_token() -> str:
    return secrets.token_hex(32)
