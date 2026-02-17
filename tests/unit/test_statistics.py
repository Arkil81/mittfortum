"""Tests for statistics import functionality."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.mittfortum.models import ConsumptionData
from custom_components.mittfortum.statistics import MittFortumStatisticsManager


@pytest.fixture
def mock_hass_with_recorder():
    """Mock Home Assistant instance with recorder."""
    hass = MagicMock()
    hass.states = MagicMock()
    hass.data = {"recorder_instance": MagicMock()}
    # Make async_add_executor_job work as an async function
    hass.async_add_executor_job = AsyncMock(side_effect=lambda func, *args: func(*args))
    return hass


# Mock the recorder functions at module level
@pytest.fixture(autouse=True)
def mock_recorder_functions():
    """Mock recorder functions."""
    with (
        patch(
            "custom_components.mittfortum.statistics.get_last_statistics",
            return_value={},
        ) as mock_get_last,
        patch(
            "custom_components.mittfortum.statistics.async_add_external_statistics",
            new_callable=AsyncMock,
        ) as mock_add_stats,
        patch(
            "custom_components.mittfortum.statistics.get_instance"
        ) as mock_get_instance,
    ):
        # Configure get_instance to return a recorder instance mock
        recorder_instance = MagicMock()
        recorder_instance.async_add_executor_job = AsyncMock(
            side_effect=lambda func, *args: func(*args)
        )
        mock_get_instance.return_value = recorder_instance
        yield {
            "get_last": mock_get_last,
            "add_stats": mock_add_stats,
            "get_instance": mock_get_instance,
        }


@pytest.fixture
def statistics_manager(mock_hass_with_recorder):
    """Create statistics manager."""
    return MittFortumStatisticsManager(
        hass=mock_hass_with_recorder,
        entry_id="test_entry",
    )


@pytest.fixture
def complete_hour_data():
    """Create complete hour of 15-minute data (4 records)."""
    base_time = datetime(2024, 1, 15, 21, 0, 0, tzinfo=UTC)
    return [
        ConsumptionData(
            date_time=base_time,  # 21:00
            value=0.42,
            cost=0.10,
            unit="kWh",
        ),
        ConsumptionData(
            date_time=base_time.replace(minute=15),  # 21:15
            value=0.44,
            cost=0.11,
            unit="kWh",
        ),
        ConsumptionData(
            date_time=base_time.replace(minute=30),  # 21:30
            value=0.43,
            cost=0.10,
            unit="kWh",
        ),
        ConsumptionData(
            date_time=base_time.replace(minute=45),  # 21:45
            value=0.45,
            cost=0.11,
            unit="kWh",
        ),
    ]


@pytest.fixture
def incomplete_hour_data():
    """Create incomplete hour of 15-minute data (only 3 records)."""
    base_time = datetime(2024, 1, 15, 20, 0, 0, tzinfo=UTC)
    return [
        ConsumptionData(
            date_time=base_time.replace(minute=15),  # 20:15 (missing 20:00!)
            value=0.44,
            cost=0.11,
            unit="kWh",
        ),
        ConsumptionData(
            date_time=base_time.replace(minute=30),  # 20:30
            value=0.43,
            cost=0.10,
            unit="kWh",
        ),
        ConsumptionData(
            date_time=base_time.replace(minute=45),  # 20:45
            value=0.45,
            cost=0.11,
            unit="kWh",
        ),
    ]


@pytest.fixture
def multiple_hours_data():
    """Create multiple complete hours of 15-minute data."""
    base_time = datetime(2024, 1, 15, 21, 0, 0, tzinfo=UTC)
    data = []

    # Hour 21:00-22:00 (complete)
    for minute in [0, 15, 30, 45]:
        data.append(
            ConsumptionData(
                date_time=base_time.replace(minute=minute),
                value=0.42 + minute * 0.01,
                cost=0.10,
                unit="kWh",
            )
        )

    # Hour 22:00-23:00 (complete)
    for minute in [0, 15, 30, 45]:
        data.append(
            ConsumptionData(
                date_time=base_time.replace(hour=22, minute=minute),
                value=0.40 + minute * 0.01,
                cost=0.10,
                unit="kWh",
            )
        )

    # Hour 23:00-00:00 (complete)
    for minute in [0, 15, 30, 45]:
        data.append(
            ConsumptionData(
                date_time=base_time.replace(hour=23, minute=minute),
                value=0.38 + minute * 0.01,
                cost=0.09,
                unit="kWh",
            )
        )

    return data


class TestStatisticsFilterLogic:
    """Test the filter logic that caused the original bug."""

    async def test_filter_includes_boundary_timestamp(
        self,
        mock_recorder_functions,
        statistics_manager,
        complete_hour_data,
    ):
        """Test that filter includes records at exact boundary time (>= not >)."""
        # Last imported statistics was at 21:00:00
        last_time = datetime(2024, 1, 15, 21, 0, 0, tzinfo=UTC)

        # get_last_statistics returns a dict where statistic_id maps to list of stats
        mock_recorder_functions["get_last"].return_value = {
            statistics_manager.energy_statistic_id: [
                {"start": last_time.timestamp(), "sum": 100.0}
            ],
            statistics_manager.cost_statistic_id: [
                {"start": last_time.timestamp(), "sum": 25.0}
            ],
        }

        # New data starts at 21:00:00 (same as last_time)
        # With >= filter, all 4 records should be included
        # With > filter, first record would be excluded (BUG!)
        await statistics_manager.async_import_statistics(
            complete_hour_data, locale="FI"
        )

        # Should be called twice (energy and cost)
        mock_add_stats = mock_recorder_functions["add_stats"]
        assert mock_add_stats.call_count == 2

        # Check energy statistics call
        energy_call = mock_add_stats.call_args_list[0]
        energy_stats = energy_call[0][2]  # Third argument is the statistics list

        # With correct >= filter, we should get 1 complete hour
        assert len(energy_stats) == 1
        # Sum should be all 4 values: 0.42 + 0.44 + 0.43 + 0.45 = 1.74 kWh
        hourly_value = energy_stats[0]["state"]
        assert abs(hourly_value - 1.74) < 0.01, f"Expected 1.74 kWh, got {hourly_value}"

    async def test_filter_with_no_previous_stats(
        self,
        mock_recorder_functions,
        statistics_manager,
        complete_hour_data,
    ):
        """Test filter when no previous statistics exist."""
        # No previous stats - return empty dicts
        mock_recorder_functions["get_last"].return_value = {}

        await statistics_manager.async_import_statistics(
            complete_hour_data, locale="FI"
        )

        # Should import all 4 records into 1 hour
        mock_add_stats = mock_recorder_functions["add_stats"]
        assert mock_add_stats.call_count == 2
        energy_call = mock_add_stats.call_args_list[0]
        energy_stats = energy_call[0][2]
        assert len(energy_stats) == 1


class TestHourCompletenessValidation:
    """Test hour completeness validation (4 records per hour)."""

    async def test_complete_hour_imported(
        self,
        mock_recorder_functions,
        statistics_manager,
        complete_hour_data,
    ):
        """Test that complete hours (4 records) are imported."""
        mock_recorder_functions["get_last"].return_value = {}

        await statistics_manager.async_import_statistics(
            complete_hour_data, locale="FI"
        )

        # Should successfully import 1 complete hour
        mock_add_stats = mock_recorder_functions["add_stats"]
        assert mock_add_stats.call_count == 2
        energy_call = mock_add_stats.call_args_list[0]
        energy_stats = energy_call[0][2]
        assert len(energy_stats) == 1
        assert energy_stats[0]["state"] == pytest.approx(1.74, abs=0.01)

    async def test_incomplete_hour_skipped(
        self,
        mock_recorder_functions,
        statistics_manager,
        incomplete_hour_data,
    ):
        """Test that incomplete hours (< 4 records) are skipped."""
        mock_recorder_functions["get_last"].return_value = {}

        await statistics_manager.async_import_statistics(
            incomplete_hour_data, locale="FI"
        )

        # Incomplete hour should be skipped - no statistics imported
        # Function may still be called but with empty list
        mock_add_stats = mock_recorder_functions["add_stats"]
        if mock_add_stats.call_count > 0:
            energy_call = mock_add_stats.call_args_list[0]
            energy_stats = energy_call[0][2]
            assert len(energy_stats) == 0

    async def test_mixed_complete_incomplete_hours(
        self,
        mock_recorder_functions,
        statistics_manager,
        complete_hour_data,
        incomplete_hour_data,
    ):
        """Test mix of complete and incomplete hours - only complete imported."""
        mock_recorder_functions["get_last"].return_value = {}

        # Mix complete and incomplete data
        mixed_data = incomplete_hour_data + complete_hour_data

        await statistics_manager.async_import_statistics(mixed_data, locale="FI")

        # Only the complete hour should be imported
        mock_add_stats = mock_recorder_functions["add_stats"]
        assert mock_add_stats.call_count == 2
        energy_call = mock_add_stats.call_args_list[0]
        energy_stats = energy_call[0][2]
        assert len(energy_stats) == 1  # Only complete hour


class TestStatisticsAggregation:
    """Test aggregation of 15-minute data into hourly statistics."""

    async def test_hourly_aggregation_accuracy(
        self,
        mock_recorder_functions,
        statistics_manager,
        complete_hour_data,
    ):
        """Test that 15-minute values are correctly summed into hourly totals."""
        mock_recorder_functions["get_last"].return_value = {}

        await statistics_manager.async_import_statistics(
            complete_hour_data, locale="FI"
        )

        mock_add_stats = mock_recorder_functions["add_stats"]
        energy_call = mock_add_stats.call_args_list[0]
        energy_stats = energy_call[0][2]

        # Verify sum: 0.42 + 0.44 + 0.43 + 0.45 = 1.74
        assert energy_stats[0]["state"] == pytest.approx(1.74, abs=0.01)

    async def test_multiple_hours_aggregation(
        self,
        mock_recorder_functions,
        statistics_manager,
        multiple_hours_data,
    ):
        """Test aggregation of multiple complete hours."""
        mock_recorder_functions["get_last"].return_value = {}

        await statistics_manager.async_import_statistics(
            multiple_hours_data, locale="FI"
        )

        mock_add_stats = mock_recorder_functions["add_stats"]
        energy_call = mock_add_stats.call_args_list[0]
        energy_stats = energy_call[0][2]

        # Should have 3 complete hours
        assert len(energy_stats) == 3

    async def test_cumulative_sum_calculation(
        self,
        mock_recorder_functions,
        statistics_manager,
        multiple_hours_data,
    ):
        """Test that cumulative sums are correctly calculated."""
        # Start with existing sum of 100 kWh
        last_time = datetime(2024, 1, 15, 20, 0, 0, tzinfo=UTC)
        mock_recorder_functions["get_last"].return_value = {
            statistics_manager.energy_statistic_id: [
                {"start": last_time.timestamp(), "sum": 100.0}
            ],
            statistics_manager.cost_statistic_id: [
                {"start": last_time.timestamp(), "sum": 25.0}
            ],
        }

        await statistics_manager.async_import_statistics(
            multiple_hours_data, locale="FI"
        )

        mock_add_stats = mock_recorder_functions["add_stats"]
        energy_call = mock_add_stats.call_args_list[0]
        energy_stats = energy_call[0][2]

        # Verify cumulative sum increases with each hour
        assert len(energy_stats) == 3
        prev_sum = 100.0
        for stat in energy_stats:
            current_sum = stat["sum"]
            assert current_sum > prev_sum
            prev_sum = current_sum


class TestStatisticsMetadata:
    """Test statistics metadata and identifiers."""

    def test_statistic_ids(self, statistics_manager):
        """Test that statistic IDs are correctly formatted."""
        assert statistics_manager.energy_statistic_id == "mittfortum:energy_consumption"
        assert statistics_manager.cost_statistic_id == "mittfortum:energy_cost"

    async def test_metadata_structure(
        self,
        mock_recorder_functions,
        statistics_manager,
        complete_hour_data,
    ):
        """Test that statistics metadata is correctly structured."""
        mock_recorder_functions["get_last"].return_value = {}

        await statistics_manager.async_import_statistics(
            complete_hour_data, locale="FI"
        )

        # Check energy metadata
        mock_add_stats = mock_recorder_functions["add_stats"]
        energy_call = mock_add_stats.call_args_list[0]
        energy_metadata = energy_call[0][1]
        assert energy_metadata["source"] == "mittfortum"
        assert energy_metadata["statistic_id"] == "mittfortum:energy_consumption"
        assert "unit_of_measurement" in energy_metadata
