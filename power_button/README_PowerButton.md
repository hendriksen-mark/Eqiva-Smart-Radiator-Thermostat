# Raspberry Pi Power Button

A Python-based power button implementation for Raspberry Pi 4B that allows you to:
- **Short press**: Log button events
- **Long press (3+ seconds)**: Safely shutdown the Pi
- **Wake from halt**: GPIO 3 can wake the Pi from powered-off state

## Hardware Requirements

- Raspberry Pi 4B (or any Pi with GPIO)
- Momentary push button (normally open)
- 2 jumper wires
- Optional: LED on GPIO 18 for shutdown indication

## Wiring Diagram

```
Raspberry Pi GPIO Layout:
   3V3  (1) (2)  5V
 GPIO3  (3) (4)  5V
 GPIO5  (5) (6)  GND  <- Connect button here
GPIO14  (7) (8)  GPIO15
   GND  (9) (10) GPIO18 <- Optional LED
```

**Connections:**
1. Connect one side of the button to **GPIO 3** (Physical Pin 5)
2. Connect the other side of the button to **Ground** (Physical Pin 6)
3. (Optional) Connect LED with resistor between GPIO 18 and Ground

> **Why GPIO 3?** GPIO 3 has a special property - it can wake the Raspberry Pi from a halted state when pulled low. This means pressing the button can turn the Pi back on after shutdown.

## Installation

### Quick Installation

1. Copy the files to your Raspberry Pi
2. Run the installation script:

```bash
sudo bash install_power_button.sh
```

### Manual Installation

1. Install required packages:
```bash
sudo apt-get update
sudo apt-get install python3-rpi.gpio
```

2. Test the hardware:
```bash
sudo python3 test_power_button.py
```

3. Install the service:
```bash
sudo cp power_button.py /opt/power-button/
sudo cp power-button.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable power-button.service
sudo systemctl start power-button.service
```

## Usage

### Button Behavior
- **Short press** (< 3 seconds): Logs the button press event
- **Long press** (≥ 3 seconds): Initiates safe system shutdown
- **Press when off**: Wakes the Pi from halt state (GPIO 3 feature)

### Service Management

```bash
# Check service status
sudo systemctl status power-button

# View live logs
sudo journalctl -u power-button -f

# Stop the service
sudo systemctl stop power-button

# Start the service
sudo systemctl start power-button

# Disable auto-start
sudo systemctl disable power-button
```

### Log Files

- Service logs: `sudo journalctl -u power-button`
- Application logs: `/var/log/power_button.log`

## Configuration

Edit `/opt/power-button/power_button.py` to customize:

```python
# Configuration
BUTTON_PIN = 3              # GPIO pin number
LONG_PRESS_TIME = 3.0       # Seconds to hold for shutdown
DEBOUNCE_TIME = 0.05        # Debounce delay
```

## Troubleshooting

### Service Won't Start
```bash
# Check service status and logs
sudo systemctl status power-button
sudo journalctl -u power-button -n 50

# Verify GPIO access
sudo python3 -c "import RPi.GPIO; print('GPIO OK')"
```

### Button Not Responding
1. Test hardware with: `sudo python3 test_power_button.py`
2. Check wiring connections
3. Verify button is normally-open type
4. Check GPIO 3 is not used by other services

### Permission Issues
- The service runs as root to access GPIO
- Log files are created with appropriate permissions
- GPIO cleanup is handled automatically

## Integration with Existing API

The power button service runs independently of your existing thermostat API. Both can run simultaneously:

- **Thermostat API**: Port 5002 (your existing service)
- **Power Button**: Background systemd service
- **No conflicts**: Different GPIO pins and processes

## Safety Features

- **Debouncing**: Prevents accidental triggers from electrical noise
- **GPIO cleanup**: Proper cleanup on service stop/restart
- **Signal handling**: Graceful shutdown on SIGTERM/SIGINT
- **Logging**: All events logged for troubleshooting
- **Safe shutdown**: Uses `sync` and proper shutdown command

## Advanced Features

### LED Feedback (Optional)
Connect an LED to GPIO 18 to get visual feedback during shutdown:
- LED blinks 3 times when shutdown is initiated
- Modify `blink_led()` function to customize behavior

### Custom Actions
Modify the `button_pressed()` handler to add custom actions:
- Send notifications
- Trigger other services
- Custom GPIO control

## Uninstallation

```bash
# Stop and disable service
sudo systemctl stop power-button
sudo systemctl disable power-button

# Remove files
sudo rm /etc/systemd/system/power-button.service
sudo rm -rf /opt/power-button/
sudo rm /var/log/power_button.log

# Reload systemd
sudo systemctl daemon-reload
```

## Files Overview

- `power_button.py` - Main power button service
- `test_power_button.py` - Hardware testing script  
- `power-button.service` - Systemd service configuration
- `install_power_button.sh` - Automated installation script
- `README_PowerButton.md` - This documentation

## License

This power button implementation is provided as-is for educational and practical use with Raspberry Pi projects.
