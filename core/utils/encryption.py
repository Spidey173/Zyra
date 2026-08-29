import base64
import hashlib
from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken

def _get_fernet():
    """Derives a deterministic 32-byte Fernet key from Django SECRET_KEY."""
    secret = getattr(settings, 'SECRET_KEY', 'zyra-default-secret-encryption-key')
    key = hashlib.sha256(secret.encode('utf-8')).digest()
    fernet_key = base64.urlsafe_b64encode(key)
    return Fernet(fernet_key)

def encrypt_message_text(plain_text: str) -> str:
    """
    Encrypts message plain text into a secure ciphertext string.
    Ciphertext is prefixed with 'enc::' for identification.
    """
    if not plain_text:
        return ''
    try:
        f = _get_fernet()
        cipher_bytes = f.encrypt(plain_text.encode('utf-8'))
        return f"enc::{cipher_bytes.decode('utf-8')}"
    except Exception:
        return plain_text

def decrypt_message_text(cipher_text: str) -> str:
    """
    Decrypts message ciphertext back to plain text.
    Gracefully returns plain text for legacy unencrypted messages.
    """
    if not cipher_text:
        return ''
    if not str(cipher_text).startswith('enc::'):
        return cipher_text
    try:
        f = _get_fernet()
        raw_token = cipher_text[5:].encode('utf-8')
        plain_bytes = f.decrypt(raw_token)
        return plain_bytes.decode('utf-8')
    except (InvalidToken, Exception):
        return '[Encrypted message]'
