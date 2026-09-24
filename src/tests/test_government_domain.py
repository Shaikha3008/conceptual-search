"""Checks for the government-initiative setup (AI_ENTREP_DOMAIN=government)."""

import csv
import os
from pathlib import Path
import string
import sys
import unittest

os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import global_search_prompts
import government_prompts
import local_search_prompts
from agents_common import FidelityAuditor
from semantic_novelty import COMPONENTS, component_texts

REPO = Path(__file__).resolve().parents[2]


def placeholders(template: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(template) if name}


class GovernmentDomainTests(unittest.TestCase):
    def test_government_prompts_keep_the_original_placeholders(self):
        for module in (local_search_prompts, global_search_prompts):
            for name in dir(government_prompts):
                original = getattr(module, name, None)
                replacement = getattr(government_prompts, name)
                if isinstance(original, str) and isinstance(replacement, str):
                    self.assertEqual(
                        placeholders(original), placeholders(replacement), name
                    )

    def test_government_guidance_covers_every_component(self):
        self.assertEqual(
            set(government_prompts.MUTATION_COMPONENT_GUIDANCE), set(COMPONENTS)
        )

    def test_default_prompts_are_unchanged_without_the_switch(self):
        if os.environ.get("AI_ENTREP_DOMAIN"):
            self.skipTest("AI_ENTREP_DOMAIN is set in this environment")
        self.assertIn("crowdfunding", local_search_prompts.EVALUATOR_PROMPT)

    def test_idea_file_and_list_match_and_parse_into_six_components(self):
        with open(REPO / "in" / "gov-ideas.csv", newline="", encoding="utf-8") as f:
            ideas = {row["id"]: row["description"] for row in csv.DictReader(f)}
        with open(REPO / "in" / "gov-firm-set-15.txt", encoding="utf-8") as f:
            listed = [line.split("#", 1)[0].strip() for line in f]
        listed = [idea_id for idea_id in listed if idea_id]
        self.assertEqual(len(listed), 15)
        self.assertEqual(listed[0], "proactive-benefits")  # GOV_SEED in the Makefile
        self.assertEqual(set(listed), set(ideas))
        for idea_id, text in ideas.items():
            projected = component_texts(text)
            missing = [c for c in COMPONENTS if projected[c] == "Not specified."]
            self.assertEqual(missing, [], idea_id)

    def test_initiative_wording_is_read_as_prospective_or_existing(self):
        planned = "The initiative plans to pilot the service in two districts."
        claimed = "The initiative has served 5,000 families."
        self.assertTrue(FidelityAuditor._is_clearly_prospective_claim(planned, planned))
        self.assertFalse(FidelityAuditor._is_clearly_prospective_claim(claimed, claimed))


if __name__ == "__main__":
    unittest.main()
