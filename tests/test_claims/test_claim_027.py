"""CLM-027: EvidenceDrivenScheduler closes Loop 2 (paper quantities -> scheduler feedback).

Asserted by docs/CLAIMS.md:616-648.
EvidenceDrivenScheduler is registered as the plug-in scheduler family
`"evidence_driven"`. It subscribes to the runner's per-round metric dict
via `record_round_feedback` and updates `n_cap` via a PID-lite controller.

We pin:
    1. The class is importable from `adaptive_reflow.algorithm.scheduler.evidence_driven`.
    2. The PROTOCOL_REGISTRY exposes the family key `evidence_driven`.
    3. The class has a `record_round_feedback` hook (per SchedulerProtocol).
"""
from __future__ import annotations

from adaptive_reflow.algorithm.scheduler.evidence_driven import (
    EvidenceDrivenScheduler,
)
from tests.test_claims._claim_template import default_cosine_scheduler, registered_families


def _default_cfg(cycle_length: int):
    return default_cosine_scheduler(
        cycle_length=cycle_length, n_min=0.05, n_max=1.0,
    ).config

def test_claim_027_evidence_driven_class_importable() -> None:
    assert EvidenceDrivenScheduler is not None

def test_claim_027_evidence_driven_in_protocol_registry() -> None:
    families = registered_families()
    assert "evidence_driven" in families.get("SchedulerProtocol", ())

def test_claim_027_evidence_driven_has_feedback_hook() -> None:
    """record_round_feedback is the canonical feedback hook for Loop 2."""
    cfg = _default_cfg(cycle_length=10)
    sch = EvidenceDrivenScheduler(cfg)
    assert hasattr(sch, "record_round_feedback")

def test_claim_027_evidence_driven_conforms_to_protocol() -> None:
    """Every SchedulerProtocol method is present on the class."""
    for method in (
        "sample", "cycle_length", "schedule_family",
        "config_hash", "reset", "inject_noise",
        "to_config", "from_config",
    ):
        assert hasattr(EvidenceDrivenScheduler, method), f"missing {method}"
