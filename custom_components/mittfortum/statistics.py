"""Statistics management for MittFortum integration."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import (
    StatisticData,
    StatisticMetaData,
    async_add_external_statistics,
    get_last_statistics,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .models import ConsumptionData

_LOGGER = logging.getLogger(__name__)


class MittFortumStatisticsManager:
    """Manage statistics for MittFortum integration."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialize statistics manager."""
        self.hass = hass
        self.entry_id = entry_id

        # Statistics IDs for external statistics (format: domain:id)
        # Use simple, safe IDs that don't contain special characters
        self.energy_statistic_id = "mittfortum:energy_consumption"
        self.cost_statistic_id = "mittfortum:energy_cost"

    async def async_import_statistics(
        self,
        consumption_data: list[ConsumptionData],
        locale: str,
    ) -> None:
        """Import consumption data as statistics.

        This allows Home Assistant's Energy Dashboard to properly track
        consumption over time with 15-minute granularity.
        """
        if not consumption_data:
            _LOGGER.debug("No consumption data to import")
            return

        # Get the last statistics to determine starting point
        last_energy_stats = await get_instance(self.hass).async_add_executor_job(
            get_last_statistics,
            self.hass,
            1,
            self.energy_statistic_id,
            True,
            {"sum"},
        )

        last_cost_stats = await get_instance(self.hass).async_add_executor_job(
            get_last_statistics,
            self.hass,
            1,
            self.cost_statistic_id,
            True,
            {"sum"},
        )

        # Determine the last imported timestamp
        last_energy_time = None
        last_energy_sum: float = 0.0
        if self.energy_statistic_id in last_energy_stats:
            last_stat = last_energy_stats[self.energy_statistic_id][0]
            last_energy_time = datetime.fromtimestamp(last_stat["start"], tz=UTC)
            last_energy_sum = float(last_stat.get("sum") or 0.0)

        last_cost_time = None
        last_cost_sum: float = 0.0
        if self.cost_statistic_id in last_cost_stats:
            last_stat = last_cost_stats[self.cost_statistic_id][0]
            last_cost_time = datetime.fromtimestamp(last_stat["start"], tz=UTC)
            last_cost_sum = float(last_stat.get("sum") or 0.0)

        _LOGGER.debug(
            "Last energy statistics: time=%s, sum=%.2f kWh",
            last_energy_time,
            last_energy_sum,
        )
        _LOGGER.debug(
            "Last cost statistics: time=%s, sum=%.2f",
            last_cost_time,
            last_cost_sum,
        )

        # Filter out data we've already imported
        new_energy_data = [
            item
            for item in consumption_data
            if last_energy_time is None or item.date_time >= last_energy_time
        ]

        new_cost_data = [
            item
            for item in consumption_data
            if (last_cost_time is None or item.date_time >= last_cost_time)
            and item.cost is not None
        ]

        if not new_energy_data and not new_cost_data:
            _LOGGER.debug("No new statistics to import")
            return

        _LOGGER.info(
            "Importing %d new energy statistics and %d cost statistics",
            len(new_energy_data),
            len(new_cost_data),
        )

        # Import energy statistics
        if new_energy_data:
            await self._import_energy_statistics(new_energy_data, last_energy_sum)

        # Import cost statistics
        if new_cost_data:
            await self._import_cost_statistics(new_cost_data, last_cost_sum, locale)

    async def _import_energy_statistics(
        self,
        consumption_data: list[ConsumptionData],
        last_sum: float,
    ) -> None:
        """Import energy consumption statistics."""
        from collections import defaultdict

        # Aggregate 15-minute data into hourly buckets
        # HA statistics require timestamps at the top of the hour
        hourly_data: dict[datetime, float] = defaultdict(float)
        hourly_counts: dict[datetime, int] = defaultdict(int)

        for item in consumption_data:
            # Round down to the start of the hour
            hour_start = item.date_time.replace(minute=0, second=0, microsecond=0)
            hourly_data[hour_start] += item.value
            hourly_counts[hour_start] += 1

        # Validate that we have complete hours (4 records for 15-min data)
        # Only import hours with complete data to prevent partial sums
        incomplete_hours = [hour for hour, count in hourly_counts.items() if count < 4]
        if incomplete_hours:
            _LOGGER.warning(
                "Found %d incomplete hours with less than 4 15-minute records. "
                "These will be skipped: %s",
                len(incomplete_hours),
                [h.isoformat() for h in sorted(incomplete_hours)],
            )
            # Remove incomplete hours from import
            for hour in incomplete_hours:
                del hourly_data[hour]

        # Build statistics data with cumulative sums
        statistics = []
        cumulative_sum = last_sum

        # Sort by time to ensure correct cumulative calculation
        for hour_start in sorted(hourly_data.keys()):
            hourly_value = hourly_data[hour_start]
            cumulative_sum += hourly_value

            # Convert datetime to UTC timestamp
            start_time = hour_start.replace(tzinfo=UTC)

            statistics.append(
                {
                    "start": start_time,
                    "state": hourly_value,  # Energy consumed in this hour
                    "sum": cumulative_sum,  # Cumulative energy
                }
            )

        # Define metadata for the statistics
        metadata: StatisticMetaData = {
            "source": "mittfortum",
            "name": "Energy Consumption",
            "statistic_id": self.energy_statistic_id,
            "unit_of_measurement": "kWh",
            "has_mean": False,
            "has_sum": True,
        }

        # Import into HA statistics database
        async_add_external_statistics(
            self.hass,
            metadata,
            cast(list[StatisticData], statistics),
        )

        _LOGGER.info(
            "Imported %d hourly energy statistics "
            "(aggregated from %d 15-min records, cumulative: %.2f kWh)",
            len(statistics),
            len(consumption_data),
            cumulative_sum,
        )

    async def _import_cost_statistics(
        self,
        consumption_data: list[ConsumptionData],
        last_sum: float,
        locale: str,
    ) -> None:
        """Import cost statistics (aggregated to hourly)."""
        from collections import defaultdict

        from .const import get_cost_unit

        # Aggregate 15-minute data into hourly buckets
        hourly_data: dict[datetime, float] = defaultdict(float)

        for item in consumption_data:
            if item.cost is None:
                continue

            # Round timestamp to the start of the hour (minutes and seconds = 0)
            hour_start = item.date_time.replace(minute=0, second=0, microsecond=0)
            hourly_data[hour_start] += item.cost

        if not hourly_data:
            _LOGGER.debug("No cost data to import after filtering")
            return

        # Build statistics from hourly aggregated data
        statistics = []
        cumulative_sum = last_sum

        for hour_start in sorted(hourly_data.keys()):
            cumulative_sum += hourly_data[hour_start]

            # Convert datetime to UTC timestamp
            start_time = hour_start.replace(tzinfo=UTC)

            statistics.append(
                {
                    "start": start_time,
                    "state": hourly_data[hour_start],  # Cost in this hour
                    "sum": cumulative_sum,  # Cumulative cost
                }
            )

        # Define metadata for the statistics
        metadata: StatisticMetaData = {
            "source": "mittfortum",
            "name": "Total Cost",
            "statistic_id": self.cost_statistic_id,
            "unit_of_measurement": get_cost_unit(locale),
            "has_mean": False,
            "has_sum": True,
        }

        # Import into HA statistics database
        async_add_external_statistics(
            self.hass,
            metadata,
            cast(list[StatisticData], statistics),
        )

        _LOGGER.info(
            "Imported %d hourly cost statistics "
            "(aggregated from %d 15-min records, cumulative: %.2f %s)",
            len(statistics),
            len(consumption_data),
            cumulative_sum,
            get_cost_unit(locale),
        )
