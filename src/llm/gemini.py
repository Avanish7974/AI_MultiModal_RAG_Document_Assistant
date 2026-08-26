print("✅ GEMINI.PY LOADED")

import os
import re

from dotenv import load_dotenv
from google import genai
from google.genai import types

from src.prompts.rag_prompt import RAG_PROMPT


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
# MODELS
# =========================================================

# Existing model for normal document RAG.
MODEL_NAME = "gemini-3.5-flash-lite"

# Multimodal video model.
MULTIMODAL_MODEL_NAME = "gemini-3.7-flash"


# =========================================================
# NORMAL TEXT RAG
# =========================================================

def generate_response(context, question):
    """
    Existing text-based RAG response.

    Used for normal documents and existing application
    features.

    This function intentionally remains unchanged.
    """

    prompt = RAG_PROMPT.format(
        context=context,
        question=question
    )

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    return response.text


# =========================================================
# TIME PARSING HELPERS
# =========================================================

def _parse_timestamp_to_seconds(timestamp):
    """
    Convert:

        5:30
        47:00
        1:28:30

    into seconds.
    """

    if not timestamp:
        return None

    timestamp = timestamp.strip()

    parts = timestamp.split(":")

    try:

        if len(parts) == 2:

            minutes = int(parts[0])
            seconds = int(parts[1])

            return (
                minutes * 60
                + seconds
            )

        if len(parts) == 3:

            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2])

            return (
                hours * 3600
                + minutes * 60
                + seconds
            )

    except ValueError:
        return None

    return None


def _extract_timestamp_from_question(question):
    """
    Detect explicit timestamps from questions.

    Examples:

        around 5 minutes
        around 47 minutes
        at 1:28:30
        around 12:45
        at 1 hour 28 minutes
    """

    if not question:
        return None

    text = question.lower()

    # -----------------------------------------------------
    # HH:MM:SS
    # -----------------------------------------------------

    match = re.search(
        r"\b(\d{1,2}):(\d{2}):(\d{2})\b",
        text
    )

    if match:

        hours = int(match.group(1))
        minutes = int(match.group(2))
        seconds = int(match.group(3))

        return (
            hours * 3600
            + minutes * 60
            + seconds
        )

    # -----------------------------------------------------
    # MM:SS
    # -----------------------------------------------------

    match = re.search(
        r"\b(\d{1,3}):(\d{2})\b",
        text
    )

    if match:

        minutes = int(match.group(1))
        seconds = int(match.group(2))

        return (
            minutes * 60
            + seconds
        )

    # -----------------------------------------------------
    # X HOURS Y MINUTES
    # -----------------------------------------------------

    match = re.search(
        r"(\d+)\s*hour[s]?"
        r"(?:\s*(?:and\s*)?(\d+)\s*minute[s]?)?",
        text
    )

    if match:

        hours = int(
            match.group(1)
        )

        minutes = int(
            match.group(2) or 0
        )

        return (
            hours * 3600
            + minutes * 60
        )

    # -----------------------------------------------------
    # X MINUTES
    # -----------------------------------------------------

    match = re.search(
        r"(\d+)\s*minute[s]?",
        text
    )

    if match:

        minutes = int(
            match.group(1)
        )

        return minutes * 60

    return None


def _extract_timestamps_from_context(context):
    """
    Extract timestamps from the YouTube RAG context.

    The Streamlit context contains entries such as:

        Timestamp: [05:12]

    Returns a list of timestamps in seconds.
    """

    if not context:
        return []

    matches = re.findall(
        r"Timestamp:\s*\[([0-9:]+)\]",
        context,
        flags=re.IGNORECASE
    )

    timestamps = []

    for value in matches:

        seconds = _parse_timestamp_to_seconds(
            value
        )

        if seconds is not None:
            timestamps.append(seconds)

    return timestamps


# =========================================================
# DETERMINE MULTIMODAL WINDOW
# =========================================================

def _determine_video_window(
    question,
    context
):
    """
    Decide which part of the YouTube video Gemini should
    inspect.

    Priority:

        1. Explicit timestamp in user question.
        2. Timestamp retrieved from transcript RAG.
        3. No timestamp -> analyze the full video.

    For targeted analysis we use a small surrounding window.
    """

    # -----------------------------------------------------
    # QUESTION TIMESTAMP
    # -----------------------------------------------------

    question_timestamp = (
        _extract_timestamp_from_question(
            question
        )
    )

    if question_timestamp is not None:

        # For a timestamp question, inspect ±2 minutes.
        start = max(
            0,
            question_timestamp - 120
        )

        end = (
            question_timestamp + 120
        )

        return start, end, "explicit"


    # -----------------------------------------------------
    # RETRIEVED TRANSCRIPT TIMESTAMP
    # -----------------------------------------------------

    context_timestamps = (
        _extract_timestamps_from_context(
            context
        )
    )

    if context_timestamps:

        # Use the relevant retrieved region.
        center = context_timestamps[0]

        start = max(
            0,
            center - 120
        )

        end = (
            center + 180
        )

        return start, end, "retrieved"


    # -----------------------------------------------------
    # NO TARGETED TIMESTAMP
    # -----------------------------------------------------

    return None, None, "full"


# =========================================================
# YOUTUBE QUESTION ROUTING
# =========================================================

def should_use_youtube_multimodal(question):
    """
    Return True only when a question is likely to require the actual
    video's visual/audio content rather than transcript retrieval alone.

    This keeps normal YouTube Q&A fast on free-tier API usage while
    preserving the existing multimodal engine for targeted questions.
    """

    text = (question or "").lower()

    visual_terms = (
        "shown", "showing", "on screen", "screen", "visual",
        "image", "picture", "diagram", "graph", "chart",
        "slide", "slides", "equation", "code on screen",
        "table", "demonstration", "demo", "what appears",
        "what does the screen", "what is displayed",
        "look like", "looks like",
    )

    timestamp_terms = (
        "timestamp", "minute", "minutes", "second", "seconds",
    )

    explicit_timestamp = bool(
        re.search(r"\b\d{1,3}:\d{2}(?::\d{2})?\b", text)
    )

    return any(term in text for term in visual_terms) or any(
        term in text for term in timestamp_terms
    ) or explicit_timestamp


# =========================================================
# YOUTUBE LEVEL-2 MULTIMODAL RESPONSE
# =========================================================

def generate_youtube_multimodal_response(
    video_url,
    context,
    question
):
    """
    Level-2 multimodal YouTube analysis.

    Uses Google's native YouTube URL video input.

    The video is analyzed using:
        - audio
        - visual frames
        - transcript context
        - timestamp references
    """

    # =====================================================
    # VALIDATE URL
    # =====================================================

    if not video_url:

        raise ValueError(
            "YouTube video URL is required "
            "for multimodal analysis."
        )


    # =====================================================
    # BUILD PROMPT
    # =====================================================

    prompt = f"""
You are a precise multimodal YouTube RAG assistant.

Analyze the supplied YouTube video using BOTH:

1. Audio / spoken content
2. Visual content

You also have retrieved transcript context.

=========================================================
STRICT RULES
=========================================================

1. Answer only from the supplied YouTube video and the
   retrieved transcript context.

2. Do not use outside knowledge.

3. If the user asks what the speaker explains, analyze
   the spoken audio and transcript.

4. If the user asks what is shown on screen, analyze the
   visual frames.

5. Pay attention to:
   - slides
   - diagrams
   - graphs
   - charts
   - equations
   - code
   - tables
   - screen demonstrations
   - written text

6. If the user refers to a timestamp, focus on that
   specific part of the video.

7. Use timestamps in MM:SS format when useful.

8. Do not invent timestamps.

9. If the requested information is not present, say:

   "I couldn't find that information in the video."

10. Give the direct answer first.

11. Then briefly explain the evidence from the video.

=========================================================
RETRIEVED TRANSCRIPT CONTEXT
=========================================================

{context}

=========================================================
USER QUESTION
=========================================================

{question}

=========================================================
TASK
=========================================================

Analyze the YouTube video itself.

Use both its audio and visual information.

For visual questions, inspect what is actually shown.

For spoken-content questions, use the audio and transcript.

For timestamp questions, focus on the requested moment.

Answer the user now.
"""


    # =====================================================
    # GEMINI MULTIMODAL REQUEST
    # =====================================================

    interaction = client.interactions.create(

        model=MULTIMODAL_MODEL_NAME,

        input=[
            {
                "type": "video",
                "uri": video_url
            },

            {
                "type": "text",
                "text": prompt
            }
        ],

        generation_config={
            "thinking_level": "low"
        }
    )


    # =====================================================
    # RESPONSE
    # =====================================================

    answer = interaction.output_text


    if not answer:

        raise RuntimeError(
            "Gemini returned an empty multimodal response."
        )


    return answer

