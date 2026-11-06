"""
SIP Insight Lab — Unit and Integration Tests: Phase 2 (Tasks 2.1–2.15)
======================================================================
Tests for:
  - Language detection (Task 2.1)
  - PII scrubber with NER & regex (Tasks 2.2, 2.3)
  - Noise remover (Task 2.4)
  - Text normaliser (Task 2.5)
  - Cleaning pipeline orchestrator & spot-check (Tasks 2.6, 2.7)
  - Prompt builder (Tasks 2.8, 2.9, 2.15)
  - LLM client with retry & mock simulator (Task 2.10)
  - JSON response parser with schema validation (Task 2.11)
  - Confidence scorer (Task 2.12)
  - Human review router (Task 2.13)
  - Classification engine orchestrator (Task 2.14)

Run:
    python -m pytest tests/test_phase2.py -v
"""

import json
import sqlite3
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.cleaning.lang_detect import LanguageDetector
from src.cleaning.noise_removal import NoiseRemover
from src.cleaning.normaliser import TextNormaliser
from src.cleaning.pii_scrubber import PIIScrubber
from src.cleaning.pipeline import CleaningPipeline, CleanedItem
from src.classification.confidence import ConfidenceScorer
from src.classification.engine import ClassificationEngine
from src.classification.llm_client import LLMClient, LLMResponse
from src.classification.parser import ParserError, ResponseParser
from src.classification.prompt_builder import PromptBuilder
from src.classification.router import ClassificationRouter
from src.db.schema import init_db
from src.ingestion.writer import RawItem, RawItemWriter


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def in_memory_db():
    """Provide an in-memory SQLite DB with the full schema for each test."""
    conn = init_db(":memory:")
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Task 2.1 — Language Detector
# ---------------------------------------------------------------------------

class TestLanguageDetector:

    def test_english_accepted(self):
        ld = LanguageDetector()
        text = "Groww cancelled my SIP after 3 failed debits without any alert."
        assert ld.is_accepted(text) is True
        assert ld.detect(text) == "en"

    def test_hindi_devanagari_accepted(self):
        ld = LanguageDetector()
        text = "मेरा SIP बिना किसी सूचना के बंद कर दिया गया। बहुत खराब अनुभव।"
        assert ld.is_accepted(text) is True
        assert ld.detect(text) == "hi"

    def test_unsupported_language_rejected(self):
        ld = LanguageDetector()
        # French text
        text = "Le service client ne répond jamais et mon compte est bloqué depuis trois semaines."
        assert ld.is_accepted(text) is False

    def test_empty_text_handled_safely(self):
        ld = LanguageDetector()
        assert ld.detect("") == "unknown"
        assert ld.is_accepted("") is False


# ---------------------------------------------------------------------------
# Tasks 2.2 & 2.3 — PII Scrubber
# ---------------------------------------------------------------------------

class TestPIIScrubber:

    def test_scrub_phone_number(self):
        scrubber = PIIScrubber(use_ner=False)
        text = "Call me back on 9876543210 regarding my SIP refund."
        cleaned, log = scrubber.scrub(text)
        assert "[REDACTED:PHONE]" in cleaned
        assert "9876543210" not in cleaned
        assert log.get("PHONE") == 1
        assert log.get("total_redacted") >= 1

    def test_scrub_email_address(self):
        scrubber = PIIScrubber(use_ner=False)
        text = "Send my statement to investor.test@gmail.com please."
        cleaned, log = scrubber.scrub(text)
        assert "[REDACTED:EMAIL]" in cleaned
        assert "investor.test@gmail.com" not in cleaned
        assert log.get("EMAIL") == 1

    def test_scrub_upi_id(self):
        scrubber = PIIScrubber(use_ner=False)
        text = "Debited 5000 rs from rahul123@okaxis but SIP not created."
        cleaned, log = scrubber.scrub(text)
        assert "[REDACTED:UPI_ID]" in cleaned
        assert "rahul123@okaxis" not in cleaned
        assert log.get("UPI_ID") == 1

    def test_scrub_aadhaar(self):
        scrubber = PIIScrubber(use_ner=False)
        text = "My Aadhaar card is 9876 5432 1098 for KYC update."
        cleaned, log = scrubber.scrub(text)
        assert "[REDACTED:AADHAAR]" in cleaned
        assert "9876 5432 1098" not in cleaned

    def test_scrub_pan(self):
        scrubber = PIIScrubber(use_ner=False)
        text = "My PAN number ABCDE1234F is already verified."
        cleaned, log = scrubber.scrub(text)
        assert "[REDACTED:PAN]" in cleaned
        assert "ABCDE1234F" not in cleaned

    def test_values_never_stored_in_log(self):
        scrubber = PIIScrubber(use_ner=False)
        sensitive = "Call 9123456789 or email secret@corp.in"
        cleaned, log = scrubber.scrub(sensitive)
        log_str = json.dumps(log)
        assert "9123456789" not in log_str
        assert "secret@corp.in" not in log_str

    def test_has_pii(self):
        scrubber = PIIScrubber(use_ner=False)
        assert scrubber.has_pii("Contact me on 9876543210") is True
        assert scrubber.has_pii("Groww app SIP returns are very solid.") is False


# ---------------------------------------------------------------------------
# Task 2.4 — Noise Remover
# ---------------------------------------------------------------------------

class TestNoiseRemover:

    def test_strip_html(self):
        nr = NoiseRemover()
        raw = "<p>My SIP failed on <b>Monday</b> &amp; customer care was unhelpful.</p>"
        cleaned = nr.clean(raw)
        assert "<p>" not in cleaned
        assert "<b>" not in cleaned
        assert "&amp;" not in cleaned
        assert "Monday & customer care" in cleaned

    def test_strip_urls(self):
        nr = NoiseRemover()
        raw = "Read full details at https://groww.in/blog/sip-rules and help me."
        cleaned = nr.clean(raw)
        assert "https://" not in cleaned
        assert "groww.in" not in cleaned

    def test_collapse_excessive_punctuation(self):
        nr = NoiseRemover()
        raw = "Groww app failed again!!!! Why?????"
        cleaned = nr.clean(raw)
        assert "!!!!" not in cleaned
        assert "????" not in cleaned
        assert "!!" in cleaned
        assert "??" in cleaned

    def test_collapse_repeated_words(self):
        nr = NoiseRemover()
        raw = "The service is very very very bad bad bad."
        cleaned = nr.clean(raw)
        assert "bad bad bad" not in cleaned

    def test_dedup_duplicate_sentences(self):
        nr = NoiseRemover()
        raw = "My mandate was rejected. My mandate was rejected. Please help."
        cleaned = nr.clean(raw)
        assert cleaned.count("My mandate was rejected.") == 1


# ---------------------------------------------------------------------------
# Task 2.5 — Text Normaliser
# ---------------------------------------------------------------------------

class TestTextNormaliser:

    def test_nfkc_and_whitespace(self):
        tn = TextNormaliser()
        raw = "  My\u00a0SIP\t\tinvestment   is\r\ngreat.  "
        norm = tn.normalise(raw)
        assert norm == "My SIP investment is\ngreat."

    def test_mojibake_encoding_fixes(self):
        tn = TextNormaliser()
        raw = "I\u00e2\u20ac\u2122m not happy \u00a0 payment failed."
        norm = tn.normalise(raw)
        assert norm == "I'm not happy payment failed."

    def test_preserves_casing_for_acronyms(self):
        tn = TextNormaliser()
        raw = "My SIP, NAV, and KYC are in order."
        norm = tn.normalise(raw)
        assert "SIP" in norm
        assert "NAV" in norm
        assert "KYC" in norm


# ---------------------------------------------------------------------------
# Tasks 2.6 & 2.7 — Cleaning Pipeline Orchestrator & Spot-Check
# ---------------------------------------------------------------------------

class TestCleaningPipeline:

    def test_end_to_end_cleaning_and_db_write(self, in_memory_db):
        writer = RawItemWriter(in_memory_db)
        raw = RawItem(
            source="play_store",
            source_id="rev_1",
            raw_text="<p>Call 9876543210. Groww SIP stopped due to mandate fail.</p>",
            raw_url="https://play.google.com/1",
            dedup_hash="hash_1",
        )
        writer.write(raw)

        pipeline = CleaningPipeline(in_memory_db, use_ner=False)
        stats = pipeline.run()

        assert stats["total_raw"] == 1
        assert stats["cleaned_and_written"] == 1
        assert stats["pii_total_redacted"] >= 1

        # Check DB row
        cursor = in_memory_db.cursor()
        cursor.execute("SELECT cleaned_text, language, pii_removal_log FROM cleaned_item WHERE item_id = ?", (raw.item_id,))
        row = cursor.fetchone()
        assert row is not None
        cleaned_text, lang, pii_log_json = row
        assert "[REDACTED:PHONE]" in cleaned_text
        assert "9876543210" not in cleaned_text
        assert lang == "en"

    def test_spot_check_sampling(self, in_memory_db):
        writer = RawItemWriter(in_memory_db)
        for i in range(5):
            writer.write(RawItem(
                source="reddit",
                source_id=f"r_{i}",
                raw_text=f"SIP discussion number {i} with no issues.",
                raw_url=f"https://reddit.com/{i}",
                dedup_hash=f"hash_r_{i}",
            ))

        pipeline = CleaningPipeline(in_memory_db, use_ner=False)
        pipeline.run()

        sample = pipeline.spot_check(n=3)
        assert len(sample) == 3
        assert "cleaned_text" in sample[0]
        assert "source" in sample[0]


# ---------------------------------------------------------------------------
# Tasks 2.8, 2.9, 2.15 — Prompt Builder & Versioning
# ---------------------------------------------------------------------------

class TestPromptBuilder:

    def test_prompt_builder_v1_and_v2(self):
        pb1 = PromptBuilder(version="v1")
        prompt1 = pb1.build_prompt("My SIP failed", source="reddit")
        assert "Research Taxonomy" in prompt1
        assert "Output Schema" in prompt1
        assert "CRITICAL RULE" in prompt1

        pb2 = PromptBuilder(version="v2")
        prompt2 = pb2.build_prompt("My SIP failed", source="reddit")
        assert "CRITICAL DISAMBIGUATION RULES" in prompt2
        assert "INVOLUNTARY LAPSE" in prompt2

    def test_few_shot_injection(self):
        pb = PromptBuilder(version="v1")
        few_shots = pb.format_few_shots(count=2)
        assert "Example 1:" in few_shots
        assert "Example 2:" in few_shots
        assert "lifecycle_stage" in few_shots


# ---------------------------------------------------------------------------
# Task 2.10 — LLM Client
# ---------------------------------------------------------------------------

class TestLLMClient:

    def test_mock_simulator_response(self):
        client = LLMClient(provider="mock")
        prompt = "Groww auto-cancelled my SIP because of 3 failed debits due to bank mandate issue."
        res = client.generate(prompt)

        assert isinstance(res, LLMResponse)
        assert res.provider == "mock"
        assert res.total_tokens > 0

        data = json.loads(res.raw_text)
        assert data["root_cause"] == "RC-01"
        assert data["stop_type"] == "ST-01"
        assert data["actual_action"] == "cancelled"

    def test_stats_tracking(self):
        client = LLMClient(provider="mock")
        client.generate("Test prompt 1")
        client.generate("Test prompt 2")
        stats = client.stats()
        assert stats["total_calls"] == 2
        assert stats["successful_calls"] == 2
        assert stats["total_tokens"] > 0


# ---------------------------------------------------------------------------
# Task 2.11 — Response Parser
# ---------------------------------------------------------------------------

class TestResponseParser:

    def test_parse_valid_json_with_code_fences(self):
        parser = ResponseParser()
        raw_llm = """
        ```json
        {
          "lifecycle_stage": "LS-01",
          "stated_intent": "stop",
          "actual_action": "active",
          "stop_type": "ST-02",
          "root_cause": "RC-03",
          "root_cause_sub": "Calculator mismatch",
          "trigger_moment": "1 year returns were low",
          "help_sources": ["reddit"],
          "retention_factor": null,
          "investor_segment": {
            "age_group": "25-30",
            "income_stability": "salaried_stable",
            "money_source": "salary_emi",
            "influencer_type": "self_research"
          },
          "sentiment_score": -0.6,
          "confidence_score": 0.88,
          "field_confidences": {
            "lifecycle_stage": 0.85,
            "stated_intent": 0.90,
            "actual_action": 0.88,
            "stop_type": 0.85,
            "root_cause": 0.90
          }
        }
        ```
        """
        parsed = parser.parse(raw_llm)
        assert parsed["lifecycle_stage"] == "LS-01"
        assert parsed["stated_intent"] == "stop"
        assert parsed["actual_action"] == "active"
        assert parsed["root_cause"] == "RC-03"
        assert parsed["sentiment_score"] == -0.6

    def test_canonicalises_label_to_code(self):
        parser = ResponseParser()
        raw = json.dumps({
            "lifecycle_stage": "0_3mo",
            "stated_intent": "pause",
            "actual_action": "paused",
            "stop_type": "involuntary_lapse",
            "root_cause": "RC-01",
            "sentiment_score": -0.5,
            "confidence_score": 0.8,
        })
        parsed = parser.parse(raw)
        assert parsed["lifecycle_stage"] == "LS-01"
        assert parsed["stop_type"] == "ST-01"

    def test_invalid_json_raises_parser_error(self):
        parser = ResponseParser()
        with pytest.raises(ParserError):
            parser.parse("Not a JSON string at all.")


# ---------------------------------------------------------------------------
# Task 2.12 — Confidence Scorer
# ---------------------------------------------------------------------------

class TestConfidenceScorer:

    def test_confident_item_passes(self):
        scorer = ConfidenceScorer(threshold=0.75)
        item = {
            "root_cause": "RC-01",
            "stated_intent": "stop",
            "actual_action": "cancelled",
            "stop_type": "ST-01",
            "lifecycle_stage": "LS-01",
            "confidence_score": 0.88,
            "field_confidences": {
                "root_cause": 0.90,
                "stated_intent": 0.90,
                "actual_action": 0.90,
                "stop_type": 0.85,
                "lifecycle_stage": 0.80,
            },
        }
        eval_res = scorer.evaluate(item)
        assert eval_res.is_confident is True
        assert eval_res.aggregate_score >= 0.75
        assert len(eval_res.flags) == 0

    def test_low_confidence_item_flagged(self):
        scorer = ConfidenceScorer(threshold=0.75)
        item = {
            "root_cause": "RC-02",
            "stated_intent": "unknown",
            "actual_action": "unknown",
            "stop_type": "ST-99",
            "lifecycle_stage": "LS-99",
            "confidence_score": 0.60,
            "field_confidences": {
                "root_cause": 0.55,
                "stated_intent": 0.60,
                "actual_action": 0.60,
                "stop_type": 0.50,
                "lifecycle_stage": 0.50,
            },
        }
        eval_res = scorer.evaluate(item)
        assert eval_res.is_confident is False
        assert eval_res.routing_reason == "low_confidence"

    def test_unclassifiable_root_cause_routed_to_review(self):
        scorer = ConfidenceScorer(threshold=0.75)
        item = {
            "root_cause": "RC-99",
            "stated_intent": "neutral",
            "actual_action": "active",
            "stop_type": "ST-03",
            "lifecycle_stage": "LS-01",
            "confidence_score": 0.90,
            "field_confidences": {
                "root_cause": 0.85,
                "stated_intent": 0.90,
                "actual_action": 0.90,
                "stop_type": 0.90,
                "lifecycle_stage": 0.90,
            },
        }
        eval_res = scorer.evaluate(item)
        assert eval_res.is_confident is False
        assert "unclassifiable_root_cause" in eval_res.flags


# ---------------------------------------------------------------------------
# Task 2.13 — Router
# ---------------------------------------------------------------------------

def _seed_cleaned_item(conn, item_id: str):
    conn.execute(
        "INSERT OR IGNORE INTO raw_item (item_id, source, source_id, raw_text, dedup_hash, collected_at) VALUES (?, 'play_store', 'src_1', 'dummy text', ?, datetime('now'))",
        (item_id, f"hash_{item_id}"),
    )
    conn.execute(
        "INSERT OR IGNORE INTO cleaned_item (item_id, cleaned_text, language, cleaning_version, cleaned_at) VALUES (?, 'dummy clean text', 'en', '1.0', datetime('now'))",
        (item_id,),
    )


class TestClassificationRouter:

    def test_route_auto_accepted(self, in_memory_db):
        _seed_cleaned_item(in_memory_db, "item_101")
        router = ClassificationRouter(in_memory_db)
        scorer = ConfidenceScorer(threshold=0.75)

        data = {
            "lifecycle_stage": "LS-01",
            "stated_intent": "stop",
            "actual_action": "cancelled",
            "stop_type": "ST-01",
            "root_cause": "RC-01",
            "sentiment_score": -0.8,
            "confidence_score": 0.92,
            "field_confidences": {"root_cause": 0.92},
        }
        evaluation = scorer.evaluate(data)
        dest, rec_id = router.route("item_101", data, evaluation)

        assert dest == "auto"
        assert rec_id == "item_101"

        # Check DB row
        cursor = in_memory_db.cursor()
        cursor.execute("SELECT review_status FROM labelled_item WHERE item_id = 'item_101'")
        assert cursor.fetchone()[0] == "auto"

        # Verify nothing entered into human_review_queue
        assert router.get_queue_backlog_count() == 0

    def test_route_human_review_queue(self, in_memory_db):
        _seed_cleaned_item(in_memory_db, "item_102")
        router = ClassificationRouter(in_memory_db)
        scorer = ConfidenceScorer(threshold=0.75)

        data = {
            "lifecycle_stage": "LS-99",
            "stated_intent": "unknown",
            "actual_action": "unknown",
            "stop_type": "ST-99",
            "root_cause": "RC-99",
            "sentiment_score": 0.0,
            "confidence_score": 0.55,
            "field_confidences": {"root_cause": 0.50},
        }
        evaluation = scorer.evaluate(data)
        dest, queue_id = router.route("item_102", data, evaluation)

        assert dest == "human_review"
        assert queue_id is not None

        # Check DB row in labelled_item
        cursor = in_memory_db.cursor()
        cursor.execute("SELECT review_status FROM labelled_item WHERE item_id = 'item_102'")
        assert cursor.fetchone()[0] == "flagged"

        # Check entry in human_review_queue
        assert router.get_queue_backlog_count() == 1


# ---------------------------------------------------------------------------
# Task 2.14 — Classification Engine End-to-End
# ---------------------------------------------------------------------------

class TestClassificationEngine:

    def test_pilot_classification_batch(self, in_memory_db):
        writer = RawItemWriter(in_memory_db)
        # Create 5 test items with different characteristics
        items = [
            ("item_1", "Groww mandate failed 3 times, auto-cancelled my SIP!"),
            ("item_2", "I lost my job so I had to stop investing this month."),
            ("item_3", "Great app, continuing SIP every month on salary day for rupee cost averaging."),
            ("item_4", "Calculator promised 15% but I'm getting negative returns, very disappointed."),
            ("item_5", "Why was money deducted today? Mutual funds are confusing."),
        ]
        for item_id, text in items:
            writer.write(RawItem(
                source="play_store",
                source_id=item_id,
                raw_text=text,
                raw_url=f"https://play.google.com/{item_id}",
                dedup_hash=f"hash_{item_id}",
            ))

        # Run cleaning pipeline
        clean_pipeline = CleaningPipeline(in_memory_db, use_ner=False)
        clean_pipeline.run()

        # Run classification engine with mock provider
        engine = ClassificationEngine(
            conn=in_memory_db,
            llm_client=LLMClient(provider="mock"),
            prompt_version="v2",
        )

        report = engine.run(limit=10)

        assert report["total_processed"] == 5
        assert report["auto_accepted"] + report["human_review_routed"] == 5
        assert report["items_per_minute"] > 10.0
        assert report["meets_throughput_target"] is True
        assert len(report["root_cause_distribution"]) > 0

        # Verify DB rows exist in labelled_item
        cursor = in_memory_db.cursor()
        cursor.execute("SELECT count(*) FROM labelled_item")
        assert cursor.fetchone()[0] == 5
