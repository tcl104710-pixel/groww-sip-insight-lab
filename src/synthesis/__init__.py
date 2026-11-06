"""
SIP Insight Lab — Synthesis & Hypothesis Engine Package (Phase 4)
=================================================================
"""

from src.synthesis.aggregator import (
    FeedbackAggregator,
    BucketStatistics,
    LabelledItemData,
)
from src.synthesis.scorers import (
    FrequencyScorer,
    SeverityScorer,
    First6MoConcentrationScorer,
)
from src.synthesis.addressability import (
    AddressabilityChecker,
    AddressabilityResult,
)
from src.synthesis.ranker import (
    OpportunityRanker,
    RankedOpportunity,
)
from src.synthesis.nudge_checker import (
    NudgeChecker,
    NudgeCheckResult,
)
from src.synthesis.interview_guide import (
    InterviewGuideGenerator,
)
from src.synthesis.card_generator import (
    HypothesisCardGenerator,
    HypothesisCard,
)

__all__ = [
    "FeedbackAggregator",
    "BucketStatistics",
    "LabelledItemData",
    "FrequencyScorer",
    "SeverityScorer",
    "First6MoConcentrationScorer",
    "AddressabilityChecker",
    "AddressabilityResult",
    "OpportunityRanker",
    "RankedOpportunity",
    "NudgeChecker",
    "NudgeCheckResult",
    "InterviewGuideGenerator",
    "HypothesisCardGenerator",
    "HypothesisCard",
]
