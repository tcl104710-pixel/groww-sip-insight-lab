"""
Groww SIP Insight Lab — Reddit Collector
========================================
Collects posts and discussions discussing Groww, SIP investments, and mutual fund experiences
from r/IndiaInvestments, r/mutualfunds, r/Groww, and r/personalfinanceindia.

Uses Apify actor `fatihtahta/reddit-scraper-search-fast` with Reddit RSS fallback.
Extracts: Review/Comment ID, Source, Date, Rating (None), Text, Subreddit Reference, URL.
Saves raw records to data/raw/raw_reddit.csv.
"""

import os
import sys
import time
import logging
import re
import html
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("collector.reddit")

APIFY_TOKEN = os.getenv("APIFY_API_TOKEN", "")
RAW_OUTPUT_PATH = PROJECT_ROOT / "data" / "raw" / "raw_reddit.csv"

TARGET_QUERIES = [
    "Groww SIP",
    "Groww mutual fund SIP stopped",
    "Groww SIP mandate failure",
    "Groww SIP auto debit failed",
    "Groww pause SIP cancel",
    "Groww SIP loss market crash",
    "Groww SIP bounce charges",
    "Groww delayed NAV allotment",
    "Groww step up SIP",
]

SUBREDDITS = [
    "IndiaInvestments",
    "mutualfunds",
    "Groww",
    "personalfinanceindia",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 SIPInsightLab/1.0"
}
ATOM_NS = "{http://www.w3.org/2005/Atom}"


def clean_html_summary(html_content: str) -> str:
    """Removes HTML tags and decodes entities from RSS summary content."""
    if not html_content:
        return ""
    text = re.sub(r"<[^>]+>", " ", html_content)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def collect_via_apify(queries: list = None, max_items: int = 400) -> list:
    """Runs Apify Reddit scraper actor for fast, block-free extraction."""
    if not APIFY_TOKEN or APIFY_TOKEN.startswith("your_"):
        logger.warning("No valid APIFY_API_TOKEN configured. Skipping Apify.")
        return []

    try:
        from apify_client import ApifyClient
        client = ApifyClient(APIFY_TOKEN)
        queries = queries or TARGET_QUERIES
        records = []
        logger.info("Executing Apify Reddit scraper for queries: %s ...", queries)

        run = client.actor("fatihtahta/reddit-scraper-search-fast").call(
            run_input={
                "queries": queries,
                "maxPosts": max_items,
                "sort": "relevance",
            }
        )
        dataset_id = getattr(run, "default_dataset_id", None) or (run.get("default_dataset_id") if isinstance(run, dict) else None)
        if dataset_id:
            logger.info("Apify run succeeded. Fetching dataset %s ...", dataset_id)
            dataset = client.dataset(dataset_id)
            for it in dataset.iterate_items():
                title = it.get("title", "")
                selftext = it.get("selftext", "") or it.get("body", "") or it.get("description", "")
                full_text = f"{title}\n{selftext}".strip() if selftext else title
                post_id = str(it.get("id") or it.get("postId") or len(records))
                link = it.get("url") or it.get("permalink") or "https://reddit.com"
                if not link.startswith("http"):
                    link = f"https://www.reddit.com{link}"

                created = it.get("createdAt") or it.get("createdUtc") or datetime.now(timezone.utc).isoformat()

                if len(full_text) >= 15:
                    records.append({
                        "source_id": f"reddit_{post_id}",
                        "source": "reddit",
                        "date": created,
                        "rating": None,
                        "raw_text": full_text,
                        "reference": f"r/{it.get('subreddit', 'IndiaInvestments')}: {title[:80]}",
                        "url": link,
                    })

            logger.info("Apify Reddit collector retrieved %d valid items.", len(records))
        return records
    except Exception as e:
        logger.error("Apify Reddit collection encountered error: %s", e)
        return []


def collect_via_reddit_rss(subreddits: list = None) -> list:
    """Quick RSS fetch for top recent subreddit posts with single pass."""
    subreddits = subreddits or ["IndiaInvestments", "mutualfunds", "Groww"]
    records = []
    session = requests.Session()
    session.headers.update(HEADERS)

    for sub in subreddits:
        url = f"https://www.reddit.com/r/{sub}/search.rss?q=SIP+Groww&restrict_sr=1&sort=relevance&limit=20"
        try:
            resp = session.get(url, timeout=10)
            if resp.status_code == 200:
                root = ET.fromstring(resp.content)
                entries = root.findall(f"{ATOM_NS}entry")
                for entry in entries:
                    id_el = entry.find(f"{ATOM_NS}id")
                    title_el = entry.find(f"{ATOM_NS}title")
                    content_el = entry.find(f"{ATOM_NS}content")
                    updated_el = entry.find(f"{ATOM_NS}updated")
                    link_el = entry.find(f"{ATOM_NS}link")

                    item_id = id_el.text.strip() if id_el is not None and id_el.text else ""
                    title = title_el.text.strip() if title_el is not None and title_el.text else ""
                    body_html = content_el.text if content_el is not None and content_el.text else ""
                    body = clean_html_summary(body_html)
                    link = link_el.get("href") if link_el is not None else f"https://www.reddit.com/r/{sub}"
                    date_str = updated_el.text.strip() if updated_el is not None and updated_el.text else datetime.now(timezone.utc).isoformat()

                    full_text = f"{title}. {body}".strip() if body and body != title else title
                    if len(full_text) >= 15:
                        records.append({
                            "source_id": item_id or f"reddit_rss_{len(records)}",
                            "source": "reddit",
                            "date": date_str,
                            "rating": None,
                            "raw_text": full_text,
                            "reference": f"r/{sub}: {title[:80]}",
                            "url": link,
                        })
            else:
                logger.info("RSS fetch for r/%s returned status %d. Relying on primary collector.", sub, resp.status_code)
        except Exception as e:
            logger.info("RSS fetch failed for r/%s: %s", sub, e)

        time.sleep(1.0)

    return records


def collect_reddit_discussions() -> pd.DataFrame:
    """Orchestrates Reddit collection combining Apify and RSS feeds."""
    logger.info("Starting Reddit feedback collection...")
    apify_records = collect_via_apify()
    rss_records = collect_via_reddit_rss() if len(apify_records) < 30 else []

    combined = apify_records + rss_records
    # Dedup by source_id or raw_text
    seen = set()
    final_records = []
    for r in combined:
        key = r["raw_text"][:80].lower()
        if key not in seen:
            seen.add(key)
            final_records.append(r)

    df = pd.DataFrame(final_records)
    RAW_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(RAW_OUTPUT_PATH, index=False, encoding="utf-8")
    logger.info("Successfully saved %d Reddit records to %s", len(df), RAW_OUTPUT_PATH)
    return df


if __name__ == "__main__":
    df_res = collect_reddit_discussions()
    print(f"Reddit Collection Complete: {len(df_res)} items.")
