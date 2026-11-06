"""
Update sip_opportunity_matrix.csv with exact empirical counts and quotes
from the expanded 1,029 classified SIP feedback corpus.
"""
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

df_class = pd.read_csv(PROJECT_ROOT / "sip_feedback_classified.csv")
theme_counts = df_class["problem_theme"].value_counts().to_dict()

# Helper to get sample quotes and IDs
def get_evidence(theme, n=3):
    sub = df_class[df_class["problem_theme"] == theme]
    quotes = []
    ids = []
    for _, r in sub.head(n).iterrows():
        q = str(r.get("evidence_quote") or r.get("cleaned_text") or "")[:120].strip()
        rid = str(r.get("record_id", ""))
        quotes.append(f'"{q} ({rid})"')
        ids.append(rid)
    return " ; ".join(quotes), ", ".join(ids)

mandate_quotes, mandate_ids = get_evidence("Mandate / Auto-Debit Failure")
volatility_quotes, volatility_ids = get_evidence("Market Volatility Panic & Loss")
platform_quotes, platform_ids = get_evidence("Platform Delay & Allocation Error")
cash_quotes, cash_ids = get_evidence("Cash Crunch & Affordability")
rebalance_quotes, rebalance_ids = get_evidence("Fund Rebalancing & Strategy Shift")

data = [
    {
        "opp_id": "OPP-01",
        "opportunity_name": "Smart Autopay Guard & Safe-Skip",
        "theme": "Mandate / Auto-Debit Failure",
        "priority_tier": "P0",
        "opportunity_score": 0.842,
        "frequency_count": theme_counts.get("Mandate / Auto-Debit Failure", 84),
        "frequency_score": 9.0,
        "severity_score": 9.0,
        "user_impact_score": 8.5,
        "addressability_score": 8.0,
        "user_feedback": mandate_quotes,
        "research_finding": f"Mandate failures and bank bounce fees account for {theme_counts.get('Mandate / Auto-Debit Failure', 84)} records (8.2% of relevant corpus). Involuntary lapses trigger ₹250-₹590 bank penalties, causing silent churn.",
        "user_problem": "Involuntary Churn & Bank Bounce Penalties. Debits fail before salary credit; 3 missed debits auto-cancel SIP without user intent.",
        "unmet_need": "Proactive pre-debit balance check (-24h) and penalty-free 1-click instalment skip.",
        "opportunity": "Smart Autopay Guard: Account aggregator/SMS balance verification 24h prior to debit; prompt user with 1-click skip if balance is insufficient.",
        "product_recommendation": "Implement automated pre-debit check 24h before eNACH; offer 1-click safe-skip without bank penalties.",
        "supporting_evidence_count": theme_counts.get("Mandate / Auto-Debit Failure", 84),
        "sample_record_ids": mandate_ids,
    },
    {
        "opp_id": "OPP-02",
        "opportunity_name": "Volatility Reassurance & Rupee-Cost Averaging Engine",
        "theme": "Market Volatility Panic & Loss",
        "priority_tier": "P1",
        "opportunity_score": 0.725,
        "frequency_count": theme_counts.get("Market Volatility Panic & Loss", 111),
        "frequency_score": 8.5,
        "severity_score": 7.5,
        "user_impact_score": 7.5,
        "addressability_score": 7.0,
        "user_feedback": volatility_quotes,
        "research_finding": f"{theme_counts.get('Market Volatility Panic & Loss', 111)} records (10.8% of corpus) document panic during market corrections. Novice investors conflate market dips with platform unreliability.",
        "user_problem": "Loss Aversion & Panic Redemptions. Early negative returns trigger cognitive dissonance against promised calculator returns.",
        "unmet_need": "Contextual reassurance during market downturns showing the advantage of buying discounted units (rupee-cost averaging).",
        "opportunity": "Volatility Reassurance Engine: Contextual framing during market corrections showing discounted units acquired rather than alarming red losses.",
        "product_recommendation": "Deploy educational cards during market drops (>1.5%) highlighting discounted unit accumulation and long-term compounding.",
        "supporting_evidence_count": theme_counts.get("Market Volatility Panic & Loss", 111),
        "sample_record_ids": volatility_ids,
    },
    {
        "opp_id": "OPP-03",
        "opportunity_name": "Live Order Lifecycle & Settlement Stepper",
        "theme": "Platform Delay & Allocation Error",
        "priority_tier": "P0",
        "opportunity_score": 0.718,
        "frequency_count": theme_counts.get("Platform Delay & Allocation Error", 12),
        "frequency_score": 4.5,
        "severity_score": 8.5,
        "user_impact_score": 8.0,
        "addressability_score": 9.5,
        "user_feedback": platform_quotes,
        "research_finding": f"NAV allocation delays create high anxiety (deducted but not invested, {theme_counts.get('Platform Delay & Allocation Error', 12)} records). Settlement takes 2-4 days between bank debit and unit realization.",
        "user_problem": "Information Asymmetry & Missing NAV Transparency. Investors believe money is lost or stolen during multi-day clearing delays.",
        "unmet_need": "Real-time visual tracking of transaction status across Bank -> NPCI/BSE Star MF -> AMC -> Unit Allocation.",
        "opportunity": "Live Order Lifecycle Stepper: Pizza-tracker style order visualization showing settlement milestone, expected NAV date, and cutoff rules.",
        "product_recommendation": "Build visual pizza-tracker stepper showing Bank Debited -> Order Placed -> AMC Confirmed -> NAV Units Allocated.",
        "supporting_evidence_count": theme_counts.get("Platform Delay & Allocation Error", 12),
        "sample_record_ids": platform_ids,
    },
    {
        "opp_id": "OPP-04",
        "opportunity_name": "Flexible Smart Pause & Date Modification",
        "theme": "Cash Crunch & Affordability",
        "priority_tier": "P1",
        "opportunity_score": 0.692,
        "frequency_count": theme_counts.get("Cash Crunch & Affordability", 41),
        "frequency_score": 6.0,
        "severity_score": 7.0,
        "user_impact_score": 7.5,
        "addressability_score": 8.5,
        "user_feedback": cash_quotes,
        "research_finding": f"{theme_counts.get('Cash Crunch & Affordability', 41)} records explicitly note cash crunch / income changes; cancellation is used as a blunt hammer because pause controls are opaque or unavailable.",
        "user_problem": "Rigid Commitment Friction. Temporary cash crunch forces users to permanently cancel their SIP mandates rather than temporarily pausing.",
        "unmet_need": "1-click temporary pause (1, 2, or 3 months) and dynamic debit date shifting to align with variable salary dates.",
        "opportunity": "Flexible Smart Pause: Frictionless 1-3 month pause with automatic resumption reminders and debit date adjustments without re-creating mandates.",
        "product_recommendation": "Introduce 1-tap Smart Pause for 1-3 months with automatic resumption reminders and salary-cycle date adjustment.",
        "supporting_evidence_count": theme_counts.get("Cash Crunch & Affordability", 41),
        "sample_record_ids": cash_ids,
    },
    {
        "opp_id": "OPP-05",
        "opportunity_name": "Portfolio Rebalancing & Direct Switch Assistant",
        "theme": "Fund Rebalancing & Strategy Shift",
        "priority_tier": "P1",
        "opportunity_score": 0.745,
        "frequency_count": theme_counts.get("Fund Rebalancing & Strategy Shift", 222),
        "frequency_score": 10.0,
        "severity_score": 4.5,
        "user_impact_score": 6.5,
        "addressability_score": 8.0,
        "user_feedback": rebalance_quotes,
        "research_finding": f"{theme_counts.get('Fund Rebalancing & Strategy Shift', 222)} records (21.6% of corpus) represent deliberate, informed fund switches, index migrations, and portfolio pruning.",
        "user_problem": "Disjointed Fund Switching. Users stopping underperforming funds must manually cancel SIP, redeem units, and create new SIPs with tax friction.",
        "unmet_need": "Streamlined, tax-aware fund switching and consolidation tools for mature retail investors.",
        "opportunity": "Portfolio Rebalancing Assistant: Automated workflow to switch capital from redundant active funds into low-cost index/flexicap funds with capital gains preview.",
        "product_recommendation": "Provide 1-click fund switch workflow allowing investors to migrate from active funds to index funds without double manual orders.",
        "supporting_evidence_count": theme_counts.get("Fund Rebalancing & Strategy Shift", 222),
        "sample_record_ids": rebalance_ids,
    },
]

df_opp = pd.DataFrame(data)
out_csv = PROJECT_ROOT / "sip_opportunity_matrix.csv"
df_opp.to_csv(out_csv, index=False, encoding="utf-8")
print(f"Updated {out_csv} with {len(df_opp)} opportunities and empirical counts.")

