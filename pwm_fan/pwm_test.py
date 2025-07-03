import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(lineno)d - %(levelname)s - %(message)s'
)

MIN_TEMP = 25
MAX_TEMP = 80
MIN_SPEED = 0
MAX_SPEED = 255

def renormalize(n, range1, range2):
    """Scale n from range1 to range2."""
    delta1 = range1[1] - range1[0]
    delta2 = range2[1] - range2[0]
    return (delta2 * (n - range1[0]) / delta1) + range2[0]


def main():
    try:
        temp = 26
        temp = max(MIN_TEMP, min(MAX_TEMP, temp))
        # Convert temp to pigpio duty cycle (0-255)
        duty_cycle = renormalize(temp, [MIN_TEMP, MAX_TEMP], [MIN_SPEED, MAX_SPEED])
        logging.info(f"CPU Temp: {temp:.1f}°C, Fan Duty cycle: {duty_cycle:.1f}")
    except Exception as e:
        logging.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()