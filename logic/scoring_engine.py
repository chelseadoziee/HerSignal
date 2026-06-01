import json
import logging
from pathlib import Path


logger = logging.getLogger(__name__)

VALID_RESPONSES = {"yes", "no", "maybe"}

RESPONSE_WEIGHTS = {
    "yes": 2,
    "maybe": 1,
    "no": 0,
}

CATEGORY_KEYS = ("hormonal", "metabolic", "inflammatory")


def load_symptom_questions(json_path=None):
    """
    Load symptom questions from JSON.
    """
    if json_path is None:
        project_root = Path(__file__).resolve().parent.parent
        json_path = project_root / "data" / "symptom_questions.json"
    else:
        json_path = Path(json_path).resolve()

    try:
        with open(json_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, list):
            logger.error("symptom_questions.json did not contain a list.")
            return []

        validated_questions = []
        for item in data:
            if not isinstance(item, dict):
                continue

            symptom_id = item.get("id", "")
            question = item.get("question", "")
            category = item.get("category", "general")

            if symptom_id and question:
                validated_questions.append(
                    {
                        "id": str(symptom_id).strip(),
                        "question": str(question).strip(),
                        "category": str(category).strip() or "general",
                    }
                )

        return validated_questions

    except FileNotFoundError:
        logger.exception("Symptom questions file not found: %s", json_path)
        return []
    except json.JSONDecodeError:
        logger.exception("Symptom questions JSON is malformed: %s", json_path)
        return []
    except Exception:
        logger.exception("Unexpected error while loading symptom questions.")
        return []


def load_symptom_rules(json_path=None):
    """
    Load overlap-based symptom rules from JSON.

    Each symptom can contribute to one or more categories using rule weights.
    Example:
        "acne": {"hormonal": 2, "inflammatory": 1}
    """
    if json_path is None:
        project_root = Path(__file__).resolve().parent.parent
        json_path = project_root / "data" / "symptom_rules.json"
    else:
        json_path = Path(json_path).resolve()

    try:
        with open(json_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            logger.error("symptom_rules.json did not contain a dictionary.")
            return {}

        validated_rules = {}
        for symptom_id, category_map in data.items():
            if not isinstance(category_map, dict):
                continue

            validated_rules[symptom_id] = {
                "hormonal": category_map.get("hormonal", 0),
                "metabolic": category_map.get("metabolic", 0),
                "inflammatory": category_map.get("inflammatory", 0),
            }

        return validated_rules

    except FileNotFoundError:
        logger.exception("Symptom rules file not found: %s", json_path)
        return {}
    except json.JSONDecodeError:
        logger.exception("Symptom rules JSON is malformed: %s", json_path)
        return {}
    except Exception:
        logger.exception("Unexpected error while loading symptom rules.")
        return {}


def normalise_response(user_input):
    """
    Normalise raw user input into yes / no / maybe.
    """
    if not user_input:
        return ""

    cleaned = str(user_input).strip().lower()

    aliases = {
        "y": "yes",
        "yeah": "yes",
        "yep": "yes",
        "yes": "yes",
        "n": "no",
        "no": "no",
        "nope": "no",
        "nah": "no",
        "m": "maybe",
        "maybe": "maybe",
        "not sure": "maybe",
        "unsure": "maybe",
        "i am not sure": "maybe",
        "i'm not sure": "maybe",
        "sometimes": "maybe",
    }

    return aliases.get(cleaned, cleaned)


def collect_symptom_responses():
    """
    Ask the user each symptom question and collect yes / no / maybe responses.
    """
    questions = load_symptom_questions()
    responses = {}

    if not questions:
        print("HerSignal could not load the symptom questions right now.")
        return responses

    print("HerSignal Symptom Insight Flow")
    print("Please answer each question with: yes, no, or maybe.\n")

    for item in questions:
        while True:
            print(item["question"])
            user_answer = input("Your answer: ").strip()
            normalised = normalise_response(user_answer)

            if normalised in VALID_RESPONSES:
                responses[item["id"]] = normalised
                print()
                break

            print("Please answer with yes, no, or maybe.\n")

    return responses


def build_fallback_rule_map(questions):
    """
    Build a fallback single-category rule map from symptom_questions.json.

    This is used when a symptom exists in the questionnaire but has not yet been
    added to symptom_rules.json. It keeps the live app stable while still allowing
    multi-category overlap scoring where rules already exist.
    """
    fallback_rules = {}

    for item in questions:
        if not isinstance(item, dict):
            continue

        symptom_id = item.get("id")
        category = item.get("category", "general")

        if not symptom_id:
            continue

        fallback_rules[symptom_id] = {
            "hormonal": 0,
            "metabolic": 0,
            "inflammatory": 0,
        }

        if category in fallback_rules[symptom_id]:
            fallback_rules[symptom_id][category] = 2

    return fallback_rules


def merge_rules_with_fallback(symptom_rules, fallback_rules):
    """
    Merge explicit overlap rules with fallback single-category rules.

    Explicit rules from symptom_rules.json take priority.
    Missing symptoms fall back to the category defined in symptom_questions.json.
    """
    merged = {}

    all_symptom_ids = set(fallback_rules.keys()) | set(symptom_rules.keys())

    for symptom_id in all_symptom_ids:
        if symptom_id in symptom_rules:
            category_map = symptom_rules.get(symptom_id, {})
            merged[symptom_id] = {
                "hormonal": category_map.get("hormonal", 0),
                "metabolic": category_map.get("metabolic", 0),
                "inflammatory": category_map.get("inflammatory", 0),
            }
        else:
            merged[symptom_id] = fallback_rules[symptom_id]

    return merged


def calculate_category_scores(responses, questions=None, symptom_rules=None):
    """
    Convert yes / no / maybe responses into weighted category scores.

    New live logic:
    - yes = 2
    - maybe = 1
    - no = 0

    symptom_rules.json provides overlap weights per symptom:
    - 2 = strong contribution
    - 1 = secondary contribution
    - 0 = no contribution

    To preserve the previous scale:
    - a 'yes' on a primary rule weight of 2 contributes 2 points
    - a 'maybe' on a primary rule weight of 2 contributes 1 point
    - a 'yes' on a secondary rule weight of 1 contributes 1 point
    - a 'maybe' on a secondary rule weight of 1 contributes 0.5 points

    Formula:
        contribution = response_weight * (rule_weight / 2)

    This allows overlap scoring without making category totals explode.
    """
    try:
        if not isinstance(responses, dict):
            logger.error("Responses were not provided as a dictionary.")
            return {
                "hormonal": 0.0,
                "metabolic": 0.0,
                "inflammatory": 0.0,
            }

        if questions is None:
            questions = load_symptom_questions()

        if symptom_rules is None:
            symptom_rules = load_symptom_rules()

        if not questions:
            logger.error("No symptom questions available for score calculation.")
            return {
                "hormonal": 0.0,
                "metabolic": 0.0,
                "inflammatory": 0.0,
            }

        fallback_rules = build_fallback_rule_map(questions)
        merged_rules = merge_rules_with_fallback(symptom_rules, fallback_rules)

        scores = {
            "hormonal": 0.0,
            "metabolic": 0.0,
            "inflammatory": 0.0,
        }

        for item in questions:
            if not isinstance(item, dict):
                continue

            symptom_id = item.get("id")
            if not symptom_id:
                continue

            answer = normalise_response(responses.get(symptom_id, "no"))
            response_weight = RESPONSE_WEIGHTS.get(answer, 0)

            if response_weight == 0:
                continue

            category_weights = merged_rules.get(symptom_id, fallback_rules.get(symptom_id, {}))

            for category in CATEGORY_KEYS:
                rule_weight = category_weights.get(category, 0)
                contribution = response_weight * (rule_weight / 2)
                scores[category] += contribution

        return {
            "hormonal": round(scores["hormonal"], 2),
            "metabolic": round(scores["metabolic"], 2),
            "inflammatory": round(scores["inflammatory"], 2),
        }

    except Exception:
        logger.exception("Unexpected error while calculating category scores.")
        return {
            "hormonal": 0.0,
            "metabolic": 0.0,
            "inflammatory": 0.0,
        }


def calculate_response_profile(responses):
    """
    Count how many yes / maybe / no answers were given.
    This helps with confidence wording later.
    """
    profile = {"yes": 0, "maybe": 0, "no": 0}

    if not isinstance(responses, dict):
        return profile

    for answer in responses.values():
        normalised = normalise_response(answer)
        if normalised in profile:
            profile[normalised] += 1

    return profile