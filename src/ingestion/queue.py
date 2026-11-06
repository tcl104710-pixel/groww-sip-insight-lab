"""
SIP Insight Lab - Ingestion: Queue (Task 1.6)
==============================================
Rate-limited, retry-aware ingestion queue that receives RawItems
from all scrapers and routes them through dedup -> DB write.

Usage:
    queue = IngestionQueue(conn)
    queue.enqueue(item)           # single item
    queue.flush()                 # process all queued items
    print(queue.stats())
"""

import time
import logging
from collections import deque
from typing import Optional

from src.ingestion.dedup import Deduplicator
from src.ingestion.writer import RawItem, RawItemWriter

logger = logging.getLogger(__name__)


class IngestionQueue:
    """
    Buffers RawItems from scrapers, deduplicates, and writes to DB.

    Args:
        conn:             Open sqlite3 connection.
        batch_size:       Write to DB in batches of this size.
        inter_batch_delay: Seconds to sleep between batches (rate control).
        max_retries:      Number of write retries on transient errors.
    """

    def __init__(
        self,
        conn,
        batch_size: int = 50,
        inter_batch_delay: float = 0.0,
        max_retries: int = 3,
    ):
        self._conn = conn
        self._batch_size = batch_size
        self._delay = inter_batch_delay
        self._max_retries = max_retries
        self._queue: deque[RawItem] = deque()
        self._dedup = Deduplicator(conn)
        self._writer = RawItemWriter(conn)

        # Running totals
        self._total_enqueued = 0
        self._total_duplicate = 0
        self._total_written = 0
        self._total_errors = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enqueue(self, item: RawItem) -> bool:
        """
        Add an item to the queue after dedup check.

        Returns:
            True if enqueued (not a duplicate), False if duplicate.
        """
        self._total_enqueued += 1

        if self._dedup.is_duplicate(item.raw_text):
            self._total_duplicate += 1
            logger.debug("Duplicate skipped at enqueue: source=%s id=%s", item.source, item.source_id)
            return False

        # Register hash immediately so parallel scrapers don't double-enqueue
        item.dedup_hash = self._dedup.register(item.raw_text)
        self._queue.append(item)

        # Auto-flush when batch is full
        if len(self._queue) >= self._batch_size:
            self._flush_batch()

        return True

    def enqueue_many(self, items: list[RawItem]) -> dict:
        """Enqueue a list of items and return per-call stats."""
        enqueued = 0
        duplicates = 0
        for item in items:
            if self.enqueue(item):
                enqueued += 1
            else:
                duplicates += 1
        return {"enqueued": enqueued, "duplicates": duplicates}

    def flush(self) -> dict:
        """Process all remaining items in the queue."""
        while self._queue:
            self._flush_batch()
        return self.stats()

    def stats(self) -> dict:
        return {
            "total_enqueued":   self._total_enqueued,
            "total_duplicate":  self._total_duplicate,
            "total_written":    self._total_written,
            "total_errors":     self._total_errors,
            "queue_depth":      len(self._queue),
            "duplicate_rate":   (
                round(self._total_duplicate / self._total_enqueued, 3)
                if self._total_enqueued else 0.0
            ),
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _flush_batch(self) -> None:
        batch: list[RawItem] = []
        while self._queue and len(batch) < self._batch_size:
            batch.append(self._queue.popleft())

        for attempt in range(1, self._max_retries + 1):
            try:
                result = self._writer.write_batch(batch)
                self._total_written += result["written"]
                logger.debug(
                    "Batch flushed: %d written, %d skipped (attempt %d).",
                    result["written"], result["skipped"], attempt,
                )
                break
            except Exception as e:
                logger.warning("Batch write failed (attempt %d/%d): %s", attempt, self._max_retries, e)
                if attempt == self._max_retries:
                    self._total_errors += len(batch)
                    logger.error("Batch permanently failed after %d retries.", self._max_retries)
                else:
                    time.sleep(2 ** attempt)

        if self._delay > 0:
            time.sleep(self._delay)
