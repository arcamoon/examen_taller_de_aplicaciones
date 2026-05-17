import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from flask import current_app


def _aes_key() -> bytes:
    key = current_app.config.get("AES256_KEY", "")

    try:
        key_bytes = bytes.fromhex(key)
    except ValueError as exc:
        raise ValueError("AES256_KEY must be a 64-character hex value") from exc

    if len(key_bytes) != 32:
        raise ValueError("AES256_KEY must represent exactly 32 bytes")

    return key_bytes


def encrypt_id(value: int) -> str:
    nonce = os.urandom(12)
    encrypted = AESGCM(_aes_key()).encrypt(nonce, str(value).encode("utf-8"), None)
    token = base64.urlsafe_b64encode(nonce + encrypted).decode("utf-8")
    return token.rstrip("=")


def decrypt_id(token: str) -> int:
    padded_token = token + ("=" * (-len(token) % 4))
    raw_token = base64.urlsafe_b64decode(padded_token.encode("utf-8"))
    nonce = raw_token[:12]
    encrypted = raw_token[12:]
    value = AESGCM(_aes_key()).decrypt(nonce, encrypted, None)
    return int(value.decode("utf-8"))
