"""
SIP Insight Lab - Scraper: Reddit PRAW Client (Task 1.3)
=========================================================
Collects SIP-related posts and comments from target subreddits
using the Reddit Public API (PRAW, read-only OAuth).

Targets:
  Subreddits : r/IndiaInvestments, r/mutualfunds, r/Groww, r/personalfinanceindia
  Search     : SIP, mutual fund, groww SIP, SIP stopped, SIP cancelled
  Volume     : >= 500 items

Credentials required in .env:
  REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT

Usage:
    from src.scrapers.reddit import RedditScraper
    scraper = RedditScraper()
    for item in scraper.scrape():
        queue.enqueue(item)
"""

import os
import time
import logging
from datetime import datetime, timezone
from typing import Generator

from src.ingestion.writer import RawItem

logger = logging.getLogger(__name__)

SOURCE = "reddit"

SUBREDDITS = [
    "IndiaInvestments",
    "mutualfunds",
    "Groww",
    "personalfinanceindia",
]

SEARCH_TERMS = [
    "SIP",
    "systematic investment plan",
    "SIP stopped",
    "SIP cancelled",
    "groww SIP",
    "mutual fund cancel",
    "stop SIP",
    "SIP lapse",
    "SIP debit failed",
]


def _utc_iso(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


class RedditScraper:
    """
    Collects Reddit posts and comments related to SIP churn/retention.

    Args:
        subreddits:   List of subreddit names to search.
        search_terms: List of query strings to search within each subreddit.
        delay:        Seconds between API calls (PRAW auto-rates, this is extra safety).
        posts_per_query: Max posts per search query per subreddit.
        comments_per_post: Max top-level comments to collect per post.
    """

    def __init__(
        self,
        subreddits: list[str] = SUBREDDITS,
        search_terms: list[str] = SEARCH_TERMS,
        delay: float = 1.0,
        posts_per_query: int = 25,
        comments_per_post: int = 10,
    ):
        self.subreddits = subreddits
        self.search_terms = search_terms
        self.delay = delay
        self.posts_per_query = posts_per_query
        self.comments_per_post = comments_per_post
        self._reddit = self._build_client()

    def _build_client(self):
        try:
            import praw
        except ImportError:
            logger.error("praw not installed. Run: pip install praw")
            return None

        client_id     = os.getenv("REDDIT_CLIENT_ID", "")
        client_secret = os.getenv("REDDIT_CLIENT_SECRET", "")
        user_agent    = os.getenv("REDDIT_USER_AGENT", "SIPInsightLab/1.0")

        if not client_id or not client_secret:
            logger.warning(
                "Reddit credentials not set in .env. "
                "Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET."
            )
            return None

        return praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
            read_only=True,     # Read-only scope — no account actions
        )

    def scrape(self) -> Generator[RawItem, None, None]:
        """
        Yield RawItems: both post selftext and top-level comments.
        Usernames are NOT stored — discarded at collection time.
        """
        if not self._reddit:
            logger.error("RedditScraper: no valid Reddit client. Check credentials.")
            return

        seen_ids: set[str] = set()

        for subreddit_name in self.subreddits:
            subreddit = self._reddit.subreddit(subreddit_name)
            logger.info("RedditScraper: searching r/%s ...", subreddit_name)

            for term in self.search_terms:
                try:
                    posts = subreddit.search(term, limit=self.posts_per_query, sort="relevance")
                    for post in posts:
                        post_id = post.id

                        # --- Post body ---
                        if post_id not in seen_ids and post.selftext and len(post.selftext.strip()) > 20:
                            seen_ids.add(post_id)
                            yield RawItem(
                                source=SOURCE,
                                source_id=f"post_{post_id}",
                                raw_text=post.selftext.strip(),
                                raw_url=f"https://www.reddit.com{post.permalink}",
                                dedup_hash="",
                                collected_at=_utc_iso(post.created_utc),
                                star_rating=None,
                                metadata={
                                    "subreddit": subreddit_name,
                                    "score": post.score,
                                    "type": "post",
                                    "search_term": term,
                                },
                            )

                        # --- Top-level comments ---
                        try:
                            post.comments.replace_more(limit=0)
                            for comment in post.comments[:self.comments_per_post]:
                                c_id = comment.id
                                body = (comment.body or "").strip()
                                if c_id in seen_ids or len(body) < 20 or body == "[deleted]":
                                    continue
                                seen_ids.add(c_id)
                                yield RawItem(
                                    source=SOURCE,
                                    source_id=f"comment_{c_id}",
                                    raw_text=body,
                                    raw_url=f"https://www.reddit.com{post.permalink}",
                                    dedup_hash="",
                                    collected_at=_utc_iso(comment.created_utc),
                                    star_rating=None,
                                    metadata={
                                        "subreddit": subreddit_name,
                                        "score": comment.score,
                                        "type": "comment",
                                        "search_term": term,
                                        "post_id": post_id,
                                    },
                                )
                        except Exception as ce:
                            logger.debug("Comment fetch error for post %s: %s", post_id, ce)

                except Exception as e:
                    logger.warning(
                        "RedditScraper: error searching r/%s for '%s': %s",
                        subreddit_name, term, e,
                    )

                time.sleep(self.delay)

        logger.info("RedditScraper: done. Total unique IDs seen: %d", len(seen_ids))


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    scraper = RedditScraper(
        subreddits=["IndiaInvestments"],
        search_terms=["SIP stopped"],
        posts_per_query=5,
        comments_per_post=3,
    )
    items = list(scraper.scrape())
    print(f"Fetched {len(items)} items from Reddit.")
    if items:
        print(f"Sample: {items[0].raw_text[:150]}")
