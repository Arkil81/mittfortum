"""Unit tests for utility functions."""

import pytest

from custom_components.mittfortum.utils import (
    extract_customer_id_from_token,
    format_currency,
    format_energy,
    safe_get_nested,
)


class TestUtils:
    """Test utility functions."""

    def test_extract_customer_id_from_valid_token(self):
        """Test extracting customer ID from valid JWT token."""
        # Use jwt library to create a proper token
        import jwt

        payload = {"customerid": [{"crmid": "12345"}]}
        token = jwt.encode(payload, "secret", algorithm="HS256")

        result = extract_customer_id_from_token(token)
        assert result == "12345"

    def test_extract_customer_id_from_invalid_token(self):
        """Test error handling for invalid token."""
        # JWT DecodeError should be caught and wrapped as ValueError
        with pytest.raises(ValueError, match="Failed to extract customer ID"):
            extract_customer_id_from_token("invalid")

    def test_extract_customer_id_missing_customerid(self):
        """Test error handling for token missing customerid field."""
        import jwt

        payload = {"user": "test"}  # Missing customerid
        token = jwt.encode(payload, "secret", algorithm="HS256")

        with pytest.raises(ValueError, match="Failed to extract customer ID"):
            extract_customer_id_from_token(token)

    def test_safe_get_nested_success(self):
        """Test safely getting nested dictionary values."""
        data = {"user": {"profile": {"name": "John"}}}
        result = safe_get_nested(data, "user", "profile", "name")
        assert result == "John"

    def test_safe_get_nested_missing_key(self):
        """Test safe_get_nested returns default for missing keys."""
        data = {"user": {}}
        result = safe_get_nested(data, "user", "profile", "name", default="Unknown")
        assert result == "Unknown"

    def test_safe_get_nested_none_default(self):
        """Test safe_get_nested returns None by default."""
        data = {"user": {}}
        result = safe_get_nested(data, "user", "profile", "name")
        assert result is None

    def test_safe_get_nested_non_dict_value(self):
        """Test safe_get_nested handles non-dict values."""
        data = {"user": "string_value"}
        result = safe_get_nested(data, "user", "profile", default="fallback")
        assert result == "fallback"

    def test_format_currency_swedish(self):
        """Test currency formatting for Swedish locale."""
        result = format_currency(123.45, "SEK")
        assert result == "123.45 SEK"

    def test_format_currency_finnish(self):
        """Test currency formatting for Finnish locale."""
        result = format_currency(99.99, "EUR")
        assert result == "99.99 EUR"

    def test_format_currency_norwegian(self):
        """Test currency formatting for Norwegian locale."""
        result = format_currency(250.50, "NOK")
        assert result == "250.50 NOK"

    def test_format_currency_none(self):
        """Test currency formatting with None value."""
        result = format_currency(None, "EUR")
        assert result == "0.00 EUR"

    def test_format_currency_zero(self):
        """Test currency formatting with zero value."""
        result = format_currency(0.0, "SEK")
        assert result == "0.00 SEK"

    def test_format_currency_large_amount(self):
        """Test currency formatting with large amount."""
        result = format_currency(12345678.90, "SEK")
        assert result == "12345678.90 SEK"

    def test_format_energy(self):
        """Test energy amount formatting."""
        result = format_energy(1234.56, "kWh")
        assert result == "1234.56 kWh"

    def test_format_energy_default_unit(self):
        """Test energy formatting with default unit."""
        result = format_energy(500.25)
        assert result == "500.25 kWh"

    def test_format_energy_none(self):
        """Test energy formatting with None value."""
        result = format_energy(None)
        assert result == "0.00 kWh"

    def test_format_energy_zero(self):
        """Test energy formatting with zero value."""
        result = format_energy(0.0)
        assert result == "0.00 kWh"

    def test_format_energy_mwh(self):
        """Test energy formatting with MWh unit."""
        result = format_energy(1.234, "MWh")
        assert result == "1.23 MWh"
