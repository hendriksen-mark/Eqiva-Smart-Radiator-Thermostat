import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(lineno)d - %(levelname)s - %(message)s'
)

try:
    import Adafruit_DHT  # type: ignore
except ImportError:
    logging.warning("Adafruit_DHT module not found. Using dummy implementation.")
    class DummyDHT:
        DHT11 = None
        @staticmethod
        def read_retry(sensor, pin):
            return 22.0, 50.0
    Adafruit_DHT = DummyDHT()

sensor = Adafruit_DHT.DHT11
DHT_PIN = 25

def read_dht_temperature() -> float:
    """
    Read the temperature from the DHT sensor.
    Replace this stub with actual sensor reading code.
    """
    try:
        humidity, temperature = Adafruit_DHT.read_retry(sensor, DHT_PIN)
        
        if temperature is not None and -40.0 < temperature < 80.0:
            logging.debug(f"Temperature: {temperature}")
        else:
            logging.debug("Temperature value not updated (None or out of range)")
            return None, None
        if humidity is not None and 0.0 <= humidity <= 100.0:
            logging.debug(f"Humidity: {humidity}")
        else:
            logging.debug("Humidity value not updated (None or out of range)")
            return None, None
        return temperature, humidity
    except Exception as e:
        logging.error(f"Error reading DHT sensor: {e}")
        return None

def main():
    """
    Main function to read and log the DHT sensor data.
    """
    logging.info("Starting DHT sensor reading...")
    result = read_dht_temperature()
    if result is not None:
        humidity, temperature = result
        logging.info(f"Humidity: {humidity}%, Temperature: {temperature}°C")
    else:
        logging.warning("Failed to read from DHT sensor.")

if __name__ == "__main__":
    main()
