"""
SIP Insight Lab — Classification Engine Orchestrator (Tasks 2.14 & 2.15)
========================================================================
Runs the end-to-end classification pipeline:
  cleaned_item -> PromptBuilder -> LLMClient -> ResponseParser -> ConfidenceScorer -> Router

Monitors throughput (ensuring >= 10 items/min requirement is met)
and tracks detailed distribution statistics for pilot and production batches.

Usage:
    from src.classification.engine import ClassificationEngine
    engine = ClassificationEngine(conn)
    report = engine.run(limit=200, prompt_version="v2")
"""

import json
import logging
import sqlite3
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

from src.classification.confidence import ConfidenceScorer
from src.classification.llm_client import LLMClient
from src.classification.parser import ResponseParser
from src.classification.prompt_builder import PromptBuilder
from src.classification.router import ClassificationRouter
from src.config import config
from src.taxonomy_loader import TaxonomyLoader

logger = logging.getLogger(__name__)


class ClassificationEngine:
    """
    End-to-end orchestrator for the LLM Classification Engine.
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        llm_client: Optional[LLMClient] = None,
        prompt_version: str = "v1",
        confidence_threshold: Optional[float] = None,
    ):
        self.conn = conn
        self.taxonomy = TaxonomyLoader()
        self.prompt_builder = PromptBuilder(version=prompt_version, taxonomy_loader=self.taxonomy)
        self.llm_client = llm_client or LLMClient()
        self.parser = ResponseParser(taxonomy_loader=self.taxonomy)
        self.scorer = ConfidenceScorer(threshold=confidence_threshold)
        self.router = ClassificationRouter(conn, taxonomy_version=self.taxonomy.version)

    def classify_single(
        self,
        item_id: str,
        cleaned_text: str,
        source: str = "play_store",
        star_rating: Optional[int] = None,
        save_to_db: bool = True,
    ) -> Dict:
        """
        Classify a single item end-to-end and route to DB.
        """
        prompt = self.prompt_builder.build_prompt(
            cleaned_text=cleaned_text,
            source=source,
            star_rating=star_rating,
        )

        response = self.llm_client.generate(prompt)
        parsed = self.parser.parse(response.raw_text)
        evaluation = self.scorer.evaluate(parsed)

        if save_to_db:
            dest, dest_id = self.router.route(item_id, parsed, evaluation)
        else:
            dest, dest_id = "in_memory", None

        return {
            "item_id": item_id,
            "destination": dest,
            "destination_id": dest_id,
            "parsed": parsed,
            "evaluation": evaluation,
            "llm_response": response,
        }

    def run(
        self,
        limit: Optional[int] = None,
        prompt_version: Optional[str] = None,
        reprocess: bool = False,
    ) -> Dict:
        """
        Run classification on cleaned items in the DB.

        Args:
            limit: Maximum items to classify (e.g. 200 for pilot batch).
            prompt_version: 'v1' or 'v2'.
            reprocess: Whether to reclassify already labelled items.
        """
        if prompt_version:
            self.prompt_builder.set_version(prompt_version)

        unprocessed = self._fetch_unprocessed(limit=limit, reprocess=reprocess)
        total_items = len(unprocessed)
        logger.info("ClassificationEngine: Starting run on %d items (prompt=%s)...", total_items, self.prompt_builder.version)

        if total_items == 0:
            return {
                "total_processed": 0,
                "auto_accepted": 0,
                "human_review_routed": 0,
                "items_per_minute": 0.0,
                "avg_confidence": 0.0,
                "message": "No unclassified items found.",
            }

        start_time = time.time()
        auto_accepted = 0
        human_review_routed = 0
        errors = 0
        conf_sum = 0.0
        root_causes: Dict[str, int] = {}
        intents: Dict[str, int] = {}
        actions: Dict[str, int] = {}

        for idx, (item_id, text, source, rating) in enumerate(unprocessed, 1):
            try:
                result = self.classify_single(
                    item_id=item_id,
                    cleaned_text=text,
                    source=source or "unknown",
                    star_rating=rating,
                )

                parsed = result["parsed"]
                eval_res = result["evaluation"]
                conf_sum += eval_res.aggregate_score

                if result["destination"] == "auto":
                    auto_accepted += 1
                else:
                    human_review_routed += 1

                rc = parsed.get("root_cause", "RC-99")
                root_causes[rc] = root_causes.get(rc, 0) + 1

                si = parsed.get("stated_intent", "unknown")
                intents[si] = intents.get(si, 0) + 1

                act = parsed.get("actual_action", "unknown")
                actions[act] = actions.get(act, 0) + 1

            except Exception as e:
                logger.error("Failed to classify item %s: %s", item_id, e)
                errors += 1

        elapsed_sec = max(time.time() - start_time, 0.001)
        items_per_minute = round((total_items / elapsed_sec) * 60.0, 2)
        avg_confidence = round(conf_sum / max(total_items - errors, 1), 3)

        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prompt_version": self.prompt_builder.version,
            "total_processed": total_items,
            "auto_accepted": auto_accepted,
            "human_review_routed": human_review_routed,
            "errors": errors,
            "avg_confidence": avg_confidence,
            "elapsed_seconds": round(elapsed_sec, 2),
            "items_per_minute": items_per_minute,
            "meets_throughput_target": items_per_minute >= 10.0,
            "root_cause_distribution": root_causes,
            "stated_intent_distribution": intents,
            "actual_action_distribution": actions,
            "llm_stats": self.llm_client.stats(),
        }

        logger.info(
            "ClassificationEngine finished: %d items, %.1f items/min, %d auto, %d review",
            total_items,
            items_per_minute,
            auto_accepted,
            human_review_routed,
        )
        return report

    def _fetch_unprocessed(self, limit: Optional[int] = None, reprocess: bool = False) -> List[tuple]:
        """Fetch items from cleaned_item that have not yet been labelled."""
        query = """
            SELECT c.item_id, c.cleaned_text, r.source, r.star_rating
            FROM cleaned_item c
            JOIN raw_item r ON c.item_id = r.item_id
        """
        if not reprocess:
            query += " LEFT JOIN labelled_item l ON c.item_id = l.item_id WHERE l.item_id IS NULL "

        if limit:
            query += f" LIMIT {int(limit)}"

        cursor = self.conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()
