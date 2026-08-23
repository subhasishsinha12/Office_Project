"""In-process ServiceRequest store for the prototype.

The target schema is the Postgres DDL in `data/schema.sql`
(`SERVICE_REQUEST` table + related tables). This slice keeps state
in-process to keep the reviewable diff focused on the control-plane logic
(gateway, registries, rule engine, maker-checker, tool gateway); wiring
SQLAlchemy models to that DDL is a mechanical follow-up, not an
architectural change — nothing in `bankai_core` or `workflow` assumes an
in-memory store.
"""
from __future__ import annotations

import threading

from workflow.state_machine import ServiceRequest


class RequestStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests: dict[str, ServiceRequest] = {}

    def save(self, request: ServiceRequest) -> None:
        with self._lock:
            self._requests[request.request_id] = request

    def get(self, request_id: str) -> ServiceRequest | None:
        with self._lock:
            return self._requests.get(request_id)

    def all(self) -> list[ServiceRequest]:
        with self._lock:
            return list(self._requests.values())


request_store = RequestStore()
