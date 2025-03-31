import configparser
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages reading and writing to the INI configuration file."""

    DEFAULT_CONFIG_FILE = "config.ini"

    def __init__(self, config_file=DEFAULT_CONFIG_FILE):
        self.config_file = config_file
        self.config = configparser.ConfigParser(interpolation=None) # Disable interpolation
        self.load_config()

    def load_config(self):
        """Loads configuration from the INI file."""
        if not os.path.exists(self.config_file):
            logger.warning(f"Configuration file '{self.config_file}' not found. Using default fallbacks.")
            # Optionally create a default config here if needed
            return False
        try:
            self.config.read(self.config_file)
            logger.info(f"Configuration loaded from '{self.config_file}'.")
            return True
        except configparser.Error as e:
            logger.error(f"Error reading configuration file '{self.config_file}': {e}")
            # Reset config object to avoid partial state
            self.config = configparser.ConfigParser(interpolation=None)
            return False

    def get(self, section: str, key: str, fallback: str = None) -> Optional[str]:
        """Gets a string value from the configuration."""
        try:
            return self.config.get(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError):
                if fallback is not None:
                    logger.debug(f"Config '{section}/{key}' not found, using fallback: '{fallback}'")
                    return fallback
                else:
                    logger.warning(f"Config '{section}/{key}' not found and no fallback provided.")
                    return None
        except Exception as e:
            logger.error(f"Error getting config '{section}/{key}': {e}")
            return fallback


    def get_int(self, section: str, key: str, fallback: int = 0) -> int:
        """Gets an integer value from the configuration."""
        try:
            return self.config.getint(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError):
            logger.debug(f"Config '{section}/{key}' not found or invalid, using fallback: {fallback}")
            return fallback
        except ValueError:
            logger.warning(f"Config value for '{section}/{key}' is not a valid integer. Using fallback: {fallback}")
            return fallback
        except Exception as e:
                logger.error(f"Error getting int config '{section}/{key}': {e}")
                return fallback

    def get_float(self, section: str, key: str, fallback: float = 0.0) -> float:
        """Gets a float value from the configuration."""
        try:
            return self.config.getfloat(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError):
                logger.debug(f"Config '{section}/{key}' not found or invalid, using fallback: {fallback}")
                return fallback
        except ValueError:
            logger.warning(f"Config value for '{section}/{key}' is not a valid float. Using fallback: {fallback}")
            return fallback
        except Exception as e:
                logger.error(f"Error getting float config '{section}/{key}': {e}")
                return fallback


    def get_boolean(self, section: str, key: str, fallback: bool = False) -> bool:
        """Gets a boolean value from the configuration."""
        try:
            # Be explicit about fallback to handle parsing errors correctly
            return self.config.getboolean(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError):
                logger.debug(f"Config '{section}/{key}' not found, using fallback: {fallback}")
                return fallback
        except ValueError:
                logger.warning(f"Config value for '{section}/{key}' is not a valid boolean. Using fallback: {fallback}")
                return fallback
        except Exception as e:
                logger.error(f"Error getting boolean config '{section}/{key}': {e}")
                return fallback

    def set(self, section: str, key: str, value):
        """Sets a value in the configuration (in memory)."""
        if not self.config.has_section(section):
            self.config.add_section(section)
            logger.info(f"Added new config section: '{section}'")
        str_value = str(value) # Ensure value is string for configparser
        self.config.set(section, key, str_value)
        logger.debug(f"Set config (in memory): '{section}/{key}' = '{str_value}'")

    def save_config(self):
        """Saves the current configuration state to the INI file."""
        try:
            with open(self.config_file, 'w') as configfile:
                self.config.write(configfile)
            logger.info(f"Configuration saved successfully to '{self.config_file}'.")
            return True
        except IOError as e:
            logger.error(f"Error writing configuration file '{self.config_file}': {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error saving config: {e}")
            return False


# --- Singleton Instance ---
# This instance is created when the module is first imported.
config_manager = ConfigManager()