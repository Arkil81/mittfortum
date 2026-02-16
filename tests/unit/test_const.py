"""Test constants and locale-specific functions."""

import pytest

from custom_components.mittfortum.const import (
    get_api_base_url,
    get_auth_index_value,
    get_cost_unit,
    get_fortum_base_url,
    get_oauth_redirect_uri,
    get_session_url,
    get_time_series_base_url,
    get_trpc_base_url,
)


class TestLocaleSpecificFunctions:
    """Test locale-specific URL and configuration functions."""

    def test_get_fortum_base_url_swedish(self):
        """Test Swedish Fortum base URL."""
        result = get_fortum_base_url("SV")
        assert result == "https://www.fortum.com/se/el"

    def test_get_fortum_base_url_finnish(self):
        """Test Finnish Fortum base URL."""
        result = get_fortum_base_url("FI")
        assert result == "https://www.fortum.com/fi/sahkoa"

    def test_get_fortum_base_url_invalid(self):
        """Test invalid locale raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported locale: DE"):
            get_fortum_base_url("DE")

    def test_get_api_base_url_swedish(self):
        """Test Swedish API base URL."""
        result = get_api_base_url("SV")
        assert result == "https://www.fortum.com/se/el/api"

    def test_get_api_base_url_finnish(self):
        """Test Finnish API base URL."""
        result = get_api_base_url("FI")
        assert result == "https://www.fortum.com/fi/sahkoa/api"

    def test_get_trpc_base_url_swedish(self):
        """Test Swedish tRPC base URL."""
        result = get_trpc_base_url("SV")
        assert result == "https://www.fortum.com/se/el/api/trpc"

    def test_get_trpc_base_url_finnish(self):
        """Test Finnish tRPC base URL."""
        result = get_trpc_base_url("FI")
        assert result == "https://www.fortum.com/fi/sahkoa/api/trpc"

    def test_get_auth_index_value_swedish(self):
        """Test Swedish auth index value."""
        result = get_auth_index_value("SV")
        assert result == "SeB2COGWLogin"

    def test_get_auth_index_value_finnish(self):
        """Test Finnish auth index value."""
        result = get_auth_index_value("FI")
        assert result == "FIB2CLogin"

    def test_get_auth_index_value_invalid(self):
        """Test invalid locale raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported locale: NO"):
            get_auth_index_value("NO")

    def test_get_session_url_swedish(self):
        """Test Swedish session URL."""
        result = get_session_url("SV")
        assert result == "https://www.fortum.com/se/el/api/auth/session"

    def test_get_session_url_finnish(self):
        """Test Finnish session URL."""
        result = get_session_url("FI")
        assert result == "https://www.fortum.com/fi/sahkoa/api/auth/session"

    def test_get_time_series_base_url_swedish(self):
        """Test Swedish time series base URL."""
        result = get_time_series_base_url("SV")
        assert (
            result
            == "https://www.fortum.com/se/el/api/trpc/loggedIn.timeSeries.listTimeSeries"
        )

    def test_get_time_series_base_url_finnish(self):
        """Test Finnish time series base URL."""
        result = get_time_series_base_url("FI")
        assert (
            result
            == "https://www.fortum.com/fi/sahkoa/api/trpc/loggedIn.timeSeries.listTimeSeries"
        )

    def test_get_oauth_redirect_uri_swedish(self):
        """Test Swedish OAuth redirect URI."""
        result = get_oauth_redirect_uri("SV")
        assert result == "https://www.fortum.com/se/el/api/auth/callback/ciamprod"

    def test_get_oauth_redirect_uri_finnish(self):
        """Test Finnish OAuth redirect URI."""
        result = get_oauth_redirect_uri("FI")
        assert result == "https://www.fortum.com/fi/sahkoa/api/auth/callback/ciamprod"

    def test_get_cost_unit_swedish(self):
        """Test Swedish cost unit (SEK)."""
        result = get_cost_unit("SV")
        assert result == "SEK"

    def test_get_cost_unit_finnish(self):
        """Test Finnish cost unit (EUR)."""
        result = get_cost_unit("FI")
        assert result == "EUR"

    def test_get_cost_unit_invalid(self):
        """Test invalid locale raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported locale: DK"):
            get_cost_unit("DK")
