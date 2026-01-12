"""Unit tests for the password-derived crypto envelope and password hashing."""

from __future__ import annotations

import pytest
from cryptography.exceptions import InvalidTag

from app.security import crypto
from app.security.passwords import hash_password, needs_rehash, verify_password


def test_encrypt_decrypt_roundtrip():
    key = crypto.generate_dek()
    plaintext = b"super-secret-connection-password"
    blob = crypto.encrypt(plaintext, key)
    assert blob != plaintext
    assert crypto.decrypt(blob, key) == plaintext


def test_encrypt_is_nondeterministic():
    key = crypto.generate_dek()
    a = crypto.encrypt(b"same", key)
    b = crypto.encrypt(b"same", key)
    assert a != b  # random nonce per call


def test_decrypt_with_wrong_key_raises():
    blob = crypto.encrypt(b"data", crypto.generate_dek())
    with pytest.raises(InvalidTag):
        crypto.decrypt(blob, crypto.generate_dek())


def test_tampered_ciphertext_raises():
    key = crypto.generate_dek()
    blob = bytearray(crypto.encrypt(b"data", key))
    blob[-1] ^= 0x01  # flip a bit in the tag
    with pytest.raises(InvalidTag):
        crypto.decrypt(bytes(blob), key)


def test_kdf_is_deterministic_for_same_inputs():
    salt = crypto.generate_kdf_salt()
    k1 = crypto.derive_enc_key("hunter2", salt)
    k2 = crypto.derive_enc_key("hunter2", salt)
    assert k1 == k2
    assert len(k1) == crypto.ENC_KEY_LEN


def test_kdf_differs_by_salt_and_password():
    salt_a = crypto.generate_kdf_salt()
    salt_b = crypto.generate_kdf_salt()
    assert crypto.derive_enc_key("pw", salt_a) != crypto.derive_enc_key("pw", salt_b)
    assert crypto.derive_enc_key("pw1", salt_a) != crypto.derive_enc_key("pw2", salt_a)


def test_dek_wrap_unwrap():
    enc_key = crypto.derive_enc_key("pw", crypto.generate_kdf_salt())
    dek = crypto.generate_dek()
    wrapped = crypto.wrap_dek(dek, enc_key)
    assert crypto.unwrap_dek(wrapped, enc_key) == dek


def test_full_envelope_roundtrip():
    """password -> ENC_KEY -> wrap DEK -> encrypt field -> decrypt back."""
    salt = crypto.generate_kdf_salt()
    enc_key = crypto.derive_enc_key("correct horse", salt)
    dek = crypto.generate_dek()
    wrapped = crypto.wrap_dek(dek, enc_key)

    blob = crypto.encrypt_str("db.internal.example.com", dek)

    # Later, in a fresh request: re-derive, unwrap, decrypt.
    enc_key2 = crypto.derive_enc_key("correct horse", salt)
    dek2 = crypto.unwrap_dek(wrapped, enc_key2)
    assert crypto.decrypt_str(blob, dek2) == "db.internal.example.com"


def test_password_hash_and_verify():
    h = hash_password("s3cret-passphrase")
    assert h != "s3cret-passphrase"
    assert verify_password(h, "s3cret-passphrase") is True
    assert verify_password(h, "wrong") is False


def test_verify_rejects_garbage_hash():
    assert verify_password("not-a-real-hash", "whatever") is False


def test_needs_rehash_false_for_current_params():
    assert needs_rehash(hash_password("pw")) is False
