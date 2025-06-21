import logging
from flask import Flask, request, jsonify
import asyncio
import threading
import time
from utils.Thermostat import Thermostat
from utils.Temperature import Temperature
from utils.EqivaException import EqivaException
import yaml
import os
from bleak import BleakError
from typing import Dict, Any, Optional
from threading import Lock
try:
    import Adafruit_DHT  # type: ignore
except ImportError:
    class DummyDHT:
        DHT22 = None

        @staticmethod
        def read_retry(sensor, pin):
            return 22.0, 50.0
    Adafruit_DHT = DummyDHT()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(lineno)d - %(levelname)s - %(message)s'
)

app = Flask(__name__)

latest_temperature: Optional[float] = None
latest_humidity: Optional[float] = None
dht_lock = Lock()

sensor = Adafruit_DHT.DHT22
DHT_PIN = 24

STATUS_YAML_PATH: str = os.path.join(os.path.dirname(__file__), "status_store.yaml")
HOST_HTTP_PORT: int = 5002

status_store: Dict[str, Dict[str, Any]] = {}

def format_mac(mac: str) -> str:
    return mac.replace('-', ':').upper()

def load_status_store() -> None:
    global status_store
    if os.path.exists(STATUS_YAML_PATH):
        with open(STATUS_YAML_PATH, "r") as f:
            data = yaml.safe_load(f)
            if isinstance(data, dict):
                status_store = data
            else:
                status_store = {}
    else:
        status_store = {}

def save_status_store() -> None:
    with open(STATUS_YAML_PATH, "w") as f:
        yaml.safe_dump(status_store, f)

def read_dht_temperature() -> None:
    """
    Continuously read the temperature and humidity from the DHT sensor
    and update the global variables every 5 seconds.
    If the sensor returns invalid values (None or out of range), do not update globals.
    """
    global latest_temperature, latest_humidity
    while True:
        try:
            humidity, temperature = Adafruit_DHT.read_retry(sensor, DHT_PIN)
            logging.debug(f"Raw DHT read: temperature={temperature}, humidity={humidity}")
            with dht_lock:
                # Only update if values are valid
                if temperature is not None and -40.0 < temperature < 80.0:
                    latest_temperature = float(temperature)
                    logging.debug(f"Updated latest_temperature: {latest_temperature}")
                else:
                    logging.debug("Temperature value not updated (None or out of range)")
                if humidity is not None and 0.0 <= humidity <= 100.0:
                    latest_humidity = float(humidity)
                    logging.debug(f"Updated latest_humidity: {latest_humidity}")
                else:
                    logging.debug("Humidity value not updated (None or out of range)")
        except Exception as e:
            logging.error(f"Error reading DHT sensor: {e}")
        time.sleep(5)

@app.route('/dht', methods=['GET'])
def get_dht() -> Any:
    """
    Return the latest DHT temperature and humidity.
    If values are not available, return HTTP 503.
    """
    with dht_lock:
        temp = latest_temperature
        hum = latest_humidity
    if temp is None or hum is None:
        return jsonify({"error": "DHT sensor data not available"}), 503
    return jsonify({
        "temperature": temp,
        "humidity": hum
    })

async def poll_status(mac: str) -> None:
    logging.info(f"Polling: Attempting to connect to {mac}")
    thermostat = Thermostat(mac)
    try:
        await thermostat.connect()
        logging.info(f"Polling: Connected to {mac}")
        await thermostat.requestStatus()
        logging.info(f"Polling: Status requested from {mac}")
        mode = thermostat.mode
        valve = thermostat.valve
        temp = thermostat.temperature.valueC

        global latest_temperature, latest_humidity
        with dht_lock:
            current_temp = latest_temperature if latest_temperature is not None else temp
            current_hum = latest_humidity if latest_humidity is not None else 50.0

        if mode == 'off':
            mode_status = 0
        elif valve and valve > 0:
            mode_status = 1
        elif valve == 0:
            mode_status = 2
        else:
            mode_status = 3 if mode == 'auto' else 1

        status_store[mac] = {
            "targetHeatingCoolingState": 3 if mode == 'auto' else (1 if mode == 'manual' else 0),
            "targetTemperature": temp,
            "currentHeatingCoolingState": mode_status,
            "currentTemperature": current_temp,
            "currentRelativeHumidity": current_hum
        }
        logging.info(
            f"Polling: Updated status_store for {mac}: {status_store[mac]}")
    except BleakError as e:
        logging.error(f"Polling: BLE error for {mac}: {e}")
        raise
    except EqivaException as e:
        logging.error(f"Polling: EqivaException for {mac}: {e}")
        pass
    finally:
        try:
            await thermostat.disconnect()
            logging.info(f"Polling: Disconnected from {mac}")
        except Exception as e:
            logging.error(f"Polling: Error disconnecting from {mac}: {e}")

def polling_loop() -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    while True:
        load_status_store()
        macs_to_poll = list(status_store.keys())
        logging.info(f"Polling MACs: {macs_to_poll}")
        if not macs_to_poll:
            logging.info("Polling: No MACs to poll, sleeping.")
        tasks = [poll_status(mac) for mac in macs_to_poll]
        if tasks:
            results = loop.run_until_complete(
                asyncio.gather(*tasks, return_exceptions=True))
            for mac, result in zip(macs_to_poll, results):
                if isinstance(result, Exception):
                    logging.error(
                        f"Polling failed for {mac}: {type(result).__name__}: {result}")
        save_status_store()
        time.sleep(30)

def start_polling() -> None:
    """
    Start background threads for polling thermostats and reading DHT sensor.
    Prevent duplicate threads if called multiple times.
    """
    load_status_store()
    if not hasattr(start_polling, "_started"):
        threading.Thread(target=polling_loop, daemon=True).start()
        threading.Thread(target=read_dht_temperature, daemon=True).start()
        start_polling._started = True

@app.route('/<mac>/<request_type>', defaults={'value': None}, methods=['GET'])
@app.route('/<mac>/<request_type>/<value>', methods=['GET'])
def handle(mac: str, request_type: str, value: Optional[str]) -> Any:
    mac = format_mac(mac)
    if value is None:
        value = request.args.get("value")
    logging.info(
        f"Received request: mac={mac}, request_type={request_type}, value={value}")
    if request_type == 'status':
        if mac not in status_store:
            status_store[mac] = {
                "targetHeatingCoolingState": 0,
                "targetTemperature": 20.0,
                "currentHeatingCoolingState": 0,
                "currentTemperature": 20.0,
                "currentRelativeHumidity": 50.0
            }
            save_status_store()
            logging.info(f"MAC {mac} not found, returning default values.")
        return jsonify(status_store[mac])
    elif request_type == 'targetTemperature' and value:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(set_temperature(mac, value))
        except BleakError:
            logging.error(f"Device with address {mac} was not found")
            return jsonify({"result": "error", "message": f"Device with address {mac} was not found"}), 404
        logging.info(f"Set targetTemperature for {mac} to {value}: {result}")
        return jsonify(result)
    elif request_type == 'targetHeatingCoolingState' and value:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(set_mode(mac, value))
        except BleakError:
            logging.error(f"Device with address {mac} was not found")
            return jsonify({"result": "error", "message": f"Device with address {mac} was not found"}), 404
        logging.info(
            f"Set targetHeatingCoolingState for {mac} to {value}: {result}")
        return jsonify(result)
    else:
        logging.error(
            f"Invalid request: mac={mac}, request_type={request_type}, value={value}")
        return jsonify({"error": "Invalid request"}), 400

async def set_temperature(mac: str, temp: str) -> Dict[str, Any]:
    thermostat = Thermostat(mac)
    try:
        logging.info(f"Set temperature for {mac} to {temp}")
        await thermostat.connect()
        await thermostat.setTemperature(temperature=Temperature(valueC=float(temp)))
        return {"result": "ok"}
    except BleakError:
        logging.error(f"Device with address {mac} was not found")
        return {"result": "error", "message": f"Device with address {mac} was not found"}
    except EqivaException as ex:
        logging.error(f"EqivaException for {mac}: {str(ex)}")
        return {"result": "error", "message": str(ex)}
    finally:
        try:
            await thermostat.disconnect()
        except Exception as e:
            logging.error(f"Error disconnecting from {mac}: {e}")

async def set_mode(mac: str, mode: str) -> Dict[str, Any]:
    thermostat = Thermostat(mac)
    try:
        await thermostat.connect()
        if mode == '0':
            await thermostat.setTemperatureOff()
        elif mode in ('1', '2'):
            await thermostat.setModeManual()
        elif mode == '3':
            await thermostat.setModeAuto()
        logging.info(f"Set mode for {mac} to {mode}")
        return {"result": "ok"}
    except BleakError:
        logging.error(f"Device with address {mac} was not found")
        return {"result": "error", "message": f"Device with address {mac} was not found"}
    except EqivaException as ex:
        logging.error(f"EqivaException for {mac}: {str(ex)}")
        return {"result": "error", "message": str(ex)}
    finally:
        try:
            await thermostat.disconnect()
        except Exception as e:
            logging.error(f"Error disconnecting from {mac}: {e}")

if __name__ == '__main__':
    start_polling()
    app.run(host='0.0.0.0', port=HOST_HTTP_PORT)
