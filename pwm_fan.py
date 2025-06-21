# Created by: Michael Klements
# For 40mm 5V PWM Fan Control On A Raspberry Pi
# Sets fan speed proportional to CPU temperature - best for good quality fans
# Works well with a Pi Desktop Case with OLED Stats Display
# Installation & Setup Instructions - https://www.the-diy-life.com/connecting-a-pwm-fan-to-a-raspberry-pi/

import RPi.GPIO as IO # type: ignore
import time
import subprocess

FAN_GPIO_PIN = 14
FAN_PWM_FREQ = 100

MIN_TEMP = 25
MAX_TEMP = 80
MIN_SPEED = 0
MAX_SPEED = 100

IO.setwarnings(False)
IO.setmode(IO.BCM)
IO.setup(FAN_GPIO_PIN, IO.OUT)
fan = IO.PWM(FAN_GPIO_PIN, FAN_PWM_FREQ)
fan.start(0)

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
            duty_cycle = int(renormalize(temp, [MIN_TEMP, MAX_TEMP], [MIN_SPEED, MAX_SPEED]))
            fan.ChangeDutyCycle(duty_cycle)
            time.sleep(5)
    except KeyboardInterrupt:
        fan.ChangeDutyCycle(0)
        fan.stop()
        IO.cleanup()

if __name__ == "__main__":
    main()