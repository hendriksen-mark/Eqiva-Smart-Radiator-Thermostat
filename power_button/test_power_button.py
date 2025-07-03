#!/usr/bin/env python3
"""
Power Button Test Script

Simple script to test if the power button hardware is working correctly.
This will print button state changes without implementing shutdown functionality.

Usage:
    sudo python3 test_power_button.py
"""

import RPi.GPIO as GPIO
import time
import sys

# Configuration
BUTTON_PIN = 3  # GPIO 3 (Physical pin 5)

def test_button():
    """Test power button functionality"""
    print("=== Power Button Hardware Test ===")
    print(f"Testing button on GPIO {BUTTON_PIN}")
    print("Press Ctrl+C to exit")
    print()
    
    try:
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        last_state = GPIO.input(BUTTON_PIN)
        press_start = None
        
        print("Monitoring button... (Press the button to test)")
        
        while True:
            current_state = GPIO.input(BUTTON_PIN)
            
            # State change detected
            if current_state != last_state:
                time.sleep(0.05)  # Debounce
                current_state = GPIO.input(BUTTON_PIN)  # Re-read after debounce
                
                if current_state == GPIO.LOW:  # Button pressed
                    press_start = time.time()
                    print("Button PRESSED")
                elif current_state == GPIO.HIGH and press_start:  # Button released
                    press_duration = time.time() - press_start
                    print(f"Button RELEASED (held for {press_duration:.2f} seconds)")
                    if press_duration >= 3.0:
                        print("  -> This would trigger SHUTDOWN in the real script")
                    else:
                        print("  -> This would be logged as a short press")
                    press_start = None
                
                last_state = current_state
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure to run with: sudo python3 test_power_button.py")
    finally:
        GPIO.cleanup()
        print("GPIO cleanup completed")

if __name__ == '__main__':
    test_button()
