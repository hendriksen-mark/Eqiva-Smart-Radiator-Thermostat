import logging
from turtle import st
from flask import Flask, request, jsonify
import asyncio
from time import sleep, localtime
from utils.Thermostat import Thermostat
from utils.Temperature import Temperature
from utils.EqivaException import EqivaException
import yaml
import os
from bleak import BleakError
from typing import Dict, Any, Optional
from threading import Lock, Thread
import signal
import subprocess
from functools import wraps

try:
    import Adafruit_DHT  # type: ignore
except ImportError:
    class DummyDHT:
        DHT22 = None

        @staticmethod
        def read_retry(sensor, pin):
            return 22.0, 50.0
    Adafruit_DHT = DummyDHT()

# Configuration management
class Config:
    """Application configuration"""
    HOST_HTTP_PORT = int(os.getenv('HOST_HTTP_PORT', 5002))
    STATUS_YAML_PATH = os.path.join(os.path.dirname(__file__), "status_store.yaml")
    POLLING_INTERVAL = int(os.getenv('POLLING_INTERVAL', 30))
    DHT_READ_INTERVAL = int(os.getenv('DHT_READ_INTERVAL', 5))
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # Temperature validation ranges
    MIN_TEMPERATURE = 5.0
    MAX_TEMPERATURE = 30.0
    
    # DHT sensor validation ranges
    MIN_DHT_TEMP = -40.0
    MAX_DHT_TEMP = 80.0
    MIN_HUMIDITY = 0.0
    MAX_HUMIDITY = 100.0

# Update logging configuration
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(lineno)d - %(levelname)s - %(message)s'
)

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
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "targetHeatingCoolingState": self.target_heating_cooling_state,
            "targetTemperature": self.target_temperature,
            "currentHeatingCoolingState": self.current_heating_cooling_state,
            "currentTemperature": self.current_temperature,
            "currentRelativeHumidity": self.current_relative_humidity
        }

def async_route(f):
    """Decorator to handle async functions in Flask routes"""
    @wraps(f)
    def wrapper(*args, **kwargs):
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

def create_default_thermostat_status() -> Dict[str, Any]:
    """Create default thermostat status"""
    return ThermostatStatus(
        target_heating_cooling_state=0,
        target_temperature=20.0,
        current_heating_cooling_state=0,
        current_temperature=20.0,
        current_relative_humidity=50.0
    ).to_dict()

app = Flask(__name__)

latest_temperature: Optional[float] = None
latest_humidity: Optional[float] = None
dht_lock = Lock()

sensor = Adafruit_DHT.DHT22
DHT_PIN = None

STATUS_YAML_PATH: str = Config.STATUS_YAML_PATH
HOST_HTTP_PORT: int = Config.HOST_HTTP_PORT

status_store: Dict[str, Dict[str, Any]] = {}
connected_thermostats = set()
connected_thermostats_lock = Lock()

def format_mac(mac: str) -> str:
    return mac.replace('-', ':').upper()

def load_status_store() -> None:
    global status_store, DHT_PIN
    if os.path.exists(STATUS_YAML_PATH):
        with open(STATUS_YAML_PATH, "r") as f:
            data = yaml.safe_load(f)
            if isinstance(data, dict):
                # Load thermostats data
                status_store = data.get("thermostats", {})
                # Load DHT pin configuration
                dht_config = data.get("dht_config", {})
                if "pin" in dht_config and dht_config["pin"] is not None:
                    DHT_PIN = int(dht_config["pin"])
                    logging.info(f"Loaded DHT_PIN from config: {DHT_PIN}")
                else:
                    DHT_PIN = None
            else:
                status_store = {}
                DHT_PIN = None
    else:
        status_store = {}
        DHT_PIN = None

def save_status_store() -> None:
    data = {
        "thermostats": status_store,
        "dht_config": {
            "pin": DHT_PIN,
            "last_updated": localtime()
        }
    }
    with open(STATUS_YAML_PATH, "w") as f:
        yaml.safe_dump(data, f)

def get_PI_temp():
    """Read the CPU temperature and return it as a float in degrees Celsius."""
    try:
        output = subprocess.run(['vcgencmd', 'measure_temp'], capture_output=True, check=True)
        temp_str = output.stdout.decode()
        return float(temp_str.split('=')[1].split('\'')[0])
    except (IndexError, ValueError, subprocess.CalledProcessError, FileNotFoundError):
        raise RuntimeError('Could not get temperature')

@app.route('/pi_temp', methods=['GET'])
def read_pi_temperature() -> Any:
    """
    Return the Raspberry Pi CPU temperature.
    """
    try:
        temp = get_PI_temp()
        return jsonify({"temperature": temp}), 200
    except RuntimeError as e:
        logging.error(f"Error reading Pi temperature: {e}")
        return jsonify({"error": "Could not read Pi temperature"}), 503

def read_dht_temperature() -> None:
    """
    Continuously read the temperature and humidity from the DHT sensor
    and update the global variables every 5 seconds.
    If the sensor returns invalid values (None or out of range), do not update globals.
    """
    global latest_temperature, latest_humidity, DHT_PIN
    while DHT_PIN is not None:
        try:
            humidity, temperature = Adafruit_DHT.read_retry(sensor, DHT_PIN)
            logging.debug(f"Raw DHT read: temperature={temperature}, humidity={humidity}")
            with dht_lock:
                # Only update if values are valid
                if temperature is not None and Config.MIN_DHT_TEMP < temperature < Config.MAX_DHT_TEMP:
                    if latest_temperature is None or latest_temperature != round(float(temperature), 1):
                        latest_temperature = round(float(temperature), 1)
                        logging.info(f"Updated temperature: {latest_temperature}")
                else:
                    logging.error("Temperature value not updated (None or out of range)")
                if humidity is not None and Config.MIN_HUMIDITY <= humidity <= Config.MAX_HUMIDITY:
                    if latest_humidity is None or latest_humidity != round(float(humidity), 1):
                        latest_humidity = round(float(humidity), 1)
                        logging.info(f"Updated humidity: {latest_humidity}")
                else:
                    logging.error("Humidity value not updated (None or out of range)")
        except Exception as e:
            logging.error(f"Error reading DHT sensor: {e}")
        sleep(Config.DHT_READ_INTERVAL)

@app.route('/dht/<pin>', methods=['GET'])
@app.route('/dht', methods=['GET'])
def get_dht(pin: int = None) -> Any:
    """
    Return the latest DHT temperature and humidity.
    If pin is provided, set the DHT pin. If not, use current pin.
    If values are not available, return HTTP 503.
    """
    global DHT_PIN
    
    # Handle pin parameter - from URL path or query parameter
    if pin is None:
        pin = request.args.get("pin", type=int)
    update_dht_pin(int(pin) if pin else None)
    
    # If no pin is set at all, return default values
    if DHT_PIN is None:
        logging.warning("DHT_PIN is not set, returning default values.")
        return jsonify({
            "temperature": 22.0,  # Default temperature
            "humidity": 50.0,     # Default humidity
            "warning": "DHT sensor not configured"
        }), 200

    # Get current sensor values
    global latest_temperature, latest_humidity
    with dht_lock:
        temp = latest_temperature
        hum = latest_humidity
    
    if temp is None or hum is None:
        logging.warning("DHT sensor data not available, returning default values")
        return jsonify({
            "temperature": 22.0,  # Default temperature
            "humidity": 50.0,     # Default humidity
            "warning": "DHT sensor data not available"
        }), 200
    
    logging.debug(f"Returning DHT data: temperature={temp}, humidity={hum}, pin={DHT_PIN}")
    
    return jsonify({
        "temperature": temp,
        "humidity": hum,
        "pin": DHT_PIN
    }), 200

async def safe_connect(thermostat: Thermostat) -> None:
    await thermostat.connect()
    with connected_thermostats_lock:
        connected_thermostats.add(thermostat)

async def safe_disconnect(thermostat: Thermostat) -> None:
    try:
        await thermostat.disconnect()
    except (TimeoutError, asyncio.CancelledError) as e:
        logging.warning(f"Disconnect timeout/cancelled for {thermostat.address}: {e}")
    except Exception as e:
        logging.error(f"Error disconnecting from {thermostat.address}: {e}")
    with connected_thermostats_lock:
        connected_thermostats.discard(thermostat)

async def poll_status(mac: str) -> None:
    logging.debug(f"Polling: Attempting to connect to {mac}")
    thermostat = Thermostat(mac)
    try:
        await safe_connect(thermostat)
        logging.debug(f"Polling: Connected to {mac}")
        await thermostat.requestStatus()
        logging.debug(f"Polling: Status requested from {mac}")
        mode = thermostat.mode.to_dict()
        valve = thermostat.valve
        temp = thermostat.temperature.valueC

        global latest_temperature, latest_humidity
        with dht_lock:
            current_temp = latest_temperature if latest_temperature is not None else temp
            current_hum = latest_humidity if latest_humidity is not None else 50.0

        mode_status = calculate_heating_cooling_state(mode, valve)

        new_status = {
            "targetHeatingCoolingState": 3 if 'AUTO' in mode else (1 if 'MANUAL' in mode else 0),
            "targetTemperature": temp,
            "currentHeatingCoolingState": mode_status,
            "currentTemperature": current_temp,
            "currentRelativeHumidity": current_hum
        }
        
        # Only update and log if the status has changed
        if mac not in status_store or status_store[mac] != new_status:
            status_store[mac] = new_status
            status_store[mac]["last_updated"] = localtime()
            save_status_store()
            logging.info(f"Polling: Status changed for {mac}: {status_store[mac]}")
        else:
            logging.debug(f"Polling: No status change for {mac}, skipping update")
    except BleakError as e:
        logging.error(f"Polling: BLE error for {mac}: {e}")
        raise
    except EqivaException as e:
        logging.error(f"Polling: EqivaException for {mac}: {e}")
        pass
    finally:
        try:
            await safe_disconnect(thermostat)
            logging.debug(f"Polling: Disconnected from {mac}")
        except Exception as e:
            logging.error(f"Polling: Error disconnecting from {mac}: {e}")

def polling_loop() -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    while True:
        macs_to_poll = list(status_store.keys())
        logging.debug(f"Polling MACs: {macs_to_poll}")
        if not macs_to_poll:
            logging.debug("Polling: No MACs to poll, sleeping.")
        tasks = [poll_status(mac) for mac in macs_to_poll]
        if tasks:
            results = loop.run_until_complete(
                asyncio.gather(*tasks, return_exceptions=True))
            for mac, result in zip(macs_to_poll, results):
                if isinstance(result, Exception):
                    logging.error(
                        f"Polling failed for {mac}: {type(result).__name__}: {result}")
        sleep(Config.POLLING_INTERVAL)

def start_polling() -> None:
    """
    Start background threads for polling thermostats and reading DHT sensor.
    Prevent duplicate threads if called multiple times.
    """
    load_status_store()
    if not hasattr(start_polling, "_started"):
        Thread(target=polling_loop, daemon=True).start()
        start_polling._started = True
        logging.info("Started thermostat polling thread")
    
    # Start DHT thread if pin is configured in the loaded config
    if DHT_PIN is not None:
        ensure_dht_thread_running()
        logging.info(f"DHT sensor configured on pin {DHT_PIN} - starting reading thread")

def update_dht_pin(dht_pin: Optional[int]) -> None:
    """Update DHT pin if provided and ensure DHT reading is active"""
    global DHT_PIN
    if dht_pin is not None and DHT_PIN != dht_pin:
        logging.info(f"Setting DHT_PIN to {dht_pin}")
        DHT_PIN = dht_pin
        # Save the updated configuration
        save_status_store()
        # Ensure DHT reading thread is started
        ensure_dht_thread_running()

def ensure_dht_thread_running() -> None:
    """Ensure DHT reading thread is running if DHT_PIN is set"""
    global DHT_PIN
    if DHT_PIN is not None:
        if not hasattr(ensure_dht_thread_running, "_dht_thread_started"):
            Thread(target=read_dht_temperature, daemon=True).start()
            ensure_dht_thread_running._dht_thread_started = True
            logging.info(f"Started DHT reading thread for pin {DHT_PIN}")

# HomeKit/Homebridge compatible routes
@app.route('/<mac>/<dht_pin>/status', methods=['GET'])
def get_homekit_status(mac: str, dht_pin: int) -> Any:
    """
    Get thermostat status in HomeKit format
    URL: /MAC_ADDRESS/DHT_PIN/status
    """
    if not validate_mac_address(mac):
        return jsonify({"error": "Invalid MAC address format"}), 400
    
    mac = format_mac(mac)
    update_dht_pin(int(dht_pin) if dht_pin else None)
    
    if mac not in status_store:
        status_store[mac] = create_default_thermostat_status()
        save_status_store()
        logging.info(f"MAC {mac} not found, created default status.")
    
    # Return HomeKit compatible format
    response = {
        "targetHeatingCoolingState": status_store[mac]["targetHeatingCoolingState"],
        "targetTemperature": status_store[mac]["targetTemperature"],
        "currentHeatingCoolingState": status_store[mac]["currentHeatingCoolingState"],
        "currentTemperature": status_store[mac]["currentTemperature"]
    }
    
    # Add humidity if available
    if status_store[mac].get("currentRelativeHumidity") is not None:
        response["currentRelativeHumidity"] = status_store[mac]["currentRelativeHumidity"]
    
    logging.info(f"Returning status for {mac}: {response}")
    return jsonify(response), 200

@app.route('/<mac>/<dht_pin>/targetTemperature', methods=['GET'])
@async_route
async def set_homekit_target_temperature(mac: str, dht_pin: int) -> Any:
    """
    Set target temperature via HomeKit format
    URL: /MAC_ADDRESS/DHT_PIN/targetTemperature?value=FLOAT_VALUE
    """
    if not validate_mac_address(mac):
        return jsonify({"error": "Invalid MAC address format"}), 400
    
    mac = format_mac(mac)
    update_dht_pin(int(dht_pin) if dht_pin else None)
    
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
        result = await set_temperature(mac, str(temperature))
        logging.info(f"HomeKit: Set targetTemperature for {mac} to {temperature}: {result}")
        
        if result["result"] == "ok":
            return jsonify({"success": True, "temperature": temperature}), 200
        else:
            return jsonify(result), 400
            
    except BleakError:
        logging.error(f"Device with address {mac} was not found")
        return jsonify({"error": f"Device with address {mac} was not found"}), 404

@app.route('/<mac>/<dht_pin>/targetHeatingCoolingState', methods=['GET'])
@async_route
async def set_homekit_target_heating_cooling_state(mac: str, dht_pin: int) -> Any:
    """
    Set target heating/cooling state via HomeKit format
    URL: /MAC_ADDRESS/DHT_PIN/targetHeatingCoolingState?value=INT_VALUE
    """
    if not validate_mac_address(mac):
        return jsonify({"error": "Invalid MAC address format"}), 400
    
    mac = format_mac(mac)
    update_dht_pin(int(dht_pin) if dht_pin else None)
    
    # Get mode value from query parameter
    mode_value = request.args.get('value')
    if not mode_value:
        return jsonify({"error": "Mode value is required as 'value' parameter"}), 400
    
    if mode_value not in ['0', '1', '2', '3']:
        return jsonify({"error": "Mode must be 0 (off), 1 (heat), 2 (cool), or 3 (auto)"}), 400
    
    try:
        result = await set_mode(mac, mode_value)
        logging.info(f"HomeKit: Set targetHeatingCoolingState for {mac} to {mode_value}: {result}")
        
        if result["result"] == "ok":
            return jsonify({"success": True, "mode": int(mode_value)}), 200
        else:
            return jsonify(result), 400
            
    except BleakError:
        logging.error(f"Device with address {mac} was not found")
        return jsonify({"error": f"Device with address {mac} was not found"}), 404

@app.route('/all', methods=['GET'])
def get_all_status():
    """
    Get the status of all thermostats and DHT sensor.
    """
    message = {}
    message["thermostats"] = status_store
    message["dht"] = {
        "pin": DHT_PIN,
        "temperature": latest_temperature,
        "humidity": latest_humidity,
        "active": DHT_PIN is not None
    }
    try:
        message["pi_temp"] = get_PI_temp()
    except RuntimeError:
        message["pi_temp"] = None
    return jsonify(message), 200

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check() -> Any:
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "version": "1.0.0",
        "thermostats_connected": len(status_store),
        "dht_sensor_active": DHT_PIN is not None,
        "temperature_available": latest_temperature is not None,
        "humidity_available": latest_humidity is not None
    }), 200

# API documentation endpoint
@app.route('/api', methods=['GET'])
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
            }
        },
        "mac_format": "MAC address can use either : or - as separator (e.g., 00:1A:22:16:3D:E7 or 00-1A-22-16-3D-E7)",
        "temperature_range": f"{Config.MIN_TEMPERATURE}°C to {Config.MAX_TEMPERATURE}°C"
    }), 200

# Request logging middleware
@app.before_request
def log_request_info():
    logging.debug(f"Request: {request.method} {request.url} from {request.remote_addr}")

@app.after_request
def log_response_info(response):
    logging.debug(f"Response: {response.status_code} for {request.method} {request.url}")
    # Add CORS headers
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route('/api', methods=['OPTIONS'])
@app.route('/api/thermostats/<path:path>', methods=['OPTIONS'])
def handle_options(path=None):
    """Handle CORS preflight requests"""
    return '', 200

# Async thermostat operations
async def set_temperature(mac: str, temp: str) -> Dict[str, Any]:
    """Set thermostat target temperature"""
    thermostat = Thermostat(mac)
    try:
        logging.info(f"Set temperature for {mac} to {temp}")
        await safe_connect(thermostat)
        await thermostat.setTemperature(temperature=Temperature(valueC=float(temp)))
        status_store[mac]["targetTemperature"] = float(temp)
        save_status_store()
        return {"result": "ok", "temperature": float(temp)}
    except BleakError:
        logging.error(f"Device with address {mac} was not found")
        return {"result": "error", "message": f"Device with address {mac} was not found"}
    except EqivaException as ex:
        logging.error(f"EqivaException for {mac}: {str(ex)}")
        return {"result": "error", "message": str(ex)}
    except ValueError as ex:
        logging.error(f"Invalid temperature value for {mac}: {str(ex)}")
        return {"result": "error", "message": "Invalid temperature value"}
    finally:
        try:
            await safe_disconnect(thermostat)
        except Exception as e:
            logging.error(f"Error disconnecting from {mac}: {e}")

async def set_mode(mac: str, mode: str) -> Dict[str, Any]:
    """Set thermostat heating/cooling mode"""
    thermostat = Thermostat(mac)
    try:
        await safe_connect(thermostat)
        if mode == '0':
            await thermostat.setTemperatureOff()
        elif mode in ('1', '2'):
            await thermostat.setModeManual()
        elif mode == '3':
            await thermostat.setModeAuto()
        else:
            return {"result": "error", "message": "Invalid mode value"}
            
        status_store[mac]["targetHeatingCoolingState"] = 3 if mode == '3' else (1 if mode in ('1', '2') else 0)
        save_status_store()
        logging.info(f"Set mode for {mac} to {mode}")
        return {"result": "ok", "mode": int(mode)}
    except BleakError:
        logging.error(f"Device with address {mac} was not found")
        return {"result": "error", "message": f"Device with address {mac} was not found"}
    except EqivaException as ex:
        logging.error(f"EqivaException for {mac}: {str(ex)}")
        return {"result": "error", "message": str(ex)}
    finally:
        try:
            await safe_disconnect(thermostat)
        except Exception as e:
            logging.error(f"Error disconnecting from {mac}: {e}")

# Improved status calculation
def calculate_heating_cooling_state(mode: Dict[str, Any], valve: Optional[int]) -> int:
    """Calculate the current heating/cooling state based on mode and valve position"""
    if 'OFF' in mode:
        return 0  # Off
    elif valve and valve > 0 and 'MANUAL' in mode:
        return 1  # Heating
    elif valve == 0 and 'MANUAL' in mode:
        return 2  # Not actively heating but in manual mode
    elif 'AUTO' in mode:
        return 3  # Auto mode
    else:
        return 1  # Default to heating for manual mode

# Error handlers
@app.errorhandler(400)
def bad_request(error):
    return jsonify({"error": "Bad request", "message": str(error)}), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found", "message": str(error)}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

def cleanup_thermostats():
    logging.info("Cleanup: Disconnecting all thermostats before exit...")
    with connected_thermostats_lock:
        thermostats = list(connected_thermostats)
    
    if not thermostats:
        logging.info("Cleanup: No thermostats to disconnect.")
        return
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def cleanup_all():
        tasks = []
        for thermostat in thermostats:
            try:
                # Create a timeout wrapper for each disconnect
                task = asyncio.wait_for(safe_disconnect(thermostat), timeout=5.0)
                tasks.append(task)
            except Exception as e:
                logging.error(f"Cleanup: Error preparing disconnect for {thermostat.address}: {e}")
        
        if tasks:
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except Exception as e:
                logging.error(f"Cleanup: Error during gather: {e}")
    
    try:
        loop.run_until_complete(cleanup_all())
    except Exception as e:
        logging.error(f"Cleanup: Error during cleanup: {e}")
    finally:
        try:
            loop.close()
        except Exception as e:
            logging.error(f"Cleanup: Error closing loop: {e}")
    
    logging.info("Cleanup: All thermostats disconnected.")

def handle_exit(signum, frame):
    logging.info(f"Received signal {signum}, shutting down gracefully...")
    cleanup_thermostats()
    os._exit(0)

signal.signal(signal.SIGTERM, handle_exit)
signal.signal(signal.SIGINT, handle_exit)

# Legacy route redirects
@app.route('/status', methods=['GET'])
def legacy_status_redirect():
    """Redirect legacy /status to /all"""
    from flask import redirect, url_for
    return redirect(url_for('get_all_status'))

# Backward compatibility: Keep old thermostat routes but mark as deprecated

if __name__ == '__main__':
    start_polling()
    app.run(host='0.0.0.0', port=HOST_HTTP_PORT)
