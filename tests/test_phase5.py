"""
SIP Insight Lab — Unit and Integration Tests: Phase 5 (Tasks 5.1–5.14)
======================================================================
Tests for:
  - Dashboard Data Loader: full corpus, flattens segments, intent-action gap (Task 5.1 & 5.2)
  - 7 Filter Dimensions: Stage, Root Cause, Stop Type, Source, Segments, Gap, Date (Task 5.1)
  - Source Traceability & Drill-down verification (Task 5.5)
  - AI Evidence Log Export (CSV + JSON) with >= 10 records (Task 5.3 & 5.12)
  - Live QA Metrics Panel extraction (Task 5.4)
  - Dashboard Visualizations: Plotly figure generation across all views (Task 5.1 & 5.2)
  - Stakeholder Readout Deck & Decisions Log (Task 5.6, 5.7, 5.8)
  - Validation Handoff: Briefing & Calendar with >= 5 interviews (Task 5.9 & 5.10)
  - Hypothesis Cards updated with validation status (Task 5.11)
  - Retrospective & Taxonomy v2.0 frozen (Task 5.13 & 5.14)

Run:
    python -m pytest tests/test_phase5.py -v
"""

import json
import sqlite3
import sys
import tempfile
from pathlib import Path
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.dashboard.data_loader import DashboardDataLoader
from src.dashboard.components import (
    render_opportunity_ranking_chart,
    render_intent_action_gap_heatmap,
    render_gap_rate_bar_chart,
    render_churn_timeline,
    render_involuntary_vs_deliberate_chart,
    render_retention_factors_chart,
    render_source_quality_chart,
    render_qa_metrics_charts,
)
from src.taxonomy_loader import TaxonomyLoader
from src.db.schema import init_db

DB_PATH = PROJECT_ROOT / "data" / "sip_insight_lab.db"


@pytest.fixture
def loader():
    return DashboardDataLoader(str(DB_PATH))


@pytest.fixture
def full_df(loader):
    return loader.load_full_corpus()


# =============================================================================
# Tasks 5.1 & 5.2 — Data Loader & 7 Filter Dimensions
# =============================================================================

class TestDashboardDataLoader:

    def test_load_full_corpus_schema_and_types(self, full_df):
        assert not full_df.empty, "Corpus should not be empty"
        assert len(full_df) >= 300, f"Expected >= 300 items, got {len(full_df)}"

        # Verify key columns
        required_cols = [
            "item_id", "source", "raw_text", "cleaned_text", "lifecycle_stage",
            "root_cause", "stated_intent", "actual_action", "stop_type",
            "confidence_score", "sentiment_score", "has_gap",
            "segment_age_group", "segment_income_stability",
            "segment_money_source", "segment_influencer_type",
        ]
        for col in required_cols:
            assert col in full_df.columns, f"Missing required column: {col}"

    def test_filter_dimension_1_lifecycle_stage(self, loader, full_df):
        f = loader.filter_corpus(full_df, lifecycle_stages=["LS-01"])
        assert not f.empty
        assert (f["lifecycle_stage"] == "LS-01").all()

    def test_filter_dimension_2_root_cause(self, loader, full_df):
        f = loader.filter_corpus(full_df, root_causes=["RC-01"])
        assert not f.empty
        assert (f["root_cause"] == "RC-01").all()

    def test_filter_dimension_3_stop_type(self, loader, full_df):
        f = loader.filter_corpus(full_df, stop_types=["ST-01"])
        assert not f.empty
        assert (f["stop_type"] == "ST-01").all()

    def test_filter_dimension_4_source_platform(self, loader, full_df):
        f = loader.filter_corpus(full_df, sources=["play_store"])
        assert not f.empty
        assert (f["source"] == "play_store").all()

    def test_filter_dimension_5_investor_segment(self, loader, full_df):
        f = loader.filter_corpus(full_df, age_groups=["25-30"])
        assert not f.empty
        assert (f["segment_age_group"] == "25-30").all()

    def test_filter_dimension_6_intent_action_gap(self, loader, full_df):
        f_gap = loader.filter_corpus(full_df, gap_filter="gap_only")
        assert not f_gap.empty
        assert f_gap["has_gap"].all()

        f_aligned = loader.filter_corpus(full_df, gap_filter="aligned_only")
        assert not f_aligned.empty
        assert not f_aligned["has_gap"].any()

    def test_filter_dimension_7_date_range(self, loader, full_df):
        min_date = full_df["collected_at"].min()
        max_date = full_df["collected_at"].max()
        f = loader.filter_corpus(full_df, date_range=(min_date, max_date))
        assert len(f) == len(full_df)

    def test_multi_filter_combination(self, loader, full_df):
        f = loader.filter_corpus(
            full_df,
            lifecycle_stages=["LS-01"],
            root_causes=["RC-01"],
            sources=["play_store"],
            gap_filter="gap_only",
        )
        assert not f.empty
        assert (f["lifecycle_stage"] == "LS-01").all()
        assert (f["root_cause"] == "RC-01").all()
        assert (f["source"] == "play_store").all()
        assert f["has_gap"].all()


# =============================================================================
# Task 5.2 — Intent vs. Action Gap Analysis
# =============================================================================

class TestIntentActionGapAnalysis:

    def test_gap_breakdown_metrics(self, loader, full_df):
        gap = loader.get_intent_action_gap_breakdown(full_df)
        assert gap["total_items"] == len(full_df)
        assert gap["gap_count"] > 0
        assert 0.0 < gap["gap_rate"] <= 100.0

        # Crosstab checks
        assert not gap["crosstab"].empty
        assert "Total" in gap["crosstab"].columns

        # By source and by stage
        assert not gap["gap_by_source"].empty
        assert "gap_percentage" in gap["gap_by_source"].columns
        assert not gap["gap_by_stage"].empty
        assert "gap_percentage" in gap["gap_by_stage"].columns


# =============================================================================
# Task 5.3 & 5.12 — AI Evidence Log Export (CSV + JSON)
# =============================================================================

class TestEvidenceLogExport:

    def test_export_evidence_log_to_temp_files(self, loader):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "test_log.csv"
            json_path = Path(tmpdir) / "test_log.json"

            df_log, json_str = loader.export_evidence_log(str(csv_path), str(json_path))

            assert csv_path.exists()
            assert json_path.exists()
            assert len(df_log) >= 10, f"Expected >= 10 evidence log records, got {len(df_log)}"

            # Verify JSON structure
            parsed = json.loads(json_str)
            assert isinstance(parsed, list)
            assert len(parsed) >= 10
            for record in parsed:
                assert "log_id" in record
                assert "event_type" in record
                assert record["event_type"] in ["correction", "approval", "rejection"]


# =============================================================================
# Task 5.4 — QA Metrics Panel Extraction
# =============================================================================

class TestQAMetricsExtraction:

    def test_qa_metrics_values(self, loader):
        qa = loader.get_qa_metrics()
        assert qa["golden_set_size"] >= 20
        assert qa["overall_accuracy"] >= 80.0
        assert qa["per_field_f1"]["root_cause"] >= 0.75
        assert qa["per_field_f1"]["stop_type"] >= 0.75
        assert qa["per_field_f1"]["lifecycle_stage"] >= 0.75
        assert qa["human_review_rate_pct"] < 20.0
        assert qa["evidence_log_total"] >= 10


# =============================================================================
# Task 5.5 — Source Traceability & Drill-down
# =============================================================================

class TestSourceTraceability:

    def test_drill_down_quote_traceability(self, full_df):
        for idx in range(min(5, len(full_df))):
            item = full_df.iloc[idx]
            assert pd.notna(item["raw_text"]) and len(item["raw_text"]) > 0
            assert pd.notna(item["cleaned_text"]) and len(item["cleaned_text"]) > 0
            assert item["source"] in ["play_store", "app_store", "reddit", "tradingqa", "youtube"]

    def test_hypothesis_cards_traceable_quotes(self, loader):
        cards = loader.get_opportunity_rankings()
        assert len(cards) >= 5, "Expected >= 5 hypothesis cards"
        for card in cards:
            quotes = card["supporting_quotes"]
            assert len(quotes) >= 1
            for q in quotes:
                assert isinstance(q, str) and len(q) > 10


# =============================================================================
# Task 5.1 — Visualizations & Component Generation
# =============================================================================

class TestDashboardComponents:

    def test_render_all_plotly_charts(self, loader, full_df):
        cards = loader.get_opportunity_rankings()
        gap = loader.get_intent_action_gap_breakdown(full_df)
        qa = loader.get_qa_metrics()

        # Opportunity ranking chart
        fig_rank = render_opportunity_ranking_chart(cards)
        assert fig_rank is not None
        assert len(fig_rank.data) == 4  # 4 components

        # Heatmap
        fig_heat = render_intent_action_gap_heatmap(gap["crosstab"])
        assert fig_heat is not None

        # Gap rate bar chart
        fig_gap_src = render_gap_rate_bar_chart(gap["gap_by_source"], "source", "Gap by Source")
        assert fig_gap_src is not None

        # Churn timeline
        fig_timeline = render_churn_timeline(full_df)
        assert fig_timeline is not None

        # Involuntary vs deliberate
        fig_inv = render_involuntary_vs_deliberate_chart(full_df)
        assert fig_inv is not None

        # Retention factors
        fig_rf = render_retention_factors_chart(full_df)
        assert fig_rf is not None

        # Source quality
        fig_src = render_source_quality_chart(full_df)
        assert fig_src is not None

        # QA metrics
        fig_qa = render_qa_metrics_charts(qa)
        assert fig_qa is not None


# =============================================================================
# Tasks 5.6–5.14 — Documentation, Handoff & Taxonomy v2.0
# =============================================================================

class TestPhase5HandoffDeliverables:

    def test_stakeholder_readout_deck_exists(self):
        deck = PROJECT_ROOT / "outputs" / "reports" / "stakeholder_readout_deck.md"
        assert deck.is_file()
        content = deck.read_text(encoding="utf-8")
        assert "RC-01" in content
        assert "RC-03" in content
        assert "RC-02" in content
        assert "Opportunity Score =" in content

    def test_stakeholder_decisions_log_exists(self):
        decisions = PROJECT_ROOT / "outputs" / "reports" / "stakeholder_decisions.md"
        assert decisions.is_file()
        content = decisions.read_text(encoding="utf-8")
        assert "Decision Matrix" in content
        assert "Sign-Off" in content

    def test_user_research_handoff_briefing_exists(self):
        briefing = PROJECT_ROOT / "outputs" / "reports" / "interview_handoff_briefing.md"
        assert briefing.is_file()
        content = briefing.read_text(encoding="utf-8")
        assert "Ethical Guardrails" in content
        assert "Recruitment Criteria" in content

    def test_user_interview_calendar_has_minimum_5_interviews(self):
        cal = PROJECT_ROOT / "outputs" / "reports" / "interview_calendar.md"
        assert cal.is_file()
        content = cal.read_text(encoding="utf-8")
        for i in range(1, 6):
            assert f"INT-0{i}" in content, f"Missing interview INT-0{i}"

    def test_hypothesis_cards_have_validation_status(self):
        for code in ["RC-01", "RC-02", "RC-03"]:
            card_path = PROJECT_ROOT / "outputs" / "hypothesis_cards" / f"HC-{code}.md"
            assert card_path.is_file()
            content = card_path.read_text(encoding="utf-8")
            assert "Interview Validation Findings & Synthesis" in content

    def test_retrospective_and_taxonomy_v2(self):
        retro = PROJECT_ROOT / "outputs" / "retrospective.md"
        assert retro.is_file()

        tax2 = PROJECT_ROOT / "taxonomy" / "taxonomy_v2.yaml"
        assert tax2.is_file()

        loader = TaxonomyLoader(str(tax2))
        assert loader.version == "2.0"
        assert loader.is_frozen
        assert len(loader.root_cause_codes) >= 8

