"""Model Registry (§37).

Records governance metadata for every model the bank has approved, and is
the only place a `ModelProvider` instance is looked up from. Adding a real
model means adding one `ModelRegistryEntry` here with `approval_status`
already reviewed — the router never talks to a provider that isn't
registered and approved.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from bankai_core.models.base import ModelProvider, ModelTier
from bankai_core.models.providers import LargeModelProvider, RuleBasedProvider, SmallModelProvider


@dataclass
class ModelRegistryEntry:
    model_id: str
    model_name: str
    provider: ModelProvider
    tier: ModelTier
    provider_org: str  # "bank-hosted" | "approved-vendor" | "hybrid"
    owner: str
    risk_class: str  # LOW | MEDIUM | HIGH
    hosting_mode: str  # Mode A / B / C per §5.3
    data_classes_allowed: list[str] = field(default_factory=list)
    validation_status: str = "VALIDATED"
    approval_status: str = "APPROVED"
    last_review: date = field(default_factory=date.today)
    retirement_status: str = "ACTIVE"


class ModelRegistry:
    def __init__(self) -> None:
        self._entries: dict[str, ModelRegistryEntry] = {}

    def register(self, entry: ModelRegistryEntry) -> None:
        self._entries[entry.model_id] = entry

    def get(self, model_id: str) -> ModelRegistryEntry:
        try:
            return self._entries[model_id]
        except KeyError as exc:
            raise ModelNotRegistered(model_id) from exc

    def by_tier(self, tier: ModelTier) -> list[ModelRegistryEntry]:
        return [e for e in self._entries.values() if e.tier == tier and e.approval_status == "APPROVED" and e.retirement_status == "ACTIVE"]

    def all_entries(self) -> list[ModelRegistryEntry]:
        return list(self._entries.values())


class ModelNotRegistered(RuntimeError):
    pass


model_registry = ModelRegistry()
model_registry.register(
    ModelRegistryEntry(
        model_id="bankai-tier1-rules",
        model_name="BankAI Deterministic Classifier",
        provider=RuleBasedProvider(),
        tier=ModelTier.TIER_1_DETERMINISTIC,
        provider_org="bank-hosted",
        owner="MLOps",
        risk_class="LOW",
        hosting_mode="Mode A",
        data_classes_allowed=["MASKED_PII", "INTERNAL"],
    )
)
model_registry.register(
    ModelRegistryEntry(
        model_id="bankai-tier2-slm-mock",
        model_name="BankAI Small Language Model (mock)",
        provider=SmallModelProvider(),
        tier=ModelTier.TIER_2_SLM,
        provider_org="bank-hosted",
        owner="GenAI Engineering",
        risk_class="MEDIUM",
        hosting_mode="Mode A",
        data_classes_allowed=["MASKED_PII", "INTERNAL"],
    )
)
model_registry.register(
    ModelRegistryEntry(
        model_id="bankai-tier3-llm-mock",
        model_name="BankAI Large Language Model (mock)",
        provider=LargeModelProvider(),
        tier=ModelTier.TIER_3_LLM,
        provider_org="hybrid",
        owner="GenAI Engineering",
        risk_class="HIGH",
        hosting_mode="Mode C",
        data_classes_allowed=["MASKED_PII", "INTERNAL"],
    )
)
