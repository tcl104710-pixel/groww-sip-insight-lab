"""
SIP Insight Lab — Classification Response Parser (Task 2.11)
=============================================================
Enforces strict JSON schema validation for LLM responses using Pydantic.
Normalises outputs, validates taxonomy codes/enums, and handles markdown fences.

Usage:
    from src.classification.parser import ResponseParser
    parser = ResponseParser()
    parsed_item = parser.parse(raw_llm_string)
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

from src.taxonomy_loader import TaxonomyLoader

logger = logging.getLogger(__name__)


class ParserError(ValueError):
    """Raised when LLM response cannot be parsed or fails schema validation."""
    pass


class InvestorSegmentModel(BaseModel):
    age_group: Optional[str] = "unknown"
    income_stability: Optional[str] = "unknown"
    money_source: Optional[str] = "unknown"
    influencer_type: Optional[str] = "unknown"


class ClassificationOutputModel(BaseModel):
    lifecycle_stage: str = Field(description="LS code (LS-00 to LS-04, LS-99)")
    stated_intent: str = Field(description="continue | pause | stop | neutral | unknown")
    actual_action: str = Field(description="active | paused | cancelled | unknown")
    stop_type: str = Field(description="ST-01 | ST-02 | ST-03 | ST-99")
    root_cause: str = Field(description="RC-01 to RC-07 | RC-99")
    root_cause_sub: Optional[str] = None
    trigger_moment: Optional[str] = None
    help_sources: List[str] = Field(default_factory=list)
    retention_factor: Optional[str] = None
    investor_segment: InvestorSegmentModel = Field(default_factory=InvestorSegmentModel)
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    confidence_score: float = Field(ge=0.0, le=1.0)
    field_confidences: Dict[str, float] = Field(default_factory=dict)

    @field_validator("sentiment_score")
    @classmethod
    def clamp_sentiment(cls, v: float) -> float:
        return max(-1.0, min(1.0, float(v)))

    @field_validator("confidence_score")
    @classmethod
    def clamp_confidence(cls, v: float) -> float:
        return max(0.0, min(1.0, float(v)))


class ResponseParser:
    """
    Parses and validates LLM completion string into a structured, validated dict.
    """

    def __init__(self, taxonomy_loader: Optional[TaxonomyLoader] = None):
        self.taxonomy = taxonomy_loader or TaxonomyLoader()

        # Build mapping from labels to codes for fault tolerance
        self._ls_label_to_code = {
            "pre_first_sip": "LS-00",
            "0_3mo": "LS-01",
            "0-3mo": "LS-01",
            "3_6mo": "LS-02",
            "3-6mo": "LS-02",
            "6_12mo": "LS-03",
            "6-12mo": "LS-03",
            "12mo_plus": "LS-04",
            "12mo+": "LS-04",
            "unknown": "LS-99",
        }
        self._st_label_to_code = {
            "involuntary_lapse": "ST-01",
            "deliberate_exit": "ST-02",
            "not_applicable": "ST-03",
            "unknown": "ST-99",
        }

    def clean_text(self, text: str) -> str:
        """Strip markdown code blocks, backticks, and extra whitespace."""
        cleaned = text.strip()

        # Match ```json ... ``` or ``` ... ```
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
        if fence_match:
            cleaned = fence_match.group(1).strip()
        elif cleaned.startswith("```"):
            cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned).strip()

        return cleaned

    def parse(self, raw_response: str) -> Dict[str, Any]:
        """
        Parse raw response string into validated classification output dictionary.
        """
        if not raw_response or not raw_response.strip():
            raise ParserError("Empty response received from LLM.")

        cleaned = self.clean_text(raw_response)

        # Parse JSON
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            # Fallback: attempt to find first '{' and last '}'
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    data = json.loads(cleaned[start : end + 1])
                except json.JSONDecodeError:
                    raise ParserError(f"Invalid JSON in LLM response: {e}\nRaw snippet: {cleaned[:100]}")
            else:
                raise ParserError(f"No valid JSON object found in response: {e}")

        if not isinstance(data, dict):
            raise ParserError(f"Expected JSON object, got {type(data).__name__}")

        # Normalise / Canonicalise fields
        data = self._canonicalise_data(data)

        # Validate with Pydantic model
        try:
            model = ClassificationOutputModel(**data)
        except Exception as e:
            raise ParserError(f"Schema validation error: {e}")

        # Post-validation against Taxonomy
        result = model.model_dump()
        self._validate_taxonomy_alignment(result)

        return result

    def _canonicalise_data(self, data: dict) -> dict:
        """Normalise field names and code representations."""
        # Handle 'help_source' vs 'help_sources'
        if "help_source" in data and "help_sources" not in data:
            val = data.pop("help_source")
            data["help_sources"] = val if isinstance(val, list) else [val]
        elif "help_sources" not in data:
            data["help_sources"] = ["none_mentioned"]

        # Canonicalise lifecycle_stage
        ls = str(data.get("lifecycle_stage", "LS-99")).strip()
        if ls in self._ls_label_to_code:
            data["lifecycle_stage"] = self._ls_label_to_code[ls]
        elif not self.taxonomy.valid_lifecycle_stage(ls):
            data["lifecycle_stage"] = "LS-99"

        # Canonicalise stop_type
        st = str(data.get("stop_type", "ST-99")).strip()
        if st in self._st_label_to_code:
            data["stop_type"] = self._st_label_to_code[st]
        elif not self.taxonomy.valid_stop_type(st):
            data["stop_type"] = "ST-99"

        # Canonicalise stated_intent
        intent = str(data.get("stated_intent", "unknown")).lower().strip()
        if not self.taxonomy.valid_stated_intent(intent):
            intent = "unknown"
        data["stated_intent"] = intent

        # Canonicalise actual_action
        action = str(data.get("actual_action", "unknown")).lower().strip()
        if not self.taxonomy.valid_actual_action(action):
            action = "unknown"
        data["actual_action"] = action

        # Canonicalise root_cause code
        rc = str(data.get("root_cause", "RC-99")).strip()
        if not self.taxonomy.valid_root_cause(rc):
            # Check if label was provided instead of code
            found_code = None
            for code in self.taxonomy.root_cause_codes:
                lbl = self.taxonomy.get_root_cause_label(code)
                if lbl and lbl.lower() in rc.lower():
                    found_code = code
                    break
            data["root_cause"] = found_code or "RC-99"

        # Ensure field_confidences dict exists
        if "field_confidences" not in data or not isinstance(data["field_confidences"], dict):
            conf = float(data.get("confidence_score", 0.8))
            data["field_confidences"] = {
                "lifecycle_stage": conf,
                "stated_intent": conf,
                "actual_action": conf,
                "stop_type": conf,
                "root_cause": conf,
            }

        return data

    def _validate_taxonomy_alignment(self, item: dict) -> None:
        """Validate adherence to domain rules."""
        # Critical rule check: stated_intent and actual_action must exist
        assert "stated_intent" in item, "Missing stated_intent"
        assert "actual_action" in item, "Missing actual_action"

        # Retention factor null if user cancelled or deliberate exit
        if item.get("actual_action") == "cancelled" and item.get("retention_factor") is not None:
            # Clear retention factor for churned items
            item["retention_factor"] = None


if __name__ == "__main__":
    parser = ResponseParser()
    sample_json = """
    ```json
    {
      "lifecycle_stage": "0_3mo",
      "stated_intent": "stop",
      "actual_action": "active",
      "stop_type": "involuntary_lapse",
      "root_cause": "RC-01",
      "root_cause_sub": "Bank mandate failure",
      "trigger_moment": "Mandate rejected by SBI",
      "help_sources": ["groww_customer_support"],
      "retention_factor": null,
      "investor_segment": {
        "age_group": "25-30",
        "income_stability": "salaried_stable",
        "money_source": "salary_emi",
        "influencer_type": "self_research"
      },
      "sentiment_score": -0.7,
      "confidence_score": 0.91,
      "field_confidences": {
        "lifecycle_stage": 0.88,
        "stated_intent": 0.95,
        "actual_action": 0.92,
        "stop_type": 0.95,
        "root_cause": 0.95
      }
    }
    ```
    """
    res = parser.parse(sample_json)
    print("Parsed output successfully:")
    print(json.dumps(res, indent=2))
