# SIP Insight Lab

> **AI-Powered Discovery Engine for SIP Retention**  
> Growth Team · Groww · Phase 0 (Foundations)

---

## Goal

Increase the percentage of first-time mutual fund investors who still have an
**active SIP 12 months** after starting their first one — by replacing scattered
opinions with traceable, AI-classified evidence from public investor feedback.

---

## Quick Start

### 1. Clone & set up environment

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate    # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Download spaCy NER model (needed for PII scrubbing in Phase 2)
python -m spacy download en_core_web_trf
```

### 2. Configure credentials

```bash
# Copy the template and fill in your API keys
copy .env.template .env
# Edit .env with your actual keys
```

### 3. Initialise the database

```bash
python src/db/schema.py
```

### 4. Validate Phase 0 setup

```bash
python scripts/validate_phase0.py
```

Expected output:
```
✅  All N Phase 0 checks passed. Ready for Phase 1.
```

---

## Project Structure

```
sip-insight-lab/
│
├── config.yaml                  # Central config (confidence threshold, QA targets, etc.)
├── requirements.txt             # Python dependencies
├── .env.template                # Credentials template (copy → .env)
├── .gitignore
│
├── taxonomy/
│   └── taxonomy_v1.yaml         # Frozen research taxonomy (root causes, retention factors, etc.)
│
├── data/
│   ├── SOURCES.md               # ToS compliance doc for all 5 data sources
│   └── sip_insight_lab.db       # SQLite database (auto-created on first run)
│
├── golden_set/                  # Hand-labelled items for QA evaluation (Phase 3)
│
├── outputs/                     # Generated reports, hypothesis cards, AI evidence log exports
│   └── logs/
│
├── docs/                        # Architecture & implementation plan (reference)
│
├── scripts/
│   └── validate_phase0.py       # Phase 0 exit criteria checker
│
└── src/
    ├── config.py                # Typed config loader (imports config.yaml)
    ├── taxonomy_loader.py       # Loads + validates taxonomy YAML
    │
    ├── db/
    │   └── schema.py            # DB schema DDL + init_db() function
    │
    ├── scrapers/                # Phase 1 — data source connectors
    │   ├── play_store.py
    │   ├── app_store.py
    │   ├── reddit.py
    │   ├── tradingqa.py
    │   └── youtube.py
    │
    ├── ingestion/               # Phase 1 — queue, dedup, DB write
    │   ├── queue.py
    │   └── dedup.py
    │
    ├── cleaning/                # Phase 2 — PII scrubber, normaliser
    │   ├── lang_detect.py
    │   ├── pii_scrubber.py
    │   ├── noise_removal.py
    │   └── normaliser.py
    │
    ├── classification/          # Phase 2 — LLM classifier
    │   ├── prompt_builder.py
    │   ├── llm_client.py
    │   ├── parser.py
    │   ├── confidence.py
    │   └── router.py
    │
    ├── qa/                      # Phase 3 — golden set eval, evidence log
    │   ├── comparator.py
    │   └── evidence_log.py
    │
    ├── agents/                  # Phase 3 — counter-evidence agent
    │   ├── counter_evidence.py
    │   └── ce_formatter.py
    │
    ├── synthesis/               # Phase 4 — opportunity ranking, hypothesis cards
    │   ├── aggregator.py
    │   ├── scorers.py
    │   ├── addressability.py
    │   ├── ranker.py
    │   ├── card_generator.py
    │   └── interview_guide.py
    │
    └── prompts/                 # LLM prompt templates
        ├── classify_v1.txt
        └── counter_evidence_v1.txt
```

---

### 5. Running Phase 3 (Quality Assurance & Counter-Evidence)

```bash
# Seed Golden Set (25 curated dual-labelled items) into DB
python scripts/seed_golden_set.py

# Run QA Evaluation against Golden Set (target: >= 80% accuracy, >= 0.75 F1)
python scripts/run_qa_evaluation.py --prompt-version v2

# Export & Process Human Review Queue (with automatic AI Evidence Log persistence)
python scripts/human_review_tool.py --export-template
python scripts/human_review_tool.py --process outputs/review_queue_template.csv --reviewer reviewer_anon_01

# Run Counter-Evidence Adversarial Agent across Top 5 Themes
python scripts/run_counter_evidence.py --out outputs/reports/counter_evidence_review.md

# Validate all Phase 3 Exit Criteria
python scripts/validate_phase3.py
```

---

### 6. Running Phase 4 (Insight Synthesis & Opportunity Ranking)

```bash
# Run end-to-end synthesis pipeline (generates cards, rankings, and nudge review)
python scripts/run_synthesis.py
```

---

### 7. Running Phase 5 & Multi-Source Research Discovery Engine

#### Option A: Streamlit Interactive Exploration Dashboard
```bash
# Launch the upgraded Streamlit AI Discovery Engine Dashboard
streamlit run src/dashboard/app.py
# Or via helper script:
python scripts/run_dashboard.py --port 8501
```

#### Option B: Production Gateway & Edge Frontend (Vercel-Equivalent)
```bash
# Run the local production server (serves FastAPI /api + static UI on port 3000)
python scripts/run_production_server.py --port 3000
```

#### Option C: Deploying to Vercel
1. Push repository to GitHub.
2. Import project in [Vercel Dashboard](https://vercel.com/new).
3. Framework Preset: **Other** (Root directory: `.`).
4. Set Environment Variables in Project Settings:
   - `GROQ_API_KEY` (your Groq API key for AI Research Assistant queries)
   - `GROQ_MODEL` (default: `openai/gpt-oss-20b` or `llama-3.3-70b-versatile`)
5. Click **Deploy**. Vercel will automatically build the Edge frontend from `public/` and deploy the serverless Python API from `api/index.py` via `vercel.json`.

---

### 8. Verification & Test Suite

```bash
# Run all 109 automated tests (Scrapers, Pipeline, QA, Discovery Engine, Vercel API)
python -m pytest tests/
```

---

## 📦 Core Research Deliverables & Evidence Log

All research deliverables are persisted at the project root and embedded in the dashboard:

| Deliverable File | Description | Records / Scope |
|---|---|---|
| [`sip_feedback_combined.csv`](sip_feedback_combined.csv) | Deduplicated, normalized multi-source corpus | 696 clean records |
| [`sip_feedback_classified.csv`](sip_feedback_classified.csv) | Full taxonomy AI classification | 269 SIP records |
| [`sip_insights_report.md`](sip_insights_report.md) | In-depth empirical research findings & Mermaid diagrams | 7 recurring patterns |
| [`sip_evidence_log.csv`](sip_evidence_log.csv) | Traceable audit log with quotes, confidence scores, URLs | 269 verifiable entries |
| [`sip_opportunity_matrix.csv`](sip_opportunity_matrix.csv) | Ranked product opportunities with full discovery chain | 5 prioritized initiatives |

---

## 🔗 The 6-Stage Discovery Progression

The SIP Insight Lab functions as a genuine Discovery Engine by connecting empirical evidence through to concrete product opportunities:

$$\text{User Feedback} \longrightarrow \text{Research Finding} \longrightarrow \text{User Problem} \longrightarrow \text{Unmet Need} \longrightarrow \text{Opportunity} \longrightarrow \text{Supporting Evidence}$$

1. **User Feedback:** Verbatim quotes collected across Play Store, App Store, Reddit, and YouTube.
2. **Research Finding:** Empirical frequency counts, percentage share, and statistical patterns.
3. **User Problem:** Root cause identification (e.g. involuntary bank bounce penalties vs. deliberate rebalancing).
4. **Unmet Need:** Precise user requirement (e.g. -24h pre-debit balance check with penalty-free skip).
5. **Product Opportunity:** Actionable, formula-ranked product initiative (P0/P1 tiers).
6. **Supporting Evidence:** Complete traceability to record IDs and original URLs.

---

## Implementation Phases

| Phase | Focus | Status |
|---|---|---|
| **Phase 0** | Foundations, taxonomy, DB schema, config | ✅ Complete |
| **Phase 1** | Data collection — 5 source connectors & ingestion | ✅ Complete |
| **Phase 2** | Cleaning, PII removal, classification engine | ✅ Complete |
| **Phase 3** | QA golden set, counter-evidence agent, AI Evidence Log | ✅ Complete |
| **Phase 4** | Insight synthesis, opportunity ranking, hypothesis cards | ✅ Complete |
| **Phase 5** | Dashboard, stakeholder readout, user interview handoff | ✅ Complete |

See [`implementation-plan.md`](implementation-plan.md) for the full task list and exit criteria.

---

## Ethics & Constraints

- Public feedback is treated as **hypotheses only**, not proof of causality
- **No specific fund or stock recommendations** ever generated
- **No fear, FOMO, urgency, or manipulative nudge language** in any output
- All AI corrections/rejections logged in an exportable **AI Evidence Log**
- PII is scrubbed before any data is stored or analysed

---

## Key Documents

| Document | Purpose |
|---|---|
| [`ProblemStatement.txt`](ProblemStatement.txt) | Original problem brief |
| [`problemStatement.md`](problemStatement.md) | Structured markdown version |
| [`architecture.md`](architecture.md) | 8-layer system architecture with diagrams |
| [`implementation-plan.md`](implementation-plan.md) | Phase-wise task plan (10 weeks) |
| [`taxonomy/taxonomy_v1.yaml`](taxonomy/taxonomy_v1.yaml) | Frozen research taxonomy |
| [`data/SOURCES.md`](data/SOURCES.md) | Data source ToS compliance |
| [`config.yaml`](config.yaml) | Central configuration |
