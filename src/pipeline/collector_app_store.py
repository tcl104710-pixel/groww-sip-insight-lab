"""
Groww SIP Insight Lab — Apple App Store Collector
=================================================
Collects all available customer reviews for Groww from the Apple App Store RSS API.
Extracts: Review ID, Source, Date, Rating, Review Text, App Reference, URL.
Saves raw records to data/raw/raw_app_store.csv.
"""

import os
import sys
import time
import logging
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("collector.app_store")

APP_ID = os.getenv("APP_STORE_APP_ID", "1404871703")
COUNTRY = os.getenv("APP_STORE_COUNTRY", "in")
DELAY = float(os.getenv("APP_STORE_REQUEST_DELAY_SECONDS", "1.0"))
RAW_OUTPUT_PATH = PROJECT_ROOT / "data" / "raw" / "raw_app_store.csv"

RSS_URL_TEMPLATE = "https://itunes.apple.com/{country}/rss/customerreviews/page={page}/id={app_id}/sortBy=mostRecent/xml"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "itunes": "http://itunes.apple.com/rss"}
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


def collect_app_store_reviews(app_id: str = APP_ID, country: str = COUNTRY, max_pages: int = 10) -> pd.DataFrame:
    """
    Collects customer reviews across all available RSS pages (Apple RSS provides up to 10 pages).
    """
    logger.info("Starting Apple App Store collection for app %s (%s) up to %d pages ...", app_id, country, max_pages)
    reviews = []
    session = requests.Session()
    session.headers.update(HEADERS)

    for page in range(1, max_pages + 1):
        url = RSS_URL_TEMPLATE.format(country=country, page=page, app_id=app_id)
        try:
            resp = session.get(url, timeout=15)
            if resp.status_code == 404 or resp.status_code == 400:
                logger.info("End of available pages at page %d.", page)
                break
            resp.raise_for_status()
        except Exception as e:
            logger.warning("Error fetching App Store page %d: %s", page, e)
            break

        try:
            root = ET.fromstring(resp.content)
        except Exception as pe:
            logger.error("XML parse error on page %d: %s", page, pe)
            break

        entries = root.findall("atom:entry", ATOM_NS)
        # Skip index 0 if it contains app summary rather than customer review
        entries = [e for e in entries if e.find("atom:id", ATOM_NS) is not None]
        if not entries:
            logger.info("No more reviews found on page %d.", page)
            break

        for entry in entries:
            title_el = entry.find("atom:title", ATOM_NS)
            content_el = entry.find("atom:content", ATOM_NS)
            rating_el = entry.find("itunes:rating", ATOM_NS)
            id_el = entry.find("atom:id", ATOM_NS)
            updated_el = entry.find("atom:updated", ATOM_NS)

            title = (title_el.text or "").strip() if title_el is not None else ""
            body = (content_el.text or "").strip() if content_el is not None else ""
            full_text = f"{title}\n{body}".strip() if title and title != body else body

            if not full_text:
                continue

            review_id = (id_el.text or "").strip() if id_el is not None else f"appstore_{page}_{len(reviews)}"
            star = int(rating_el.text) if rating_el is not None and rating_el.text and rating_el.text.isdigit() else None
            date_str = updated_el.text.strip() if updated_el is not None and updated_el.text else datetime.now(timezone.utc).isoformat()

            reviews.append({
                "source_id": review_id,
                "source": "app_store",
                "date": date_str,
                "rating": star,
                "raw_text": full_text,
                "reference": "Groww Stocks, Mutual Fund, IPO",
                "url": f"https://apps.apple.com/{country}/app/groww/id{app_id}",
            })

        logger.info("App Store Page %d collected. Total items so far: %d", page, len(reviews))
        time.sleep(DELAY)

    df = pd.DataFrame(reviews)
    RAW_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(RAW_OUTPUT_PATH, index=False, encoding="utf-8")
    logger.info("Successfully saved %d App Store reviews to %s", len(df), RAW_OUTPUT_PATH)
    return df


if __name__ == "__main__":
    df_res = collect_app_store_reviews(max_pages=10)
    print(f"App Store Collection Complete: {len(df_res)} reviews.")

