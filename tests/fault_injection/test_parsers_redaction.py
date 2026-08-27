"""Parser and redaction tests.

Per Luna Directive — Focus Area 2: PII redaction, input sanitization,
encoding edge cases, and format validation.
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")
sys.path.insert(0, "packages")


from common.redaction import (
    detect_injection,
    redact_pii,
    sanitize_input,
    validate_crypto_address,
    validate_domain_format,
    validate_email_format,
    validate_phone_format,
    validate_url_format,
)


class TestPIIRedaction:
    """Test PII redaction."""

    def test_redact_email(self):
        """Email addresses should be redacted."""
        text = "Contact us at admin@example.com for info"
        result = redact_pii(text)
        assert "admin@example.com" not in result
        assert "[EMAIL_REDACTED]" in result

    def test_redact_phone(self):
        """Phone numbers should be redacted."""
        text = "Call +1 555 123 4567 for support"
        result = redact_pii(text)
        assert "555" not in result
        assert "[PHONE_REDACTED]" in result

    def test_redact_ssn(self):
        """SSN should be redacted."""
        text = "SSN: 123-45-6789"
        result = redact_pii(text)
        assert "123-45-6789" not in result
        assert "[SSN_REDACTED]" in result

    def test_redact_credit_card(self):
        """Credit card numbers should be redacted."""
        text = "Card: 4111 1111 1111 1111"
        result = redact_pii(text)
        assert "4111" not in result
        assert "[CARD_REDACTED]" in result

    def test_redact_multiple_pii(self):
        """Multiple PII types should all be redacted."""
        text = "Email: a@b.com Phone: +1 555 123 4567 SSN: 123-45-6789"
        result = redact_pii(text)
        assert "[EMAIL_REDACTED]" in result
        assert "[PHONE_REDACTED]" in result
        assert "[SSN_REDACTED]" in result

    def test_no_pii_unchanged(self):
        """Text without PII should be unchanged."""
        text = "This is a normal sentence with no PII."
        result = redact_pii(text)
        assert result == text


class TestInputSanitization:
    """Test input sanitization."""

    def test_sanitize_xss(self):
        """XSS patterns should be escaped."""
        text = "<script>alert('xss')</script>"
        result = sanitize_input(text)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_sanitize_path_traversal(self):
        """Path traversal patterns should be removed."""
        text = "../../../etc/passwd"
        result = sanitize_input(text)
        assert ".." not in result or "../" not in result

    def test_sanitize_null_bytes(self):
        """Null bytes should be removed."""
        text = "hello\x00world"
        result = sanitize_input(text)
        assert "\x00" not in result

    def test_sanitize_clean_text_unchanged(self):
        """Clean text should be minimally changed."""
        text = "Normal entity name"
        result = sanitize_input(text)
        assert "Normal" in result
        assert "entity" in result


class TestInjectionDetection:
    """Test injection attack detection."""

    def test_detect_sql_injection(self):
        """SQL injection patterns should be detected."""
        text = "1'; DROP TABLE users; --"
        threats = detect_injection(text)
        assert "SQL_INJECTION" in threats

    def test_detect_xss(self):
        """XSS patterns should be detected."""
        text = "<script>alert('xss')</script>"
        threats = detect_injection(text)
        assert "XSS" in threats

    def test_detect_path_traversal(self):
        """Path traversal should be detected."""
        text = "../../../etc/passwd"
        threats = detect_injection(text)
        assert "PATH_TRAVERSAL" in threats

    def test_detect_null_byte(self):
        """Null bytes should be detected."""
        text = "hello\x00world"
        threats = detect_injection(text)
        assert "NULL_BYTE" in threats

    def test_no_threats_in_clean_text(self):
        """Clean text should have no threats."""
        text = "This is a normal fraud report"
        threats = detect_injection(text)
        assert len(threats) == 0


class TestFormatValidation:
    """Test format validation for entity types."""

    def test_valid_email(self):
        """Valid emails should pass validation."""
        assert validate_email_format("user@example.com")
        assert validate_email_format("test.user+tag@domain.co.uk")

    def test_invalid_email(self):
        """Invalid emails should fail validation."""
        assert not validate_email_format("not-an-email")
        assert not validate_email_format("@domain.com")
        assert not validate_email_format("user@")

    def test_valid_phone(self):
        """Valid phone numbers should pass validation."""
        assert validate_phone_format("+1234567890")
        assert validate_phone_format("+447123456789")

    def test_invalid_phone(self):
        """Invalid phone numbers should fail validation."""
        assert not validate_phone_format("abc")
        assert not validate_phone_format("")

    def test_valid_domain(self):
        """Valid domains should pass validation."""
        assert validate_domain_format("example.com")
        assert validate_domain_format("sub.domain.co.uk")

    def test_invalid_domain(self):
        """Invalid domains should fail validation."""
        assert not validate_domain_format("-invalid.com")
        assert not validate_domain_format("")

    def test_valid_url(self):
        """Valid URLs should pass validation."""
        assert validate_url_format("https://example.com")
        assert validate_url_format("http://test.org/path")

    def test_invalid_url(self):
        """Invalid URLs should fail validation."""
        assert not validate_url_format("not-a-url")
        assert not validate_url_format("")

    def test_valid_bitcoin_address(self):
        """Valid Bitcoin address should pass validation."""
        assert validate_crypto_address("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "bitcoin")

    def test_valid_ethereum_address(self):
        """Valid Ethereum address should pass validation."""
        assert validate_crypto_address("0x742d35Cc6634C0532925a3b844Bc454e4438f44e", "ethereum")

    def test_invalid_crypto_address(self):
        """Invalid crypto address should fail validation."""
        assert not validate_crypto_address("invalid", "bitcoin")


class TestEncodingEdgeCases:
    """Test encoding edge cases."""

    def test_utf8_text(self):
        """UTF-8 text should not crash redaction."""
        text = "Café résumé naïve 日本語 emoji 🔒"
        result = redact_pii(text)
        assert isinstance(result, str)

    def test_emoji_text(self):
        """Emoji should not crash sanitization."""
        text = "Hello 🌍 world 🎉"
        result = sanitize_input(text)
        assert isinstance(result, str)

    def test_empty_string(self):
        """Empty string should not crash any function."""
        assert redact_pii("") == ""
        assert sanitize_input("") == ""
        assert detect_injection("") == []

    def test_very_long_string(self):
        """Very long string should not crash."""
        text = "x" * 100000
        assert redact_pii(text) == text
        assert isinstance(sanitize_input(text), str)

    def test_null_bytes_in_redaction(self):
        """Null bytes should not crash redaction."""
        text = "hello\x00world@test.com"
        result = redact_pii(text)
        assert isinstance(result, str)
