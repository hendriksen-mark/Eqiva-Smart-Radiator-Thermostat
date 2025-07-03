"""
Routes package initialization
"""
from .dht_routes import dht_bp
from .homekit_routes import homekit_bp
from .system_routes import system_bp

__all__ = ['dht_bp', 'homekit_bp', 'system_bp']
