"""Workflow Compiler (§18).

Turns intent + policy + rule-engine output into an ordered, human-readable
list of workflow steps for the UI/API — a projection of
`workflow.state_machine.WorkflowState`, not a second source of truth. It is
deliberately deterministic (built from `RuleOutcome`/`RegulatoryRule`
fields only) rather than model-generated, because a hallucinated workflow
step list is a compliance risk the brief explicitly calls out (§14).
"""
from __future__ import annotations

from dataclasses import dataclass

from bankai_core.policy.regulatory_twin import RegulatoryRule
from bankai_core.policy.rule_engine import RuleOutcome
from workflow.state_machine import WorkflowState


@dataclass(frozen=True)
class CompiledStep:
    name: str
    state: WorkflowState
    required: bool


def compile_workflow(rule_outcome: RuleOutcome, regulatory_rule: RegulatoryRule | None) -> list[CompiledStep]:
    documents_required = bool(regulatory_rule and regulatory_rule.document_requirement)
    steps = [
        CompiledStep("Authenticate", WorkflowState.AUTHENTICATION_PENDING, True),
        CompiledStep("Collect Documents", WorkflowState.DOCUMENT_PENDING, documents_required),
        CompiledStep("Document Validation", WorkflowState.DOCUMENT_VERIFICATION, documents_required),
        CompiledStep("Policy Validation", WorkflowState.POLICY_VALIDATION, True),
        CompiledStep("Risk Review", WorkflowState.RISK_REVIEW, True),
        CompiledStep("Maker Review", WorkflowState.MAKER_PENDING, rule_outcome.maker_required),
        CompiledStep("Checker Approval", WorkflowState.CHECKER_PENDING, rule_outcome.checker_required),
        CompiledStep("CBS Update", WorkflowState.CBS_PENDING, True),
        CompiledStep("Post-Execution Verification", WorkflowState.POST_VERIFICATION, True),
        CompiledStep("Close", WorkflowState.COMPLETED, True),
    ]
    return [s for s in steps if s.required]
