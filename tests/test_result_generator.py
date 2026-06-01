import unittest

from logic.result_generator import (
    build_symptom_specific_explanation,
    generate_result_data,
)

GENERATOR_OWNED_KEYS = (
    "page_title",
    "page_intro",
    "contributing_intro",
    "contributing_preview",
    "pattern_overlap_note",
    "overlap_preview",
    "why_hersignal_paragraphs",
    "why_preview",
    "why_hersignal_presented_response",
    "supplement_intro",
    "chart_explanation",
    "chart_preview",
    "friendly_note",
    "note_preview",
    "general_disclaimer",
    "supplement_disclaimer",
)

HEDGING_WORDS = ("may", "suggest", "appears", "can ")


def _collect_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _collect_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _collect_strings(item)


def _generator_owned_strings(result_data):
    for key in GENERATOR_OWNED_KEYS:
        if key in result_data:
            yield from _collect_strings(result_data[key])
    for item in result_data.get("contributing_symptoms", []):
        yield item.get("label", "")
        yield item.get("short_label", "")


class ResultGeneratorPanelDataTests(unittest.TestCase):
    def _hormonal_responses(self):
        return {
            "irregular_periods": "yes",
            "acne": "yes",
            "facial_hair": "yes",
            "mood_swings": "maybe",
            "weight_gain": "no",
            "fatigue": "no",
        }

    def test_generate_result_data_panel_fields(self):
        scores = {"hormonal": 4, "metabolic": 1, "inflammatory": 0}
        responses = self._hormonal_responses()
        data = generate_result_data(scores, responses)

        self.assertIsInstance(data["why_hersignal_paragraphs"], list)
        self.assertGreaterEqual(len(data["why_hersignal_paragraphs"]), 2)
        self.assertEqual(
            data["why_hersignal_presented_response"],
            "\n\n".join(data["why_hersignal_paragraphs"]),
        )
        self.assertTrue(data["why_preview"])
        self.assertTrue(data["contributing_preview"])
        self.assertTrue(data["overlap_preview"])
        self.assertTrue(data["chart_preview"])
        self.assertTrue(data["note_preview"])
        self.assertTrue(data["supplements_preview"])
        # supplements_preview may include names from supplement_info.json

        for note in data["supplement_notes"]:
            self.assertIn("preview", note)
            self.assertTrue(note["preview"])

    def test_explanation_paragraphs_have_no_hyphens(self):
        scores = {"hormonal": 5, "metabolic": 1, "inflammatory": 0}
        paragraphs = build_symptom_specific_explanation(
            scores,
            self._hormonal_responses(),
            {"hormonal": [], "metabolic": [], "inflammatory": []},
        )
        joined = " ".join(paragraphs)
        self.assertNotIn("-", joined)

    def test_generator_owned_strings_have_no_hyphens(self):
        scores = {"hormonal": 4, "metabolic": 1, "inflammatory": 0}
        data = generate_result_data(scores, self._hormonal_responses())
        for text in _generator_owned_strings(data):
            self.assertNotIn("-", text, msg=f"Unexpected hyphen in: {text[:80]!r}")

    def test_why_paragraphs_use_hedging_language(self):
        scores = {"hormonal": 5, "metabolic": 1, "inflammatory": 0}
        data = generate_result_data(scores, self._hormonal_responses())
        joined = " ".join(data["why_hersignal_paragraphs"]).lower()
        self.assertTrue(
            any(word in joined for word in HEDGING_WORDS),
            msg="Expected may/suggest/appears hedging in featured copy",
        )


if __name__ == "__main__":
    unittest.main()
