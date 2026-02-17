"""Test coordinator module."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import homeassistant.util.dt as dt_util
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.mittfortum.api.client import FortumAPIClient
from custom_components.mittfortum.coordinator import MittFortumDataCoordinator
from custom_components.mittfortum.exceptions import APIError
from custom_components.mittfortum.models import ConsumptionData


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    return Mock(spec=HomeAssistant)


@pytest.fixture
def mock_api_client():
    """Create a mock API client."""
    client = AsyncMock(spec=FortumAPIClient)
    # Configure the async mock to return actual data
    test_data = [
        ConsumptionData(value=150.5, unit="kWh", date_time=datetime.now(), cost=25.50)
    ]
    # The coordinator calls get_total_consumption, not get_consumption_data
    client.get_total_consumption.return_value = test_data
    return client


@pytest.fixture
def yesterday_data():
    """Create sample data from yesterday."""
    now = dt_util.now()
    yesterday = (now - timedelta(days=1)).replace(
        hour=21, minute=0, second=0, microsecond=0
    )
    return [
        ConsumptionData(
            value=0.42, unit="kWh", date_time=yesterday.replace(minute=m), cost=0.10
        )
        for m in [0, 15, 30, 45]
    ]


@pytest.fixture
def today_data():
    """Create sample data from today (incomplete)."""
    now = dt_util.now()
    today = now.replace(hour=10, minute=0, second=0, microsecond=0)
    return [
        ConsumptionData(
            value=0.42, unit="kWh", date_time=today.replace(minute=m), cost=0.10
        )
        for m in [0, 15, 30]  # Only 3 records (incomplete)
    ]


@pytest.fixture
def coordinator(mock_hass, mock_api_client):
    """Create a coordinator instance."""
    return MittFortumDataCoordinator(
        hass=mock_hass,
        api_client=mock_api_client,
        statistics_manager=None,  # Don't test statistics in coordinator tests
        locale="FI",
        update_interval=timedelta(minutes=15),
    )


class TestMittFortumDataCoordinator:
    """Test MittFortum data coordinator."""

    async def test_init(self, coordinator, mock_hass, mock_api_client):
        """Test coordinator initialization."""
        assert coordinator.hass == mock_hass
        assert coordinator.api_client == mock_api_client
        assert coordinator.name == "MittFortum"
        assert coordinator.update_interval == timedelta(minutes=15)

    async def test_async_update_data_success(self, coordinator, mock_api_client):
        """Test successful data update."""
        data = await coordinator._async_update_data()

        assert len(data) == 1
        assert abs(data[0].value - 150.5) < 0.01
        assert data[0].unit == "kWh"
        assert abs(data[0].cost - 25.50) < 0.01
        mock_api_client.get_total_consumption.assert_called_once()

    async def test_async_update_data_authentication_error(
        self, coordinator, mock_api_client
    ):
        """Test data update with authentication error."""
        mock_api_client.get_total_consumption.side_effect = APIError("Auth failed")

        with pytest.raises(UpdateFailed) as exc_info:
            await coordinator._async_update_data()

        assert "API error" in str(exc_info.value)

    async def test_async_update_data_api_error(self, coordinator, mock_api_client):
        """Test data update with API error."""
        mock_api_client.get_total_consumption.side_effect = APIError("API error")

        with pytest.raises(UpdateFailed) as exc_info:
            await coordinator._async_update_data()

        assert "API error" in str(exc_info.value)

    async def test_async_update_data_unexpected_error(
        self, coordinator, mock_api_client
    ):
        """Test data update with unexpected error."""
        mock_api_client.get_total_consumption.side_effect = Exception(
            "Unexpected error"
        )

        with pytest.raises(UpdateFailed) as exc_info:
            await coordinator._async_update_data()

        assert "Unexpected error" in str(exc_info.value)

    async def test_async_update_data_empty_response(self, coordinator, mock_api_client):
        """Test data update with empty response."""
        mock_api_client.get_total_consumption.return_value = []

        data = await coordinator._async_update_data()
        assert data == []

    async def test_async_update_data_none_response(self, coordinator, mock_api_client):
        """Test data update with None response."""
        mock_api_client.get_total_consumption.return_value = None

        data = await coordinator._async_update_data()
        assert data == []


class TestSmartDailyPolling:
    """Test smart daily polling logic (only fetch after 15:00)."""

    @patch("custom_components.mittfortum.coordinator.dt_util.now")
    async def test_should_not_fetch_before_15_00(
        self, mock_now, coordinator, mock_api_client
    ):
        """Test that data is not fetched before 15:00."""
        # Set time to 14:30 (before 15:00 publication time)
        test_time = datetime(2024, 1, 16, 14, 30, 0)
        mock_now.return_value = test_time.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)

        await coordinator._async_update_data()

        # Should return empty or existing data without calling API
        mock_api_client.get_total_consumption.assert_not_called()

    @patch("custom_components.mittfortum.coordinator.dt_util.now")
    async def test_should_fetch_after_15_00(
        self, mock_now, coordinator, mock_api_client
    ):
        """Test that data IS fetched after 15:00."""
        # Set time to 15:30 (after 15:00 publication time)
        test_time = datetime(2024, 1, 16, 15, 30, 0)
        mock_now.return_value = test_time.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)

        # Create yesterday's data
        yesterday = test_time - timedelta(days=1)
        yesterday_data = [
            ConsumptionData(
                value=0.42,
                unit="kWh",
                date_time=yesterday.replace(
                    hour=21, minute=m, tzinfo=dt_util.DEFAULT_TIME_ZONE
                ),
                cost=0.10,
            )
            for m in [0, 15, 30, 45]
        ]

        mock_api_client.get_total_consumption.return_value = yesterday_data

        await coordinator._async_update_data()

        # Should call API after 15:00
        mock_api_client.get_total_consumption.assert_called_once()

    @patch("custom_components.mittfortum.coordinator.dt_util.now")
    async def test_should_fetch_next_day_after_15_00(
        self, mock_now, coordinator, mock_api_client
    ):
        """Test that data IS fetched again the next day after 15:00."""
        test_time = datetime(2024, 1, 16, 15, 30, 0)

        # Create day 1 yesterday data
        yesterday = test_time - timedelta(days=1)
        day1_yesterday_data = [
            ConsumptionData(
                value=0.42,
                unit="kWh",
                date_time=yesterday.replace(
                    hour=21, minute=m, tzinfo=dt_util.DEFAULT_TIME_ZONE
                ),
                cost=0.10,
            )
            for m in [0, 15, 30, 45]
        ]

        # First fetch on day 1 at 15:30
        mock_now.return_value = test_time.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
        mock_api_client.get_total_consumption.return_value = day1_yesterday_data

        await coordinator._async_update_data()
        assert mock_api_client.get_total_consumption.call_count == 1

        # Next day at 15:30
        test_time = datetime(2024, 1, 17, 15, 30, 0)
        mock_now.return_value = test_time.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)

        # Create day 2 yesterday data
        yesterday = test_time - timedelta(days=1)
        day2_yesterday_data = [
            ConsumptionData(
                value=0.42,
                unit="kWh",
                date_time=yesterday.replace(
                    hour=21, minute=m, tzinfo=dt_util.DEFAULT_TIME_ZONE
                ),
                cost=0.10,
            )
            for m in [0, 15, 30, 45]
        ]
        mock_api_client.get_total_consumption.return_value = day2_yesterday_data

        # Should fetch again on new day
        await coordinator._async_update_data()
        assert mock_api_client.get_total_consumption.call_count == 2

    @patch("custom_components.mittfortum.coordinator.dt_util.now")
    async def test_has_previous_day_data_detection(self, mock_now, coordinator):
        """Test detection of previous day's data in response."""
        # Mock current time as Jan 16, 2024 at 15:30
        test_time = datetime(2024, 1, 16, 15, 30, 0)
        mock_now.return_value = test_time.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)

        # Create yesterday's data (Jan 15, 2024)
        yesterday = test_time - timedelta(days=1)
        yesterday_data = [
            ConsumptionData(
                value=0.42,
                unit="kWh",
                date_time=yesterday.replace(
                    hour=21, minute=m, tzinfo=dt_util.DEFAULT_TIME_ZONE
                ),
                cost=0.10,
            )
            for m in [0, 15, 30, 45]
        ]

        # Create today's data (Jan 16, 2024)
        today_data = [
            ConsumptionData(
                value=0.42,
                unit="kWh",
                date_time=test_time.replace(
                    hour=10, minute=m, tzinfo=dt_util.DEFAULT_TIME_ZONE
                ),
                cost=0.10,
            )
            for m in [0, 15, 30]
        ]

        # Test with yesterday's data (should return True)
        assert coordinator._has_previous_day_data(yesterday_data)

        # Test with only today's data (should return False)
        assert not coordinator._has_previous_day_data(today_data)

        # Test with empty data
        assert not coordinator._has_previous_day_data([])

    @patch("custom_components.mittfortum.coordinator.dt_util.now")
    async def test_retry_if_no_previous_day_data(
        self, mock_now, coordinator, mock_api_client
    ):
        """Test retry logic when previous day's data not yet available."""
        test_time = datetime(2024, 1, 16, 15, 10, 0)

        # Create today's data (incomplete - no yesterday data yet)
        today_data = [
            ConsumptionData(
                value=0.42,
                unit="kWh",
                date_time=test_time.replace(
                    hour=10, minute=m, tzinfo=dt_util.DEFAULT_TIME_ZONE
                ),
                cost=0.10,
            )
            for m in [0, 15, 30]
        ]

        # Create yesterday's data
        yesterday = test_time - timedelta(days=1)
        yesterday_data = [
            ConsumptionData(
                value=0.42,
                unit="kWh",
                date_time=yesterday.replace(
                    hour=21, minute=m, tzinfo=dt_util.DEFAULT_TIME_ZONE
                ),
                cost=0.10,
            )
            for m in [0, 15, 30, 45]
        ]

        # First fetch at 15:10 - only gets today's data (incomplete)
        mock_now.return_value = test_time.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
        mock_api_client.get_total_consumption.return_value = today_data

        await coordinator._async_update_data()
        assert mock_api_client.get_total_consumption.call_count == 1
        assert coordinator._waiting_for_data  # Still waiting

        # Second fetch at 15:40 (30 min later) - gets yesterday's data
        test_time = datetime(2024, 1, 16, 15, 40, 0)
        mock_now.return_value = test_time.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
        mock_api_client.get_total_consumption.return_value = yesterday_data

        await coordinator._async_update_data()
        assert mock_api_client.get_total_consumption.call_count == 2
        assert not coordinator._waiting_for_data  # Got data

    @patch("custom_components.mittfortum.coordinator.dt_util.now")
    async def test_should_fetch_logic_boundary_conditions(self, mock_now, coordinator):
        """Test _should_fetch_now at exact boundary conditions."""
        # Exactly at 15:00
        test_time = datetime(2024, 1, 16, 15, 0, 0)
        mock_now.return_value = test_time.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
        assert coordinator._should_fetch_now()

        # One minute before 15:00
        test_time = datetime(2024, 1, 16, 14, 59, 0)
        mock_now.return_value = test_time.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
        assert not coordinator._should_fetch_now()

        # Midnight
        test_time = datetime(2024, 1, 16, 0, 0, 0)
        mock_now.return_value = test_time.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
        assert not coordinator._should_fetch_now()

        # Late at night (23:59)
        test_time = datetime(2024, 1, 16, 23, 59, 0)
        mock_now.return_value = test_time.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
        assert coordinator._should_fetch_now()  # Should still fetch if haven't today
