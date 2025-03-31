import logging
from io import BytesIO
from typing import Optional

from PIL import Image # Pillow

from src.config.config_manager import config_manager

logger = logging.getLogger(__name__)

def save_image_to_bytes(image: Image.Image) -> Optional[BytesIO]:
    """
    Saves a PIL Image to an in-memory BytesIO stream.

    Args:
        image: The PIL Image object to save.

    Returns:
        A BytesIO stream containing the image data, or None on error.
    """
    if not isinstance(image, Image.Image):
            logger.error("Invalid input: 'image' must be a PIL Image object.")
            return None

    try:
        img_format = config_manager.get("GENERAL", "image_format", fallback="png").upper()
        # Validate format if necessary (e.g., check against Image.SAVE.keys())
        if img_format not in Image.SAVE:
                logger.warning(f"Unsupported image format '{img_format}' specified in config. Defaulting to PNG.")
                img_format = "PNG"

        img_io = BytesIO()
        image.save(img_io, format=img_format)
        img_io.seek(0) # Reset stream position to the beginning
        logger.debug(f"Image saved to BytesIO stream in {img_format} format.")
        return img_io
    except Exception as e:
        logger.error(f"Error saving image to BytesIO stream: {e}", exc_info=True)
        return None

# Add other image-related utility functions here if needed
# e.g., resize_image, convert_image_format, etc.