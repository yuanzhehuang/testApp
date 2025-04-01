import os
import threading
import time
import logging
from io import BytesIO
from typing import Optional, List, Tuple # Keep Tuple if used elsewhere, not needed for history now

import customtkinter as ctk
from PIL import Image

# Configuration and Core Modules
from src.config.config_manager import config_manager
from src.core.hotkeys import GlobalHotkeys

# Features
from src.features.screenshot.capture import take_screenshot
from src.features.screenshot.processing import blur_sensitive_data
from src.features.uploader.word_exporter import save_to_word
from src.features.uploader.api_clients import ask_file_upload # Moved dialog here

# UI Elements
from src.ui.settings_window import SettingsWindow
from src.ui.dialogs import showinfo, showwarning, showerror # Use centralized dialogs
from src.ui.history_view import HistoryView # <-- Import the new HistoryView

# Utilities
from src.utils.file_manager import file_manager
from src.utils.image_utils import save_image_to_bytes
from src.utils.resource_path import resource_path # Import resource_path helper

logger = logging.getLogger(__name__)

class ScreenshotApp(ctk.CTk):
    """Main application class for the Screenshot Tool."""

    def __init__(self):
        super().__init__()
        logger.info("Initializing ScreenshotApp...")

        # --- Core Attributes ---
        self.app_version = "1.0"
        self.screenshots: List[BytesIO] = [] # Store images in memory (BytesIO)
        self.screenshot_titles: List[str] = []
        self.is_capturing: bool = False
        self.stop_event = threading.Event()
        self.hotkeys: Optional[GlobalHotkeys] = None
        self.settings_window: Optional[SettingsWindow] = None
        self.history_view: Optional[HistoryView] = None # <-- Add placeholder for HistoryView instance

        # --- Load Configuration ---
        self.screenshot_interval = config_manager.get_int("GENERAL", "screenshot_interval", fallback=10)
        self.enable_blurring = config_manager.get_boolean("BLUR", "enable_blurring", fallback=False)
        self.enable_hotkeys = config_manager.get_boolean("HOTKEYS", "enabled", fallback=True)
        self.num_history_items = 5 # Or make this configurable

        # --- Setup UI ---
        self.title(f"Screenshot Tool v{self.app_version}")
        self.geometry("800x425") # Adjusted size
        self.minsize(750, 425) # Min size
        self._setup_ui()

        # --- Initialize Hotkeys ---
        if self.enable_hotkeys:
            self.hotkeys = GlobalHotkeys(self)
            self.hotkeys.start()
        else:
            logger.warning("Global hotkeys are disabled in config.")

        self.protocol("WM_DELETE_WINDOW", self.on_closing) # Handle window close cleanly

        logger.info("ScreenshotApp initialized successfully.")


    def _setup_ui(self):
        """Configures the main application window UI elements."""
        logger.debug("Setting up main UI.")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1) # Allow history frame container to expand

        # --- Header Frame ---
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1) # Make label expand

        # Logo (optional)
        try:
            # Use resource_path to find assets correctly when packaged
            logo_path = resource_path(os.path.join("assets", "TD_Canada_Trust_logo.png")) # Adjusted to use TD logo based on screenshot
            if os.path.exists(logo_path):
                self.logo_image = ctk.CTkImage(Image.open(logo_path), size=(60, 60)) # Adjust size as needed
                logo_label = ctk.CTkLabel(header_frame, image=self.logo_image, text="")
                logo_label.grid(row=0, column=0, padx=(10, 20), pady=10)
            else:
                logger.warning(f"Logo file not found at resolved path: {logo_path}")
        except Exception as e:
            logger.error(f"Error loading logo: {e}", exc_info=True)

        header_title = ctk.CTkLabel(header_frame, text="Screenshot Capture Tool", font=ctk.CTkFont(size=16, weight="bold"))
        header_title.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        # --- History Frame Container ---
        # This outer frame helps manage padding/layout for the HistoryView instance
        history_container_frame = ctk.CTkFrame(self, fg_color="transparent") # Keep it transparent
        history_container_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        history_container_frame.grid_columnconfigure(0, weight=1) # Allow HistoryView inside to expand horizontally
        history_container_frame.grid_rowconfigure(0, weight=1) # Allow HistoryView inside to expand vertically

        # --- Instantiate and Grid the HistoryView ---
        # Pass the container frame as the master
        self.history_view = HistoryView(master=history_container_frame,
                                        num_items_to_display=self.num_history_items)
                                        # You can pass border_width etc. here if needed:
                                        # border_width=1, border_color=("gray70", "gray30"))
        self.history_view.grid(row=0, column=0, padx=0, pady=0, sticky="nsew") # Fill the container

        # --- Control Frame ---
        control_frame = ctk.CTkFrame(self)
        control_frame.grid(row=2, column=0, padx=10, pady=(5, 10), sticky="ew")
        # Make buttons distribute space evenly
        control_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1, uniform="buttons") # Use uniform grouping

        # Buttons
        self.btn_manual_capture = ctk.CTkButton(control_frame, text="Manual Capture", command=self.take_and_store_screenshot)
        self.btn_manual_capture.grid(row=0, column=0, padx=5, pady=10, sticky="ew")

        self.btn_auto_capture = ctk.CTkButton(control_frame, text="Start Auto Capture", command=self.toggle_auto_capture)
        self.btn_auto_capture.grid(row=0, column=1, padx=5, pady=10, sticky="ew")

        self.btn_save_word = ctk.CTkButton(control_frame, text="Save to Word", command=self.save_screenshots_to_word)
        self.btn_save_word.grid(row=0, column=2, padx=5, pady=10, sticky="ew")

        self.btn_clear = ctk.CTkButton(control_frame, text="Clear Screenshots", command=self.clear_screenshots)
        self.btn_clear.grid(row=0, column=3, padx=5, pady=10, sticky="ew")

        self.btn_settings = ctk.CTkButton(control_frame, text="Settings", command=self.open_settings_window)
        self.btn_settings.grid(row=0, column=4, padx=5, pady=10, sticky="ew")

        # --- Status Bar --- (Optional)
        # self.status_label = ctk.CTkLabel(self, text="Ready", anchor="w")
        # self.status_label.grid(row=3, column=0, padx=10, pady=(5,5), sticky="ew")



    def take_and_store_screenshot(self, auto_mode=False):
        """Captures, processes (if enabled), and stores a screenshot."""
        logger.info(f"Taking screenshot (Auto Mode: {auto_mode}).")
        screenshot_pil = take_screenshot()

        if screenshot_pil is None:
            logger.error("Failed to capture screenshot.")
            showerror("Capture Error", "Could not take screenshot.")
            return

        processed_img = screenshot_pil
        if config_manager.get_boolean("BLUR", "enable_blurring", fallback=False):
            logger.debug("Blurring enabled, processing screenshot.")
            try:
                processed_img = blur_sensitive_data(screenshot_pil)
                if processed_img is None:
                     logger.warning("Blurring returned None, using original screenshot.")
                     processed_img = screenshot_pil
            except Exception as e:
                logger.error(f"Error during image blurring: {e}", exc_info=True)
                showerror("Blurring Error", f"Failed to blur image: {e}")
                processed_img = screenshot_pil

        img_io = save_image_to_bytes(processed_img)
        if img_io:
            title = f"Screenshot {len(self.screenshots) + 1}"
            if auto_mode:
                title += " (Auto)"
            self.screenshots.append(img_io)
            self.screenshot_titles.append(title)

            # --- Update the history view ---
            if self.history_view:
                self.history_view.update_display(
                    titles_to_display=self.screenshot_titles[-self.num_history_items:], # Pass last N titles
                    total_screenshots=len(self.screenshots)       # Pass total count
                )
            # self.status_label.configure(text=f"Captured: {title}") # Update status if using one
            logger.info(f"Stored screenshot: '{title}'")

        else:
            logger.error("Failed to save screenshot to memory.")
            showerror("Storage Error", "Could not save screenshot to memory.")


    def remove_last_screenshot(self):
        """Removes the most recent screenshot."""
        if not self.screenshots:
            logger.info("No screenshots to remove.")
            showinfo("Info", "There are no screenshots to remove.")
            return

        try:
            removed_title = self.screenshot_titles.pop()
            self.screenshots.pop()
            logger.info(f"Removed last screenshot: '{removed_title}'")

            # --- Update the history view ---
            if self.history_view:
                 self.history_view.update_display(
                    titles_to_display=self.screenshot_titles[-self.num_history_items:],
                    total_screenshots=len(self.screenshots)
                 )
            # self.status_label.configure(text=f"Removed: {removed_title}") # Update status

        except IndexError:
             logger.warning("IndexError during removal, list likely empty.")
             showinfo("Info", "No more screenshots to remove.")


    def _auto_capture_thread(self):
        """Thread target for automatic screenshot capture."""
        self.is_capturing = True
        logger.info(f"Auto-capture started. Interval: {self.screenshot_interval} seconds.")

        while not self.stop_event.is_set():
            self.after(0, self.take_and_store_screenshot, True)
            self.stop_event.wait(self.screenshot_interval)

        self.is_capturing = False
        logger.info("Auto-capture thread stopped.")
        self.after(0, self._update_auto_capture_button)


    def toggle_auto_capture(self):
        """Starts or stops the automatic screenshot capture."""
        if not self.is_capturing:
            self.stop_event.clear()
            self.screenshot_interval = config_manager.get_int("GENERAL", "screenshot_interval", fallback=10)
            if self.screenshot_interval <= 0:
                showerror("Invalid Interval", "Screenshot interval must be positive.")
                return

            thread = threading.Thread(target=self._auto_capture_thread, daemon=True)
            thread.start()
            self.is_capturing = True
            logger.info("Attempting to start auto-capture.")
        else:
            self.stop_event.set()
            logger.info("Attempting to stop auto-capture.")

        self._update_auto_capture_button()


    def _update_auto_capture_button(self):
        """ Updates the text and color of the auto-capture button based on state. """
        if self.is_capturing:
            self.btn_auto_capture.configure(text="Stop Auto Capture", fg_color="red", hover_color="darkred")
        else:
            # Use ThemeManager to get default colors if available, otherwise hardcode fallback
            try:
                default_fg = ctk.ThemeManager.theme["CTkButton"]["fg_color"]
                default_hover = ctk.ThemeManager.theme["CTkButton"]["hover_color"]
                self.btn_auto_capture.configure(text="Start Auto Capture", fg_color=default_fg, hover_color=default_hover)
            except KeyError: # Fallback if theme doesn't define button colors explicitly
                 self.btn_auto_capture.configure(text="Start Auto Capture", fg_color="#3B8ED0", hover_color="#36719F") # Example blue


    def save_screenshots_to_word(self):
        """Saves captured screenshots to a Word document and potentially uploads it."""
        if not self.screenshots:
            showwarning("No Screenshots", "No screenshots have been taken yet.")
            return

        doc_path = save_to_word(self.screenshots, self.screenshot_titles)

        if doc_path:
            showinfo("Success", f"Word document saved as:\n{doc_path}")
            ask_file_upload(self, doc_path)
        else:
            showerror("Save Error", "Failed to save Word document.")


    def clear_screenshots(self):
        """Clears all stored screenshots and updates the UI."""
        if not self.screenshots:
            showinfo("Info", "Screenshot list is already empty.")
            return

        self.screenshots.clear()
        self.screenshot_titles.clear()
        logger.info("All screenshots cleared.")

        # --- Update the history view ---
        if self.history_view:
             self.history_view.update_display(
                 titles_to_display=[], # Empty list
                 total_screenshots=0  # Zero count
             )
        # self.status_label.configure(text="Screenshots cleared.") # Update status
        showinfo("Cleared", "All screenshots have been removed.")


    def open_settings_window(self):
         """Opens the settings window."""
         if self.settings_window is None or not self.settings_window.winfo_exists():
             logger.debug("Opening settings window.")
             self.settings_window = SettingsWindow(self)
             self.settings_window.grab_set()
         else:
             logger.debug("Settings window already open.")
             self.settings_window.focus()


    def apply_settings_changes(self):
        """Applies changes made in the settings window."""
        logger.info("Applying settings changes from main app.")
        self.screenshot_interval = config_manager.get_int("GENERAL", "screenshot_interval", fallback=10)
        self.enable_blurring = config_manager.get_boolean("BLUR", "enable_blurring", fallback=False)
        file_manager.update_save_directory() # Update file manager's path

        # Restart hotkeys if their enabled status or bindings changed
        new_hotkeys_enabled = config_manager.get_boolean("HOTKEYS", "enabled", fallback=True)
        hotkeys_changed = new_hotkeys_enabled != self.enable_hotkeys

        if self.hotkeys: # Check if hotkeys were previously running
            # Check if individual keys changed even if enabled status didn't
            current_config_keys = (
                config_manager.get("HOTKEYS", "screenshot_hotkey", fallback=""),
                config_manager.get("HOTKEYS", "undo_hotkey", fallback=""),
                config_manager.get("HOTKEYS", "toggle_auto_capture", fallback="")
            )
            previous_keys = (self.hotkeys.screenshot_key, self.hotkeys.undo_key, self.hotkeys.toggle_auto_key)
            if current_config_keys != previous_keys:
                 hotkeys_changed = True

        if hotkeys_changed or (new_hotkeys_enabled and not self.hotkeys):
            logger.info(f"Hotkey configuration changed (Enabled: {new_hotkeys_enabled}). Restarting listener.")
            self.enable_hotkeys = new_hotkeys_enabled
            if self.hotkeys:
                self.hotkeys.stop()
            if self.enable_hotkeys:
                self.hotkeys = GlobalHotkeys(self) # Recreate with potentially new key bindings loaded inside
                self.hotkeys.start()
            else:
                self.hotkeys = None


    def close_app(self):
        """Performs cleanup before closing the application."""
        logger.info("Close requested. Cleaning up...")
        if self.is_capturing:
            self.stop_event.set()
        if self.hotkeys:
            self.hotkeys.stop()
        self.destroy()


    def on_closing(self):
         """Handles the event when the window's close button is pressed."""
         self.close_app()