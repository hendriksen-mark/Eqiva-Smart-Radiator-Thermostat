import logging
from flask import Flask, request, jsonify
import asyncio
import threading
import time
from eqiva import Thermostat, Temperature, EqivaException
import yaml
import os
from bleak import BleakError  # <-- Use this instead
from typing import Dict, Any, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(message)s"
)

app = Flask(__name__)

STATUS_YAML_PATH: str = os.path.join(os.path.dirname(__file__), "status_store.yaml")

# Store latest status per MAC
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
                status_store = {}  # Ensure it's always a dict if file is empty or invalid
    else:
        status_store = {}  # Ensure it's always a dict if file does not exist

def save_status_store() -> None:
    with open(STATUS_YAML_PATH, "w") as f:
        yaml.safe_dump(status_store, f)

async def poll_status(mac: str) -> None:
    logging.info(f"Polling: Attempting to connect to {mac}")
    thermostat = Thermostat(mac)
    try:
        await thermostat.connect()
        logging.info(f"Polling: Connected to {mac}")  # <-- Add this line
        await thermostat.requestStatus()
        logging.info(f"Polling: Status requested from {mac}")  # <-- Add this line
        mode = thermostat.mode
        valve = thermostat.valve
        temp = thermostat.temperature.valueC

        # Map modes to PHP logic
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
            "currentTemperature": temp
        }
        logging.info(f"Polling: Updated status_store for {mac}: {status_store[mac]}")  # <-- Add this line
    except BleakError as e:
        logging.error(f"Polling: BLE error for {mac}: {e}")  # <-- Show BLE error details
        # Device not found or BLE error, do not update status_store
        raise
    except EqivaException as e:
        logging.error(f"Polling: EqivaException for {mac}: {e}")  # <-- Show Eqiva error details
        # Do not update status_store on error
        pass
    finally:
        try:
            await thermostat.disconnect()
            logging.info(f"Polling: Disconnected from {mac}")  # <-- Add this line
        except Exception as e:
            logging.error(f"Polling: Error disconnecting from {mac}: {e}")  # <-- Add this line

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
            results = loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
            for mac, result in zip(macs_to_poll, results):
                if isinstance(result, Exception):
                    logging.error(f"Polling failed for {mac}: {type(result).__name__}: {result}")
        save_status_store()
        time.sleep(30)  # Poll every 30 seconds

def start_polling() -> None:
    load_status_store()
    t = threading.Thread(target=polling_loop, daemon=True)
    t.start()

@app.route('/<mac>/<request_type>', defaults={'value': None}, methods=['GET'])
@app.route('/<mac>/<request_type>/<value>', methods=['GET'])
def handle(mac: str, request_type: str, value: Optional[str]) -> Any:
    mac = format_mac(mac)
    # Support value from query string if not present in path
    if value is None:
        value = request.args.get("value")
    logging.info(f"Received request: mac={mac}, request_type={request_type}, value={value}")
    if request_type == 'status':
        if mac not in status_store:
            # Add unknown MAC to status_store with default values and return immediately
            status_store[mac] = {
                "targetHeatingCoolingState": 0,
                "targetTemperature": 20.0,
                "currentHeatingCoolingState": 0,
                "currentTemperature": 20.0
            }
            save_status_store()
            logging.info(f"MAC {mac} not found, returning default values.")
            return jsonify(status_store[mac])
        if mac in status_store:
            return jsonify(status_store[mac])
        else:
            logging.error(f"No status available for MAC {mac}")
            return jsonify({"error": "No status available"}), 404
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
        logging.info(f"Set targetHeatingCoolingState for {mac} to {value}: {result}")
        return jsonify(result)
    else:
        logging.error(f"Invalid request: mac={mac}, request_type={request_type}, value={value}")
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
    app.run(host='0.0.0.0', port=5001)
