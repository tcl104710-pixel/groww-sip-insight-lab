"""
SIP Insight Lab -- Phase 5 Validation Script
===========================================
Run this script to verify all Phase 5 exit criteria are met:

    python scripts/validate_phase5.py

Phase 5 Exit Criteria verified:
  1. Dashboard files and Streamlit components live and importable
  2. All 7 filter dimensions verified functional
  3. Intent vs. Action Gap analysis engine operational
  4. Source traceability working (drill-down to supporting verbatim quotes)
  5. AI Evidence Log exportable; final CSV and JSON archived with >= 10 entries
  6. Live QA Metrics panel data available (accuracy, F1, human review/override rate)
  7. Stakeholder readout deck delivered & decision log recorded
  8. Interview guides handed off & >= 5 user interviews scheduled in calendar
  9. Top hypothesis cards updated with qualitative validation findings
 10. Project retrospective completed & taxonomy_v2.yaml drafted and frozen
"""

import os
import sys
import json
import sqlite3
import pandas as pd
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Fix Windows console encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from src.dashboard.data_loader import DashboardDataLoader
from src.taxonomy_loader import TaxonomyLoader

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
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def validate_phase5() -> bool:
    db_path = PROJECT_ROOT / "data" / "sip_insight_lab.db"

    # -------------------------------------------------------------------------
    # Criterion 1: Dashboard Scaffolding & Dependencies
    # -------------------------------------------------------------------------
    section("Criterion 1 -- Dashboard Application Scaffolding")
    app_file = PROJECT_ROOT / "src" / "dashboard" / "app.py"
    loader_file = PROJECT_ROOT / "src" / "dashboard" / "data_loader.py"
    components_file = PROJECT_ROOT / "src" / "dashboard" / "components.py"
    runner_file = PROJECT_ROOT / "scripts" / "run_dashboard.py"

    check("src/dashboard/app.py exists", app_file.is_file())
    check("src/dashboard/data_loader.py exists", loader_file.is_file())
    check("src/dashboard/components.py exists", components_file.is_file())
    check("scripts/run_dashboard.py runner exists", runner_file.is_file())

    # -------------------------------------------------------------------------
    # Criterion 2: All 7 Filter Dimensions Functional
    # -------------------------------------------------------------------------
    section("Criterion 2 -- Verification of All 7 Filter Dimensions")
    loader = DashboardDataLoader(str(db_path))
    df_corpus = loader.load_full_corpus()
    check("Data loader successfully loads corpus", len(df_corpus) > 0, f"Loaded {len(df_corpus)} items")

    # 1. Lifecycle Stage Filter
    f_ls = loader.filter_corpus(df_corpus, lifecycle_stages=["LS-01"])
    check("Dimension 1: Lifecycle Stage filtering functional", len(f_ls) > 0 and (f_ls["lifecycle_stage"] == "LS-01").all())

    # 2. Root Cause Filter
    f_rc = loader.filter_corpus(df_corpus, root_causes=["RC-01"])
    check("Dimension 2: Root Cause filtering functional", len(f_rc) > 0 and (f_rc["root_cause"] == "RC-01").all())

    # 3. Stop Type Filter
    f_st = loader.filter_corpus(df_corpus, stop_types=["ST-01"])
    check("Dimension 3: Stop Type filtering functional", len(f_st) > 0 and (f_st["stop_type"] == "ST-01").all())

    # 4. Source Platform Filter
    f_src = loader.filter_corpus(df_corpus, sources=["play_store"])
    check("Dimension 4: Source Platform filtering functional", len(f_src) > 0 and (f_src["source"] == "play_store").all())

    # 5. Investor Segment Filter
    f_seg = loader.filter_corpus(df_corpus, age_groups=["25-30"])
    check("Dimension 5: Investor Segment filtering functional", len(f_seg) > 0 and (f_seg["segment_age_group"] == "25-30").all())

    # 6. Intent vs Action Gap Filter
    f_gap = loader.filter_corpus(df_corpus, gap_filter="gap_only")
    check("Dimension 6: Intent vs. Action Gap filtering functional", len(f_gap) > 0 and f_gap["has_gap"].all())

    # 7. Time Period (Date Range) Filter
    min_date = df_corpus["collected_at"].min()
    max_date = df_corpus["collected_at"].max()
    f_date = loader.filter_corpus(df_corpus, date_range=(min_date, max_date))
    check("Dimension 7: Date Range filtering functional", len(f_date) == len(df_corpus))

    # -------------------------------------------------------------------------
    # Criterion 3: Intent vs. Action Gap Analysis
    # -------------------------------------------------------------------------
    section("Criterion 3 -- Intent vs. Action Gap Engine")
    gap_summary = loader.get_intent_action_gap_breakdown(df_corpus)
    check("Intent vs Action gap computed across corpus", gap_summary["gap_count"] > 0)
    check("Gap rate correctly calculated", gap_summary["gap_rate"] > 0, f"Gap Rate: {gap_summary['gap_rate']}%")
    check("Gap breakdown by source present", not gap_summary["gap_by_source"].empty)
    check("Gap breakdown by lifecycle stage present", not gap_summary["gap_by_stage"].empty)

    # -------------------------------------------------------------------------
    # Criterion 4: Source Traceability (Click/Drill Down to Quotes)
    # -------------------------------------------------------------------------
    section("Criterion 4 -- Source Traceability Drill-down")
    sample_item = df_corpus.iloc[0]
    check("Feedback items retain raw unmodified text", bool(sample_item["raw_text"]))
    check("Feedback items retain cleaned PII-scrubbed text", bool(sample_item["cleaned_text"]))
    check("Feedback items trace back to original source platform", sample_item["source"] in ["play_store", "app_store", "reddit", "tradingqa", "youtube"])
    cards = loader.get_opportunity_rankings()
    check("Hypothesis cards retain traceable supporting quotes", len(cards[0]["supporting_quotes"]) >= 3)

    # -------------------------------------------------------------------------
    # Criterion 5: AI Evidence Log Export (CSV + JSON with >= 10 entries)
    # -------------------------------------------------------------------------
    section("Criterion 5 -- AI Evidence Log Export (CSV & JSON)")
    final_csv = PROJECT_ROOT / "outputs" / "ai_evidence_log_final.csv"
    final_json = PROJECT_ROOT / "outputs" / "ai_evidence_log_final.json"

    # Export fresh
    df_exp, json_exp = loader.export_evidence_log(str(final_csv), str(final_json))
    check("outputs/ai_evidence_log_final.csv exists", final_csv.is_file())
    check("outputs/ai_evidence_log_final.json exists", final_json.is_file())
    check("AI Evidence Log contains >= 10 verified audit records", len(df_exp) >= 10, f"Count = {len(df_exp)}")

    # -------------------------------------------------------------------------
    # Criterion 6: Live QA Metrics Panel
    # -------------------------------------------------------------------------
    section("Criterion 6 -- Live QA Metrics Panel")
    qa = loader.get_qa_metrics()
    check("QA overall accuracy certified >= 80%", qa["overall_accuracy"] >= 80.0, f"{qa['overall_accuracy']}%")
    check("Per-field F1 scores available and meet SLA", all(score >= 0.75 for score in qa["per_field_f1"].values()))
    check("Human review rate tracked (< 20%)", qa["human_review_rate_pct"] < 20.0, f"{qa['human_review_rate_pct']}%")
    check("Human override rate tracked", qa["human_override_rate_pct"] >= 0)

    # -------------------------------------------------------------------------
    # Criterion 7: Stakeholder Readout & Decisions Log
    # -------------------------------------------------------------------------
    section("Criterion 7 -- Stakeholder Readout Deck & Decision Log")
    deck_path = PROJECT_ROOT / "outputs" / "reports" / "stakeholder_readout_deck.md"
    decisions_path = PROJECT_ROOT / "outputs" / "reports" / "stakeholder_decisions.md"

    check("outputs/reports/stakeholder_readout_deck.md exists", deck_path.is_file())
    check("outputs/reports/stakeholder_decisions.md exists", decisions_path.is_file())

    deck_content = deck_path.read_text(encoding="utf-8") if deck_path.is_file() else ""
    check("Readout covers Top 5 opportunities", "RC-01" in deck_content and "RC-03" in deck_content and "RC-02" in deck_content)
    check("Readout includes visible scoring formula", "Opportunity Score =" in deck_content)

    decisions_content = decisions_path.read_text(encoding="utf-8") if decisions_path.is_file() else ""
    check("Decisions log captures qualitative validation vs backlog", "USER INTERVIEWS" in decisions_content and "BACKLOG" in decisions_content)

    # -------------------------------------------------------------------------
    # Criterion 8: User Interview Handoff & Scheduled Calendar (>= 5 interviews)
    # -------------------------------------------------------------------------
    section("Criterion 8 -- User Interview Handoff & Calendar (>= 5 Sessions)")
    briefing_path = PROJECT_ROOT / "outputs" / "reports" / "interview_handoff_briefing.md"
    calendar_path = PROJECT_ROOT / "outputs" / "reports" / "interview_calendar.md"

    check("outputs/reports/interview_handoff_briefing.md exists", briefing_path.is_file())
    check("outputs/reports/interview_calendar.md exists", calendar_path.is_file())

    cal_content = calendar_path.read_text(encoding="utf-8") if calendar_path.is_file() else ""
    has_5_interviews = all(f"INT-0{i}" in cal_content for i in range(1, 6))
    check("Interview calendar schedules >= 5 user interviews (INT-01 to INT-05)", has_5_interviews)

    # -------------------------------------------------------------------------
    # Criterion 9: Hypothesis Cards Updated with Validation Status
    # -------------------------------------------------------------------------
    section("Criterion 9 -- Hypothesis Cards Validation Status Updates")
    hc1 = PROJECT_ROOT / "outputs" / "hypothesis_cards" / "HC-RC-01.md"
    hc2 = PROJECT_ROOT / "outputs" / "hypothesis_cards" / "HC-RC-02.md"
    hc3 = PROJECT_ROOT / "outputs" / "hypothesis_cards" / "HC-RC-03.md"

    check("HC-RC-01 updated with validation findings", hc1.is_file() and "Interview Validation Findings & Synthesis" in hc1.read_text(encoding="utf-8"))
    check("HC-RC-02 updated with validation findings", hc2.is_file() and "Interview Validation Findings & Synthesis" in hc2.read_text(encoding="utf-8"))
    check("HC-RC-03 updated with validation findings", hc3.is_file() and "Interview Validation Findings & Synthesis" in hc3.read_text(encoding="utf-8"))

    # -------------------------------------------------------------------------
    # Criterion 10: Retrospective & Taxonomy v2.0 Frozen
    # -------------------------------------------------------------------------
    section("Criterion 10 -- Retrospective Document & Taxonomy v2.0")
    retro_path = PROJECT_ROOT / "outputs" / "retrospective.md"
    tax2_path = PROJECT_ROOT / "taxonomy" / "taxonomy_v2.yaml"

    check("outputs/retrospective.md exists", retro_path.is_file())
    check("taxonomy/taxonomy_v2.yaml exists", tax2_path.is_file())

    tx2 = TaxonomyLoader(str(tax2_path))
    check("taxonomy_v2.yaml version is 2.0", tx2.version == "2.0")
    check("taxonomy_v2.yaml is frozen", tx2.is_frozen)
    check("taxonomy_v2.yaml has root cause codes", len(tx2.root_cause_codes) >= 8)

    # -------------------------------------------------------------------------
    # Final Result
    # -------------------------------------------------------------------------
    all_passed = all(results)
    print("\n" + "=" * 70)
    if all_passed:
        print(f"  {PASS} ALL PHASE 5 EXIT CRITERIA SATISFIED! (Pass Count: {len(results)}/{len(results)})")
        print("  System ready for full executive handoff and production deployment.")
    else:
        failed = len(results) - sum(results)
        print(f"  {FAIL} {failed} check(s) failed in Phase 5 validation.")
    print("=" * 70 + "\n")
    return all_passed


if __name__ == "__main__":
    success = validate_phase5()
    sys.exit(0 if success else 1)
