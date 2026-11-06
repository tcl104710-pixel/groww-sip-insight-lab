"""
SIP Insight Lab — Database Schema Setup (Task 0.3)
====================================================
Creates all tables defined in the architecture:
  - RAW_ITEM
  - CLEANED_ITEM
  - LABELLED_ITEM
  - GOLDEN_SET
  - AI_EVIDENCE_LOG
  - HYPOTHESIS_CARD
  - HUMAN_REVIEW_QUEUE  (operational table, not in architecture ERD)

Supports SQLite (default) and PostgreSQL.
Run once to initialise the database:
    python src/db/schema.py

Or import `init_db()` from application code.
"""

import os
import sqlite3
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

DB_BACKEND = os.getenv("DB_BACKEND", "sqlite")
DB_PATH = os.getenv("DB_PATH", "./data/sip_insight_lab.db")

# ---------------------------------------------------------------------------
# DDL statements — SQLite-compatible syntax
# ---------------------------------------------------------------------------

DDL_RAW_ITEM = """
CREATE TABLE IF NOT EXISTS raw_item (
    item_id         TEXT PRIMARY KEY,          -- UUID v4
    source          TEXT NOT NULL,             -- play_store | app_store | reddit | tradingqa | youtube
    source_id       TEXT NOT NULL,             -- Platform-native ID (review ID, comment ID, post ID)
    raw_text        TEXT NOT NULL,             -- Original, unmodified text
    raw_url         TEXT,                      -- Direct link to the original item
    star_rating     INTEGER,                   -- 1-5 (where applicable)
    collected_at    TEXT NOT NULL,             -- ISO-8601 datetime
    dedup_hash      TEXT NOT NULL UNIQUE,      -- SHA-256 of normalised raw_text (dedup key)
    metadata        TEXT                       -- JSON blob for source-specific extras (vote count, etc.)
);
"""

DDL_CLEANED_ITEM = """
CREATE TABLE IF NOT EXISTS cleaned_item (
    item_id             TEXT PRIMARY KEY,      -- FK → raw_item.item_id
    cleaned_text        TEXT NOT NULL,         -- PII-scrubbed, normalised text
    language            TEXT NOT NULL,         -- Detected language code (en | hi)
    pii_removal_log     TEXT,                  -- JSON: {"redacted_count": N, "types": [...]}
    cleaning_version    TEXT NOT NULL,         -- Version of cleaning pipeline used
    cleaned_at          TEXT NOT NULL,         -- ISO-8601 datetime
    FOREIGN KEY (item_id) REFERENCES raw_item(item_id)
);
"""

DDL_LABELLED_ITEM = """
CREATE TABLE IF NOT EXISTS labelled_item (
    item_id             TEXT PRIMARY KEY,      -- FK → cleaned_item.item_id
    taxonomy_version    TEXT NOT NULL,         -- e.g. "1.0" — links to taxonomy YAML version
    lifecycle_stage     TEXT,                  -- LS-00 … LS-04 | LS-99
    stated_intent       TEXT,                  -- continue | pause | stop | neutral | unknown
    actual_action       TEXT,                  -- active | paused | cancelled | unknown
    stop_type           TEXT,                  -- ST-01 | ST-02 | ST-03 | ST-99
    root_cause          TEXT,                  -- RC-01 … RC-07 | RC-99
    root_cause_sub      TEXT,                  -- Free-text subcategory label
    trigger_moment      TEXT,                  -- Textual description of the triggering event
    help_sources        TEXT,                  -- JSON array of help_source codes
    retention_factor    TEXT,                  -- RF-01 … RF-07 | RF-99 (null if churned)
    investor_segment    TEXT,                  -- JSON object: {age_group, income_stability, ...}
    sentiment_score     REAL,                  -- -1.0 to +1.0
    confidence_score    REAL NOT NULL,         -- 0.0 to 1.0 (aggregate)
    field_confidences   TEXT,                  -- JSON: per-field confidence scores
    review_status       TEXT DEFAULT 'auto',   -- auto | human_reviewed | rejected
    classified_at       TEXT NOT NULL,         -- ISO-8601 datetime
    FOREIGN KEY (item_id) REFERENCES cleaned_item(item_id)
);
"""

DDL_GOLDEN_SET = """
CREATE TABLE IF NOT EXISTS golden_set (
    golden_id           TEXT PRIMARY KEY,      -- UUID v4
    item_id             TEXT NOT NULL,         -- FK → raw_item.item_id
    human_labels        TEXT NOT NULL,         -- JSON: same schema as labelled_item fields
    labeller_id         TEXT NOT NULL,         -- Anonymised reviewer identifier
    labelled_at         TEXT NOT NULL,         -- ISO-8601 datetime
    reconciliation_note TEXT,                  -- Free-text if two labellers disagreed
    FOREIGN KEY (item_id) REFERENCES raw_item(item_id)
);
"""

DDL_AI_EVIDENCE_LOG = """
CREATE TABLE IF NOT EXISTS ai_evidence_log (
    log_id          TEXT PRIMARY KEY,          -- UUID v4
    item_id         TEXT NOT NULL,             -- FK → labelled_item.item_id
    timestamp       TEXT NOT NULL,             -- ISO-8601 datetime
    event_type      TEXT NOT NULL,             -- correction | rejection | approval
    ai_output       TEXT NOT NULL,             -- JSON: {field: value, confidence: float}
    human_output    TEXT,                      -- JSON: {field: corrected_value} (null for approval)
    reviewer_id     TEXT NOT NULL,             -- Anonymised reviewer identifier
    reason_note     TEXT,                      -- Optional free-text explanation
    FOREIGN KEY (item_id) REFERENCES labelled_item(item_id)
);
"""

DDL_HYPOTHESIS_CARD = """
CREATE TABLE IF NOT EXISTS hypothesis_card (
    card_id                 TEXT PRIMARY KEY,  -- UUID v4
    opportunity_label       TEXT NOT NULL,     -- One-sentence description
    root_cause              TEXT NOT NULL,     -- RC-XX taxonomy code
    lifecycle_stage_focus   TEXT,              -- Most affected stage (e.g. LS-02)
    frequency_score         REAL,              -- 0.0–1.0 normalised
    severity_score          REAL,              -- 0.0–1.0 normalised
    first_6mo_concentration REAL,              -- 0.0–1.0
    addressability_score    REAL,              -- 0 or 1
    opportunity_score       REAL NOT NULL,     -- Weighted composite
    supporting_item_ids     TEXT,              -- JSON array of item_id references
    supporting_quotes       TEXT,              -- JSON array of anonymised quote strings
    counter_evidence_summary TEXT,             -- Free-text from counter-evidence agent
    confidence_level        TEXT,              -- High | Medium | Low
    interview_guide         TEXT,              -- JSON array of question strings
    nudge_checklist_passed  INTEGER DEFAULT 0, -- 1 = passed, 0 = pending/failed
    generated_at            TEXT NOT NULL      -- ISO-8601 datetime
);
"""

DDL_HUMAN_REVIEW_QUEUE = """
CREATE TABLE IF NOT EXISTS human_review_queue (
    queue_id        TEXT PRIMARY KEY,          -- UUID v4
    item_id         TEXT NOT NULL,             -- FK → labelled_item.item_id
    reason          TEXT NOT NULL,             -- low_confidence | flagged_by_rule | random_sample
    confidence_score REAL,                     -- Score that triggered the routing
    assigned_to     TEXT,                      -- Anonymised reviewer ID (null = unassigned)
    status          TEXT DEFAULT 'pending',    -- pending | in_review | completed | skipped
    created_at      TEXT NOT NULL,             -- ISO-8601 datetime
    completed_at    TEXT,                      -- ISO-8601 datetime (null until done)
    FOREIGN KEY (item_id) REFERENCES labelled_item(item_id)
);
"""

DDL_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_raw_item_source ON raw_item(source);",
    "CREATE INDEX IF NOT EXISTS idx_raw_item_collected ON raw_item(collected_at);",
    "CREATE INDEX IF NOT EXISTS idx_labelled_lifecycle ON labelled_item(lifecycle_stage);",
    "CREATE INDEX IF NOT EXISTS idx_labelled_root_cause ON labelled_item(root_cause);",
    "CREATE INDEX IF NOT EXISTS idx_labelled_stop_type ON labelled_item(stop_type);",
    "CREATE INDEX IF NOT EXISTS idx_labelled_review_status ON labelled_item(review_status);",
    "CREATE INDEX IF NOT EXISTS idx_ai_log_event ON ai_evidence_log(event_type);",
    "CREATE INDEX IF NOT EXISTS idx_hrq_status ON human_review_queue(status);",
]

ALL_DDL = [
    DDL_RAW_ITEM,
    DDL_CLEANED_ITEM,
    DDL_LABELLED_ITEM,
    DDL_GOLDEN_SET,
    DDL_AI_EVIDENCE_LOG,
    DDL_HYPOTHESIS_CARD,
    DDL_HUMAN_REVIEW_QUEUE,
] + DDL_INDEXES


def init_db(db_path: str = DB_PATH) -> sqlite3.Connection:
    """
    Initialise the SQLite database, create all tables and indexes.

    Args:
        db_path: Path to the SQLite file. Created if it doesn't exist.

    Returns:
        An open sqlite3.Connection.
    """
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    logger.info("Initialising database at: %s", db_path)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")     # Better concurrent read performance
    conn.execute("PRAGMA foreign_keys=ON;")      # Enforce FK constraints

    with conn:
        for statement in ALL_DDL:
            conn.execute(statement)

    logger.info("All tables and indexes created successfully.")
    return conn


def verify_schema(conn: sqlite3.Connection) -> dict:
    """
    Verify all expected tables exist and return their row counts.

    Args:
        conn: Open sqlite3.Connection.

    Returns:
        dict mapping table_name → row_count.
    """
    expected_tables = [
        "raw_item",
        "cleaned_item",
        "labelled_item",
        "golden_set",
        "ai_evidence_log",
        "hypothesis_card",
        "human_review_queue",
    ]
    result = {}
    cursor = conn.cursor()
    for table in expected_tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table};")
            count = cursor.fetchone()[0]
            result[table] = count
            logger.info("  ✓ %s  (%d rows)", table, count)
        except sqlite3.OperationalError as e:
            result[table] = f"ERROR: {e}"
            logger.error("  ✗ %s  — %s", table, e)
    return result


if __name__ == "__main__":
    conn = init_db()
    print("\n=== Schema Verification ===")
    counts = verify_schema(conn)
    for table, count in counts.items():
        print(f"  {table}: {count}")
    conn.close()
    print("\nPhase 0 · Task 0.3 complete — database schema initialised.")
