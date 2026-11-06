"""
SIP Insight Lab — Prompt Builder (Task 2.9)
===========================================
Constructs structured LLM prompts by injecting:
  - Research Taxonomy definitions (via TaxonomyLoader)
  - Curated few-shot examples
  - Target feedback item metadata (source, star_rating, cleaned_text)

Supports versioned templates:
  - v1: src/prompts/classify_v1.txt (Base prompt)
  - v2: src/prompts/classify_v2.txt (Iterated prompt with disambiguation rules)

Usage:
    from src.classification.prompt_builder import PromptBuilder
    pb = PromptBuilder(version="v1")
    prompt = pb.build_prompt("Groww cancelled my SIP after mandate failed", source="reddit")
"""

import json
import logging
from pathlib import Path
from typing import Optional

from src.taxonomy_loader import TaxonomyLoader

logger = logging.getLogger(__name__)

DEFAULT_TEMPLATE_DIR = Path(__file__).parent.parent / "prompts"


# High-quality few-shot examples adhering to the taxonomy schema
FEW_SHOT_EXAMPLES = [
    {
        "source": "play_store",
        "star_rating": 1,
        "text": "My SIP got auto cancelled because of 3 failed debits due to bank technical issue. Why doesn't Groww retry or give alert?",
        "annotation": {
            "lifecycle_stage": "LS-01",
            "stated_intent": "unknown",
            "actual_action": "cancelled",
            "stop_type": "ST-01",
            "root_cause": "RC-01",
            "root_cause_sub": "Auto-cancellation after 3 misses",
            "trigger_moment": "3 failed debits due to bank technical issue",
            "help_sources": ["none_mentioned"],
            "retention_factor": None,
            "investor_segment": {
                "age_group": "unknown",
                "income_stability": "unknown",
                "money_source": "unknown",
                "influencer_type": "unknown",
            },
            "sentiment_score": -0.85,
            "confidence_score": 0.95,
            "field_confidences": {
                "lifecycle_stage": 0.85,
                "stated_intent": 0.80,
                "actual_action": 0.95,
                "stop_type": 0.98,
                "root_cause": 0.96,
            },
        },
    },
    {
        "source": "reddit",
        "star_rating": None,
        "text": "Investing in Parag Parikh Flexi Cap for 8 months now. Markets are down but I know rupee cost averaging works. Continuing my SIP every month on salary day.",
        "annotation": {
            "lifecycle_stage": "LS-03",
            "stated_intent": "continue",
            "actual_action": "active",
            "stop_type": "ST-03",
            "root_cause": "RC-99",
            "root_cause_sub": None,
            "trigger_moment": "Market downturn",
            "help_sources": ["reddit"],
            "retention_factor": "RF-07",
            "investor_segment": {
                "age_group": "25-30",
                "income_stability": "salaried_stable",
                "money_source": "salary_emi",
                "influencer_type": "self_research",
            },
            "sentiment_score": 0.75,
            "confidence_score": 0.92,
            "field_confidences": {
                "lifecycle_stage": 0.95,
                "stated_intent": 0.98,
                "actual_action": 0.98,
                "stop_type": 0.98,
                "root_cause": 0.85,
            },
        },
    },
    {
        "source": "tradingqa",
        "star_rating": None,
        "text": "I lost my job last month so stopped my monthly 10k SIP. Will restart once I find a new role.",
        "annotation": {
            "lifecycle_stage": "LS-99",
            "stated_intent": "continue",
            "actual_action": "cancelled",
            "stop_type": "ST-02",
            "root_cause": "RC-04",
            "root_cause_sub": "Job loss",
            "trigger_moment": "Job loss last month",
            "help_sources": ["tradingqa"],
            "retention_factor": None,
            "investor_segment": {
                "age_group": "unknown",
                "income_stability": "salaried_variable",
                "money_source": "own_savings",
                "influencer_type": "unknown",
            },
            "sentiment_score": -0.40,
            "confidence_score": 0.90,
            "field_confidences": {
                "lifecycle_stage": 0.70,
                "stated_intent": 0.90,
                "actual_action": 0.95,
                "stop_type": 0.95,
                "root_cause": 0.95,
            },
        },
    },
]


class PromptBuilder:
    """
    Builds the complete prompt sent to the LLM for feedback classification.
    """

    def __init__(
        self,
        version: str = "v1",
        taxonomy_loader: Optional[TaxonomyLoader] = None,
        template_dir: Path = DEFAULT_TEMPLATE_DIR,
        few_shot_count: int = 3,
    ):
        self.version = version
        self.template_dir = template_dir
        self.few_shot_count = few_shot_count
        self.taxonomy_loader = taxonomy_loader or TaxonomyLoader()
        self._template: str = self._load_template(version)

    def _load_template(self, version: str) -> str:
        filename = f"classify_{version}.txt"
        path = self.template_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Prompt template not found: {path}")
        return path.read_text(encoding="utf-8")

    def set_version(self, version: str) -> None:
        """Switch template version (e.g. 'v1' or 'v2')."""
        self._template = self._load_template(version)
        self.version = version

    def format_few_shots(self, count: Optional[int] = None) -> str:
        """Format few-shot examples as readable text blocks."""
        k = count or self.few_shot_count
        examples = FEW_SHOT_EXAMPLES[:k]
        blocks = []
        for idx, ex in enumerate(examples, 1):
            rating_str = f"{ex['star_rating']} stars" if ex['star_rating'] else "N/A"
            blocks.append(
                f"### Example {idx}:\n"
                f"Source: {ex['source']} (Rating: {rating_str})\n"
                f'Text: "{ex["text"]}"\n'
                f"Classification Output:\n"
                f"{json.dumps(ex['annotation'], indent=2)}"
            )
        return "\n\n".join(blocks)

    def build_prompt(
        self,
        cleaned_text: str,
        source: str = "play_store",
        star_rating: Optional[int] = None,
    ) -> str:
        """
        Assemble the full prompt for a given feedback item.
        """
        rating_str = str(star_rating) if star_rating is not None else "None"
        taxonomy_context = self.taxonomy_loader.as_prompt_context()
        few_shots = self.format_few_shots()

        prompt = (
            self._template
            .replace("{taxonomy_context}", taxonomy_context)
            .replace("{few_shot_examples}", few_shots)
            .replace("{source}", source)
            .replace("{star_rating}", rating_str)
            .replace("{cleaned_text}", cleaned_text)
        )
        return prompt


if __name__ == "__main__":
    pb = PromptBuilder(version="v1")
    sample_prompt = pb.build_prompt("Groww rejected my mandate 3 times!", source="play_store", star_rating=1)
    print("=== Sample Generated Prompt (first 600 chars) ===")
    print(sample_prompt[:600])
    print(f"\nTotal prompt length: {len(sample_prompt)} chars")
