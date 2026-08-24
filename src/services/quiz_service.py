import os
import json

from dotenv import load_dotenv
from google import genai

from src.prompts.quiz_prompt import QUIZ_PROMPT


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
# GENERATE QUIZ
# =========================================================

def generate_quiz(
    context,
    num_questions,
    difficulty
):
    """
    Generate a structured MCQ quiz.
    """

    question = f"""
Generate exactly {num_questions} multiple-choice questions.

Difficulty: {difficulty}
"""

    prompt = QUIZ_PROMPT.format(
        context=context,
        question=question
    )

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config={
            "response_mime_type": "application/json"
        }
    )

    try:
        return json.loads(response.text)

    except json.JSONDecodeError:

        raise ValueError(
            "Gemini returned invalid quiz JSON."
        )