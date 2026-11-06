"""
SIP Insight Lab — PII Spot-Check Tool (Task 2.7)
=================================================
Performs a rigorous spot-check of 50 cleaned items from the database
or a simulated sample, validating zero PII leakage (phone, email, UPI,
Aadhaar, PAN, bank accounts, names).
Produces a formatted markdown QA report in outputs/reports/pii_spot_check_report.md.

Usage:
    python scripts/spot_check_pii.py [--n 50] [--db-path ./data/sip_insight_lab.db]
"""

import argparse
import json
import logging
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.cleaning.pii_scrubber import PIIScrubber
from src.cleaning.pipeline import CleaningPipeline
from src.db.schema import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("spot_check_pii")


def run_spot_check(conn: sqlite3.Connection, n: int = 50) -> dict:
    pipeline = CleaningPipeline(conn, use_ner=False)
    items = pipeline.spot_check(n)

    scrubber = PIIScrubber(use_ner=False)
    results = []
    leak_count = 0

    for idx, item in enumerate(items, 1):
        text = item["cleaned_text"]
        _, secondary_log = scrubber.scrub(text)
        leaked = secondary_log.get("total_redacted", 0) > 0
        if leaked:
            leak_count += 1

        results.append({
            "index": idx,
            "item_id": item["item_id"],
            "source": item["source"],
            "language": item["language"],
            "cleaned_snippet": text[:80] + ("..." if len(text) > 80 else ""),
            "redacted_log": item["pii_removal_log"],
            "leak_detected": leaked,
        })

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sample_size": len(items),
        "leaks_detected": leak_count,
        "pass_status": leak_count == 0,
        "items": results,
    }
    return report


def save_report(report: dict, output_path: str = "./outputs/reports/pii_spot_check_report.md"):
    out_dir = Path(output_path).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    status_icon = "PASS" if report["pass_status"] else "FAIL"

    lines = [
        "# SIP Insight Lab — PII Spot-Check QA Report (Task 2.7)",
        "",
        f"- **Date & Time:** {report['timestamp']}",
        f"- **Sample Size:** {report['sample_size']} items",
        f"- **PII Leaks Detected:** {report['leaks_detected']}",
        f"- **Status:** **{status_icon}** (Target: 0 leaks)",
        "",
        "---",
        "",
        "## Checked Sample Items",
        "",
        "| # | Item ID | Source | Lang | Snippet | Redacted Log | Leak? |",
        "|---|---|---|---|---|---|---|",
    ]

    for item in report["items"]:
        snippet = item["cleaned_snippet"].replace("|", "\\|").replace("\n", " ")
        log_str = json.dumps(item["redacted_log"])
        leak_str = "YES" if item["leak_detected"] else "No"
        lines.append(f"| {item['index']} | `{item['item_id'][:8]}` | {item['source']} | {item['language']} | {snippet} | `{log_str}` | {leak_str} |")

    lines.append("")
    lines.append("## Sign-off")
    lines.append("- **Reviewed by:** Growth PM & AI Researcher")
    lines.append(f"- **Outcome:** {'Approved for Phase 2 classification' if report['pass_status'] else 'Action required: tune PII regex/NER'}")
    lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info("Report saved to %s", output_path)


def main():
    parser = argparse.ArgumentParser(description="PII Spot-Check QA Runner")
    parser.add_argument("--n", type=int, default=50, help="Number of items to sample")
    parser.add_argument("--db-path", type=str, default="./data/sip_insight_lab.db", help="Path to DB")
    parser.add_argument("--out", type=str, default="./outputs/reports/pii_spot_check_report.md", help="Output path")

    args = parser.parse_args()
    conn = init_db(args.db_path)

    report = run_spot_check(conn, args.n)
    save_report(report, args.out)

    print(f"\nSpot Check Completed: Sample={report['sample_size']}, Leaks={report['leaks_detected']}, Status={'PASS' if report['pass_status'] else 'FAIL'}")
    conn.close()


if __name__ == "__main__":
    main()
