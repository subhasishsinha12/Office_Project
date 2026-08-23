"""Prompt/response audit trail (§39 of the BankAI Core brief).

Stores hashes rather than raw content by default, since prompts/responses
may carry customer PII even after masking. Raw content is retained only when
`retain_raw=True` is explicitly passed (e.g. a flagged/incident run under a
retention policy), matching "Do not necessarily store raw sensitive content
if policy prohibits it."
"""
from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PromptAuditRecord:
    prompt_id: int
    model: str
    model_version: str
    agent: str
    input_hash: str
    policy_context: Optional[str]
    tool_context: Optional[str]
    response_hash: str
    decision: str
    user: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    raw_input: Optional[str] = None
    raw_response: Optional[str] = None


class PromptAudit:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: list[PromptAuditRecord] = []
        self._next_id = 1

    def record(
        self,
        model: str,
        model_version: str,
        agent: str,
        input_text: str,
        response_text: str,
        decision: str,
        user: str,
        policy_context: Optional[str] = None,
        tool_context: Optional[str] = None,
        retain_raw: bool = False,
    ) -> PromptAuditRecord:
        rec = PromptAuditRecord(
            prompt_id=self._next_id,
            model=model,
            model_version=model_version,
            agent=agent,
            input_hash=_hash(input_text),
            policy_context=policy_context,
            tool_context=tool_context,
            response_hash=_hash(response_text),
            decision=decision,
            user=user,
            raw_input=input_text if retain_raw else None,
            raw_response=response_text if retain_raw else None,
        )
        with self._lock:
            self._next_id += 1
            self._records.append(rec)
        return rec

    def all_records(self) -> list[PromptAuditRecord]:
        with self._lock:
            return list(self._records)


prompt_audit = PromptAudit()
