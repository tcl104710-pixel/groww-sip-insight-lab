"""
SIP Insight Lab — Confidence Scorer (Task 2.12)
================================================
Evaluates per-field and aggregate classification confidence scores.
Applies domain weights to determine if an item is sufficiently confident
to be auto-accepted or needs human review routing.

Weights:
  - root_cause       : 0.35 (critical discovery metric)
  - stated_intent    : 0.20 (critical behavioral separation)
  - actual_action    : 0.20 (critical behavioral separation)
  - stop_type        : 0.15
  - lifecycle_stage  : 0.10

Usage:
    from src.classification.confidence import ConfidenceScorer
    scorer = ConfidenceScorer(threshold=0.75)
    decision = scorer.evaluate(parsed_item)
    # decision.is_confident -> True/False
    # decision.flags        -> ['low_root_cause_confidence']
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.config import config

logger = logging.getLogger(__name__)

DEFAULT_FIELD_WEIGHTS: Dict[str, float] = {
    "root_cause": 0.35,
    "stated_intent": 0.20,
    "actual_action": 0.20,
    "stop_type": 0.15,
    "lifecycle_stage": 0.10,
}


@dataclass
class ConfidenceEvaluation:
    is_confident: bool
    aggregate_score: float
    field_scores: Dict[str, float]
    flags: List[str] = field(default_factory=list)
    routing_reason: Optional[str] = None


class ConfidenceScorer:
    """
    Computes weighted aggregate confidence scores and flags low-confidence predictions.
    """

    def __init__(
        self,
        threshold: Optional[float] = None,
        field_weights: Optional[Dict[str, float]] = None,
        min_field_threshold: float = 0.50,
    ):
        self.threshold = threshold if threshold is not None else config.classification.confidence_threshold
        self.field_weights = field_weights or DEFAULT_FIELD_WEIGHTS
        self.min_field_threshold = min_field_threshold

    def calculate_aggregate_score(self, item: dict) -> float:
        """
        Compute weighted aggregate score from field_confidences.
        Falls back to item's confidence_score if field confidences are missing.
        """
        field_confs = item.get("field_confidences", {})
        if not field_confs:
            return float(item.get("confidence_score", 0.0))

        total_weight = 0.0
        weighted_sum = 0.0

        for field_name, weight in self.field_weights.items():
            if field_name in field_confs:
                score = max(0.0, min(1.0, float(field_confs[field_name])))
                weighted_sum += score * weight
                total_weight += weight

        if total_weight > 0:
            return round(weighted_sum / total_weight, 4)

        return float(item.get("confidence_score", 0.0))

    def evaluate(self, item: dict) -> ConfidenceEvaluation:
        """
        Evaluate full classification item against confidence criteria and domain rules.
        """
        field_scores = item.get("field_confidences", {})
        agg_score = self.calculate_aggregate_score(item)

        flags: List[str] = []
        routing_reason = None

        # Check for unclassifiable root cause
        if item.get("root_cause") == "RC-99":
            flags.append("unclassifiable_root_cause")
            routing_reason = "unclassifiable_root_cause"

        # Check per-field scores
        for field_name, score in field_scores.items():
            if score < self.min_field_threshold:
                flags.append(f"low_{field_name}_confidence_{score:.2f}")

        # Check aggregate against threshold
        if agg_score < self.threshold:
            flags.append(f"below_aggregate_threshold_{agg_score:.2f}_vs_{self.threshold:.2f}")
            if not routing_reason:
                routing_reason = "low_confidence"

        # Special domain heuristic: intent/action mismatch with medium confidence
        intent = item.get("stated_intent")
        action = item.get("actual_action")
        if intent == "continue" and action == "cancelled" and agg_score < 0.85:
            flags.append("intent_action_divergence")
            if not routing_reason:
                routing_reason = "flagged_by_rule"

        is_confident = (agg_score >= self.threshold) and ("unclassifiable_root_cause" not in flags)

        return ConfidenceEvaluation(
            is_confident=is_confident,
            aggregate_score=agg_score,
            field_scores=field_scores,
            flags=flags,
            routing_reason=routing_reason if not is_confident else None,
        )


if __name__ == "__main__":
    scorer = ConfidenceScorer(threshold=0.75)
    sample_item = {
        "root_cause": "RC-01",
        "stated_intent": "stop",
        "actual_action": "cancelled",
        "stop_type": "ST-01",
        "lifecycle_stage": "LS-01",
        "confidence_score": 0.85,
        "field_confidences": {
            "root_cause": 0.80,
            "stated_intent": 0.90,
            "actual_action": 0.90,
            "stop_type": 0.85,
            "lifecycle_stage": 0.80,
        },
    }
    res = scorer.evaluate(sample_item)
    print(f"Agg score: {res.aggregate_score}, Confident: {res.is_confident}, Flags: {res.flags}")
