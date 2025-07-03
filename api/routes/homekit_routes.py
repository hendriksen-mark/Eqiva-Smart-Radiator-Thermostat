"""
HomeKit/Homebridge compatible routes
"""
from flask import Blueprint, request, jsonify
from bleak import BleakError
from typing import Any
import logManager

from ..config import Config
from ..services import thermostat_service, dht_service
from ..utils import validate_mac_address, format_mac, async_route

logging = logManager.logger.get_logger(__name__)

homekit_bp = Blueprint('homekit', __name__)


@homekit_bp.route('/<mac>/<int:dht_pin>/status', methods=['GET'])
def get_homekit_status(mac: str, dht_pin: int) -> Any:
    """
    Get thermostat status in HomeKit format
    URL: /MAC_ADDRESS/DHT_PIN/status
    """
    if not validate_mac_address(mac):
        return jsonify({"error": "Invalid MAC address format"}), 400
    
    mac = format_mac(mac)
    if dht_pin:
        dht_service.set_pin(dht_pin)
    
    status = thermostat_service.get_status(mac)
    
    # Return HomeKit compatible format
    response = {
        "targetHeatingCoolingState": status["targetHeatingCoolingState"],
        "targetTemperature": status["targetTemperature"],
        "currentHeatingCoolingState": status["currentHeatingCoolingState"],
        "currentTemperature": status["currentTemperature"]
    }
    
    # Add humidity if available
    if status.get("currentRelativeHumidity") is not None:
        response["currentRelativeHumidity"] = status["currentRelativeHumidity"]
    
    logging.info(f"Returning status for {mac}")
    logging.debug(f"Status response: {response}")
    return jsonify(response), 200


@homekit_bp.route('/<mac>/<int:dht_pin>/targetTemperature', methods=['GET'])
@async_route
async def set_homekit_target_temperature(mac: str, dht_pin: int) -> Any:
    """
    Set target temperature via HomeKit format
    URL: /MAC_ADDRESS/DHT_PIN/targetTemperature?value=FLOAT_VALUE
    """
    if not validate_mac_address(mac):
        return jsonify({"error": "Invalid MAC address format"}), 400
    
    mac = format_mac(mac)
    if dht_pin:
        dht_service.set_pin(dht_pin)
    
    # Get temperature value from query parameter
    temp_value = request.args.get('value')
    if not temp_value:
        return jsonify({"error": "Temperature value is required as 'value' parameter"}), 400
    
    try:
        temperature = float(temp_value)
        if not (Config.MIN_TEMPERATURE <= temperature <= Config.MAX_TEMPERATURE):
            return jsonify({
                "error": f"Temperature must be between {Config.MIN_TEMPERATURE}°C and {Config.MAX_TEMPERATURE}°C"
            }), 400
    except ValueError:
        return jsonify({"error": "Invalid temperature value"}), 400
    
    try:
        result = await thermostat_service.set_temperature(mac, str(temperature))
        logging.info(f"HomeKit: Set targetTemperature for {mac} to {temperature}: {result}")
        
        if result["result"] == "ok":
            return jsonify({"success": True, "temperature": temperature}), 200
        else:
            return jsonify(result), 400
            
    except BleakError:
        logging.error(f"Device with address {mac} was not found")
        return jsonify({"error": f"Device with address {mac} was not found"}), 404


@homekit_bp.route('/<mac>/<int:dht_pin>/targetHeatingCoolingState', methods=['GET'])
@async_route
async def set_homekit_target_heating_cooling_state(mac: str, dht_pin: int) -> Any:
    """
    Set target heating/cooling state via HomeKit format
    URL: /MAC_ADDRESS/DHT_PIN/targetHeatingCoolingState?value=INT_VALUE
    """
    if not validate_mac_address(mac):
        return jsonify({"error": "Invalid MAC address format"}), 400
    
    mac = format_mac(mac)
    if dht_pin:
        dht_service.set_pin(dht_pin)
    
    # Get mode value from query parameter
    mode_value = request.args.get('value')
    if not mode_value:
        return jsonify({"error": "Mode value is required as 'value' parameter"}), 400
    
    if mode_value not in ['0', '1', '2', '3']:
        return jsonify({"error": "Mode must be 0 (off), 1 (heat), 2 (cool), or 3 (auto)"}), 400
    
    try:
        result = await thermostat_service.set_mode(mac, mode_value)
        logging.info(f"HomeKit: Set targetHeatingCoolingState for {mac} to {mode_value}: {result}")
        
        if result["result"] == "ok":
            return jsonify({"success": True, "mode": int(mode_value)}), 200
        else:
            return jsonify(result), 400
            
    except BleakError:
        logging.error(f"Device with address {mac} was not found")
        return jsonify({"error": f"Device with address {mac} was not found"}), 404
