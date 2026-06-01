import json
import logging
from pathlib import Path
from logic.scoring_engine import (
    calculate_response_profile,
    load_symptom_questions,
    load_symptom_rules,
    normalise_response,
)

logger = logging.getLogger(__name__)

CATEGORY_LABELS = {
    "hormonal": "Hormonal",
    "metabolic": "Metabolic",
    "inflammatory": "Inflammatory",
}


def build_symptom_details():
    questions = load_symptom_questions()
    details = {}

    short_label_map = {
        "irregular_periods": "cycle irregularity",
        "acne": "skin changes related to acne",
        "facial_hair": "facial or body hair growth changes",
        "scalp_thinning": "scalp hair thinning or shedding",
        "weight_changes": "difficulty with weight changes",
        "fatigue": "fatigue or low energy",
        "cravings": "cravings or energy crashes",
        "stress_worsening": "symptoms that worsen with stress",
        "bloating": "bloating or puffiness",
        "mood_changes": "mood or emotional pattern changes",
    }

    label_map = {
        "irregular_periods": "Irregular or missed periods",
        "acne": "Persistent acne or unusual breakouts",
        "facial_hair": "Increased facial or body hair growth",
        "scalp_thinning": "Scalp hair thinning or hair shedding",
        "weight_changes": "Unexplained weight gain or difficulty managing weight",
        "fatigue": "Feeling unusually tired or fatigued",
        "cravings": "Strong cravings or energy crashes",
        "stress_worsening": "Symptoms that worsen with stress",
        "bloating": "Bloating or puffiness",
        "mood_changes": "Mood changes linked to symptoms or cycle",
    }

    for item in questions:
        if not isinstance(item, dict):
            continue

        symptom_id = item.get("id")
        if not symptom_id:
            continue

        details[symptom_id] = {
            "label": label_map.get(
                symptom_id,
                symptom_id.replace("_", " ").replace("-", " ").title(),
            ),
            "short_label": short_label_map.get(
                symptom_id,
                symptom_id.replace("_", " ").replace("-", " ").title(),
            ),
            "default_category": item.get("category", "general"),
        }

    return details


SYMPTOM_DETAILS = build_symptom_details()


def load_supplement_info(json_path=None):
    if json_path is None:
        project_root = Path(__file__).resolve().parent.parent
        json_path = project_root / "data" / "supplement_info.json"
    else:
        json_path = Path(json_path).resolve()

    try:
        with open(json_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            logger.error("supplement_info.json did not contain a dictionary.")
            return {}

        return data

    except FileNotFoundError:
        logger.exception("Supplement info file not found: %s", json_path)
        return {}
    except json.JSONDecodeError:
        logger.exception("Supplement info JSON is malformed: %s", json_path)
        return {}
    except Exception:
        logger.exception("Unexpected error while loading supplement info.")
        return {}


def format_category_name(category):
    return CATEGORY_LABELS.get(category, str(category).title())


def _first_sentence(text):
    """Return the first sentence of plain text for panel previews."""
    if not text or not str(text).strip():
        return ""
    chunk = str(text).strip().replace("\n", " ")
    for end in (". ", "! ", "? "):
        idx = chunk.find(end)
        if idx != -1:
            return chunk[: idx + 1].strip()
    return chunk


def _preview_text(text, max_chars=100):
    """Trim text to a single line preview without breaking mid word."""
    if not text:
        return ""
    clean = " ".join(str(text).split())
    if len(clean) <= max_chars:
        return clean
    snippet = clean[:max_chars].rsplit(" ", 1)[0]
    return f"{snippet}…"


def _preview_from_paragraphs(paragraphs, max_chars=100):
    if not paragraphs:
        return ""
    return _preview_text(paragraphs[0], max_chars=max_chars)


def _join_paragraphs(paragraphs):
    return "\n\n".join(p for p in (paragraphs or []) if p)


def _build_contributing_preview(contributing_symptoms):
    if not contributing_symptoms:
        return "No contributing symptoms highlighted"
    n = len(contributing_symptoms)
    word = "symptom" if n == 1 else "symptoms"
    return f"{n} {word} highlighted in this result"


def _build_supplements_preview(notes):
    if not notes:
        return "No supplement notes for this pattern"
    names = [n.get("name", "") for n in notes if n.get("name")]
    head = ", ".join(names[:3])
    if len(names) > 3:
        head = f"{head}, and more"
    count = len(notes)
    label = "note" if count == 1 else "notes"
    return f"{count} educational {label} · {head}"


def _attach_supplement_previews(notes):
    enriched = []
    for note in notes:
        item = dict(note)
        item["preview"] = _preview_text(item.get("summary", ""), max_chars=90)
        enriched.append(item)
    return enriched


def format_category_list(categories):
    labels = [format_category_name(category).lower() for category in categories]

    if not labels:
        return "general"

    if len(labels) == 1:
        return labels[0]

    if len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"

    return ", ".join(labels[:-1]) + f", and {labels[-1]}"


def get_sorted_categories(scores):
    if not isinstance(scores, dict):
        scores = {"hormonal": 0, "metabolic": 0, "inflammatory": 0}

    safe_scores = {
        "hormonal": scores.get("hormonal", 0),
        "metabolic": scores.get("metabolic", 0),
        "inflammatory": scores.get("inflammatory", 0),
    }

    return sorted(safe_scores.items(), key=lambda item: item[1], reverse=True)


def build_result_logic_summary(scores, responses):
    sorted_categories = get_sorted_categories(scores)
    top_category, top_score = sorted_categories[0]
    second_category, second_score = sorted_categories[1]
    third_category, third_score = sorted_categories[2]

    profile = calculate_response_profile(responses)

    score_gap = top_score - second_score
    all_zero = top_score == 0 and second_score == 0 and third_score == 0
    all_equal_non_zero = top_score == second_score == third_score and top_score > 0
    balanced_top_two = score_gap <= 1 and second_score > 0
    low_signal = (
        all_zero
        or (profile["yes"] <= 1 and profile["maybe"] >= 2)
        or (top_score <= 1 and profile["yes"] <= 2)
    )

    return {
        "top_category": top_category,
        "top_score": top_score,
        "second_category": second_category,
        "second_score": second_score,
        "third_category": third_category,
        "third_score": third_score,
        "balanced_top_two": balanced_top_two,
        "all_equal_non_zero": all_equal_non_zero,
        "low_signal": low_signal,
        "yes_count": profile["yes"],
        "maybe_count": profile["maybe"],
    }


def get_symptom_category_contributions(symptom_id):
    symptom_rules = load_symptom_rules()
    symptom = SYMPTOM_DETAILS.get(symptom_id, {})
    default_category = symptom.get("default_category", "general")

    if symptom_id in symptom_rules:
        active_categories = [
            category
            for category, weight in symptom_rules[symptom_id].items()
            if weight > 0
        ]
        if active_categories:
            return active_categories

    if default_category in CATEGORY_LABELS:
        return [default_category]

    return []


def get_contributing_symptoms(responses):
    contributing = []

    if not isinstance(responses, dict):
        return contributing

    for symptom_id, answer in responses.items():
        normalised_answer = normalise_response(answer)

        if normalised_answer not in {"yes", "maybe"}:
            continue

        symptom = SYMPTOM_DETAILS.get(
            symptom_id,
            {
                "label": symptom_id.replace("_", " ").title(),
                "short_label": symptom_id.replace("_", " ").title(),
                "default_category": "general",
            },
        )

        categories = get_symptom_category_contributions(symptom_id)

        contributing.append(
            {
                "id": symptom_id,
                "label": symptom["label"],
                "short_label": symptom["short_label"],
                "default_category": symptom.get("default_category", "general"),
                "categories": categories,
                "category_labels": [format_category_name(category) for category in categories],
                "category_text": format_category_list(categories),
                "response": normalised_answer,
            }
        )

    contributing.sort(key=lambda item: (0 if item["response"] == "yes" else 1, item["label"]))
    return contributing


def group_contributing_symptoms_by_category(contributing_symptoms):
    grouped = {
        "hormonal": [],
        "metabolic": [],
        "inflammatory": [],
    }

    for item in contributing_symptoms:
        for category in item.get("categories", []):
            if category in grouped:
                grouped[category].append(item)

    return grouped


def get_prominent_categories(scores):
    sorted_categories = get_sorted_categories(scores)
    highest_score = sorted_categories[0][1]
    prominent = []

    for category, score in sorted_categories:
        if highest_score == 0:
            continue
        if score >= highest_score - 1 and score > 0:
            prominent.append(category)

    return prominent


def build_contributing_intro(contributing_symptoms):
    if not contributing_symptoms:
        return (
            "No strong contributing symptoms were selected in this response, so HerSignal has less detail to connect into a clearer pattern."
        )

    yes_count = sum(1 for item in contributing_symptoms if item["response"] == "yes")
    maybe_count = sum(1 for item in contributing_symptoms if item["response"] == "maybe")
    overlap_count = sum(1 for item in contributing_symptoms if len(item["categories"]) > 1)

    if yes_count >= 4 and overlap_count >= 2:
        return (
            "These symptoms showed up most clearly in your answers, and several also appeared across more than one educational category. "
            "That overlap may help explain why the pattern feels connected rather than isolated."
        )

    if yes_count >= 4:
        return (
            "These symptoms showed up most clearly in your answers and shaped the strongest educational pattern in this result."
        )

    if maybe_count > yes_count:
        return (
            "These symptoms contributed to the result, although some answers carried uncertainty. "
            "HerSignal suggests reading this pattern gently and noticing what repeats over time."
        )

    if overlap_count >= 2:
        return (
            "These symptom signals contributed to the result, and some influenced more than one educational category rather than sitting in a single group alone."
        )

    return (
        "These symptom signals helped HerSignal organise your answers into the educational categories shown above."
    )


def build_pattern_overlap_note(scores, responses, logic_summary=None):
    logic_summary = logic_summary or build_result_logic_summary(scores, responses)

    top_category = logic_summary["top_category"]
    second_category = logic_summary["second_category"]

    top_label = format_category_name(top_category)
    second_label = format_category_name(second_category)

    if logic_summary["all_equal_non_zero"]:
        return (
            f"Your responses suggest broad overlap across symptom areas, with {top_label.lower()} and {second_label.lower()} signals appearing closely together as part of the same wider pattern."
        )

    if logic_summary["balanced_top_two"]:
        return (
            f"Your responses suggest noticeable overlap between {top_label.lower()} and {second_label.lower()} areas, which may be easier to understand when read as connected signals rather than separate themes."
        )

    return (
        f"Your responses appear more concentrated in the {top_label.lower()} area, although overlap may still exist across your broader symptom picture."
    )


def build_symptom_specific_explanation(scores, responses, grouped_symptoms, logic_summary=None):
    """
    Return spaced paragraphs for the featured "What this may mean" block.
    Copy is concise, educational, and avoids hyphen characters.
    """
    logic_summary = logic_summary or build_result_logic_summary(scores, responses)

    if logic_summary["low_signal"]:
        return [
            "This response shows a gentle pattern rather than one sharp signal standing alone.",
            "That can still be worth noticing if the same symptoms keep repeating across your cycle, sleep, or stress.",
            "Tracking what stays connected over time may help the picture feel less random and easier to understand.",
        ]

    top_category = logic_summary["top_category"]

    if logic_summary["balanced_top_two"]:
        top_label = format_category_name(logic_summary["top_category"]).lower()
        second_label = format_category_name(logic_summary["second_category"]).lower()
        return [
            f"Your responses suggest that {top_label} and {second_label} pattern signals are showing up closely together right now.",
            "These areas may be part of the same wider picture rather than separate stories.",
            "Noticing how they connect over time may help you understand the pattern more clearly than focusing on one symptom alone.",
        ]

    if top_category == "hormonal":
        return [
            "Your responses suggest that symptoms linked to hormones are showing up most clearly right now.",
            "These signals can feel separate, but in PCOS they may be part of the same hormonal pattern.",
            "Behind the scenes, hormone signalling can become uneven, and your body may show this through your cycle, skin, hair, and mood.",
            "Metabolic or inflammatory overlap may still be playing a role in the background.",
        ]

    if top_category == "metabolic":
        return [
            "Your responses suggest that metabolic pattern signals may be showing up most clearly in this result.",
            "Cravings, energy dips, or difficulty with weight changes may feel confusing when daily habits stay similar.",
            "In PCOS, how the body handles insulin and energy can influence hormones behind the scenes.",
            "Noticing meals, energy, and mood together over time may help these signals feel less random and easier to understand.",
        ]

    if top_category == "inflammatory":
        return [
            "Your responses suggest that inflammatory pattern signals may be showing up most clearly right now.",
            "Fatigue, bloating, skin irritation, or symptoms during stress can cluster when the body stays under gentle ongoing strain.",
            "That strain may influence energy, hormones, and recovery together rather than as separate problems.",
            "Easing pressures that feed inflammation may help some daily symptoms feel lighter over time.",
        ]

    return [
        "Your responses suggest overlap across more than one symptom area.",
        "In PCOS, hormonal, metabolic, and inflammatory processes often influence one another.",
        "Seeing the wider pattern may be more useful than focusing on a single symptom alone.",
    ]


def build_chart_explanation(scores, logic_summary=None):
    """
    Explain what the chart is showing visually.
    """
    sorted_categories = get_sorted_categories(scores)
    top_category, top_score = sorted_categories[0]
    second_category, second_score = sorted_categories[1]
    third_category, third_score = sorted_categories[2]

    top_label = format_category_name(top_category)
    second_label = format_category_name(second_category)

    if top_score == second_score == third_score and top_score > 0:
        return (
            "The chart shows a fairly even shape across all three categories. "
            "This suggests your selected symptoms are spread across hormonal, metabolic, and inflammatory areas rather than concentrated in one section alone."
        )

    if top_score - second_score <= 1 and second_score > 0:
        return (
            f"The chart extends most clearly across the {top_label.lower()} and {second_label.lower()} sides. "
            "More of your selected symptoms were grouped into those two educational areas, which may visually support a mixed or overlapping symptom picture."
        )

    if top_score > 0 and second_score > 0:
        return (
            f"The chart leans most strongly toward the {top_label.lower()} side, with a smaller extension toward the {second_label.lower()} side. "
            f"This suggests {top_label.lower()} signals were more noticeable in this response, while some {second_label.lower()} overlap may still be present."
        )

    if top_score > 0:
        return (
            f"The chart leans most strongly toward the {top_label.lower()} side. "
            "This suggests your selected symptoms were more concentrated in that educational category than in the others."
        )

    return (
        "The chart remains fairly small because only limited symptom activity was captured in this response. "
        "HerSignal suggests reading it gently, mainly as a simple visual organiser of the answers you shared."
    )


def build_friendly_note(scores, responses, logic_summary=None):
    """
    Provide a useful and supportive closing note based on the pattern.
    """
    profile = calculate_response_profile(responses)
    yes_count = profile["yes"]
    maybe_count = profile["maybe"]
    prominent_categories = get_prominent_categories(scores)

    if maybe_count >= 3:
        return (
            "If some of these answers felt uncertain, it may help to notice whether symptoms repeat around your cycle, stress periods, sleep changes, or food and energy patterns. "
            "Tracking this over time can sometimes help the pattern feel clearer and less random."
        )

    if len(prominent_categories) >= 2:
        return (
            "Because more than one symptom area appears active here, it may be useful to notice how cycle changes, skin or hair changes, fatigue, cravings, mood changes, and difficulty with weight connect over time rather than looking at them one by one."
        )

    if yes_count >= 4:
        return (
            "This response suggests a more noticeable symptom pattern, so a simple tracker for periods, skin changes, hair changes, cravings, energy, mood, and changes in weight may help you spot whether these experiences are staying linked over time."
        )

    return (
        "This result is best used as a gentle educational awareness tool. Even a lighter pattern can still be worth noticing if the same symptoms keep repeating over time."
    )


def select_supplement_notes(scores, responses=None, grouped_symptoms=None, logic_summary=None):
    supplement_data = load_supplement_info()
    selected_keys = []

    grouped_symptoms = grouped_symptoms or {"hormonal": [], "metabolic": [], "inflammatory": []}
    logic_summary = logic_summary or build_result_logic_summary(scores, responses or {})

    if logic_summary["top_category"] == "hormonal":
        selected_keys.extend(["myo_inositol", "vitamin_d", "spearmint_tea", "chromium"])

    elif logic_summary["top_category"] == "metabolic":
        selected_keys.extend(["myo_inositol", "magnesium", "l_carnitine", "zinc"])

    elif logic_summary["top_category"] == "inflammatory":
        selected_keys.extend(["omega_3", "curcumin", "probiotics", "selenium"])

    notes = []
    for key in selected_keys[:4]:
        supplement = supplement_data.get(key, {})
        notes.append(
            {
                "name": supplement.get("name", key.replace("_", " ").title()),
                "summary": supplement.get("summary", ""),
                "warning": supplement.get("warning", ""),
            }
        )

    return notes


def build_supplement_intro(notes, logic_summary=None):
    if not notes:
        return "No specific supplement notes were triggered by this response pattern."

    return (
        "HerSignal has shared these gentle educational notes based on the symptom categories that appeared more noticeable in your response."
    )


def generate_result_data(scores, responses):
    try:
        safe_scores = {
            "hormonal": scores.get("hormonal", 0),
            "metabolic": scores.get("metabolic", 0),
            "inflammatory": scores.get("inflammatory", 0),
        }

        logic_summary = build_result_logic_summary(safe_scores, responses)
        contributing_symptoms = get_contributing_symptoms(responses)
        grouped_symptoms = group_contributing_symptoms_by_category(contributing_symptoms)

        supplement_notes = _attach_supplement_previews(
            select_supplement_notes(
                safe_scores,
                responses=responses,
                grouped_symptoms=grouped_symptoms,
                logic_summary=logic_summary,
            )
        )

        why_paragraphs = build_symptom_specific_explanation(
            safe_scores, responses, grouped_symptoms, logic_summary=logic_summary
        )
        overlap_note = build_pattern_overlap_note(
            safe_scores, responses, logic_summary=logic_summary
        )
        chart_explanation = build_chart_explanation(safe_scores, logic_summary=logic_summary)
        friendly_note = build_friendly_note(safe_scores, responses, logic_summary=logic_summary)

        return {
            "page_title": "Your Symptom Pattern Results",
            "page_intro": "HerSignal has grouped your answers into hormonal, metabolic, and inflammatory educational scores to help you see the pattern below.",
            "scores": safe_scores,
            "contributing_intro": build_contributing_intro(contributing_symptoms),
            "contributing_preview": _build_contributing_preview(contributing_symptoms),
            "contributing_symptoms": contributing_symptoms,
            "grouped_contributing_symptoms": grouped_symptoms,
            "pattern_overlap_note": overlap_note,
            "overlap_preview": _preview_text(_first_sentence(overlap_note), max_chars=100),
            "why_hersignal_paragraphs": why_paragraphs,
            "why_preview": _preview_from_paragraphs(why_paragraphs, max_chars=100),
            "why_hersignal_presented_response": _join_paragraphs(why_paragraphs),
            "supplement_intro": build_supplement_intro(supplement_notes, logic_summary=logic_summary),
            "supplements_preview": _build_supplements_preview(supplement_notes),
            "supplement_notes": supplement_notes,
            "chart_explanation": chart_explanation,
            "chart_preview": _preview_text(_first_sentence(chart_explanation), max_chars=100),
            "friendly_note": friendly_note,
            "note_preview": _preview_text(_first_sentence(friendly_note), max_chars=100),
            "general_disclaimer": "HerSignal is for education and support only. It does not diagnose PCOS, replace professional medical advice, or recommend treatment.",
            "supplement_disclaimer": "Supplement information from HerSignal is educational only. Please consult a qualified healthcare professional before starting supplements.",
        }

    except Exception:
        logger.exception("Unexpected error while generating result data.")
        fallback_paragraphs = [
            "HerSignal could not share a fuller interpretation just now.",
            "You can still use the category scores above as a gentle educational guide.",
        ]
        return {
            "page_title": "Your Symptom Pattern Results",
            "page_intro": "HerSignal could not build the full result just now.",
            "scores": {"hormonal": 0, "metabolic": 0, "inflammatory": 0},
            "contributing_intro": "No symptom details available.",
            "contributing_preview": "No contributing symptoms highlighted",
            "contributing_symptoms": [],
            "grouped_contributing_symptoms": {"hormonal": [], "metabolic": [], "inflammatory": []},
            "pattern_overlap_note": "A full overlap explanation could not be generated just now.",
            "overlap_preview": "Overlap note unavailable",
            "why_hersignal_paragraphs": fallback_paragraphs,
            "why_preview": fallback_paragraphs[0],
            "why_hersignal_presented_response": _join_paragraphs(fallback_paragraphs),
            "supplement_intro": "No supplement notes available.",
            "supplements_preview": "No supplement notes for this pattern",
            "supplement_notes": [],
            "chart_explanation": "A chart explanation could not be prepared just now.",
            "chart_preview": "Chart explanation unavailable",
            "friendly_note": "Please use this as a gentle educational guide.",
            "note_preview": "Gentle educational guide",
            "general_disclaimer": "HerSignal is an educational support system only.",
            "supplement_disclaimer": "Supplement information is educational only.",
        }


def generate_result_summary(scores, responses):
    result_data = generate_result_data(scores, responses)

    lines = [
        "HerSignal Insight Summary:",
        "",
        "Symptoms contributing to this result:",
        result_data["contributing_intro"],
    ]

    for item in result_data["contributing_symptoms"]:
        lines.append(f"• {item['label']}")

    lines.extend(
        [
            "",
            "Pattern overlap notes:",
            result_data["pattern_overlap_note"],
            "",
            "Why HerSignal presented this response:",
            result_data["why_hersignal_presented_response"],
            "",
            "Suggested educational supplement notes:",
            result_data["supplement_intro"],
        ]
    )

    for note in result_data["supplement_notes"]:
        lines.append(f"• {note['name']}: {note['summary']}")

    return "\n".join(lines)