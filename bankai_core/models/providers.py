"""Mock model providers for the three routing tiers.

Deterministic and keyword-based by design (see base.py docstring for why).
Each provider only ever reads `payload.data`/`payload.context` as data — it
never treats them as instructions, and none of these providers can emit a
field that the workflow engine treats as an authorization (that is enforced
structurally in `workflow/maker_checker.py`, not here).
"""
from __future__ import annotations

import re

from bankai_core.models.base import ModelProvider, ModelResponse, ModelTier, PromptPayload

_INTENT_KEYWORDS: list[tuple[str, str, str, str, str]] = [
    # (keyword_pattern, domain, service, subservice, intent_code)
    (r"\bmobile\b|\bphone number\b|\bcontact number\b", "CUSTOMER_MAINTENANCE", "CONTACT_DETAILS", "MOBILE", "CM_CONTACT_MOBILE_MOD"),
    (r"\baddress\b", "CUSTOMER_MAINTENANCE", "CONTACT_DETAILS", "ADDRESS", "CM_CONTACT_ADDRESS_MOD"),
    (r"\be-?mail\b", "CUSTOMER_MAINTENANCE", "CONTACT_DETAILS", "EMAIL", "CM_CONTACT_EMAIL_MOD"),
    (r"\bpartner\b.*\b(retir|resign|join|add|remov)", "CUSTOMER_MAINTENANCE", "CONSTITUTION", "PARTNER", "CM_PARTNER_CONSTITUTION_CHANGE"),
    (r"\bsignatory\b|\bsigning authority\b", "CUSTOMER_MAINTENANCE", "MANDATE", "SIGNATORY", "CM_SIGNATORY_CHANGE"),
    (r"\bstop\b.*\bcheque\b|\bcheque\b.*\bstop\b", "CHEQUES", "CHEQUE_BOOK", "STOP_PAYMENT", "CQ_STOP_PAYMENT"),
    (r"\bnominee\b", "CUSTOMER_MAINTENANCE", "PROFILE", "NOMINEE", "CM_NOMINEE_UPDATE"),
]


class RuleBasedProvider(ModelProvider):
    """Tier 1 — deterministic classification / scoring. No hallucination risk."""

    tier = ModelTier.TIER_1_DETERMINISTIC
    model_id = "bankai-tier1-rules"

    def generate(self, payload: PromptPayload) -> ModelResponse:
        if payload.task_type == "intent_classification":
            return self._classify_intent(payload)
        if payload.task_type == "risk_scoring":
            return self._score_risk(payload)
        raise ValueError(f"RuleBasedProvider cannot handle task_type={payload.task_type!r}")

    def _classify_intent(self, payload: PromptPayload) -> ModelResponse:
        text = str(payload.data.get("text", "")).lower()
        for pattern, domain, service, subservice, intent_code in _INTENT_KEYWORDS:
            if re.search(pattern, text):
                structured = {
                    "domain": domain,
                    "service": service,
                    "subservice": subservice,
                    "action": "MODIFY",
                    "intent_code": intent_code,
                }
                return ModelResponse(
                    text=f"Classified as {intent_code}",
                    structured=structured,
                    confidence=0.97,
                    model_id=self.model_id,
                    model_version=self.model_version,
                )
        return ModelResponse(
            text="No confident match",
            structured={"intent_code": None},
            confidence=0.3,
            model_id=self.model_id,
            model_version=self.model_version,
        )

    def _score_risk(self, payload: PromptPayload) -> ModelResponse:
        changed_fields = set(payload.data.get("changed_fields", []))
        sensitive = {"MOBILE", "EMAIL", "ADDRESS"}
        overlap = changed_fields & sensitive
        recent_mobile_changes = int(payload.data.get("recent_mobile_changes_90d", 0))
        failed_otp = int(payload.data.get("failed_otp_attempts", 0))

        reasons = []
        score = 0
        if len(overlap) >= 2:
            score += 50
            reasons.append(f"simultaneous change of {sorted(overlap)}")
        if recent_mobile_changes >= 2:
            score += 30
            reasons.append(f"{recent_mobile_changes} mobile changes in last 90 days")
        if failed_otp >= 3:
            score += 25
            reasons.append(f"{failed_otp} failed OTP attempts")

        risk_class = "GREEN"
        if score >= 60:
            risk_class = "RED"
        elif score >= 30:
            risk_class = "AMBER"

        return ModelResponse(
            text=f"risk_class={risk_class}",
            structured={"risk_score": score, "risk_class": risk_class, "risk_reasons": reasons},
            confidence=0.9,
            model_id=self.model_id,
            model_version=self.model_version,
        )


class SmallModelProvider(ModelProvider):
    """Tier 2 — SLM stand-in for extraction / summarization / routine intent."""

    tier = ModelTier.TIER_2_SLM
    model_id = "bankai-tier2-slm-mock"

    def generate(self, payload: PromptPayload) -> ModelResponse:
        if payload.task_type == "document_field_extraction":
            return self._extract_fields(payload)
        if payload.task_type == "summarize":
            text = str(payload.data.get("text", ""))
            summary = text.strip().split(".")[0][:200]
            return ModelResponse(
                text=summary,
                structured={"summary": summary},
                confidence=0.8,
                model_id=self.model_id,
                model_version=self.model_version,
            )
        raise ValueError(f"SmallModelProvider cannot handle task_type={payload.task_type!r}")

    def _extract_fields(self, payload: PromptPayload) -> ModelResponse:
        text = str(payload.data.get("text", ""))
        pan_matches = re.findall(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", text)
        names = re.findall(r"(?:Mr\.|Ms\.|Mrs\.)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)", text)
        structured = {
            "pan_numbers_detected": pan_matches,
            "names_detected": names,
            "fields_extracted": len(pan_matches) + len(names),
        }
        return ModelResponse(
            text=f"Extracted {structured['fields_extracted']} field(s)",
            structured=structured,
            confidence=0.75 if structured["fields_extracted"] else 0.4,
            model_id=self.model_id,
            model_version=self.model_version,
        )


class LargeModelProvider(ModelProvider):
    """Tier 3 — LLM stand-in for multi-part reasoning / request decomposition."""

    tier = ModelTier.TIER_3_LLM
    model_id = "bankai-tier3-llm-mock"

    def generate(self, payload: PromptPayload) -> ModelResponse:
        if payload.task_type == "decompose_request":
            return self._decompose(payload)
        raise ValueError(f"LargeModelProvider cannot handle task_type={payload.task_type!r}")

    def _decompose(self, payload: PromptPayload) -> ModelResponse:
        text = str(payload.data.get("text", ""))
        # Split on conjunctions to find candidate child requests; classify
        # each fragment with the same Tier-1 rules used for a single-intent
        # request. This is advisory decomposition only — the deterministic
        # rule engine independently validates each child's requirements.
        fragments = re.split(r"\band\b|,", text, flags=re.IGNORECASE)
        classifier = RuleBasedProvider()
        children = []
        for frag in fragments:
            frag = frag.strip()
            if not frag:
                continue
            resp = classifier.generate(PromptPayload(task_type="intent_classification", instructions="", data={"text": frag}))
            if resp.structured.get("intent_code"):
                children.append({"fragment": frag, **resp.structured})
        return ModelResponse(
            text=f"Decomposed into {len(children)} child request(s)",
            structured={"children": children},
            confidence=0.85 if children else 0.4,
            model_id=self.model_id,
            model_version=self.model_version,
        )
