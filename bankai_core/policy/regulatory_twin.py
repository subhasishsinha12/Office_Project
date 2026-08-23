"""Regulatory Digital Twin (§12) — machine-readable, version-controlled
regulatory/policy database.

All synthetic content — no real RBI circular numbers or text. `PolicyAgent`
(bankai_core/agents/policy_agent.py) may only read from this store; it has
no ability to fabricate a rule. If no `FINAL`, currently-effective rule
matches, the caller gets `POLICY_CONFIRMATION_REQUIRED`, never a guess.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class RuleStatus(str, Enum):
    FINAL = "FINAL"
    DRAFT = "DRAFT"
    INTERNAL = "INTERNAL"
    SUPERSEDED = "SUPERSEDED"


@dataclass(frozen=True)
class RegulatoryRule:
    rule_id: str
    regulator: str
    regulation: str
    circular: str
    clause: str
    status: RuleStatus
    publication_date: date
    effective_from: date
    effective_until: date | None
    customer_type: str  # e.g. INDIVIDUAL | PARTNERSHIP | COMPANY | ALL
    account_type: str
    service: str
    document_requirement: list[str] = field(default_factory=list)
    authentication: str = "OTP"
    maker_required: bool = True
    checker_required: bool = True
    approval_authority: str = "BRANCH_MANAGER"
    permitted_channel: list[str] = field(default_factory=lambda: ["BRANCH"])
    cbs_action: str = ""
    sla_hours: int = 24
    retention_rule: str = "7_YEARS"
    notification_rule: str = "SMS_EMAIL_ON_COMPLETION"
    source_reference: str = ""
    supersedes: str | None = None


class RegulatoryTwinStore:
    def __init__(self) -> None:
        self._rules: dict[str, RegulatoryRule] = {}

    def add(self, rule: RegulatoryRule) -> None:
        self._rules[rule.rule_id] = rule

    def find(self, service: str, customer_type: str, as_of: date | None = None) -> RegulatoryRule | None:
        as_of = as_of or date.today()
        candidates = [
            r
            for r in self._rules.values()
            if r.status == RuleStatus.FINAL
            and r.service == service
            and r.customer_type in (customer_type, "ALL")
            and r.effective_from <= as_of
            and (r.effective_until is None or as_of < r.effective_until)
        ]
        if not candidates:
            return None
        # Prefer the most specific customer_type match, then most recent.
        candidates.sort(key=lambda r: (r.customer_type != "ALL", r.effective_from), reverse=True)
        return candidates[0]

    def all_rules(self) -> list[RegulatoryRule]:
        return list(self._rules.values())


regulatory_twin = RegulatoryTwinStore()
