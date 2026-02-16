"""Energy consumption sensor for MittFortum."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy

from ..const import ENERGY_SENSOR_KEY

if TYPE_CHECKING:
    from ..coordinator import MittFortumDataCoordinator
    from ..device import MittFortumDevice

from ..entity import MittFortumEntity


class MittFortumEnergySensor(MittFortumEntity, SensorEntity):
    """Energy consumption sensor for MittFortum."""

    def __init__(
        self,
        coordinator: MittFortumDataCoordinator,
        device: MittFortumDevice,
    ) -> None:
        """Initialize energy sensor."""
        super().__init__(
            coordinator=coordinator,
            device=device,
            entity_key=ENERGY_SENSOR_KEY,
            name="Energy Consumption",
        )

    @property
    def native_value(self) -> float | None:
        """Return the cumulative energy consumption.

        This returns the sum of all energy readings in the time range,
        which represents the total energy consumed during that period.
        For HA Energy dashboard integration, this should be the cumulative
        consumption that increases over time.
        """
        if self.coordinator.data is None:
            return None
        if not self.coordinator.data:  # Empty list
            return 0.0

        data = self.coordinator.data
        assert isinstance(data, list)  # Type narrowing for pyrefly

        # Sum all energy values to get cumulative consumption
        energy_values = [float(item.value) for item in data]
        return sum(energy_values, 0.0)

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return UnitOfEnergy.KILO_WATT_HOUR

    @property
    def device_class(self) -> SensorDeviceClass:
        """Return the device class."""
        return SensorDeviceClass.ENERGY

    @property
    def state_class(self) -> SensorStateClass:
        """Return the state class.

        Using TOTAL for periodic consumption readings.
        The value represents the total energy consumed in the time range.
        """
        return SensorStateClass.TOTAL

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes."""
        if not self.coordinator.data:
            return None

        data = self.coordinator.data
        assert isinstance(data, list)  # Type narrowing for pyrefly

        # Calculate time range
        earliest_date = data[0].date_time if data else None
        latest_date = data[-1].date_time if data else None

        # Calculate resolution (time between consecutive readings)
        resolution_minutes = None
        if len(data) >= 2:
            time_diff = (data[1].date_time - data[0].date_time).total_seconds() / 60
            resolution_minutes = int(time_diff)

        return {
            "total_records": len(data),
            "earliest_date": earliest_date.isoformat() if earliest_date else None,
            "latest_date": latest_date.isoformat() if latest_date else None,
            "time_range_hours": (
                (latest_date - earliest_date).total_seconds() / 3600
                if earliest_date and latest_date
                else None
            ),
            "resolution_minutes": resolution_minutes,
            "unit": data[0].unit if data else None,
            "average_consumption_per_hour": (
                sum(float(item.value) for item in data) / len(data)
                if data
                else None
            ),
        }
