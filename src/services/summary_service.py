from dotenv import load_dotenv
from google import genai

from src.prompts.summary_prompt import SUMMARY_PROMPT


# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()


# =========================================================
# GEMINI CLIENT
# =========================================================

import os

client = genai.Client(
    api_key=os.getenv("GOOGLE_API_KEY")
)


# =========================================================
# MODEL
# =========================================================

MODEL_NAME = "gemini-3.5-flash-lite"


# =========================================================
# GENERATE SUMMARY
# =========================================================

def generate_summary(
    context,
    question
):
    """
    Generate a structured document summary.
    """

    prompt = SUMMARY_PROMPT.format(
        context=context,
        question=question
    )

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    return response.text