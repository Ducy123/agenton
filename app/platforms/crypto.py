import base64
import hashlib

from cryptography.fernet import Fernet

from app.config import get_settings


def _fernet() -> Fernet:
    """Derives a Fernet key from SECRET_KEY instead of managing a second
    secret — this table is the only place raw OAuth tokens touch disk, and
    rotating SECRET_KEY already invalidates JWTs, so tying token encryption
    to the same key keeps operators from having to track two rotation
    schedules."""
    settings = get_settings()
    key_bytes = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(key_bytes))


def encrypt_token(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_token(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
