"""
SIP Insight Lab — Human Review Queue Router (Task 2.13)
=======================================================
Routes classified feedback items based on confidence score and domain rules:
  - Confidence >= 0.75 and no flags:
      -> Writes to labelled_item with review_status = 'auto'
  - Confidence < 0.75 or flagged:
      -> Writes to labelled_item with review_status = 'flagged'
      -> Enqueues in human_review_queue table (status = 'pending')

Usage:
    from src.classification.router import ClassificationRouter
    router = ClassificationRouter(conn)
    dest, record_id = router.route(item_id, parsed_data, evaluation)
"""

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple

from src.classification.confidence import ConfidenceEvaluation
from src.config import config

logger = logging.getLogger(__name__)


class ClassificationRouter:
    """
    Manages routing of classified items into Labelled Store or Human Review Queue.
    """

    def __init__(self, conn: sqlite3.Connection, taxonomy_version: str = "1.0"):
        self.conn = conn
        self.taxonomy_version = taxonomy_version

    def route(
        self,
        item_id: str,
        data: dict,
        evaluation: ConfidenceEvaluation,
    ) -> Tuple[str, str]:
        """
        Persist classification result and route according to confidence evaluation.

        Returns:
            Tuple of (destination, identifier)
            e.g. ("auto", item_id) or ("human_review", queue_id)
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        review_status = "auto" if evaluation.is_confident else "flagged"

        with self.conn:
            # 1. Upsert into labelled_item table
            self.conn.execute(
                """
                INSERT OR REPLACE INTO labelled_item (
                    item_id, taxonomy_version, lifecycle_stage, stated_intent,
                    actual_action, stop_type, root_cause, root_cause_sub,
                    trigger_moment, help_sources, retention_factor,
                    investor_segment, sentiment_score, confidence_score,
                    field_confidences, review_status, classified_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    self.taxonomy_version,
                    data.get("lifecycle_stage", "LS-99"),
                    data.get("stated_intent", "unknown"),
                    data.get("actual_action", "unknown"),
                    data.get("stop_type", "ST-99"),
                    data.get("root_cause", "RC-99"),
                    data.get("root_cause_sub"),
                    data.get("trigger_moment"),
                    json.dumps(data.get("help_sources", [])),
                    data.get("retention_factor"),
                    json.dumps(data.get("investor_segment", {})),
                    float(data.get("sentiment_score", 0.0)),
                    float(evaluation.aggregate_score),
                    json.dumps(evaluation.field_scores),
                    review_status,
                    now_iso,
                ),
            )

            # 2. If below threshold or flagged, push to human_review_queue
            if not evaluation.is_confident:
                queue_id = str(uuid.uuid4())
                reason = evaluation.routing_reason or "low_confidence"

                self.conn.execute(
                    """
                    INSERT OR REPLACE INTO human_review_queue (
                        queue_id, item_id, reason, confidence_score,
                        assigned_to, status, created_at
                    ) VALUES (?, ?, ?, ?, NULL, 'pending', ?)
                    """,
                    (
                        queue_id,
                        item_id,
                        reason,
                        evaluation.aggregate_score,
                        now_iso,
                    ),
                )
                logger.info(
                    "Routed item %s to Human Review Queue (queue_id=%s, reason=%s, conf=%.2f)",
                    item_id[:8],
                    queue_id[:8],
                    reason,
                    evaluation.aggregate_score,
                )
                return "human_review", queue_id

        return "auto", item_id

    def get_queue_backlog_count(self) -> int:
        """Return the number of pending items in the review queue."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM human_review_queue WHERE status = 'pending';")
        return cursor.fetchone()[0]

    def is_backlog_alert(self) -> bool:
        """Check if review backlog exceeds threshold defined in config.yaml."""
        count = self.get_queue_backlog_count()
        threshold = config.human_review.backlog_alert_threshold
        return count >= threshold
