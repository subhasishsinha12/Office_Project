"""Complex Request Decomposition Agent (§10) — advisory only.

Proposes a parent/child request graph for compound requests such as
"one partner retired, add the new partner as signatory and change our
firm's mobile number." The proposal is never binding: the deterministic
rule engine and workflow compiler independently validate every child
request's requirements before any workflow is created.
"""
from __future__ import annotations

from dataclasses import dataclass

from bankai_core.agents.base import AdvisoryAgent


@dataclass(frozen=True)
class ChildRequestProposal:
    fragment: str
    intent_code: str
    domain: str
    service: str
    subservice: str


class DecompositionAgent(AdvisoryAgent):
    agent_id = "DECOMPOSITION_AGENT"

    def decompose(self, text: str, caller_role: str, caller_id: str) -> list[ChildRequestProposal]:
        result = self._invoke(
            caller_role=caller_role,
            caller_id=caller_id,
            task_type="decompose_request",
            instructions="Decompose the compound banking service request into independent child requests.",
            data={"text": text},
        )
        children = result.response.structured.get("children", [])
        return [
            ChildRequestProposal(
                fragment=c["fragment"],
                intent_code=c["intent_code"],
                domain=c["domain"],
                service=c["service"],
                subservice=c["subservice"],
            )
            for c in children
        ]


decomposition_agent = DecompositionAgent()
