# API Structure Refactoring

This document describes the new modular structure of the Eqiva Smart Radiator Thermostat API.

## New Structure

The original monolithic `api.py` file has been refactored into a modular structure:

```
api/
├── __init__.py              # Main application factory and initialization
├── config.py                # Configuration management
├── utils.py                 # Utility functions
├── models/
│   ├── __init__.py         # Models package
│   └── thermostat.py       # Thermostat data models
├── services/
│   ├── __init__.py         # Services package
│   ├── dht_service.py      # DHT sensor service
│   └── thermostat_service.py # Thermostat management service
├── routes/
│   ├── __init__.py         # Routes package
│   ├── dht_routes.py       # DHT sensor endpoints
│   ├── homekit_routes.py   # HomeKit/Homebridge endpoints
│   └── system_routes.py    # System and configuration endpoints
└── middleware/
    └── __init__.py         # Middleware (logging, CORS, error handling)
```

## Key Features

### 1. **Separation of Concerns**
- **Models**: Data structures and business logic
- **Services**: Background tasks and business operations
- **Routes**: HTTP endpoints and request handling
- **Middleware**: Cross-cutting concerns (logging, CORS, error handling)
- **Config**: Centralized configuration management

### 2. **Modular Architecture**
- Each component has a single responsibility
- Easy to maintain and extend
- Clear dependencies between modules

### 3. **Flask Application Factory Pattern**
- `create_app()` function for creating Flask instances
- Better for testing and multiple environments
- Clean separation of initialization logic

### 4. **Service Layer**
- `ThermostatService`: Manages all thermostat operations
- `DHTService`: Handles DHT sensor reading
- Services are singleton instances for shared state

### 5. **Blueprint-based Routing**
- Routes are organized into logical blueprints
- Each blueprint handles a specific domain (DHT, HomeKit, System)

## Usage

### Running the Application

```bash
# Use Python 3
python3 api.py

# Or directly
python3 -c "from api import create_app, initialize_services; initialize_services(); app = create_app(); app.run(host='0.0.0.0', port=5002)"
```

### Importing Components

```python
# Import the application factory
from api import create_app

# Import services
from api.services import dht_service, thermostat_service

# Import configuration
from api.config import Config

# Import models
from api.models import ThermostatStatus, create_default_thermostat_status
```

## Migration Notes

### What Changed
1. **Main file**: `api.py` is now a simple entry point (13 lines vs 900+ lines)
2. **Services**: Background tasks moved to dedicated service classes
3. **Routes**: HTTP endpoints organized into blueprints
4. **Configuration**: Centralized in `api/config.py`
5. **Models**: Data structures moved to `api/models/`

### What Stayed the Same
- All API endpoints work exactly the same
- Same functionality and behavior
- Same configuration options
- Same dependencies

### Benefits
- **Maintainability**: Each file has a single responsibility
- **Testability**: Individual components can be tested in isolation
- **Extensibility**: Easy to add new features without modifying existing code
- **Readability**: Code is organized logically and easy to navigate
- **Reusability**: Services and utilities can be reused across different parts of the application

### Backup
The original `api.py` file has been backed up as `api_backup.py` for reference.

## File Descriptions

### `api/__init__.py`
- Application factory function
- Service initialization
- Signal handler setup
- Main entry point coordination

### `api/config.py`
- Configuration class with all settings
- Environment file management
- Centralized configuration access

### `api/models/thermostat.py`
- ThermostatStatus data class
- Default status creation
- Heating/cooling state calculation

### `api/services/dht_service.py`
- DHT sensor reading thread
- Temperature/humidity monitoring
- Pin configuration management

### `api/services/thermostat_service.py`
- Thermostat polling and management
- Status store operations
- Bluetooth connectivity handling

### `api/routes/`
- **dht_routes.py**: DHT sensor endpoints (`/dht`, `/pi_temp`)
- **homekit_routes.py**: HomeKit compatibility endpoints
- **system_routes.py**: System info, health, config endpoints

### `api/middleware/__init__.py`
- Request/response logging
- CORS headers
- Error handling
- Common middleware functions

This refactoring maintains 100% backward compatibility while providing a much more maintainable and extensible codebase.
