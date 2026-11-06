"""
SIP Insight Lab - Scraper: TradingQ&A (Task 1.4)
=================================================
Collects SIP/mutual-fund-related Q&A from tradingqna.com via
permitted HTTP scraping (respects robots.txt and rate limits).

Targets:
  Tags   : sip, mutual-fund, groww
  Volume : >= 300 items (questions + answers)

Usage:
    from src.scrapers.tradingqa import TradingQAScraper
    scraper = TradingQAScraper()
    for item in scraper.scrape():
        queue.enqueue(item)
"""

import os
import time
import logging
from datetime import datetime, timezone
from typing import Generator
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from src.ingestion.writer import RawItem

logger = logging.getLogger(__name__)

BASE_URL = os.getenv("TRADINGQA_BASE_URL", "https://tradingqna.com")
DELAY    = float(os.getenv("TRADINGQA_REQUEST_DELAY_SECONDS", "3"))
SOURCE   = "tradingqa"

HEADERS = {
    "User-Agent": "SIPInsightLab/1.0 (research; non-commercial; contact: research@example.com)",
    "Accept-Language": "en-US,en;q=0.9",
}

TAGS = ["sip", "mutual-fund", "groww", "mutual-funds"]


def _check_robots(base_url: str, path: str) -> bool:
    """Return True if scraping `path` is permitted by robots.txt."""
    robots_url = urljoin(base_url, "/robots.txt")
    rp = RobotFileParser()
    rp.set_url(robots_url)
    try:
        rp.read()
        return rp.can_fetch(HEADERS["User-Agent"], urljoin(base_url, path))
    except Exception:
        logger.warning("Could not read robots.txt — proceeding with caution.")
        return True


class TradingQAScraper:
    """
    Scrapes questions and accepted/top answers from tradingqna.com.

    Args:
        base_url: Root URL of the site.
        tags:     List of topic tags to search.
        delay:    Seconds between HTTP requests.
        max_pages_per_tag: Maximum paginated pages per tag.
    """

    def __init__(
        self,
        base_url: str = BASE_URL,
        tags: list[str] = TAGS,
        delay: float = DELAY,
        max_pages_per_tag: int = 10,
    ):
        self.base_url = base_url.rstrip("/")
        self.tags = tags
        self.delay = delay
        self.max_pages = max_pages_per_tag
        self._session = requests.Session()
        self._session.headers.update(HEADERS)
        self._seen_ids: set[str] = set()

    def scrape(self) -> Generator[RawItem, None, None]:
        """
        Yield RawItems for questions and their top answers.
        Usernames are discarded at collection time.
        """
        # Robots check once at start
        if not _check_robots(self.base_url, "/questions"):
            logger.error("TradingQAScraper: robots.txt forbids scraping. Aborting.")
            return

        for tag in self.tags:
            logger.info("TradingQAScraper: scraping tag='%s' ...", tag)
            yield from self._scrape_tag(tag)

    def _scrape_tag(self, tag: str) -> Generator[RawItem, None, None]:
        for page in range(1, self.max_pages + 1):
            # Attempt common Discourse/Q2A URL patterns
            url = f"{self.base_url}/questions/tagged/{tag}?page={page}"
            try:
                resp = self._session.get(url, timeout=15)
                if resp.status_code == 404:
                    # Try alternate pattern
                    url = f"{self.base_url}/tag/{tag}?page={page}"
                    resp = self._session.get(url, timeout=15)
                resp.raise_for_status()
            except requests.RequestException as e:
                logger.warning("TradingQAScraper: request error [%s, page %d]: %s", tag, page, e)
                break

            soup = BeautifulSoup(resp.text, "lxml")
            question_links = self._extract_question_links(soup)

            if not question_links:
                logger.info("TradingQAScraper: no more questions at page %d for tag '%s'.", page, tag)
                break

            for q_url, q_id in question_links:
                if q_id in self._seen_ids:
                    continue
                self._seen_ids.add(q_id)
                yield from self._scrape_question(q_url, q_id, tag)
                time.sleep(self.delay)

            logger.info("TradingQAScraper: tag='%s' page=%d done.", tag, page)
            time.sleep(self.delay)

    def _extract_question_links(self, soup: BeautifulSoup) -> list[tuple[str, str]]:
        """
        Extract (absolute_url, unique_id) pairs from the tag listing page.
        Handles both Discourse and Q2A-style markup.
        """
        results = []
        # Try Discourse topic links
        for a in soup.select("a.title, a.topic-title, td.main a[href*='/t/'], a[href*='/questions/']"):
            href = a.get("href", "")
            if not href:
                continue
            full_url = href if href.startswith("http") else urljoin(self.base_url, href)
            # Use the last path segment as a unique ID
            path = urlparse(full_url).path.rstrip("/")
            uid = path.split("/")[-1] or path.replace("/", "_")
            results.append((full_url, uid))
        return results

    def _scrape_question(self, url: str, q_id: str, tag: str) -> Generator[RawItem, None, None]:
        """Fetch a single question page and yield question body + top answers."""
        try:
            resp = self._session.get(url, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.debug("TradingQAScraper: failed to fetch question %s: %s", url, e)
            return

        soup = BeautifulSoup(resp.text, "lxml")

        # --- Question body ---
        q_body = (
            soup.select_one(".question-body, .topic-body, .cooked, article .content")
            or soup.find("div", class_=lambda c: c and "body" in c)
        )
        q_text = q_body.get_text(separator=" ", strip=True) if q_body else ""

        if q_text and len(q_text) > 30:
            yield RawItem(
                source=SOURCE,
                source_id=f"q_{q_id}",
                raw_text=q_text,
                raw_url=url,
                dedup_hash="",
                collected_at=datetime.now(timezone.utc).isoformat(),
                star_rating=None,
                metadata={"type": "question", "tag": tag},
            )

        # --- Top answers / replies ---
        answer_els = soup.select(".answer-body, .reply .cooked, .post-text")[:5]
        for i, a_el in enumerate(answer_els):
            a_text = a_el.get_text(separator=" ", strip=True)
            if a_text and len(a_text) > 30:
                yield RawItem(
                    source=SOURCE,
                    source_id=f"a_{q_id}_{i}",
                    raw_text=a_text,
                    raw_url=url,
                    dedup_hash="",
                    collected_at=datetime.now(timezone.utc).isoformat(),
                    star_rating=None,
                    metadata={"type": "answer", "tag": tag, "question_id": q_id},
                )


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    scraper = TradingQAScraper(tags=["sip"], max_pages_per_tag=2)
    items = list(scraper.scrape())
    print(f"Fetched {len(items)} items from TradingQ&A.")
    if items:
        print(f"Sample: {items[0].raw_text[:150]}")
