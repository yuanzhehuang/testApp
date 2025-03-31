import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from src.config.config_manager import config_manager

def setup_logging() -> bool:
    """
    Configures the logging system based on settings in config.ini.

    Reads 'LOGGING' section for 'enable_logging', 'log_level', 'log_directory'.
    Sets up console and rotating file handlers.

    Returns:
        bool: True if logging was enabled and set up, False otherwise.
    """
    enable_logging = config_manager.get_boolean("LOGGING", "enable_logging", fallback=True)

    if not enable_logging:
        logging.basicConfig(level=logging.CRITICAL + 1) # Effectively disable standard logging
        # You might still want basic print feedback for critical setup errors
        print("Logging is disabled in config.ini.")
        return False

    log_level_str = config_manager.get("LOGGING", "log_level", fallback="INFO").upper()
    log_dir = config_manager.get("LOGGING", "log_directory", fallback="logs")
    log_file = os.path.join(log_dir, "app.log")

    # Ensure log directory exists
    try:
        os.makedirs(log_dir, exist_ok=True)
    except OSError as e:
        # Fallback to basic console logging if directory creation fails
        logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        logging.error(f"Failed to create log directory '{log_dir}'. Logging to console only. Error: {e}")
        return True # Logging is technically enabled, just not to file

    # Map string level to logging constant
    log_level = getattr(logging, log_level_str, logging.INFO)

    # Define log format
    log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # --- Console Handler ---
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    console_handler.setLevel(log_level) # Console shows messages at the configured level or higher

    # --- Rotating File Handler ---
    try:
        # Rotate logs: 5 files max, 5MB each
        file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
        file_handler.setFormatter(log_format)
        file_handler.setLevel(log_level) # File logs at the configured level or higher

        # --- Add Handlers ---
        # Clear existing handlers (important if this function is called multiple times)
        if root_logger.hasHandlers():
            root_logger.handlers.clear()

        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)

        logging.info(f"Logging enabled. Level: {log_level_str}. Log file: '{log_file}'")
        return True

    except Exception as e:
            # Fallback to basic console logging if file handler setup fails
        logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        logging.error(f"Failed to setup file logging to '{log_file}'. Logging to console only. Error: {e}")
        return True

# Example toggle function (less common now that setup handles enable flag)
# def toggle_logging():
#     """ Toggles the enable_logging setting in config and re-applies logging setup. """
#     current_status = config_manager.get_boolean("LOGGING", "enable_logging", fallback=True)
#     new_status = not current_status
#     config_manager.set("LOGGING", "enable_logging", new_status)
#     config_manager.save_config()
#     print(f"Logging {'enabled' if new_status else 'disabled'}. Restart may be required for full effect.")
#     setup_logging() # Re-run setup to apply immediately (might have limitations)
#     return new_status