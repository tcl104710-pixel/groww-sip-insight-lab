"""
SIP Insight Lab — Synthesis Scorers (Tasks 4.2, 4.3, 4.4)
=========================================================
Implements component scorers for Opportunity Ranking:
  - FrequencyScorer: Normalised count per root cause bucket [0, 1]
  - SeverityScorer: Weighted average sentiment magnitude per bucket [0, 1]
  - First6MoConcentrationScorer: % of bucket items occurring in first 6mo [0, 1]
"""

from typing import List, Optional
import logging

logger = logging.getLogger("synthesis.scorers")


class FrequencyScorer:
    """
    Task 4.2: Computes normalised frequency score for a root cause bucket.
    """

    def __init__(self, mode: str = "relative_to_max"):
        """
        :param mode: 'relative_to_max' (scales relative to highest count bucket, top = 1.0)
                     or 'corpus_ratio' (count / total_corpus)
        """
        self.mode = mode

    def score(
        self,
        bucket_count: int,
        total_corpus: int,
        max_bucket_count: Optional[int] = None,
    ) -> float:
        """
        Calculate normalised frequency score in [0.0, 1.0].
        """
        if total_corpus <= 0 or bucket_count <= 0:
            return 0.0

        if self.mode == "relative_to_max" and max_bucket_count and max_bucket_count > 0:
            val = bucket_count / max_bucket_count
        else:
            val = bucket_count / total_corpus

        return min(max(val, 0.0), 1.0)


class SeverityScorer:
    """
    Task 4.3: Computes severity score from sentiment magnitude.
    Formula: Average magnitude of sentiment scores per bucket, normalised [0, 1].
    """

    def __init__(self, penalize_negative: bool = True):
        self.penalize_negative = penalize_negative

    def score(self, sentiment_scores: List[float]) -> float:
        """
        Calculate severity score in [0.0, 1.0].
        If sentiment is negative, investors experienced frustration/churn friction.
        """
        if not sentiment_scores:
            return 0.0

        count = len(sentiment_scores)
        if self.penalize_negative:
            # Shift sentiment -1.0..1.0 to distress scale where -1.0 -> 1.0 distress, +1.0 -> 0.0
            # or use weighted abs(sentiment)
            distress_scores = [abs(s) if s < 0 else (s * 0.5) for s in sentiment_scores]
            avg_distress = sum(distress_scores) / count
            return min(max(avg_distress, 0.0), 1.0)
        else:
            # Pure abs magnitude
            avg_mag = sum(abs(s) for s in sentiment_scores) / count
            return min(max(avg_mag, 0.0), 1.0)


class First6MoConcentrationScorer:
    """
    Task 4.4: Computes % of bucket items with lifecycle_stage in first 6 months.
    Categories: LS-00 (pre-SIP), LS-01 (0–3mo), LS-02 (3–6mo).
    """

    def score(self, first_6mo_count: int, total_bucket_count: int) -> float:
        """
        Calculate concentration score in [0.0, 1.0].
        """
        if total_bucket_count <= 0 or first_6mo_count <= 0:
            return 0.0

        val = first_6mo_count / total_bucket_count
        return min(max(val, 0.0), 1.0)
