"""
SIP Insight Lab - Ingestion: Deduplication Module (Task 1.7)
=============================================================
Computes SHA-256 hashes of normalised text and checks the DB
for duplicates before any item is written.

Usage:
    from src.ingestion.dedup import Deduplicator
    dedup = Deduplicator(conn)
    if not dedup.is_duplicate(text):
        dedup.register(text)
"""

import hashlib
import sqlite3
import unicodedata
import re
import logging

logger = logging.getLogger(__name__)


def _normalise_for_hash(text: str) -> str:
    """
    Normalise text before hashing so near-identical items collapse.
    Steps: NFKC unicode normalise -> lowercase -> collapse whitespace.
    """
    text = unicodedata.normalize("NFKC", text)
    text = text.lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def compute_hash(text: str) -> str:
    """Return the SHA-256 hex digest of the normalised text."""
    normalised = _normalise_for_hash(text)
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


class Deduplicator:
    """
    Checks and tracks dedup hashes against the raw_item table.

    Args:
        conn: An open sqlite3.Connection to the project DB.
    """

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        self._seen_hashes: set[str] = self._load_existing_hashes()
        logger.info("Deduplicator initialised with %d existing hashes.", len(self._seen_hashes))

    def _load_existing_hashes(self) -> set[str]:
        """Pre-load all hashes already in the DB to avoid repeated queries."""
        cursor = self._conn.execute("SELECT dedup_hash FROM raw_item;")
        return {row[0] for row in cursor.fetchall()}

    def is_duplicate(self, text: str) -> bool:
        """Return True if this text (or a near-identical copy) already exists."""
        h = compute_hash(text)
        return h in self._seen_hashes

    def register(self, text: str) -> str:
        """
        Mark this text as seen (does NOT write to DB — that happens in the writer).
        Returns the hash so the caller can include it in the DB record.
        """
        h = compute_hash(text)
        self._seen_hashes.add(h)
        return h

    def stats(self) -> dict:
        return {"unique_hashes_tracked": len(self._seen_hashes)}
