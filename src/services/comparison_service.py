import os

from dotenv import load_dotenv
from google import genai

from src.prompts.comparison_prompt import COMPARISON_PROMPT


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
# COMPARISON
# =========================================================

def generate_comparison(
    context,
    question
):
    """
    Generate a comparison between multiple
    retrieved documents.
    """

    prompt = COMPARISON_PROMPT.format(
        context=context,
        question=question
    )

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    return response.text
