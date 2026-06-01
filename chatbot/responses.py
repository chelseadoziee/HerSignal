import logging
import random

from chatbot.matcher import get_ranked_faq_matches


logger = logging.getLogger(__name__)
FAQ_MATCH_THRESHOLD = 0.70
FAQ_NEAR_THRESHOLD_MIN = 0.60

FOLLOW_UPS = {
    "basics": [
        "I’m here if you’d like to ask another question.",
        "You can also explore more symptoms if something feels familiar.",
    ],
    "symptoms_hormonal": [
        "Hormonal symptoms can look different from one woman to another.",
        "You can also check how your wider symptom pattern fits together.",
    ],
    "symptoms_metabolic": [
        "Metabolic symptoms often overlap more than women expect.",
        "Most times these patterns make more sense when viewed together.",
    ],
    "symptoms_inflammatory": [
        "Inflammatory symptoms can sometimes feel subtle at first.",
        "These symptoms often overlap with other syptoms of PCOS too.",
    ],
    "management": [
        "Support usually works best when it fits your own pattern.",
        "You can also explore the symptom checker if you want a broader view.",
    ],
    "fertility": [
        "Fertility experiences can vary a lot between women.",
        "If this is a major concern, professional guidance is always important too.",
    ],
    "supplements": [
        "Supplement choices usually work best when approached carefully.",
        "It helps to understand the wider symptom pattern before relying on one option.",
    ],
    "safety": [
        "If symptoms feel severe or confusing, speaking to a healthcare professional matters.",
        "Educational tools work best alongside proper medical support when needed.",
    ]
}


def clean_join(parts):
    return " ".join(part.strip() for part in parts if part and str(part).strip())


def get_faq_response(user_input):
    try:
        if not user_input or not str(user_input).strip():
            return "Please type a short PCOS-related question so HerSignal can guide you more clearly."

        ranked_matches = get_ranked_faq_matches(user_input)
        if not ranked_matches:
            return "I’m still learning the best way to answer that clearly. Could you maybe try asking it in a slightly different way?"

        top_match = ranked_matches[0]
        top_score = float(top_match.get("score", 0.0))

        if top_score >= FAQ_MATCH_THRESHOLD:
            category = top_match.get("category", "basics")
            core_answer = top_match.get("answer", "").strip()

            if not core_answer:
                return "HerSignal found a possible match for that question, but the answer could not be prepared clearly just now. Please try again."

            follow_up = random.choice(
                FOLLOW_UPS.get(category, ["Let me know if you would like to explore that a little further."])
            )

            return clean_join([core_answer, follow_up])

        if top_score >= FAQ_NEAR_THRESHOLD_MIN and len(ranked_matches) > 1:
            option_a = top_match.get("display_question", top_match.get("question", "")).strip()
            option_b = ranked_matches[1].get("display_question", ranked_matches[1].get("question", "")).strip()
            if option_a and option_b:
                return clean_join(
                    [
                        "I found two close topics but I’m not fully certain.",
                        f"Did you mean: '{option_a}' or '{option_b}'?",
                    ]
                )

        return "I’m still learning the best way to answer that clearly. Could you maybe try asking it in a slightly different way?"

    except Exception:
        logger.exception("Unexpected error while generating FAQ response.")
        return "Something went wrong while HerSignal was preparing that answer. Please try again."
