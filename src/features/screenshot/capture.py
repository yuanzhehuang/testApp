import logging
import pyautogui
from PIL import Image
from typing import Optional

logger = logging.getLogger(__name__)

def take_screenshot() -> Optional[Image.Image]:
    """
    Captures the primary screen using pyautogui.

    Returns:
        Optional[Image.Image]: A PIL Image object of the screenshot, or None on error.
    """
    try:
        screenshot = pyautogui.screenshot()
        # screenshot is already a PIL Image object
        logger.info("Screenshot taken successfully.")
        return screenshot
    except pyautogui.PyAutoGUIException as e:
        logger.error(f"PyAutoGUI error taking screenshot: {e}", exc_info=True)
        return None
    except Exception as e:
        # Catch potential OS-level issues (e.g., permissions, display server problems)
        logger.error(f"Unexpected error taking screenshot: {e}", exc_info=True)
        return None