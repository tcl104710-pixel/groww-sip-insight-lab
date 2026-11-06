"""
SIP Insight Lab — AI Evidence Log (Task 3.7)
=============================================
Manages an immutable, append-only audit trail of all human-in-the-loop
interactions (approvals, corrections, and rejections) with AI classification outputs.

Dual-persistence:
  1. Relational: ai_evidence_log table in SQLite DB
  2. Append-only JSONL file: outputs/logs/ai_evidence_log.jsonl

Schema:
  - log_id       : UUID v4
  - item_id      : Reference to labelled_item.item_id
  - timestamp    : ISO-8601 UTC
  - event_type   : 'correction' | 'rejection' | 'approval'
  - ai_output    : Dict of AI prediction & confidence
  - human_output : Dict of human-corrected fields (or None for approval)
  - reviewer_id  : Anonymised reviewer ID
  - reason_note  : Free-text rationale

Usage:
    from src.qa.evidence_log import EvidenceLogWriter
    logger = EvidenceLogWriter(conn)
    logger.log_correction(
        item_id="...",
        ai_output={"root_cause": "RC-02", "confidence": 0.61},
        human_output={"root_cause": "RC-01"},
        reviewer_id="reviewer_01",
        reason_note="Debit failure is involuntary",
    )
"""

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_LOG_FILE = Path(__file__).parent.parent.parent / "outputs" / "logs" / "ai_evidence_log.jsonl"


class EvidenceLogWriter:
    """
    Append-only AI Evidence Log writer and analyzer.
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        log_file_path: Path = DEFAULT_LOG_FILE,
    ):
        self.conn = conn
        self.log_file_path = Path(log_file_path)
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)

    def log_entry(
        self,
        item_id: str,
        event_type: str,
        ai_output: Dict[str, Any],
        human_output: Optional[Dict[str, Any]] = None,
        reviewer_id: str = "reviewer_anon",
        reason_note: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Record an immutable log entry in SQLite DB and append to JSONL log file.
        """
        valid_events = {"correction", "rejection", "approval"}
        if event_type not in valid_events:
            raise ValueError(f"Invalid event_type '{event_type}'. Must be one of {valid_events}")

        log_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()

        entry = {
            "log_id": log_id,
            "item_id": item_id,
            "timestamp": now_iso,
            "event_type": event_type,
            "ai_output": ai_output,
            "human_output": human_output,
            "reviewer_id": reviewer_id,
            "reason_note": reason_note,
        }

        # 1. Write to SQLite
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO ai_evidence_log (
                    log_id, item_id, timestamp, event_type,
                    ai_output, human_output, reviewer_id, reason_note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    log_id,
                    item_id,
                    now_iso,
                    event_type,
                    json.dumps(ai_output),
                    json.dumps(human_output) if human_output is not None else None,
                    reviewer_id,
                    reason_note,
                ),
            )

        # 2. Append to JSONL file
        with open(self.log_file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        logger.info(
            "Logged %s event for item %s by %s (log_id=%s)",
            event_type,
            item_id[:8],
            reviewer_id,
            log_id[:8],
        )
        return entry

    def log_approval(
        self,
        item_id: str,
        ai_output: Dict[str, Any],
        reviewer_id: str = "reviewer_anon",
        reason_note: Optional[str] = "AI classification validated by human reviewer",
    ) -> Dict[str, Any]:
        """Log human approval of AI output."""
        return self.log_entry(
            item_id=item_id,
            event_type="approval",
            ai_output=ai_output,
            human_output=None,
            reviewer_id=reviewer_id,
            reason_note=reason_note,
        )

    def log_correction(
        self,
        item_id: str,
        ai_output: Dict[str, Any],
        human_output: Dict[str, Any],
        reviewer_id: str = "reviewer_anon",
        reason_note: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Log human correction of AI output."""
        return self.log_entry(
            item_id=item_id,
            event_type="correction",
            ai_output=ai_output,
            human_output=human_output,
            reviewer_id=reviewer_id,
            reason_note=reason_note,
        )

    def log_rejection(
        self,
        item_id: str,
        ai_output: Dict[str, Any],
        reviewer_id: str = "reviewer_anon",
        reason_note: Optional[str] = "Output rejected as spam or incomprehensible",
    ) -> Dict[str, Any]:
        """Log human rejection of AI output."""
        return self.log_entry(
            item_id=item_id,
            event_type="rejection",
            ai_output=ai_output,
            human_output=None,
            reviewer_id=reviewer_id,
            reason_note=reason_note,
        )

    def get_entries(
        self,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query entries from SQLite table."""
        cursor = self.conn.cursor()
        query = "SELECT log_id, item_id, timestamp, event_type, ai_output, human_output, reviewer_id, reason_note FROM ai_evidence_log"
        params = []
        if event_type:
            query += " WHERE event_type = ?"
            params.append(event_type)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        rows = cursor.execute(query, params).fetchall()
        return [
            {
                "log_id": r[0],
                "item_id": r[1],
                "timestamp": r[2],
                "event_type": r[3],
                "ai_output": json.loads(r[4]) if r[4] else {},
                "human_output": json.loads(r[5]) if r[5] else None,
                "reviewer_id": r[6],
                "reason_note": r[7],
            }
            for r in rows
        ]

    def count_by_event(self) -> Dict[str, int]:
        """Return counts of each event_type."""
        cursor = self.conn.cursor()
        rows = cursor.execute(
            "SELECT event_type, COUNT(*) FROM ai_evidence_log GROUP BY event_type"
        ).fetchall()
        return dict(rows)

    def get_metrics(self) -> Dict[str, Any]:
        """
        Calculate key operational metrics from the AI Evidence Log.
        - Human Override Rate: corrections / total_reviews
        - Total reviews
        """
        counts = self.count_by_event()
        corrections = counts.get("correction", 0)
        approvals = counts.get("approval", 0)
        rejections = counts.get("rejection", 0)
        total = corrections + approvals + rejections

        override_rate = (corrections / total) if total > 0 else 0.0

        return {
            "total_log_entries": total,
            "approvals": approvals,
            "corrections": corrections,
            "rejections": rejections,
            "human_override_rate": round(override_rate, 4),
        }
