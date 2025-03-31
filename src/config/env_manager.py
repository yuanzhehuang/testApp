import os
import logging
from typing import Optional
from dotenv import load_dotenv, set_key, find_dotenv, dotenv_values

logger = logging.getLogger(__name__)

class EnvManager:
    """Manages reading and writing sensitive secrets using a .env file."""

    DEFAULT_ENV_FILE = ".env" # Standard name

    def __init__(self, env_file=DEFAULT_ENV_FILE):
        # Find the .env file automatically, searching upwards from CWD
        self.env_file = find_dotenv(filename=env_file, raise_error_if_not_found=False, usecwd=True)

        if not self.env_file:
                logger.warning(f".env file ('{env_file}') not found in project directory or parent directories. Secrets depending on it will be unavailable.")
                self.env_file = env_file # Store the intended name even if not found yet
                self._create_env_file_if_needed() # Attempt to create it
        else:
                logger.info(f"Using .env file found at: '{self.env_file}'")
                self.load() # Load existing values on init


    def _create_env_file_if_needed(self):
            """Creates an empty .env file if it doesn't exist."""
            if not os.path.exists(self.env_file):
                try:
                    with open(self.env_file, 'w') as f:
                        f.write("# Add sensitive keys like API tokens here\n")
                        f.write("# Example: JIRA_API_TOKEN=your_token\n")
                    logger.info(f"Created empty .env file at: '{self.env_file}'")
                except IOError as e:
                    logger.error(f"Could not create .env file at '{self.env_file}': {e}")


    def load(self) -> bool:
        """
        Loads environment variables from the .env file into the process environment.
        Returns True if loading was successful (file exists), False otherwise.
        """
        if self.env_file and os.path.exists(self.env_file):
            loaded = load_dotenv(dotenv_path=self.env_file, override=True) # Override existing env vars
            if loaded:
                logger.debug(f"Loaded environment variables from '{self.env_file}'.")
            else:
                    logger.debug(f"'{self.env_file}' exists but contained no variables to load.")
            return True
        else:
            logger.debug(f".env file '{self.env_file}' not found or not specified. Skipping load.")
            return False


    def set_secret(self, secret_name: str, secret_value: str) -> bool:
        """
        Sets (adds or updates) a secret in the .env file.
        Returns True on success, False on failure.
        """
        if not self.env_file:
                logger.error("Cannot set secret: .env file path is not defined.")
                return False

        self._create_env_file_if_needed() # Ensure file exists before writing

        try:
            # Use set_key which handles adding/updating correctly
            success = set_key(self.env_file, secret_name, secret_value)
            if success:
                logger.info(f"Set secret '{secret_name}' in '{self.env_file}'.")
                # Optionally reload environment variables after setting
                self.load()
                return True
            else:
                # This case might indicate an issue with the dotenv library or file permissions
                logger.error(f"Failed to set secret '{secret_name}' in '{self.env_file}' using set_key.")
                return False

        except IOError as e:
                logger.error(f"I/O error setting secret '{secret_name}' in '{self.env_file}': {e}")
                return False
        except Exception as e:
                logger.error(f"Unexpected error setting secret '{secret_name}': {e}")
                return False


    def get_secret(self, secret_name: str) -> Optional[str]:
        """
        Gets a secret value. Tries os.environ first (if loaded), then reads directly.
        """
        # 1. Try getting from environment (might have been loaded)
        secret = os.environ.get(secret_name)
        if secret:
            logger.debug(f"Retrieved secret '{secret_name}' from process environment.")
            return secret

        # 2. If not in env, try reading directly from the file (in case load hasn't happened or failed)
        if self.env_file and os.path.exists(self.env_file):
                try:
                    values = dotenv_values(self.env_file)
                    secret = values.get(secret_name)
                    if secret:
                        logger.debug(f"Retrieved secret '{secret_name}' directly from '{self.env_file}'.")
                        return secret
                except Exception as e:
                    logger.error(f"Error directly reading secret '{secret_name}' from '{self.env_file}': {e}")


        logger.warning(f"Secret '{secret_name}' not found in environment or '{self.env_file}'.")
        return None


    def remove_secret(self, secret_name: str) -> bool:
        """
        Removes a secret from the .env file by rewriting the file without it.
        Note: This can be inefficient for large files and removes comments.
        Returns True on success, False on failure.
        """
        if not self.env_file or not os.path.exists(self.env_file):
            logger.warning(f"Cannot remove secret '{secret_name}': .env file '{self.env_file}' not found.")
            return False

        try:
            lines = []
            found = False
            with open(self.env_file, 'r') as file:
                lines = file.readlines()

            # Rewrite the file excluding the line with the secret
            with open(self.env_file, 'w') as file:
                for line in lines:
                    # Basic check: starts with key followed by =
                    # More robust parsing might be needed for complex .env files
                    if line.strip().startswith(f"{secret_name}="):
                        found = True
                        continue # Skip this line
                    file.write(line)

            if found:
                logger.info(f"Removed secret '{secret_name}' from '{self.env_file}'.")
                # Optionally reload environment
                self.load()
                return True
            else:
                logger.info(f"Secret '{secret_name}' not found in '{self.env_file}', nothing removed.")
                return False # Indicate it wasn't found to remove

        except IOError as e:
            logger.error(f"I/O error removing secret '{secret_name}' from '{self.env_file}': {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error removing secret '{secret_name}': {e}")
            return False

# --- Singleton Instance ---
env_manager = EnvManager()