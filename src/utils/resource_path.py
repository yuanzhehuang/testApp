# src/utils/resource_path.py

import sys
import os
import logging

logger = logging.getLogger(__name__)

def resource_path(relative_path: str) -> str:
    """
    Get the absolute path to a resource file.
    Works for development mode and for PyInstaller/cx_Freeze executables.

    Args:
        relative_path: The path to the resource relative to the project root
                       (e.g., "assets/logo.png", "config.ini").

    Returns:
        The absolute path to the resource.
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        # This attribute exists when the code runs inside a bundled executable.
        base_path = sys._MEIPASS
        logger.debug(f"Running in PyInstaller bundle, _MEIPASS: {base_path}")
    except AttributeError:
        # sys._MEIPASS attribute not found, so we are likely running in
        # normal Python development mode.
        # Assume the project root is two levels up from this utils directory
        # (src/utils -> src -> project_root)
        # Adjust this if your directory structure is different!
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        logger.debug(f"Running in development mode, base path: {base_path}")
    except Exception as e:
        # Fallback in case of unexpected errors
        logger.error(f"Unexpected error determining base path: {e}. Defaulting to CWD.")
        base_path = os.path.abspath(".") # Use current working directory as a last resort


    # Construct the absolute path to the resource
    final_path = os.path.join(base_path, relative_path.replace('/', os.sep)) # Ensure correct path separators
    logger.debug(f"Resolved resource path for '{relative_path}': '{final_path}'")
    return final_path