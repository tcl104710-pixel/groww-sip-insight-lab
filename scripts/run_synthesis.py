"""
SIP Insight Lab — Run Phase 4 Synthesis & Hypothesis Engine
===========================================================
Executes the Phase 4 synthesis pipeline end-to-end:
  1. Aggregates labelled store by root_cause and lifecycle stage
  2. Calculates visible Opportunity Score across all buckets
  3. Outputs ranked opportunity list to `outputs/reports/opportunity_ranking.md`
  4. Generates standard hypothesis cards with interview guides
  5. Enforces ethical Nudge Checklist (zero tolerance for advice or FOMO)
  6. Writes hypothesis cards to SQLite DB and `outputs/hypothesis_cards/`
  7. Outputs compliance review log to `outputs/reports/nudge_checklist_review.md`

Usage:
  python scripts/run_synthesis.py
"""

import os
import sys
import argparse
import sqlite3
import logging
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.db.schema import init_db
from src.synthesis.aggregator import FeedbackAggregator
from src.synthesis.ranker import OpportunityRanker
from src.synthesis.card_generator import HypothesisCardGenerator
from src.synthesis.nudge_checker import NudgeChecker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("run_synthesis")


def run_synthesis(
    db_path: str = "./data/sip_insight_lab.db",
    ranking_report_path: str = "./outputs/reports/opportunity_ranking.md",
    nudge_report_path: str = "./outputs/reports/nudge_checklist_review.md",
    cards_dir: str = "./outputs/hypothesis_cards",
) -> dict:
    conn = init_db(db_path)

    # 1. Feedback Aggregation
    logger.info("Step 1: Aggregating feedback items across root causes...")
    aggregator = FeedbackAggregator(conn)
    items = aggregator.load_items()
    buckets = aggregator.aggregate_by_root_cause(items)
    gap_analysis = aggregator.compute_intent_action_gap(items)

    logger.info(
        "Loaded %d items across %d root cause buckets. Involuntary Gap Rate: %.1f%%",
        len(items),
        len(buckets),
        gap_analysis["involuntary_gap_rate"] * 100,
    )

    # 2. Opportunity Ranking
    logger.info("Step 2: Scoring and ranking opportunities...")
    ranker = OpportunityRanker()
    ranked = ranker.rank_buckets(buckets=buckets, total_corpus=len(items))

    # Save Ranking Report Markdown
    ranking_file = Path(ranking_report_path)
    ranking_file.parent.mkdir(parents=True, exist_ok=True)
    report_md = ranker.generate_ranking_report_markdown(ranked)
    ranking_file.write_text(report_md, encoding="utf-8")
    logger.info("Saved opportunity ranking report to: %s", ranking_report_path)

    # 3. Hypothesis Card Generation & Persistence
    logger.info("Step 3: Generating hypothesis cards with interview guides & counter-evidence...")
    nudge_checker = NudgeChecker()
    card_gen = HypothesisCardGenerator(
        conn=conn,
        nudge_checker=nudge_checker,
        output_dir=cards_dir,
    )

    batch_res = card_gen.generate_all(ranked)
    logger.info("Generated %d hypothesis cards in %s", batch_res["total_generated"], cards_dir)

    # 4. Save Nudge Review Audit Log
    nudge_file = Path(nudge_report_path)
    nudge_file.parent.mkdir(parents=True, exist_ok=True)
    nudge_md = nudge_checker.generate_review_report_markdown(batch_res["nudge_results"])
    nudge_file.write_text(nudge_md, encoding="utf-8")
    logger.info("Saved nudge checklist audit log to: %s", nudge_report_path)

    conn.close()

    return {
        "total_items": len(items),
        "total_buckets": len(buckets),
        "ranked_opportunities": ranked,
        "cards": batch_res["cards"],
        "nudge_results": batch_res["nudge_results"],
        "ranking_report_path": str(ranking_file),
        "nudge_report_path": str(nudge_file),
        "cards_dir": cards_dir,
        "gap_analysis": gap_analysis,
    }


def main():
    parser = argparse.ArgumentParser(description="Run Phase 4 Synthesis & Hypothesis Engine")
    parser.add_argument("--db-path", type=str, default="./data/sip_insight_lab.db", help="Path to DB")
    parser.add_argument("--ranking-out", type=str, default="./outputs/reports/opportunity_ranking.md", help="Ranking output path")
    parser.add_argument("--nudge-out", type=str, default="./outputs/reports/nudge_checklist_review.md", help="Nudge review output path")
    parser.add_argument("--cards-dir", type=str, default="./outputs/hypothesis_cards", help="Hypothesis cards directory")

    args = parser.parse_args()

    results = run_synthesis(
        db_path=args.db_path,
        ranking_report_path=args.ranking_out,
        nudge_report_path=args.nudge_out,
        cards_dir=args.cards_dir,
    )

    print("\n" + "=" * 70)
    print("SIP Insight Lab — Phase 4 Synthesis & Hypothesis Engine Summary")
    print("=" * 70)
    print(f"Total Corpus Feedback Analyzed : {results['total_items']} items")
    print(f"Root Cause Buckets Evaluated   : {results['total_buckets']}")
    print(f"Intent vs. Action Gap Rate     : {results['gap_analysis']['involuntary_gap_rate'] * 100:.1f}%\n")

    print("Ranked Priority Opportunities:")
    print(f"{'Rank':<5} {'Code':<8} {'Opportunity Focus':<38} {'Opp Score':<10} {'Confidence':<10}")
    print("-" * 75)
    for opp in results["ranked_opportunities"]:
        print(f"#{opp.rank:<4} {opp.root_cause:<8} {opp.opportunity_label[:36]:<38} {opp.opportunity_score:<10.3f} {opp.confidence_level:<10}")

    print("\n" + "-" * 75)
    cards_count = len(results["cards"])
    all_nudge_passed = all(r.passed for r in results["nudge_results"])
    print(f"Hypothesis Cards Generated   : {cards_count} (Saved to {results['cards_dir']})")
    print(f"All Passed Nudge Checklist   : {'YES [PASS]' if all_nudge_passed else 'NO [FLAGGED]'}")
    print(f"Opportunity Ranking Report   : {results['ranking_report_path']}")
    print(f"Nudge Compliance Audit Log   : {results['nudge_report_path']}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
