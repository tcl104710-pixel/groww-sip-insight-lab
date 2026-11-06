"""
SIP Insight Lab - Cleaning: Pipeline Orchestrator (Task 2.6)
=============================================================
Runs the full cleaning pipeline on all raw_item records and
writes results to the cleaned_item table.

Pipeline order:
  raw_item -> Language detect -> PII scrub -> Noise remove -> Normalise -> cleaned_item

Usage:
    python scripts/run_cleaning.py
    # or import:
    from src.cleaning.pipeline import CleaningPipeline
    pipeline = CleaningPipeline(conn)
    stats = pipeline.run()
"""

import json
import logging
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from src.cleaning.lang_detect import LanguageDetector
from src.cleaning.noise_removal import NoiseRemover
from src.cleaning.normaliser import TextNormaliser
from src.cleaning.pii_scrubber import PIIScrubber

logger = logging.getLogger(__name__)

CLEANING_VERSION = "1.0"


@dataclass
class CleanedItem:
    item_id: str
    cleaned_text: str
    language: str
    pii_removal_log: dict
    cleaning_version: str
    cleaned_at: str


class CleaningPipeline:
    """
    Orchestrates the full cleaning pipeline over all raw_item records.

    Args:
        conn:        Open sqlite3.Connection to the project DB.
        use_ner:     Whether to use spaCy NER for PII scrubbing (default True).
        batch_size:  Number of items to process per DB commit batch.
        reprocess:   If True, re-clean items already in cleaned_item (default False).
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        use_ner: bool = True,
        batch_size: int = 100,
        reprocess: bool = False,
    ):
        self._conn = conn
        self._batch_size = batch_size
        self._reprocess = reprocess

        self._lang_detector = LanguageDetector()
        self._pii_scrubber  = PIIScrubber(use_ner=use_ner)
        self._noise_remover = NoiseRemover()
        self._normaliser    = TextNormaliser()

        logger.info(
            "CleaningPipeline ready (NER=%s, batch=%d, reprocess=%s).",
            use_ner, batch_size, reprocess,
        )

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def run(self) -> dict:
        """
        Process all unprocessed raw_item records through the cleaning pipeline.

        Returns:
            Stats dict with counts for each pipeline stage.
        """
        stats = {
            "total_raw": 0,
            "already_cleaned": 0,
            "lang_rejected": 0,
            "too_short_after_clean": 0,
            "cleaned_and_written": 0,
            "pii_total_redacted": 0,
            "errors": 0,
        }

        raw_items = self._fetch_unprocessed()
        stats["total_raw"] = len(raw_items)
        logger.info("CleaningPipeline: %d raw items to process.", len(raw_items))

        batch: list[CleanedItem] = []

        for raw in raw_items:
            item_id, source, raw_text = raw

            try:
                result = self._clean_one(item_id, raw_text)
            except Exception as e:
                logger.error("Error cleaning item %s: %s", item_id, e)
                stats["errors"] += 1
                continue

            if result is None:
                stats["lang_rejected"] += 1
                continue

            if not result.cleaned_text or len(result.cleaned_text) < 15:
                stats["too_short_after_clean"] += 1
                continue

            batch.append(result)
            stats["pii_total_redacted"] += result.pii_removal_log.get("total_redacted", 0)

            if len(batch) >= self._batch_size:
                written = self._write_batch(batch)
                stats["cleaned_and_written"] += written
                batch = []

        # Flush remaining
        if batch:
            written = self._write_batch(batch)
            stats["cleaned_and_written"] += written

        logger.info(
            "CleaningPipeline done: %d cleaned, %d lang-rejected, %d too-short, %d errors.",
            stats["cleaned_and_written"],
            stats["lang_rejected"],
            stats["too_short_after_clean"],
            stats["errors"],
        )
        return stats

    def clean_one_raw(self, item_id: str, raw_text: str) -> Optional[CleanedItem]:
        """
        Clean a single raw text and return a CleanedItem (does not write to DB).
        Returns None if the item is rejected (wrong language, too short).
        """
        return self._clean_one(item_id, raw_text)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _fetch_unprocessed(self) -> list[tuple]:
        """Fetch raw_item records that haven't been cleaned yet."""
        if self._reprocess:
            rows = self._conn.execute(
                "SELECT item_id, source, raw_text FROM raw_item;"
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT r.item_id, r.source, r.raw_text
                FROM raw_item r
                LEFT JOIN cleaned_item c ON r.item_id = c.item_id
                WHERE c.item_id IS NULL;
                """
            ).fetchall()
        return rows

    def _clean_one(self, item_id: str, raw_text: str) -> Optional[CleanedItem]:
        """Run the full pipeline on one item. Returns None if rejected."""

        # Step 1: Language detection
        lang = self._lang_detector.detect(raw_text)
        if lang not in {"en", "hi"}:
            logger.debug("Rejected (lang=%s): %s...", lang, raw_text[:50])
            return None

        # Step 2: Noise removal (before PII scrub — cleaner input for NER)
        text = self._noise_remover.clean(raw_text)

        # Step 3: PII scrubbing
        text, pii_log = self._pii_scrubber.scrub(text)

        # Step 4: Text normalisation
        text = self._normaliser.normalise(text)

        return CleanedItem(
            item_id=item_id,
            cleaned_text=text,
            language=lang,
            pii_removal_log=pii_log,
            cleaning_version=CLEANING_VERSION,
            cleaned_at=datetime.now(timezone.utc).isoformat(),
        )

    def _write_batch(self, items: list[CleanedItem]) -> int:
        """Write a batch of CleanedItems to the cleaned_item table."""
        written = 0
        try:
            with self._conn:
                for item in items:
                    self._conn.execute(
                        """
                        INSERT OR IGNORE INTO cleaned_item
                            (item_id, cleaned_text, language, pii_removal_log,
                             cleaning_version, cleaned_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            item.item_id,
                            item.cleaned_text,
                            item.language,
                            json.dumps(item.pii_removal_log),
                            item.cleaning_version,
                            item.cleaned_at,
                        ),
                    )
                    written += 1
        except Exception as e:
            logger.error("Batch write to cleaned_item failed: %s", e)
        return written

    def spot_check(self, n: int = 50) -> list[dict]:
        """
        Task 2.7: Return a random sample of cleaned items for manual PII review.
        """
        rows = self._conn.execute(
            """
            SELECT c.item_id, c.cleaned_text, c.language, c.pii_removal_log,
                   r.source
            FROM cleaned_item c
            JOIN raw_item r ON c.item_id = r.item_id
            ORDER BY RANDOM()
            LIMIT ?;
            """,
            (n,),
        ).fetchall()

        return [
            {
                "item_id":         row[0],
                "cleaned_text":    row[1],
                "language":        row[2],
                "pii_removal_log": json.loads(row[3]) if row[3] else {},
                "source":          row[4],
            }
            for row in rows
        ]
