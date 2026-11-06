"""
Groww SIP Insight Lab — YouTube Comments Collector
==================================================
Collects user comments from Groww and SIP-related videos using YouTube Data API v3.
Extracts: Comment ID, Source, Date, Rating (None), Comment Text, Video Reference, URL.
Saves raw records to data/raw/raw_youtube.csv.
"""

import os
import sys
import time
import logging
import requests
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("collector.youtube")

API_KEY = os.getenv("YOUTUBE_API_KEY", "")
DELAY = float(os.getenv("YOUTUBE_REQUEST_DELAY_SECONDS", "1.0"))
RAW_OUTPUT_PATH = PROJECT_ROOT / "data" / "raw" / "raw_youtube.csv"
YT_API_BASE = "https://www.googleapis.com/youtube/v3"

SEARCH_QUERIES = [
    "groww SIP review",
    "groww app mutual fund experience",
    "SIP cancelled Groww",
    "SIP debit failed India",
    "should I stop SIP mutual fund",
    "groww SIP mandate problem",
    "mutual fund SIP loss India",
]


def search_videos(query: str, api_key: str, max_results: int = 5) -> list:
    """Finds top video IDs for a query."""
    url = f"{YT_API_BASE}/search"
    params = {
        "part": "id,snippet",
        "q": query,
        "type": "video",
        "relevanceLanguage": "en",
        "regionCode": "IN",
        "maxResults": max_results,
        "key": api_key,
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        videos = []
        for it in items:
            vid = it.get("id", {}).get("videoId")
            title = it.get("snippet", {}).get("title", "")
            if vid:
                videos.append({"video_id": vid, "title": title})
        return videos
    except Exception as e:
        logger.error("YouTube search error for query '%s': %s", query, e)
        return []


def collect_comments_for_video(video: dict, api_key: str, max_comments: int = 150) -> list:
    """Fetches top-level comments for a given video."""
    video_id = video["video_id"]
    video_title = video["title"]
    comments = []
    page_token = None
    url = f"{YT_API_BASE}/commentThreads"

    while len(comments) < max_comments:
        params = {
            "part": "snippet",
            "videoId": video_id,
            "maxResults": min(100, max_comments - len(comments)),
            "textFormat": "plainText",
            "key": api_key,
        }
        if page_token:
            params["pageToken"] = page_token

        try:
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 403:
                # Comments might be disabled on this video
                logger.warning("Comments disabled or forbidden for video %s", video_id)
                break
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning("Error fetching comments for video %s: %s", video_id, e)
            break

        items = data.get("items", [])
        if not items:
            break

        for it in items:
            snippet = it.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
            text = (snippet.get("textDisplay") or snippet.get("textOriginal") or "").strip()
            cid = it.get("id") or f"yt_{video_id}_{len(comments)}"
            published_at = snippet.get("publishedAt") or datetime.now(timezone.utc).isoformat()
            if text:
                comments.append({
                    "source_id": str(cid),
                    "source": "youtube",
                    "date": published_at,
                    "rating": None,
                    "raw_text": text,
                    "reference": f"{video_title} (ID: {video_id})",
                    "url": f"https://www.youtube.com/watch?v={video_id}&lc={cid}",
                })

        page_token = data.get("nextPageToken")
        if not page_token:
            break
        time.sleep(DELAY)

    return comments


def collect_youtube_comments(queries: list = None, max_videos_per_query: int = 6, max_comments_per_video: int = 120) -> pd.DataFrame:
    """
    Collects comments across relevant YouTube videos.
    """
    if not API_KEY:
        logger.error("YOUTUBE_API_KEY is missing from environment. Cannot proceed with YouTube collection.")
        return pd.DataFrame()

    queries = queries or SEARCH_QUERIES
    logger.info("Starting YouTube collection across %d queries ...", len(queries))
    all_comments = []
    seen_ids = set()

    for q in queries:
        logger.info("Searching YouTube videos for: '%s' ...", q)
        videos = search_videos(q, API_KEY, max_results=max_videos_per_query)
        for v in videos:
            v_comments = collect_comments_for_video(v, API_KEY, max_comments=max_comments_per_video)
            for c in v_comments:
                if c["source_id"] not in seen_ids:
                    seen_ids.add(c["source_id"])
                    all_comments.append(c)
            time.sleep(DELAY)

    df = pd.DataFrame(all_comments)
    RAW_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(RAW_OUTPUT_PATH, index=False, encoding="utf-8")
    logger.info("Successfully saved %d YouTube comments to %s", len(df), RAW_OUTPUT_PATH)
    return df


if __name__ == "__main__":
    df_res = collect_youtube_comments(max_videos_per_query=3, max_comments_per_video=60)
    print(f"YouTube Collection Complete: {len(df_res)} comments.")

