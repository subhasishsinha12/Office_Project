"""Deterministic Rule Engine (§14).

Separate from every LLM/agent in this codebase. Produces the *binding*
maker/checker/KYC-revalidation flags for a request. Agents (Policy Agent,
Intent Agent, Decomposition Agent) may retrieve or explain a rule; only
this module's `RuleEngine.evaluate()` output is used by the workflow
compiler to decide what approvals a request actually needs.

Implemented as an explicit decision table (§14's IF/THEN style), evaluated
over structured facts only — never over free text or model output.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from bankai_core.policy.regulatory_twin import RegulatoryRule


@dataclass(frozen=True)
class Facts:
    customer_type: str
    service: str
    subservice: str
    risk_class: str = "GREEN"


@dataclass(frozen=True)
class RuleOutcome:
    resolution_required: bool
    maker_required: bool
    checker_required: bool
    kyc_revalidation: str  # NOT_REQUIRED | CONDITIONAL | REQUIRED
    escalation_required: bool
    reasons: list[str]


@dataclass(frozen=True)
class DecisionRule:
    rule_id: str
    condition: Callable[[Facts], bool]
    resolution_required: bool = False
    maker_required: bool = True
    checker_required: bool = True
    kyc_revalidation: str = "NOT_REQUIRED"
    escalation_required: bool = False
    description: str = ""


class RuleEngine:
    def __init__(self) -> None:
        self._table: list[DecisionRule] = []

    def add(self, rule: DecisionRule) -> None:
        self._table.append(rule)

    def evaluate(self, facts: Facts, regulatory_rule: RegulatoryRule | None) -> RuleOutcome:
        maker_required = regulatory_rule.maker_required if regulatory_rule else True
        checker_required = regulatory_rule.checker_required if regulatory_rule else True
        kyc = "NOT_REQUIRED"
        resolution_required = False
        escalation_required = False
        reasons: list[str] = []

        if regulatory_rule is None:
            reasons.append("POLICY_CONFIRMATION_REQUIRED: no FINAL, effective regulatory rule matched")
            resolution_required = True
            escalation_required = True

        for rule in self._table:
            if rule.condition(facts):
                maker_required = maker_required or rule.maker_required
                checker_required = checker_required or rule.checker_required
                resolution_required = resolution_required or rule.resolution_required
                escalation_required = escalation_required or rule.escalation_required
                if rule.kyc_revalidation != "NOT_REQUIRED":
                    kyc = rule.kyc_revalidation
                reasons.append(f"{rule.rule_id}: {rule.description}")

        # Risk-driven escalation is itself a deterministic rule, not an AI
        # decision: RED risk always forces checker + escalation regardless
        # of what any agent recommended.
        if facts.risk_class == "RED":
            checker_required = True
            escalation_required = True
            reasons.append("RISK_RED: enhanced review mandated regardless of base policy")
        elif facts.risk_class == "AMBER":
            checker_required = True
            reasons.append("RISK_AMBER: human verification mandated")

        return RuleOutcome(
            resolution_required=resolution_required,
            maker_required=maker_required,
            checker_required=checker_required,
            kyc_revalidation=kyc,
            escalation_required=escalation_required,
            reasons=reasons,
        )


rule_engine = RuleEngine()

rule_engine.add(
    DecisionRule(
        rule_id="RE-001",
        condition=lambda f: f.customer_type == "PARTNERSHIP" and f.subservice == "SIGNATORY",
        resolution_required=True,
        maker_required=True,
        checker_required=True,
        kyc_revalidation="CONDITIONAL",
        description="Partnership signatory change requires resolution, maker and checker; KYC revalidation conditional on documents.",
    )
)
rule_engine.add(
    DecisionRule(
        rule_id="RE-002",
        condition=lambda f: f.customer_type == "PARTNERSHIP" and f.subservice == "PARTNER",
        resolution_required=True,
        maker_required=True,
        checker_required=True,
        kyc_revalidation="REQUIRED",
        description="Partner constitution change always triggers full KYC revalidation.",
    )
)
rule_engine.add(
    DecisionRule(
        rule_id="RE-003",
        condition=lambda f: f.subservice == "MOBILE",
        maker_required=True,
        checker_required=True,
        description="Mobile number modification requires maker and checker per contact-details SOP.",
    )
)
