import customtkinter as ctk
from typing import List
import logging

logger = logging.getLogger(__name__)

class HistoryView(ctk.CTkFrame):
    """
    A custom frame widget to display the recent screenshot history.
    """
    def __init__(self, master, num_items_to_display: int = 5, **kwargs):
        """
        Initializes the HistoryView frame.

        Args:
            master: The parent widget.
            num_items_to_display: The number of history items to show.
            **kwargs: Additional arguments passed to the CTkFrame constructor.
        """
        # Set default frame appearance if not provided via kwargs
        # Ensures the frame itself doesn't add extra borders unless specified
        frame_kwargs = {
            "fg_color": "transparent",
            "border_width": 0
        }
        frame_kwargs.update(kwargs) # Allow overriding defaults
        super().__init__(master, **frame_kwargs)

        self.num_items_to_display = num_items_to_display
        # List to store tuples of (number_label, title_label) for easy updating
        self.history_widgets: List[tuple[ctk.CTkLabel, ctk.CTkLabel]] = []

        self._setup_widgets()
        logger.debug(f"HistoryView initialized with {num_items_to_display} placeholder items.")

    def _setup_widgets(self):
        """Creates the static UI elements for the history view."""
        self.grid_columnconfigure(0, weight=1) # Allow items to expand horizontally

        # --- Header ---
        header_label = ctk.CTkLabel(self, text=f"Screenshot History (Last {self.num_items_to_display})",
                                    font=ctk.CTkFont(weight="bold"))
        header_label.grid(row=0, column=0, padx=10, pady=(5, 10), sticky="w")

        # --- History Item Placeholders ---
        for i in range(self.num_items_to_display):
            # Frame to hold image num and title side-by-side for better alignment & padding
            # Apply border/styling to this frame if you want borders around each item
            item_frame = ctk.CTkFrame(self, fg_color="transparent", border_width=1) # Example border
            item_frame.grid(row=i + 1, column=0, padx=10, pady=3, sticky="ew") # pady=3 adds spacing
            item_frame.grid_columnconfigure(1, weight=1) # Make title label expand

            # Number Label (fixed width helps alignment)
            num_label = ctk.CTkLabel(item_frame, text="-", width=30, anchor="w")
            num_label.grid(row=0, column=0, padx=(5, 5), pady=2, sticky="w")

            # Title Label
            title_label = ctk.CTkLabel(item_frame, text="- No Screenshot -", anchor="w")
            title_label.grid(row=0, column=1, padx=5, pady=2, sticky="ew") # Expand title horizontally

            # Store references for updating
            self.history_widgets.append((num_label, title_label))

    def update_display(self, titles_to_display: List[str], total_screenshots: int):
        """
        Updates the text of the history item labels based on the provided data.

        Args:
            titles_to_display: A list containing the titles of the most recent
                               screenshots to display (e.g., the last 5).
            total_screenshots: The total number of screenshots currently stored.
        """
        logger.debug(f"Updating history display. Total screenshots: {total_screenshots}. Titles to show: {len(titles_to_display)}")
        num_widgets = len(self.history_widgets)

        if len(titles_to_display) > num_widgets:
            logger.warning(f"More titles provided ({len(titles_to_display)}) than widgets available ({num_widgets}). Displaying first {num_widgets}.")
            titles_to_display = titles_to_display[:num_widgets]

        for idx, (num_label, title_label) in enumerate(self.history_widgets):
            if idx < len(titles_to_display):
                # Calculate the actual screenshot index (1-based) from the total count
                # Example: total=10, titles_to_display=5 (titles 6-10)
                # idx=0 => title 6 => actual_index = 10 - 5 + 0 = 5 (correct, 0-based for index 6)
                # idx=4 => title 10 => actual_index = 10 - 5 + 4 = 9 (correct, 0-based for index 10)
                actual_index = total_screenshots - len(titles_to_display) + idx
                num_label.configure(text=f"{actual_index + 1}.") # Display 1-based number
                title_label.configure(text=titles_to_display[idx])
            else:
                # No data for this slot
                num_label.configure(text="-")
                title_label.configure(text="- No Screenshot -")