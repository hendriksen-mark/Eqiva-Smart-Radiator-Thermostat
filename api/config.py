"""
Configuration management for the Eqiva Smart Radiator Thermostat API
"""
import os


class Config:
    """Application configuration"""
    HOST_HTTP_PORT = int(os.getenv('HOST_HTTP_PORT', 5002))
    STATUS_YAML_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "status_store.yaml")
    POLLING_INTERVAL = int(os.getenv('POLLING_INTERVAL', 300)) # Default to 5 minutes
    DHT_READ_INTERVAL = int(os.getenv('DHT_READ_INTERVAL', 5))
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # Temperature validation ranges
    MIN_TEMPERATURE = 5.0
    MAX_TEMPERATURE = 30.0
    
    # DHT sensor validation ranges
    MIN_DHT_TEMP = -40.0
    MAX_DHT_TEMP = 80.0
    MIN_HUMIDITY = 0.0
    MAX_HUMIDITY = 100.0
    
    # DHT logging thresholds
    DHT_TEMP_CHANGE_THRESHOLD = 0.5  # Only log when temperature changes by more than 0.5°C
    DHT_HUMIDITY_CHANGE_THRESHOLD = 2.0  # Only log when humidity changes by more than 2%
    
    @staticmethod
    def get_current_polling_interval() -> int:
        """Get the current polling interval from environment variables (dynamic)"""
        return int(os.getenv('POLLING_INTERVAL', 300))


def update_env_file(key: str, value: str) -> None:
    """Update a key-value pair in the environment file"""
    env_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "eq3.env")
    
    # Read current content
    lines = []
    if os.path.exists(env_file_path):
        with open(env_file_path, 'r') as f:
            lines = f.readlines()
    
    # Update or add the key
    key_found = False
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[i] = f"{key}={value}\n"
            key_found = True
            break
    
    if not key_found:
        lines.append(f"{key}={value}\n")
    
    # Write back to file
    with open(env_file_path, 'w') as f:
        f.writelines(lines)


def reload_env_variables() -> None:
    """Reload environment variables from the eq3.env file"""
    env_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "eq3.env")
    
    if os.path.exists(env_file_path):
        with open(env_file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
