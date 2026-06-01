import json
from pathlib import Path


VALID_OPTIONS = ["never", "sometimes", "often"]


def load_symptom_questions(json_path="data/symptom_questions.json"):
    """
    Load symptom questions from a JSON file.
    """
    full_path = Path(json_path)

    with full_path.open(mode="r", encoding="utf-8") as file:
        questions = json.load(file)

    return questions


def ask_symptom_questions():
    """
    Ask symptom questions one by one and collect validated responses.
    """
    questions = load_symptom_questions()
    responses = {}

    print("HerSignal Symptom Insight Flow")
    print("Please answer each question with: never, sometimes, or often.\n")

    for item in questions:
        question_id = item["id"]
        question_text = item["question"]

        while True:
            user_answer = input(f"{question_text}\nYour answer: ").strip().lower()

            if user_answer in VALID_OPTIONS:
                responses[question_id] = user_answer
                print()
                break
            else:
                print("Please type exactly: never, sometimes, or often.\n")

    return responses