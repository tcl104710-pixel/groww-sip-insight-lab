"""
Groww SIP Insight Lab — SIP Relevance Filter
============================================
Identifies, scores, and filters feedback directly relevant to SIP (Systematic Investment Plan)
and mutual fund experiences across all 4 collected sources.

Relevance Dimensions:
1. SIP investment experience & lifecycle
2. SIP continuation, pausing, stopping, or cancellation
3. Returns, XIRR, CAGR, and investment losses
4. Market fluctuations, volatility, and corrections
5. Failed SIP instalments, bank mandates, eNACH, and auto-debit issues
6. Monthly affordability, financial constraints, and cash crunches
7. Investment tracking, NAV delays, unit allocation, and statement verification
8. Customer support unresponsiveness and investor education gaps

Deliverables:
- sip_feedback_relevant.csv (root & data/)
- data/sip_feedback_irrelevant.csv
"""

import os
import sys
import re
import logging
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("pipeline.filter_sip")

# Category Patterns
RELEVANCE_PATTERNS = {
    "mandate_payment_issues": re.compile(
        r"\b(mandate|auto-?debit|autopay|auto-?pay|enach|nach|failed|failure|rejected|deducted.*not.*invested|"
        r"not.*credited|pending|stuck|double.*debit|bank.*charges|bounce.*charge|penalty|"
        r"insufficient.*balance|biller|standing.*instruction)\b",
        re.IGNORECASE,
    ),
    "continuation_pause_stop": re.compile(
        r"\b(pause|stop|cancel|cancelled|discontinue|terminate|halt|resume|skip|hold|"
        r"close.*sip|closed.*sip|withdraw|redeem|redemption|exit.*load|switch|swp|stp)\b",
        re.IGNORECASE,
    ),
    "returns_losses_volatility": re.compile(
        r"\b(return|returns|loss|losses|negative|profit|cagr|xirr|red|underperform|"
        r"market.*crash|correction|dip|fluctuation|volatilit|volatile|bear.*market|"
        r"down\s+\d+%|minus\s+\d+%|dropping|fall|nifty|sensex)\b",
        re.IGNORECASE,
    ),
    "affordability_constraints": re.compile(
        r"\b(afford|affordability|salary|job.*loss|unemployed|emergency|cash.*crunch|"
        r"tight.*budget|budget.*constraint|financial.*constraint|no.*money|short.*of.*money|"
        r"monthly.*expense|cannot.*pay|unable.*to.*pay)\b",
        re.IGNORECASE,
    ),
    "tracking_portfolio_nav": re.compile(
        r"\b(nav|nav.*delay|unit|units.*allocat|portfolio.*track|statement|cams|kfintech|"
        r"cas|folio|dashboard|graph|wrong.*nav|delayed.*nav|balance.*mismatch)\b",
        re.IGNORECASE,
    ),
    "support_and_education": re.compile(
        r"\b(customer.*support|customer.*care|ticket|helpdesk|support.*team|no.*response|"
        r"unresponsive|helpless|guidance|beginner|don't.*know|where.*to.*invest|"
        r"learn|advice|recommendation|confusion|mislead)\b",
        re.IGNORECASE,
    ),
    "sip_general_investment": re.compile(
        r"\b(sip|systematic.*investment|mutual.*fund|mutual.*funds|index.*fund|"
        r"small.*cap|mid.*cap|large.*cap|flexi.*cap|elss|groww.*app|groww.*sip|"
        r"investing.*monthly|monthly.*investment|instalment|installment)\b",
        re.IGNORECASE,
    ),
}

CORE_SIP_KEYWORDS = re.compile(
    r"\b(sip|sips|mutual\s*fund|mutual\s*funds|autopay|auto\s*debit|mandate|instalment|installment|folio|elss|nav)\b",
    re.IGNORECASE,
)


def evaluate_sip_relevance(text: str) -> tuple[bool, float, list[str], str]:
    """
    Evaluates text against relevance dimensions.
    Returns: (is_relevant, score, matched_categories, primary_category)
    """
    if not text or not isinstance(text, str):
        return False, 0.0, [], "none"

    matched = []
    has_core_sip = bool(CORE_SIP_KEYWORDS.search(text))

    for cat_name, pattern in RELEVANCE_PATTERNS.items():
        if pattern.search(text):
            matched.append(cat_name)

    # Score calculation
    base_score = 0.0
    if has_core_sip:
        base_score += 0.40

    # Weight specific high-value categories
    high_value_cats = ["mandate_payment_issues", "continuation_pause_stop", "returns_losses_volatility", "affordability_constraints"]
    for cat in matched:
        if cat in high_value_cats:
            base_score += 0.20
        elif cat != "sip_general_investment":
            base_score += 0.10
        else:
            base_score += 0.05

    score = min(1.0, round(base_score, 2))

    # Relevant if: has core SIP mention AND at least one thematic hit, or score >= 0.35, or explicit SIP problem
    is_relevant = (has_core_sip and len(matched) >= 2) or (score >= 0.35) or (
        bool(re.search(r"\b(groww|sip)\b", text, re.IGNORECASE)) and any(c in matched for c in high_value_cats)
    )

    primary_category = "none"
    if is_relevant:
        # Prioritize high-impact categories
        for cat in high_value_cats:
            if cat in matched:
                primary_category = cat
                break
        if primary_category == "none" and matched:
            primary_category = matched[0]
        elif primary_category == "none":
            primary_category = "sip_general_investment"

    return is_relevant, score, matched, primary_category


def filter_sip_feedback(df_combined: pd.DataFrame = None) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Filters combined feedback into relevant and irrelevant subsets.
    Saves outputs to CSV.
    """
    if df_combined is None:
        combined_path = PROJECT_ROOT / "sip_feedback_combined.csv"
        if not combined_path.exists():
            combined_path = DATA_DIR / "sip_feedback_combined.csv"
        if not combined_path.exists():
            raise FileNotFoundError(f"Combined feedback file not found at {combined_path}")
        df_combined = pd.read_csv(combined_path, encoding="utf-8")

    logger.info("Evaluating SIP relevance on %d combined records...", len(df_combined))

    relevance_flags = []
    relevance_scores = []
    matched_cats = []
    primary_cats = []

    for _, row in df_combined.iterrows():
        text = str(row.get("cleaned_text") or row.get("raw_text") or "")
        is_rel, score, cats, primary = evaluate_sip_relevance(text)
        relevance_flags.append(is_rel)
        relevance_scores.append(score)
        matched_cats.append(";".join(cats))
        primary_cats.append(primary)

    df_combined["is_sip_relevant"] = relevance_flags
    df_combined["relevance_score"] = relevance_scores
    df_combined["matched_categories"] = matched_cats
    df_combined["sip_category"] = primary_cats

    df_relevant = df_combined[df_combined["is_sip_relevant"]].copy()
    df_irrelevant = df_combined[~df_combined["is_sip_relevant"]].copy()

    # Save relevant dataset
    root_relevant = PROJECT_ROOT / "sip_feedback_relevant.csv"
    data_relevant = DATA_DIR / "sip_feedback_relevant.csv"
    df_relevant.to_csv(root_relevant, index=False, encoding="utf-8")
    df_relevant.to_csv(data_relevant, index=False, encoding="utf-8")

    # Save irrelevant dataset for auditability
    data_irrelevant = DATA_DIR / "sip_feedback_irrelevant.csv"
    df_irrelevant.to_csv(data_irrelevant, index=False, encoding="utf-8")

    stats = {
        "total_combined": len(df_combined),
        "relevant_count": len(df_relevant),
        "irrelevant_count": len(df_irrelevant),
        "relevant_pct": round(len(df_relevant) / max(1, len(df_combined)) * 100, 2),
        "category_breakdown": df_relevant["sip_category"].value_counts().to_dict(),
        "source_breakdown": df_relevant["source"].value_counts().to_dict(),
    }

    logger.info(
        "SIP relevance filter complete: %d relevant (%.1f%%) vs %d irrelevant.",
        len(df_relevant),
        stats["relevant_pct"],
        len(df_irrelevant),
    )
    return df_relevant, df_irrelevant, stats


if __name__ == "__main__":
    rel_df, irrel_df, stats = filter_sip_feedback()
    print(f"Total Relevant: {len(rel_df)}")
    print("Category Breakdown:", stats["category_breakdown"])
    print("Source Breakdown:", stats["source_breakdown"])

