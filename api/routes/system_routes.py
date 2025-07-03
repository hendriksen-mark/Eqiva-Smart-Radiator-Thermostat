"""
System and configuration routes
"""
from flask import Blueprint, request, jsonify
from typing import Any
import logManager

from ..config import Config, update_env_file, reload_env_variables
from ..services import thermostat_service, dht_service
from ..utils import get_pi_temp

logging = logManager.logger.get_logger(__name__)

system_bp = Blueprint('system', __name__)


@system_bp.route('/all', methods=['GET'])
def get_all_status() -> Any:
    """
    Get the status of all thermostats and DHT sensor.
    """
    return jsonify(thermostat_service.get_all_status()), 200


@system_bp.route('/health', methods=['GET'])
def health_check() -> Any:
    """Health check endpoint"""
    temp, humidity = dht_service.get_data()
    
    return jsonify({
        "status": "healthy",
        "version": "1.0.0",
        "thermostats_connected": len(thermostat_service.status_store),
        "dht_sensor_active": dht_service.get_pin() is not None,
        "temperature_available": temp is not None,
        "humidity_available": humidity is not None
    }), 200


@system_bp.route('/api', methods=['GET'])
def api_documentation() -> Any:
    """API documentation"""
    return jsonify({
        "api_version": "1.0.0",
        "description": "Eqiva Smart Radiator Thermostat API - HomeKit Compatible",
        "base_url_example": "http://192.168.1.15:5002/00-1A-22-16-3D-E7/25",
        "url_format": "/{mac_address}/{dht_pin}/{endpoint}",
        "homekit_endpoints": {
            "/{mac}/{dht_pin}/status": {
                "method": "GET",
                "description": "Get thermostat status in HomeKit format",
                "response": {
                    "targetHeatingCoolingState": "INT (0=off, 1=heat, 2=cool, 3=auto)",
                    "targetTemperature": "FLOAT",
                    "currentHeatingCoolingState": "INT",
                    "currentTemperature": "FLOAT",
                    "currentRelativeHumidity": "FLOAT (optional)"
                }
            },
            "/{mac}/{dht_pin}/targetTemperature": {
                "method": "GET",
                "description": "Set target temperature",
                "parameters": {
                    "value": "FLOAT_VALUE (query parameter)"
                },
                "example": "/00-1A-22-16-3D-E7/25/targetTemperature?value=22.5"
            },
            "/{mac}/{dht_pin}/targetHeatingCoolingState": {
                "method": "GET",
                "description": "Set heating/cooling state",
                "parameters": {
                    "value": "INT_VALUE (0=off, 1=heat, 2=cool, 3=auto)"
                },
                "example": "/00-1A-22-16-3D-E7/25/targetHeatingCoolingState?value=3"
            }
        },
        "other_endpoints": {
            "/health": {
                "method": "GET",
                "description": "Health check"
            },
            "/dht": {
                "method": "GET",
                "description": "Get DHT sensor data (current pin)",
                "example": "/dht"
            },
            "/dht/{pin}": {
                "method": "GET",
                "description": "Get DHT sensor data and optionally set pin",
                "parameters": {
                    "pin": "GPIO pin number"
                },
                "response": {
                    "temperature": "FLOAT",
                    "humidity": "FLOAT", 
                    "pin": "INT (current pin)"
                },
                "example": "/dht/25"
            },
            "/pi_temp": {
                "method": "GET", 
                "description": "Get Raspberry Pi CPU temperature"
            },
            "/all": {
                "method": "GET",
                "description": "Get all system status"
            },
            "/config/log-level": {
                "method": "GET",
                "description": "Get current log level",
                "response": {
                    "current_log_level": "STRING",
                    "available_levels": "ARRAY"
                }
            },
            "/config/log-level": {
                "method": "POST",
                "description": "Set log level via JSON body. DEBUG mode enables faster polling (30s vs 300s)",
                "body": {
                    "log_level": "STRING (DEBUG|INFO|WARNING|ERROR|CRITICAL)"
                },
                "example": "POST /config/log-level with {\"log_level\": \"DEBUG\"}",
                "note": "Setting DEBUG automatically reduces polling interval to 30 seconds for faster updates"
            },
            "/config/log-level/{level}": {
                "method": "GET",
                "description": "Set log level via URL parameter. DEBUG mode enables faster polling (30s vs 300s)",
                "parameters": {
                    "level": "STRING (DEBUG|INFO|WARNING|ERROR|CRITICAL)"
                },
                "example": "/config/log-level/DEBUG",
                "note": "Setting DEBUG automatically reduces polling interval to 30 seconds for faster updates"
            }
        },
        "mac_format": "MAC address can use either : or - as separator (e.g., 00:1A:22:16:3D:E7 or 00-1A-22-16-3D-E7)",
        "temperature_range": f"{Config.MIN_TEMPERATURE}°C to {Config.MAX_TEMPERATURE}°C"
    }), 200


@system_bp.route('/api', methods=['OPTIONS'])
@system_bp.route('/api/thermostats/<path:path>', methods=['OPTIONS'])
def handle_options(path: str | None = None) -> Any:
    """Handle CORS preflight requests"""
    return '', 200


def update_log_level(log_level: str) -> dict[str, Any]:
    """
    Update log level configuration and persist to environment file
    Also adjusts polling interval based on debug mode
    Returns response dictionary for API endpoints
    """
    log_level = log_level.upper()
    valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    
    if log_level not in valid_levels:
        return {
            "error": f"Invalid log level: {log_level}",
            "valid_levels": valid_levels,
            "status_code": 400
        }
    
    try:
        # Update the logger configuration
        logManager.logger.configure_logger(log_level)
        
        # Update the environment file to persist the change
        update_env_file('LOG_LEVEL', log_level)
        
        # Adjust polling interval based on debug mode
        if log_level == 'DEBUG':
            # Set faster polling for debug mode (30 seconds)
            polling_interval = 30
            update_env_file('POLLING_INTERVAL', str(polling_interval))
            logging.info(f"Debug mode enabled - polling interval set to {polling_interval} seconds")
        else:
            # Set normal polling for non-debug modes (5 minutes)
            polling_interval = 300
            update_env_file('POLLING_INTERVAL', str(polling_interval))
            logging.info(f"Normal mode - polling interval set to {polling_interval} seconds")
        
        # Reload environment variables to make changes take effect immediately
        reload_env_variables()
        
        logging.info(f"Log level changed to {log_level}")
        return {
            "success": True,
            "message": f"Log level changed to {log_level}, polling interval set to {polling_interval} seconds",
            "new_log_level": log_level,
            "polling_interval": polling_interval,
            "status_code": 200
        }
        
    except Exception as e:
        logging.error(f"Error changing log level: {e}")
        return {
            "error": f"Failed to change log level: {str(e)}",
            "status_code": 500
        }


@system_bp.route('/config/log-level', methods=['GET'])
def get_log_level() -> Any:
    """Get current log level"""
    current_level = logManager.logger.get_level_name()
    return jsonify({
        "current_log_level": current_level,
        "available_levels": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    }), 200


@system_bp.route('/config/log-level', methods=['POST'])
def set_log_level() -> Any:
    """
    Set log level dynamically
    Body: {"log_level": "DEBUG|INFO|WARNING|ERROR|CRITICAL"}
    """
    data = request.get_json()
    if not data or 'log_level' not in data:
        return jsonify({"error": "log_level is required in request body"}), 400
    
    result = update_log_level(data['log_level'])
    status_code = result.pop('status_code', 200)
    return jsonify(result), status_code


@system_bp.route('/config/log-level/<level>', methods=['GET'])
def set_log_level_simple(level: str) -> Any:
    """
    Set log level via URL parameter (simple GET request)
    URL: /config/log-level/DEBUG
    """
    result = update_log_level(level)
    status_code = result.pop('status_code', 200)
    return jsonify(result), status_code

@system_bp.route('/pi_temp', methods=['GET'])
def read_pi_temperature() -> Any:
    """
    Return the Raspberry Pi CPU temperature.
    """
    try:
        temp = get_pi_temp()
        return jsonify({"temperature": temp}), 200
    except RuntimeError as e:
        logging.error(f"Error reading Pi temperature: {e}")
        return jsonify({"error": "Could not read Pi temperature"}), 503


# Legacy route redirects
@system_bp.route('/status', methods=['GET'])
def legacy_status_redirect() -> Any:
    """Redirect legacy /status to /all"""
    from flask import redirect, url_for
    return redirect(url_for('system.get_all_status'))
