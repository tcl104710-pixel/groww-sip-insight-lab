"""
SIP Insight Lab — Dashboard Visualizations & Components (Phase 5)
=================================================================
Interactive Plotly charts, UI metric cards, and source traceability
tables for the Streamlit Insight Dashboard.
"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import streamlit as st
from typing import Dict, List, Any, Optional


def render_metric_card(label: str, value: str, delta: Optional[str] = None, delta_color: str = "normal"):
    """Renders a styled KPI metric card in Streamlit."""
    st.metric(label=label, value=value, delta=delta, delta_color=delta_color)


def render_opportunity_ranking_chart(cards: List[Dict[str, Any]]) -> go.Figure:
    """
    Renders stacked bar chart showing the 4 visible components of Opportunity Score
    for each root cause:
      - Frequency (30%)
      - Severity (25%)
      - First 6mo Concentration (25%)
      - Addressability (20%)
    """
    if not cards:
        return go.Figure()

    df_cards = pd.DataFrame(cards)
    # Sort ascending for horizontal bar chart display
    df_cards = df_cards.sort_values(by="opportunity_score", ascending=True)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df_cards["root_cause"] + " - " + df_cards["opportunity_label"].str[:25] + "...",
        x=df_cards["frequency_score"] * 0.30,
        name="Frequency (30%)",
        orientation="h",
        marker=dict(color="#2ca02c"),
    ))
    fig.add_trace(go.Bar(
        y=df_cards["root_cause"] + " - " + df_cards["opportunity_label"].str[:25] + "...",
        x=df_cards["severity_score"] * 0.25,
        name="Severity (25%)",
        orientation="h",
        marker=dict(color="#d62728"),
    ))
    fig.add_trace(go.Bar(
        y=df_cards["root_cause"] + " - " + df_cards["opportunity_label"].str[:25] + "...",
        x=df_cards["first_6mo_concentration"] * 0.25,
        name="6mo Conc. (25%)",
        orientation="h",
        marker=dict(color="#ff7f0e"),
    ))
    fig.add_trace(go.Bar(
        y=df_cards["root_cause"] + " - " + df_cards["opportunity_label"].str[:25] + "...",
        x=df_cards["addressability_score"] * 0.20,
        name="Addressability (20%)",
        orientation="h",
        marker=dict(color="#1f77b4"),
    ))

    fig.update_layout(
        barmode="stack",
        title="Opportunity Score Breakdown by Component (Visible Formula)",
        xaxis=dict(title="Weighted Opportunity Score (0.00 – 1.00)", range=[0, 1.05]),
        yaxis=dict(title="Opportunity / Root Cause"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=50, b=30),
        height=450,
    )
    return fig


def render_intent_action_gap_heatmap(crosstab: pd.DataFrame) -> go.Figure:
    """Renders heatmap of Stated Intent vs Actual Action."""
    if crosstab.empty:
        return go.Figure()

    # Drop Margins for heatmap
    data_matrix = crosstab.drop(index="Total", columns="Total", errors="ignore")
    fig = px.imshow(
        data_matrix,
        text_auto=True,
        labels=dict(x="Actual Action (What Investors Did)", y="Stated Intent (What Investors Said)", color="Count"),
        x=data_matrix.columns.tolist(),
        y=data_matrix.index.tolist(),
        color_continuous_scale="Viridis",
        aspect="auto",
    )
    fig.update_layout(
        title="Intent vs. Action Gap Matrix (Decoupled Fields)",
        margin=dict(l=10, r=10, t=40, b=30),
        height=380,
    )
    return fig


def render_gap_rate_bar_chart(gap_df: pd.DataFrame, category_col: str, title: str) -> go.Figure:
    """Renders bar chart showing Intent vs Action Gap % by dimension."""
    if gap_df.empty:
        return go.Figure()

    fig = px.bar(
        gap_df,
        x=category_col,
        y="gap_percentage",
        text="gap_percentage",
        color="gap_percentage",
        color_continuous_scale="Reds",
        labels={category_col: category_col.replace("_", " ").title(), "gap_percentage": "Gap Rate (%)"},
        title=title,
    )
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig.update_layout(
        yaxis=dict(range=[0, max(100, gap_df["gap_percentage"].max() * 1.15)]),
        margin=dict(l=10, r=10, t=40, b=30),
        height=350,
    )
    return fig


def render_churn_timeline(df: pd.DataFrame) -> go.Figure:
    """Renders histogram of feedback volume across investor lifecycle stages."""
    if df.empty:
        return go.Figure()

    stage_order = ["LS-00", "LS-01", "LS-02", "LS-03", "LS-04", "LS-99"]
    stage_labels = {
        "LS-00": "Pre-SIP (LS-00)",
        "LS-01": "0–3 Months (LS-01)",
        "LS-02": "3–6 Months (LS-02)",
        "LS-03": "6–12 Months (LS-03)",
        "LS-04": "12+ Months (LS-04)",
        "LS-99": "Unknown (LS-99)",
    }

    counts = df["lifecycle_stage"].value_counts().reindex(stage_order, fill_value=0).reset_index()
    counts.columns = ["stage_code", "count"]
    counts["stage_label"] = counts["stage_code"].map(stage_labels)

    # Highlight early churn window (first 6 months)
    colors = ["#90caf9", "#e53935", "#fb8c00", "#43a047", "#1e88e5", "#9e9e9e"]

    fig = px.bar(
        counts,
        x="stage_label",
        y="count",
        text="count",
        title="Churn Timeline: Distribution of Feedback by Lifecycle Stage",
        labels={"stage_label": "Lifecycle Stage", "count": "Feedback Count"},
        color="stage_code",
        color_discrete_sequence=colors,
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        showlegend=False,
        margin=dict(l=10, r=10, t=40, b=30),
        height=350,
    )
    return fig


def render_involuntary_vs_deliberate_chart(df: pd.DataFrame) -> go.Figure:
    """Renders stacked bar chart of Stop Type across Root Causes."""
    if df.empty:
        return go.Figure()

    stop_labels = {
        "ST-01": "Involuntary Lapse",
        "ST-02": "Deliberate Exit",
        "ST-03": "Continuing / Active",
        "ST-99": "Unknown Stop Type",
    }
    temp = df.copy()
    temp["stop_type_label"] = temp["stop_type"].map(stop_labels).fillna("Unknown")

    counts = temp.groupby(["root_cause", "stop_type_label"]).size().reset_index(name="count")

    fig = px.bar(
        counts,
        x="root_cause",
        y="count",
        color="stop_type_label",
        title="Involuntary vs. Deliberate Churn by Root Cause",
        labels={"root_cause": "Root Cause Code", "count": "Feedback Count", "stop_type_label": "Stop Type"},
        barmode="stack",
        color_discrete_map={
            "Involuntary Lapse": "#e53935",
            "Deliberate Exit": "#3949ab",
            "Continuing / Active": "#43a047",
            "Unknown Stop Type": "#757575",
        },
    )
    fig.update_layout(
        margin=dict(l=10, r=10, t=40, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=380,
    )
    return fig


def render_retention_factors_chart(df: pd.DataFrame) -> go.Figure:
    """Renders bar chart of retention factor codes for retained investors."""
    retained_df = df[df["retention_factor"].notna() & (df["retention_factor"] != "None")]
    if retained_df.empty:
        return go.Figure()

    rf_labels = {
        "RF-01": "Positive Returns (RF-01)",
        "RF-02": "Peer / Community (RF-02)",
        "RF-03": "Nudges / Reminders (RF-03)",
        "RF-04": "Goal Tracking (RF-04)",
        "RF-05": "In-App Education (RF-05)",
        "RF-06": "Automated Flow (RF-06)",
        "RF-07": "Disciplined Habit (RF-07)",
        "RF-99": "Other Factor (RF-99)",
    }

    counts = retained_df["retention_factor"].value_counts().reset_index()
    counts.columns = ["factor_code", "count"]
    counts["factor_label"] = counts["factor_code"].map(rf_labels).fillna(counts["factor_code"])

    fig = px.bar(
        counts,
        x="factor_label",
        y="count",
        text="count",
        color="count",
        color_continuous_scale="Greens",
        title="Retention Factors: What Keeps Continuers Going",
        labels={"factor_label": "Retention Factor", "count": "Items Reporting Factor"},
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        margin=dict(l=10, r=10, t=40, b=30),
        height=350,
    )
    return fig


def render_source_quality_chart(df: pd.DataFrame) -> go.Figure:
    """Renders multi-axis chart showing volume and average confidence per source."""
    if df.empty:
        return go.Figure()

    agg = df.groupby("source").agg(
        volume=("item_id", "count"),
        avg_confidence=("confidence_score", "mean"),
        avg_sentiment=("sentiment_score", "mean"),
    ).reset_index()
    agg["avg_confidence_pct"] = (agg["avg_confidence"] * 100).round(1)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=agg["source"],
        y=agg["volume"],
        name="Feedback Volume",
        marker=dict(color="#1f77b4"),
        text=agg["volume"],
        textposition="outside",
    ))
    fig.add_trace(go.Scatter(
        x=agg["source"],
        y=agg["avg_confidence_pct"],
        name="Avg Confidence (%)",
        yaxis="y2",
        mode="lines+markers+text",
        text=agg["avg_confidence_pct"].astype(str) + "%",
        textposition="top center",
        marker=dict(size=10, color="#ff7f0e"),
        line=dict(width=3, color="#ff7f0e"),
    ))

    fig.update_layout(
        title="Source Corpus Quality: Volume vs. Classification Confidence",
        xaxis=dict(title="Data Source"),
        yaxis=dict(title="Number of Items"),
        yaxis2=dict(
            title="Average Confidence (%)",
            overlaying="y",
            side="right",
            range=[0, 115],
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=50, b=30),
        height=380,
    )
    return fig


def render_qa_metrics_charts(qa_data: Dict[str, Any]) -> go.Figure:
    """Renders F1 performance across taxonomy fields vs the 0.75 target threshold."""
    f1_scores = qa_data.get("per_field_f1", {})
    if not f1_scores:
        return go.Figure()

    fields = list(f1_scores.keys())
    scores = list(f1_scores.values())

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=fields,
        y=scores,
        text=[f"{s:.3f}" for s in scores],
        textposition="outside",
        marker=dict(color=["#2ca02c" if s >= 0.75 else "#d62728" for s in scores]),
        name="Field F1 Score",
    ))
    fig.add_shape(
        type="line",
        x0=-0.5,
        x1=len(fields) - 0.5,
        y0=0.75,
        y1=0.75,
        line=dict(color="red", width=2, dash="dash"),
    )
    fig.add_annotation(
        x=0.5,
        y=0.77,
        text="Target Threshold: F1 ≥ 0.75",
        showarrow=False,
        font=dict(color="red", size=11),
    )
    fig.update_layout(
        title="Per-Field Classification F1 Scores vs. SLA Threshold (0.75)",
        xaxis=dict(title="Taxonomy Field"),
        yaxis=dict(title="F1 Score (0.00 – 1.00)", range=[0, 1.15]),
        margin=dict(l=10, r=10, t=40, b=30),
        height=350,
    )
    return fig


# =============================================================================
# MULTI-SOURCE RESEARCH VISUALIZATIONS (AI Discovery Engine Extensions)
# =============================================================================

def render_research_funnel_chart(stats: Dict[str, Any]) -> go.Figure:
    """
    Renders research data ingestion funnel from Raw Ingestion to AI Classification.
    """
    stages = [
        "1. Raw Ingestion",
        "2. Cleaned & Normalized",
        "3. SIP Relevant Feedback",
        "4. AI Classified Corpus",
    ]
    values = [
        stats.get("total_raw", 1065),
        stats.get("total_cleaned", 696),
        stats.get("total_relevant", 269),
        stats.get("total_classified", 269),
    ]

    fig = go.Figure(go.Funnel(
        y=stages,
        x=values,
        textinfo="value+percent initial",
        marker=dict(color=["#1E3A8A", "#3B82F6", "#10B981", "#059669"]),
    ))
    fig.update_layout(
        title="Multi-Source Pipeline Funnel (Raw to AI Classified)",
        margin=dict(l=20, r=20, t=40, b=20),
        height=320,
    )
    return fig


def render_source_distribution_pie(stats: Dict[str, Any], use_relevant: bool = True) -> go.Figure:
    """Renders donut chart showing source distribution."""
    if use_relevant:
        data = stats.get("source_classified_breakdown", {})
        title = "SIP-Relevant Feedback Distribution by Source"
    else:
        data = stats.get("raw_counts", {})
        title = "Total Raw Collection by Source"

    if not data:
        return go.Figure()

    labels = list(data.keys())
    values = list(data.values())

    fig = px.pie(
        names=labels,
        values=values,
        title=title,
        hole=0.45,
        color_discrete_sequence=["#FF4500", "#FF0000", "#007AFF", "#34A853"],
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(
        margin=dict(l=10, r=10, t=40, b=20),
        height=320,
        showlegend=False,
    )
    return fig


def render_cross_source_theme_matrix(crosstab: pd.DataFrame) -> go.Figure:
    """Renders horizontal stacked bar chart comparing problem themes across platforms."""
    if crosstab.empty:
        return go.Figure()

    fig = px.bar(
        crosstab,
        x=crosstab.columns.tolist(),
        y=crosstab.index.tolist(),
        orientation="h",
        title="Cross-Source Problem Theme Distribution (%)",
        labels={"value": "Proportion within Platform (%)", "y": "Source Platform", "variable": "Problem Theme"},
        color_discrete_sequence=px.colors.qualitative.Safe,
    )
    fig.update_layout(
        barmode="stack",
        margin=dict(l=10, r=10, t=40, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
        height=380,
    )
    return fig


def render_cross_source_sentiment_chart(crosstab: pd.DataFrame) -> go.Figure:
    """Renders grouped bar chart of sentiment by source."""
    if crosstab.empty:
        return go.Figure()

    df_melt = crosstab.reset_index().melt(id_vars="source_display", var_name="Sentiment", value_name="Percentage")
    color_map = {"positive": "#10B981", "neutral": "#6B7280", "negative": "#EF4444"}

    fig = px.bar(
        df_melt,
        x="source_display",
        y="Percentage",
        color="Sentiment",
        barmode="group",
        title="Sentiment Polarity Distribution Across Channels (%)",
        labels={"source_display": "Source Channel", "Percentage": "% of Feedback in Channel"},
        color_discrete_map=color_map,
    )
    fig.update_layout(
        margin=dict(l=10, r=10, t=40, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=350,
    )
    return fig


def render_problem_theme_bar(df: pd.DataFrame) -> go.Figure:
    """Renders horizontal bar chart of problem themes with exact counts."""
    if df.empty or "problem_theme" not in df.columns:
        return go.Figure()

    counts = df["problem_theme"].value_counts().reset_index()
    counts.columns = ["theme", "count"]
    counts = counts.sort_values(by="count", ascending=True)

    fig = px.bar(
        counts,
        x="count",
        y="theme",
        orientation="h",
        text="count",
        title="Problem Themes Ranked by Empirical Frequency",
        labels={"count": "Feedback Count", "theme": "Problem Theme"},
        color="count",
        color_continuous_scale="Teal",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        margin=dict(l=10, r=10, t=40, b=30),
        height=380,
        coloraxis_showscale=False,
    )
    return fig


def render_stage_vs_theme_heatmap(df: pd.DataFrame) -> go.Figure:
    """Renders heatmap of User Journey Stage vs Problem Theme."""
    if df.empty or "user_journey_stage" not in df.columns or "problem_theme" not in df.columns:
        return go.Figure()

    ct = pd.crosstab(df["user_journey_stage"], df["problem_theme"])
    fig = px.imshow(
        ct,
        text_auto=True,
        labels=dict(x="Problem Theme", y="Journey Stage", color="Count"),
        x=ct.columns.tolist(),
        y=ct.index.tolist(),
        color_continuous_scale="Purples",
        aspect="auto",
    )
    fig.update_layout(
        title="Journey Stage vs. Problem Theme Matrix",
        margin=dict(l=10, r=10, t=40, b=30),
        height=380,
    )
    return fig


def render_opportunity_matrix_scatter(opp_df: pd.DataFrame) -> go.Figure:
    """
    Renders 2D Opportunity Matrix scatter plot:
      - X: Frequency Score (Volume impact)
      - Y: Severity & User Impact Score
      - Bubble Size: Opportunity Score
      - Color: Priority Tier
    """
    if opp_df.empty:
        return go.Figure()

    fig = px.scatter(
        opp_df,
        x="frequency_score",
        y="severity_score",
        size="opportunity_score",
        color="priority_tier",
        text="opp_id",
        hover_name="opportunity_name",
        hover_data={
            "opp_id": False,
            "theme": True,
            "opportunity_score": ":.3f",
            "frequency_count": True,
            "product_recommendation": True,
        },
        title="Opportunity Prioritization Matrix: Frequency vs. Severity",
        labels={
            "frequency_score": "Frequency Score (0.00 – 1.00)",
            "severity_score": "Severity Score (0.00 – 1.00)",
            "priority_tier": "Priority Tier",
            "opportunity_score": "Opportunity Score",
        },
        color_discrete_map={
            "P0 — Critical": "#DC2626",
            "P1 — High": "#F59E0B",
            "P2 — Medium": "#3B82F6",
        },
        size_max=35,
    )
    fig.update_traces(textposition="top center")
    fig.update_layout(
        xaxis=dict(range=[0.2, 1.05]),
        yaxis=dict(range=[0.3, 1.05]),
        margin=dict(l=10, r=10, t=40, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=450,
    )
    return fig

