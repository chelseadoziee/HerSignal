"""
Scale raw category scores to a 0–1 range so baseline (full questionnaire) and
retake (shorter questionnaire) summaries can be compared fairly.

Maxima are computed as if every question in the given list were answered "yes"
(full response weight), using the same rule merge logic as calculate_category_scores.
"""

from logic.scoring_engine import (
    CATEGORY_KEYS,
    RESPONSE_WEIGHTS,
    build_fallback_rule_map,
    load_symptom_rules,
    merge_rules_with_fallback,
    normalise_response,
)


def max_possible_category_scores(questions, symptom_rules=None):
    """
    Upper bound per category for the given question list (all "yes" answers).

    Returns the same keys as calculate_category_scores: hormonal, metabolic, inflammatory.
    """
    if symptom_rules is None:
        symptom_rules = load_symptom_rules()

    if not questions:
        return {k: 0.0 for k in CATEGORY_KEYS}

    fallback_rules = build_fallback_rule_map(questions)
    merged_rules = merge_rules_with_fallback(symptom_rules, fallback_rules)

    scores = {k: 0.0 for k in CATEGORY_KEYS}

    for item in questions:
        if not isinstance(item, dict):
            continue
        symptom_id = item.get("id")
        if not symptom_id:
            continue

        answer = normalise_response("yes")
        response_weight = RESPONSE_WEIGHTS.get(answer, 0)
        if response_weight == 0:
            continue

        category_weights = merged_rules.get(symptom_id, fallback_rules.get(symptom_id, {}))
        for category in CATEGORY_KEYS:
            rule_weight = category_weights.get(category, 0)
            contribution = response_weight * (rule_weight / 2)
            scores[category] += contribution

    return {k: round(scores[k], 4) for k in CATEGORY_KEYS}


def normalize_scores_unit_interval(raw_scores, max_scores):
    """
    Map raw totals into ~[0, 1] by dividing by per-category maxima.

    If a category has no weight in this questionnaire (max == 0), the normalized
    value is 0.0 to avoid divide-by-zero.
    """
    out = {}
    for k in CATEGORY_KEYS:
        raw = float(raw_scores.get(k) or 0)
        mx = float(max_scores.get(k) or 0)
        if mx <= 0:
            out[k] = 0.0
        else:
            ratio = min(1.0, max(0.0, raw / mx))
            out[k] = round(ratio, 4)
    return out


def normalized_deltas(normal_current, normal_previous):
    """Later minus earlier on the 0–1 scale (educational comparison only)."""
    return {
        k: round(float(normal_current.get(k) or 0) - float(normal_previous.get(k) or 0), 4)
        for k in CATEGORY_KEYS
    }


def test_type_is_retake(value):
    return (value or "").strip().lower() == "retake"
