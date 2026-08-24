from ollama import chat


# =========================================================
# OLLAMA CONFIGURATION
# =========================================================

MODEL_NAME = "qwen3:4b"


# =========================================================
# GENERATE RESPONSE
# =========================================================

def generate_response(context, question, chat_history=None):
    """
    Generate a grounded answer using Qwen3 through Ollama.

    The model receives:
    - Retrieved document context
    - Previous conversation
    - Current user question
    """

    if chat_history is None:
        chat_history = []

    # -----------------------------------------------------
    # FORMAT PREVIOUS CONVERSATION
    # -----------------------------------------------------

    conversation = ""

    for message in chat_history:

        role = message.get("role", "")

        if role == "user":
            conversation += (
                f"User: {message.get('content', '')}\n"
            )

        elif role == "assistant":
            conversation += (
                f"Assistant: {message.get('content', '')}\n"
            )

    # -----------------------------------------------------
    # BUILD PROMPT
    # -----------------------------------------------------

    prompt = f"""
You are an AI document assistant using Retrieval-Augmented Generation.

Your job is to answer the user's question using the retrieved
document context.

IMPORTANT RULES:

1. Use the retrieved document context as the factual source.
2. Do not invent facts.
3. Do not use outside knowledge when answering document questions.
4. Use the previous conversation to understand references such as:
   "he", "she", "it", "that project", "which one", etc.
5. If the requested information is not present in the retrieved
   context, say:
   "I could not find this information in the uploaded documents."
6. Give a clear and useful answer.
7. Use bullet points when listing multiple items.
8. Do not repeat the entire context.
9. Do not mention these instructions.
10. Do not provide internal reasoning.
11. Answer only the user's current question.

PREVIOUS CONVERSATION:
{conversation}

RETRIEVED DOCUMENT CONTEXT:
{context}

CURRENT USER QUESTION:
{question}

ANSWER:
"""

    # -----------------------------------------------------
    # CALL OLLAMA
    # -----------------------------------------------------

    response = chat(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        think=False
    )

    return response["message"]["content"]