"""
Educational copy for the follow-up (retake) insight page.

Language is intentionally cautious: "suggest", "in this check", "more noticeable",
not diagnosis or verified symptom trajectories.
"""

from logic.score_normalization import CATEGORY_KEYS

# On 0–1 normalized scale; within this band we call the category "fairly stable"
STABLE_BAND = 0.05

CATEGORY_LABELS = {
    "hormonal": "Hormonal",
    "metabolic": "Metabolic",
    "inflammatory": "Inflammatory",
}


def _trend_for_delta(delta):
    if abs(delta) < STABLE_BAND:
        return "stable"
    if delta > 0:
        return "more_noticeable"
    return "slightly_reduced"


def build_category_trends(normalized_previous, normalized_current):
    """
    Per-category trend labels comparing current follow-up to the saved prior insight.
    """
    trends = {}
    for k in CATEGORY_KEYS:
        prev_v = float(normalized_previous.get(k) or 0)
        cur_v = float(normalized_current.get(k) or 0)
        delta = round(cur_v - prev_v, 4)
        trends[k] = {
            "delta": delta,
            "trend": _trend_for_delta(delta),
            "label": CATEGORY_LABELS[k],
            "previous": prev_v,
            "current": cur_v,
        }
    return trends


def build_category_interpretation_sentences(trends):
    """Short educational sentences per category."""
    sentences = []
    for k in CATEGORY_KEYS:
        t = trends[k]
        label = CATEGORY_LABELS[k]
        if t["trend"] == "stable":
            sentences.append(
                f"Your {label} educational category looks fairly stable compared with "
                "your previous saved insight in this follow-up check."
            )
        elif t["trend"] == "more_noticeable":
            sentences.append(
                f"In this follow-up, {label} areas may appear slightly more noticeable "
                "in the educational categories than in your previous saved insight."
            )
        else:
            sentences.append(
                f"In this follow-up, {label} areas may appear slightly reduced in how "
                "salient they look within the educational categories compared with your previous insight."
            )
    return sentences


def build_overall_pattern_summary(trends):
    """
    One paragraph: stable / mixed / directional — category-level only.
    """
    verdicts = [trends[k]["trend"] for k in CATEGORY_KEYS]
    if all(v == "stable" for v in verdicts):
        return (
            "Across the three educational categories, your follow-up responses suggest a fairly stable "
            "picture compared with your last saved insight."
        )
    ups = sum(1 for v in verdicts if v == "more_noticeable")
    downs = sum(1 for v in verdicts if v == "slightly_reduced")
    stables = sum(1 for v in verdicts if v == "stable")
    if ups >= 1 and downs >= 1:
        return (
            "This follow-up suggests mixed pattern changes: some educational categories look a little "
            "more salient than before, and others a little less, which is common when life context shifts."
        )
    if ups >= 2:
        return (
            "In this check, more than one educational category looks somewhat more noticeable than "
            "in your previous insight—useful as a reflection point, not as a medical judgement."
        )
    if downs >= 2:
        return (
            "In this check, several categories look a little less salient than in your previous "
            "insight within this educational tool—still only a snapshot of how you answered today."
        )
    if stables >= 2 and ups == 1:
        return (
            "Most categories look fairly stable, with one area standing out a bit more in this "
            "follow-up than in your previous saved summary."
        )
    if stables >= 2 and downs == 1:
        return (
            "Most categories look fairly stable, with one area a little less prominent in this "
            "follow-up than in your last saved summary."
        )
    return (
        "Your follow-up shows a blend of small shifts across educational categories—helpful for noticing "
        "patterns over time, not for diagnosing an illness."
    )


def dominant_pattern_note(previous_dominant_label, current_dominant_label):
    """
    Optional short note when the same dominant category appears twice — careful wording.
    """
    if not previous_dominant_label or not current_dominant_label:
        return None
    prev_f = (previous_dominant_label or "").strip().lower()
    cur_f = (current_dominant_label or "").strip().lower()
    if not prev_f or not cur_f:
        return None
    if prev_f == cur_f:
        return (
            "The same broad educational category stood out most strongly in both this follow-up and "
            "your previous saved insight—which can mean that theme has stayed on your mind, not that "
            "anything is medically \"persistent\"."
        )
    return None


def followup_reflection_bullets(retake_questions, responses):
    """
    Map change-focused questions (ids starting with followup_) to reflection bullets
    when the user answered yes or maybe.
    """
    reflections = {
        "followup_energy_cravings_shift": {
            "yes": "You noted that energy crashes or strong cravings have felt more noticeable since your last saved insight.",
            "maybe": "You were unsure whether energy or craving patterns have shifted since your last saved insight.",
        },
        "followup_skin_complexion_shift": {
            "yes": "You noted that skin or complexion-related patterns have felt more noticeable since your last saved insight.",
            "maybe": "You were unsure whether skin or complexion changes have shifted since your last saved insight.",
        },
        "followup_stress_sleep_shift": {
            "yes": "You indicated that stress, sleep, or related ups and downs have made symptoms feel harder to manage lately.",
            "maybe": "You were unsure whether stress or sleep context has changed how symptoms feel.",
        },
        "followup_weight_appetite_shift": {
            "yes": "You noted that weight or appetite changes have felt more noticeable in daily life since your last saved insight.",
            "maybe": "You were unsure whether weight or appetite patterns have shifted since your last saved insight.",
        },
    }
    bullets = []
    for item in retake_questions:
        qid = item.get("id", "")
        if not str(qid).startswith("followup_"):
            continue
        raw = (responses.get(qid) or "").strip().lower()
        if raw not in ("yes", "maybe"):
            continue
        msgs = reflections.get(qid, {})
        text = msgs.get(raw)
        if text:
            bullets.append(text)
    return bullets
