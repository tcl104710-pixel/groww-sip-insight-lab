"""
SIP Insight Lab - Scraper: YouTube Data API v3 (Task 1.5)
==========================================================
Collects comments from SIP/Groww-related YouTube videos
using the official YouTube Data API v3.

Targets:
  Queries  : "groww SIP review", "SIP cancelled", "should I stop SIP", etc.
  Volume   : >= 500 comments across top 20 videos per query
  API Key  : Required — set YOUTUBE_API_KEY in .env

Quota note:
  - list(search) = 100 units per call
  - commentThreads.list = 1 unit per call
  - Free tier: 10,000 units/day  -> ~95 video searches + comments

Usage:
    from src.scrapers.youtube import YouTubeScraper
    scraper = YouTubeScraper()
    for item in scraper.scrape():
        queue.enqueue(item)
"""

import os
import time
import logging
from datetime import datetime, timezone
from typing import Generator, Optional

import requests

from src.ingestion.writer import RawItem

logger = logging.getLogger(__name__)

API_KEY = os.getenv("YOUTUBE_API_KEY", "")
DELAY   = float(os.getenv("YOUTUBE_REQUEST_DELAY_SECONDS", "1"))
SOURCE  = "youtube"

SEARCH_QUERIES = [
    "groww SIP review",
    "SIP mutual fund beginner India",
    "should I stop SIP",
    "SIP cancelled Groww",
    "groww app mutual fund experience",
    "SIP debit failed India",
    "mutual fund SIP problems India",
]

YT_API_BASE = "https://www.googleapis.com/youtube/v3"


class YouTubeScraper:
    """
    Scrapes YouTube comments from SIP-related videos via the Data API v3.

    Args:
        api_key:         YouTube Data API v3 key.
        search_queries:  List of search strings.
        max_videos_per_query: Videos to process per query.
        max_comments_per_video: Top-level comments per video.
        delay:           Seconds between API calls.
    """

    def __init__(
        self,
        api_key: str = API_KEY,
        search_queries: list[str] = SEARCH_QUERIES,
        max_videos_per_query: int = 5,
        max_comments_per_video: int = 100,
        delay: float = DELAY,
    ):
        self.api_key = api_key
        self.queries = search_queries
        self.max_videos = max_videos_per_query
        self.max_comments = max_comments_per_video
        self.delay = delay
        self._seen_comment_ids: set[str] = set()
        self._quota_used = 0

    def scrape(self) -> Generator[RawItem, None, None]:
        """Yield RawItems for YouTube comments. Author names are discarded."""
        if not self.api_key:
            logger.error(
                "YouTubeScraper: YOUTUBE_API_KEY not set. "
                "Set it in .env and retry."
            )
            return

        for query in self.queries:
            logger.info("YouTubeScraper: searching for '%s' ...", query)
            video_ids = self._search_videos(query)
            for video_id in video_ids:
                yield from self._collect_comments(video_id, query)
                time.sleep(self.delay)

        logger.info(
            "YouTubeScraper: done. Quota used: ~%d units. Unique comments: %d",
            self._quota_used, len(self._seen_comment_ids),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get(self, endpoint: str, params: dict) -> Optional[dict]:
        """Make an authenticated GET request to the YouTube API."""
        params["key"] = self.api_key
        try:
            resp = requests.get(f"{YT_API_BASE}/{endpoint}", params=params, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.error("YouTubeScraper API error [%s]: %s", endpoint, e)
            return None

    def _search_videos(self, query: str) -> list[str]:
        """Return up to max_videos video IDs for a search query."""
        data = self._get("search", {
            "part":          "id",
            "q":             query,
            "type":          "video",
            "relevanceLanguage": "en",
            "regionCode":    "IN",
            "maxResults":    self.max_videos,
            "videoCategoryId": "27",   # Education category
        })
        self._quota_used += 100  # search costs 100 units

        if not data or "items" not in data:
            logger.warning("YouTubeScraper: no videos found for query '%s'.", query)
            return []

        ids = [item["id"].get("videoId") for item in data["items"] if "id" in item]
        return [v for v in ids if v]

    def _collect_comments(self, video_id: str, query: str) -> Generator[RawItem, None, None]:
        """Yield comment RawItems for one video."""
        page_token: Optional[str] = None
        collected = 0
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        while collected < self.max_comments:
            params = {
                "part":       "snippet",
                "videoId":    video_id,
                "maxResults": min(100, self.max_comments - collected),
                "order":      "relevance",
                "textFormat": "plainText",
            }
            if page_token:
                params["pageToken"] = page_token

            data = self._get("commentThreads", params)
            self._quota_used += 1  # commentThreads costs 1 unit

            if not data or "items" not in data:
                break

            for item in data["items"]:
                snippet = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                text    = (snippet.get("textDisplay") or "").strip()
                c_id    = item.get("id", "")
                pub_at  = snippet.get("publishedAt") or datetime.now(timezone.utc).isoformat()
                likes   = snippet.get("likeCount", 0)

                if not text or len(text) < 15 or c_id in self._seen_comment_ids:
                    continue

                # Author display name is NOT stored — discarded here
                self._seen_comment_ids.add(c_id)
                collected += 1

                yield RawItem(
                    source=SOURCE,
                    source_id=c_id,
                    raw_text=text,
                    raw_url=video_url,
                    dedup_hash="",
                    collected_at=pub_at,
                    star_rating=None,
                    metadata={
                        "video_id":   video_id,
                        "like_count": likes,
                        "search_query": query,
                    },
                )

            page_token = data.get("nextPageToken")
            if not page_token:
                break

            time.sleep(self.delay)

        logger.info("YouTubeScraper: video %s — %d comments collected.", video_id, collected)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    scraper = YouTubeScraper(
        search_queries=["groww SIP review"],
        max_videos_per_query=2,
        max_comments_per_video=20,
    )
    items = list(scraper.scrape())
    print(f"Fetched {len(items)} items from YouTube.")
    if items:
        print(f"Sample: {items[0].raw_text[:150]}")
