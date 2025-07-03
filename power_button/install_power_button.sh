#!/bin/bash
"""
Power Button Installation Script for Raspberry Pi

This script installs and configures the power button service.
Run with: sudo bash install_power_button.sh
"""

set -e  # Exit on any error

echo "=== Raspberry Pi Power Button Installation ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

# Install required Python packages
echo "Installing required Python packages..."
apt-get update
apt-get install -y python3-rpi.gpio python3-pip

# Verify RPi.GPIO installation
python3 -c "import RPi.GPIO; print('RPi.GPIO installed successfully')" || {
    echo "Error: Failed to install RPi.GPIO"
    exit 1
}

# Create installation directory
INSTALL_DIR="/opt/power-button"
mkdir -p "$INSTALL_DIR"

# Copy power button script
echo "Installing power button script..."
cp power_button.py "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/power_button.py"

# Update systemd service file with correct path
sed "s|/home/pi/power_button.py|$INSTALL_DIR/power_button.py|g" power-button.service > /etc/systemd/system/power-button.service

# Create log directory
mkdir -p /var/log
touch /var/log/power_button.log
chmod 644 /var/log/power_button.log

# Enable and start the service
echo "Configuring systemd service..."
systemctl daemon-reload
systemctl enable power-button.service
systemctl start power-button.service

# Check service status
echo "Checking service status..."
if systemctl is-active --quiet power-button.service; then
    echo "✓ Power button service is running"
else
    echo "⚠ Warning: Service may not be running properly"
    systemctl status power-button.service
fi

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Hardware Setup:"
echo "1. Connect a momentary push button between:"
echo "   - GPIO 3 (Physical Pin 5)"
echo "   - Ground (Physical Pin 6)"
echo ""
echo "Usage:"
echo "- Short press: Logs button event"
echo "- Long press (3+ seconds): Initiates shutdown"
echo "- GPIO 3 can wake Pi from halt state"
echo ""
echo "Service Management:"
echo "- Check status: sudo systemctl status power-button"
echo "- View logs: sudo journalctl -u power-button -f"
echo "- Stop service: sudo systemctl stop power-button"
echo "- Start service: sudo systemctl start power-button"
echo "- Disable service: sudo systemctl disable power-button"
echo ""
echo "Log file: /var/log/power_button.log"
echo ""
echo "To test: Press and hold the button for 3 seconds"
