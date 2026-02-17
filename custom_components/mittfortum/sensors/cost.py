"""Cost sensor for MittFortum."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)

from ..const import COST_SENSOR_KEY, get_cost_unit

if TYPE_CHECKING:
    from ..coordinator import MittFortumDataCoordinator
    from ..device import MittFortumDevice

from ..entity import MittFortumEntity


class MittFortumCostSensor(MittFortumEntity, SensorEntity):
    """Cost sensor for MittFortum."""

    def __init__(
        self,
        coordinator: MittFortumDataCoordinator,
        device: MittFortumDevice,
        locale: str,
    ) -> None:
        """Initialize cost sensor."""
        super().__init__(
            coordinator=coordinator,
            device=device,
            entity_key=COST_SENSOR_KEY,
            name="Total Cost",
        )

        self._locale = locale

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        if not self.coordinator.data:  # Empty list
            return 0.0

        data = self.coordinator.data
        assert isinstance(data, list)  # Type narrowing for pyrefly
        cost_values = [item.cost for item in data if item.cost is not None]
        return sum(cost_values, 0.0)

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return get_cost_unit(self._locale)

    @property
    def device_class(self) -> SensorDeviceClass:
        """Return the device class."""
        return SensorDeviceClass.MONETARY

    @property
    def state_class(self) -> SensorStateClass:
        """Return the state class."""
        return SensorStateClass.TOTAL

    @property
    def statistic_id(self) -> str:
        """Return the statistic_id for this sensor.

        This links the sensor to the external statistics we import,
        making it visible in Developer Tools → Statistics.
        """
        return "mittfortum:energy_cost"

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes."""
        if not self.coordinator.data:
            return None

        data = self.coordinator.data
        assert isinstance(data, list)  # Type narrowing for pyrefly
        cost_data = [item for item in data if item.cost is not None]

        # Calculate time range
        earliest_date = data[0].date_time if data else None
        latest_date = data[-1].date_time if data else None

        # Calculate resolution (time between consecutive readings)
        resolution_minutes = None
        if len(data) >= 2:
            time_diff = (data[1].date_time - data[0].date_time).total_seconds() / 60
            resolution_minutes = int(time_diff)

        return {
            "total_records_with_cost": len(cost_data),
            "currency": get_cost_unit(self._locale),
            "earliest_date": earliest_date.isoformat() if earliest_date else None,
            "latest_date": latest_date.isoformat() if latest_date else None,
            "time_range_hours": (
                (latest_date - earliest_date).total_seconds() / 3600
                if earliest_date and latest_date
                else None
            ),
            "resolution_minutes": resolution_minutes,
            "average_cost_per_hour": (
                sum(item.cost for item in cost_data) / len(cost_data)
                if cost_data
                else None
            ),
        }
