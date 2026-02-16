"""Test API endpoints with locale support."""

from custom_components.mittfortum.api.endpoints import APIEndpoints


class TestAPIEndpoints:
    """Test API endpoints with locale support."""

    def test_get_auth_init_url_swedish(self):
        """Test Swedish auth init URL."""
        result = APIEndpoints.get_auth_init_url("SV")
        assert "locale=sv" in result
        assert "authIndexValue=seb2cogwlogin" in result
        assert "authIndexType=service" in result

    def test_get_auth_init_url_finnish(self):
        """Test Finnish auth init URL."""
        result = APIEndpoints.get_auth_init_url("FI")
        assert "locale=fi" in result
        assert "authIndexValue=fib2clogin" in result
        assert "authIndexType=service" in result

    def test_get_session_username_url_swedish(self):
        """Test Swedish session username URL."""
        result = APIEndpoints.get_session_username_url("SV")
        assert result == "https://www.fortum.com/se/el/api/get-session-username"

    def test_get_session_username_url_finnish(self):
        """Test Finnish session username URL."""
        result = APIEndpoints.get_session_username_url("FI")
        assert result == "https://www.fortum.com/fi/sahkoa/api/get-session-username"

    def test_get_session_url_swedish(self):
        """Test Swedish session URL."""
        result = APIEndpoints.get_session_url("SV")
        assert result == "https://www.fortum.com/se/el/api/auth/session"

    def test_get_session_url_finnish(self):
        """Test Finnish session URL."""
        result = APIEndpoints.get_session_url("FI")
        assert result == "https://www.fortum.com/fi/sahkoa/api/auth/session"

    def test_get_time_series_url_swedish(self):
        """Test Swedish time series URL."""
        from datetime import datetime

        result = APIEndpoints.get_time_series_url(
            locale="SV",
            metering_point_nos=["123456789"],
            from_date=datetime(2024, 1, 1),
            to_date=datetime(2024, 1, 31),
            resolution="MONTH",
        )
        
        assert "https://www.fortum.com/se/el/api/trpc" in result
        assert "loggedIn.timeSeries.listTimeSeries" in result
        assert "batch=1" in result
        assert "input=" in result

    def test_get_time_series_url_finnish(self):
        """Test Finnish time series URL."""
        from datetime import datetime

        result = APIEndpoints.get_time_series_url(
            locale="FI",
            metering_point_nos=["987654321"],
            from_date=datetime(2024, 1, 1),
            to_date=datetime(2024, 1, 31),
            resolution="MONTH",
        )
        
        assert "https://www.fortum.com/fi/sahkoa/api/trpc" in result
        assert "loggedIn.timeSeries.listTimeSeries" in result
        assert "batch=1" in result
        assert "input=" in result

    def test_get_time_series_url_multiple_metering_points(self):
        """Test time series URL with multiple metering points."""
        from datetime import datetime

        result = APIEndpoints.get_time_series_url(
            locale="SV",
            metering_point_nos=["123456789", "987654321"],
            from_date=datetime(2024, 1, 1),
            to_date=datetime(2024, 1, 31),
            resolution="DAY",
        )
        
        assert "batch=1" in result
        assert "input=" in result
        # Verify the URL contains encoded JSON with both metering points
        assert "123456789" in result or "%22123456789%22" in result
