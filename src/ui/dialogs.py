import logging
import customtkinter as ctk
from typing import Optional
from tkinter import messagebox # Use standard tkinter messageboxes

logger = logging.getLogger(__name__)

# --- Message Dialogs ---

def showinfo(title: str, message: str):
    """Displays an information message box."""
    logger.debug(f"Showing info dialog: Title='{title}', Message='{message}'")
    messagebox.showinfo(title, message)

def showwarning(title: str, message: str):
    """Displays a warning message box."""
    logger.warning(f"Showing warning dialog: Title='{title}', Message='{message}'")
    messagebox.showwarning(title, message)

def showerror(title: str, message: str):
    """Displays an error message box."""
    logger.error(f"Showing error dialog: Title='{title}', Message='{message}'")
    messagebox.showerror(title, message)

# --- Question Dialogs ---

def askyesno(title: str, message: str) -> bool:
    """Asks a yes/no question, returns True for Yes, False for No."""
    logger.debug(f"Asking yes/no dialog: Title='{title}', Message='{message}'")
    return messagebox.askyesno(title, message)

def askokcancel(title: str, message: str) -> bool:
    """Asks an ok/cancel question, returns True for OK, False for Cancel."""
    logger.debug(f"Asking ok/cancel dialog: Title='{title}', Message='{message}'")
    return messagebox.askokcancel(title, message)

def askretrycancel(title: str, message: str) -> bool:
    """Asks a retry/cancel question, returns True for Retry, False for Cancel."""
    logger.debug(f"Asking retry/cancel dialog: Title='{title}', Message='{message}'")
    return messagebox.askretrycancel(title, message)

# --- Input Dialogs ---

def askstring(title: str, prompt: str, **kwargs) -> Optional[str]:
    """
    Asks the user to enter a string using CTkInputDialog.

    Args:
        title: The dialog window title.
        prompt: The text displayed to the user.
        **kwargs: Additional keyword arguments passed to CTkInputDialog.

    Returns:
        The string entered by the user, or None if cancelled.
    """
    logger.debug(f"Asking string input dialog: Title='{title}', Prompt='{prompt}'")
    dialog = ctk.CTkInputDialog(text=prompt, title=title, **kwargs)
    # Center the dialog relative to the screen or a parent window if available
    # Basic screen centering:
    # dialog.update_idletasks()
    # screen_width = dialog.winfo_screenwidth()
    # screen_height = dialog.winfo_screenheight()
    # x = (screen_width - dialog.winfo_width()) // 2
    # y = (screen_height - dialog.winfo_height()) // 2
    # dialog.geometry(f"+{x}+{y}")
    
    result = dialog.get_input()
    logger.debug(f"String input result: {'Cancelled' if result is None else 'Provided'}")
    return result

# --- Custom Dialogs (Example - Loading Window) ---

class LoadingWindow(ctk.CTkToplevel):
    """ A simple non-blocking loading indicator window. """
    def __init__(self, parent, title="Loading...", message="Please wait..."):
            super().__init__(parent)
            self.title(title)
            self.geometry("300x100")
            self.resizable(False, False)
            self.transient(parent)
            # self.grab_set() # DO NOT grab_set for non-blocking

            self.protocol("WM_DELETE_WINDOW", self.on_close) # Handle accidental close

            label = ctk.CTkLabel(self, text=message)
            label.pack(padx=20, pady=20, expand=True, fill="both")

            # Center relative to parent
            self.update_idletasks()
            parent_x = parent.winfo_x()
            parent_y = parent.winfo_y()
            parent_w = parent.winfo_width()
            parent_h = parent.winfo_height()
            win_w = self.winfo_width()
            win_h = self.winfo_height()
            x = parent_x + (parent_w - win_w) // 2
            y = parent_y + (parent_h - win_h) // 2
            self.geometry(f"+{x}+{y}")

            self.lift() # Ensure it's visible


    def on_close(self):
            # Prevent closing via window manager, must be closed programmatically
            logger.warning("Loading window close attempt ignored.")
            pass

    def close_window(self):
            """ Safely destroys the loading window. """
            if self.winfo_exists():
                self.destroy()

# You might have more complex custom dialogs here