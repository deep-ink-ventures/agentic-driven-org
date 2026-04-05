"""Tests for cookie encryption/decryption round-trip."""

import pytest
from cryptography.fernet import InvalidToken

from integrations.extensions.views import decrypt_cookies, encrypt_cookies


class TestEncryptDecryptRoundTrip:
    def test_simple_dict(self):
        original = {"auth_token": "abc123", "ct0": "xyz789"}
        encrypted = encrypt_cookies(original)
        decrypted = decrypt_cookies(encrypted)
        assert decrypted == original

    def test_nested_dict(self):
        original = {"outer": {"inner": "value"}, "list_key": [1, 2, 3]}
        encrypted = encrypt_cookies(original)
        decrypted = decrypt_cookies(encrypted)
        assert decrypted == original

    def test_unicode_values(self):
        original = {"name": "Muller", "emoji": "Hello"}
        encrypted = encrypt_cookies(original)
        decrypted = decrypt_cookies(encrypted)
        assert decrypted == original

    def test_empty_dict(self):
        original = {}
        encrypted = encrypt_cookies(original)
        decrypted = decrypt_cookies(encrypted)
        assert decrypted == original

    def test_list_values(self):
        original = {"tags": ["a", "b", "c"], "count": 42}
        encrypted = encrypt_cookies(original)
        decrypted = decrypt_cookies(encrypted)
        assert decrypted == original

    def test_encrypted_output_is_not_plaintext(self):
        original = {"secret": "super_secret_value_12345"}
        encrypted = encrypt_cookies(original)
        assert "super_secret_value_12345" not in encrypted
        assert "secret" not in encrypted

    def test_encrypted_output_is_string(self):
        encrypted = encrypt_cookies({"key": "val"})
        assert isinstance(encrypted, str)

    def test_encrypted_starts_with_fernet_prefix(self):
        encrypted = encrypt_cookies({"key": "val"})
        assert encrypted.startswith("gAAAAA")

    def test_different_inputs_produce_different_outputs(self):
        e1 = encrypt_cookies({"a": "1"})
        e2 = encrypt_cookies({"b": "2"})
        assert e1 != e2


class TestDecryptionWithWrongKey:
    def test_wrong_key_fails(self):
        from cryptography.fernet import Fernet

        original = {"token": "secret"}
        encrypted = encrypt_cookies(original)

        # Create a Fernet instance with a different key
        wrong_fernet = Fernet(Fernet.generate_key())
        with pytest.raises(InvalidToken):
            wrong_fernet.decrypt(encrypted.encode())

    def test_corrupted_ciphertext_fails(self):
        encrypted = encrypt_cookies({"token": "val"})
        corrupted = encrypted[:-5] + "XXXXX"
        with pytest.raises((InvalidToken, ValueError)):
            decrypt_cookies(corrupted)
