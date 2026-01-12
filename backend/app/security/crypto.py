"""Password-derived credential encryption; ENC_KEY lives only in Redis per session, so a stolen DB alone decrypts nothing."""

from __future__ import annotations

import os

from argon2.low_level import Type, hash_secret_raw
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# AES key-derivation parameters (PLAN §10.1: time=3, memory=64MB, parallelism=4).
_KDF_TIME_COST = 3
_KDF_MEMORY_COST_KIB = 64 * 1024
_KDF_PARALLELISM = 4

ENC_KEY_LEN = 32  # AES-256
DEK_LEN = 32
SALT_LEN = 16
NONCE_LEN = 12


def generate_kdf_salt() -> bytes:
    return os.urandom(SALT_LEN)


def derive_enc_key(password: str, kdf_salt: bytes) -> bytes:
    """Derive the 32-byte AES key (ENC_KEY) from the password; separate from the login hash (different salt, raw output)."""
    return hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=kdf_salt,
        time_cost=_KDF_TIME_COST,
        memory_cost=_KDF_MEMORY_COST_KIB,
        parallelism=_KDF_PARALLELISM,
        hash_len=ENC_KEY_LEN,
        type=Type.ID,
    )


def generate_dek() -> bytes:
    return os.urandom(DEK_LEN)


def encrypt(plaintext: bytes, key: bytes) -> bytes:
    """AES-GCM encrypt. Returns nonce || ciphertext+tag."""
    nonce = os.urandom(NONCE_LEN)
    ct = AESGCM(key).encrypt(nonce, plaintext, None)
    return nonce + ct


def decrypt(blob: bytes, key: bytes) -> bytes:
    """Inverse of :func:`encrypt`; raises ``InvalidTag`` if the key is wrong or the blob was tampered with."""
    nonce, ct = blob[:NONCE_LEN], blob[NONCE_LEN:]
    return AESGCM(key).decrypt(nonce, ct, None)


def wrap_dek(dek: bytes, enc_key: bytes) -> bytes:
    return encrypt(dek, enc_key)


def unwrap_dek(wrapped: bytes, enc_key: bytes) -> bytes:
    return decrypt(wrapped, enc_key)


def encrypt_str(plaintext: str, key: bytes) -> bytes:
    return encrypt(plaintext.encode("utf-8"), key)


def decrypt_str(blob: bytes, key: bytes) -> str:
    return decrypt(blob, key).decode("utf-8")
