"""
API package initialization
"""
from flask import Flask
import signal
import os
from typing import Any
import logManager

from .config import Config
from .services import thermostat_service
from .routes import dht_bp, homekit_bp, system_bp
from .middleware import register_middleware

logging = logManager.logger.get_logger(__name__)


def create_app() -> Flask:
    """Application factory function"""
    app = Flask(__name__)
    
    # Register middleware
    register_middleware(app)
    
    # Register blueprints
    app.register_blueprint(dht_bp)
    app.register_blueprint(homekit_bp)
    app.register_blueprint(system_bp)
    
    return app


def handle_exit(signum: int, frame: Any) -> None:
    """Handle exit signals"""
    logging.info(f"Received signal {signum} on {frame}, shutting down gracefully...")
    thermostat_service.cleanup_thermostats()
    os._exit(0)


def setup_signal_handlers() -> None:
    """Setup signal handlers for graceful shutdown"""
    signal.signal(signal.SIGTERM, handle_exit)
    signal.signal(signal.SIGINT, handle_exit)


def initialize_services() -> None:
    """Initialize all services"""
    logging.info("Starting Eqiva Smart Radiator Thermostat API...")
    logging.info(f"Current log level: {Config.LOG_LEVEL}")
    logManager.logger.configure_logger(Config.LOG_LEVEL)
    thermostat_service.start_polling()


__all__ = ['create_app', 'setup_signal_handlers', 'initialize_services', 'Config']
