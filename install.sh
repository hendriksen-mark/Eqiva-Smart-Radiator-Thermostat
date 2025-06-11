#!/bin/bash
#curl -fsSL https://raw.githubusercontent.com/hendriksen-mark/Eqiva-Smart-Radiator-Thermostat/main/install.sh | bash

set -e

echo "== Eqiva Smart Radiator Thermostat Project Installer =="

# Check for Python 3
if ! command -v python3 &>/dev/null; then
    echo "Python 3 is not installed. Please install Python 3 and rerun this script."
    exit 1
fi

# Check for pip
if ! command -v pip3 &>/dev/null; then
    echo "pip3 is not installed. Installing pip3..."
    sudo apt-get update
    sudo apt-get install -y python3-pip
fi

# Check for uxterm
if ! command -v uxterm &>/dev/null; then
    echo "uxterm is not installed. Installing uxterm..."
    sudo apt-get update
    sudo apt-get install -y xterm
fi

# Optional: create and activate a virtual environment
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Create systemd service for API
SERVICE_FILE="/etc/systemd/system/eqiva-api.service"
if [ ! -f "$SERVICE_FILE" ]; then
    echo "Creating systemd service to start API on boot..."
    cat <<EOF | sudo tee $SERVICE_FILE > /dev/null
[Unit]
Description=Eqiva Smart Radiator Thermostat API
After=network.target

[Service]
Type=simple
WorkingDirectory=$(pwd)
ExecStart=/usr/bin/uxterm -hold -e $(pwd)/venv/bin/python3 $(pwd)/api.py
Restart=always
User=$(whoami)
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable eqiva-api.service
    sudo systemctl start eqiva-api.service
    echo "Systemd service eqiva-api.service created and started."
else
    echo "Systemd service eqiva-api.service already exists."
fi

echo "== Installation complete =="
echo "To activate the virtual environment in the future, run:"
echo "  source venv/bin/activate"
