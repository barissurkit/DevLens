import base64
import hashlib
import re
import secrets

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

AAD = b"devlens-oauth-pkce-v1"
NONCE_SIZE = 12
KEY_SIZE = 32


class AuthStateCryptoError(ValueError):
    """Raised when the OAuth state encryption key or ciphertext is invalid."""


def decode_encryption_key(value: str) -> bytes:
    if not re.fullmatch(r"[A-Za-z0-9_-]*={0,2}", value) or len(value.rstrip("=")) % 4 == 1:
        raise AuthStateCryptoError("AUTH_STATE_ENCRYPTION_KEY must be base64url encoded.")
    try:
        padded = value + "=" * (-len(value) % 4)
        key = base64.b64decode(padded.encode("ascii"), altchars=b"-_", validate=True)
    except (ValueError, UnicodeEncodeError) as exc:
        raise AuthStateCryptoError("AUTH_STATE_ENCRYPTION_KEY must be base64url encoded.") from exc
    if len(key) != KEY_SIZE:
        raise AuthStateCryptoError("AUTH_STATE_ENCRYPTION_KEY must decode to 32 bytes.")
    return key


def random_urlsafe_token(size: int = 32) -> str:
    return secrets.token_urlsafe(size)


def sha256_digest(value: str) -> bytes:
    return hashlib.sha256(value.encode("utf-8")).digest()


def encrypt_verifier(verifier: str, key: bytes) -> tuple[bytes, bytes]:
    nonce = secrets.token_bytes(NONCE_SIZE)
    return nonce, AESGCM(key).encrypt(nonce, verifier.encode("ascii"), AAD)


def decrypt_verifier(ciphertext: bytes, nonce: bytes, key: bytes) -> str:
    try:
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, AAD)
        return plaintext.decode("ascii")
    except (InvalidTag, UnicodeDecodeError, ValueError) as exc:
        raise AuthStateCryptoError("OAuth verifier could not be decrypted.") from exc
