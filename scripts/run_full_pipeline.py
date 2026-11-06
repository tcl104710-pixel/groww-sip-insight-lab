"""
Groww SIP Insight Lab — End-to-End Pipeline Orchestrator
========================================================
Executes the full research pipeline sequentially:
1. Multi-source collection (Play Store, App Store, Reddit, YouTube)
2. Cleaning, normalization, and deduplication (sip_feedback_combined.csv)
3. SIP relevance filtering (sip_feedback_relevant.csv)
4. AI-powered classification (sip_feedback_classified.csv)
5. Research insights synthesis (sip_insights_report.md)
6. Deliverables packaging (summary report, evidence log)
"""

import os
import sys
import time
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("orchestrator")


def run_collection(skip_if_exists: bool = False):
    """Executes or verifies raw collection across all 4 sources."""
    logger.info("=" * 70)
    logger.info("STAGE 1: MULTI-SOURCE FEEDBACK COLLECTION")
    logger.info("=" * 70)

    from src.pipeline.collector_play_store import collect_play_store_reviews, RAW_OUTPUT_PATH as PS_PATH
    from src.pipeline.collector_app_store import collect_app_store_reviews, RAW_OUTPUT_PATH as AS_PATH
    from src.pipeline.collector_youtube import collect_youtube_comments, RAW_OUTPUT_PATH as YT_PATH
    from src.pipeline.collector_reddit import collect_reddit_discussions, RAW_OUTPUT_PATH as RD_PATH

    # Play Store
    if skip_if_exists and PS_PATH.exists() and PS_PATH.stat().st_size > 500:
        logger.info("Play Store raw file already exists (%d bytes). Skipping re-fetch.", PS_PATH.stat().st_size)
    else:
        logger.info("Collecting Google Play Store reviews (up to 3,000)...")
        try:
            collect_play_store_reviews(max_reviews=3000)
        except Exception as e:
            logger.error("Play Store collection error: %s", e)

    # App Store
    if skip_if_exists and AS_PATH.exists() and AS_PATH.stat().st_size > 500:
        logger.info("App Store raw file already exists (%d bytes). Skipping re-fetch.", AS_PATH.stat().st_size)
    else:
        logger.info("Collecting Apple App Store reviews...")
        try:
            collect_app_store_reviews(max_pages=10)
        except Exception as e:
            logger.error("App Store collection error: %s", e)

    # YouTube
    if skip_if_exists and YT_PATH.exists() and YT_PATH.stat().st_size > 500:
        logger.info("YouTube raw file already exists (%d bytes). Skipping re-fetch.", YT_PATH.stat().st_size)
    else:
        logger.info("Collecting YouTube comments...")
        try:
            collect_youtube_comments(max_videos_per_query=6, max_comments_per_video=120)
        except Exception as e:
            logger.error("YouTube collection error: %s", e)

    # Reddit
    if skip_if_exists and RD_PATH.exists() and RD_PATH.stat().st_size > 500:
        logger.info("Reddit raw file already exists (%d bytes). Skipping re-fetch.", RD_PATH.stat().st_size)
    else:
        logger.info("Collecting Reddit discussions...")
        try:
            collect_reddit_discussions()
        except Exception as e:
            logger.error("Reddit collection error: %s", e)


def run_pipeline():
    """Executes stages 2 through 6 using collected raw files."""
    from src.pipeline.cleaner import clean_and_combine_data
    from src.pipeline.filter_sip import filter_sip_feedback
    from src.pipeline.classifier import classify_feedback_dataset
    from src.pipeline.insights_generator import (
        generate_evidence_log,
        generate_data_collection_cleaning_summary,
        generate_research_insights_report,
    )

    # STAGE 2: Cleaning & Combining
    logger.info("=" * 70)
    logger.info("STAGE 2: CLEANING & NORMALIZATION")
    logger.info("=" * 70)
    df_combined, cleaning_stats = clean_and_combine_data()
    logger.info("Cleaned & combined %d total unique records.", len(df_combined))

    # STAGE 3: SIP Relevance Filtering
    logger.info("=" * 70)
    logger.info("STAGE 3: SIP RELEVANCE FILTERING")
    logger.info("=" * 70)
    df_relevant, df_irrelevant, rel_stats = filter_sip_feedback(df_combined)
    logger.info("Filtered %d relevant SIP records (%.1f%%).", len(df_relevant), rel_stats["relevant_pct"])

    # STAGE 4: AI Classification
    logger.info("=" * 70)
    logger.info("STAGE 4: AI-POWERED MULTI-DIMENSIONAL CLASSIFICATION")
    logger.info("=" * 70)
    df_classified = classify_feedback_dataset(df_relevant, sample_llm_limit=25)
    logger.info("Successfully classified %d records.", len(df_classified))

    # STAGE 5 & 6: Research Insights & Deliverables
    logger.info("=" * 70)
    logger.info("STAGE 5 & 6: INSIGHTS GENERATION & DELIVERABLES")
    logger.info("=" * 70)
    evidence_csv, evidence_jsonl = generate_evidence_log(df_classified)
    summary_path = generate_data_collection_cleaning_summary(cleaning_stats, df_combined, df_relevant)
    report_path = generate_research_insights_report(df_classified)

    # Deliverables synchronization
    import shutil
    shutil.copy(evidence_csv, PROJECT_ROOT / "sip_evidence_log.csv")
    
    from scripts.bundle_research_data import bundle_data
    bundle_data()

    for f in ["sip_opportunity_matrix.csv", "sip_evidence_log.csv", "sip_insights_report.md", "sip_feedback_combined.csv", "sip_feedback_classified.csv"]:
        src = PROJECT_ROOT / f
        if src.exists():
            shutil.copy(src, PROJECT_ROOT / "public" / f)

    logger.info("=" * 70)
    logger.info("PIPELINE COMPLETED SUCCESSFULLY!")
    logger.info("=" * 70)
    print("\n--- DELIVERABLES PRODUCED ---")
    print(f"1. Cleaned Combined CSV:      {PROJECT_ROOT / 'sip_feedback_combined.csv'}")
    print(f"2. SIP Relevant CSV:          {PROJECT_ROOT / 'sip_feedback_relevant.csv'}")
    print(f"3. Classified Feedback CSV:   {PROJECT_ROOT / 'sip_feedback_classified.csv'}")
    print(f"4. Research Insights Report:  {report_path}")
    print(f"5. Collection Summary:        {summary_path}")
    print(f"6. Evidence Log (CSV):        {evidence_csv}")
    print(f"7. Evidence Log (JSONL):      {evidence_jsonl}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Groww SIP Insight Lab Pipeline")
    parser.add_argument("--collect", action="store_true", help="Force re-collection of raw sources")
    parser.add_argument("--skip-collection-if-exists", action="store_true", default=True, help="Skip collection if raw data exists")
    args = parser.parse_args()

    if args.collect:
        run_collection(skip_if_exists=False)
    else:
        run_collection(skip_if_exists=True)

    run_pipeline()

