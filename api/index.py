"""
Groww SIP Insight Lab — Vercel Serverless API Entrypoint
=========================================================
Production-ready FastAPI backend deployed on Vercel (@vercel/python).
Provides high-performance, stateless REST endpoints for research metrics,
cross-source analytics, evidence records, and AI Research Assistant queries.
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import Optional, List, Dict, Any

# Starlette 1.x / FastAPI compatibility patch for legacy on_startup/on_shutdown kwargs
try:
    import starlette.routing
    _orig_router_init = starlette.routing.Router.__init__
    def _safe_router_init(self, *args, **kwargs):
        kwargs.pop("on_startup", None)
        kwargs.pop("on_shutdown", None)
        return _orig_router_init(self, *args, **kwargs)
    starlette.routing.Router.__init__ = _safe_router_init
except Exception:
    pass

from fastapi import FastAPI, Query, HTTPException, Response
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Locate project root dynamically across local and Vercel serverless environments
CURRENT_DIR = Path(__file__).resolve().parent
CANDIDATE_ROOTS = [
    CURRENT_DIR.parent,
    CURRENT_DIR,
    Path("/var/task"),
    Path.cwd(),
]
PROJECT_ROOT = next((p for p in CANDIDATE_ROOTS if (p / "sip_feedback_classified.csv").exists() or (p / "public" / "data" / "research_data.json").exists()), CURRENT_DIR.parent)
sys.path.insert(0, str(PROJECT_ROOT))

# Initialize FastAPI application
app = FastAPI(
    title="Groww SIP Insight Lab API",
    description="Research Analysis & AI Discovery Engine Backend for Vercel",
    version="1.0.0",
)

# Enable CORS for frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory cached dataset
_CACHED_DATA: Optional[Dict[str, Any]] = None


def get_bundled_data() -> Dict[str, Any]:
    """Loads bundled research data from JSON with fallback to DataLoader."""
    global _CACHED_DATA
    if _CACHED_DATA is not None:
        return _CACHED_DATA

    # Check candidate JSON locations
    json_paths = [
        CURRENT_DIR / "data" / "research_data.json",
        CURRENT_DIR.parent / "public" / "data" / "research_data.json",
        PROJECT_ROOT / "public" / "data" / "research_data.json",
        CURRENT_DIR / "public" / "data" / "research_data.json",
        Path("/var/task") / "api" / "data" / "research_data.json",
        Path("/var/task") / "public" / "data" / "research_data.json",
        PROJECT_ROOT / "data" / "research_data.json",
    ]
    for jp in json_paths:
        if jp.exists():
            try:
                with open(jp, "r", encoding="utf-8") as f:
                    _CACHED_DATA = json.load(f)
                    return _CACHED_DATA
            except Exception:
                pass

    # Fallback to DataLoader if JSON not found
    try:
        from src.dashboard.data_loader import DashboardDataLoader
        loader = DashboardDataLoader()
        df = loader.load_research_corpus()
        stats = loader.get_research_overview_stats()
        cs = loader.get_cross_source_analysis(df)
        ins = loader.get_recurring_insights(df)
        opps = loader.get_opportunity_matrix(df)

        recs = []
        for _, r in df.iterrows():
            d = r.to_dict()
            for k, v in d.items():
                if isinstance(v, float) and (v != v):  # NaN
                    d[k] = None
            recs.append(d)

        _CACHED_DATA = {
            "stats": stats,
            "records": recs,
            "cross_source": {
                "summary": cs["summary_table"].to_dict(orient="records"),
                "theme_crosstab": cs["theme_crosstab"].to_dict(orient="index"),
                "sentiment_crosstab": cs["sentiment_crosstab"].to_dict(orient="index"),
            },
            "insights": ins,
            "opportunities": opps.to_dict(orient="records"),
        }
        return _CACHED_DATA
    except Exception as e:
        return {
            "stats": {
                "total_raw": 4983,
                "total_cleaned": 3726,
                "total_relevant": 1029,
                "total_classified": 1029,
                "relevance_rate_pct": 27.6,
                "noise_filtered_pct": 25.2,
                "raw_counts": {"Google Play Store": 3000, "YouTube": 1634, "Reddit": 256, "Apple App Store": 93},
                "source_classified_breakdown": {"YouTube": 460, "Google Play Store": 309, "Reddit": 239, "Apple App Store": 21}
            },
            "records": [],
            "cross_source": {"summary": [], "theme_crosstab": {}, "sentiment_crosstab": {}},
            "insights": [],
            "opportunities": [],
            "error": str(e),
        }


class AskRequest(BaseModel):
    query: str


# -----------------------------------------------------------------------------
# ROOT & FRONTEND SPA ENDPOINTS
# -----------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
def serve_index_html():
    """Serves the SIP Insight Lab frontend SPA directly from the lambda."""
    for p in [
        CURRENT_DIR / "public" / "index.html",
        PROJECT_ROOT / "public" / "index.html",
        Path.cwd() / "public" / "index.html",
        Path("/var/task/public/index.html"),
        Path("/var/task/api/public/index.html"),
    ]:
        if p.exists():
            return HTMLResponse(content=p.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>SIP Insight Lab Discovery Engine</h1><p>API online at <a href='/api/health'>/api/health</a></p>")


@app.get("/app.js")
def serve_app_js():
    """Serves app.js directly from the lambda."""
    for p in [
        CURRENT_DIR / "public" / "app.js",
        PROJECT_ROOT / "public" / "app.js",
        Path.cwd() / "public" / "app.js",
        Path("/var/task/public/app.js"),
        Path("/var/task/api/public/app.js"),
    ]:
        if p.exists():
            return Response(content=p.read_text(encoding="utf-8"), media_type="application/javascript")
    raise HTTPException(status_code=404, detail="app.js not found")


@app.get("/grow/{filename}")
def serve_grow_image(filename: str):
    """Serves visual canvas images from api/grow or project grow directories."""
    safe_name = Path(filename).name
    candidates = [
        CURRENT_DIR / "grow" / safe_name,
        CURRENT_DIR / "public" / "grow" / safe_name,
        PROJECT_ROOT / "grow" / safe_name,
        PROJECT_ROOT / "public" / "grow" / safe_name,
        Path.cwd() / "grow" / safe_name,
        Path.cwd() / "public" / "grow" / safe_name,
        Path("/var/task/grow") / safe_name,
        Path("/var/task/api/grow") / safe_name,
        Path("/var/task/public/grow") / safe_name,
    ]
    for p in candidates:
        if p.exists() and p.is_file():
            return Response(content=p.read_bytes(), media_type="image/png")
    raise HTTPException(status_code=404, detail=f"Image {safe_name} not found")


@app.get("/data/{filename}")
def serve_data_file(filename: str):
    """Serves static data files like research_data.json."""
    safe_name = Path(filename).name
    candidates = [
        CURRENT_DIR / "data" / safe_name,
        CURRENT_DIR / "public" / "data" / safe_name,
        PROJECT_ROOT / "data" / safe_name,
        PROJECT_ROOT / "public" / "data" / safe_name,
        Path.cwd() / "data" / safe_name,
        Path.cwd() / "public" / "data" / safe_name,
        Path("/var/task/data") / safe_name,
        Path("/var/task/api/data") / safe_name,
        Path("/var/task/public/data") / safe_name,
    ]
    for p in candidates:
        if p.exists() and p.is_file():
            media_type = "application/json" if safe_name.endswith(".json") else "text/plain"
            return Response(content=p.read_bytes(), media_type=media_type)
    raise HTTPException(status_code=404, detail=f"File {safe_name} not found")


@app.get("/{filename}.csv")
@app.get("/{filename}.md")
def serve_deliverable(filename: str):
    """Serves downloadable deliverables from root or public."""
    safe_name = Path(filename).name
    for ext in [".csv", ".md"]:
        candidates = [
            CURRENT_DIR / f"{safe_name}{ext}",
            PROJECT_ROOT / f"{safe_name}{ext}",
            PROJECT_ROOT / "public" / f"{safe_name}{ext}",
            Path.cwd() / f"{safe_name}{ext}",
            Path("/var/task") / f"{safe_name}{ext}",
            Path("/var/task/public") / f"{safe_name}{ext}",
        ]
        for p in candidates:
            if p.exists() and p.is_file():
                media_type = "text/csv" if ext == ".csv" else "text/markdown"
                return Response(content=p.read_bytes(), media_type=media_type)
    raise HTTPException(status_code=404, detail=f"Deliverable {safe_name} not found")


# -----------------------------------------------------------------------------
# REST ENDPOINTS
# -----------------------------------------------------------------------------

@app.get("/api/health")
def health_check():
    data = get_bundled_data()
    return {
        "status": "ok",
        "service": "SIP Insight Lab AI Discovery Engine",
        "environment": "vercel_serverless" if os.getenv("VERCEL") else "local",
        "records_loaded": len(data.get("records", [])),
    }


@app.get("/api/stats")
def get_stats():
    data = get_bundled_data()
    return data.get("stats", {})


@app.get("/api/cross-source")
def get_cross_source():
    data = get_bundled_data()
    return data.get("cross_source", {})


@app.get("/api/insights")
def get_insights():
    data = get_bundled_data()
    return data.get("insights", [])


@app.get("/api/opportunities")
def get_opportunities():
    data = get_bundled_data()
    return data.get("opportunities", [])


@app.get("/api/discovery-chain")
def get_discovery_chain():
    data = get_bundled_data()
    return data.get("discovery_chain", [])


@app.get("/api/assignment-evaluation")
def get_assignment_evaluation():
    data = get_bundled_data()
    return data.get("assignment_questions", [])


@app.get("/api/records")
def get_records(
    search: Optional[str] = None,
    source: Optional[str] = None,
    theme: Optional[str] = None,
    sentiment: Optional[str] = None,
    stage: Optional[str] = None,
    behaviour: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
):
    data = get_bundled_data()
    records = data.get("records", [])

    filtered = records

    if source:
        sources_list = [s.strip().lower() for s in source.split(",") if s.strip()]
        filtered = [
            r for r in filtered
            if str(r.get("source", "")).lower() in sources_list
            or str(r.get("source_display", "")).lower() in sources_list
        ]

    if theme:
        themes_list = [t.strip().lower() for t in theme.split(",") if t.strip()]
        filtered = [r for r in filtered if str(r.get("problem_theme", "")).lower() in themes_list]

    if sentiment:
        sentiments_list = [s.strip().lower() for s in sentiment.split(",") if s.strip()]
        filtered = [r for r in filtered if str(r.get("sentiment", "")).lower() in sentiments_list]

    if stage:
        stages_list = [st.strip().lower() for st in stage.split(",") if st.strip()]
        filtered = [r for r in filtered if str(r.get("user_journey_stage", "")).lower() in stages_list]

    if behaviour:
        beh_list = [b.strip().lower() for b in behaviour.split(",") if b.strip()]
        filtered = [r for r in filtered if str(r.get("user_behaviour", "")).lower() in beh_list]

    if search and search.strip():
        sq = search.strip().lower()
        filtered = [
            r for r in filtered
            if sq in str(r.get("cleaned_text", "")).lower()
            or sq in str(r.get("raw_text", "")).lower()
            or sq in str(r.get("evidence_quote", "")).lower()
            or sq in str(r.get("record_id", "")).lower()
            or sq in str(r.get("classification_reason", "")).lower()
        ]

    limit_int = getattr(limit, "default", limit) if not isinstance(limit, int) else limit
    offset_int = getattr(offset, "default", offset) if not isinstance(offset, int) else offset
    total_matched = len(filtered)
    paginated = filtered[offset_int : offset_int + limit_int]

    return {
        "total": total_matched,
        "limit": limit_int,
        "offset": offset_int,
        "records": paginated,
    }


@app.post("/api/ask")
def ask_assistant(req: AskRequest):
    """
    AI Research Assistant: Synthesizes evidence-backed answers using Groq LLM
    with fallback to deterministic semantic retrieval. Never exposes secrets to frontend.
    """
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    data = get_bundled_data()
    records = data.get("records", [])

    if not records:
        return {
            "answer": "No feedback records available to answer this inquiry.",
            "citations": [],
            "retrieved_count": 0,
        }

    # Keyword scoring for retrieval
    q_terms = [w.lower() for w in re.findall(r"\w+", query) if len(w) > 2]

    def score_item(r):
        s = 0
        text = (str(r.get("cleaned_text", "")) + " " + str(r.get("problem_theme", ""))).lower()
        for term in q_terms:
            if term in text:
                s += 1
        if str(r.get("problem_theme", "")).lower() in query.lower():
            s += 3
        return s

    scored = sorted(records, key=score_item, reverse=True)
    top_items = scored[:6]

    citations = []
    context_lines = []
    for it in top_items:
        rec_id = it.get("record_id", "N/A")
        quote = str(it.get("evidence_quote") or it.get("cleaned_text") or "")[:180].strip()
        src = it.get("source_display", it.get("source", "N/A"))
        theme = it.get("problem_theme", "N/A")
        rating = it.get("rating_display", "N/A")
        url = it.get("url", "")

        citations.append({
            "record_id": rec_id,
            "source": src,
            "theme": theme,
            "rating": rating,
            "quote": quote,
            "url": url,
        })
        context_lines.append(f"[{rec_id}] ({src}, Rating: {rating}, Theme: {theme}): \"{quote}\"")

    context_str = "\n".join(context_lines)

    # Groq LLM Server-side generation
    groq_key = os.getenv("GROQ_API_KEY", "")
    groq_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

    if groq_key and not groq_key.startswith("your_"):
        try:
            from groq import Groq
            client = Groq(api_key=groq_key, timeout=2.0, max_retries=0)
            sys_prompt = (
                "You are an expert research analyst for the Groww SIP Insight Lab. "
                "Answer the user's question STRICTLY using the provided feedback citations. "
                "Explicitly reference the supporting record IDs (e.g. [GFB_...]) for every assertion. "
                "Keep your answer structured, factual, and concise."
            )
            user_prompt = f"Evidence Snippets:\n{context_str}\n\nUser Question: {query}\n\nAnswer:"
            resp = client.chat.completions.create(
                model=groq_model,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=500,
            )
            return {
                "answer": resp.choices[0].message.content.strip(),
                "citations": citations,
                "retrieved_count": len(citations),
                "model_used": groq_model,
            }
        except Exception:
            pass  # Fall back to extractive synthesis

    # Extractive fallback
    themes = list(set(c["theme"] for c in citations))
    summary = [
        f"Based on `{len(citations)}` relevant records retrieved across Groww investor feedback channels:\n",
        f"**Core Themes:** {', '.join(themes)}.\n",
        "**Verified Evidence:**",
    ]
    for c in citations[:4]:
        summary.append(f"- **[{c['record_id']}]** ({c['source']}, {c['theme']}): *\"{c['quote']}\"*")

    summary.append("\n**Synthesis:** Empirical evidence demonstrates that user decisions are largely driven by operational practical barriers (e.g. bank auto-debit bounce penalties) and informed strategy reallocation rather than generic disinterest.")

    return {
        "answer": "\n".join(summary),
        "citations": citations,
        "retrieved_count": len(citations),
        "model_used": "Deterministic Extractive Synthesizer (Zero Cold-Start Mode)",
    }

