"""
SIP Insight Lab — Counter-Evidence Agent Runner (Task 3.13)
===========================================================
Executes the Counter-Evidence Agent across top 5 preliminary themes
to actively uncover contradicting evidence and stress-test assumptions.

Outputs:
  - outputs/reports/counter_evidence_review.md

Usage:
    python scripts/run_counter_evidence.py [--out outputs/reports/counter_evidence_review.md]
"""

import argparse
import logging
import os
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.counter_evidence import CounterEvidenceAgent
from src.agents.ce_formatter import CounterEvidenceFormatter
from src.db.schema import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("run_counter_evidence")

TOP_5_PRELIMINARY_THEMES = [
    {
        "theme": "Bank mandate failures and silent 3-strike auto-cancellations are the primary driver of involuntary early SIP churn.",
        "root_cause": "RC-01",
        "lifecycle_stage": "LS-01",
    },
    {
        "theme": "Confusing app interface and payment gateway drop-offs prevent investors from modifying or pausing their SIPs.",
        "root_cause": "RC-02",
        "lifecycle_stage": None,
    },
    {
        "theme": "Return disappointment and calculator mismatch cause investors to prematurely abandon SIPs within the first 3–6 months.",
        "root_cause": "RC-03",
        "lifecycle_stage": "LS-02",
    },
    {
        "theme": "Job loss and sudden salary reductions are the sole reason investors pause or cancel active SIPs during their journey.",
        "root_cause": "RC-04",
        "lifecycle_stage": None,
    },
    {
        "theme": "Investors misinterpret normal market NAV drawdowns as application fraud or money theft, leading to panic exits.",
        "root_cause": "RC-06",
        "lifecycle_stage": "LS-01",
    },
]


def run_counter_evidence_analysis(
    conn: sqlite3.Connection,
    output_path: str = "./outputs/reports/counter_evidence_review.md",
) -> list:
    agent = CounterEvidenceAgent(conn)
    formatter = CounterEvidenceFormatter()

    analyses = []
    logger.info("Running Counter-Evidence Agent on %d preliminary themes...", len(TOP_5_PRELIMINARY_THEMES))

    for t_spec in TOP_5_PRELIMINARY_THEMES:
        analysis = agent.analyze_theme(
            theme=t_spec["theme"],
            root_cause=t_spec["root_cause"],
            lifecycle_stage=t_spec.get("lifecycle_stage"),
        )
        analyses.append(analysis)

    report_md = formatter.format_full_review_document(analyses)

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(report_md, encoding="utf-8")
    logger.info("Counter-evidence review document saved to: %s", output_path)

    return analyses


def main():
    parser = argparse.ArgumentParser(description="Run Counter-Evidence Agent on Top 5 Themes")
    parser.add_argument("--out", type=str, default="./outputs/reports/counter_evidence_review.md", help="Output report path")
    parser.add_argument("--db-path", type=str, default="./data/sip_insight_lab.db", help="Path to DB")

    args = parser.parse_args()
    conn = init_db(args.db_path)

    analyses = run_counter_evidence_analysis(conn, output_path=args.out)

    print("\n" + "=" * 70)
    print("SIP Insight Lab — Counter-Evidence Agent Stress-Test Results")
    print("=" * 70)
    for idx, a in enumerate(analyses, 1):
        print(f"\n[{idx}] Theme: \"{a.theme[:60]}...\"")
        print(f"    Target Root Cause        : {a.root_cause}")
        print(f"    Counter-Evidence Strength: {a.counter_evidence_strength}")
        print(f"    Revised Confidence       : {a.revised_confidence}")
        print(f"    Recommendation           : {a.recommendation}")

    print("\n" + "=" * 70)
    print(f"Tested {len(analyses)} themes against 4 adversarial strategies.")
    print(f"Full Review Document: {args.out}")
    print("=" * 70 + "\n")

    conn.close()


if __name__ == "__main__":
    main()
