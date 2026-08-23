"""Model Router (§5.2) — picks the smallest suitable model for a task.

Routing is driven by a `TaskSpec`, never by an application hardcoding a
model name. This is what lets the platform swap models by editing the
registry instead of every call site.
"""
from __future__ import annotations

from dataclasses import dataclass

from bankai_core.guardrails.kill_switch import kill_switch
from bankai_core.models.base import ModelProvider, ModelTier, PromptPayload
from bankai_core.models.registry import ModelRegistry, ModelRegistryEntry, model_registry

# task_type -> minimum tier capable of handling it
_TASK_MIN_TIER: dict[str, ModelTier] = {
    "intent_classification": ModelTier.TIER_1_DETERMINISTIC,
    "risk_scoring": ModelTier.TIER_1_DETERMINISTIC,
    "document_field_extraction": ModelTier.TIER_2_SLM,
    "summarize": ModelTier.TIER_2_SLM,
    "decompose_request": ModelTier.TIER_3_LLM,
}


@dataclass(frozen=True)
class TaskSpec:
    task_type: str
    data_sensitivity: str = "INTERNAL"  # PUBLIC | INTERNAL | CONFIDENTIAL | RESTRICTED
    latency_requirement_ms: int = 2000
    regulatory_classification: str = "STANDARD"
    confidence_threshold: float = 0.6


class ModelRouter:
    def __init__(self, registry: ModelRegistry) -> None:
        self._registry = registry

    def resolve(self, spec: TaskSpec) -> ModelRegistryEntry:
        tier = _TASK_MIN_TIER.get(spec.task_type)
        if tier is None:
            raise UnroutableTask(spec.task_type)

        candidates = self._registry.by_tier(tier)
        for candidate in candidates:
            try:
                kill_switch.check_model(candidate.model_id)
            except Exception:
                continue
            return candidate
        raise NoModelAvailable(spec.task_type, tier)

    def invoke(self, spec: TaskSpec, payload: PromptPayload):
        entry = self.resolve(spec)
        response = entry.provider.generate(payload)
        return entry, response


class UnroutableTask(RuntimeError):
    pass


class NoModelAvailable(RuntimeError):
    def __init__(self, task_type: str, tier: ModelTier) -> None:
        super().__init__(f"no approved, enabled model available for task_type={task_type!r} tier={tier}")


model_router = ModelRouter(model_registry)
