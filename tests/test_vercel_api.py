"""
Groww SIP Insight Lab — Vercel API & Endpoints Test Suite
=========================================================
Tests for FastAPI serverless endpoints and business logic deployed on Vercel:
- health_check (/api/health)
- get_stats (/api/stats)
- get_cross_source (/api/cross-source)
- get_records (/api/records - unfiltered, filtered, paginated)
- get_insights (/api/insights)
- get_opportunities (/api/opportunities)
- get_discovery_chain (/api/discovery-chain)
- get_assignment_evaluation (/api/assignment-evaluation)
- ask_assistant (/api/ask)
"""

import pytest
from api.index import (
    health_check,
    get_stats,
    get_cross_source,
    get_records,
    get_insights,
    get_opportunities,
    get_discovery_chain,
    get_assignment_evaluation,
    ask_assistant,
    AskRequest,
    get_bundled_data,
)
from fastapi import HTTPException


def test_health_endpoint():
    res = health_check()
    assert res["status"] == "ok"
    assert "SIP Insight Lab" in res["service"]
    assert res["records_loaded"] >= 1000


def test_stats_endpoint():
    stats = get_stats()
    assert stats["total_raw"] >= 4000
    assert stats["total_cleaned"] >= 3000
    assert stats["total_relevant"] >= 1000
    assert stats["total_classified"] >= 1000
    assert stats["relevance_rate_pct"] > 20.0
    assert "source_classified_breakdown" in stats
    assert stats["source_classified_breakdown"]["Reddit"] >= 200


def test_cross_source_endpoint():
    data = get_cross_source()
    assert "summary" in data
    assert len(data["summary"]) >= 3
    assert "theme_crosstab" in data
    assert "sentiment_crosstab" in data


def test_insights_endpoint():
    insights = get_insights()
    assert len(insights) >= 5
    first = insights[0]
    assert "insight_id" in first
    assert "title" in first
    assert "severity" in first
    assert "supporting_record_ids" in first
    assert len(first["supporting_record_ids"]) > 0


def test_opportunities_endpoint():
    opps = get_opportunities()
    assert len(opps) >= 4
    first = opps[0]
    assert "opportunity_name" in first
    assert "priority_tier" in first
    assert "opportunity_score" in first


def test_discovery_chain_endpoint():
    chain = get_discovery_chain()
    assert len(chain) == 5
    first = chain[0]
    assert "opp_id" in first
    assert "opportunity_name" in first
    assert "user_feedback" in first
    assert "research_finding" in first
    assert "user_problem" in first
    assert "unmet_need" in first
    assert "opportunity" in first


def test_assignment_evaluation_endpoint():
    questions = get_assignment_evaluation()
    assert len(questions) == 5
    q1 = questions[0]
    assert q1["question_id"] == "Q1"
    assert "research_finding" in q1
    assert "user_problem" in q1
    assert "unmet_need" in q1
    assert "opportunity" in q1
    assert len(q1["supporting_evidence"]) > 0


def test_records_unfiltered():
    data = get_records(limit=50, offset=0)
    assert data["total"] >= 1000
    assert len(data["records"]) == 50
    assert data["limit"] == 50
    assert data["offset"] == 0


def test_records_filtering_by_source():
    data = get_records(source="reddit", limit=300)
    assert data["total"] >= 200
    assert all(r["source"] == "reddit" for r in data["records"])


def test_records_filtering_by_theme():
    data = get_records(theme="Mandate / Auto-Debit Failure")
    assert data["total"] >= 80
    assert all(r["problem_theme"] == "Mandate / Auto-Debit Failure" for r in data["records"])


def test_records_filtering_by_sentiment():
    data = get_records(sentiment="positive")
    assert data["total"] >= 20
    assert all(r["sentiment"] == "positive" for r in data["records"])


def test_records_search_query():
    data = get_records(search="bounce")
    assert data["total"] > 0
    for r in data["records"]:
        blob = " ".join([
            str(r.get("cleaned_text", "")),
            str(r.get("raw_text", "")),
            str(r.get("evidence_quote", "")),
            str(r.get("classification_reason", ""))
        ]).lower()
        assert "bounce" in blob


def test_ask_assistant_empty_query():
    with pytest.raises(HTTPException) as excinfo:
        ask_assistant(AskRequest(query="   "))
    assert excinfo.value.status_code == 400


def test_ask_assistant_valid_query():
    data = ask_assistant(AskRequest(query="Why do users stop SIP?"))
    assert "answer" in data
    assert len(data["answer"]) > 20
    assert "citations" in data
    assert isinstance(data["citations"], list)
    if data["citations"]:
        cit = data["citations"][0]
        assert "record_id" in cit
        assert "source" in cit
        assert "quote" in cit


def test_vercel_json_config():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    vj_path = root / "vercel.json"
    assert vj_path.exists()
    config = json.loads(vj_path.read_text(encoding="utf-8"))
    assert "rewrites" in config
    assert any("/api" in r.get("source", "") and "api/index.py" in r.get("destination", "") for r in config["rewrites"])


def test_vercel_static_assets():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    
    # 1. HTML5 SPA
    html_file = root / "public" / "index.html"
    assert html_file.exists()
    content = html_file.read_text(encoding="utf-8")
    assert "tabContent-canvasGallery" in content
    assert "imageLightboxModal" in content

    # 2. Bundled research JSON
    json_file = root / "public" / "data" / "research_data.json"
    assert json_file.exists()
    assert json_file.stat().st_size > 1_000_000
    data = json.loads(json_file.read_text(encoding="utf-8"))
    assert len(data["records"]) >= 1000
    assert data["stats"]["total_classified"] >= 1000


def test_vercel_canvas_images():
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    grow_dir = root / "public" / "grow"
    assert grow_dir.exists()
    expected_canvases = [
        "1_overview.png",
        "2_investor_behaviour.png",
        "3_pause_discontinuation.png",
        "4_user_needs_opportunities.png",
        "5_evidence_explorer.png",
        "6_engine_evidence_log.png",
    ]
    for c in expected_canvases:
        img_p = grow_dir / c
        assert img_p.exists(), f"Missing canvas image {c}"
        assert img_p.stat().st_size > 500_000, f"Canvas image {c} is too small"


def test_vercel_csv_deliverables():
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    pub_dir = root / "public"
    expected_files = [
        "sip_feedback_combined.csv",
        "sip_feedback_classified.csv",
        "sip_evidence_log.csv",
        "sip_opportunity_matrix.csv",
        "sip_insights_report.md",
    ]
    for ef in expected_files:
        fp = pub_dir / ef
        assert fp.exists(), f"Missing deliverable in public: {ef}"
        assert fp.stat().st_size > 1000, f"File {ef} is unexpectedly small"


def test_vercel_api_data_sync():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    api_json = root / "api" / "data" / "research_data.json"
    pub_json = root / "public" / "data" / "research_data.json"
    assert api_json.exists(), "api/data/research_data.json missing for serverless packaging"
    assert pub_json.exists(), "public/data/research_data.json missing for edge static CDN"
    assert api_json.stat().st_size == pub_json.stat().st_size


def test_records_limit_2000():
    res = get_records(limit=2000)
    assert res["total"] >= 1000
    assert len(res["records"]) >= 1000


def test_serve_grow_image():
    from api.index import serve_grow_image
    res = serve_grow_image("1_overview.png")
    assert res.media_type == "image/png"
    assert len(res.body) > 500_000


def test_serve_data_file():
    from api.index import serve_data_file
    res = serve_data_file("research_data.json")
    assert res.media_type == "application/json"
    assert len(res.body) > 1_000_000
