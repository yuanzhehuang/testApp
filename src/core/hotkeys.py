
import logging
import threading
import time
import keyboard # Using the 'keyboard' library

from src.config.config_manager import config_manager

logger = logging.getLogger(__name__)

class GlobalHotkeys:
    """Manages global keyboard shortcuts for the application."""

    def __init__(self, app_instance):
        """
        Initializes the hotkey manager.

        Args:
            app_instance: The main application instance (e.g., ScreenshotApp)
                            to call methods on when hotkeys are triggered.
        """
        self.app = app_instance
        self._load_hotkeys_from_config()
        self._listener_thread = None
        self._stop_event = threading.Event()
        self._active_hotkeys = {} # Store currently registered hotkeys

    def _load_hotkeys_from_config(self):
        """Loads hotkey combinations from the config file."""
        self.screenshot_key = config_manager.get("HOTKEYS", "screenshot_hotkey", fallback="ctrl+shift+s")
        self.undo_key = config_manager.get("HOTKEYS", "undo_hotkey", fallback="ctrl+shift+z")
        self.toggle_auto_key = config_manager.get("HOTKEYS", "toggle_auto_capture", fallback="ctrl+shift+a")
        logger.info(f"Loaded hotkeys: Screenshot='{self.screenshot_key}', Undo='{self.undo_key}', ToggleAuto='{self.toggle_auto_key}'")

    def _register_hotkeys(self):
        """Registers the configured hotkeys with the keyboard listener."""
        logger.debug("Attempting to register hotkeys...")
        self._active_hotkeys = {} # Clear previous registrations

        if not config_manager.get_boolean("HOTKEYS", "enabled", fallback=True):
                logger.info("Hotkeys are disabled in config, skipping registration.")
                return

        try:
            if self.screenshot_key:
                # Use lambda to avoid issues with loop variables if registering many keys
                # Use schedule_event for thread safety if calling GUI functions directly
                # However, app methods might be designed to be thread-safe or use 'after'
                hk = keyboard.add_hotkey(self.screenshot_key, lambda: self.app.take_and_store_screenshot(auto_mode=False), trigger_on_release=False)
                self._active_hotkeys[self.screenshot_key] = hk
                logger.debug(f"Registered hotkey: '{self.screenshot_key}'")

            if self.undo_key:
                hk = keyboard.add_hotkey(self.undo_key, self.app.remove_last_screenshot, trigger_on_release=False)
                self._active_hotkeys[self.undo_key] = hk
                logger.debug(f"Registered hotkey: '{self.undo_key}'")

            if self.toggle_auto_key:
                hk = keyboard.add_hotkey(self.toggle_auto_key, self.app.toggle_auto_capture, trigger_on_release=False)
                self._active_hotkeys[self.toggle_auto_key] = hk
                logger.debug(f"Registered hotkey: '{self.toggle_auto_key}'")

            logger.info(f"Successfully registered {len(self._active_hotkeys)} hotkeys.")

        except ValueError as e:
                logger.error(f"ValueError registering hotkeys (invalid key combination?): {e}")
        except Exception as e:
            # Catch potential errors from the keyboard library (e.g., permissions on Linux/macOS)
            logger.error(f"Error registering hotkeys: {e}", exc_info=True)
            # Consider notifying the user via the app's UI if registration fails critically
            # self.app.after(0, lambda: showerror("Hotkey Error", f"Could not register hotkeys: {e}"))


    def _unregister_hotkeys(self):
        """Unregisters all currently active hotkeys."""
        logger.debug("Unregistering hotkeys...")
        count = 0
        # Use remove_hotkey with the stored handles if possible, otherwise clear all
        # For simplicity here, keyboard.remove_all_hotkeys() is often sufficient if managed solely by this class
        try:
            keyboard.remove_all_hotkeys()
            count = len(self._active_hotkeys)
            self._active_hotkeys = {} # Clear our record
            logger.info(f"Unregistered {count} hotkeys.")
        except Exception as e:
                logger.error(f"Error during hotkey unregistration: {e}", exc_info=True)


    def _listen(self):
        """Target function for the listener thread."""
        # This thread will block here until keyboard.wait() is interrupted or stop() is called.
        # keyboard hooks run in their own threads managed by the library.
        logger.info("Hotkey listener thread started.")
        try:
            # Register hotkeys within this thread's context if required by the lib,
            # but usually add_hotkey can be called from the main thread before starting.
            # self._register_hotkeys() # Registering before wait might be safer

            # keyboard.wait() blocks until the process exits or is explicitly stopped.
            # We use a loop with the stop_event for more graceful shutdown control.
            while not self._stop_event.is_set():
                # The keyboard library handles event dispatching internally.
                # We just need to keep this thread alive.
                time.sleep(0.1) # Prevent busy-waiting

        except Exception as e:
            logger.error(f"Exception in hotkey listener thread: {e}", exc_info=True)
        finally:
            logger.info("Hotkey listener thread finishing.")
            # self._unregister_hotkeys() # Ensure cleanup on exit


    def start(self):
        """Starts the hotkey listener thread."""
        if not config_manager.get_boolean("HOTKEYS", "enabled", fallback=True):
            logger.info("Hotkeys disabled, listener not starting.")
            return

        if self._listener_thread and self._listener_thread.is_alive():
            logger.warning("Hotkey listener thread already running.")
            return

        try:
            self._stop_event.clear()
            self._register_hotkeys() # Register before starting thread
            self._listener_thread = threading.Thread(target=self._listen, daemon=True)
            self._listener_thread.start()
            logger.info("Hotkey listener thread initiated.")
        except Exception as e:
                logger.error(f"Failed to start hotkey listener: {e}", exc_info=True)


    def stop(self):
        """Stops the hotkey listener thread gracefully."""
        if self._listener_thread and self._listener_thread.is_alive():
            logger.info("Stopping hotkey listener...")
            self._stop_event.set() # Signal the thread to stop
            self._unregister_hotkeys() # Unregister immediately

                # Wait for the thread to finish
            self._listener_thread.join(timeout=1.0) # Wait max 1 second
            if self._listener_thread.is_alive():
                    logger.warning("Hotkey listener thread did not stop gracefully.")
            else:
                    logger.info("Hotkey listener stopped.")
            self._listener_thread = None
        else:
            logger.debug("Hotkey listener not running or already stopped.")


    def reregister_hotkeys(self):
            """Unregisters existing hotkeys and registers them again based on current config."""
            logger.info("Re-registering hotkeys...")
            self._unregister_hotkeys()
            self._load_hotkeys_from_config() # Reload keys from config file
            self._register_hotkeys() # Register the potentially new keys
