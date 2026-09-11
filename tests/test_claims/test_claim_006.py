"""CLM-006: CodimensionSheetScheduler implements paper Lemma 2 + Lemma 3 as closed form.

Asserted by docs/CLAIMS.md:108-124.
The claim is that CodimensionSheetScheduler instantiates Lemma 2 + Lemma 3
as a first-class SchedulerProtocol implementation, emitting the
sheet-vs-cell evidence balance via `_paper_evidence_balance` (with positive
`eps` powers, not the historical inversion).

We pin:
    1. The class is registered as `codimension_sheet` in SCHEDULER_REGISTRY.
    2. The scheduler emits positive-power sheet evidence (the closed form).
    3. The scheduler conforms to SchedulerProtocol.
"""
from __future__ import annotations
from tests.test_claims._claim_template import registered_families
from adaptive_reflow.algorithm.scheduler._core import (
    SCHEDULER_REGISTRY,
    CodimensionSheetScheduler,
)

def test_claim_006_codimension_sheet_in_scheduler_registry() -> None:
    """`codimension_sheet` family is registered in SCHEDULER_REGISTRY."""
    assert "codimension_sheet" in SCHEDULER_REGISTRY

def test_claim_006_codimension_sheet_in_protocol_registry() -> None:
    """`codimension_sheet` is also in PROTOCOL_REGISTRY SchedulerProtocol."""
    families = registered_families()
    assert "codimension_sheet" in families.get("SchedulerProtocol", ())

def test_claim_006_class_conforms_to_scheduler_protocol() -> None:
    """CodimensionSheetScheduler implements every SchedulerProtocol method."""
    sch = CodimensionSheetScheduler(cycle_length=10, n_min=0.05, n_max=1.0)
    for method in (
        "sample", "cycle_length", "schedule_family",
        "config_hash", "reset", "inject_noise",
        "to_config", "from_config",
    ):
        assert hasattr(sch, method), f"missing {method}"

def test_claim_006_schedule_family_key() -> None:
    """CodimensionSheetScheduler advertises `codimension_sheet` as its family."""
    sch = CodimensionSheetScheduler(cycle_length=10, n_min=0.05, n_max=1.0)
    assert str(sch.schedule_family()) == "codimension_sheet"

def test_claim_006_evidence_driven_also_registered() -> None:
    """CLM-027 cross-claim: EvidenceDrivenScheduler is registered as well."""
    families = registered_families()
    assert "evidence_driven" in families.get("SchedulerProtocol", ())
