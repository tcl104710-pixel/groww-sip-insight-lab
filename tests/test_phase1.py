"""
SIP Insight Lab - Unit Tests: Phase 1 (Task 1.1–1.8)
======================================================
Tests for dedup, writer, queue, and all 5 scrapers.
Run: python -m pytest tests/test_phase1.py -v

No live API calls are made — scrapers are tested with mocked responses.
"""

import json
import sqlite3
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root on path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.db.schema import init_db
from src.ingestion.dedup import Deduplicator, compute_hash
from src.ingestion.writer import RawItem, RawItemWriter
from src.ingestion.queue import IngestionQueue


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def in_memory_db():
    """Provide an in-memory SQLite DB with the full schema for each test."""
    conn = init_db(":memory:")
    yield conn
    conn.close()


def make_item(source="reddit", text="Test SIP feedback text that is long enough", idx=0) -> RawItem:
    return RawItem(
        source=source,
        source_id=f"test_{idx}",
        raw_text=text,
        raw_url=f"https://example.com/{idx}",
        dedup_hash="placeholder",  # Will be replaced by Deduplicator
    )


# ---------------------------------------------------------------------------
# Task 1.7 — Deduplicator
# ---------------------------------------------------------------------------

class TestDeduplicator:

    def test_compute_hash_deterministic(self):
        h1 = compute_hash("Hello World")
        h2 = compute_hash("Hello World")
        assert h1 == h2

    def test_compute_hash_normalises_case(self):
        assert compute_hash("hello") == compute_hash("HELLO")

    def test_compute_hash_normalises_whitespace(self):
        assert compute_hash("a  b") == compute_hash("a b")

    def test_new_item_not_duplicate(self, in_memory_db):
        dedup = Deduplicator(in_memory_db)
        assert not dedup.is_duplicate("brand new unique text 12345")

    def test_register_makes_duplicate(self, in_memory_db):
        dedup = Deduplicator(in_memory_db)
        text = "SIP cancelled after 3 failed debits"
        dedup.register(text)
        assert dedup.is_duplicate(text)

    def test_loads_existing_hashes_from_db(self, in_memory_db):
        """Dedup should pick up hashes already written to DB."""
        writer = RawItemWriter(in_memory_db)
        item = make_item(text="Existing item already in DB")
        item.dedup_hash = compute_hash(item.raw_text)
        writer.write(item)

        dedup2 = Deduplicator(in_memory_db)
        assert dedup2.is_duplicate("Existing item already in DB")


# ---------------------------------------------------------------------------
# Task 1.8 — RawItemWriter
# ---------------------------------------------------------------------------

class TestRawItemWriter:

    def test_write_single_item(self, in_memory_db):
        writer = RawItemWriter(in_memory_db)
        item = make_item()
        item.dedup_hash = compute_hash(item.raw_text)
        result = writer.write(item)
        assert result is True
        assert writer.count() == 1

    def test_duplicate_write_returns_false(self, in_memory_db):
        writer = RawItemWriter(in_memory_db)
        item = make_item()
        item.dedup_hash = compute_hash(item.raw_text)
        writer.write(item)
        result = writer.write(item)  # Same hash — should fail gracefully
        assert result is False
        assert writer.count() == 1  # Still 1, not 2

    def test_count_by_source(self, in_memory_db):
        writer = RawItemWriter(in_memory_db)
        for i, src in enumerate(["reddit", "reddit", "youtube"]):
            item = make_item(source=src, text=f"unique text {i} xyz", idx=i)
            item.dedup_hash = compute_hash(item.raw_text)
            writer.write(item)
        assert writer.count("reddit") == 2
        assert writer.count("youtube") == 1
        assert writer.count() == 3

    def test_invalid_source_raises(self):
        with pytest.raises(ValueError, match="Invalid source"):
            RawItem(source="invalid_source", source_id="x", raw_text="text", raw_url="url", dedup_hash="abc")

    def test_empty_text_raises(self):
        with pytest.raises(ValueError, match="raw_text must not be empty"):
            RawItem(source="reddit", source_id="x", raw_text="   ", raw_url="url", dedup_hash="abc")

    def test_metadata_json(self, in_memory_db):
        writer = RawItemWriter(in_memory_db)
        item = make_item()
        item.dedup_hash = compute_hash(item.raw_text)
        item.metadata = {"score": 10, "subreddit": "Groww"}
        writer.write(item)
        row = in_memory_db.execute("SELECT metadata FROM raw_item;").fetchone()
        assert json.loads(row[0])["score"] == 10


# ---------------------------------------------------------------------------
# Task 1.6 — IngestionQueue
# ---------------------------------------------------------------------------

class TestIngestionQueue:

    def test_enqueue_and_flush(self, in_memory_db):
        q = IngestionQueue(in_memory_db, batch_size=10)
        for i in range(5):
            q.enqueue(make_item(text=f"unique item number {i} abcdefg", idx=i))
        stats = q.flush()
        assert stats["total_written"] == 5
        assert stats["total_duplicate"] == 0

    def test_duplicate_rejected_at_enqueue(self, in_memory_db):
        q = IngestionQueue(in_memory_db, batch_size=10)
        item1 = make_item(text="this is a duplicate text sample")
        item2 = make_item(text="this is a duplicate text sample")
        r1 = q.enqueue(item1)
        r2 = q.enqueue(item2)
        q.flush()
        assert r1 is True
        assert r2 is False
        assert q.stats()["total_duplicate"] == 1

    def test_auto_flush_on_batch_size(self, in_memory_db):
        q = IngestionQueue(in_memory_db, batch_size=3)
        for i in range(3):
            q.enqueue(make_item(text=f"auto flush item {i} xyzabc", idx=i))
        # Auto-flush should have fired at batch_size=3
        assert q._writer.count() == 3

    def test_stats_structure(self, in_memory_db):
        q = IngestionQueue(in_memory_db)
        stats = q.stats()
        assert "total_enqueued" in stats
        assert "duplicate_rate" in stats
        assert "queue_depth" in stats


# ---------------------------------------------------------------------------
# Task 1.1 — PlayStoreScraper (mocked)
# ---------------------------------------------------------------------------

class TestPlayStoreScraper:

    def test_yields_raw_items(self):
        from src.scrapers.play_store import PlayStoreScraper

        mock_review = {
            "reviewId": "r123",
            "content": "Groww SIP cancelled without any reason! Very frustrating.",
            "score": 1,
            "appVersion": "4.5.0",
            "at": None,
        }

        with patch("src.scrapers.play_store.reviews") as mock_reviews:
            # Simulate one page then no more
            mock_reviews.side_effect = [
                ([mock_review], None),
            ]
            scraper = PlayStoreScraper()
            items = list(scraper.scrape(count=1))

        assert len(items) == 1
        assert items[0].source == "play_store"
        assert items[0].star_rating == 1
        assert "SIP cancelled" in items[0].raw_text

    def test_empty_text_skipped(self):
        from src.scrapers.play_store import PlayStoreScraper

        mock_review = {"reviewId": "r999", "content": "", "score": 3, "at": None}
        with patch("src.scrapers.play_store.reviews") as mock_reviews:
            mock_reviews.side_effect = [([mock_review], None)]
            scraper = PlayStoreScraper()
            items = list(scraper.scrape(count=5))
        assert len(items) == 0


# ---------------------------------------------------------------------------
# Task 1.2 — AppStoreScraper (mocked)
# ---------------------------------------------------------------------------

class TestAppStoreScraper:

    def test_yields_raw_items(self):
        from src.scrapers.app_store import AppStoreScraper
        import xml.etree.ElementTree as ET

        ns_atom = "http://www.w3.org/2005/Atom"
        ns_im   = "http://itunes.apple.com/rss"

        root = ET.Element(f"{{{ns_atom}}}feed")
        entry = ET.SubElement(root, f"{{{ns_atom}}}entry")
        id_el = ET.SubElement(entry, f"{{{ns_atom}}}id")
        id_el.text = "review-001"
        content = ET.SubElement(entry, f"{{{ns_atom}}}content")
        content.text = "My SIP was auto-cancelled after 3 failed attempts."
        rating = ET.SubElement(entry, f"{{{ns_im}}}rating")
        rating.text = "2"
        updated = ET.SubElement(entry, f"{{{ns_atom}}}updated")
        updated.text = "2024-01-01T00:00:00Z"

        xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)

        mock_resp = MagicMock()
        mock_resp.content = xml_bytes
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()

        # Second call returns 404 to stop pagination
        mock_resp2 = MagicMock()
        mock_resp2.status_code = 200
        mock_resp2.content = ET.tostring(ET.Element(f"{{{ns_atom}}}feed"))
        mock_resp2.raise_for_status = MagicMock()

        with patch("requests.Session.get", side_effect=[mock_resp, mock_resp2]):
            scraper = AppStoreScraper()
            items = list(scraper.scrape(max_pages=2))

        assert len(items) >= 1
        assert items[0].source == "app_store"
        assert items[0].star_rating == 2


# ---------------------------------------------------------------------------
# Task 1.3 — RedditScraper (mocked)
# ---------------------------------------------------------------------------

class TestRedditScraper:

    def test_yields_posts_and_comments(self):
        from src.scrapers.reddit import RedditScraper

        mock_comment = MagicMock()
        mock_comment.id = "c001"
        mock_comment.body = "I stopped my SIP because the interface was confusing and payment kept failing."
        mock_comment.score = 15
        mock_comment.created_utc = 1700000000.0

        mock_post = MagicMock()
        mock_post.id = "p001"
        mock_post.selftext = "Has anyone else had their Groww SIP auto-cancelled after 3 missed debits?"
        mock_post.permalink = "/r/IndiaInvestments/comments/p001/test"
        mock_post.score = 50
        mock_post.created_utc = 1700000000.0
        # comments must support .replace_more() and slicing [:N]
        mock_post.comments.replace_more = MagicMock()
        mock_post.comments.__getitem__ = MagicMock(return_value=[mock_comment])
        # Make it iterable for the slice mock_post.comments[:N]
        type(mock_post.comments).__getitem__ = MagicMock(return_value=[mock_comment])

        mock_subreddit = MagicMock()
        mock_subreddit.search = MagicMock(return_value=[mock_post])

        mock_reddit_client = MagicMock()
        mock_reddit_client.subreddit = MagicMock(return_value=mock_subreddit)

        # Build scraper WITHOUT credentials, then inject the mock client
        scraper = RedditScraper(
            subreddits=["IndiaInvestments"],
            search_terms=["SIP"],
            posts_per_query=1,
            comments_per_post=1,
        )
        scraper._reddit = mock_reddit_client  # Inject directly

        items = list(scraper.scrape())
        assert len(items) >= 1
        assert any(i.source == "reddit" for i in items)
        assert any("SIP" in i.raw_text for i in items)



# ---------------------------------------------------------------------------
# Task 1.5 — YouTubeScraper (mocked)
# ---------------------------------------------------------------------------

class TestYouTubeScraper:

    def test_yields_comments(self):
        from src.scrapers.youtube import YouTubeScraper

        search_resp = {
            "items": [{"id": {"videoId": "vid001"}}]
        }
        comments_resp = {
            "items": [{
                "id": "c_yt_001",
                "snippet": {
                    "topLevelComment": {
                        "snippet": {
                            "textDisplay": "I stopped my Groww SIP after the debit failed three times and it got cancelled.",
                            "publishedAt": "2024-01-01T00:00:00Z",
                            "likeCount": 5,
                        }
                    }
                }
            }],
            # No nextPageToken — stop after one page
        }

        with patch("requests.get") as mock_get:
            mock_search = MagicMock()
            mock_search.json.return_value = search_resp
            mock_search.raise_for_status = MagicMock()

            mock_comments = MagicMock()
            mock_comments.json.return_value = comments_resp
            mock_comments.raise_for_status = MagicMock()

            mock_get.side_effect = [mock_search, mock_comments]

            scraper = YouTubeScraper(
                api_key="fake_key",
                search_queries=["groww SIP"],
                max_videos_per_query=1,
                max_comments_per_video=10,
            )
            items = list(scraper.scrape())

        assert len(items) == 1
        assert items[0].source == "youtube"
        assert "SIP" in items[0].raw_text

    def test_no_api_key_returns_nothing(self):
        from src.scrapers.youtube import YouTubeScraper
        scraper = YouTubeScraper(api_key="", search_queries=["test"])
        items = list(scraper.scrape())
        assert items == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
