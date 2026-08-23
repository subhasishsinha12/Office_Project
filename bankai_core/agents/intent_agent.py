"""Intent Agent (§9) — advisory only."""
from __future__ import annotations

from dataclasses import dataclass

from bankai_core.agents.base import AdvisoryAgent

CONFIDENCE_THRESHOLD = 0.6


@dataclass(frozen=True)
class IntentResult:
    intent_code: str | None
    domain: str | None
    service: str | None
    subservice: str | None
    action: str | None
    confidence: float
    human_clarification_required: bool


class IntentAgent(AdvisoryAgent):
    agent_id = "INTENT_AGENT"

    def classify(self, text: str, caller_role: str, caller_id: str) -> IntentResult:
        result = self._invoke(
            caller_role=caller_role,
            caller_id=caller_id,
            task_type="intent_classification",
            instructions="Classify the banking service request into the canonical taxonomy.",
            data={"text": text},
        )
        structured = result.response.structured
        confidence = result.response.confidence
        return IntentResult(
            intent_code=structured.get("intent_code"),
            domain=structured.get("domain"),
            service=structured.get("service"),
            subservice=structured.get("subservice"),
            action=structured.get("action"),
            confidence=confidence,
            human_clarification_required=confidence < CONFIDENCE_THRESHOLD or not structured.get("intent_code"),
        )


intent_agent = IntentAgent()
