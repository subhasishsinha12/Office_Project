"""Model provider abstraction (§5.3).

A `ModelProvider` is the only thing that knows how to talk to an actual
model (bank-hosted open-weight LLM, an approved commercial API, or — as
in this prototype — a deterministic mock standing in for Tier 1/2/3
behaviour). Swapping a real model in means writing one new subclass and
registering it in `bankai_core/models/registry.py`; nothing in
`bankai_core/agents/*` or `apps/branchone_api/*` changes.

The mock providers here are intentionally simple/deterministic: they exist
to prove the *routing and control* architecture (which tier handles which
task, and that agents never call a provider directly), not to demonstrate
model quality. A real deployment replaces `SmallModelProvider`/
`LargeModelProvider` with actual SLM/LLM calls behind the same interface.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ModelTier(str, Enum):
    TIER_1_DETERMINISTIC = "TIER_1_DETERMINISTIC"
    TIER_2_SLM = "TIER_2_SLM"
    TIER_3_LLM = "TIER_3_LLM"


@dataclass(frozen=True)
class PromptPayload:
    """Structural separation of trusted instructions from untrusted data.

    `instructions` is fixed, developer-authored text for the task type.
    `data` holds untrusted customer/document content as named fields, never
    concatenated into `instructions`. This is what makes prompt injection
    structurally inert regardless of what `data` contains (see
    `bankai_core/guardrails/injection_defense.py`).
    """

    task_type: str
    instructions: str
    data: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelResponse:
    text: str
    structured: dict[str, Any]
    confidence: float
    model_id: str
    model_version: str


class ModelProvider:
    tier: ModelTier
    model_id: str
    model_version: str = "0.1.0"

    def generate(self, payload: PromptPayload) -> ModelResponse:  # pragma: no cover - interface
        raise NotImplementedError
