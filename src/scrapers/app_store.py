"""
SIP Insight Lab - Scraper: Apple App Store (Task 1.2)
======================================================
Collects Groww app reviews from the Apple App Store using the
public iTunes RSS API — no API key required.

Targets:
  App ID  : 1404457431
  Store   : India (country=in)
  Volume  : >= 500 reviews (all pages)

Usage:
    from src.scrapers.app_store import AppStoreScraper
    scraper = AppStoreScraper()
    for item in scraper.scrape():
        queue.enqueue(item)
"""

import os
import time
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Generator

import requests

from src.ingestion.writer import RawItem

logger = logging.getLogger(__name__)

APP_ID  = os.getenv("APP_STORE_APP_ID", "1404871703")
COUNTRY = os.getenv("APP_STORE_COUNTRY", "in")
DELAY   = float(os.getenv("APP_STORE_REQUEST_DELAY_SECONDS", "1"))
SOURCE  = "app_store"

# iTunes RSS API: 10 pages x 50 reviews per page = 500 max
RSS_BASE = "https://itunes.apple.com/{country}/rss/customerreviews/page={page}/id={app_id}/sortBy=mostRecent/xml"
HEADERS  = {"User-Agent": "SIPInsightLab/1.0 (research; non-commercial)"}

NS = {"atom": "http://www.w3.org/2005/Atom"}


class AppStoreScraper:
    """
    Fetches reviews from the Apple App Store RSS feed (public, paginated).

    Args:
        app_id:  iTunes App ID (numeric string).
        country: Two-letter country code.
        delay:   Seconds between page requests.
    """

    def __init__(
        self,
        app_id: str = APP_ID,
        country: str = COUNTRY,
        delay: float = DELAY,
    ):
        self.app_id = app_id
        self.country = country
        self.delay = delay
        self._session = requests.Session()
        self._session.headers.update(HEADERS)

    def scrape(self, max_pages: int = 10) -> Generator[RawItem, None, None]:
        """
        Yield RawItems from iTunes RSS, one page at a time (max 50 per page).

        Args:
            max_pages: Max RSS pages to fetch (10 = 500 reviews).
        """
        logger.info(
            "AppStoreScraper: fetching up to %d pages for app %s [%s] ...",
            max_pages, self.app_id, self.country,
        )
        total = 0

        for page in range(1, max_pages + 1):
            url = RSS_BASE.format(country=self.country, page=page, app_id=self.app_id)
            try:
                resp = self._session.get(url, timeout=15)
                resp.raise_for_status()
            except requests.RequestException as e:
                logger.error("AppStoreScraper page %d error: %s", page, e)
                break

            try:
                root = ET.fromstring(resp.content)
            except ET.ParseError as e:
                logger.error("AppStoreScraper: XML parse error on page %d: %s", page, e)
                break

            entries = root.findall("atom:entry", NS)
            # First <entry> is the app metadata — skip it
            entries = [e for e in entries if e.find("atom:id", NS) is not None]
            if not entries:
                logger.info("AppStoreScraper: no more entries at page %d.", page)
                break

            for entry in entries:
                text_el   = entry.find("atom:content", NS)
                rating_el = entry.find("{http://itunes.apple.com/rss}rating")
                id_el     = entry.find("atom:id", NS)
                updated   = entry.find("atom:updated", NS)

                text = (text_el.text or "").strip() if text_el is not None else ""
                if not text:
                    continue

                # reviewer names not stored — discarded here
                review_id = (id_el.text or "").strip() if id_el is not None else f"p{page}_i{total}"
                star = int(rating_el.text) if rating_el is not None and rating_el.text else None
                date_str = (
                    updated.text.strip()
                    if updated is not None and updated.text
                    else datetime.now(timezone.utc).isoformat()
                )

                yield RawItem(
                    source=SOURCE,
                    source_id=review_id,
                    raw_text=text,
                    raw_url=f"https://apps.apple.com/{self.country}/app/groww/id{self.app_id}",
                    dedup_hash="",
                    collected_at=date_str,
                    star_rating=star,
                    metadata={"page": page, "country": self.country},
                )
                total += 1

            logger.info("AppStoreScraper: page %d done — %d total so far.", page, total)
            time.sleep(self.delay)

        logger.info("AppStoreScraper: done. Total yielded: %d", total)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    scraper = AppStoreScraper()
    pages = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    items = list(scraper.scrape(max_pages=pages))
    print(f"Fetched {len(items)} items from App Store.")
    if items:
        print(f"Sample: [{items[0].star_rating}*] {items[0].raw_text[:120]}")
