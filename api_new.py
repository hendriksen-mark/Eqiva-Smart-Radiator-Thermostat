#!/usr/bin/env python3
"""
Main entry point for the Eqiva Smart Radiator Thermostat API
"""
from api import create_app, setup_signal_handlers, initialize_services, Config

if __name__ == '__main__':
    # Initialize services and setup signal handlers
    initialize_services()
    setup_signal_handlers()
    
    # Create and run the Flask application
    app = create_app()
    app.run(host='0.0.0.0', port=Config.HOST_HTTP_PORT)
