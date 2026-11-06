"""
SIP Insight Lab - Ingestion: Raw Item DB Writer (Task 1.8)
===========================================================
Writes a validated RawItem to the raw_item table.
Called by the ingestion queue after dedup passes.

Usage:
    from src.ingestion.writer import RawItem, RawItemWriter
    writer = RawItemWriter(conn)
    writer.write(raw_item)
"""

import json
import sqlite3
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

VALID_SOURCES = {"play_store", "app_store", "reddit", "tradingqa", "youtube"}


@dataclass
class RawItem:
    """
    Represents a single raw feedback item as collected from a source.
    Matches the raw_item table schema exactly.
    """
    source: str                        # play_store | app_store | reddit | tradingqa | youtube
    source_id: str                     # Platform-native ID
    raw_text: str                      # Original, unmodified text
    raw_url: str                       # Direct link to the original item
    dedup_hash: str                    # SHA-256 of normalised text (computed by Deduplicator)
    collected_at: str = field(         # ISO-8601 UTC timestamp
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    item_id: str = field(              # UUID v4 (auto-generated)
        default_factory=lambda: str(uuid.uuid4())
    )
    star_rating: Optional[int] = None  # 1-5 where applicable
    metadata: Optional[dict] = None    # Source-specific extras (vote count, etc.)

    def __post_init__(self):
        if self.source not in VALID_SOURCES:
            raise ValueError(f"Invalid source '{self.source}'. Must be one of: {VALID_SOURCES}")
        if not self.raw_text or not self.raw_text.strip():
            raise ValueError("raw_text must not be empty.")
        # dedup_hash starts as "" and is filled by Deduplicator.register() at enqueue time


class RawItemWriter:
    """
    Writes RawItem objects to the raw_item table.

    Args:
        conn: An open sqlite3.Connection to the project DB.
    """

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def write(self, item: RawItem) -> bool:
        """
        Insert one RawItem into the DB.

        Returns:
            True on success, False if the item already exists (dedup_hash collision).
        """
        try:
            metadata_json = json.dumps(item.metadata) if item.metadata else None
            self._conn.execute(
                """
                INSERT INTO raw_item
                    (item_id, source, source_id, raw_text, raw_url,
                     star_rating, collected_at, dedup_hash, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.item_id,
                    item.source,
                    item.source_id,
                    item.raw_text,
                    item.raw_url,
                    item.star_rating,
                    item.collected_at,
                    item.dedup_hash,
                    metadata_json,
                ),
            )
            self._conn.commit()
            return True
        except sqlite3.IntegrityError:
            logger.debug("Duplicate skipped (dedup_hash collision): %s", item.dedup_hash[:12])
            return False
        except Exception as e:
            logger.error("Failed to write raw item %s: %s", item.item_id, e)
            raise

    def write_batch(self, items: list[RawItem]) -> dict:
        """
        Insert a list of RawItems; returns counts of written and skipped.
        """
        written = 0
        skipped = 0
        for item in items:
            if self.write(item):
                written += 1
            else:
                skipped += 1
        logger.info("Batch write complete: %d written, %d skipped.", written, skipped)
        return {"written": written, "skipped": skipped}

    def count(self, source: Optional[str] = None) -> int:
        """Return the row count for a source (or all sources)."""
        if source:
            cursor = self._conn.execute(
                "SELECT COUNT(*) FROM raw_item WHERE source = ?;", (source,)
            )
        else:
            cursor = self._conn.execute("SELECT COUNT(*) FROM raw_item;")
        return cursor.fetchone()[0]
