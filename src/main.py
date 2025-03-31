# src/main.py

import sys
import os
import customtkinter as ctk
import logging

# Ensure the src directory is in the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.app import ScreenshotApp
from src.config.logging_config import setup_logging
from src.config.config_manager import config_manager # Import config manager

logger = logging.getLogger(__name__)

def main():
    """Initializes and runs the Screenshot Application."""
    log_enabled = setup_logging()
    if log_enabled:
        logger.info("Application starting.")
    else:
        print("Logging is disabled via config.")

    try:
        # --- Theme Loading ---
        # Read appearance mode from config
        appearance_mode = config_manager.get("APPEARANCE", "appearance_mode", fallback="System")
        ctk.set_appearance_mode(appearance_mode)
        logger.info(f"Set appearance mode to: {appearance_mode}")

        # Read the theme file setting from config.ini
        theme_setting = config_manager.get("APPEARANCE", "theme_file", fallback="assets/blue.json") # Provide a built-in fallback

        # Construct the absolute path based on the setting
        if os.path.isabs(theme_setting):
            theme_path = theme_setting
        else:
            # Assume relative to project root
            theme_path = os.path.join(project_root, theme_setting)

        # --- Apply Theme ---
        if os.path.exists(theme_path):
            try:
                ctk.set_default_color_theme(theme_path)
                logger.info(f"Applied custom theme from: {theme_path}")
            except Exception as theme_error:
                logger.error(f"Error loading theme file '{theme_path}': {theme_error}. Falling back to default 'blue'.", exc_info=True)
                ctk.set_default_color_theme("blue") # Fallback to a default theme
        else:
            # Check if the setting was trying to load a built-in theme (e.g., "blue", "dark-blue", "green")
            built_in_themes = ["blue", "dark-blue", "green"]
            if theme_setting.lower() in built_in_themes:
                 ctk.set_default_color_theme(theme_setting.lower())
                 logger.info(f"Applied built-in theme: {theme_setting}")
            else:
                 logger.warning(f"Custom theme file not found at '{theme_path}'. Falling back to default 'blue'.")
                 ctk.set_default_color_theme("blue") # Fallback to a default theme
        # --- End Theme Loading ---


        app = ScreenshotApp()
        app.mainloop()

    except Exception as e:
        logger.critical(f"Critical error initializing or running the application: {e}", exc_info=True)
        # Optional: Show simple error message if GUI fails early
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Fatal Error", f"Application failed to start: {e}")
        root.destroy()
        if log_enabled: # Ensure logging happens even after GUI error popup
            logger.info("Application shutting down after fatal error.")

    finally:
        if log_enabled:
            logger.info("Application shutting down.")


if __name__ == "__main__":
    main()