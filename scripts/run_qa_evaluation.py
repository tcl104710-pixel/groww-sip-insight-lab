"""
SIP Insight Lab — QA Evaluation Runner (Tasks 3.4, 3.5, 3.6)
=============================================================
Evaluates the Classification Engine against the Golden Set.
Generates comprehensive QA accuracy and F1 reports:
  - Task 3.4: outputs/qa_report_v1.md (Evaluation on prompt v1)
  - Task 3.6: outputs/qa_report_v2.md (Evaluation on refined prompt v2)

Targets:
  - Overall Exact Match Accuracy: ≥ 80%
  - Per-field F1 Score: ≥ 0.75 across all taxonomy fields

Usage:
    python scripts/run_qa_evaluation.py --prompt-version v1 --out outputs/qa_report_v1.md
    python scripts/run_qa_evaluation.py --prompt-version v2 --out outputs/qa_report_v2.md
"""

import argparse
import logging
import os
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.classification.engine import ClassificationEngine
from src.classification.llm_client import LLMClient
from src.db.schema import init_db
from src.qa.comparator import QAComparator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("run_qa_evaluation")


def run_qa_evaluation(
    conn: sqlite3.Connection,
    prompt_version: str = "v1",
    output_report_path: str = "./outputs/qa_report_v1.md",
) -> dict:
    comparator = QAComparator(conn, target_overall_accuracy=0.80, target_field_f1=0.75)
    golden_set = comparator.load_golden_set_from_db()

    logger.info("Evaluating QA on %d golden set items using prompt version '%s'...", len(golden_set), prompt_version)

    engine = ClassificationEngine(
        conn=conn,
        llm_client=LLMClient(),
        prompt_version=prompt_version,
    )

    predictions = {}
    for item_id, (text, y_true) in golden_set.items():
        res = engine.classify_single(
            item_id=item_id,
            cleaned_text=text,
            source="golden_set",
            star_rating=None,
            save_to_db=False,
        )
        predictions[item_id] = res["parsed"]

    qa_result = comparator.evaluate(predictions, golden_set=golden_set, prompt_version=prompt_version)

    report_md = comparator.generate_report_markdown(
        qa_result, title=f"Quality Assurance Report ({prompt_version.upper()})"
    )

    out_file = Path(output_report_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(report_md, encoding="utf-8")
    logger.info("QA report saved to: %s", output_report_path)

    return {
        "result": qa_result,
        "summary": qa_result.summary(),
        "report_path": str(out_file),
    }


def main():
    parser = argparse.ArgumentParser(description="Run QA Golden Set Evaluation")
    parser.add_argument("--prompt-version", type=str, default="v2", choices=["v1", "v2"], help="Prompt version to test")
    parser.add_argument("--out", type=str, default=None, help="Output markdown report path")
    parser.add_argument("--db-path", type=str, default="./data/sip_insight_lab.db", help="Path to DB")

    args = parser.parse_args()

    default_out = f"./outputs/qa_report_{args.prompt_version}.md"
    out_path = args.out or default_out

    conn = init_db(args.db_path)
    evaluation_info = run_qa_evaluation(conn, prompt_version=args.prompt_version, output_report_path=out_path)

    res = evaluation_info["result"]
    summary = evaluation_info["summary"]

    print("\n" + "=" * 65)
    print(f"SIP Insight Lab — QA Golden Set Evaluation ({args.prompt_version.upper()})")
    print("=" * 65)
    print(f"Total Golden Items Evaluated : {res.total_golden_items}")
    print(f"Overall Exact-Match Accuracy : {summary['overall_accuracy'] * 100:.1f}% "
          f"(Target: ≥ 80% — {'[PASS]' if summary['meets_overall_target'] else '[FAIL]'})")
    print("\nPer-Field Weighted F1 Scores:")
    for f, f1 in summary["field_f1_scores"].items():
        status = "[PASS]" if f1 >= 0.75 else "[FAIL]"
        print(f"  - {f:<18} : {f1:.3f} (Target: ≥ 0.75) {status}")

    print(f"\nAll Fields Meet Target (≥0.75): {'YES [PASS]' if summary['all_fields_meet_target'] else 'NO [FAIL]'}")
    print(f"Mismatches / Errors Count    : {summary['error_count']}")
    print(f"Full Report Saved To         : {evaluation_info['report_path']}")
    print("=" * 65 + "\n")

    conn.close()


if __name__ == "__main__":
    main()
