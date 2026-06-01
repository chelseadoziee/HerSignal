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
        "acne": "acne-related skin changes",
        "facial_hair": "facial or body hair growth changes",
        "scalp_thinning": "scalp hair thinning or shedding",
        "weight_changes": "weight-related difficulty",
        "fatigue": "fatigue or low energy",
        "cravings": "cravings or energy crashes",
        "stress_worsening": "stress-linked symptom worsening",
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
        "stress_worsening": "Stress-linked symptom worsening",
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
            "No strong contributing symptoms were selected in this response, so HerSignal has less information to organise into a clearer pattern."
        )

    yes_count = sum(1 for item in contributing_symptoms if item["response"] == "yes")
    maybe_count = sum(1 for item in contributing_symptoms if item["response"] == "maybe")
    overlap_count = sum(1 for item in contributing_symptoms if len(item["categories"]) > 1)

    if yes_count >= 4 and overlap_count >= 2:
        return (
            "These symptoms contributed most clearly to the result because they were selected directly and several of them also overlapped across more than one educational category."
        )

    if yes_count >= 4:
        return (
            "These symptoms contributed most clearly to the result because they were selected directly and formed the strongest educational pattern in this response."
        )

    if maybe_count > yes_count:
        return (
            "These symptoms contributed to the result, although some were selected with uncertainty. "
            "That means the pattern should still be read gently."
        )

    if overlap_count >= 2:
        return (
            "These symptom areas contributed to the result, and some of them influenced more than one educational category rather than sitting in only one group."
        )

    return (
        "These symptom areas contributed to the result and helped HerSignal organise the response into the educational categories shown above."
    )


def build_pattern_overlap_note(scores, responses, logic_summary=None):
    logic_summary = logic_summary or build_result_logic_summary(scores, responses)

    top_category = logic_summary["top_category"]
    second_category = logic_summary["second_category"]

    top_label = format_category_name(top_category)
    second_label = format_category_name(second_category)

    if logic_summary["all_equal_non_zero"]:
        return (
            f"Your responses show a broad overlap across multiple symptom areas, with {top_label.lower()} and {second_label.lower()} features appearing closely together."
        )

    if logic_summary["balanced_top_two"]:
        return (
            f"Your responses suggest noticeable overlap between {top_label.lower()} and {second_label.lower()} symptom areas."
        )

    return (
        f"Your responses appear more concentrated in the {top_label.lower()} category, although some overlap may still exist across the broader symptom picture."
    )


def build_symptom_specific_explanation(scores, responses, grouped_symptoms, logic_summary=None):
    logic_summary = logic_summary or build_result_logic_summary(scores, responses)

    if logic_summary["low_signal"]:
        return (
            "The current response does not show a very strong or sharply defined symptom pattern. It may help to notice whether the same changes keep repeating over time."
        )

    top_category = logic_summary["top_category"]

    if logic_summary["balanced_top_two"]:
        top_label = format_category_name(logic_summary["top_category"]).lower()
        second_label = format_category_name(logic_summary["second_category"]).lower()
        return (
            f"Your responses suggest a mixed {top_label} and {second_label} pattern rather than one isolated category."
        )

    if top_category == "hormonal":
        return (
            "Based off your responses, your PCOS symptoms suggest that hormonal features are currently more noticeable. "
            "Common PCOS symptoms such as irregular periods, acne, facial hair growth, scalp hair thinning, "
            "or mood changes often reflect the way androgen activity and ovarian hormone signalling can become disrupted in PCOS. "
            "This usually happens because the ovaries begin producing hormones in an uneven pattern, which can interfere with regular ovulation "
            "and make hormone levels shift in ways the body feels quite clearly through the skin, hair, menstrual cycle, and emotional rhythm. "
            "When ovulation becomes inconsistent, periods may arrive unpredictably, acne may become harder to control, "
            "and hair changes can feel confusing because the body is responding to hormone signals that are not staying balanced. "
            "Even when hormonal symptoms appear strongest, overlap with metabolic or inflammatory activity can still exist underneath. "
            "In many women, understanding why these symptoms are appearing together is important because reducing the pressure behind those hormonal disruptions "
            "may gradually help some symptoms feel easier to manage over time."
        )

    if top_category == "metabolic":
        return (
            "This response suggests that metabolic features are currently more noticeable in your PCOS pattern. "
            "In PCOS, this often means the body may be responding less efficiently to insulin, even when blood sugar problems are not obvious. "
            "When that happens, the body can hold onto energy differently, which may make weight changes feel difficult to explain, "
            "increase cravings, create tiredness after meals, or lead to sudden drops in energy during the day. "
            "Many women notice that these symptoms feel frustrating because effort does not always produce the expected result, "
            "especially when appetite, body response, and energy rhythm seem to work against each other. "
            "This pattern develops because insulin does more than regulate sugar, it also influences hormone behaviour, "
            "which means metabolic strain can quietly make other PCOS symptoms feel stronger too. "
            "Understanding that connection can help because improving the reasons these symptoms cluster together "
            "may gradually relieve part of the daily symptom burden."
        )

    if top_category == "inflammatory":
        return (
            "This response suggests that inflammatory features are currently more noticeable in your PCOS pattern. "
            "Inflammatory patterns in PCOS can appear through fatigue, skin irritation, internal heaviness, poor recovery from stress, "
            "or symptoms feeling worse during emotionally demanding periods. "
            "This happens because the body can remain in a low-level stressed state for long periods, "
            "which may influence how the immune system, hormones, and energy regulation interact. "
            "That can make symptoms feel heavier than expected, even when outward signs are difficult to explain clearly. "
            "Inflammatory activity often does not stay separate from hormones or metabolism, "
            "which is why symptoms can sometimes feel layered rather than isolated. "
            "Understanding that pattern matters because easing some of the pressures that feed inflammation "
            "may help reduce how intense certain symptoms feel over time."
        )

    return (
        "Your responses suggest overlap across more than one symptom area. "
        "This reflects how PCOS rarely behaves in one isolated category because hormonal, metabolic, "
        "and inflammatory processes often influence one another together. "
        "When symptoms overlap like this, understanding the wider pattern often becomes more useful than focusing on one symptom alone, "
        "because improving one underlying area can sometimes ease pressure across several symptoms at once."
    )


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
            "This suggests the selected symptoms are spread across the hormonal, metabolic, and inflammatory areas rather than being concentrated in one section alone."
        )

    if top_score - second_score <= 1 and second_score > 0:
        return (
            f"The chart extends most clearly across the {top_label.lower()} and {second_label.lower()} sides. "
            "This means more of the selected symptoms were grouped into those two educational areas, which visually supports a mixed or overlapping symptom picture."
        )

    if top_score > 0 and second_score > 0:
        return (
            f"The chart leans most strongly toward the {top_label.lower()} side, with a smaller extension toward the {second_label.lower()} side. "
            f"This suggests that {top_label.lower()} features were more noticeable in this response, while some {second_label.lower()} overlap also remains present."
        )

    if top_score > 0:
        return (
            f"The chart leans most strongly toward the {top_label.lower()} side. "
            "This suggests the selected symptoms were more concentrated in that educational category than in the others."
        )

    return (
        "The chart remains fairly small because only limited symptom activity was captured in this response. "
        "That means the visual pattern should be read cautiously and mainly as a simple organiser of the answers provided."
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
            "Tracking this over time can sometimes make the picture feel clearer."
        )

    if len(prominent_categories) >= 2:
        return (
            "Because more than one symptom area appears active here, it may be useful to notice how cycle changes, skin or hair changes, fatigue, cravings, mood changes, and weight-related difficulty connect over time rather than looking at them one by one."
        )

    if yes_count >= 4:
        return (
            "This response suggests a more noticeable symptom pattern, so a simple tracker for periods, skin changes, hair changes, cravings, energy, mood, and weight-related symptoms may help you spot whether these experiences are staying linked over time."
        )

    return (
        "This result is best used as a gentle awareness tool. Even a lighter pattern can still be worth noticing if the same symptoms keep repeating over time."
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
        "These educational notes are based on the symptom categories that appeared more noticeable in your response."
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

        supplement_notes = select_supplement_notes(
            safe_scores,
            responses=responses,
            grouped_symptoms=grouped_symptoms,
            logic_summary=logic_summary,
        )

        return {
            "page_title": "Your Symptom Pattern Results",
            "page_intro": "Based on your responses, HerSignal has organised your symptom findings into the PCOS symptom pattern categories below.",
            "scores": safe_scores,
            "contributing_intro": build_contributing_intro(contributing_symptoms),
            "contributing_symptoms": contributing_symptoms,
            "grouped_contributing_symptoms": grouped_symptoms,
            "pattern_overlap_note": build_pattern_overlap_note(safe_scores, responses, logic_summary=logic_summary),
            "why_hersignal_presented_response": build_symptom_specific_explanation(
                safe_scores, responses, grouped_symptoms, logic_summary=logic_summary
            ),
            "supplement_intro": build_supplement_intro(supplement_notes, logic_summary=logic_summary),
            "supplement_notes": supplement_notes,
            "chart_explanation": build_chart_explanation(safe_scores, logic_summary=logic_summary),
            "friendly_note": build_friendly_note(safe_scores, responses, logic_summary=logic_summary),
            "general_disclaimer": "HerSignal is an educational support system only. It does not diagnose PCOS, replace professional medical advice, or recommend treatment.",
            "supplement_disclaimer": "Supplement information provided by HerSignal is educational only. Women should consult a qualified healthcare professional before starting supplements.",
        }

    except Exception:
        logger.exception("Unexpected error while generating result data.")
        return {
            "page_title": "Your Symptom Pattern Results",
            "page_intro": "HerSignal could not build the full result just now.",
            "scores": {"hormonal": 0, "metabolic": 0, "inflammatory": 0},
            "contributing_intro": "No symptom details available.",
            "contributing_symptoms": [],
            "grouped_contributing_symptoms": {"hormonal": [], "metabolic": [], "inflammatory": []},
            "pattern_overlap_note": "A full overlap explanation could not be generated just now.",
            "why_hersignal_presented_response": "A fuller interpretation could not be generated just now.",
            "supplement_intro": "No supplement notes available.",
            "supplement_notes": [],
            "chart_explanation": "A chart explanation could not be prepared just now.",
            "friendly_note": "Please use this as a gentle educational guide.",
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
        lines.append(f"- {item['label']}")

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
        lines.append(f"- {note['name']}: {note['summary']}")

    return "\n".join(lines)