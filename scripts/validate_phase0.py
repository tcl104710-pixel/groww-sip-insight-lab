"""
SIP Insight Lab - Phase 0 Validation Script
============================================
Run this script to verify all Phase 0 exit criteria are met:

  python scripts/validate_phase0.py

Expected output when all checks pass:
  [PASS] All Phase 0 exit criteria satisfied. Ready for Phase 1.
"""

import os
import sys
import sqlite3
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"
results = []


def check(label: str, condition: bool, note: str = "") -> bool:
    status = PASS if condition else FAIL
    msg = f"  {status}  {label}"
    if note:
        msg += f"  ({note})"
    print(msg)
    results.append(condition)
    return condition


def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# 0.1 — Folder structure
# ---------------------------------------------------------------------------
section("Task 0.1 — Folder Structure")
required_dirs = [
    "data", "src", "taxonomy", "golden_set", "outputs",
    "src/ingestion", "src/scrapers", "src/cleaning",
    "src/classification", "src/qa", "src/synthesis",
    "src/agents", "src/prompts", "src/db",
]
for d in required_dirs:
    p = PROJECT_ROOT / d
    check(f"Directory exists: {d}", p.is_dir())

# ---------------------------------------------------------------------------
# 0.2 — Credentials template
# ---------------------------------------------------------------------------
section("Task 0.2 — Credentials Vault")
check(
    ".env.template exists",
    (PROJECT_ROOT / ".env.template").exists(),
)
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    check(".env file present (credentials configured)", True)
else:
    print(f"  {WARN} .env not found — copy .env.template to .env and fill in credentials before Phase 1.")

# ---------------------------------------------------------------------------
# 0.3 — Database schema
# ---------------------------------------------------------------------------
section("Task 0.3 — Database Schema")
db_path = PROJECT_ROOT / "data" / "sip_insight_lab.db"

# Try to initialise if not present
if not db_path.exists():
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from db.schema import init_db
        init_db(str(db_path))
    except Exception as e:
        print(f"  {FAIL}  Could not initialise DB: {e}")

if db_path.exists():
    check("Database file exists", True, str(db_path.relative_to(PROJECT_ROOT)))
    conn = sqlite3.connect(str(db_path))
    expected_tables = [
        "raw_item", "cleaned_item", "labelled_item",
        "golden_set", "ai_evidence_log", "hypothesis_card", "human_review_queue",
    ]
    for table in expected_tables:
        try:
            conn.execute(f"SELECT 1 FROM {table} LIMIT 1;")
            check(f"Table exists: {table}", True)
        except sqlite3.OperationalError:
            check(f"Table exists: {table}", False)
    conn.close()
else:
    check("Database file exists", False, "Run: python src/db/schema.py")

# ---------------------------------------------------------------------------
# 0.4 — Taxonomy v1
# ---------------------------------------------------------------------------
section("Task 0.4 — Taxonomy v1")
tax_path = PROJECT_ROOT / "taxonomy" / "taxonomy_v1.yaml"
check("taxonomy_v1.yaml exists", tax_path.exists())

if tax_path.exists():
    import yaml
    with open(tax_path) as f:
        tx = yaml.safe_load(f)
    check("version field present", "version" in tx, tx.get("version"))
    check("frozen=true", tx.get("frozen") is True)
    check("root_causes defined (≥7)", len(tx.get("root_causes", [])) >= 7,
          f"{len(tx.get('root_causes', []))} found")
    check("retention_factors defined (≥6)", len(tx.get("retention_factors", [])) >= 6,
          f"{len(tx.get('retention_factors', []))} found")
    check("lifecycle_stages defined (≥5)", len(tx.get("lifecycle_stages", [])) >= 5,
          f"{len(tx.get('lifecycle_stages', []))} found")
    check("stop_types defined (≥3)", len(tx.get("stop_types", [])) >= 3,
          f"{len(tx.get('stop_types', []))} found")
    check("classification_config.confidence_threshold present",
          tx.get("classification_config", {}).get("confidence_threshold") is not None,
          str(tx.get("classification_config", {}).get("confidence_threshold")))

# ---------------------------------------------------------------------------
# 0.5 — Config file
# ---------------------------------------------------------------------------
section("Task 0.5/0.6 — Config File")
config_path = PROJECT_ROOT / "config.yaml"
check("config.yaml exists", config_path.exists())

if config_path.exists():
    import yaml
    with open(config_path) as f:
        cfg = yaml.safe_load(f)
    ct = cfg.get("classification", {}).get("confidence_threshold")
    check("confidence_threshold = 0.75", ct == 0.75, str(ct))
    sla = cfg.get("human_review", {}).get("sla_hours")
    check("human_review.sla_hours = 48", sla == 48, str(sla))
    check("ethics.nudge_checklist_required = true",
          cfg.get("ethics", {}).get("nudge_checklist_required") is True)

# ---------------------------------------------------------------------------
# 0.? — .gitignore
# ---------------------------------------------------------------------------
section("Safety Checks")
gi = PROJECT_ROOT / ".gitignore"
check(".gitignore exists", gi.exists())
if gi.exists():
    content = gi.read_text()
    check(".gitignore excludes .env", ".env" in content)
    check(".gitignore excludes data/raw/", "data/raw/" in content)

check("data/SOURCES.md exists", (PROJECT_ROOT / "data" / "SOURCES.md").exists())
check("requirements.txt exists", (PROJECT_ROOT / "requirements.txt").exists())

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
total = len(results)
passed = sum(results)
failed = total - passed

print(f"\n{'='*60}")
if failed == 0:
    print(f"  [PASS]  All {total} Phase 0 checks passed. Ready for Phase 1.")
else:
    print(f"  [FAIL]  {failed}/{total} checks failed. Resolve issues above before Phase 1.")
print(f"{'='*60}\n")

sys.exit(0 if failed == 0 else 1)
