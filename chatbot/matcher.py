import csv
import logging
import re
from functools import lru_cache
from pathlib import Path

import nltk
from nltk.stem import WordNetLemmatizer
from sentence_transformers import SentenceTransformer, util
from thefuzz import fuzz


logger = logging.getLogger(__name__)
_lemmatizer = WordNetLemmatizer()

TYPO_CORRECTIONS = {
    "symptomps": "symptoms",
    "symptom": "symptoms",
    "managem": "manage",
    "fertilty": "fertility",
    "fertiltiy": "fertility",
    "ovultion": "ovulation",
    "facialhair": "facial hair",
    "hairloss": "hair loss",
    "irregualr": "irregular",
    "weigt": "weight",
    "craveings": "cravings",
    "docotr": "doctor",
    "diagnois": "diagnosis",
    "cant": "can not",
    "dont": "do not",
    "doesnt": "does not",
    "im": "i am",
    "ive": "i have",
}


KEYWORD_CATEGORIES = {
    "fertility": ["fertility", "pregnant", "pregnancy", "conceive", "ovulation", "ovulate", "infertility"],
    "symptoms_hormonal": ["acne", "facial hair", "chin hair", "body hair", "hair thinning", "hair loss", "period", "periods", "missed periods", "ovulation", "hormone", "hormonal", "oily skin"],
    "symptoms_metabolic": ["weight", "cravings", "fatigue", "tired", "blood sugar", "insulin", "dark skin", "dark patches", "acanthosis"],
    "symptoms_inflammatory": ["inflammation", "bloating", "headaches"],
    "management": ["manage", "management", "help", "support", "improve", "lifestyle", "diet", "exercise", "track", "mood", "mental health", "confused"],
    "supplements": ["supplement", "supplements", "inositol", "vitamin d", "magnesium"],
    "safety": ["diagnose", "diagnosis", "medical advice", "doctor", "gp", "safe", "severe"],
    "basics": ["what is pcos", "what does pcos mean", "causes", "common", "curable", "cysts"],
}


def normalise_text(text):
    """
    Lowercase, remove punctuation, compress spaces, and apply lightweight typo correction.
    """
    if not text:
        return ""

    text = str(text).lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    words = text.split()
    corrected_words = [TYPO_CORRECTIONS.get(word, word) for word in words]
    text = " ".join(corrected_words)

    for wrong, right in TYPO_CORRECTIONS.items():
        text = text.replace(wrong, right)

    return text


def _ensure_nltk_resources():
    """
    Ensure NLTK resources needed for lemmatization are available.
    """
    try:
        nltk.data.find("corpora/wordnet")
    except LookupError:
        nltk.download("wordnet", quiet=True)

    try:
        nltk.data.find("corpora/omw-1.4")
    except LookupError:
        nltk.download("omw-1.4", quiet=True)


def preprocess_text(text):
    """
    Normalize text and lemmatize tokens for stronger semantic and fuzzy matching.
    """
    normalized = normalise_text(text)
    if not normalized:
        return ""

    _ensure_nltk_resources()
    tokens = normalized.split()
    lemmatized_tokens = [_lemmatizer.lemmatize(token) for token in tokens]
    return " ".join(lemmatized_tokens)


def _build_intent_id(question, raw_intent_id=None):
    """
    Build a stable fallback intent id when CSV does not provide one.
    """
    if raw_intent_id and str(raw_intent_id).strip():
        return str(raw_intent_id).strip().lower()

    normalized_question = normalise_text(question)
    if not normalized_question:
        return "faq_unknown_intent"

    slug = re.sub(r"\s+", "_", normalized_question).strip("_")
    slug = re.sub(r"[^a-z0-9_]", "", slug)
    return f"faq_{slug}" if slug else "faq_unknown_intent"


def _aggregate_ranked_by_intent(ranked_items):
    """
    Keep the highest-scoring candidate per intent_id.
    """
    best_per_intent = {}

    for item in ranked_items:
        if not isinstance(item, dict):
            continue

        intent_id = item.get("intent_id", "")
        if not intent_id:
            intent_id = _build_intent_id(item.get("question", ""))

        existing = best_per_intent.get(intent_id)
        if existing is None or item.get("score", 0.0) > existing.get("score", 0.0):
            best_per_intent[intent_id] = {**item, "intent_id": intent_id}

    aggregated = list(best_per_intent.values())
    aggregated.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    return aggregated


@lru_cache(maxsize=1)
def _load_embedding_model():
    return SentenceTransformer("all-MiniLM-L6-v2")


def load_faq_data(csv_path=None):
    """
    Load FAQ question-answer-category rows from CSV.
    Expected columns:
    - question
    - answer
    - category
    """
    faq_data = []

    if csv_path is None:
        project_root = Path(__file__).resolve().parent.parent
        full_path = project_root / "data" / "pcos_qa.csv"
    else:
        full_path = Path(csv_path).resolve()

    try:
        with full_path.open(mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if not isinstance(row, dict):
                    continue

                question = preprocess_text(row.get("question", ""))
                display_question = str(row.get("question", "")).strip()
                answer = str(row.get("answer", "")).strip()
                category = str(row.get("category", "basics")).strip() or "basics"
                intent_id = _build_intent_id(
                    question=row.get("question", ""),
                    raw_intent_id=row.get("intent_id", "")
                )
                variant_group = str(row.get("variant_group", "")).strip().lower()
                status = str(row.get("status", "active")).strip().lower() or "active"

                if question and answer and status != "inactive":
                    faq_data.append(
                        {
                            "question": question,
                            "display_question": display_question,
                            "answer": answer,
                            "category": category,
                            "intent_id": intent_id,
                            "variant_group": variant_group,
                            "status": status,
                        }
                    )

        return faq_data

    except FileNotFoundError:
        logger.exception("FAQ CSV file not found: %s", full_path)
        return []
    except UnicodeDecodeError:
        logger.exception("FAQ CSV file could not be decoded: %s", full_path)
        return []
    except Exception:
        logger.exception("Unexpected error while loading FAQ data.")
        return []


@lru_cache(maxsize=1)
def _get_faq_embeddings():
    faq_data = load_faq_data()
    if not faq_data:
        return [], []

    questions = [item["question"] for item in faq_data]
    model = _load_embedding_model()
    embeddings = model.encode(questions, convert_to_tensor=True)
    return faq_data, embeddings


def detect_priority_categories(user_input):
    """
    Detect likely FAQ categories from keywords in the user's question.
    """
    detected = set()

    if not user_input:
        return detected

    processed_input = preprocess_text(user_input)

    for category, keywords in KEYWORD_CATEGORIES.items():
        for keyword in keywords:
            if keyword in processed_input:
                detected.add(category)
                break

    return detected


def _build_ranked_matches_from_scores(cleaned_input, faq_data, semantic_scores):
    """
    Build ranked FAQ candidates from precomputed semantic scores.
    """
    priority_categories = detect_priority_categories(cleaned_input)
    ranked = []

    for index, item in enumerate(faq_data):
        if not isinstance(item, dict):
            continue

        question = item.get("question", "")
        answer = item.get("answer", "")
        category = item.get("category", "basics")

        if not question or not answer:
            continue

        semantic_score = float(semantic_scores[index]) if index < len(semantic_scores) else 0.0
        fuzzy_score = fuzz.token_set_ratio(cleaned_input, question) / 100.0
        score = (semantic_score * 0.85) + (fuzzy_score * 0.15)

        if category in priority_categories:
            score += 0.05

        input_words = set(cleaned_input.split())
        question_words = set(question.split())
        overlap = len(input_words.intersection(question_words))
        score += min(overlap * 0.01, 0.05)
        score = min(score, 1.0)

        ranked.append(
            {
                "question": question,
                "display_question": item.get("display_question", question),
                "answer": answer,
                "category": category,
                "intent_id": item.get("intent_id", _build_intent_id(question)),
                "score": round(score, 4),
            }
        )

    return ranked


def get_ranked_faq_matches(user_input, faq_data=None):
    """
    Return ranked intent-aware FAQ candidates for a user input.
    """
    try:
        if faq_data is None:
            faq_data, faq_embeddings = _get_faq_embeddings()
        else:
            faq_embeddings = None

        cleaned_input = preprocess_text(user_input)
        if not cleaned_input or not faq_data:
            return []

        if faq_embeddings is not None:
            model = _load_embedding_model()
            input_embedding = model.encode(cleaned_input, convert_to_tensor=True)
            semantic_scores = [float(score) for score in util.cos_sim(input_embedding, faq_embeddings)[0]]
            ranked = _build_ranked_matches_from_scores(cleaned_input, faq_data, semantic_scores)
            return _aggregate_ranked_by_intent(ranked)

        return rank_faq_matches(cleaned_input, faq_data)

    except Exception:
        logger.exception("Unexpected error while ranking FAQ matches.")
        return []


def rank_faq_matches(user_input, faq_data):
    """
    Rank FAQ entries using semantic similarity and fuzzy typo tolerance.
    """
    cleaned_input = preprocess_text(user_input)
    if not cleaned_input or not faq_data:
        return []

    model = _load_embedding_model()
    input_embedding = model.encode(cleaned_input, convert_to_tensor=True)
    semantic_scores = []
    for item in faq_data:
        question = item.get("question", "") if isinstance(item, dict) else ""
        if question:
            semantic_scores.append(float(util.cos_sim(input_embedding, model.encode(question, convert_to_tensor=True))[0][0]))
        else:
            semantic_scores.append(0.0)

    ranked = _build_ranked_matches_from_scores(cleaned_input, faq_data, semantic_scores)
    return _aggregate_ranked_by_intent(ranked)


def find_best_faq_match(user_input, faq_data=None, threshold=0.70):
    """
    Return the best FAQ match dict if threshold is met.
    Otherwise return None.
    """
    try:
        ranked = get_ranked_faq_matches(user_input, faq_data=faq_data)

        if not ranked:
            return None

        best_match = ranked[0]

        if best_match["score"] < threshold:
            return None

        return best_match

    except Exception:
        logger.exception("Unexpected error while finding FAQ match.")
        return None


def warmup_faq_matcher():
    """
    Preload FAQ data and embeddings once at startup for faster requests.
    """
    try:
        faq_data, _ = _get_faq_embeddings()
        logger.info("FAQ matcher warmed up with %d entries.", len(faq_data))
    except Exception:
        logger.exception("Failed to warm up FAQ matcher.")