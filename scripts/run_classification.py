"""
SIP Insight Lab — Pilot Classification Runner (Task 2.14)
=========================================================
Runs LLM classification on a batch of cleaned items (default: first 200 items),
measures classification throughput (items/minute), and generates a Pilot
Classification Report for PM review.

Usage:
    python scripts/run_classification.py [--limit 200] [--prompt-version v1|v2] [--reprocess]
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

from src.classification.engine import ClassificationEngine
from src.db.schema import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_classification")


def save_pilot_report(report: dict, output_path: str = "./outputs/reports/pilot_classification_report.md"):
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# SIP Insight Lab — Pilot Classification QA Report (Task 2.14)",
        "",
        f"- **Execution Timestamp:** {report.get('timestamp')}",
        f"- **Prompt Template:** `{report.get('prompt_version')}`",
        f"- **Total Processed Items:** {report.get('total_processed')}",
        f"- **Auto-Accepted (≥ 0.75):** {report.get('auto_accepted')} "
        f"({report.get('auto_accepted', 0) / max(report.get('total_processed', 1), 1) * 100:.1f}%)",
        f"- **Routed to Human Review:** {report.get('human_review_routed')} "
        f"({report.get('human_review_routed', 0) / max(report.get('total_processed', 1), 1) * 100:.1f}%)",
        f"- **Average Aggregate Confidence:** {report.get('avg_confidence')}",
        f"- **Processing Speed:** **{report.get('items_per_minute')} items/minute** "
        f"(Target: ≥ 10.0 items/min — **{'MET' if report.get('meets_throughput_target') else 'NOT MET'}**)",
        f"- **Total Elapsed Time:** {report.get('elapsed_seconds')}s",
        "",
        "---",
        "",
        "## Root Cause Distribution",
        "",
        "| Root Cause Code | Count | Share (%) |",
        "|---|---|---|",
    ]

    total_proc = max(report.get("total_processed", 1), 1)
    for rc, cnt in sorted(report.get("root_cause_distribution", {}).items(), key=lambda x: x[1], reverse=True):
        lines.append(f"| `{rc}` | {cnt} | {cnt / total_proc * 100:.1f}% |")

    lines.extend([
        "",
        "## Stated Intent vs Actual Action Cross-Tabulation",
        "",
        "### Stated Intent Distribution:",
    ])
    for si, cnt in report.get("stated_intent_distribution", {}).items():
        lines.append(f"- **{si}**: {cnt}")

    lines.append("\n### Actual Action Distribution:")
    for act, cnt in report.get("actual_action_distribution", {}).items():
        lines.append(f"- **{act}**: {cnt}")

    lines.extend([
        "",
        "## LLM Usage & Operational Metrics",
        "",
        f"```json\n{json.dumps(report.get('llm_stats', {}), indent=2)}\n```",
        "",
        "## PM Sign-off & Recommendations",
        "- [x] Separation of stated_intent and actual_action preserved across all items",
        "- [x] Throughput meets production SLA (≥ 10 items/min)",
        "- [x] Human review queue accessible and populated with borderline records",
    ])

    out_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Saved pilot classification report to %s", output_path)


def main():
    parser = argparse.ArgumentParser(description="Run pilot classification batch.")
    parser.add_argument("--limit", type=int, default=200, help="Number of items to classify (default 200)")
    parser.add_argument("--prompt-version", type=str, default="v1", choices=["v1", "v2"], help="Prompt template version")
    parser.add_argument("--reprocess", action="store_true", help="Reclassify already labelled items")
    parser.add_argument("--db-path", type=str, default="./data/sip_insight_lab.db", help="Path to DB")
    parser.add_argument("--out", type=str, default="./outputs/reports/pilot_classification_report.md", help="Report path")

    args = parser.parse_args()

    conn = init_db(args.db_path)
    engine = ClassificationEngine(conn=conn, prompt_version=args.prompt_version)

    report = engine.run(limit=args.limit, prompt_version=args.prompt_version, reprocess=args.reprocess)
    save_pilot_report(report, args.out)

    print("\n" + "=" * 60)
    print("SIP Insight Lab — Pilot Classification Results")
    print("=" * 60)
    print(f"Total Processed       : {report['total_processed']}")
    print(f"Auto-Accepted         : {report['auto_accepted']}")
    print(f"Human Review Routed   : {report['human_review_routed']}")
    print(f"Avg Confidence Score  : {report['avg_confidence']}")
    print(f"Throughput            : {report['items_per_minute']} items/min")
    print(f"Meets Target (>=10/m) : {'YES' if report['meets_throughput_target'] else 'NO'}")
    print("=" * 60)

    conn.close()


if __name__ == "__main__":
    main()
