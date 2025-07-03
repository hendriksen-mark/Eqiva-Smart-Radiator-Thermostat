"""
DHT sensor service for temperature and humidity monitoring
"""
from time import sleep
from threading import Lock, Thread
import logManager

from ..config import Config

logging = logManager.logger.get_logger(__name__)

try:
    import Adafruit_DHT  # type: ignore
except ImportError:
    class DummyDHT:
        DHT22 = None

        @staticmethod
        def read_retry(sensor, pin):
            return 22.0, 50.0
    Adafruit_DHT = DummyDHT()


class DHTService:
    """DHT sensor service for reading temperature and humidity"""
    
    def __init__(self):
        self.sensor = Adafruit_DHT.DHT22
        self.dht_pin: int | None = None
        self.latest_temperature: float | None = None
        self.latest_humidity: float | None = None
        self.dht_lock = Lock()
        self.last_logged_dht_temp: float | None = None
        self.last_logged_dht_humidity: float | None = None
        self._thread_started = False
    
    def set_pin(self, pin: int | None) -> None:
        """Set DHT pin and start reading if not already started"""
        if pin is not None and self.dht_pin != pin:
            logging.info(f"Setting DHT_PIN to {pin}")
            self.dht_pin = pin
            self._ensure_thread_running()
    
    def get_pin(self) -> int | None:
        """Get current DHT pin"""
        return self.dht_pin
    
    def get_data(self) -> tuple[float | None, float | None]:
        """Get current temperature and humidity data"""
        with self.dht_lock:
            return self.latest_temperature, self.latest_humidity
    
    def _ensure_thread_running(self) -> None:
        """Ensure DHT reading thread is running if DHT_PIN is set"""
        if self.dht_pin is not None and not self._thread_started:
            Thread(target=self._read_dht_temperature, daemon=True).start()
            self._thread_started = True
            logging.info(f"Started DHT reading thread for pin {self.dht_pin}")
    
    def _read_dht_temperature(self) -> None:
        """
        Continuously read the temperature and humidity from the DHT sensor
        and update the global variables every 5 seconds.
        If the sensor returns invalid values (None or out of range), do not update globals.
        """
        while self.dht_pin is not None:
            try:
                humidity, temperature = Adafruit_DHT.read_retry(self.sensor, self.dht_pin)
                logging.debug(f"Raw DHT read: temperature={temperature}, humidity={humidity}")
                
                with self.dht_lock:
                    # Only update if values are valid
                    if temperature is not None and Config.MIN_DHT_TEMP < temperature < Config.MAX_DHT_TEMP:
                        rounded_temp = round(float(temperature), 1)
                        if self.latest_temperature != rounded_temp:
                            self.latest_temperature = rounded_temp
                            # Only log when temperature changes significantly or this is the first reading
                            if (self.last_logged_dht_temp is None or 
                                abs(rounded_temp - self.last_logged_dht_temp) >= Config.DHT_TEMP_CHANGE_THRESHOLD):
                                logging.info(f"Updated temperature: {self.latest_temperature}°C")
                                self.last_logged_dht_temp = rounded_temp
                    else:
                        logging.error("Temperature value not updated (None or out of range)")
                        
                    if humidity is not None and Config.MIN_HUMIDITY <= humidity <= Config.MAX_HUMIDITY:
                        rounded_humidity = round(float(humidity), 1)
                        if self.latest_humidity != rounded_humidity:
                            self.latest_humidity = rounded_humidity
                            # Only log when humidity changes significantly or this is the first reading
                            if (self.last_logged_dht_humidity is None or 
                                abs(rounded_humidity - self.last_logged_dht_humidity) >= Config.DHT_HUMIDITY_CHANGE_THRESHOLD):
                                logging.info(f"Updated humidity: {self.latest_humidity}%")
                                self.last_logged_dht_humidity = rounded_humidity
                    else:
                        logging.error("Humidity value not updated (None or out of range)")
                        
            except Exception as e:
                logging.error(f"Error reading DHT sensor: {e}")
            
            sleep(Config.DHT_READ_INTERVAL)


# Global DHT service instance
dht_service = DHTService()
