import unittest

from logic.scoring_engine import load_symptom_questions, calculate_category_scores, normalise_response
from logic.score_normalization import (
    max_possible_category_scores,
    normalize_scores_unit_interval,
    normalized_deltas,
)


class RetakeNormalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pathlib import Path

        root = Path(__file__).resolve().parent.parent
        cls.retake_path = root / "data" / "retake_questions.json"
        cls.retake_q = load_symptom_questions(cls.retake_path)

    def test_max_possible_non_zero_for_retake(self):
        mx = max_possible_category_scores(self.retake_q)
        for k in ("hormonal", "metabolic", "inflammatory"):
            self.assertGreater(mx[k], 0, k)

    def test_normalize_full_yes_is_one(self):
        mx = max_possible_category_scores(self.retake_q)
        responses = {item["id"]: "yes" for item in self.retake_q}
        raw = calculate_category_scores(responses, questions=self.retake_q)
        norm = normalize_scores_unit_interval(raw, mx)
        for k in ("hormonal", "metabolic", "inflammatory"):
            self.assertAlmostEqual(norm[k], 1.0, places=3, msg=k)

    def test_normalized_delta_direction(self):
        mx = max_possible_category_scores(self.retake_q)
        all_yes = {item["id"]: "yes" for item in self.retake_q}
        all_no = {item["id"]: "no" for item in self.retake_q}
        raw_high = calculate_category_scores(all_yes, questions=self.retake_q)
        raw_low = calculate_category_scores(all_no, questions=self.retake_q)
        norm_high = normalize_scores_unit_interval(raw_high, mx)
        norm_low = normalize_scores_unit_interval(raw_low, mx)
        d = normalized_deltas(norm_high, norm_low)
        for k in d:
            self.assertGreaterEqual(d[k], 0)


if __name__ == "__main__":
    unittest.main()
