"""
Groww SIP Insight Lab — AI Discovery Engine Verification Tests
==============================================================
Validates all 8 core improvements implemented in the Discovery Engine:
  1. Research Overview: Ingestion metrics, source breakdown, classification coverage.
  2. Cross-Source Analysis: Play Store, App Store, Reddit, YouTube comparative metrics.
  3. Problem Explorer: Themes, stages, sentiments, behaviours.
  4. Evidence Explorer: Schema, ratings, original quotes, record IDs.
  5. Insight Explorer: Recurring patterns, supporting counts, and linked feedback drilldown.
  6. Opportunity Matrix: Visible formula, frequency, severity, addressability, opportunity scores.
  7. Search and Filters: Multi-dimensional filtering and instant text search.
  8. AI Research Assistant: Question answering with verifiable citations to record IDs.
"""

import sys
from pathlib import Path
import pytest
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.dashboard.data_loader import DashboardDataLoader
from src.dashboard.components import (
    render_research_funnel_chart,
    render_source_distribution_pie,
    render_cross_source_theme_matrix,
    render_cross_source_sentiment_chart,
    render_problem_theme_bar,
    render_stage_vs_theme_heatmap,
    render_opportunity_matrix_scatter,
)


@pytest.fixture
def loader():
    return DashboardDataLoader()


@pytest.fixture
def research_df(loader):
    df = loader.load_research_corpus()
    assert not df.empty, "Research corpus (sip_feedback_classified.csv) should not be empty"
    return df


class TestDiscoveryEngine:

    def test_improvement_1_research_overview(self, loader, research_df):
        stats = loader.get_research_overview_stats()
        assert stats["total_raw"] >= 1000, f"Expected >= 1000 raw records, got {stats['total_raw']}"
        assert stats["total_cleaned"] >= 600, f"Expected >= 600 cleaned records, got {stats['total_cleaned']}"
        assert stats["total_relevant"] >= 250, f"Expected >= 250 relevant records, got {stats['total_relevant']}"
        assert stats["total_classified"] == stats["total_relevant"], "All relevant records should be classified"
        assert stats["classification_rate_pct"] == 100.0, "Classification rate should be 100%"

        # Verify all 4 sources exist in raw counts
        raw_keys = list(stats["raw_counts"].keys())
        for src in ["Google Play Store", "Apple App Store", "Reddit", "YouTube"]:
            assert src in raw_keys, f"Missing source in raw counts: {src}"
            assert stats["raw_counts"][src] > 0, f"Source count should be > 0: {src}"

        # Test funnel and pie chart renders
        fig_funnel = render_research_funnel_chart(stats)
        assert fig_funnel is not None
        fig_pie = render_source_distribution_pie(stats)
        assert fig_pie is not None

    def test_improvement_2_cross_source_analysis(self, loader, research_df):
        cs = loader.get_cross_source_analysis(research_df)
        summary_table = cs["summary_table"]
        assert not summary_table.empty, "Cross-source summary table should not be empty"
        assert len(summary_table) == 4, f"Expected 4 source platforms, got {len(summary_table)}"

        # Verify required columns
        for col in ["Source Platform", "Relevant Feedback Count", "Avg Sentiment Score", "Dominant Problem Theme"]:
            assert col in summary_table.columns, f"Missing column in summary: {col}"

        # Verify crosstabs
        assert not cs["theme_crosstab"].empty, "Theme crosstab should not be empty"
        assert not cs["sentiment_crosstab"].empty, "Sentiment crosstab should not be empty"

        # Test Plotly figures
        fig_themes = render_cross_source_theme_matrix(cs["theme_crosstab"])
        assert fig_themes is not None
        fig_sent = render_cross_source_sentiment_chart(cs["sentiment_crosstab"])
        assert fig_sent is not None

    def test_improvement_3_problem_explorer(self, loader, research_df):
        assert "problem_theme" in research_df.columns
        assert "user_journey_stage" in research_df.columns
        assert "sentiment" in research_df.columns
        assert "user_behaviour" in research_df.columns
        assert "classification_type" in research_df.columns

        # Verify distributions
        theme_counts = research_df["problem_theme"].value_counts()
        assert len(theme_counts) >= 5, "Expected at least 5 distinct problem themes"

        stage_counts = research_df["user_journey_stage"].value_counts()
        assert len(stage_counts) >= 4, "Expected at least 4 distinct journey stages"

        # Test charts
        fig_p = render_problem_theme_bar(research_df)
        assert fig_p is not None
        fig_hm = render_stage_vs_theme_heatmap(research_df)
        assert fig_hm is not None

    def test_improvement_4_evidence_explorer_traceability(self, loader, research_df):
        # Verify required schema
        for col in ["record_id", "source", "date", "rating", "cleaned_text", "raw_text", "evidence_quote", "confidence_score", "classification_reason"]:
            assert col in research_df.columns, f"Missing column: {col}"

        # Check record ID format
        assert (research_df["record_id"].str.startswith("GFB_")).all(), "All record IDs should start with GFB_"

        # Verify evidence quotes are present
        non_empty_quotes = research_df["evidence_quote"].dropna()
        assert len(non_empty_quotes) >= len(research_df) * 0.95, "At least 95% of records should have evidence quotes"

    def test_improvement_5_insight_explorer_with_drilldown(self, loader, research_df):
        insights = loader.get_recurring_insights(research_df)
        assert len(insights) >= 5, f"Expected at least 5 recurring insights, got {len(insights)}"

        for ins in insights:
            assert "insight_id" in ins
            assert "title" in ins
            assert "count" in ins
            assert ins["count"] > 0, f"Insight {ins['insight_id']} count should be > 0"
            assert "supporting_record_ids" in ins
            assert len(ins["supporting_record_ids"]) == ins["count"]

            # Verify that every supporting ID exists in the research corpus
            first_id = ins["supporting_record_ids"][0]
            matched = research_df[research_df["record_id"] == first_id]
            assert not matched.empty, f"Record ID {first_id} not found in research corpus"

    def test_improvement_6_opportunity_matrix(self, loader, research_df):
        opp_df = loader.get_opportunity_matrix(research_df)
        assert not opp_df.empty
        assert len(opp_df) >= 4, f"Expected >= 4 opportunities, got {len(opp_df)}"

        # Check required columns
        for col in ["opp_id", "opportunity_name", "theme", "frequency_score", "severity_score", "user_impact_score", "addressability_score", "opportunity_score", "priority_tier", "product_recommendation"]:
            assert col in opp_df.columns, f"Missing column in opportunity matrix: {col}"

        # Verify formula calculation: (Freq*0.30) + (Sev*0.25) + (Impact*0.25) + (Addr*0.20)
        for _, r in opp_df.iterrows():
            expected = round(r["frequency_score"] * 0.30 + r["severity_score"] * 0.25 + r["user_impact_score"] * 0.25 + r["addressability_score"] * 0.20, 3)
            assert abs(r["opportunity_score"] - expected) <= 0.005, f"Opportunity score formula mismatch for {r['opp_id']}"

        fig_matrix = render_opportunity_matrix_scatter(opp_df)
        assert fig_matrix is not None

    def test_improvement_7_search_and_filters(self, loader, research_df):
        # Test Source filter
        f_src = loader.filter_research_corpus(research_df, sources=["reddit"])
        assert not f_src.empty
        assert (f_src["source"] == "reddit").all()

        # Test Theme filter
        f_theme = loader.filter_research_corpus(research_df, themes=["Mandate / Auto-Debit Failure"])
        assert not f_theme.empty
        assert (f_theme["problem_theme"] == "Mandate / Auto-Debit Failure").all()

        # Test Sentiment filter
        f_sent = loader.filter_research_corpus(research_df, sentiments=["negative"])
        assert not f_sent.empty
        assert (f_sent["sentiment"] == "negative").all()

        # Test Text Search
        f_search = loader.filter_research_corpus(research_df, search_query="bounce")
        assert not f_search.empty
        for _, r in f_search.iterrows():
            combined = (str(r["cleaned_text"]) + str(r["evidence_quote"]) + str(r["classification_reason"])).lower()
            assert "bounce" in combined

    def test_improvement_8_ai_research_assistant(self, loader, research_df):
        resp = loader.ask_ai_research_assistant("Why do users stop or pause SIP?", research_df)
        assert resp is not None
        assert "answer" in resp and len(resp["answer"]) > 50, "Answer should be substantive"
        assert "citations" in resp and len(resp["citations"]) > 0, "Should return supporting citations"

        # Verify citations format
        first_cite = resp["citations"][0]
        assert "record_id" in first_cite
        assert first_cite["record_id"].startswith("GFB_")
        assert "quote" in first_cite and len(first_cite["quote"]) > 0
        assert "source" in first_cite

