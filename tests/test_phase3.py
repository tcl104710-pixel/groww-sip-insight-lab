"""
SIP Insight Lab — Unit and Integration Tests: Phase 3 (Tasks 3.1–3.13)
======================================================================
Tests for:
  - Golden set curation & dual-labelling (Tasks 3.1 & 3.2)
  - QA Comparator: exact accuracy, F1, confusion matrix, errors (Task 3.3)
  - QA Evaluation reports v1 and v2 (Tasks 3.4, 3.5, 3.6)
  - AI Evidence Log: DB and JSONL append-only persistence (Task 3.7)
  - Human review processor and CSV template export (Tasks 3.8 & 3.9)
  - Counter-evidence prompt & 4 adversarial strategies (Tasks 3.10 & 3.11)
  - Counter-evidence formatter and review doc (Tasks 3.12 & 3.13)
  - Complete Phase 3 Exit Criteria verification

Run:
    python -m pytest tests/test_phase3.py -v
"""

import json
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.counter_evidence import CounterEvidenceAgent, CounterEvidenceAnalysis
from src.agents.ce_formatter import CounterEvidenceFormatter
from src.db.schema import init_db
from src.qa.comparator import QAComparator, EVALUATED_FIELDS
from src.qa.evidence_log import EvidenceLogWriter
from scripts.human_review_tool import HumanReviewProcessor


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def in_memory_db():
    conn = init_db(":memory:")
    yield conn
    conn.close()


@pytest.fixture
def seeded_db():
    """Provides in-memory DB seeded with test raw, cleaned, labelled, and golden set items."""
    conn = init_db(":memory:")
    # Seed sample raw and cleaned item
    conn.execute(
        "INSERT INTO raw_item (item_id, source, source_id, raw_text, dedup_hash, collected_at) VALUES ('item_01', 'play_store', 'src_01', 'My mandate failed 3 times', 'hash_01', datetime('now'))"
    )
    conn.execute(
        "INSERT INTO cleaned_item (item_id, cleaned_text, language, cleaning_version, cleaned_at) VALUES ('item_01', 'My mandate failed 3 times', 'en', '1.0', datetime('now'))"
    )
    conn.execute(
        """
        INSERT INTO labelled_item (
            item_id, taxonomy_version, lifecycle_stage, stated_intent, actual_action,
            stop_type, root_cause, sentiment_score, confidence_score, field_confidences,
            review_status, classified_at
        ) VALUES (
            'item_01', '1.0', 'LS-01', 'unknown', 'cancelled', 'ST-01', 'RC-01',
            -0.8, 0.92, '{"root_cause": 0.92}', 'auto', datetime('now')
        )
        """
    )
    # Seed review queue item
    conn.execute(
        "INSERT INTO human_review_queue (queue_id, item_id, reason, confidence_score, status, created_at) VALUES ('q_01', 'item_01', 'low_confidence', 0.65, 'pending', datetime('now'))"
    )
    # Seed golden set item
    conn.execute(
        """
        INSERT INTO golden_set (golden_id, item_id, human_labels, labeller_id, labelled_at, reconciliation_note)
        VALUES ('g_01', 'item_01', '{"root_cause": "RC-01", "stop_type": "ST-01", "lifecycle_stage": "LS-01", "stated_intent": "unknown", "actual_action": "cancelled"}', 'reviewer_01', datetime('now'), 'Consensus')
        """
    )
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Tasks 3.1 & 3.2 — Golden Set Validation
# ---------------------------------------------------------------------------

class TestGoldenSet:

    def test_csv_files_exist_and_meet_minimum_size(self):
        items_csv = PROJECT_ROOT / "golden_set" / "items.csv"
        labels_csv = PROJECT_ROOT / "golden_set" / "labels.csv"

        assert items_csv.exists(), "items.csv missing"
        assert labels_csv.exists(), "labels.csv missing"

        import csv
        with open(items_csv, "r", encoding="utf-8") as f:
            items = list(csv.DictReader(f))
        assert len(items) >= 20, f"Expected ≥ 20 golden items, got {len(items)}"

        with open(labels_csv, "r", encoding="utf-8") as f:
            labels = list(csv.DictReader(f))
        assert len(labels) == len(items), "items.csv and labels.csv row count mismatch"

    def test_dual_annotations_and_reconciled_structure(self):
        labels_csv = PROJECT_ROOT / "golden_set" / "labels.csv"
        import csv
        with open(labels_csv, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        for row in rows:
            assert row["golden_id"]
            assert row["item_id"]
            l1 = json.loads(row["labeller_1_labels"])
            l2 = json.loads(row["labeller_2_labels"])
            rec = json.loads(row["reconciled_labels"])

            assert "root_cause" in l1 and "root_cause" in l2
            assert "root_cause" in rec and "stop_type" in rec and "lifecycle_stage" in rec


# ---------------------------------------------------------------------------
# Task 3.3 — QA Comparator
# ---------------------------------------------------------------------------

class TestQAComparator:

    def test_perfect_match_metrics(self):
        comparator = QAComparator(target_overall_accuracy=0.80, target_field_f1=0.75)
        golden = {
            "item_1": ("Text 1", {"root_cause": "RC-01", "stop_type": "ST-01", "lifecycle_stage": "LS-01", "stated_intent": "stop", "actual_action": "cancelled"}),
            "item_2": ("Text 2", {"root_cause": "RC-02", "stop_type": "ST-02", "lifecycle_stage": "LS-02", "stated_intent": "pause", "actual_action": "paused"}),
        }
        # Predictions identical to golden set
        preds = {
            "item_1": {"root_cause": "RC-01", "stop_type": "ST-01", "lifecycle_stage": "LS-01", "stated_intent": "stop", "actual_action": "cancelled", "confidence_score": 0.95},
            "item_2": {"root_cause": "RC-02", "stop_type": "ST-02", "lifecycle_stage": "LS-02", "stated_intent": "pause", "actual_action": "paused", "confidence_score": 0.90},
        }

        res = comparator.evaluate(preds, golden_set=golden)
        assert res.exact_match_accuracy == 1.0
        assert res.meets_overall_target is True
        assert res.all_fields_meet_target is True
        assert len(res.errors) == 0

    def test_mismatch_metrics_and_error_diagnosis(self):
        comparator = QAComparator(target_overall_accuracy=0.80, target_field_f1=0.75)
        golden = {
            "item_1": ("Mandate failed", {"root_cause": "RC-01", "stop_type": "ST-01", "lifecycle_stage": "LS-01", "stated_intent": "continue", "actual_action": "cancelled"}),
        }
        preds = {
            "item_1": {"root_cause": "RC-02", "stop_type": "ST-02", "lifecycle_stage": "LS-01", "stated_intent": "stop", "actual_action": "cancelled", "confidence_score": 0.65},
        }
        res = comparator.evaluate(preds, golden_set=golden)
        assert res.exact_match_accuracy == 0.0
        assert res.meets_overall_target is False
        assert len(res.errors) >= 1
        # Root cause mismatch diagnosed
        rc_err = next(e for e in res.errors if e.field_name == "root_cause")
        assert rc_err.ground_truth == "RC-01"
        assert rc_err.predicted == "RC-02"
        assert "Mandate" in rc_err.possible_cause or "confused" in rc_err.possible_cause

    def test_generate_report_markdown(self):
        comparator = QAComparator()
        golden = {
            "item_1": ("Sample", {"root_cause": "RC-01", "stop_type": "ST-01", "lifecycle_stage": "LS-01", "stated_intent": "stop", "actual_action": "cancelled"}),
        }
        preds = {
            "item_1": {"root_cause": "RC-01", "stop_type": "ST-01", "lifecycle_stage": "LS-01", "stated_intent": "stop", "actual_action": "cancelled", "confidence_score": 0.9},
        }
        res = comparator.evaluate(preds, golden_set=golden)
        md = comparator.generate_report_markdown(res, title="Unit Test QA Report")
        assert "# SIP Insight Lab — Unit Test QA Report" in md
        assert "Per-Field Performance Summary" in md
        assert "Root Cause (RC) Per-Class Performance Breakdown" in md


# ---------------------------------------------------------------------------
# Task 3.7 — AI Evidence Log
# ---------------------------------------------------------------------------

class TestEvidenceLog:

    def test_dual_persistence_and_override_rate(self, in_memory_db, tmp_path):
        # Create prerequisite raw and cleaned and labelled items for FK
        in_memory_db.execute(
            "INSERT INTO raw_item (item_id, source, source_id, raw_text, dedup_hash, collected_at) VALUES ('it_01', 'play_store', 's1', 'txt', 'h1', datetime('now'))"
        )
        in_memory_db.execute(
            "INSERT INTO cleaned_item (item_id, cleaned_text, language, cleaning_version, cleaned_at) VALUES ('it_01', 'txt', 'en', '1.0', datetime('now'))"
        )
        in_memory_db.execute(
            "INSERT INTO labelled_item (item_id, taxonomy_version, root_cause, confidence_score, classified_at) VALUES ('it_01', '1.0', 'RC-02', 0.65, datetime('now'))"
        )

        log_file = tmp_path / "test_evidence.jsonl"
        writer = EvidenceLogWriter(in_memory_db, log_file_path=log_file)

        # Log approval
        writer.log_approval("it_01", ai_output={"root_cause": "RC-02", "confidence": 0.85})
        # Log correction
        writer.log_correction(
            "it_01",
            ai_output={"root_cause": "RC-02", "confidence": 0.61},
            human_output={"root_cause": "RC-01"},
            reviewer_id="reviewer_lead",
            reason_note="Involuntary mandate failure",
        )

        # Verify DB entries
        entries = writer.get_entries(limit=10)
        assert len(entries) == 2

        # Verify JSONL entries
        assert log_file.exists()
        lines = log_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2
        entry_2 = json.loads(lines[1])
        assert entry_2["event_type"] == "correction"
        assert entry_2["human_output"] == {"root_cause": "RC-01"}

        # Verify metrics
        metrics = writer.get_metrics()
        assert metrics["total_log_entries"] == 2
        assert metrics["approvals"] == 1
        assert metrics["corrections"] == 1
        assert metrics["human_override_rate"] == 0.5


# ---------------------------------------------------------------------------
# Tasks 3.8 & 3.9 — Human Review Processor
# ---------------------------------------------------------------------------

class TestHumanReviewProcessor:

    def test_export_template_and_process_actions(self, seeded_db, tmp_path):
        processor = HumanReviewProcessor(seeded_db)
        out_csv = tmp_path / "review_template.csv"

        n = processor.export_csv_template(str(out_csv))
        assert n == 1
        assert out_csv.exists()

        # Process a correction
        processor.process_correction(
            queue_id="q_01",
            item_id="item_01",
            corrections={"root_cause": "RC-01", "root_cause_sub": "Bank mandate failure"},
            reviewer_id="reviewer_lead",
            reason_note="Updated to mandate failure",
        )

        # Check labelled_item updated
        cursor = seeded_db.cursor()
        status, rc = cursor.execute("SELECT review_status, root_cause FROM labelled_item WHERE item_id = 'item_01'").fetchone()
        assert status == "human_reviewed"
        assert rc == "RC-01"

        # Check queue status updated
        q_status = cursor.execute("SELECT status FROM human_review_queue WHERE queue_id = 'q_01'").fetchone()[0]
        assert q_status == "completed"

        # Check evidence log has entry
        metrics = processor.evidence_log.get_metrics()
        assert metrics["corrections"] == 1


# ---------------------------------------------------------------------------
# Tasks 3.10, 3.11, 3.12 — Counter-Evidence Agent & Formatter
# ---------------------------------------------------------------------------

class TestCounterEvidenceAgent:

    def test_adversarial_strategies_and_analysis(self, seeded_db):
        agent = CounterEvidenceAgent(seeded_db)
        analysis = agent.analyze_theme(
            theme="Bank mandate failures are the primary driver of early SIP churn",
            root_cause="RC-01",
            lifecycle_stage="LS-01",
        )

        assert isinstance(analysis, CounterEvidenceAnalysis)
        assert analysis.root_cause == "RC-01"
        assert "inverse_query" in analysis.strategy_results
        assert "segment_drilldown" in analysis.strategy_results
        assert "temporal_check" in analysis.strategy_results
        assert "frequency_sanity" in analysis.strategy_results

    def test_formatter_renders_markdown(self, seeded_db):
        agent = CounterEvidenceAgent(seeded_db)
        formatter = CounterEvidenceFormatter()
        analysis = agent.analyze_theme(
            theme="UX friction causes churn",
            root_cause="RC-02",
        )
        md_section = formatter.format_theme_section(analysis)
        assert "### Theme: \"UX friction causes churn\"" in md_section
        assert "4-Strategy Adversarial Evaluation" in md_section
        assert "Synthesis & PM Guidance" in md_section

        full_doc = formatter.format_full_review_document([analysis])
        assert "# SIP Insight Lab — Counter-Evidence Agent — Preliminary Themes Stress-Test Review" in full_doc
        assert "Executive Summary" in full_doc


# ---------------------------------------------------------------------------
# Phase 3 Exit Criteria End-to-End Verification
# ---------------------------------------------------------------------------

class TestPhase3ExitCriteria:

    def test_qa_reports_exist_and_meet_thresholds(self):
        v1_path = PROJECT_ROOT / "outputs" / "qa_report_v1.md"
        v2_path = PROJECT_ROOT / "outputs" / "qa_report_v2.md"
        ce_path = PROJECT_ROOT / "outputs" / "reports" / "counter_evidence_review.md"
        ev_log_path = PROJECT_ROOT / "outputs" / "logs" / "ai_evidence_log.jsonl"

        assert v1_path.exists(), "outputs/qa_report_v1.md missing"
        assert v2_path.exists(), "outputs/qa_report_v2.md missing"
        assert ce_path.exists(), "counter_evidence_review.md missing"
        assert ev_log_path.exists(), "ai_evidence_log.jsonl missing"

        # Check v2 accuracy in file
        v2_content = v2_path.read_text(encoding="utf-8")
        assert "**Exact-Match Overall Accuracy:** **80.0%**" in v2_content
        assert "**All Per-Field F1 ≥ 0.75:** **YES (PASS)**" in v2_content
