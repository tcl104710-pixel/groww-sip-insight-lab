"""
SIP Insight Lab — Taxonomy Loader
==================================
Loads and validates taxonomy_v1.yaml (or any versioned taxonomy file).
Provides helper functions used by the Classification Engine and QA modules.

Usage:
    from src.taxonomy_loader import TaxonomyLoader
    tx = TaxonomyLoader()
    tx.valid_root_cause("RC-01")   # True
    tx.get_label("RC-03")          # "Return Disappointment"
"""

import yaml
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class TaxonomyLoader:
    """
    Loads a versioned taxonomy YAML and exposes validation helpers.
    """

    def __init__(self, path: str = "./taxonomy/taxonomy_v1.yaml"):
        self.path = Path(path)
        self._data: dict = {}
        self._root_cause_map: dict = {}     # code → entry dict
        self._retention_factor_map: dict = {}
        self._lifecycle_stage_map: dict = {}
        self._stop_type_map: dict = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            raise FileNotFoundError(f"Taxonomy file not found: {self.path}")

        with open(self.path, "r", encoding="utf-8") as f:
            self._data = yaml.safe_load(f)

        version = self._data.get("version", "unknown")
        frozen = self._data.get("frozen", False)
        logger.info("Taxonomy loaded: version=%s, frozen=%s", version, frozen)

        # Build lookup maps
        for rc in self._data.get("root_causes", []):
            self._root_cause_map[rc["code"]] = rc

        for rf in self._data.get("retention_factors", []):
            self._retention_factor_map[rf["code"]] = rf

        for ls in self._data.get("lifecycle_stages", []):
            self._lifecycle_stage_map[ls["code"]] = ls

        for st in self._data.get("stop_types", []):
            self._stop_type_map[st["code"]] = st

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def version(self) -> str:
        return self._data.get("version", "unknown")

    @property
    def is_frozen(self) -> bool:
        return self._data.get("frozen", False)

    @property
    def root_cause_codes(self) -> list[str]:
        return list(self._root_cause_map.keys())

    @property
    def retention_factor_codes(self) -> list[str]:
        return list(self._retention_factor_map.keys())

    @property
    def lifecycle_stage_codes(self) -> list[str]:
        return list(self._lifecycle_stage_map.keys())

    @property
    def stop_type_codes(self) -> list[str]:
        return list(self._stop_type_map.keys())

    @property
    def stated_intents(self) -> list[str]:
        return self._data.get("stated_intents", [])

    @property
    def actual_actions(self) -> list[str]:
        return self._data.get("actual_actions", [])

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def valid_root_cause(self, code: str) -> bool:
        return code in self._root_cause_map

    def valid_retention_factor(self, code: str) -> bool:
        return code in self._retention_factor_map

    def valid_lifecycle_stage(self, code: str) -> bool:
        return code in self._lifecycle_stage_map

    def valid_stop_type(self, code: str) -> bool:
        return code in self._stop_type_map

    def valid_stated_intent(self, value: str) -> bool:
        return value in self.stated_intents

    def valid_actual_action(self, value: str) -> bool:
        return value in self.actual_actions

    # ------------------------------------------------------------------
    # Label lookups
    # ------------------------------------------------------------------

    def get_root_cause_label(self, code: str) -> Optional[str]:
        entry = self._root_cause_map.get(code)
        return entry["label"] if entry else None

    def is_addressable(self, root_cause_code: str) -> bool:
        """Returns True if this root cause is considered product-addressable."""
        entry = self._root_cause_map.get(root_cause_code, {})
        return entry.get("addressable", False)

    def get_subcategories(self, root_cause_code: str) -> list[str]:
        entry = self._root_cause_map.get(root_cause_code, {})
        subs = entry.get("subcategories", [])
        return [s["label"] if isinstance(s, dict) else s for s in subs]

    def as_prompt_context(self) -> str:
        """
        Render the taxonomy as a compact string suitable for LLM prompt injection.
        """
        lines = [f"TAXONOMY VERSION: {self.version}", ""]

        lines.append("ROOT CAUSES:")
        for code, rc in self._root_cause_map.items():
            subs = self.get_subcategories(code)
            sub_str = "; ".join(subs) if subs else "—"
            lines.append(f"  {code}: {rc['label']} (addressable={rc.get('addressable', '?')})")
            lines.append(f"    Subcategories: {sub_str}")

        lines.append("")
        lines.append("LIFECYCLE STAGES:")
        for code, ls in self._lifecycle_stage_map.items():
            lines.append(f"  {code}: {ls['label']}")

        lines.append("")
        lines.append("STOP TYPES:")
        for code, st in self._stop_type_map.items():
            lines.append(f"  {code}: {st['label']}")

        lines.append("")
        lines.append("STATED INTENTS (not actual action):")
        lines.append("  " + " | ".join(self.stated_intents))

        lines.append("")
        lines.append("ACTUAL ACTIONS (not stated intent):")
        lines.append("  " + " | ".join(self.actual_actions))

        lines.append("")
        lines.append("RETENTION FACTORS:")
        for code, rf in self._retention_factor_map.items():
            lines.append(f"  {code}: {rf['label']}")

        return "\n".join(lines)

    def summary(self) -> dict:
        """Return a summary dict useful for logging and reports."""
        return {
            "version": self.version,
            "frozen": self.is_frozen,
            "root_cause_count": len(self._root_cause_map),
            "retention_factor_count": len(self._retention_factor_map),
            "lifecycle_stage_count": len(self._lifecycle_stage_map),
            "stop_type_count": len(self._stop_type_map),
        }


if __name__ == "__main__":
    import json
    loader = TaxonomyLoader()
    print("=== Taxonomy Summary ===")
    print(json.dumps(loader.summary(), indent=2))
    print("\n=== Root Cause Codes ===")
    for code in loader.root_cause_codes:
        label = loader.get_root_cause_label(code)
        addressable = loader.is_addressable(code)
        subs = loader.get_subcategories(code)
        print(f"  {code}: {label} [addressable={addressable}]")
        for sub in subs:
            print(f"    - {sub}")
    print("\n=== Prompt Context (first 500 chars) ===")
    print(loader.as_prompt_context()[:500])
