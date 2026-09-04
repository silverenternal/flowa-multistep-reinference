"""CLM-029: FreeTrajScheduler (arXiv:2507.10532) registered as a plug-in scheduler family.

Asserted by docs/CLAIMS.md:686-715.
The class `FreeTrajScheduler` is registered under the key `"freetraj"` in
the scheduler registry.

We pin:
    1. The class is importable.
    2. The PROTOCOL_REGISTRY exposes the family key `freetraj`.
    3. The scheduler's `schedule_family()` returns `freetraj`.
"""
from __future__ import annotations

from adaptive_reflow.algorithm.protocol_registry import registered_families
from adaptive_reflow.algorithm.scheduler._core import default_cosine_scheduler
from adaptive_reflow.algorithm.scheduler.freetraj import FreeTrajScheduler


def test_claim_029_freetraj_class_importable() -> None:
    assert FreeTrajScheduler is not None


def test_claim_029_freetraj_in_protocol_registry() -> None:
    families = registered_families()
    assert "freetraj" in families.get("SchedulerProtocol", ())


def test_claim_029_freetraj_schedule_family_key() -> None:
    """FreeTrajScheduler advertises `freetraj` as its schedule_family."""
    cfg = default_cosine_scheduler(cycle_length=10, n_min=0.05, n_max=1.0).config
    sch = FreeTrajScheduler(cfg)
    assert str(sch.schedule_family()) == "freetraj"


def test_claim_029_freetraj_conforms_to_protocol() -> None:
    for method in (
        "sample", "cycle_length", "schedule_family",
        "config_hash", "reset", "inject_noise",
        "to_config", "from_config",
    ):
        assert hasattr(FreeTrajScheduler, method), f"missing {method}"
