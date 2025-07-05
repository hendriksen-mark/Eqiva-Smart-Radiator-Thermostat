"""
Data models for the Eqiva Smart Radiator Thermostat API
"""
from typing import Any


class ThermostatStatus:
    """Data class for thermostat status"""
    def __init__(self, target_heating_cooling_state: int, target_temperature: float,
                 current_heating_cooling_state: int, current_temperature: float,
                 current_relative_humidity: float):
        self.target_heating_cooling_state = target_heating_cooling_state
        self.target_temperature = target_temperature
        self.current_heating_cooling_state = current_heating_cooling_state
        self.current_temperature = current_temperature
        self.current_relative_humidity = current_relative_humidity
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "targetHeatingCoolingState": self.target_heating_cooling_state,
            "targetTemperature": self.target_temperature,
            "currentHeatingCoolingState": self.current_heating_cooling_state,
            "currentTemperature": self.current_temperature,
            "currentRelativeHumidity": self.current_relative_humidity
        }


def create_default_thermostat_status() -> dict[str, Any]:
    """Create default thermostat status"""
    return ThermostatStatus(
        target_heating_cooling_state=0,
        target_temperature=20.0,
        current_heating_cooling_state=0,
        current_temperature=20.0,
        current_relative_humidity=50.0
    ).to_dict()


def calculate_heating_cooling_state(mode: dict[str, Any], valve: int = None) -> int:
    """
    Calculate the current heating/cooling state based on mode and valve position
    Possible return values:
    0 - Off
    1 - Heating
    2 - Cooling (not used in this context)
    """
    if 'OFF' in mode or (valve is not None and valve <= 0):
        return 0  # Off
    elif valve and valve > 0:
        return 1  # Heating
    else:
        # Default to off if no specific conditions are met
        return 0
    #elif valve == 0 and 'MANUAL' in mode:
    #    return 2  # Not actively heating but in manual mode
    #elif 'AUTO' in mode:
    #    return 3  # Auto mode
    #else:
    #    return 1  # Default to heating for manual mode
