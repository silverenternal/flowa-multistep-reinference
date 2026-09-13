"""Hand-written tests for :class:`FlowMol3Adapter` (Wave 15 C — D.3).

This is the placeholder :class:`FlowMol3Adapter` (DTB-G2) — it does
NOT import or call FlowMol3 source code; it produces deterministic
hash-stable placeholder state suitable for the public engine + adapter
protocol surface (DTB-G1). The tests here exercise the surface end-to-end
so the Wave 11 + Wave 14 refactors of the universal layer stay
backwards-compatible with the FlowMol3 hand-off point.

Note: this file is distinct from ``test_flowmol3_v2_adapter.py``
which tests the **v2** adapter wired into the per-channel materializer
(:class:`FlowMol3V2Adapter`). The v1 / v2 split is the Wave 9
registry separation; the two adapters share the registry family key
``flowmol3`` / ``flowmol3_v2`` but expose different capabilities and
materializer wiring.

Tests in this file (Wave 15 C — D.3 ≥ 10 tests):

* Capabilities handshake (5)
* Lifecycle (3)
* Failure-closed paths (2)
* Byte-stability (1)
* Forward-noise injection (1)
* Channel vocabulary (1)

Total: **13 tests** (Wave 15 C D.3 floor: 10). Later waves appended
their own classes below (Wave 49 Agent F, Wave 50 Agent A, Wave 58), so
the live count is higher than the Wave 15 baseline recorded here.
"""
from __future__ import annotations

import os

import pytest

from adaptive_reflow.adapters import (
    AUDIT_FLOWMOL3_ATOM_TYPE_ENTROPY_RESTART,
    FLOWMOL3_ATOM_TYPE_VOCAB_SIZE,
    FLOWMOL3_CHANNEL_DOMAINS,
    FLOWMOL3_CHANNELS,
    PER_POSITION_ENTROPY_REDUCTION,
    FlowMol3Adapter,
    FlowMol3AtomTypeEntropyRestartPolicy,
    FlowMol3Capabilities,
    default_flowmol3_adapter,
    flowmol3_registry_entry,
)
from adaptive_reflow.adapters.flowmol3 import (
    AUDIT_FLOWMOL3_RESTART_SKIPPED_LOW_NFE,
    FLOWMOL3_REAL_CKPT_LOADED_MARKER,
    FLOWMOL3_REAL_CKPT_PATH,
    FLOWMOL3_RESTART_MIN_NFE,
    _try_load_real_ckpt,
)
from adaptive_reflow.frame.adapter import (
    AdapterCapabilities,
    CapabilityMissingError,
    ODEIntegratorTrace,
    StateBundle,
)
from adaptive_reflow.universal import FlowMatchingODEAdapter
from adaptive_reflow.universal.state import (
    ChannelName,
    ODEConditionDelta,
    validate_state_bundle,
)
from adaptive_reflow.writer.registry import FLOWMOL3_PINNED_COMMIT

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

#: Sentinel distinguishing "argument omitted" from "argument is None"
#: in the Wave 58 gate helpers below (``None`` is itself one of the
#: values under test).
_UNSET: object = object()


@pytest.fixture
def adapter() -> FlowMol3Adapter:
    return default_flowmol3_adapter()


# ---------------------------------------------------------------------------
# Capabilities handshake
# ---------------------------------------------------------------------------


class TestFlowMol3EntropyMetric:
    """Per-atom-type entropy reduction metric (Wave 49 Agent F).

    Mirrors :meth:`LineageFlowAdapter.observe_entropy_reduction` (Wave
    45 Agent E). Returns the per-atom Shannon entropy reduction from a
    baseline atom-type distribution to a framework endpoint.
    """

    def test_observe_entropy_reduction_default_returns_zero(
        self, adapter
    ) -> None:
        """Synthetic-mode fallback returns ``0.0`` (uniform-vs-uniform)."""
        import numpy as np

        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        cond = ODEConditionDelta(
            delta_spec={"num_steps": 1},
            source="test_flowmol3",
            target_round=1,
            calibration_artifact_hash="a" * 64,
        )
        trace = adapter.solve_ode(bundle, cond, seed=0)
        result = adapter.observe_entropy_reduction(trace)
        assert PER_POSITION_ENTROPY_REDUCTION in result
        # Synthetic uniform-vs-uniform → entropy reduction = 0.
        assert result[PER_POSITION_ENTROPY_REDUCTION] == 0.0

    def test_observe_entropy_reduction_explicit_arrays(
        self, adapter
    ) -> None:
        """Explicit ``theta_before`` and ``theta_after`` produce a real number."""
        import numpy as np

        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        cond = ODEConditionDelta(
            delta_spec={"num_steps": 1},
            source="test_flowmol3",
            target_round=1,
            calibration_artifact_hash="a" * 64,
        )
        trace = adapter.solve_ode(bundle, cond, seed=0)
        # Sharpened (low-entropy) after-vs-uniform before → positive reduction.
        theta_after = np.zeros(
            (8, int(FLOWMOL3_ATOM_TYPE_VOCAB_SIZE)), dtype=np.float64,
        )
        theta_after[:, 0] = 100.0  # confident spike
        theta_before = np.full_like(theta_after, 1.0)  # uniform
        result = adapter.observe_entropy_reduction(
            trace, theta_before=theta_before, theta_after=theta_after,
        )
        assert result[PER_POSITION_ENTROPY_REDUCTION] > 0.0

    def test_observe_entropy_reduction_widening_is_negative(
        self, adapter
    ) -> None:
        """Going from sharp to uniform should yield a negative reduction."""
        import numpy as np

        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        cond = ODEConditionDelta(
            delta_spec={"num_steps": 1},
            source="test_flowmol3",
            target_round=1,
            calibration_artifact_hash="a" * 64,
        )
        trace = adapter.solve_ode(bundle, cond, seed=0)
        # Sharpened before, uniform after.
        theta_before = np.zeros(
            (8, int(FLOWMOL3_ATOM_TYPE_VOCAB_SIZE)), dtype=np.float64,
        )
        theta_before[:, 0] = 100.0
        theta_after = np.full_like(theta_before, 1.0)
        result = adapter.observe_entropy_reduction(
            trace, theta_before=theta_before, theta_after=theta_after,
        )
        assert result[PER_POSITION_ENTROPY_REDUCTION] < 0.0

    def test_observe_entropy_reduction_byte_stable(
        self, adapter
    ) -> None:
        """Two calls with the same trace return identical results."""
        import numpy as np

        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        cond = ODEConditionDelta(
            delta_spec={"num_steps": 1},
            source="test_flowmol3",
            target_round=1,
            calibration_artifact_hash="a" * 64,
        )
        trace = adapter.solve_ode(bundle, cond, seed=42)
        r1 = adapter.observe_entropy_reduction(trace)
        r2 = adapter.observe_entropy_reduction(trace)
        assert r1 == r2


class TestFlowMol3BugCMetricSeedIsCellKey:
    """Regression suite for Wave 65 Agent 2's Bug C fix.

    Bug C (root cause: ``docs/audit/wave65-bug-c-root-cause.md`` §5):
    :func:`tools.run_real_ckpt_eval._compute_flowmol3_real_atom_type_marginal`
    at ``tools/run_real_ckpt_eval.py:1921-1930`` (pre-fix: 1921-1928)
    derived the random initial state's seed from a SHA-256 hash of
    ``trace.native_state_digest``. Because the v1 placeholder's
    ``solve_ode`` returns a trace whose ``native_state_digest`` is a
    hash of ``(state.native_state_digest, seed, steps)``, and because
    the framework's restart-blend corrupts ``cur_bundle.native_state_digest``,
    the framework and baseline arms fed DIFFERENT random initial states
    into the real FlowMol3 ckpt. The framework's "improvement" or
    "regression" was therefore a Monte Carlo noise artifact on a
    different random input, not a real signal of framework value-add.

    The Wave 65 Agent 2 fix replaces the hash-based extraction with the
    per-cell ``(seed, nfe)`` key. The regression test below verifies
    that two calls with the SAME ``(seed, nfe)`` but DIFFERENT
    ``trace.native_state_digest`` values now produce the SAME captured
    random-seed integer — which is the load-bearing property that
    proves the metric no longer sees the framework's restart-blended
    digest.
    """

    def _run_and_capture_seed(
        self,
        *,
        seed: int,
        nfe: int,
        digest_value: str,
    ) -> int:
        """Call the metric helper with heavy machinery stubbed out and
        return the seed argument passed into ``np.random.default_rng``.

        Stubs out the v2 adapter import + model forward so we don't
        need the real FlowMol3 ckpt or torch; intercepts
        ``np.random.default_rng`` to capture the integer seed that the
        helper computes for the random initial state.

        Wave 122: the helper (``tools.eval.metrics._compute_flowmol3_real_atom_type_marginal``)
        uses a lazy ``import numpy as np`` inside the function body
        (post Wave 97.B — the eval subpackage no longer re-exports
        ``np`` at module level). We therefore patch
        ``numpy.random.default_rng`` directly instead of the stale
        ``tools.run_real_ckpt_eval.np`` attribute (which no longer
        exists). We also stub ``torch`` via :mod:`sys.modules` so the
        helper's ``import torch`` (which otherwise returns ``None``
        with ``debug['theta_after_source']='torch_unavailable:...'``)
        succeeds; the downstream model build + forward is fully mocked.

        The torch stub is removed in a ``finally`` block to prevent
        cross-test pollution — a leaked empty stub would mask
        downstream ``pytest.importorskip('torch')`` checks (e.g. the
        :class:`TestFlowMol3V2SeedThreading` tests in
        :mod:`test_flowmol3_v2_adapter_conformance`) and cause
        ``AttributeError: module 'torch' has no attribute 'manual_seed'``
        in subsequent tests.
        """
        import sys
        from types import ModuleType, SimpleNamespace
        from unittest.mock import patch

        # Stub torch if real torch is unavailable (CI / Wave 122 env).
        _stub_installed = False
        if "torch" not in sys.modules:
            try:
                import torch  # noqa: F401
            except ImportError:
                sys.modules["torch"] = ModuleType("torch")
                _stub_installed = True

        try:
            import tools.run_real_ckpt_eval as _rce

            # Build a stub adapter with a populated _real_ckpt_meta so the
            # helper proceeds past the early `real_ckpt_meta is None` check.
            stub_adapter = SimpleNamespace(
                _real_ckpt_meta={"path": "/dev/null/flowmol3_stub.ckpt"},
            )
            stub_trace = SimpleNamespace(native_state_digest=digest_value)

            # Stub the lazy v2 import + the model build/forward. We only
            # need to control `default_rng`; the rest of the body runs
            # but is mocked into returning a sane per-atom softmax.
            class _StubModule:
                pass

            captured: dict[str, int] = {}

            class _CapturingRNG:
                def __init__(self, seed_arg: int) -> None:
                    captured["seed"] = int(seed_arg)

                def standard_normal(self, shape):
                    import numpy as _np
                    return _np.zeros(shape, dtype=_np.float32)

                def integers(self, low, high=None, size=None):
                    import numpy as _np
                    if high is None:
                        low, high = 0, low
                    return _np.zeros(size, dtype=_np.int64)

                def random(self) -> float:
                    return 0.0

            fake_module = _StubModule()
            # The lazy import returns (build, ctvf, load, K_atom, K_bond).
            # We don't need build/ctvf/load to actually run because we
            # intercept default_rng BEFORE those are called.
            def _fake_ctvf(*args, **kwargs):
                import numpy as _np
                # (vx, c_pred, p_a, p_c, p_e, vx_dup) — uniform softmax.
                n_atoms = 8
                K_atom = 10
                p_a = _np.full(
                    (n_atoms, K_atom), 1.0 / K_atom, dtype=_np.float64,
                )
                return (
                    _np.zeros((n_atoms, 3), dtype=_np.float32),
                    _np.zeros(n_atoms, dtype=_np.float64),
                    p_a, None, None,
                    _np.zeros((n_atoms, 3), dtype=_np.float32),
                )

            fake_module._build_flowmol3_velocity_module = (
                lambda *a, **kw: _StubModule()
            )
            fake_module._ctmc_real_velocity_field_ex = _fake_ctvf
            fake_module._load_flowmol3_state_dict = (
                lambda *a, **kw: {"state_dict": {}, "n_tensors": 0}
            )
            fake_module.FLOWMOL3ADAPTER_N_ATOM_TYPES = 10
            fake_module.FLOWMOL3ADAPTER_N_BOND_TYPES = 5

            # Patch BOTH the helper's local lazy import AND the np.random
            # entry point. We don't patch torch because the helper catches
            # the ImportError and returns (None, debug) BEFORE the import
            # in the patched function — but we need torch to be importable
            # OR we mock the lazy import entirely. We mock the lazy import.
            #
            # Wave 122: the helper does ``import numpy as np`` inside the
            # function (lazy import, post Wave 97.B). Patch
            # ``numpy.random.default_rng`` directly so the captured seed
            # is the one the helper passes in, regardless of which module
            # attribute the import binds to.
            with patch(
                "numpy.random.default_rng",
                side_effect=lambda s: _CapturingRNG(s),
            ), patch.object(
                _rce, "_ctmc_real_velocity_field_ex",
                _fake_ctvf,
                create=True,
            ):
                # Patch the lazy import of v2 helpers by giving the module
                # a stub attribute. The helper does
                # `from adaptive_reflow.adapters.flowmol3_v2_adapter import (...)`
                # inside a try/except, so we must patch the *target* import
                # system. Easier: patch the four names on the target module.
                import adaptive_reflow.adapters.flowmol3_v2_adapter as _v2
                with patch.multiple(
                    _v2,
                    _build_flowmol3_velocity_module=(
                        fake_module._build_flowmol3_velocity_module
                    ),
                    _ctmc_real_velocity_field_ex=_fake_ctvf,
                    _load_flowmol3_state_dict=(
                        fake_module._load_flowmol3_state_dict
                    ),
                    FLOWMOL3ADAPTER_N_ATOM_TYPES=10,
                    FLOWMOL3ADAPTER_N_BOND_TYPES=5,
                ):
                    theta, debug = _rce._compute_flowmol3_real_atom_type_marginal(
                        adapter=stub_adapter,
                        trace=stub_trace,
                        seed=seed,
                        nfe=nfe,
                    )
            assert "seed" in captured, (
                "np.random.default_rng was never called — helper bailed "
                f"early with debug={debug!r}"
            )
            return captured["seed"]
        finally:
            # Remove the torch stub so subsequent tests that gate on
            # ``pytest.importorskip('torch')`` see a missing module.
            if _stub_installed and "torch" in sys.modules:
                del sys.modules["torch"]

    def test_same_seed_nfe_with_different_digest_yields_same_rng_seed(
        self,
    ) -> None:
        """The corruption property of Bug C is GONE: changing the
        trace's ``native_state_digest`` while holding ``(seed, nfe)``
        constant MUST NOT change the captured random-seed integer.

        Pre-fix (Wave 65 Agent 1 §5): the SHA-256 hash of the digest
        seeded the RNG, so two different digests produced two
        different seeds → two different random initial states → the
        metric saw the framework's restart-blended state as a
        different random input (the corruption that drove 3/9 cells
        to REGRESSION at seed 43/44 NFE=200 post-Wave-64).
        Post-fix (Wave 65 Agent 2): the helper uses
        ``int(seed) * 31 + int(nfe)`` directly, so the seed is
        invariant under changes to ``trace.native_state_digest``.
        """
        # Seed 43, NFE 200 — the regression cell.
        seed_a = self._run_and_capture_seed(
            seed=43, nfe=200,
            digest_value="flowmol3:restart:DEADBEEF_blended_round2",
        )
        seed_b = self._run_and_capture_seed(
            seed=43, nfe=200,
            digest_value="flowmol3:digest:COMPLETELY_DIFFERENT_AAAA",
        )
        assert seed_a == seed_b, (
            f"Bug C not fixed: different digests produced different "
            f"seeds (a={seed_a}, b={seed_b}). The metric is still "
            f"sensitive to trace.native_state_digest."
        )

    def test_captured_seed_equals_per_cell_key(self) -> None:
        """The captured seed must be the per-cell ``int(seed)*31+int(nfe)``
        key — never the SHA-256 hash of the trace digest.

        Verifies the fix is the EXACT line Agent 1 specified in
        ``docs/audit/wave65-bug-c-root-cause.md`` §5.
        """
        captured = self._run_and_capture_seed(
            seed=44, nfe=200,
            digest_value="anything-goes-here",
        )
        assert captured == 44 * 31 + 200 == 1564, (
            f"Bug C fix is not the per-cell key: "
            f"captured={captured}, expected={44*31+200}"
        )

    def test_different_nfe_yields_different_captured_seed(self) -> None:
        """Sanity: the per-cell key must vary with NFE so the metric
        still distinguishes cells, just on (seed, nfe) instead of
        the trace digest.

        Pre-fix: NFE was a factor of `steps` in the trace digest,
        but it was NOT the dominant factor (the digest's full
        ``source`` SHA was). Post-fix: NFE directly drives the seed
        via the per-cell key.
        """
        seed_50 = self._run_and_capture_seed(
            seed=43, nfe=50,
            digest_value="flowmol3:restart:fixed_digest",
        )
        seed_200 = self._run_and_capture_seed(
            seed=43, nfe=200,
            digest_value="flowmol3:restart:fixed_digest",
        )
        assert seed_50 != seed_200, (
            "Per-cell key collapse: same seed with different NFE "
            "produced the same captured RNG seed."
        )
        # And the per-cell key matches the documented formula.
        assert seed_50 == 43 * 31 + 50
        assert seed_200 == 43 * 31 + 200


# ---------------------------------------------------------------------------
# Wave 68 Phase 3 — :meth:`FlowMol3Adapter.observe` wraps the legacy
# ``observe_endpoint`` + ``observe_entropy_reduction`` into a typed tuple.
# ---------------------------------------------------------------------------
