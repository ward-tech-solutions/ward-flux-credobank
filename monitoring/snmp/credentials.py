"""
WARD FLUX - SNMP Credential Management

Secure storage and retrieval of SNMP credentials using Fernet encryption.
"""

import os
import logging
import threading
from typing import Optional
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class CredentialEncryption:
    """
    Handles encryption and decryption of SNMP credentials
    """

    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryption handler

        Args:
            encryption_key: Fernet encryption key (base64-encoded)
                          If not provided, reads from WARD_ENCRYPTION_KEY env var
        """
        key = encryption_key or os.getenv("WARD_ENCRYPTION_KEY")

        if not key:
            raise ValueError(
                "Encryption key not provided. Set WARD_ENCRYPTION_KEY environment variable "
                "or pass encryption_key parameter. Generate key with: "
                "python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )

        try:
            self.cipher = Fernet(key.encode() if isinstance(key, str) else key)
            logger.info("Credential encryption initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            raise

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string

        Args:
            plaintext: String to encrypt

        Returns:
            Encrypted string (base64-encoded)
        """
        try:
            if not plaintext:
                return ""

            encrypted = self.cipher.encrypt(plaintext.encode())
            return encrypted.decode()

        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise

    def decrypt(self, encrypted: str) -> str:
        """
        Decrypt an encrypted string

        Args:
            encrypted: Encrypted string (base64-encoded)

        Returns:
            Decrypted plaintext string
        """
        try:
            if not encrypted:
                return ""

            decrypted = self.cipher.decrypt(encrypted.encode())
            return decrypted.decode()

        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new Fernet encryption key

        Returns:
            Base64-encoded encryption key

        Example:
            key = CredentialEncryption.generate_key()
            print(f"WARD_ENCRYPTION_KEY={key}")
        """
        key = Fernet.generate_key()
        return key.decode()


# Singleton instance with thread-safe initialization
_encryption: Optional[CredentialEncryption] = None
_encryption_lock = threading.Lock()


def get_encryption() -> CredentialEncryption:
    """
    Get or create CredentialEncryption singleton (thread-safe)

    Returns:
        CredentialEncryption instance
    """
    global _encryption

    # Double-checked locking pattern for thread safety
    if _encryption is None:
        with _encryption_lock:
            if _encryption is None:  # Double check inside lock
                _encryption = CredentialEncryption()

    return _encryption


def encrypt_credential(plaintext: str) -> str:
    """
    Convenience function to encrypt a credential

    Args:
        plaintext: Credential to encrypt

    Returns:
        Encrypted credential
    """
    return get_encryption().encrypt(plaintext)


def decrypt_credential(encrypted: str) -> str:
    """
    Convenience function to decrypt a credential

    Args:
        encrypted: Encrypted credential

    Returns:
        Decrypted credential
    """
    return get_encryption().decrypt(encrypted)
