import logging
from typing import Optional, Tuple, List

import cv2
import numpy as np
import pytesseract
import easyocr
import spacy
from PIL import Image

from src.config.config_manager import config_manager

logger = logging.getLogger(__name__)

# --- Configuration Loading ---
def _load_blur_settings() -> Tuple[Tuple[int, int], int]:
    """Loads blur kernel and intensity from config."""
    try:
        kernel_str = config_manager.get("BLUR", "blur_kernel", fallback="15,15")
        intensity_str = config_manager.get("BLUR", "blur_intensity", fallback="35")
        kernel = tuple(map(int, kernel_str.split(',')))
        intensity = int(intensity_str)
        if len(kernel) != 2 or kernel[0] <= 0 or kernel[1] <= 0 or intensity <= 0:
                raise ValueError("Invalid kernel or intensity values")
            # Ensure kernel dimensions are odd
        kernel = (kernel[0] | 1, kernel[1] | 1)
        logger.debug(f"Loaded blur settings: Kernel={kernel}, Intensity={intensity}")
        return kernel, intensity
    except ValueError as e:
        logger.warning(f"Invalid blur settings in config: {e}. Using defaults (15,15), 35.")
        return (15, 15), 35
    except Exception as e:
        logger.error(f"Error loading blur settings: {e}. Using defaults.", exc_info=True)
        return (15, 15), 35

BLUR_KERNEL, BLUR_INTENSITY = _load_blur_settings()


# --- OCR and NLP Initialization (Lazy Loading Recommended) ---
OCR_READER = None
NLP_MODEL = None

def get_ocr_reader():
    """Initializes and returns the EasyOCR reader instance."""
    global OCR_READER
    if OCR_READER is None:
        try:
            logger.info("Initializing EasyOCR reader (may take a moment)...")
            OCR_READER = easyocr.Reader(['en']) # Add other languages if needed
            logger.info("EasyOCR reader initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR reader: {e}", exc_info=True)
            # Propagate the error or handle it gracefully
            raise RuntimeError("Could not initialize EasyOCR") from e
    return OCR_READER

def get_nlp_model():
        """Initializes and returns the SpaCy NLP model instance."""
        global NLP_MODEL
        if NLP_MODEL is None:
            try:
                logger.info("Loading SpaCy NLP model (en_core_web_sm)...")
                # Consider making the model name configurable
                NLP_MODEL = spacy.load("en_core_web_sm")
                logger.info("SpaCy NLP model loaded.")
            except OSError as e:
                logger.error(f"Failed to load SpaCy model 'en_core_web_sm': {e}. "
                            f"Please ensure it's downloaded: python -m spacy download en_core_web_sm", exc_info=True)
                raise RuntimeError("Could not initialize SpaCy NLP model") from e
            except Exception as e:
                logger.error(f"Failed to initialize SpaCy NLP model: {e}", exc_info=True)
                raise RuntimeError("Could not initialize SpaCy NLP model") from e
        return NLP_MODEL


# --- Image Blurring Functions ---

def blur_region(image_np: np.ndarray, x_min: int, y_min: int, x_max: int, y_max: int) -> np.ndarray:
    """Applies Gaussian blur to a specified region of a NumPy image array."""
    if x_min >= x_max or y_min >= y_max:
            logger.warning(f"Invalid blur region coordinates: min=({x_min},{y_min}), max=({x_max},{y_max})")
            return image_np # Return original if coordinates are invalid

    # Ensure coordinates are within image bounds
    h, w = image_np.shape[:2]
    x_min, y_min = max(0, x_min), max(0, y_min)
    x_max, y_max = min(w, x_max), min(h, y_max)

    if x_min >= x_max or y_min >= y_max: # Check again after clamping
            logger.warning(f"Blur region became invalid after clamping to image bounds.")
            return image_np

    blur_region_view = image_np[y_min:y_max, x_min:x_max]

    if blur_region_view.size > 0:
        # Apply Gaussian Blur
        blurred = cv2.GaussianBlur(blur_region_view, BLUR_KERNEL, BLUR_INTENSITY)
        # Place the blurred region back into the original image
        image_np[y_min:y_max, x_min:x_max] = blurred
        # Optional: Draw rectangle for debugging
        # cv2.rectangle(image_np, (x_min, y_min), (x_max, y_max), (0, 0, 255), 1) # Red border
    else:
            logger.warning("Calculated blur region has zero size.")

    return image_np


def blur_numbers_pytesseract(image: Image.Image) -> Optional[Image.Image]:
    """
    Detects and blurs numeric sequences in an image using Pytesseract.

    Args:
        image: PIL Image object.

    Returns:
        Optional[Image.Image]: Processed PIL Image with numbers blurred, or None on error.
    """
    if not config_manager.get_boolean("BLUR", "enable_blurring", fallback=False):
            return image

    logger.info("Blurring numbers using Pytesseract...")
    try:
        # Convert PIL image to OpenCV format (NumPy array)
        image_np = np.array(image)
        image_cv = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR) # Pytesseract often works better with BGR

        # Use pytesseract to get detailed data including bounding boxes and confidence
        # --psm 6 assumes a single uniform block of text (adjust if needed)
        data = pytesseract.image_to_data(image_cv, output_type=pytesseract.Output.DICT, config='--psm 6')
        n_boxes = len(data['level'])

        boxes_blurred = 0
        for i in range(n_boxes):
            # Check confidence level (adjust threshold as needed)
            conf = int(data['conf'][i])
            if conf < 50: # Skip low confidence detections
                    continue

            text = data['text'][i].strip()
            # Check if the detected text contains only digits (and potentially formatting like - . ,)
            # This is a simple check; more robust regex might be needed for specific formats.
            if text.isdigit(): # Stricter: only purely digits
            # if any(char.isdigit() for char in text) and not text.isalpha(): # More lenient
                (x, y, w, h) = (data['left'][i], data['top'][i], data['width'][i], data['height'][i])
                logger.debug(f"Blurring detected number '{text}' at (x={x}, y={y}, w={w}, h={h})")
                image_np = blur_region(image_np, x, y, x + w, y + h)
                boxes_blurred += 1

        logger.info(f"Blurred {boxes_blurred} potential numeric regions (Pytesseract).")

        # Convert back to PIL Image
        return Image.fromarray(image_np)

    except pytesseract.TesseractNotFoundError:
        logger.error("Pytesseract Error: 'tesseract' command not found or not in PATH. Please install Tesseract.")
        # Return original image or raise an error? Returning original for now.
        return image
    except Exception as e:
        logger.error(f"Error during number blurring (Pytesseract): {e}", exc_info=True)
        return None # Return None to indicate failure


def blur_sensitive_data(image: Image.Image) -> Optional[Image.Image]:
    """
    Detects and blurs sensitive data (numbers, specific labels) using EasyOCR and SpaCy.

    Args:
        image: PIL Image object.

    Returns:
        Optional[Image.Image]: Processed PIL Image with sensitive data blurred, or None on error.
    """
    if not config_manager.get_boolean("BLUR", "enable_blurring", fallback=False):
            return image

    logger.info("Blurring sensitive data using EasyOCR/SpaCy...")
    try:
        # Initialize models (lazy loading)
        reader = get_ocr_reader()
        # nlp = get_nlp_model() # Uncomment if using SpaCy for NER

        image_np = np.array(image)
        image_cv_rgb = cv2.cvtColor(image_np, cv2.COLOR_BGR2RGB) # EasyOCR prefers RGB

        # Perform OCR
        # Set detail=1 for bounding boxes, paragraph=False for line-by-line
        ocr_results = reader.readtext(image_cv_rgb, detail=1, paragraph=False)

        # Define labels that might indicate sensitive info nearby
        sensitive_labels = {
            "address", "cc", "credit", "card", "number", # CC related
            "zip", "postcode", # Address related
            "ssn", "social", "security", # ID related
            "passport", "driver", "license", "dl", # ID related
            "dob", "birth", # Date of Birth
            # Add more keywords relevant to your domain
        }

        boxes_blurred = 0
        for (bbox, text, prob) in ocr_results:
            text_lower = text.lower().strip()
            logger.debug(f"OCR Result: Text='{text}', Confidence={prob:.2f}")

            # --- Blurring Strategy ---
            # 1. Blur purely numeric sequences (similar to Pytesseract approach but using EasyOCR boxes)
            # 2. Blur text regions if they contain sensitive keywords (more advanced)
            # 3. Blur text regions identified as specific entities by SpaCy (e.g., PERSON, ORG, CARDINAL)

            blur_this_box = False

            # Strategy 1: Purely numeric (and high confidence)
            # Add length checks if desired (e.g., >= 4 digits)
            if text.isdigit() and prob > 0.6: # Adjust confidence threshold
                    logger.debug(f"Found numeric sequence: '{text}'. Marking for blur.")
                    blur_this_box = True

            # Strategy 2: Sensitive keywords (check if any part of the text matches)
            # This is basic keyword spotting. More context might be needed.
            # Be careful, this might blur too aggressively (e.g., blurring "cardigan" because of "card")
            # Consider checking whole words: `if any(label in text_lower.split() for label in sensitive_labels):`
            if not blur_this_box and any(label in text_lower for label in sensitive_labels):
                logger.debug(f"Found sensitive keyword near/in: '{text}'. Marking for blur.")
                blur_this_box = True


            # # Strategy 3: SpaCy NER (Uncomment and test if needed)
            # # Process text with SpaCy
            # if not blur_this_box and nlp:
            #     doc = nlp(text)
            #     for ent in doc.ents:
            #         # Check for specific entity types you want to blur
            #         # Example: CARDINAL (numbers), PERSON, ORG, DATE, GPE (locations)
            #         if ent.label_ in ["CARDINAL", "PERSON", "DATE", "GPE", "ORG"]:
            #             logger.debug(f"Found SpaCy entity '{ent.text}' (Label: {ent.label_}). Marking for blur.")
            #             blur_this_box = True
            #             break # Blur the whole box if any sensitive entity is found


            # --- Apply Blur ---
            if blur_this_box:
                # EasyOCR bbox format is [[x_min, y_min], [x_max, y_min], [x_max, y_max], [x_min, y_max]]
                # Extract min/max coordinates
                pts = np.array(bbox, dtype=np.int32)
                x_min, y_min = np.min(pts, axis=0)
                x_max, y_max = np.max(pts, axis=0)

                # Add padding around the box (optional, can help ensure full coverage)
                padding = 2
                x_min = max(0, x_min - padding)
                y_min = max(0, y_min - padding)
                x_max += padding # No need for max check here, blur_region handles bounds
                y_max += padding

                logger.debug(f"Blurring region for '{text}': x_min={x_min}, y_min={y_min}, x_max={x_max}, y_max={y_max}")
                image_np = blur_region(image_np, x_min, y_min, x_max, y_max)
                boxes_blurred += 1


        logger.info(f"Blurred {boxes_blurred} sensitive regions (EasyOCR/Keyword).")

        # Convert back to PIL Image (original color space was RGB)
        return Image.fromarray(image_np) # Assuming image_np is still RGB

    except ImportError as e:
            logger.error(f"ImportError during sensitive data blurring: {e}. Ensure EasyOCR, SpaCy, and OpenCV are installed.")
            return None
    except RuntimeError as e: # Catch init errors from lazy loaders
            logger.error(f"RuntimeError during sensitive data blurring (model init failed?): {e}", exc_info=True)
            return None
    except Exception as e:
        logger.error(f"Unexpected error during sensitive data blurring: {e}", exc_info=True)
        return None