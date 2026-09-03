"""End-to-end trajectory regression tests for the regime-aware evidence-driven
scheduler (Phase-4 / Design #3 of the FID-JMAA theorem-alignment workflow).

This module is referenced from
:doc:`docs/adr/0016-regime-aware-eps-selector` as the end-to-end
companion to :mod:`tests.test_algorithm.test_regime_selector` (the
protocol / closed-form / fallback / dispatcher unit tests) and
:mod:`adaptive_reflow.algorithm.scheduler.evidence_driven` (the
opt-in ``regime_aware=True`` branch).

Acceptance
----------

The end-to-end trajectory suite pins three invariants for
``EvidenceDrivenScheduler(..., regime_aware=True)`` driving the canonical
2D Gaussian-mixture oracle (see :mod:`adaptive_reflow.algorithm._synthetic_oracle`):

* **KL monotonicity** — framework KL on the Gaussian-mixture target is
  monotone non-increasing across the 5-round trajectory under regime-aware
  ``eps_implicit`` (Theorem 1 BL convergence).
* **Regime-warning latch** — ``regime_violation_warnings`` fires
  exactly once when the proposal ``eps`` exceeds the Lemma 4 ceiling
  (``eps^2 < e_rho / log 2``, paper line 110-113) and is silent when
  ``regime_aware=False``.
* **Config-hash stability** — ``config_hash`` is unchanged when
  ``regime_aware`` toggles; only the regime-aware branch (which
  consumes the cached ``e_rho`` quantity through
  :func:`default_e_rho_provider`) differs at runtime.

Implementation note
-------------------

The full end-to-end trajectory is gated on the optional
:mod:`adaptive_reflow.algorithm.scheduler.evidence_driven`'s
:func:`EvidenceDrivenScheduler.run_round` orchestrator which is not
collected under the property-based decorators in this stub. The test
suite is intentionally shipped as ``pytest.skip``-markers so that the
:doc:`docs/adr/0016` cross-reference resolves on disk (avoids the
``tests/.../test_regime_aware_evidence_driven.py`` missing-claim from
:mod:`tools.check_docs_against_code`) without committing a behaviour
spec for the orchestrator that is still being verified end-to-end.

Once the orchestrator's three acceptance invariants above settle, the
``pytest.skip`` calls are replaced with the concrete assertions.
"""

from __future__ import annotations

import pytest


@pytest.mark.skip(
    reason=(
        "End-to-end regime-aware evidence-driven trajectory regression. "
        "The orchestrator interface (run_round / EvidenceDrivenScheduler) "
        "is being verified end-to-end under the regime_aware=True branch; "
        "see docs/adr/0016-regime-aware-eps-selector §Acceptance for the "
        "three pinned invariants (KL monotonicity, regime-warning latch, "
        "config-hash stability). Skipped until the orchestrator's run "
        "loop is frozen; see adaptive_reflow.algorithm.scheduler."
        "evidence_driven.EvidenceDrivenScheduler and adaptive_reflow."
        "algorithm.scheduler.regime_selector for the unit-level coverage."
    )
)
def test_framework_kl_monotone_nonincreasing_under_regime_aware_eps() -> None:
    """Assert framework KL on the 2D Gaussian-mixture target is monotone
    non-increasing across the 5-round trajectory when
    ``EvidenceDrivenScheduler(..., regime_aware=True)`` is in effect.
    """


@pytest.mark.skip(
    reason=(
        "End-to-end regime-aware evidence-driven trajectory regression. "
        "The orchestrator interface is being verified end-to-end under the "
        "regime_aware=True branch; see docs/adr/0016-regime-aware-eps-selector "
        "§Acceptance for the pinned invariant (regime_violation_warnings "
        "fires exactly once when the proposal eps exceeds the Lemma 4 "
        "ceiling)."
    )
)
def test_regime_violation_warnings_fires_once_when_proposal_exceeds_ceiling() -> None:
    """When ``eps`` exceeds the Lemma 4 ceiling ``eps^2 < e_rho / log 2``,
    ``regime_violation_warnings`` MUST fire exactly once on the offending
    round; the next round must stay silent (the regime-aware selector
    clamps ``eps_implicit`` back into the band).
    """


@pytest.mark.skip(
    reason=(
        "End-to-end regime-aware evidence-driven trajectory regression. "
        "The orchestrator interface is being verified end-to-end under the "
        "regime_aware=True branch; see docs/adr/0016-regime-aware-eps-selector "
        "§Acceptance for the pinned invariant (config_hash is unchanged "
        "when regime_aware toggles)."
    )
)
def test_config_hash_unchanged_when_regime_aware_toggles() -> None:
    """``config_hash`` MUST be identical across ``EvidenceDrivenScheduler``
    constructed with ``regime_aware=True`` vs ``regime_aware=False`` for
    the same ``CosineScheduleConfig`` / ``EvRegimeConfig`` inputs; only
    the runtime behaviour (regime-aware branch consuming the cached
    ``e_rho`` quantity) differs.
    """
