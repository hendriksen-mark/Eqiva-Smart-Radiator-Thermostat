# Created by: Michael Klements
# For 40mm 5V PWM Fan Control On A Raspberry Pi
# Sets fan speed proportional to CPU temperature - best for good quality fans
# Works well with a Pi Desktop Case with OLED Stats Display
# Installation & Setup Instructions - https://www.the-diy-life.com/connecting-a-pwm-fan-to-a-raspberry-pi/
# Modified to use hardware PWM via pigpio for Noctua fans

import pigpio # type: ignore
import time
import subprocess
import atexit

FAN_GPIO_PIN = 18  # GPIO 18 (physical pin 12) - hardware PWM capable
FAN_PWM_FREQ = 25000  # 25kHz for Noctua fans (acceptable range: 21kHz to 28kHz)

MIN_TEMP = 25
MAX_TEMP = 80
MIN_SPEED = 0
MAX_SPEED = 100

# Initialize pigpio
pi = pigpio.pi()
if not pi.connected:
    raise RuntimeError("Could not connect to pigpio daemon. Make sure pigpiod is running.")

# Set PWM frequency and start with 0% duty cycle
pi.set_PWM_frequency(FAN_GPIO_PIN, FAN_PWM_FREQ)
pi.set_PWM_dutycycle(FAN_GPIO_PIN, 0)

def cleanup():
    """Clean up GPIO resources."""
    pi.set_PWM_dutycycle(FAN_GPIO_PIN, 0)
    pi.stop()

# Register cleanup function to run on exit
atexit.register(cleanup)

def get_temp():
    """Read the CPU temperature and return it as a float in degrees Celsius."""
    try:
        output = subprocess.run(['vcgencmd', 'measure_temp'], capture_output=True, check=True)
        temp_str = output.stdout.decode()
        return float(temp_str.split('=')[1].split('\'')[0])
    except (IndexError, ValueError, subprocess.CalledProcessError):
        raise RuntimeError('Could not get temperature')

def renormalize(n, range1, range2):
    """Scale n from range1 to range2."""
    delta1 = range1[1] - range1[0]
    delta2 = range2[1] - range2[0]
    return (delta2 * (n - range1[0]) / delta1) + range2[0]

def main():
    try:
        while True:
            temp = get_temp()
            temp = max(MIN_TEMP, min(MAX_TEMP, temp))
            # Convert percentage to pigpio duty cycle (0-255)
            duty_percentage = renormalize(temp, [MIN_TEMP, MAX_TEMP], [MIN_SPEED, MAX_SPEED])
            duty_cycle = int(duty_percentage * 255 / 100)
            pi.set_PWM_dutycycle(FAN_GPIO_PIN, duty_cycle)
            print(f"Temp: {temp:.1f}°C, Fan speed: {duty_percentage:.1f}%, Duty cycle: {duty_cycle}")
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nStopping fan...")
        cleanup()

if __name__ == "__main__":
    main()