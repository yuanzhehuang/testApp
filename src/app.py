import os
import threading
import time
import logging
from io import BytesIO
from typing import Optional, List, Tuple

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

# Utilities
from src.utils.file_manager import file_manager
from src.utils.image_utils import save_image_to_bytes

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

        # --- Load Configuration ---
        self.screenshot_interval = config_manager.get_int("GENERAL", "screenshot_interval", fallback=10)
        self.enable_blurring = config_manager.get_boolean("BLUR", "enable_blurring", fallback=False)
        self.enable_hotkeys = config_manager.get_boolean("HOTKEYS", "enabled", fallback=True)

        # --- Setup UI ---
        self.title(f"Screenshot Tool v{self.app_version}")
        self.geometry("600x550") # Adjusted size
        self.minsize(450, 400) # Min size
        self._setup_ui()

        # --- Initialize Hotkeys ---
        if self.enable_hotkeys:
            self.hotkeys = GlobalHotkeys(self)
            self.hotkeys.start()
        else:
            logger.warning("Global hotkeys are disabled in config.")

        logger.info("ScreenshotApp initialized successfully.")


    def _setup_ui(self):
        """Configures the main application window UI elements."""
        logger.debug("Setting up main UI.")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1) # Allow history frame to expand

        # --- Header Frame ---
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1) # Make label expand

        # Logo (optional)
        try:
            logo_path = os.path.join(config_manager.get("GENERAL", "asset_directory", fallback="assets"), "cd_logo.png")
            if os.path.exists(logo_path):
                self.logo_image = ctk.CTkImage(Image.open(logo_path), size=(120, 43)) # Adjust size as needed
                logo_label = ctk.CTkLabel(header_frame, image=self.logo_image, text="")
                logo_label.grid(row=0, column=0, padx=(10, 20), pady=10)
            else:
                logger.warning(f"Logo file not found at: {logo_path}")
        except Exception as e:
            logger.error(f"Error loading logo: {e}")

        header_title = ctk.CTkLabel(header_frame, text="Screenshot Capture Tool", font=ctk.CTkFont(size=16, weight="bold"))
        header_title.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        # --- History Frame ---
        self.history_frame = ctk.CTkFrame(self)
        self.history_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        self.history_frame.grid_columnconfigure(0, weight=1)

        history_label = ctk.CTkLabel(self.history_frame, text="Screenshot History (Last 5)", font=ctk.CTkFont(weight="bold"))
        history_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        # Placeholders for history items
        self.history_widgets: List[Tuple[ctk.CTkLabel, ctk.CTkLabel]] = []
        for i in range(5):
                # Frame to hold image num and title side-by-side
            item_frame = ctk.CTkFrame(self.history_frame, fg_color="transparent")
            item_frame.grid(row=i + 1, column=0, padx=10, pady=2, sticky="ew")
            item_frame.grid_columnconfigure(1, weight=1)

            img_num_label = ctk.CTkLabel(item_frame, text=f"-", width=20) # Fixed width for alignment
            img_num_label.grid(row=0, column=0, padx=(0, 5), pady=2, sticky="w")

            title_label = ctk.CTkLabel(item_frame, text="- No Screenshot -")
            title_label.grid(row=0, column=1, padx=5, pady=2, sticky="w")
            self.history_widgets.append((img_num_label, title_label))

        # --- Control Frame ---
        control_frame = ctk.CTkFrame(self)
        control_frame.grid(row=2, column=0, padx=10, pady=(5, 10), sticky="ew")
        # Make buttons distribute space evenly
        control_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        # Buttons
        self.btn_manual_capture = ctk.CTkButton(control_frame, text="Manual Capture", command=self.take_and_store_screenshot)
        self.btn_manual_capture.grid(row=0, column=0, padx=5, pady=10)

        self.btn_auto_capture = ctk.CTkButton(control_frame, text="Start Auto Capture", command=self.toggle_auto_capture)
        self.btn_auto_capture.grid(row=0, column=1, padx=5, pady=10)

        self.btn_save_word = ctk.CTkButton(control_frame, text="Save to Word", command=self.save_screenshots_to_word)
        self.btn_save_word.grid(row=0, column=2, padx=5, pady=10)

        self.btn_clear = ctk.CTkButton(control_frame, text="Clear Screenshots", command=self.clear_screenshots)
        self.btn_clear.grid(row=0, column=3, padx=5, pady=10)

        self.btn_settings = ctk.CTkButton(control_frame, text="Settings", command=self.open_settings_window)
        self.btn_settings.grid(row=0, column=4, padx=5, pady=10)

        # --- Status Bar ---
        # (Could add a status bar at the bottom if needed)
        # self.status_label = ctk.CTkLabel(self, text="Ready", anchor="w")
        # self.status_label.grid(row=3, column=0, padx=10, pady=(5,5), sticky="ew")

    def update_history(self):
        """Updates the screenshot history display in the UI."""
        logger.debug("Updating history display.")
        # Get the last 5 titles (or fewer if less than 5 exist)
        last_5_titles = self.screenshot_titles[-5:]
        num_screenshots = len(self.screenshots)

        for i, (num_label, title_label) in enumerate(self.history_widgets):
            if i < len(last_5_titles):
                # Calculate the actual index from the end
                actual_index = num_screenshots - len(last_5_titles) + i
                num_label.configure(text=f"{actual_index + 1}.")
                title_label.configure(text=last_5_titles[i])
            else:
                num_label.configure(text="-")
                title_label.configure(text="- No Screenshot -")

    def take_and_store_screenshot(self, auto_mode=False):
        """Captures, processes (if enabled), and stores a screenshot."""
        logger.info(f"Taking screenshot (Auto Mode: {auto_mode}).")
        screenshot_pil = take_screenshot() # Gets a PIL image

        if screenshot_pil is None:
            logger.error("Failed to capture screenshot.")
            showerror("Capture Error", "Could not take screenshot.")
            return

        # Process blurring if enabled
        processed_img = screenshot_pil
        if config_manager.get_boolean("BLUR", "enable_blurring", fallback=False):
            logger.debug("Blurring enabled, processing screenshot.")
            try:
                processed_img = blur_sensitive_data(screenshot_pil)
                if processed_img is None: # Handle case where blurring fails
                        logger.warning("Blurring returned None, using original screenshot.")
                        processed_img = screenshot_pil
            except Exception as e:
                logger.error(f"Error during image blurring: {e}", exc_info=True)
                showerror("Blurring Error", f"Failed to blur image: {e}")
                # Decide whether to proceed with the unblurred image or stop
                processed_img = screenshot_pil # Fallback to original

        # Convert PIL image to BytesIO for in-memory storage
        img_io = save_image_to_bytes(processed_img)
        if img_io:
            title = f"Screenshot {len(self.screenshots) + 1}"
            if auto_mode:
                title += " (Auto)"
            self.screenshots.append(img_io)
            self.screenshot_titles.append(title)
            self.update_history()
            logger.info(f"Stored screenshot: '{title}'")
            # self.status_label.configure(text=f"Captured: {title}")
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
            self.update_history()
            # self.status_label.configure(text=f"Removed: {removed_title}")
        except IndexError:
                logger.warning("IndexError during removal, list likely empty.")
                showinfo("Info", "No more screenshots to remove.")


    def _auto_capture_thread(self):
        """Thread target for automatic screenshot capture."""
        self.is_capturing = True
        logger.info(f"Auto-capture started. Interval: {self.screenshot_interval} seconds.")

        while not self.stop_event.is_set():
            # Use self.after to schedule the screenshot on the main GUI thread
            self.after(0, self.take_and_store_screenshot, True) # Pass auto_mode=True
            # Wait for the specified interval, checking the stop event frequently
            self.stop_event.wait(self.screenshot_interval)

        self.is_capturing = False
        logger.info("Auto-capture thread stopped.")
            # Ensure button state is updated from the main thread
        self.after(0, self._update_auto_capture_button)


    def toggle_auto_capture(self):
        """Starts or stops the automatic screenshot capture."""
        if not self.is_capturing:
            self.stop_event.clear()
            # Read interval fresh in case it changed in settings
            self.screenshot_interval = config_manager.get_int("GENERAL", "screenshot_interval", fallback=10)
            if self.screenshot_interval <= 0:
                showerror("Invalid Interval", "Screenshot interval must be positive.")
                return

            # Start the thread
            thread = threading.Thread(target=self._auto_capture_thread, daemon=True)
            thread.start()
            self.is_capturing = True # Set flag immediately
            logger.info("Attempting to start auto-capture.")
        else:
            self.stop_event.set() # Signal the thread to stop
            logger.info("Attempting to stop auto-capture.")

        # Update button state immediately for responsiveness
        self._update_auto_capture_button()


    def _update_auto_capture_button(self):
        """ Updates the text and color of the auto-capture button based on state. """
        if self.is_capturing:
            self.btn_auto_capture.configure(text="Stop Auto Capture", fg_color="red", hover_color="darkred")
        else:
            self.btn_auto_capture.configure(text="Start Auto Capture", fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"], hover_color=ctk.ThemeManager.theme["CTkButton"]["hover_color"])


    def save_screenshots_to_word(self):
        """Saves captured screenshots to a Word document and potentially uploads it."""
        if not self.screenshots:
            showwarning("No Screenshots", "No screenshots have been taken yet.")
            return

        doc_path = save_to_word(self.screenshots, self.screenshot_titles) # Use the dedicated function

        if doc_path:
            showinfo("Success", f"Word document saved as:\n{doc_path}")
            # Ask user if they want to upload
            ask_file_upload(self, doc_path) # Pass self if needed by dialog
        else:
            showerror("Save Error", "Failed to save Word document.")


    def clear_screenshots(self):
        """Clears all stored screenshots and updates the UI."""
        if not self.screenshots:
            showinfo("Info", "Screenshot list is already empty.")
            return

        self.screenshots.clear()
        self.screenshot_titles.clear()
        self.update_history()
        # self.status_label.configure(text="Screenshots cleared.")
        logger.info("All screenshots cleared.")
        showinfo("Cleared", "All screenshots have been removed.")


    def open_settings_window(self):
            """Opens the settings window."""
            if self.settings_window is None or not self.settings_window.winfo_exists():
                logger.debug("Opening settings window.")
                self.settings_window = SettingsWindow(self)  # Pass main app reference
                self.settings_window.grab_set() # Make settings window modal
            else:
                logger.debug("Settings window already open.")
                self.settings_window.focus() # Bring to front if already open


    def apply_settings_changes(self):
        """Applies changes made in the settings window."""
        logger.info("Applying settings changes.")
        # Re-read relevant settings from config
        self.screenshot_interval = config_manager.get_int("GENERAL", "screenshot_interval", fallback=10)
        self.enable_blurring = config_manager.get_boolean("BLUR", "enable_blurring", fallback=False)

        # Potentially update UI elements if settings affect them directly
        # e.g., update tooltips or status indicators
        # Example: self.status_label.configure(text=f"Interval: {self.screenshot_interval}s")

        # Restart hotkeys if their enabled status changed
        new_hotkeys_enabled = config_manager.get_boolean("HOTKEYS", "enabled", fallback=True)
        if new_hotkeys_enabled != self.enable_hotkeys:
            logger.info(f"Hotkey enabled status changed to {new_hotkeys_enabled}. Restarting listener.")
            self.enable_hotkeys = new_hotkeys_enabled
            if self.hotkeys:
                self.hotkeys.stop() # Stop existing listener if any
            if self.enable_hotkeys:
                self.hotkeys = GlobalHotkeys(self) # Recreate and start
                self.hotkeys.start()
            else:
                self.hotkeys = None
        elif self.hotkeys: # If hotkeys are enabled and haven't been stopped, re-register with new keys
            logger.info("Refreshing hotkey bindings based on config.")
            self.hotkeys.reregister_hotkeys()


    def close_app(self):
        """Performs cleanup before closing the application."""
        logger.info("Close requested. Cleaning up...")
        if self.is_capturing:
            self.stop_event.set() # Ensure auto-capture stops
        if self.hotkeys:
            self.hotkeys.stop() # Stop hotkey listener
        self.destroy() # Close the main window

    def on_closing(self):
            """Handles the event when the window's close button is pressed."""
            self.close_app()