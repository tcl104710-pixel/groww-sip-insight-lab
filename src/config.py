"""
SIP Insight Lab — Configuration Loader
=======================================
Loads config.yaml and exposes a typed, singleton Config object.
Import this in any module that needs configuration:

    from src.config import config
    print(config.classification.confidence_threshold)
"""

import os
import yaml
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

_CONFIG_PATH = os.getenv("CONFIG_PATH", "./config.yaml")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Typed configuration sub-sections
# ---------------------------------------------------------------------------

@dataclass
class TaxonomyConfig:
    active_version: str = "1.0"
    path: str = "./taxonomy/taxonomy_v1.yaml"


@dataclass
class ClassificationConfig:
    confidence_threshold: float = 0.75
    max_tokens: int = 2048
    few_shot_count: int = 3
    max_retries: int = 3
    retry_backoff_seconds: float = 2.0
    provider: str = "openai"


@dataclass
class HumanReviewConfig:
    sla_hours: int = 48
    backlog_alert_threshold: int = 50


@dataclass
class QAConfig:
    min_golden_set_size: int = 20
    target_overall_accuracy: float = 0.80
    target_per_field_f1: float = 0.75
    max_human_review_rate: float = 0.20


@dataclass
class OpportunityScoringConfig:
    frequency_weight: float = 0.30
    severity_weight: float = 0.25
    first_6mo_concentration_weight: float = 0.25
    addressability_weight: float = 0.20


@dataclass
class EthicsConfig:
    blocked_phrases: list = field(default_factory=list)
    nudge_checklist_required: bool = True
    pii_scan_before_export: bool = True
    findings_are_hypotheses_only: bool = True


@dataclass
class LoggingConfig:
    level: str = "INFO"
    log_dir: str = "./outputs/logs"
    max_bytes: int = 10485760
    backup_count: int = 5


@dataclass
class Config:
    taxonomy: TaxonomyConfig = field(default_factory=TaxonomyConfig)
    classification: ClassificationConfig = field(default_factory=ClassificationConfig)
    human_review: HumanReviewConfig = field(default_factory=HumanReviewConfig)
    qa: QAConfig = field(default_factory=QAConfig)
    opportunity_scoring: OpportunityScoringConfig = field(default_factory=OpportunityScoringConfig)
    ethics: EthicsConfig = field(default_factory=EthicsConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    project_name: str = "SIP Insight Lab"
    phase: int = 0


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def load_config(path: str = _CONFIG_PATH) -> Config:
    """
    Load and parse config.yaml into a typed Config object.

    Args:
        path: Path to the YAML config file.

    Returns:
        A populated Config dataclass instance.
    """
    config_path = Path(path)
    if not config_path.exists():
        logger.warning("Config file not found at %s — using defaults.", path)
        return Config()

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    c = Config()
    c.project_name = raw.get("project", {}).get("name", "SIP Insight Lab")
    c.phase = raw.get("project", {}).get("phase", 0)

    # taxonomy
    tx = raw.get("taxonomy", {})
    c.taxonomy = TaxonomyConfig(
        active_version=tx.get("active_version", "1.0"),
        path=tx.get("path", "./taxonomy/taxonomy_v1.yaml"),
    )

    # classification
    cl = raw.get("classification", {})
    c.classification = ClassificationConfig(
        confidence_threshold=cl.get("confidence_threshold", 0.75),
        max_tokens=cl.get("max_tokens", 2048),
        few_shot_count=cl.get("few_shot_count", 3),
        max_retries=cl.get("max_retries", 3),
        retry_backoff_seconds=cl.get("retry_backoff_seconds", 2.0),
        provider=cl.get("provider", "openai"),
    )

    # human review
    hr = raw.get("human_review", {})
    c.human_review = HumanReviewConfig(
        sla_hours=hr.get("sla_hours", 48),
        backlog_alert_threshold=hr.get("backlog_alert_threshold", 50),
    )

    # qa
    qa = raw.get("qa", {})
    c.qa = QAConfig(
        min_golden_set_size=qa.get("min_golden_set_size", 20),
        target_overall_accuracy=qa.get("target_overall_accuracy", 0.80),
        target_per_field_f1=qa.get("target_per_field_f1", 0.75),
        max_human_review_rate=qa.get("max_human_review_rate", 0.20),
    )

    # opportunity scoring
    ops = raw.get("opportunity_scoring", {})
    c.opportunity_scoring = OpportunityScoringConfig(
        frequency_weight=ops.get("frequency_weight", 0.30),
        severity_weight=ops.get("severity_weight", 0.25),
        first_6mo_concentration_weight=ops.get("first_6mo_concentration_weight", 0.25),
        addressability_weight=ops.get("addressability_weight", 0.20),
    )

    # ethics
    eth = raw.get("ethics", {})
    c.ethics = EthicsConfig(
        blocked_phrases=eth.get("blocked_phrases", []),
        nudge_checklist_required=eth.get("nudge_checklist_required", True),
        pii_scan_before_export=eth.get("pii_scan_before_export", True),
        findings_are_hypotheses_only=eth.get("findings_are_hypotheses_only", True),
    )

    # logging
    lg = raw.get("logging", {})
    c.logging = LoggingConfig(
        level=lg.get("level", "INFO"),
        log_dir=lg.get("log_dir", "./outputs/logs"),
        max_bytes=lg.get("max_bytes", 10485760),
        backup_count=lg.get("backup_count", 5),
    )

    logger.info("Config loaded from %s (phase %d)", path, c.phase)
    return c


# Singleton — import `config` directly
config: Config = load_config()
