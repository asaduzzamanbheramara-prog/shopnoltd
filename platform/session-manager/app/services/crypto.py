"""
Encrypts proxy credentials at rest using Fernet (symmetric encryption).
Key must come from env/K8s Secret — never hardcode.
"""

import os

from cryptography.fernet import Fernet

_KEY = os.getenv("SESSION_MANAGER_ENCRYPTION_KEY")
if not _KEY:
    # Dev-only fallback so the app can boot locally; MUST be overridden
    # via a K8s Secret (SESSION_MANAGER_ENCRYPTION_KEY) in any real deploy.
    _KEY = Fernet.generate_key().decode()

_fernet = Fernet(_KEY.encode() if isinstance(_KEY, str) else _KEY)


def encrypt_secret(plaintext: str) -> str:
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    return _fernet.decrypt(ciphertext.encode()).decode()
