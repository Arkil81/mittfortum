"""Data update coordinator for MittFortum integration."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta  # noqa: TC003
from typing import TYPE_CHECKING

import homeassistant.util.dt as dt_util
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DATA_PUBLICATION_TIME, DATA_RETRY_INTERVAL, DEFAULT_UPDATE_INTERVAL
from .exceptions import APIError
from .models import ConsumptionData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .api import FortumAPIClient
    from .statistics import MittFortumStatisticsManager

_LOGGER = logging.getLogger(__name__)


class MittFortumDataCoordinator(DataUpdateCoordinator[list[ConsumptionData]]):
    """Data update coordinator for MittFortum."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_client: FortumAPIClient,
        statistics_manager: MittFortumStatisticsManager | None = None,
        locale: str = "FI",
        update_interval: timedelta = DEFAULT_UPDATE_INTERVAL,
    ) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="MittFortum",
            update_interval=update_interval,
        )
        self.api_client = api_client
        self.statistics_manager = statistics_manager
        self.locale = locale
        self._last_successful_fetch: datetime | None = None
        self._waiting_for_data = False

    async def _async_update_data(self) -> list[ConsumptionData]:
        """Fetch data from API with smart daily scheduling.

        Fortum publishes previous day's complete data around 15:00 the next day.
        We only attempt to fetch data after 15:00, and retry every 30 minutes
        until we successfully get the previous day's complete dataset.
        """
        # Check if we should fetch data based on time of day
        if not self._should_fetch_now():
            _LOGGER.debug(
                "Skipping data fetch - before daily publication time (15:00) "
                "or already fetched today's data"
            )
            # Return existing data if we have it
            return self.data if self.data else []

        try:
            _LOGGER.debug("Fetching consumption data from API")
            data = await self.api_client.get_total_consumption()
            if data is None:
                data = []
            _LOGGER.debug("Successfully fetched %d consumption records", len(data))

            # Import statistics if we have a statistics manager
            if self.statistics_manager and data:
                try:
                    _LOGGER.debug(
                        "Attempting to import statistics with IDs - "
                        "Energy: %s, Cost: %s",
                        self.statistics_manager.energy_statistic_id,
                        self.statistics_manager.cost_statistic_id,
                    )
                    await self.statistics_manager.async_import_statistics(
                        data, self.locale
                    )
                except Exception as exc:
                    _LOGGER.error(
                        "Failed to import statistics: %s. "
                        "This won't affect sensor operation.",
                        exc,
                        exc_info=True,
                    )

        except APIError as exc:
            # For authentication errors, provide more specific error message
            if (
                "Token expired" in str(exc)
                or "Access forbidden" in str(exc)
                or "Authentication failed" in str(exc)
            ):
                _LOGGER.warning(
                    "Authentication error during data update: %s. "
                    "This may be temporary due to session propagation.",
                    exc,
                )
                raise UpdateFailed(f"Authentication error: {exc}") from exc
            else:
                _LOGGER.exception("API error during data update")
                raise UpdateFailed(f"API error: {exc}") from exc
        except Exception as exc:
            _LOGGER.exception("Unexpected error during data update")
            raise UpdateFailed(f"Unexpected error: {exc}") from exc
        else:
            # Check if we got new data for the previous day
            if data and self._has_previous_day_data(data):
                self._last_successful_fetch = dt_util.now()
                self._waiting_for_data = False
                _LOGGER.info(
                    "Successfully fetched previous day's data at %s",
                    self._last_successful_fetch.strftime("%Y-%m-%d %H:%M"),
                )
            elif self._waiting_for_data:
                _LOGGER.debug(
                    "Previous day's data not yet available, will retry in %d minutes",
                    DATA_RETRY_INTERVAL.total_seconds() / 60,
                )
            return data

    def _should_fetch_now(self) -> bool:
        """Determine if we should fetch data now based on daily schedule.

        Returns:
            True if we should fetch data now, False otherwise.
        """
        now = dt_util.now()

        # Check if we're past the daily publication time (15:00)
        publication_datetime = now.replace(
            hour=DATA_PUBLICATION_TIME.hour,
            minute=DATA_PUBLICATION_TIME.minute,
            second=0,
            microsecond=0,
        )

        if now < publication_datetime:
            # Before 15:00 - don't fetch
            return False

        # After 15:00 - check if we've already successfully fetched today
        if self._last_successful_fetch:
            # If we fetched today after 15:00, don't fetch again
            last_fetch_date = self._last_successful_fetch.date()
            if (
                last_fetch_date == now.date()
                and self._last_successful_fetch >= publication_datetime
            ):
                return False

        # Either haven't fetched today, or last fetch was before 15:00
        # Mark that we're now waiting for data
        self._waiting_for_data = True
        return True

    def _has_previous_day_data(self, data: list[ConsumptionData]) -> bool:
        """Check if the data includes records from the previous day.

        Args:
            data: List of consumption data records

        Returns:
            True if data includes previous day's records, False otherwise.
        """
        if not data:
            return False

        now = dt_util.now()
        yesterday = (now - timedelta(days=1)).date()

        # Check if any records are from yesterday
        yesterday_records = [
            record for record in data if record.date_time.date() == yesterday
        ]

        if yesterday_records:
            _LOGGER.debug(
                "Found %d records from previous day (%s)",
                len(yesterday_records),
                yesterday.isoformat(),
            )
            return True

        return False
