"""
SIP Insight Lab — Production Research Data Bundler
==================================================
Compiles the classified feedback dataset, cross-source metrics, recurring patterns,
and opportunity rankings into public/data/research_data.json for edge-accelerated
Vercel deployment with zero cold-start latency.
"""

import sys
import json
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.dashboard.data_loader import DashboardDataLoader


def bundle_data():
    loader = DashboardDataLoader()
    df_research = loader.load_research_corpus()
    stats = loader.get_research_overview_stats()
    cross_source = loader.get_cross_source_analysis(df_research)
    insights = loader.get_recurring_insights(df_research)
    opps = loader.get_opportunity_matrix(df_research)
    discovery_chain = loader.get_discovery_chain()
    assignment_eval = loader.get_assignment_evaluation(df_research)

    # Convert DataFrames to JSON-serializable structures
    cs_summary = cross_source["summary_table"].to_dict(orient="records") if not cross_source["summary_table"].empty else []
    theme_ct = cross_source["theme_crosstab"].to_dict(orient="index") if not cross_source["theme_crosstab"].empty else {}
    sent_ct = cross_source["sentiment_crosstab"].to_dict(orient="index") if not cross_source["sentiment_crosstab"].empty else {}

    # Records list (sanitize NaN/floats)
    clean_records = []
    for _, r in df_research.iterrows():
        rec = r.to_dict()
        for k, v in rec.items():
            if pd.isna(v):
                rec[k] = None
            elif isinstance(v, pd.Timestamp):
                rec[k] = v.isoformat()
        clean_records.append(rec)

    opp_records = opps.to_dict(orient="records") if not opps.empty else []
    chain_records = discovery_chain.to_dict(orient="records") if not discovery_chain.empty else []

    payload = {
        "generated_at": pd.Timestamp.now().isoformat(),
        "stats": stats,
        "records": clean_records,
        "cross_source": {
            "summary": cs_summary,
            "theme_crosstab": theme_ct,
            "sentiment_crosstab": sent_ct,
        },
        "insights": insights,
        "opportunities": opp_records,
        "discovery_chain": chain_records,
        "assignment_questions": assignment_eval,
    }

    out_dir = PROJECT_ROOT / "public" / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "research_data.json"

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # Also sync to api/data/ for Vercel Serverless Function packaging
    api_data_dir = PROJECT_ROOT / "api" / "data"
    api_data_dir.mkdir(parents=True, exist_ok=True)
    api_out_file = api_data_dir / "research_data.json"
    with open(api_out_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Successfully bundled {len(clean_records)} research records into {out_file} and {api_out_file} ({out_file.stat().st_size:,} bytes).")


if __name__ == "__main__":
    bundle_data()

