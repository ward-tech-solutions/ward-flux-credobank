"""
SNMP Credential Encryption/Decryption
Uses Fernet (AES-128) for symmetric encryption
"""

import os
import logging
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

# Get encryption key from environment
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    raise RuntimeError(
        "ENCRYPTION_KEY environment variable is required but was not found. "
        "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
    )

# Initialize Fernet cipher
try:
    cipher = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)
except Exception as e:
    logger.error(f"Failed to initialize Fernet cipher: {e}")
    raise


def encrypt_credential(plaintext: str) -> str:
    """Encrypt a credential string

    Args:
        plaintext: The plaintext credential (community string, password, etc.)

    Returns:
        Base64-encoded encrypted string
    """
    if not plaintext:
        return ""

    try:
        encrypted = cipher.encrypt(plaintext.encode())
        return encrypted.decode()
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        raise


def decrypt_credential(ciphertext: str) -> str:
    """Decrypt a credential string

    Args:
        ciphertext: The base64-encoded encrypted string

    Returns:
        Decrypted plaintext string
    """
    if not ciphertext:
        return ""

    try:
        decrypted = cipher.decrypt(ciphertext.encode())
        return decrypted.decode()
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        raise
