"""
SIP Insight Lab — Counter-Evidence Agent (Task 3.11)
=====================================================
Stress-tests emerging themes and hypotheses against the labelled feedback
store to actively prevent confirmation bias.

Implements the 4 Counter-Evidence Strategies:
  1. Inverse Query       : Searches for praise or retention in the same problem area
  2. Segment Drill-down  : Tests if theme is segment-skewed vs universal
  3. Temporal Check      : Distinguishes transitory spikes from structural churn
  4. Frequency Sanity    : Checks if theme is driven by a vocal minority (< 5%)

Usage:
    from src.agents.counter_evidence import CounterEvidenceAgent
    agent = CounterEvidenceAgent(conn)
    analysis = agent.analyze_theme(
        theme="Bank mandate failures are the primary cause of early SIP churn",
        root_cause="RC-01",
    )
"""

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class StrategyResult:
    strategy_name: str
    counter_evidence_found: bool
    strength: str  # 'High' | 'Medium' | 'Low' | 'None'
    finding_summary: str
    metrics: Dict[str, Any]
    contradicting_quotes: List[str] = field(default_factory=list)


@dataclass
class CounterEvidenceAnalysis:
    theme: str
    root_cause: str
    corpus_size: int
    theme_count: int
    theme_share_pct: float
    counter_evidence_strength: str  # 'High' | 'Medium' | 'Low' | 'None'
    revised_confidence: str         # 'High' | 'Medium' | 'Low'
    recommendation: str             # 'Proceed with caveat' | 'Downgrade confidence' | 'Pivot hypothesis' | 'Validated'
    synthesis_guidance: str
    contradicting_quotes: List[str]
    strategy_results: Dict[str, StrategyResult]


class CounterEvidenceAgent:
    """
    Adversarial analysis agent operating over the labelled_item and cleaned_item tables.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_corpus_size(self) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM labelled_item")
        return cursor.fetchone()[0]

    def analyze_theme(
        self,
        theme: str,
        root_cause: str,
        lifecycle_stage: Optional[str] = None,
        segment_focus: Optional[str] = None,
    ) -> CounterEvidenceAnalysis:
        """
        Execute the 4 adversarial strategies for a proposed theme.
        """
        corpus_size = self.get_corpus_size()
        cursor = self.conn.cursor()

        # Count items matching the theme's root cause
        rc_query = "SELECT COUNT(*) FROM labelled_item WHERE root_cause = ?"
        params = [root_cause]
        if lifecycle_stage:
            rc_query += " AND lifecycle_stage = ?"
            params.append(lifecycle_stage)

        theme_count = cursor.execute(rc_query, params).fetchone()[0]
        theme_share_pct = round((theme_count / max(corpus_size, 1)) * 100, 2)

        # Run 4 strategies
        res_inverse = self._strategy_inverse_query(root_cause)
        res_segment = self._strategy_segment_drilldown(root_cause)
        res_temporal = self._strategy_temporal_check(root_cause)
        res_frequency = self._strategy_frequency_sanity(theme_count, corpus_size)

        strategies = {
            "inverse_query": res_inverse,
            "segment_drilldown": res_segment,
            "temporal_check": res_temporal,
            "frequency_sanity": res_frequency,
        }

        # Aggregate counter-evidence strength
        high_signals = sum(1 for s in strategies.values() if s.strength == "High")
        med_signals = sum(1 for s in strategies.values() if s.strength == "Medium")

        if high_signals >= 2 or (high_signals == 1 and med_signals >= 2):
            overall_strength = "High"
            revised_conf = "Low"
            recommendation = "Downgrade confidence or Pivot hypothesis"
            guidance = f"Strong contradicting evidence found across multiple strategies. The assumption that '{root_cause}' uniquely drives this theme is challenged by positive counter-examples and cohort skew."
        elif high_signals == 1 or med_signals >= 2:
            overall_strength = "Medium"
            revised_conf = "Medium"
            recommendation = "Proceed with caveat"
            guidance = f"Moderate counter-evidence detected. Recommend adding qualification regarding segment specificity or temporary timing."
        elif med_signals == 1:
            overall_strength = "Low"
            revised_conf = "High"
            recommendation = "Proceed with caveat"
            guidance = f"Minor counter-evidence noted, but the primary pattern holds robustly across the corpus."
        else:
            overall_strength = "None"
            revised_conf = "High"
            recommendation = "Validated"
            guidance = f"No significant counter-evidence detected. The theme is well-supported and resilient across segments and time."

        # Collect unique contradicting quotes
        all_quotes = []
        for s in strategies.values():
            for q in s.contradicting_quotes:
                if q not in all_quotes:
                    all_quotes.append(q)

        return CounterEvidenceAnalysis(
            theme=theme,
            root_cause=root_cause,
            corpus_size=corpus_size,
            theme_count=theme_count,
            theme_share_pct=theme_share_pct,
            counter_evidence_strength=overall_strength,
            revised_confidence=revised_conf,
            recommendation=recommendation,
            synthesis_guidance=guidance,
            contradicting_quotes=all_quotes[:5],
            strategy_results=strategies,
        )

    def _strategy_inverse_query(self, root_cause: str) -> StrategyResult:
        """
        Strategy 1: Search for positive counter-examples or praise in the same functional area.
        e.g., if RC-02 (UX Friction), search for users praising the UI/UX or auto-pilot experience.
        """
        cursor = self.conn.cursor()

        # Look for retained users or positive sentiment users praising automation / experience
        query = """
            SELECT c.cleaned_text, l.sentiment_score, l.retention_factor
            FROM labelled_item l
            JOIN cleaned_item c ON l.item_id = c.item_id
            WHERE (l.sentiment_score > 0.4 OR l.retention_factor IS NOT NULL)
              AND l.root_cause != ?
            ORDER BY l.sentiment_score DESC
            LIMIT 10;
        """
        rows = cursor.execute(query, (root_cause,)).fetchall()

        # Find quotes specifically praising ease, UI, or mandate reliability
        matching_quotes = []
        for text, score, rf in rows:
            lower = text.lower()
            if any(w in lower for w in ["easy", "smooth", "clean", "set it", "disciplined", "good app", "happy", "auto debit"]):
                matching_quotes.append(text[:120].strip())

        found = len(matching_quotes) > 0
        strength = "Medium" if len(matching_quotes) >= 3 else "Low" if found else "None"

        summary = (
            f"Found {len(matching_quotes)} items where investors actively praised the seamless experience, "
            f"indicating the issue is not universally experienced across all users."
            if found
            else "No opposing praise found in the corpus."
        )

        return StrategyResult(
            strategy_name="Inverse Query",
            counter_evidence_found=found,
            strength=strength,
            finding_summary=summary,
            metrics={"opposing_praise_count": len(matching_quotes)},
            contradicting_quotes=matching_quotes[:2],
        )

    def _strategy_segment_drilldown(self, root_cause: str) -> StrategyResult:
        """
        Strategy 2: Check if the theme is concentrated in a specific segment or holds universally.
        """
        cursor = self.conn.cursor()
        query = """
            SELECT investor_segment, COUNT(*)
            FROM labelled_item
            WHERE root_cause = ?
            GROUP BY investor_segment;
        """
        rows = cursor.execute(query, (root_cause,)).fetchall()

        total = sum(r[1] for r in rows)
        segments: Dict[str, int] = {}
        for seg_json, cnt in rows:
            try:
                seg = json.loads(seg_json) if isinstance(seg_json, str) else seg_json
                inc = seg.get("income_stability", "unknown")
                segments[inc] = segments.get(inc, 0) + cnt
            except Exception:
                pass

        # Check maximum concentration in any single segment
        max_share = max((cnt / max(total, 1) for cnt in segments.values()), default=0.0)
        found_skew = max_share > 0.65 and total >= 5

        strength = "High" if max_share > 0.80 and total >= 5 else "Medium" if found_skew else "Low" if total > 0 else "None"

        summary = (
            f"Segment concentration is {max_share*100:.1f}%. The issue is heavily skewed to specific cohorts rather than universal."
            if found_skew
            else f"Issue is distributed across cohorts with max single-segment share of {max_share*100:.1f}%."
        )

        return StrategyResult(
            strategy_name="Segment Drill-down",
            counter_evidence_found=found_skew,
            strength=strength,
            finding_summary=summary,
            metrics={"segment_distribution": segments, "max_segment_share": round(max_share, 3)},
        )

    def _strategy_temporal_check(self, root_cause: str) -> StrategyResult:
        """
        Strategy 3: Check whether occurrences are steady across time or a single temporal spike.
        """
        cursor = self.conn.cursor()
        query = """
            SELECT substr(classified_at, 1, 10) as day, COUNT(*)
            FROM labelled_item
            WHERE root_cause = ?
            GROUP BY day
            ORDER BY day;
        """
        rows = cursor.execute(query, (root_cause,)).fetchall()

        day_counts = [r[1] for r in rows]
        total_days = len(day_counts)

        # Check if single day represents > 75% of occurrences
        max_day = max(day_counts, default=0)
        total = sum(day_counts)
        is_spike = (max_day / max(total, 1)) > 0.80 and total >= 10

        strength = "High" if is_spike else "Low" if total > 0 else "None"
        summary = (
            f"Temporal spike detected: {max_day}/{total} items clustered on a single date, suggesting a transitory incident."
            if is_spike
            else "Issue exhibits consistent presence over collection timeframe."
        )

        return StrategyResult(
            strategy_name="Temporal Check",
            counter_evidence_found=is_spike,
            strength=strength,
            finding_summary=summary,
            metrics={"active_days": total_days, "peak_day_share": round(max_day / max(total, 1), 3)},
        )

    def _strategy_frequency_sanity(self, theme_count: int, corpus_size: int) -> StrategyResult:
        """
        Strategy 4: Frequency Sanity — check if the theme is driven by a vocal minority (< 5%).
        """
        share = (theme_count / max(corpus_size, 1))
        is_minority = share < 0.05 and theme_count > 0

        strength = "High" if is_minority and share < 0.03 else "Medium" if is_minority else "None"
        summary = (
            f"Vocal minority warning: theme accounts for only {share*100:.1f}% of feedback corpus (< 5% threshold). Risk of over-indexing."
            if is_minority
            else f"Theme represents substantial volume ({share*100:.1f}% of corpus), confirming high operational significance."
        )

        return StrategyResult(
            strategy_name="Frequency Sanity",
            counter_evidence_found=is_minority,
            strength=strength,
            finding_summary=summary,
            metrics={"share_percentage": round(share * 100, 2), "is_vocal_minority": is_minority},
        )
