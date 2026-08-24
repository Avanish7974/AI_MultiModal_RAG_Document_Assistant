import os

import easyocr
import numpy as np
from PIL import Image


# =========================================================
# OCR READER
# =========================================================

_reader = None


def get_ocr_reader():
    """
    Create EasyOCR reader only when OCR is actually required.
    """

    global _reader

    if _reader is None:

        _reader = easyocr.Reader(
            ["en"],
            gpu=False
        )

    return _reader


# =========================================================
# IMAGE OCR
# =========================================================

def extract_image_text(file_path):
    """
    Extract text from PNG/JPG/JPEG images using EasyOCR.

    The image is converted to a NumPy array before being
    passed to EasyOCR for reliable Windows/Streamlit handling.

    Returns:
        list of dictionaries:
        {
            "text": "...",
            "location": "OCR region 1"
        }
    """

    # -----------------------------------------------------
    # VALIDATE FILE
    # -----------------------------------------------------

    if not os.path.exists(str(file_path)):

        raise FileNotFoundError(
            f"Image file not found: {file_path}"
        )

    # -----------------------------------------------------
    # OPEN IMAGE
    # -----------------------------------------------------

    image = Image.open(
        str(file_path)
    )

    # Convert to RGB
    image = image.convert("RGB")

    # Convert PIL image → NumPy array
    image_array = np.array(image)

    # -----------------------------------------------------
    # OCR
    # -----------------------------------------------------

    reader = get_ocr_reader()

    results = reader.readtext(
        image_array,
        detail=1
    )

    # -----------------------------------------------------
    # BUILD RESULT
    # -----------------------------------------------------

    extracted_data = []

    for index, result in enumerate(
        results,
        start=1
    ):

        # EasyOCR result:
        # result[0] = bounding box
        # result[1] = detected text
        # result[2] = confidence

        text = result[1].strip()

        confidence = float(
            result[2]
        )

        if text:

            extracted_data.append(
                {
                    "text": text,
                    "location": f"OCR Region {index}",
                    "confidence": confidence
                }
            )

    return extracted_data