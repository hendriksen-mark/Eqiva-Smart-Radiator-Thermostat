# Installation Guide

## Installing the Package

You can install this package using pip in several ways:

### Option 1: Install from local directory
```bash
# Clone the repository
git clone https://github.com/hendriksen-mark/Eqiva-Smart-Radiator-Thermostat.git
cd Eqiva-Smart-Radiator-Thermostat

# Install the package with dependencies
pip3 install -r requirements.txt
pip3 install .
```

### Option 2: Install directly from git (if published)
```bash
pip3 install git+https://github.com/hendriksen-mark/Eqiva-Smart-Radiator-Thermostat.git
```

### Option 3: Development installation
```bash
# For development, use editable install
pip3 install -e .
```

## Usage

### Command Line Interface
After installation, you can use either:
- The installed `eqiva` command: `eqiva --help`
- The original script: `python3 eqiva.py --help`

```bash
# Using the installed command
eqiva --help
eqiva --scan
eqiva <mac_address> --status

# Using the original script (requires package to be installed)
python3 eqiva.py --help
python3 eqiva.py --scan
python3 eqiva.py <mac_address> --status
```

### Python Library
You can also use it as a Python library:
```python
from eqiva_thermostat import Thermostat, ThermostatController

# Create a thermostat instance
thermostat = Thermostat("MAC_ADDRESS")

# Use the controller
controller = ThermostatController()
```

## Project Structure

```
Eqiva-Smart-Radiator-Thermostat/
├── eqiva.py                    # Original CLI script (still usable)
├── eqiva_thermostat/           # Python package
│   ├── __init__.py            # Package exports
│   └── utils/                 # Utility modules
│       ├── Thermostat.py
│       ├── ThermostatCLI.py
│       └── ... (other modules)
├── setup.py                   # Package setup
├── pyproject.toml            # Modern package configuration
├── requirements.txt          # Dependencies
└── ... (other files)
```

## Requirements

- Python 3.8 or higher
- bleak library for Bluetooth LE communication
- logManager library (automatically installed from git)

## Supported Platforms

- Linux (including Raspberry Pi)
- macOS  
- Windows

## Dependencies

The package automatically installs the following dependencies:
- `bleak` - Bluetooth Low Energy platform library
- `logManager` - Logging management library from hendriksen-mark's repository
