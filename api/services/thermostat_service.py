"""
Thermostat service for managing thermostat operations
"""
import asyncio
import yaml
import os
from time import sleep, localtime, strftime
from threading import Lock, Thread
from typing import Any
from bleak import BleakError

from utils.Thermostat import Thermostat
from utils.Temperature import Temperature
from utils.EqivaException import EqivaException
import logManager

from ..config import Config
from ..models import calculate_heating_cooling_state, create_default_thermostat_status

logging = logManager.logger.get_logger(__name__)


class ThermostatService:
    """Service for managing thermostat operations"""
    
    def __init__(self):
        self.status_store: dict[str, dict[str, any]] = {}
        self.connected_thermostats: set[Thermostat] = set()
        self.connected_thermostats_lock = Lock()
        self.status_yaml_path = Config.STATUS_YAML_PATH
        self._polling_started = False
        self.failed_connections: set[str] = set()  # Track MACs that have failed connections
    
    def _get_dht_service(self):
        from .dht_service import dht_service
        return dht_service
    
    def load_status_store(self) -> None:
        """Load status store from YAML file"""
        if os.path.exists(self.status_yaml_path):
            with open(self.status_yaml_path, "r") as f:
                data = yaml.safe_load(f)
                if isinstance(data, dict):
                    # Load thermostats data
                    self.status_store = data.get("thermostats", {})
                    # Load DHT pin configuration
                    dht_config = data.get("dht_config", {})
                    if "pin" in dht_config and dht_config["pin"] is not None:
                        self._get_dht_service().set_pin(int(dht_config["pin"]))
                        logging.debug(f"Loaded DHT_PIN from config: {dht_config['pin']}")
                else:
                    self.status_store = {}
        else:
            self.status_store = {}
    
    def save_status_store(self) -> None:
        """Save status store to YAML file"""
        data = {
            "thermostats": self.status_store,
            "dht_config": {
                "pin": self._get_dht_service().get_pin(),
                "last_updated": strftime("%Y-%m-%d %H:%M:%S", localtime())
            }
        }
        with open(self.status_yaml_path, "w") as f:
            yaml.safe_dump(data, f)

    def update_dht_related_status(self, **kwargs) -> None:
        """Update DHT-related status for all MAC addresses"""
        if not self.status_store:
            return

        current_temp = kwargs.get('temperature')
        current_hum = kwargs.get('humidity')

        for mac in self.status_store:
            thermostat_status = self.status_store[mac]
            if current_temp is not None:
                thermostat_status["currentTemperature"] = current_temp
            if current_hum is not None:
                thermostat_status["currentRelativeHumidity"] = current_hum

        logging.debug(f"Updated DHT status for {len(self.status_store)} thermostats: temp={current_temp}°C, humidity={current_hum}%")

    def get_status(self, mac: str) -> dict[str, Any]:
        """Get thermostat status for a given MAC address"""
        if mac not in self.status_store:
            self.status_store[mac] = create_default_thermostat_status()
            self.save_status_store()
            logging.info(f"MAC {mac} not found, created default status.")
        return self.status_store[mac]
    
    def get_all_status(self) -> dict[str, Any]:
        """Get all thermostat status and system information"""
        temp, humidity = self._get_dht_service().get_data()
        
        message = {
            "thermostats": self.status_store,
            "dht": {
                "pin": self._get_dht_service().get_pin(),
                "temperature": temp,
                "humidity": humidity,
                "active": self._get_dht_service().get_pin() is not None
            }
        }
        
        try:
            from ..utils import get_pi_temp
            message["pi_temp"] = get_pi_temp()
        except RuntimeError:
            message["pi_temp"] = None
            
        return message
    
    async def safe_connect(self, thermostat: Thermostat) -> None:
        """Safely connect to thermostat"""
        await thermostat.connect()
        with self.connected_thermostats_lock:
            self.connected_thermostats.add(thermostat)
    
    async def safe_disconnect(self, thermostat: Thermostat) -> None:
        """Safely disconnect from thermostat"""
        try:
            await thermostat.disconnect()
        except (TimeoutError, asyncio.CancelledError) as e:
            logging.warning(f"Disconnect timeout/cancelled for {thermostat.address}: {e}")
        except Exception as e:
            logging.error(f"Error disconnecting from {thermostat.address}: {e}")
        with self.connected_thermostats_lock:
            self.connected_thermostats.discard(thermostat)
    
    async def poll_status(self, mac: str) -> None:
        """Poll thermostat status"""
        logging.debug(f"Polling: Attempting to connect to {mac}")
        thermostat = Thermostat(mac)
        try:
            await self.safe_connect(thermostat)
            
            # Check if this MAC was previously failing and log recovery
            if mac in self.failed_connections:
                self.failed_connections.remove(mac)
                logging.info(f"Connection recovered for {mac}")
            
            logging.debug(f"Polling: Connected to {mac}")
            await thermostat.requestStatus()
            logging.debug(f"Polling: Status requested from {mac}")
            mode = thermostat.mode.to_dict()
            valve = thermostat.valve
            temp = thermostat.temperature.valueC

            current_temp, current_hum = self._get_dht_service().get_data()
            if current_temp is None:
                current_temp = temp
            if current_hum is None:
                current_hum = 50.0

            mode_status = calculate_heating_cooling_state(mode, valve)

            new_status = {
                "targetHeatingCoolingState": 3 if 'AUTO' in mode else (1 if 'MANUAL' in mode else 0),
                "targetTemperature": temp,
                "currentHeatingCoolingState": mode_status,
                "currentTemperature": current_temp,
                "currentRelativeHumidity": current_hum
            }
            
            # Only update and log if the status has changed (excluding last_updated field)
            if mac not in self.status_store:
                # First time seeing this MAC
                self.status_store[mac] = new_status.copy()
                self.status_store[mac]["last_updated"] = strftime("%Y-%m-%d %H:%M:%S", localtime())
                self.save_status_store()
                logging.info(f"Polling: New thermostat {mac}: {self.status_store[mac]}")
            else:
                # Compare only the thermostat data, not the last_updated timestamp or environmental data
                current_status = {k: v for k, v in self.status_store[mac].items() if k not in ["last_updated", "currentTemperature", "currentRelativeHumidity"]}
                new_status_comparable = {k: v for k, v in new_status.items() if k not in ["currentTemperature", "currentRelativeHumidity"]}
                if current_status != new_status_comparable:
                    self.status_store[mac] = new_status.copy()
                    self.status_store[mac]["last_updated"] = strftime("%Y-%m-%d %H:%M:%S", localtime())
                    self.save_status_store()
                    logging.info(f"Polling: Status changed for {mac}: {self.status_store[mac]}")
                else:
                    logging.debug(f"Polling: No status change for {mac}, skipping update")
        except BleakError as e:
            self.failed_connections.add(mac)  # Track this MAC as failed
            logging.error(f"Polling: BLE error for {mac}: {e}")
            raise
        except EqivaException as e:
            self.failed_connections.add(mac)  # Track this MAC as failed
            logging.error(f"Polling: EqivaException for {mac}: {e}")
            pass
        finally:
            try:
                await self.safe_disconnect(thermostat)
                logging.debug(f"Polling: Disconnected from {mac}")
            except Exception as e:
                logging.error(f"Polling: Error disconnecting from {mac}: {e}")
    
    def _polling_loop(self) -> None:
        """Main polling loop"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        while True:
            macs_to_poll = list(self.status_store.keys())
            logging.debug(f"Polling MACs: {macs_to_poll}")
            if not macs_to_poll:
                logging.debug("Polling: No MACs to poll, sleeping.")
            tasks = [self.poll_status(mac) for mac in macs_to_poll]
            if tasks:
                results = loop.run_until_complete(
                    asyncio.gather(*tasks, return_exceptions=True))
                for mac, result in zip(macs_to_poll, results):
                    if isinstance(result, Exception):
                        logging.error(
                            f"Polling failed for {mac}: {type(result).__name__}: {result}")
            sleep(Config.get_current_polling_interval())
    
    def start_polling(self) -> None:
        """Start background polling thread"""
        self.load_status_store()
        if not self._polling_started:
            Thread(target=self._polling_loop, daemon=True).start()
            self._polling_started = True
            logging.info(f"Started thermostat polling thread with {len(self.status_store)} thermostats")

    async def set_temperature(self, mac: str, temp: str) -> dict[str, Any]:
        """Set thermostat target temperature"""
        thermostat = Thermostat(mac)
        try:
            logging.info(f"Set temperature for {mac} to {temp}")
            await self.safe_connect(thermostat)
            await thermostat.setTemperature(temperature=Temperature(valueC=float(temp)))
            self.status_store[mac]["targetTemperature"] = float(temp)
            self.save_status_store()
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
                await self.safe_disconnect(thermostat)
            except Exception as e:
                logging.error(f"Error disconnecting from {mac}: {e}")
    
    async def set_mode(self, mac: str, mode: str) -> dict[str, Any]:
        """Set thermostat heating/cooling mode"""
        thermostat = Thermostat(mac)
        try:
            await self.safe_connect(thermostat)
            if mode == '0':
                await thermostat.setTemperatureOff()
            elif mode in ('1', '2'):
                await thermostat.setModeManual()
            elif mode == '3':
                await thermostat.setModeAuto()
            else:
                return {"result": "error", "message": "Invalid mode value"}
                
            self.status_store[mac]["targetHeatingCoolingState"] = 3 if mode == '3' else (1 if mode in ('1', '2') else 0)
            self.save_status_store()
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
                await self.safe_disconnect(thermostat)
            except Exception as e:
                logging.error(f"Error disconnecting from {mac}: {e}")
    
    def cleanup_thermostats(self) -> None:
        """Cleanup all connected thermostats"""
        logging.info("Cleanup: Disconnecting all thermostats before exit...")
        
        # Save current status before cleanup
        try:
            logging.info("Cleanup: Saving current status to file...")
            self.save_status_store()
            logging.info("Cleanup: Status saved successfully.")
        except Exception as e:
            logging.error(f"Cleanup: Error saving status: {e}")
        
        with self.connected_thermostats_lock:
            thermostats = list(self.connected_thermostats)
        
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
                    task = asyncio.wait_for(self.safe_disconnect(thermostat), timeout=5.0)
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


# Global thermostat service instance
thermostat_service = ThermostatService()
