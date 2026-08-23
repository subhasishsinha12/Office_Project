"""Immutable audit event log.

Every workflow state transition, tool call, and AI run must append an event
here. Nothing reads this module's store and rewrites past entries — append
only. In the prototype this is an in-memory list guarded by a lock; the
production equivalent is the AUDIT_EVENT table (see data/schema.sql), and
`AuditLog` here is written so swapping the backing store does not change
any caller.
"""
from __future__ import annotations

import itertools
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass(frozen=True)
class AuditEvent:
    event_id: int
    event_type: str  # e.g. WORKFLOW_TRANSITION, TOOL_CALL, AI_RUN, MAKER_CHECKER_DECISION
    actor: str  # employee_id, customer_id, or agent_id
    actor_type: str  # EMPLOYEE | CUSTOMER | AGENT | SYSTEM
    subject_id: Optional[str]  # e.g. service_request_id
    action: str
    decision: Optional[str] = None
    previous_value: Optional[str] = None
    requested_value: Optional[str] = None
    reason: Optional[str] = None
    evidence: Optional[dict] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AuditLog:
    """Append-only audit event store."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: list[AuditEvent] = []
        self._counter = itertools.count(1)

    def record(
        self,
        event_type: str,
        actor: str,
        actor_type: str,
        action: str,
        subject_id: Optional[str] = None,
        decision: Optional[str] = None,
        previous_value: Optional[str] = None,
        requested_value: Optional[str] = None,
        reason: Optional[str] = None,
        evidence: Optional[dict[str, Any]] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            event_id=next(self._counter),
            event_type=event_type,
            actor=actor,
            actor_type=actor_type,
            subject_id=subject_id,
            action=action,
            decision=decision,
            previous_value=previous_value,
            requested_value=requested_value,
            reason=reason,
            evidence=evidence,
        )
        with self._lock:
            self._events.append(event)
        return event

    def for_subject(self, subject_id: str) -> list[AuditEvent]:
        with self._lock:
            return [e for e in self._events if e.subject_id == subject_id]

    def all_events(self) -> list[AuditEvent]:
        with self._lock:
            return list(self._events)


# Process-wide singleton. Applications inject this rather than constructing
# their own, so a single request's audit trail is never split across stores.
audit_log = AuditLog()
