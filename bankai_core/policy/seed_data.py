"""Synthetic policy seed data (§48). No real circular numbers or text.

Calling `load_seed_policies()` populates the process-wide `regulatory_twin`
singleton. Called once at application startup (see
`apps/branchone_api/main.py`).
"""
from __future__ import annotations

from datetime import date

from bankai_core.policy.regulatory_twin import RegulatoryRule, RuleStatus, regulatory_twin

_SEEDED = False


def load_seed_policies() -> None:
    global _SEEDED
    if _SEEDED:
        return

    regulatory_twin.add(
        RegulatoryRule(
            rule_id="POL-CM-CONTACT-MOBILE-001",
            regulator="INTERNAL",
            regulation="Bank Operational Instructions",
            circular="BOI/2025/CONTACT/014 (synthetic)",
            clause="4.2",
            status=RuleStatus.FINAL,
            publication_date=date(2025, 4, 1),
            effective_from=date(2025, 4, 15),
            effective_until=None,
            customer_type="ALL",
            account_type="ALL",
            service="CONTACT_DETAILS",
            document_requirement=["SELF_DECLARATION"],
            authentication="OTP",
            maker_required=True,
            checker_required=True,
            approval_authority="BRANCH_CHECKER",
            permitted_channel=["BRANCH", "MOBILE_APP"],
            cbs_action="UPDATE_MOBILE",
            sla_hours=4,
            source_reference="synthetic SOP for prototype",
        )
    )
    regulatory_twin.add(
        RegulatoryRule(
            rule_id="POL-CM-CONSTITUTION-PARTNER-001",
            regulator="INTERNAL",
            regulation="Bank Board Policy — Constitution Changes",
            circular="BOI/2024/CONST/007 (synthetic)",
            clause="6.1",
            status=RuleStatus.FINAL,
            publication_date=date(2024, 11, 1),
            effective_from=date(2024, 11, 15),
            effective_until=None,
            customer_type="PARTNERSHIP",
            account_type="CURRENT",
            service="CONSTITUTION",
            document_requirement=[
                "PARTNERSHIP_DEED",
                "PARTNER_PAN",
                "PARTNER_RESOLUTION",
                "REQUEST_LETTER",
            ],
            authentication="IN_PERSON",
            maker_required=True,
            checker_required=True,
            approval_authority="BRANCH_MANAGER",
            permitted_channel=["BRANCH"],
            cbs_action="UPDATE_CONSTITUTION",
            sla_hours=72,
            source_reference="synthetic board policy for prototype",
        )
    )
    regulatory_twin.add(
        RegulatoryRule(
            rule_id="POL-CM-MANDATE-SIGNATORY-001",
            regulator="INTERNAL",
            regulation="Bank Board Policy — Mandate Changes",
            circular="BOI/2024/MANDATE/009 (synthetic)",
            clause="3.4",
            status=RuleStatus.FINAL,
            publication_date=date(2024, 11, 1),
            effective_from=date(2024, 11, 15),
            effective_until=None,
            customer_type="PARTNERSHIP",
            account_type="CURRENT",
            service="MANDATE",
            document_requirement=["PARTNER_RESOLUTION", "SIGNATURE_CARD", "PAN"],
            authentication="IN_PERSON",
            maker_required=True,
            checker_required=True,
            approval_authority="BRANCH_MANAGER",
            permitted_channel=["BRANCH"],
            cbs_action="UPDATE_SIGNATORY",
            sla_hours=48,
            source_reference="synthetic board policy for prototype",
        )
    )
    regulatory_twin.add(
        RegulatoryRule(
            rule_id="POL-CQ-STOP-PAYMENT-001",
            regulator="INTERNAL",
            regulation="Bank Operational Instructions — Cheques",
            circular="BOI/2023/CHQ/002 (synthetic)",
            clause="2.1",
            status=RuleStatus.FINAL,
            publication_date=date(2023, 6, 1),
            effective_from=date(2023, 6, 15),
            effective_until=None,
            customer_type="ALL",
            account_type="ALL",
            service="CHEQUE_BOOK",
            document_requirement=["STOP_PAYMENT_REQUEST"],
            authentication="OTP",
            maker_required=True,
            checker_required=False,
            approval_authority="BRANCH_MAKER",
            permitted_channel=["BRANCH", "MOBILE_APP", "PHONE_BANKING"],
            cbs_action="STOP_CHEQUE",
            sla_hours=1,
            source_reference="synthetic SOP for prototype",
        )
    )
    # A DRAFT rule, present to prove drafts are never applied automatically
    # (§12: "Draft regulations must never be treated as binding automatically").
    regulatory_twin.add(
        RegulatoryRule(
            rule_id="POL-CM-CONTACT-MOBILE-002-DRAFT",
            regulator="INTERNAL",
            regulation="Proposed revision — Contact Details",
            circular="BOI/2026/CONTACT/031-DRAFT (synthetic)",
            clause="4.3",
            status=RuleStatus.DRAFT,
            publication_date=date(2026, 8, 1),
            effective_from=date(2026, 9, 1),
            effective_until=None,
            customer_type="ALL",
            account_type="ALL",
            service="CONTACT_DETAILS",
            document_requirement=["SELF_DECLARATION", "VIDEO_KYC"],
            maker_required=True,
            checker_required=True,
            cbs_action="UPDATE_MOBILE",
            source_reference="synthetic draft — not yet FINAL",
        )
    )

    _SEEDED = True
