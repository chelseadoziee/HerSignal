import unittest

from chatbot import matcher


class MatcherIntentAggregationTests(unittest.TestCase):
    def test_build_intent_id_uses_raw_when_present(self):
        intent_id = matcher._build_intent_id(
            question="What is PCOS?",
            raw_intent_id="FAQ_BASICS_PCOs"
        )
        self.assertEqual(intent_id, "faq_basics_pcos")

    def test_build_intent_id_falls_back_to_question_slug(self):
        intent_id = matcher._build_intent_id(
            question="What causes PCOS?",
            raw_intent_id=""
        )
        self.assertEqual(intent_id, "faq_what_causes_pcos")

    def test_aggregate_ranked_by_intent_keeps_highest_score_per_intent(self):
        ranked_items = [
            {"question": "what is pcos", "intent_id": "faq_basics_pcos", "score": 0.81},
            {"question": "pcos meaning", "intent_id": "faq_basics_pcos", "score": 0.88},
            {"question": "pcos fatigue", "intent_id": "faq_symptom_fatigue", "score": 0.86},
        ]

        aggregated = matcher._aggregate_ranked_by_intent(ranked_items)

        self.assertEqual(len(aggregated), 2)
        self.assertEqual(aggregated[0]["intent_id"], "faq_basics_pcos")
        self.assertAlmostEqual(aggregated[0]["score"], 0.88)
        self.assertEqual(aggregated[1]["intent_id"], "faq_symptom_fatigue")


if __name__ == "__main__":
    unittest.main()
