import os
import logging
from pathlib import Path
from typing import Optional

from src.config.config_manager import config_manager # Needs access to config for save dir

logger = logging.getLogger(__name__)

class FileManager:
    """Handles file system operations like path generation and directory creation."""

    def __init__(self):
        self.save_directory = self._get_save_directory()
        self._ensure_directory_exists(self.save_directory)

    def _get_save_directory(self) -> str:
        """
        Determines the absolute path for the save directory from config.
        Defaults to 'screenshots' relative to the script if not set or relative.
        """
        configured_dir = config_manager.get("GENERAL", "save_directory", fallback="screenshots")
        # Check if it's an absolute path
        if os.path.isabs(configured_dir):
            return configured_dir
        else:
            # Assume relative to project root or script location
            # Safest might be relative to the main script or project root.
            # Let's use project root assuming standard execution context.
            project_root = Path(__file__).parent.parent.parent # src -> project root
            abs_path = os.path.join(project_root, configured_dir)
            logger.info(f"Relative save directory '{configured_dir}' resolved to absolute path: '{abs_path}'")
            return abs_path


    def _ensure_directory_exists(self, dir_path: str):
        """Creates the directory if it doesn't exist."""
        try:
            os.makedirs(dir_path, exist_ok=True)
            logger.info(f"Ensured save directory exists: {dir_path}")
        except OSError as e:
            logger.error(f"Failed to create directory '{dir_path}': {e}", exc_info=True)
            # Depending on severity, you might want to raise an exception
            # or fall back to a temporary directory. For now, log the error.
            # raise # Re-raise if directory creation is critical

    def get_save_path(self, filename: str, extension: Optional[str] = None) -> str:
        """
        Constructs the full path for saving a file in the managed save directory.

        Args:
            filename: The base name of the file (without extension).
            extension: The file extension (e.g., "png", "docx"), without the leading dot.

        Returns:
            The absolute path for the file.
        """
        if extension:
                # Remove leading dot if present, then add one
                clean_extension = extension.lstrip('.')
                full_filename = f"{filename}.{clean_extension}"
        else:
                full_filename = filename

        # Refresh save directory path in case config changed (optional)
        # self.save_directory = self._get_save_directory()
        # self._ensure_directory_exists(self.save_directory)

        path = os.path.join(self.save_directory, full_filename)
        logger.debug(f"Generated save path: {path}")
        return path

    def update_save_directory(self):
        """Reloads the save directory from config and ensures it exists."""
        logger.info("Updating save directory path from config...")
        self.save_directory = self._get_save_directory()
        self._ensure_directory_exists(self.save_directory)


# --- Singleton Instance ---
file_manager = FileManager()