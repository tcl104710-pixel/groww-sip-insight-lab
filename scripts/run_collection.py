"""
SIP Insight Lab - Phase 1 Orchestrator (Task 1.9)
==================================================
Runs all five scrapers in sequence and populates the raw_item table.
Produces a Collection QA report at the end.

Usage:
    python scripts/run_collection.py [--sources play_store app_store reddit tradingqa youtube]
    python scripts/run_collection.py --sources reddit youtube   # subset

Flags:
    --sources   : Space-separated list of sources to run (default: all 5)
    --dry-run   : Collect items but don't write to DB (count only)
    --limit N   : Override per-source collection limit (default: from config.yaml)
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.db.schema import init_db
from src.ingestion.queue import IngestionQueue

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("orchestrator")

ALL_SOURCES = ["play_store", "app_store", "reddit", "tradingqa", "youtube"]

# Default limits (can be overridden via --limit)
DEFAULT_LIMITS = {
    "play_store": 500,
    "app_store":  500,
    "reddit":     500,
    "tradingqa":  300,
    "youtube":    500,
}


def run_play_store(queue: IngestionQueue, limit: int) -> int:
    from src.scrapers.play_store import PlayStoreScraper
    scraper = PlayStoreScraper()
    count = 0
    for item in scraper.scrape(count=limit):
        queue.enqueue(item)
        count += 1
    return count


def run_app_store(queue: IngestionQueue, limit: int) -> int:
    from src.scrapers.app_store import AppStoreScraper
    pages = max(1, limit // 50)
    scraper = AppStoreScraper()
    count = 0
    for item in scraper.scrape(max_pages=pages):
        queue.enqueue(item)
        count += 1
    return count


def run_reddit(queue: IngestionQueue, limit: int) -> int:
    from src.scrapers.reddit import RedditScraper
    scraper = RedditScraper()
    count = 0
    for item in scraper.scrape():
        queue.enqueue(item)
        count += 1
        if count >= limit:
            break
    return count


def run_tradingqa(queue: IngestionQueue, limit: int) -> int:
    from src.scrapers.tradingqa import TradingQAScraper
    scraper = TradingQAScraper()
    count = 0
    for item in scraper.scrape():
        queue.enqueue(item)
        count += 1
        if count >= limit:
            break
    return count


def run_youtube(queue: IngestionQueue, limit: int) -> int:
    from src.scrapers.youtube import YouTubeScraper
    scraper = YouTubeScraper(max_comments_per_video=100)
    count = 0
    for item in scraper.scrape():
        queue.enqueue(item)
        count += 1
        if count >= limit:
            break
    return count


RUNNERS = {
    "play_store": run_play_store,
    "app_store":  run_app_store,
    "reddit":     run_reddit,
    "tradingqa":  run_tradingqa,
    "youtube":    run_youtube,
}


def main():
    parser = argparse.ArgumentParser(description="SIP Insight Lab — Phase 1 Data Collection")
    parser.add_argument(
        "--sources", nargs="+", default=ALL_SOURCES,
        choices=ALL_SOURCES,
        help="Sources to collect from (default: all 5)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Collect but do not write to DB",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Override per-source item limit",
    )
    args = parser.parse_args()

    db_path = os.getenv("DB_PATH", "./data/sip_insight_lab.db")
    conn = init_db(db_path)
    queue = IngestionQueue(conn, batch_size=50, inter_batch_delay=0.0)

    report = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": args.dry_run,
        "sources": {},
    }

    for source in args.sources:
        limit = args.limit or DEFAULT_LIMITS[source]
        logger.info("=" * 60)
        logger.info("Starting collection: source=%s limit=%d", source, limit)
        logger.info("=" * 60)
        t0 = time.time()

        try:
            runner = RUNNERS[source]
            if args.dry_run:
                # Create a no-op queue that just counts
                class _CountQueue:
                    def __init__(self): self.n = 0
                    def enqueue(self, _): self.n += 1
                cq = _CountQueue()
                runner(cq, limit)
                collected = cq.n
                written = collected
                dupes = 0
            else:
                before = queue._writer.count(source)
                runner(queue, limit)
                queue.flush()
                after = queue._writer.count(source)
                collected = queue._total_enqueued
                written = after - before
                dupes = queue.stats()["total_duplicate"]

            elapsed = round(time.time() - t0, 1)
            report["sources"][source] = {
                "collected": collected,
                "written_to_db": written if not args.dry_run else "dry-run",
                "duration_seconds": elapsed,
            }
            logger.info(
                "source=%s  written=%s  elapsed=%.1fs",
                source, written, elapsed,
            )
        except Exception as e:
            logger.error("source=%s FAILED: %s", source, e)
            report["sources"][source] = {"error": str(e)}

    # ----- Final QA Report -----
    report["queue_stats"] = queue.stats()

    # DB counts per source
    if not args.dry_run:
        report["db_counts"] = {}
        for src in ALL_SOURCES:
            report["db_counts"][src] = queue._writer.count(src)
        report["db_counts"]["total"] = queue._writer.count()

    # Check exit criteria
    min_targets = {"play_store": 500, "app_store": 500, "reddit": 500, "tradingqa": 300, "youtube": 500}
    criteria = {}
    if not args.dry_run:
        for src, target in min_targets.items():
            actual = report["db_counts"].get(src, 0)
            criteria[src] = {"target": target, "actual": actual, "met": actual >= target}
        total_items = report["db_counts"].get("total", 0)
        criteria["total_2300"] = {"target": 2300, "actual": total_items, "met": total_items >= 2300}
        dup_rate = report["queue_stats"].get("duplicate_rate", 0.0)
        criteria["dedup_rate_lt_30pct"] = {"target": 0.30, "actual": dup_rate, "met": dup_rate < 0.30}
    report["exit_criteria"] = criteria

    # Write report
    output_path = PROJECT_ROOT / "outputs" / "collection_qa_report.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n" + "=" * 60)
    print("COLLECTION QA REPORT")
    print("=" * 60)
    print(json.dumps(report, indent=2))
    print(f"\nReport saved to: {output_path}")

    # Exit code 1 if any criteria unmet
    unmet = [k for k, v in criteria.items() if not v.get("met", True)]
    if unmet:
        print(f"\n[WARN] Exit criteria NOT met: {unmet}")
        sys.exit(1)
    else:
        print("\n[PASS] All Phase 1 exit criteria met.")

    conn.close()


if __name__ == "__main__":
    main()
