import logging
import customtkinter as ctk
from tkinter import messagebox # Use standard messagebox for simple confirmations

from src.config.config_manager import config_manager
from src.config.env_manager import env_manager
# Import dialogs if needed for this window specifically
from src.ui.dialogs import showinfo, showerror

logger = logging.getLogger(__name__)

class SettingsWindow(ctk.CTkToplevel):
    """A window for configuring application settings."""

    def __init__(self, parent_app):
        super().__init__(parent_app)
        self.parent_app = parent_app # Reference to the main ScreenshotApp instance

        self.title("Settings")
        # self.geometry("450x550") # Adjust size as needed
        self.resizable(False, False)
        self.transient(parent_app) # Keep on top of parent
        self.grab_set() # Make modal

        # --- Variables to hold settings ---
        # General
        self.save_dir_var = ctk.StringVar()
        self.interval_var = ctk.StringVar()
        # Blur
        self.blur_enabled_var = ctk.BooleanVar()
        self.blur_kernel_var = ctk.StringVar()
        self.blur_intensity_var = ctk.StringVar()
        # Hotkeys
        self.hotkeys_enabled_var = ctk.BooleanVar()
        self.hk_screenshot_var = ctk.StringVar()
        self.hk_undo_var = ctk.StringVar()
        self.hk_toggle_auto_var = ctk.StringVar()
        # Integration (Tokens/Secrets are handled via EnvManager, paths/URIs here)
        self.jira_uri_var = ctk.StringVar()
        self.jtmF_uri_var = ctk.StringVar()
        # self.sharepoint_secret_var = ctk.StringVar() # Avoid displaying secrets directly

        self._load_settings()
        self._setup_ui()

        logger.debug("Settings window initialized.")

    def _load_settings(self):
        """Load current settings from ConfigManager and EnvManager."""
        logger.debug("Loading settings into variables.")
        # General
        self.save_dir_var.set(config_manager.get("GENERAL", "save_directory", fallback="screenshots"))
        self.interval_var.set(str(config_manager.get_int("GENERAL", "screenshot_interval", fallback=10)))
        # Blur
        self.blur_enabled_var.set(config_manager.get_boolean("BLUR", "enable_blurring", fallback=False))
        self.blur_kernel_var.set(config_manager.get("BLUR", "blur_kernel", fallback="15,15"))
        self.blur_intensity_var.set(str(config_manager.get_int("BLUR", "blur_intensity", fallback=35)))
        # Hotkeys
        self.hotkeys_enabled_var.set(config_manager.get_boolean("HOTKEYS", "enabled", fallback=True))
        self.hk_screenshot_var.set(config_manager.get("HOTKEYS", "screenshot_hotkey", fallback="ctrl+shift+s"))
        self.hk_undo_var.set(config_manager.get("HOTKEYS", "undo_hotkey", fallback="ctrl+shift+z"))
        self.hk_toggle_auto_var.set(config_manager.get("HOTKEYS", "toggle_auto_capture", fallback="ctrl+shift+a"))
        # Integration URIs
        self.jira_uri_var.set(config_manager.get("JIRA", "API_URI", fallback=""))
        self.jtmF_uri_var.set(config_manager.get("JTMF", "API_URI", fallback=""))
        # Note: We don't load secrets like API tokens into UI fields for security.
        # Users should manage these via the .env file or be prompted when needed.

    def _setup_ui(self):
        """Creates the UI elements for the settings window."""
        logger.debug("Setting up settings UI.")
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(padx=15, pady=15, fill="both", expand=True)

        tabview = ctk.CTkTabview(main_frame)
        tabview.pack(fill="both", expand=True)

        tab_general = tabview.add("General")
        tab_blur = tabview.add("Blurring")
        tab_hotkeys = tabview.add("Hotkeys")
        tab_integration = tabview.add("Integration")

        self._setup_general_tab(tab_general)
        self._setup_blur_tab(tab_blur)
        self._setup_hotkeys_tab(tab_hotkeys)
        self._setup_integration_tab(tab_integration)

        # --- Save/Cancel Buttons ---
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", pady=(10, 0))
        # Center buttons in the frame
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        save_button = ctk.CTkButton(button_frame, text="Save & Apply", command=self._save_settings)
        save_button.grid(row=0, column=0, padx=10, pady=10, sticky="e")

        cancel_button = ctk.CTkButton(button_frame, text="Cancel", command=self.destroy, fg_color="gray")
        cancel_button.grid(row=0, column=1, padx=10, pady=10, sticky="w")


    def _create_setting_row(self, parent, label_text, string_var, row_num, tooltip=None):
            """Helper to create a label and entry row."""
            label = ctk.CTkLabel(parent, text=label_text)
            label.grid(row=row_num, column=0, padx=10, pady=5, sticky="w")
            entry = ctk.CTkEntry(parent, textvariable=string_var, width=250) # Adjust width
            entry.grid(row=row_num, column=1, padx=10, pady=5, sticky="ew")
            parent.grid_columnconfigure(1, weight=1) # Allow entry to expand
            # Add tooltip if needed (would require an external tooltip library or basic implementation)
            if tooltip:
                # Simple example: Use default messagebox for info - replace with a proper tooltip
                # help_button = ctk.CTkButton(parent, text="?", width=20, command=lambda t=tooltip: showinfo("Help", t))
                # help_button.grid(row=row_num, column=2, padx=5, pady=5)
                pass # Placeholder for tooltip implementation

    def _setup_general_tab(self, tab):
            self._create_setting_row(tab, "Save Directory:", self.save_dir_var, 0, tooltip="Folder where screenshots and documents are saved.")
            self._create_setting_row(tab, "Auto-Screenshot Interval (sec):", self.interval_var, 1, tooltip="Time between automatic captures.")

    def _setup_blur_tab(self, tab):
            cb_blur = ctk.CTkCheckBox(tab, text="Enable Sensitive Data Blurring", variable=self.blur_enabled_var)
            cb_blur.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="w")
            self._create_setting_row(tab, "Blur Kernel (width,height):", self.blur_kernel_var, 1, tooltip="Size of the blur area (odd numbers, e.g., 15,15).")
            self._create_setting_row(tab, "Blur Intensity:", self.blur_intensity_var, 2, tooltip="Strength of the blur effect (positive integer).")

    def _setup_hotkeys_tab(self, tab):
            cb_hotkeys = ctk.CTkCheckBox(tab, text="Enable Global Hotkeys", variable=self.hotkeys_enabled_var)
            cb_hotkeys.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="w")
            self._create_setting_row(tab, "Manual Screenshot:", self.hk_screenshot_var, 1, tooltip="Key combination (e.g., ctrl+shift+s).")
            self._create_setting_row(tab, "Remove Last Screenshot:", self.hk_undo_var, 2, tooltip="Key combination (e.g., ctrl+shift+z).")
            self._create_setting_row(tab, "Toggle Auto-Capture:", self.hk_toggle_auto_var, 3, tooltip="Key combination (e.g., ctrl+shift+a).")
            # Add note about library specifics (e.g., use lowercase, '+' separator)
            note = ctk.CTkLabel(tab, text="Note: Use '+' to combine keys (e.g., ctrl+alt+delete). Use lowercase letters.", wraplength=350, justify="left")
            note.grid(row=4, column=0, columnspan=2, padx=10, pady=(10,5), sticky="w")

    def _setup_integration_tab(self, tab):
            self._create_setting_row(tab, "JIRA Base URL:", self.jira_uri_var, 0, tooltip="Your JIRA instance URL (e.g., https://your-domain.atlassian.net).")
            self._create_setting_row(tab, "JTMF Base URL:", self.jtmF_uri_var, 1, tooltip="Your JTMF instance URL.")

            # --- Token Management Section ---
            token_frame = ctk.CTkFrame(tab, fg_color="transparent")
            token_frame.grid(row=2, column=0, columnspan=2, pady=15, sticky="ew")

            token_label = ctk.CTkLabel(token_frame, text="API Tokens / Secrets:", font=ctk.CTkFont(weight="bold"))
            token_label.pack(anchor="w", padx=10)

            token_note = ctk.CTkLabel(token_frame, text="API Tokens are stored securely in the .env file.\nUse the buttons below to update them if needed.", wraplength=350, justify="left")
            token_note.pack(anchor="w", padx=10, pady=5)

            btn_jira = ctk.CTkButton(token_frame, text="Set JIRA Token", command=lambda: self._update_secret("JIRA_API_TOKEN", "JIRA API Token"))
            btn_jira.pack(side="left", padx=10, pady=5)

            btn_jtmf = ctk.CTkButton(token_frame, text="Set JTMF Token", command=lambda: self._update_secret("JTMF_API_TOKEN", "JTMF API Token"))
            btn_jtmf.pack(side="left", padx=10, pady=5)

            # btn_sp = ctk.CTkButton(token_frame, text="Set SharePoint Secret", command=lambda: self._update_secret("SHAREPOINT_CLIENT_SECRET", "SharePoint Client Secret"))
            # btn_sp.pack(side="left", padx=10, pady=5) # Uncomment if needed

    def _update_secret(self, secret_key, prompt_title):
            """Prompts the user for a secret and saves it using EnvManager."""
            current_value = env_manager.get_secret(secret_key) # Get current value for info/masking
            prompt_text = f"Enter the new {prompt_title}:"
            if current_value:
                # Mask existing value for security - show only first/last few chars?
                # masked_value = current_value[:2] + "****" + current_value[-2:] if len(current_value) > 4 else "****"
                prompt_text += f"\n(Leave blank to keep existing)" # Or show masked value
            else:
                prompt_text += "\n(Required for integration)"

            new_value = ctk.CTkInputDialog(text=prompt_text, title=prompt_title).get_input()

            if new_value is not None: # User provided input (even if empty string)
                if new_value: # User entered a non-empty value
                    if env_manager.set_secret(secret_key, new_value):
                        showinfo("Secret Updated", f"{prompt_title} has been updated in the .env file.")
                    else:
                        showerror("Save Error", f"Failed to save {prompt_title} to the .env file.")
                elif current_value: # User entered blank, but a value existed
                    logger.info(f"User entered blank, keeping existing value for {secret_key}.")
                    showinfo("Secret Unchanged", f"{prompt_title} was not changed.")
                # Else: User entered blank and no value existed - do nothing or confirm removal? For now, do nothing.

            # No 'else' needed if user pressed Cancel (new_value is None)


    def _validate_settings(self) -> bool:
        """Validate the entered settings before saving."""
        try:
            # Interval
            interval = int(self.interval_var.get())
            if interval <= 0:
                showerror("Validation Error", "Screenshot interval must be a positive number.")
                return False

            # Blur Kernel (basic check)
            kernel_parts = self.blur_kernel_var.get().split(',')
            if len(kernel_parts) != 2 or not all(p.strip().isdigit() and int(p.strip()) > 0 for p in kernel_parts):
                    showerror("Validation Error", "Blur Kernel must be two positive numbers separated by a comma (e.g., 15,15).")
                    return False

            # Blur Intensity
            intensity = int(self.blur_intensity_var.get())
            if intensity <= 0:
                    showerror("Validation Error", "Blur Intensity must be a positive number.")
                    return False

            # Hotkeys (basic check for empty) - validation happens in 'keyboard' lib mostly
            if not self.hk_screenshot_var.get() or not self.hk_undo_var.get() or not self.hk_toggle_auto_var.get():
                    if self.hotkeys_enabled_var.get(): # Only warn if hotkeys are enabled
                        showerror("Validation Error", "Hotkey fields cannot be empty if hotkeys are enabled.")
                        return False

            # URIs (basic check for empty if needed - allow empty if optional)
            # if not self.jira_uri_var.get() or not self.jtmF_uri_var.get():
            #     showerror("Validation Error", "API Base URLs cannot be empty.")
            #     return False

            return True # All basic checks passed

        except ValueError:
                showerror("Validation Error", "Invalid number format entered for Interval or Blur Intensity.")
                return False
        except Exception as e:
                showerror("Validation Error", f"An error occurred during validation: {e}")
                logger.error(f"Validation error: {e}", exc_info=True)
                return False


    def _save_settings(self):
        """Validates and saves the settings to config.ini."""
        if not self._validate_settings():
                return # Stop saving if validation fails

        logger.info("Saving settings...")
        try:
            # General
            config_manager.set("GENERAL", "save_directory", self.save_dir_var.get())
            config_manager.set("GENERAL", "screenshot_interval", int(self.interval_var.get()))
            # Blur
            config_manager.set("BLUR", "enable_blurring", self.blur_enabled_var.get())
            config_manager.set("BLUR", "blur_kernel", self.blur_kernel_var.get())
            config_manager.set("BLUR", "blur_intensity", int(self.blur_intensity_var.get()))
            # Hotkeys
            config_manager.set("HOTKEYS", "enabled", self.hotkeys_enabled_var.get())
            config_manager.set("HOTKEYS", "screenshot_hotkey", self.hk_screenshot_var.get().lower()) # Store lowercase
            config_manager.set("HOTKEYS", "undo_hotkey", self.hk_undo_var.get().lower())
            config_manager.set("HOTKEYS", "toggle_auto_capture", self.hk_toggle_auto_var.get().lower())
            # Integration
            config_manager.set("JIRA", "API_URI", self.jira_uri_var.get().rstrip('/')) # Remove trailing slash
            config_manager.set("JTMF", "API_URI", self.jtmF_uri_var.get().rstrip('/'))

            # Save the config file
            if config_manager.save_config():
                    showinfo("Settings Saved", "Settings have been saved successfully.\nSome changes may require restarting the application.")
                    # Tell the main app to apply changes that can be applied live
                    self.parent_app.apply_settings_changes()
                    self.destroy() # Close the settings window
            else:
                showerror("Save Error", "Failed to write settings to config.ini.")

        except ValueError:
            # This ideally shouldn't happen if validation passed, but as a fallback
            showerror("Save Error", "Invalid numeric value encountered while saving.")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}", exc_info=True)
            showerror("Save Error", f"An unexpected error occurred while saving settings:\n{e}")