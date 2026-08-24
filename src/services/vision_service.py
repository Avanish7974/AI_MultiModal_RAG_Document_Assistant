import os

from dotenv import load_dotenv
from google import genai
from google.genai import types


# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()


# =========================================================
# GEMINI CLIENT
# =========================================================

client = genai.Client(
    api_key=os.getenv("GOOGLE_API_KEY")
)


# =========================================================
# MODEL
# =========================================================

MODEL_NAME = "gemini-3.5-flash-lite"


# =========================================================
# IMAGE ANALYSIS
# =========================================================

def analyze_image(image_path, question=None):
    """
    Analyze an image using Gemini.

    Uses the same Gemini model that is already working
    in the main RAG pipeline.
    """

    # -----------------------------------------------------
    # CHECK FILE
    # -----------------------------------------------------

    if not os.path.exists(image_path):

        raise FileNotFoundError(
            f"Image not found: {image_path}"
        )

    # -----------------------------------------------------
    # MIME TYPE
    # -----------------------------------------------------

    extension = os.path.splitext(
        image_path
    )[1].lower()

    mime_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg"
    }

    mime_type = mime_types.get(
        extension
    )

    if mime_type is None:

        raise ValueError(
            f"Unsupported image format: {extension}"
        )

    # -----------------------------------------------------
    # READ IMAGE
    # -----------------------------------------------------

    with open(
        image_path,
        "rb"
    ) as image_file:

        image_bytes = image_file.read()

    # -----------------------------------------------------
    # IMAGE PART
    # -----------------------------------------------------

    image_part = types.Part.from_bytes(
        data=image_bytes,
        mime_type=mime_type
    )

    # -----------------------------------------------------
    # PROMPT
    # -----------------------------------------------------

    if question:

        prompt = f"""
Analyze the image carefully.

Answer this question using only information
visible in the image:

{question}

If the image does not contain enough information
to answer the question, say so clearly.

Keep the answer concise.
"""

    else:

        prompt = """
Analyze this image.

Describe only information that is actually
visible in the image.

Include:
- important visible text
- tables
- charts
- diagrams
- objects
- important visual information
- overall purpose of the image

Do not invent information.
Keep the description concise.
"""

    # -----------------------------------------------------
    # GEMINI
    # -----------------------------------------------------

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[
            image_part,
            prompt
        ]
    )

    return response.text