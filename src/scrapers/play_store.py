"""
SIP Insight Lab - Scraper: Google Play Store (Task 1.1)
========================================================
Collects Groww app reviews from Google Play using google-play-scraper.
Yields RawItem objects ready for the IngestionQueue.

Targets:
  App ID : com.nextbillion.groww
  Volume : >= 500 reviews (all star ratings)

Install dependency:
  pip install google-play-scraper

Usage:
    from src.scrapers.play_store import PlayStoreScraper
    scraper = PlayStoreScraper()
    for item in scraper.scrape(count=500):
        queue.enqueue(item)
"""

import os
import time
import logging
from datetime import datetime, timezone
from typing import Generator

from src.ingestion.writer import RawItem

logger = logging.getLogger(__name__)

try:
    from google_play_scraper import reviews, Sort
    _GPS_AVAILABLE = True
except ImportError:
    _GPS_AVAILABLE = False
    reviews = None  # type: ignore
    Sort = None     # type: ignore
    logger.warning("google-play-scraper not installed. Run: pip install google-play-scraper")

APP_ID = os.getenv("PLAY_STORE_TARGET_APP_ID", "com.nextbillion.groww")
DELAY  = float(os.getenv("PLAY_STORE_REQUEST_DELAY_SECONDS", "2"))
SOURCE = "play_store"


class PlayStoreScraper:
    """
    Scrapes Groww reviews from Google Play Store.

    Args:
        app_id: Play Store app package ID.
        delay_seconds: Sleep between paginated API calls (rate control).
    """

    def __init__(self, app_id: str = APP_ID, delay_seconds: float = DELAY):
        self.app_id = app_id
        self.delay = delay_seconds

    def scrape(self, count: int = 500, lang: str = "en", country: str = "in") -> Generator[RawItem, None, None]:
        """
        Yield RawItem objects for each Play Store review collected.

        Args:
            count:   Total number of reviews to fetch.
            lang:    Language code for reviews (default: en).
            country: Country code (default: in).
        """
        if not _GPS_AVAILABLE:
            logger.error(
                "google-play-scraper not installed. Run: pip install google-play-scraper"
            )
            return

        logger.info("PlayStoreScraper: fetching up to %d reviews for %s ...", count, self.app_id)

        collected = 0
        continuation_token = None

        while collected < count:
            batch_size = min(200, count - collected)
            try:
                result, continuation_token = reviews(
                    self.app_id,
                    lang=lang,
                    country=country,
                    sort=Sort.NEWEST,
                    count=batch_size,
                    continuation_token=continuation_token,
                )
            except Exception as e:
                logger.error("PlayStoreScraper: API error — %s", e)
                break

            if not result:
                logger.info("PlayStoreScraper: no more results after %d items.", collected)
                break

            for review in result:
                text = (review.get("content") or "").strip()
                if not text:
                    continue

                # Usernames are discarded (not stored) — ToS compliance
                review_id = str(review.get("reviewId", ""))
                app_version = review.get("appVersion") or ""
                star = review.get("score")
                at = review.get("at")
                date_str = (
                    at.astimezone(timezone.utc).isoformat()
                    if hasattr(at, "astimezone")
                    else datetime.now(timezone.utc).isoformat()
                )

                yield RawItem(
                    source=SOURCE,
                    source_id=review_id,
                    raw_text=text,
                    raw_url=f"https://play.google.com/store/apps/details?id={self.app_id}",
                    dedup_hash="",        # Filled by Deduplicator on enqueue
                    collected_at=date_str,
                    star_rating=star,
                    metadata={"app_version": app_version, "lang": lang, "country": country},
                )
                collected += 1
                if collected >= count:
                    break

            logger.info("PlayStoreScraper: %d/%d collected.", collected, count)

            if continuation_token is None:
                break

            time.sleep(self.delay)

        logger.info("PlayStoreScraper: done. Total yielded: %d", collected)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    # Dry-run: just count items without writing to DB
    scraper = PlayStoreScraper()
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    items = list(scraper.scrape(count=n))
    print(f"Fetched {len(items)} items from Play Store.")
    if items:
        print(f"Sample: [{items[0].star_rating}*] {items[0].raw_text[:120]}")
