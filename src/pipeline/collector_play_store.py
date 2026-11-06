"""
Groww SIP Insight Lab — Google Play Store Collector
====================================================
Collects all accessible user reviews for the Groww app from the Google Play Store.
Extracts: Review ID, Source, Date, Rating, Review Text, App Reference, URL.
Saves raw records to data/raw/raw_play_store.csv.
"""

import os
import sys
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("collector.play_store")

APP_ID = os.getenv("PLAY_STORE_TARGET_APP_ID", "com.nextbillion.groww")
DELAY = float(os.getenv("PLAY_STORE_REQUEST_DELAY_SECONDS", "1.5"))
RAW_OUTPUT_PATH = PROJECT_ROOT / "data" / "raw" / "raw_play_store.csv"


def collect_play_store_reviews(app_id: str = APP_ID, max_reviews: int = 3000) -> pd.DataFrame:
    """
    Collects reviews from Google Play Store using pagination across multiple sort modes
    (NEWEST and MOST_RELEVANT) until target is reached or pagination exhausts.
    """
    from google_play_scraper import reviews, Sort

    logger.info("Starting Google Play Store collection for %s (target: up to %d reviews)...", app_id, max_reviews)
    all_reviews_map = {}
    batch_size = 200

    for sort_mode in [Sort.NEWEST, Sort.MOST_RELEVANT]:
        sort_name = "NEWEST" if sort_mode == Sort.NEWEST else "MOST_RELEVANT"
        logger.info("Fetching Play Store reviews using sort mode: %s", sort_name)
        continuation_token = None
        sort_collected = 0
        target_per_sort = max_reviews // 2

        while sort_collected < target_per_sort and len(all_reviews_map) < max_reviews:
            current_count = min(batch_size, target_per_sort - sort_collected)
            try:
                result, continuation_token = reviews(
                    app_id,
                    lang="en",
                    country="in",
                    sort=sort_mode,
                    count=current_count,
                    continuation_token=continuation_token,
                )
            except Exception as e:
                logger.error("Play Store API error during fetch (%s): %s", sort_name, e)
                break

            if not result:
                logger.info("No further reviews returned for sort %s after %d items.", sort_name, sort_collected)
                break

            for r in result:
                review_id = str(r.get("reviewId") or "")
                content = (r.get("content") or "").strip()
                score = r.get("score")
                dt = r.get("at")
                if dt and isinstance(dt, datetime):
                    date_str = dt.astimezone(timezone.utc).isoformat()
                else:
                    date_str = datetime.now(timezone.utc).isoformat()

                if content and review_id not in all_reviews_map:
                    all_reviews_map[review_id] = {
                        "source_id": review_id,
                        "source": "play_store",
                        "date": date_str,
                        "rating": score,
                        "raw_text": content,
                        "reference": app_id,
                        "url": f"https://play.google.com/store/apps/details?id={app_id}&reviewId={review_id}",
                    }
                    sort_collected += 1

            logger.info("Collected %d unique Play Store reviews total...", len(all_reviews_map))
            if not continuation_token:
                logger.info("Play Store pagination completed for %s.", sort_name)
                break
            time.sleep(0.5)

    all_reviews = list(all_reviews_map.values())
    df = pd.DataFrame(all_reviews)
    RAW_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(RAW_OUTPUT_PATH, index=False, encoding="utf-8")
    logger.info("Successfully saved %d Play Store reviews to %s", len(df), RAW_OUTPUT_PATH)
    return df


if __name__ == "__main__":
    df_res = collect_play_store_reviews(max_reviews=600)
    print(f"Play Store Collection Complete: {len(df_res)} reviews.")

