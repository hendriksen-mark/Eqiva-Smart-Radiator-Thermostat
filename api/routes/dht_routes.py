"""
DHT sensor related routes
"""
from flask import Blueprint, request, jsonify
from typing import Any
import logManager

from ..services import dht_service

logging = logManager.logger.get_logger(__name__)

dht_bp = Blueprint('dht', __name__)


@dht_bp.route('/dht/<int:pin>', methods=['GET'])
@dht_bp.route('/dht', methods=['GET'])
def get_dht(pin: int | None = None) -> Any:
    """
    Return the latest DHT temperature and humidity.
    If pin is provided, set the DHT pin. If not, use current pin.
    If values are not available, return HTTP 503.
    """
    # Handle pin parameter - from URL path or query parameter
    if pin is None:
        pin = request.args.get("pin", type=int)
    
    if pin is not None:
        dht_service.set_pin(pin)
    
    # If no pin is set at all, return default values
    if dht_service.get_pin() is None:
        logging.warning("DHT_PIN is not set, returning default values.")
        return jsonify({
            "temperature": 22.0,  # Default temperature
            "humidity": 50.0,     # Default humidity
            "warning": "DHT sensor not configured"
        }), 200

    # Get current sensor values
    temp, hum = dht_service.get_data()
    
    if temp is None or hum is None:
        logging.warning("DHT sensor data not available, returning default values")
        return jsonify({
            "temperature": 22.0,  # Default temperature
            "humidity": 50.0,     # Default humidity
            "warning": "DHT sensor data not available"
        }), 200
    
    logging.info(f"Returning DHT data")
    logging.debug(f"Temperature: {temp}°C, Humidity: {hum}%, Pin: {dht_service.get_pin()}")
    
    return jsonify({
        "temperature": temp,
        "humidity": hum,
        "pin": dht_service.get_pin()
    }), 200
