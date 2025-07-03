import logging
import sys
import threading


class Logger:
    def __init__(self):
        self.loggers = {}
        self.logLevel = logging.INFO  # Default to INFO level
        self._lock = threading.Lock()
        self._configured = False

    @staticmethod
    def _get_log_format():
        """Return the log format for the logger."""
        return logging.Formatter('%(asctime)s - %(name)s - %(lineno)d - %(levelname)s - %(message)s')

    def configure_logger(self, level):
        """Configure the logging level for all loggers."""
        with self._lock:
            self.logLevel = getattr(logging, level.upper(), logging.INFO)
            
            # If already configured, update existing loggers
            if self._configured:
                for logger_name, logger in self.loggers.items():
                    # Clear existing handlers
                    logger.handlers.clear()
                    # Re-setup with new level
                    self._setup_logger_internal(logger_name, logger)
            
            self._configured = True

    def _setup_logger_internal(self, name, logger=None):
        """Set up a logger with the given name."""
        if logger is None:
            logger = logging.getLogger(name)

        # Stream handler for stdout (DEBUG, INFO)
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(self._get_log_format())
        stdout_handler.setLevel(self.logLevel)
        stdout_handler.addFilter(lambda record: record.levelno < logging.WARNING)
        logger.addHandler(stdout_handler)

        # Stream handler for stderr (WARNING, ERROR, CRITICAL)
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setFormatter(self._get_log_format())
        stderr_handler.setLevel(logging.WARNING)
        logger.addHandler(stderr_handler)

        # Set the logger level to the configured level
        logger.setLevel(self.logLevel)
        logger.propagate = False
        return logger

    def get_logger(self, name):
        """Get a logger by name, creating it if necessary."""
        with self._lock:
            if name not in self.loggers:
                self.loggers[name] = self._setup_logger_internal(name)
            return self.loggers[name]

    def get_level_name(self):
        """Get the name of the current logging level."""
        return logging.getLevelName(self.logLevel)
    
    @staticmethod
    def hexstr(ba: bytearray) -> str:
        return " ".join([("0" + hex(b).replace("0x", ""))[-2:] for b in ba])