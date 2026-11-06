"""
SIP Insight Lab — Phase 2 Cleaning Orchestrator (Task 2.6 & 2.7)
================================================================
Runs the cleaning pipeline across raw feedback items and writes
to the cleaned_item table.

Usage:
    python scripts/run_cleaning.py [--limit N] [--reprocess] [--spot-check]

Flags:
    --limit N       : Max raw items to process (default: all unprocessed)
    --reprocess     : Re-process already cleaned items
    --spot-check    : Run a 50-item spot-check after cleaning
    --no-ner        : Disable spaCy NER and use regex-only PII scrubber
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.db.schema import init_db
from src.cleaning.pipeline import CleaningPipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_cleaning")


def main():
    parser = argparse.ArgumentParser(description="Run cleaning pipeline on raw feedback items.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of items to clean")
    parser.add_argument("--reprocess", action="store_true", help="Re-clean already processed items")
    parser.add_argument("--spot-check", action="store_true", help="Run 50-item PII spot-check afterwards")
    parser.add_argument("--no-ner", action="store_true", help="Force regex-only PII scrubber")
    parser.add_argument("--db-path", type=str, default="./data/sip_insight_lab.db", help="Path to DB")

    args = parser.parse_args()

    conn = init_db(args.db_path)
    pipeline = CleaningPipeline(
        conn=conn,
        use_ner=not args.no_ner,
        reprocess=args.reprocess,
    )

    logger.info("Starting cleaning pipeline...")
    stats = pipeline.run()

    print("\n" + "=" * 55)
    print("SIP Insight Lab — Cleaning Pipeline Summary")
    print("=" * 55)
    print(f"Total raw items examined : {stats['total_raw']}")
    print(f"Cleaned and saved to DB  : {stats['cleaned_and_written']}")
    print(f"Rejected (non-EN/HI lang): {stats['lang_rejected']}")
    print(f"Rejected (too short text): {stats['too_short_after_clean']}")
    print(f"PII entities redacted    : {stats['pii_total_redacted']}")
    print(f"Errors encountered       : {stats['errors']}")
    print("=" * 55)

    if args.spot_check or stats['cleaned_and_written'] > 0:
        sample = pipeline.spot_check(50)
        print(f"\nSpot-check sample size: {len(sample)} items")
        pii_leaks = 0
        for item in sample:
            # Check for leaked unredacted phone or email or upi
            text = item["cleaned_text"]
            if pipeline._pii_scrubber.has_pii(text):
                # Text still has identifiable PII that wasn't redacted
                pii_leaks += 1

        print(f"Potential PII leak rate: {pii_leaks} / {len(sample)} (Target: 0)")
        if pii_leaks == 0:
            print("[PASS] PII Spot-Check PASSED: 0 leaks detected.")
        else:
            print(f"[WARN] PII Spot-Check WARNING: {pii_leaks} potential leaks detected.")

    conn.close()


if __name__ == "__main__":
    main()
