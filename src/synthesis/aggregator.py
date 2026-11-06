"""
SIP Insight Lab — Feedback Aggregator Module (Task 4.1)
======================================================
Groups labelled feedback items by root_cause, lifecycle_stage,
investor_segment, and stop_type to compute cohort statistics,
sentiment distributions, and early-churn concentrations.
"""

import json
import sqlite3
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger("synthesis.aggregator")


@dataclass
class LabelledItemData:
    item_id: str
    root_cause: str
    lifecycle_stage: str
    stated_intent: str
    actual_action: str
    stop_type: str
    sentiment_score: float
    confidence_score: float
    trigger_moment: Optional[str]
    help_sources: List[str]
    retention_factor: Optional[str]
    investor_segment: Dict[str, Any]
    cleaned_text: str
    source: str
    source_id: Optional[str]


@dataclass
class BucketStatistics:
    root_cause: str
    count: int
    percentage_of_corpus: float
    sentiment_scores: List[float] = field(default_factory=list)
    mean_sentiment: float = 0.0
    mean_sentiment_magnitude: float = 0.0
    stage_counts: Dict[str, int] = field(default_factory=dict)
    first_6mo_count: int = 0
    first_6mo_ratio: float = 0.0
    most_affected_stage: str = "LS-01"
    stop_type_counts: Dict[str, int] = field(default_factory=dict)
    source_counts: Dict[str, int] = field(default_factory=dict)
    segment_breakdown: Dict[str, Dict[str, int]] = field(default_factory=dict)
    sample_items: List[LabelledItemData] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root_cause": self.root_cause,
            "count": self.count,
            "percentage_of_corpus": round(self.percentage_of_corpus, 4),
            "mean_sentiment": round(self.mean_sentiment, 4),
            "mean_sentiment_magnitude": round(self.mean_sentiment_magnitude, 4),
            "stage_counts": self.stage_counts,
            "first_6mo_count": self.first_6mo_count,
            "first_6mo_ratio": round(self.first_6mo_ratio, 4),
            "most_affected_stage": self.most_affected_stage,
            "stop_type_counts": self.stop_type_counts,
            "source_counts": self.source_counts,
            "segment_breakdown": self.segment_breakdown,
            "sample_count": len(self.sample_items),
        }


class FeedbackAggregator:
    """
    Loads classified items from SQLite database and computes multi-dimensional aggregations.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def load_items(self, include_golden_set: bool = False) -> List[LabelledItemData]:
        """
        Query all labelled items joined with cleaned_item and raw_item.
        """
        query = """
            SELECT 
                l.item_id,
                l.root_cause,
                l.lifecycle_stage,
                l.stated_intent,
                l.actual_action,
                l.stop_type,
                l.sentiment_score,
                l.confidence_score,
                l.trigger_moment,
                l.help_sources,
                l.retention_factor,
                l.investor_segment,
                c.cleaned_text,
                r.source,
                r.source_id
            FROM labelled_item l
            JOIN cleaned_item c ON l.item_id = c.item_id
            JOIN raw_item r ON l.item_id = r.item_id
        """
        if not include_golden_set:
            query += " WHERE r.source != 'golden_set'"

        cursor = self.conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()

        items = []
        for r in rows:
            help_sources = []
            if r[9]:
                try:
                    help_sources = json.loads(r[9]) if isinstance(r[9], str) else r[9]
                except Exception:
                    help_sources = [r[9]]

            investor_segment = {}
            if r[11]:
                try:
                    investor_segment = json.loads(r[11]) if isinstance(r[11], str) else r[11]
                except Exception:
                    investor_segment = {}

            item = LabelledItemData(
                item_id=r[0],
                root_cause=r[1] or "RC-99",
                lifecycle_stage=r[2] or "LS-99",
                stated_intent=r[3] or "unknown",
                actual_action=r[4] or "unknown",
                stop_type=r[5] or "ST-99",
                sentiment_score=float(r[6]) if r[6] is not None else 0.0,
                confidence_score=float(r[7]) if r[7] is not None else 0.0,
                trigger_moment=r[8],
                help_sources=help_sources,
                retention_factor=r[10],
                investor_segment=investor_segment,
                cleaned_text=r[12] or "",
                source=r[13] or "unknown",
                source_id=r[14],
            )
            items.append(item)

        logger.info("Loaded %d labelled items for aggregation", len(items))
        return items

    def aggregate_by_root_cause(
        self, items: Optional[List[LabelledItemData]] = None
    ) -> Dict[str, BucketStatistics]:
        """
        Groups items by root_cause and calculates metrics for each bucket.
        """
        if items is None:
            items = self.load_items()

        total_corpus = len(items)
        if total_corpus == 0:
            return {}

        buckets: Dict[str, List[LabelledItemData]] = {}
        for it in items:
            rc = it.root_cause
            if rc not in buckets:
                buckets[rc] = []
            buckets[rc].append(it)

        stats: Dict[str, BucketStatistics] = {}
        for rc, bucket_items in buckets.items():
            count = len(bucket_items)
            pct = (count / total_corpus) * 100.0

            sentiments = [it.sentiment_score for it in bucket_items]
            mean_sent = sum(sentiments) / count if count > 0 else 0.0
            mean_sent_mag = sum(abs(s) for s in sentiments) / count if count > 0 else 0.0

            stage_counts: Dict[str, int] = {}
            stop_type_counts: Dict[str, int] = {}
            source_counts: Dict[str, int] = {}
            segment_breakdown: Dict[str, Dict[str, int]] = {
                "age_group": {},
                "income_stability": {},
                "money_source": {},
                "influencer_type": {},
            }

            first_6mo_count = 0
            for it in bucket_items:
                # Stage
                stage = it.lifecycle_stage
                stage_counts[stage] = stage_counts.get(stage, 0) + 1
                # First 6mo: LS-00 (pre-SIP), LS-01 (0-3mo), LS-02 (3-6mo)
                if stage in ("LS-00", "LS-01", "LS-02"):
                    first_6mo_count += 1

                # Stop type
                st = it.stop_type
                stop_type_counts[st] = stop_type_counts.get(st, 0) + 1

                # Source
                src = it.source
                source_counts[src] = source_counts.get(src, 0) + 1

                # Segments
                seg = it.investor_segment
                if isinstance(seg, dict):
                    for dim in ["age_group", "income_stability", "money_source", "influencer_type"]:
                        val = seg.get(dim)
                        if val:
                            segment_breakdown[dim][val] = segment_breakdown[dim].get(val, 0) + 1

            first_6mo_ratio = first_6mo_count / count if count > 0 else 0.0

            # Determine most affected stage (excluding LS-99 unknown if other stages present)
            valid_stages = {s: c for s, c in stage_counts.items() if s != "LS-99"}
            if valid_stages:
                most_affected = max(valid_stages.items(), key=lambda x: x[1])[0]
            else:
                most_affected = max(stage_counts.items(), key=lambda x: x[1])[0] if stage_counts else "LS-01"

            # Representative sample items sorted by length / confidence
            samples = sorted(
                bucket_items,
                key=lambda x: (x.confidence_score, len(x.cleaned_text)),
                reverse=True,
            )[:10]

            stats[rc] = BucketStatistics(
                root_cause=rc,
                count=count,
                percentage_of_corpus=pct,
                sentiment_scores=sentiments,
                mean_sentiment=mean_sent,
                mean_sentiment_magnitude=mean_sent_mag,
                stage_counts=stage_counts,
                first_6mo_count=first_6mo_count,
                first_6mo_ratio=first_6mo_ratio,
                most_affected_stage=most_affected,
                stop_type_counts=stop_type_counts,
                source_counts=source_counts,
                segment_breakdown=segment_breakdown,
                sample_items=samples,
            )

        return stats

    def compute_intent_action_gap(
        self, items: Optional[List[LabelledItemData]] = None
    ) -> Dict[str, Any]:
        """
        Computes the Intent vs. Action Gap analysis matrix.
        Crucial insight requested by Groww Problem Statement:
        separating what investors state vs. what they actually do.
        """
        if items is None:
            items = self.load_items()

        matrix: Dict[str, Dict[str, int]] = {}
        discrepancy_count = 0
        total = len(items)

        for it in items:
            intent = it.stated_intent or "unknown"
            action = it.actual_action or "unknown"

            if intent not in matrix:
                matrix[intent] = {}
            matrix[intent][action] = matrix[intent].get(action, 0) + 1

            # Check gap (e.g., stated 'continue' but action is 'cancelled')
            if intent in ("continue", "pause") and action == "cancelled":
                discrepancy_count += 1

        gap_rate = (discrepancy_count / total) if total > 0 else 0.0

        return {
            "matrix": matrix,
            "discrepancy_count": discrepancy_count,
            "total_items": total,
            "involuntary_gap_rate": round(gap_rate, 4),
        }
