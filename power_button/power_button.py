#!/usr/bin/env python3
"""
Raspberry Pi Power Button Script

This script creates a software power button for Raspberry Pi using GPIO.
- Short press: Log button press
- Long press (3+ seconds): Initiate shutdown
- GPIO 3 (Pin 5) can wake Pi from halt state when pressed

Hardware setup:
- Connect momentary button between GPIO 3 (Pin 5) and Ground (Pin 6)
- No external resistor needed (uses internal pull-up)

Usage:
    python3 power_button.py
    
Or run as systemd service for automatic startup.
"""

import RPi.GPIO as GPIO
import time
import subprocess
import logging
import signal
import sys
from threading import Event

# Configuration
BUTTON_PIN = 3  # GPIO 3 (Physical pin 5) - can wake Pi from halt
LONG_PRESS_TIME = 3.0  # Seconds to hold for shutdown
DEBOUNCE_TIME = 0.05  # Debounce delay in seconds

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/power_button.log'),
        logging.StreamHandler()
    ]
)

class PowerButton:
    def __init__(self, pin=BUTTON_PIN):
        self.pin = pin
        self.shutdown_event = Event()
        self.setup_gpio()
        self.setup_signal_handlers()
        
    def setup_gpio(self):
        """Setup GPIO pin for button input"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        logging.info(f"Power button initialized on GPIO {self.pin}")
        
    def setup_signal_handlers(self):
        """Setup signal handlers for clean shutdown"""
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logging.info(f"Received signal {signum}, shutting down...")
        self.cleanup()
        sys.exit(0)
        
    def cleanup(self):
        """Clean up GPIO resources"""
        GPIO.cleanup()
        logging.info("GPIO cleanup completed")
        
    def button_pressed(self):
        """Check if button is currently pressed (LOW = pressed with pull-up)"""
        return GPIO.input(self.pin) == GPIO.LOW
        
    def wait_for_button_release(self):
        """Wait for button to be released"""
        while self.button_pressed():
            time.sleep(0.01)
            
    def execute_shutdown(self):
        """Execute system shutdown"""
        logging.info("Initiating system shutdown...")
        try:
            # Sync filesystem
            subprocess.run(['sync'], check=True)
            # Shutdown system
            subprocess.run(['sudo', 'shutdown', '-h', 'now'], check=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"Shutdown command failed: {e}")
            
    def blink_led(self, pin=18, times=3):
        """Blink LED to indicate shutdown (optional - requires LED on GPIO 18)"""
        try:
            GPIO.setup(pin, GPIO.OUT)
            for _ in range(times):
                GPIO.output(pin, GPIO.HIGH)
                time.sleep(0.2)
                GPIO.output(pin, GPIO.LOW)
                time.sleep(0.2)
        except Exception as e:
            logging.debug(f"LED blink failed (optional): {e}")
            
    def run(self):
        """Main button monitoring loop"""
        logging.info("Power button service started. Press and hold for shutdown...")
        
        try:
            while not self.shutdown_event.is_set():
                # Wait for button press (LOW state)
                if self.button_pressed():
                    # Debounce
                    time.sleep(DEBOUNCE_TIME)
                    if not self.button_pressed():
                        continue
                        
                    logging.info("Button pressed")
                    press_start = time.time()
                    
                    # Wait while button is held down
                    while self.button_pressed() and not self.shutdown_event.is_set():
                        press_duration = time.time() - press_start
                        
                        if press_duration >= LONG_PRESS_TIME:
                            logging.info(f"Long press detected ({press_duration:.1f}s) - shutting down")
                            self.blink_led()  # Optional LED feedback
                            self.execute_shutdown()
                            return
                            
                        time.sleep(0.1)
                    
                    # Button released
                    press_duration = time.time() - press_start
                    if press_duration < LONG_PRESS_TIME:
                        logging.info(f"Short press ({press_duration:.1f}s) - button event logged")
                    
                    # Wait for button to be fully released
                    self.wait_for_button_release()
                    time.sleep(DEBOUNCE_TIME)
                
                time.sleep(0.1)  # Small delay to prevent excessive CPU usage
                
        except Exception as e:
            logging.error(f"Error in main loop: {e}")
        finally:
            self.cleanup()

def check_permissions():
    """Check if script has necessary permissions"""
    try:
        # Test GPIO access
        GPIO.setmode(GPIO.BCM)
        GPIO.cleanup()
        return True
    except Exception as e:
        logging.error(f"GPIO access denied: {e}")
        logging.error("Run with: sudo python3 power_button.py")
        return False

def main():
    """Main function"""
    if not check_permissions():
        sys.exit(1)
        
    power_button = PowerButton()
    
    try:
        power_button.run()
    except KeyboardInterrupt:
        logging.info("Received keyboard interrupt")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
    finally:
        power_button.cleanup()

if __name__ == '__main__':
    main()
