"""Eqiva Smart Radiator Thermostat Python package.

A Python library and CLI for controlling Eqiva Smart Radiator Thermostat via Bluetooth LE.
"""

from .utils import (
    Thermostat,
    ThermostatController,
    ThermostatCLI,
    Temperature,
    Mode,
    Program,
    Vacation,
    OpenWindowConfig,
    Alias,
    EqivaException
)

def main():
    """Main entry point for the eqiva CLI."""
    ThermostatCLI()

__version__ = "1.0.0"
__author__ = "Mark Hendriksen"

__all__ = [
    'Thermostat',
    'ThermostatController',
    'ThermostatCLI', 
    'Temperature',
    'Mode',
    'Program',
    'Vacation',
    'OpenWindowConfig',
    'Alias',
    'EqivaException',
    'main'
]
