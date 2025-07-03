"""
Utility functions for the API
"""
import asyncio
from functools import wraps
import subprocess
from typing import Any, Callable


def async_route(f: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to handle async functions in Flask routes"""
    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(f(*args, **kwargs))
        finally:
            loop.close()
    return wrapper


def validate_mac_address(mac: str) -> bool:
    """Validate MAC address format"""
    if not mac:
        return False
    formatted_mac = format_mac(mac)
    # Basic MAC validation - should be 6 groups of 2 hex digits
    parts = formatted_mac.split(':')
    if len(parts) != 6:
        return False
    for part in parts:
        if len(part) != 2 or not all(c in '0123456789ABCDEF' for c in part):
            return False
    return True


def format_mac(mac: str) -> str:
    """Format MAC address to standard format"""
    return mac.replace('-', ':').upper()


def get_pi_temp() -> float:
    """Read the CPU temperature and return it as a float in degrees Celsius."""
    try:
        output = subprocess.run(['vcgencmd', 'measure_temp'], capture_output=True, check=True)
        temp_str = output.stdout.decode()
        return float(temp_str.split('=')[1].split('\'')[0])
    except (IndexError, ValueError, subprocess.CalledProcessError, FileNotFoundError):
        raise RuntimeError('Could not get temperature')
