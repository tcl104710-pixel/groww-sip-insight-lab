# SIP Insight Lab — System Architecture

> **Project:** AI-Powered Discovery Engine for SIP Retention  
> **Team:** Growth — Groww  
> **Goal:** Understand *why* first-time MF investors churn within 12 months and *which* churns a better product could prevent.

---

## Table of Contents

1. [High-Level Architecture Overview](#1-high-level-architecture-overview)
2. [Layer 1 — Data Collection](#2-layer-1--data-collection)
3. [Layer 2 — Data Cleaning & PII Removal](#3-layer-2--data-cleaning--pii-removal)
4. [Layer 3 — Classification Engine](#4-layer-3--classification-engine)
5. [Layer 4 — Research Taxonomy](#5-layer-4--research-taxonomy)
6. [Layer 5 — Counter-Evidence Agent](#6-layer-5--counter-evidence-agent)
7. [Layer 6 — Quality Assurance](#7-layer-6--quality-assurance)
8. [Layer 7 — Insight Synthesis & Hypothesis Engine](#8-layer-7--insight-synthesis--hypothesis-engine)
9. [Layer 8 — Output & Delivery](#9-layer-8--output--delivery)
10. [Data Model](#10-data-model)
11. [Key Design Decisions](#11-key-design-decisions)
12. [Ethics & Constraints](#12-ethics--constraints)

---

## 1. High-Level Architecture Overview

```mermaid
flowchart TD
    A["🌐 Public Data Sources\n(Play Store · App Store · Reddit · TradingQ&A · YouTube)"]
    B["📥 Data Collection Layer\n(Scrapers / API Connectors)"]
    C["🧹 Cleaning & PII Removal\n(Anonymiser + Deduplicator)"]
    D["🤖 AI Classification Engine\n(LLM + Taxonomy Mapper)"]
    E["📚 Research Taxonomy Store\n(Structured Labels)"]
    F["🔍 Counter-Evidence Agent\n(Adversarial LLM)"]
    G["✅ Quality Assurance Layer\n(Golden Set · Confidence Scores · Human Review)"]
    H["💡 Insight Synthesis Engine\n(Opportunity Ranker + Hypothesis Cards)"]
    I["📋 AI Evidence Log\n(Exportable Audit Trail)"]
    J["📊 Delivery Layer\n(Dashboard · Interview Guides · Reports)"]

    A --> B --> C --> D
    E --> D
    D --> F --> G
    G --> H
    G --> I
    H --> J
```

---

## 2. Layer 1 — Data Collection

### Purpose
Gather permitted, publicly available investor feedback from five sources at scale.

### Sources & Connectors

| Source | Method | Data Captured |
|---|---|---|
| **Google Play Store** | Play Store RSS / Scraper | Star rating, review text, app version, date |
| **Apple App Store** | iTunes RSS API | Star rating, review text, country, date |
| **Reddit** | Reddit Public API (PRAW) | Post text, comment threads, subreddit, score, date |
| **TradingQ&A** | HTTP Scraper (Permitted) | Q&A text, tags, vote count, date |
| **YouTube** | YouTube Data API v3 | Comment text, video ID, like count, date |

### Collection Rules
- Only **permitted public data** is collected (no private messages, no authenticated sessions)
- Each item is stamped with: `source`, `source_id`, `collected_at`, `raw_url`
- Rate limits and platform ToS are strictly observed
- A **deduplication hash** (SHA-256 of normalised text) is computed at ingestion

```mermaid
flowchart LR
    P1["Google Play\nScraper"] --> R["Raw Data\nIngestion Queue"]
    P2["App Store\nRSS API"] --> R
    P3["Reddit\nPRAW API"] --> R
    P4["TradingQ&A\nScraper"] --> R
    P5["YouTube\nData API"] --> R
    R --> DB["Raw Feedback Store\n(Unprocessed)"]
```

---

## 3. Layer 2 — Data Cleaning & PII Removal

### Purpose
Standardise raw text and remove any personal identifiers before analysis.

### Pipeline Steps

```mermaid
flowchart LR
    A["Raw Text"] --> B["Language Detection\n(keep only English / Hindi)"]
    B --> C["PII Scrubber\n(names · phone · email · account IDs)"]
    C --> D["Noise Removal\n(emojis normalised · HTML stripped · duplicates dropped)"]
    D --> E["Text Normalisation\n(lowercase · whitespace · encoding fix)"]
    E --> F["Cleaned Feedback Item\n(ready for classification)"]
```

### PII Removal Rules
- Named Entity Recognition (NER) model tags `PERSON`, `EMAIL`, `PHONE`, `ORG`
- All tagged spans replaced with `[REDACTED]`
- Account numbers / UPI IDs matched via regex and masked
- Output is logged (what was removed, not the value) for audit

---

## 4. Layer 3 — Classification Engine

### Purpose
Apply structured labels from the Research Taxonomy to each cleaned feedback item using an LLM.

### Architecture

```mermaid
flowchart TD
    CI["Cleaned Item"] --> PE["Prompt Engineer\n(builds structured prompt)"]
    TX["Taxonomy Store"] --> PE
    PE --> LLM["LLM\n(GPT-4 / Gemini Pro)"]
    LLM --> RP["Response Parser\n(JSON schema enforcement)"]
    RP --> CS["Confidence Scorer\n(0–1 per label field)"]
    CS --> DEC{"Confidence\n≥ Threshold?"}
    DEC -- Yes --> LS["Labelled Store"]
    DEC -- No --> HRQ["Human Review Queue"]
```

### Classification Output Fields (per item)

| Field | Type | Description |
|---|---|---|
| `lifecycle_stage` | enum | `pre_first_sip` · `0–3mo` · `3–6mo` · `6–12mo` · `12mo+` |
| `stated_intent` | enum | `continue` · `pause` · `stop` · `neutral` · `unknown` |
| `actual_action` | enum | `active` · `paused` · `cancelled` · `unknown` |
| `stop_type` | enum | `involuntary_lapse` · `deliberate_exit` · `not_applicable` |
| `root_cause` | enum | see Taxonomy (§5) |
| `trigger_moment` | string | Textual description of the triggering event |
| `help_source` | list | Where user sought help outside the app |
| `retention_factor` | string | For continuers — what kept them going |
| `investor_segment` | object | `age_group`, `income_stability`, `money_source`, `influencer_type` |
| `sentiment_score` | float | –1.0 to +1.0 |
| `confidence_score` | float | 0.0 to 1.0 (overall classification confidence) |

> **Critical Separation:** `stated_intent` and `actual_action` are always stored as **separate fields** to avoid conflating what investors say with what they do.

---

## 5. Layer 4 — Research Taxonomy

### Purpose
Provide a consistent, versioned label vocabulary used by the Classification Engine.

### Root Cause Categories

```mermaid
mindmap
  root((Root Causes))
    Involuntary Lapse
      Insufficient balance
      Bank mandate failure
      Auto-cancellation after 3 misses
    UX & Payment Friction
      Confusing interface
      Payment gateway failure
      KYC issues
    Return Disappointment
      Calculator mismatch
      Finfluencer promise gap
      Market downturn fear
    Income Change
      Job loss
      Salary reduction
      Emergency expense
    Deliberate Informed Exit
      Goal achieved
      Fund switch
      Platform switch
    Knowledge Gap
      Did not understand SIP mechanics
      Confused about NAV
    External Influence
      Peer advice
      Finfluencer recommendation
      Family pressure
```

### Retention Factor Categories

| Code | Label |
|---|---|
| `RF-01` | Seeing positive returns (even small) |
| `RF-02` | Community / peer encouragement |
| `RF-03` | App nudges or reminders |
| `RF-04` | Long-term goal tracking visible |
| `RF-05` | Educational content within app |
| `RF-06` | Automated / hassle-free experience |

### Taxonomy Versioning
- Taxonomy is stored as a **versioned YAML file** (`taxonomy_v1.yaml`, `taxonomy_v2.yaml`, …)
- Every classified item stores the `taxonomy_version` it was labelled with
- Schema changes trigger a **re-classification run** on affected items

---

## 6. Layer 5 — Counter-Evidence Agent

### Purpose
Prevent confirmation bias by actively searching for evidence that contradicts each emerging theme.

### How It Works

```mermaid
sequenceDiagram
    participant SE as Synthesis Engine
    participant CA as Counter-Evidence Agent
    participant LS as Labelled Store
    participant AR as Analyst Report

    SE->>CA: "Leading theme: UX friction causes most cancellations"
    CA->>LS: Query for items that contradict this theme
    CA->>CA: Generate adversarial search queries
    CA->>LS: Surface contradicting quotes & patterns
    CA->>AR: Append counter-evidence section with confidence score
    AR->>SE: Refined, balanced theme with supporting AND opposing evidence
```

### Counter-Evidence Strategies
1. **Inverse Query:** Search for items where UX was praised by churned users
2. **Segment Drill-down:** Check if the theme holds across all investor segments or only specific ones
3. **Temporal Check:** Does the pattern hold across all months, or only certain periods?
4. **Frequency Sanity:** Is the theme being driven by a small vocal minority?

---

## 7. Layer 6 — Quality Assurance

### Purpose
Ensure classification reliability is measured, reported, and continuously improved.

### Golden Set Evaluation

```mermaid
flowchart LR
    GS["Golden Set\n(≥20 hand-labelled items)"] --> CM["Comparison\nModule"]
    LS["AI-Labelled\nItems"] --> CM
    CM --> MR["Metrics Report\n(Accuracy · Precision · Recall · F1)"]
    CM --> ER["Error Analysis\n(confusion matrix per field)"]
    ER --> FI["Feedback to\nPrompt Engineer"]
```

### QA Metrics Tracked

| Metric | Description | Target |
|---|---|---|
| **Overall Accuracy** | % exact-match across all fields | ≥ 80% |
| **Per-field F1** | F1 score for each taxonomy label | ≥ 0.75 per field |
| **Low-confidence Rate** | % of items routed to human review | < 20% |
| **Human Override Rate** | % of AI decisions corrected by humans | Reported openly |

### AI Evidence Log Schema

Every human correction or AI output rejection is written to an **exportable AI Evidence Log**:

```json
{
  "log_id": "uuid",
  "item_id": "feedback item reference",
  "timestamp": "ISO-8601",
  "event_type": "correction | rejection | approval",
  "ai_output": { "field": "value", "confidence": 0.0 },
  "human_output": { "field": "corrected_value" },
  "reviewer_id": "anonymised",
  "reason_note": "optional free text"
}
```

---

## 8. Layer 7 — Insight Synthesis & Hypothesis Engine

### Purpose
Transform classified data into ranked opportunities and actionable hypothesis cards.

### Opportunity Ranking Formula

```
Opportunity Score =
  (Frequency_Score × 0.30)
  + (Severity_Score × 0.25)
  + (First_6mo_Concentration × 0.25)
  + (Addressability_Score × 0.20)
```

| Component | Definition |
|---|---|
| **Frequency Score** | Normalised count of items in this root cause bucket |
| **Severity Score** | Weighted average sentiment magnitude for the bucket |
| **First_6mo_Concentration** | % of bucket items occurring within the first 6 months of SIP |
| **Addressability Score** | 1 if solvable without investment advice or fear nudges; 0 otherwise |

### Hypothesis Card Structure

```markdown
## Hypothesis Card — [ID]

**Opportunity:** [One-sentence description]
**Root Cause:** [Taxonomy label]
**Frequency:** [N items / % of total corpus]
**Lifecycle Stage Most Affected:** [e.g., 3–6 months]
**Supporting Quotes:** [3–5 verbatim, anonymised quotes]
**Counter-Evidence:** [Summary from Counter-Evidence Agent]
**Confidence:** [High / Medium / Low]
**Opportunity Score:** [Calculated value]

### Interview Guide
1. [Question to validate this hypothesis with a real investor]
2. ...
```

---

## 9. Layer 8 — Output & Delivery

### Outputs Produced

```mermaid
flowchart LR
    H["Hypothesis Engine"] --> D1["📊 Insight Dashboard\n(filterable by segment, stage, root cause)"]
    H --> D2["📋 AI Evidence Log\n(exportable CSV / JSON)"]
    H --> D3["🃏 Hypothesis Cards\n(with Interview Guides)"]
    H --> D4["📈 QA Metrics Report\n(accuracy · error analysis)"]
    H --> D5["🗺️ Opportunity Ranking\n(ranked list with formula visible)"]
```

### Dashboard Filters

| Dimension | Filter Options |
|---|---|
| **Lifecycle Stage** | pre-SIP · 0–3mo · 3–6mo · 6–12mo · 12mo+ |
| **Root Cause** | Full taxonomy tree |
| **Stop Type** | Involuntary · Deliberate · Unknown |
| **Investor Segment** | Age group · Income stability · Money source · Influencer type |
| **Source** | Play Store · App Store · Reddit · TradingQ&A · YouTube |
| **Intent vs. Action** | Gap view (stated ≠ actual) |
| **Time Period** | Date range of feedback collected |

---

## 10. Data Model

```mermaid
erDiagram
    RAW_ITEM {
        string item_id PK
        string source
        string source_id
        string raw_text
        string raw_url
        datetime collected_at
        string dedup_hash
    }

    CLEANED_ITEM {
        string item_id FK
        string cleaned_text
        string language
        string pii_removal_log
        datetime cleaned_at
    }

    LABELLED_ITEM {
        string item_id FK
        string taxonomy_version
        string lifecycle_stage
        string stated_intent
        string actual_action
        string stop_type
        string root_cause
        string trigger_moment
        json help_sources
        string retention_factor
        json investor_segment
        float sentiment_score
        float confidence_score
        datetime classified_at
    }

    GOLDEN_SET {
        string golden_id PK
        string item_id FK
        json human_labels
        string labeller_id
        datetime labelled_at
    }

    AI_EVIDENCE_LOG {
        string log_id PK
        string item_id FK
        string event_type
        json ai_output
        json human_output
        string reviewer_id
        string reason_note
        datetime timestamp
    }

    HYPOTHESIS_CARD {
        string card_id PK
        string opportunity_label
        string root_cause
        float opportunity_score
        json supporting_item_ids
        string counter_evidence_summary
        string confidence_level
        json interview_guide
        datetime generated_at
    }

    RAW_ITEM ||--|| CLEANED_ITEM : "cleaned into"
    CLEANED_ITEM ||--|| LABELLED_ITEM : "classified into"
    LABELLED_ITEM ||--o{ GOLDEN_SET : "evaluated against"
    LABELLED_ITEM ||--o{ AI_EVIDENCE_LOG : "logged in"
    LABELLED_ITEM }o--|| HYPOTHESIS_CARD : "synthesised into"
```

---

## 11. Key Design Decisions

| Decision | Rationale |
|---|---|
| **Intent and Action stored as separate fields** | Prevents conflating what investors say with what they do — the core trap identified in the problem statement |
| **Taxonomy is versioned** | Enables re-classification when the label schema evolves without losing historical data |
| **Counter-Evidence Agent is a separate LLM call** | Structurally prevents the primary classifier from anchoring to its own output |
| **Confidence threshold routing** | Low-confidence items go to humans rather than being silently mislabelled |
| **Opportunity Score formula is visible** | Builds trust with stakeholders — no black-box prioritisation |
| **Public feedback = hypotheses only** | Findings are explicitly validated via interviews and behavioural data, not treated as ground truth |
| **No fund / stock recommendations** | Ethical boundary — the engine informs product decisions, not investment advice |

---

## 12. Ethics & Constraints

> **Foundational Principle:** Public feedback is a source of *hypotheses*, not a measure of retention or proof of causality.

### Hard Constraints

| Constraint | Enforcement |
|---|---|
| No specific fund / stock recommendations | Blocked at prompt level + output validation |
| No fear, FOMO, urgency, or manipulative nudge generation | Hypothesis cards reviewed against a nudge checklist |
| No PII in any downstream output | PII scrubber runs before classification; output layer strips residual identifiers |
| All AI corrections / rejections logged | AI Evidence Log is append-only and exportable |
| Findings validated before product decisions | Hypothesis cards include interview guide; internal data cited where available |

### Validation Pipeline

```mermaid
flowchart LR
    HC["Hypothesis Cards"] --> UI["User Interviews\n(qualitative validation)"]
    HC --> BD["Internal Behavioural Data\n(where available)"]
    UI --> VF["Validated Finding"]
    BD --> VF
    VF --> PD["Product Decision"]
```

---

*Architecture document based on: [`ProblemStatement.txt`](file:///c:/Users/nagas/Downloads/Grad%20project-grow/ProblemStatement.txt)*  
*Generated: 2026-10-26*
