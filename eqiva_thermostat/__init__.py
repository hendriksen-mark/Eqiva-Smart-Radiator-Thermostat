"""Eqiva Smart Radiator Thermostat Python package.

A Python library and CLI for controlling Eqiva Smart Radiator Thermostat via Bluetooth LE.
"""

from .utils import (
    Alias,
    EqivaException,
    Event,
    Listener,
    Mode,
    MyLogger,
    OpenWindowConfig,
    Program,
    Temperature,
    Thermostat,
    ThermostatCLI,
    ThermostatController,
    Vacation,
)

def main():
    """Main entry point for the eqiva CLI."""
    ThermostatCLI()

__version__ = "1.0.3"
__author__ = "Heckie"
__maintainer__ = "Mark Hendriksen"

__all__ = [
    'Alias',
    'EqivaException',
    'Event',
    'Listener',
    'main',
    'Mode',
    'MyLogger',
    'OpenWindowConfig',
    'Program',
    'Temperature',
    'Thermostat',
    'ThermostatCLI',
    'ThermostatController',
    'Vacation'
]
