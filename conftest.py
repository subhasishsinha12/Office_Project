import pytest

from bankai_core.agents.bootstrap import register_all_agents
from bankai_core.policy.seed_data import load_seed_policies


@pytest.fixture(autouse=True, scope="session")
def _bootstrap_bankai_core():
    register_all_agents()
    load_seed_policies()
