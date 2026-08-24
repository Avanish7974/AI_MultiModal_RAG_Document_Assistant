from src.services.quiz_service import generate_quiz


context = """
SOURCE 1

File: Master Resume.pdf
Location: Page 1

Content:

Avanish Singh is pursuing a B.Tech in Artificial
Intelligence and Machine Learning at SIRT Bhopal.

He worked as a Data Analyst Intern at Cybrom Technology
Pvt. Ltd. in Bhopal.

His projects include Multi-Modal RAG Document Assistant
and Laptop Price Prediction.

Technologies include Python, C++, SQL, Streamlit,
Pandas, Scikit-learn, Gemini and ChromaDB.
"""


question = """
Generate 5 medium-difficulty multiple-choice questions
from this document.
"""


answer = generate_quiz(
    context=context,
    question=question
)


print("\n")
print("========== QUIZ RESULT ==========")
print(answer)
print("=================================")