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
    FLOWMOL3_CHANNELS,
    FLOWMOL3_CHANNEL_DOMAINS,
    FlowMol3Adapter,
    FlowMol3AtomTypeEntropyRestartPolicy,
    FlowMol3Capabilities,
    PER_POSITION_ENTROPY_REDUCTION,
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


class TestFlowMol3AtomTypeEntropyRestartPolicy:
    """FlowMol3-specific restart policy (Wave 49 Agent F).

    Mirrors the :class:`KanziGPTPriorRestartPolicy` (Wave 45 Agent F)
    and :class:`LineageFlowClassifierAwareRestart` (Wave 45 Agent G)
    patterns. Reads per-atom entropy over the 10-way atom-type
    categorical and biases the schedule-driven base memory fraction
    per atom.
    """

    def test_default_construction_succeeds(self) -> None:
        policy = FlowMol3AtomTypeEntropyRestartPolicy()
        assert policy.m_floor == 0.05
        assert policy.m_ceiling == 0.95
        assert policy.entropy_floor > 0.0
        assert policy.entropy_ceiling > policy.entropy_floor

    def test_invalid_entropy_floor_raises(self) -> None:
        import pytest as _pytest
        with _pytest.raises(ValueError):
            FlowMol3AtomTypeEntropyRestartPolicy(
                entropy_floor=1.0,
                entropy_ceiling=0.5,
            )

    def test_invalid_m_floor_raises(self) -> None:
        import pytest as _pytest
        with _pytest.raises(ValueError):
            FlowMol3AtomTypeEntropyRestartPolicy(
                m_floor=0.6,
                m_ceiling=0.5,
            )

    def test_propose_restart_returns_uniform_alpha(self) -> None:
        import numpy as np

        policy = FlowMol3AtomTypeEntropyRestartPolicy()
        alpha = policy.propose_restart(trace=None, paper_quantities=None)
        assert isinstance(alpha, np.ndarray)
        assert alpha.shape == (8,)  # FLOWMOL3_PLACEHOLDER_NUM_NODES
        assert np.allclose(alpha, 0.5)

    def test_memory_fraction_vector_no_prior_entry_returns_base(
        self,
    ) -> None:
        import numpy as np

        policy = FlowMol3AtomTypeEntropyRestartPolicy()
        m_vec = policy.memory_fraction_vector(
            prior_entry=None, base_m=0.7,
        )
        # Synthetic-mode fallback: uniform m_vec = base_m.
        assert m_vec.shape == (8,)
        assert np.allclose(m_vec, 0.7)

    def test_memory_fraction_vector_missing_payload_returns_base(
        self,
    ) -> None:
        import numpy as np

        policy = FlowMol3AtomTypeEntropyRestartPolicy()
        m_vec = policy.memory_fraction_vector(
            prior_entry={"some_other_key": 1.0}, base_m=0.4,
        )
        # Missing ``atom_type_distribution`` key triggers the fallback.
        assert m_vec.shape == (8,)
        assert np.allclose(m_vec, 0.4)

    def test_memory_fraction_vector_low_entropy_high_m(self) -> None:
        import numpy as np

        policy = FlowMol3AtomTypeEntropyRestartPolicy()
        # Spike logits at index 0: per-atom entropy = 0 (low) → m_ceiling
        atom_logits = np.zeros(
            (4, int(FLOWMOL3_ATOM_TYPE_VOCAB_SIZE)), dtype=np.float64,
        )
        atom_logits[:, 0] = 100.0  # confident spike
        m_vec = policy.memory_fraction_vector(
            prior_entry={"atom_type_distribution": atom_logits},
            base_m=0.5,
        )
        # Each atom has low entropy → m near m_ceiling = 0.95,
        # but clamped to [min(base, m_floor), max(base, m_ceiling)]
        # = [0.05, 0.95]. So m_vec is ~0.95.
        assert np.all(m_vec >= 0.05)
        assert np.all(m_vec <= 0.95)
        # With base_m=0.5 and low entropy, m_vec should be near ceiling.
        assert float(m_vec.mean()) > 0.7

    def test_memory_fraction_vector_high_entropy_low_m(self) -> None:
        import numpy as np

        policy = FlowMol3AtomTypeEntropyRestartPolicy()
        # Uniform logits: per-atom entropy = log(K) (high) → m_floor
        atom_logits = np.ones(
            (4, int(FLOWMOL3_ATOM_TYPE_VOCAB_SIZE)), dtype=np.float64,
        )
        m_vec = policy.memory_fraction_vector(
            prior_entry={"atom_type_distribution": atom_logits},
            base_m=0.5,
        )
        # Each atom has high entropy → m near m_floor = 0.05,
        # clamped to [min(base, m_floor), max(base, m_ceiling)]
        # = [0.05, 0.95]. So m_vec is ~0.05.
        assert np.all(m_vec >= 0.05)
        assert np.all(m_vec <= 0.95)
        # With base_m=0.5 and high entropy, m_vec should be near floor.
        assert float(m_vec.mean()) < 0.3

    def test_memory_fraction_vector_malformed_shape_raises(
        self,
    ) -> None:
        import numpy as np
        import pytest as _pytest

        policy = FlowMol3AtomTypeEntropyRestartPolicy()
        # Wrong last dim: 7 instead of FLOWMOL3_ATOM_TYPE_VOCAB_SIZE.
        atom_logits = np.zeros((4, 7), dtype=np.float64)
        with _pytest.raises(ValueError, match="atom_type_distribution_shape_invalid"):
            policy.memory_fraction_vector(
                prior_entry={"atom_type_distribution": atom_logits},
                base_m=0.5,
            )


class TestFlowMol3PolicyWiring:
    """Restart policy wiring into apply_restart_distribution (Wave 49 Agent F)."""

    def test_default_adapter_no_atom_policy(
        self, adapter
    ) -> None:
        """Default-constructed adapter has no atom-type policy."""
        assert adapter._atom_type_entropy_restart_policy is None  # noqa: SLF001

    def test_invalid_policy_type_raises(self) -> None:
        import pytest as _pytest
        with _pytest.raises(TypeError):
            FlowMol3Adapter(atom_type_entropy_restart_policy="not_a_policy")  # type: ignore[arg-type]

    def test_valid_policy_accepted(self) -> None:
        policy = FlowMol3AtomTypeEntropyRestartPolicy()
        adapter = FlowMol3Adapter(
            atom_type_entropy_restart_policy=policy,
        )
        assert (
            adapter._atom_type_entropy_restart_policy  # noqa: SLF001
            is policy
        )

    def test_apply_restart_emits_atom_audit_when_policy_active(
        self, adapter
    ) -> None:
        """When the atom-type policy is wired, the restart bundle carries
        the AUDIT_FLOWMOL3_ATOM_TYPE_ENTROPY_RESTART code in its provenance.
        """
        from types import SimpleNamespace
        policy = FlowMol3AtomTypeEntropyRestartPolicy()
        adapter = FlowMol3Adapter(
            atom_type_entropy_restart_policy=policy,
        )
        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        # Minimal policy with beta_by_channel.
        restart_policy = SimpleNamespace(
            policy_hash="test",
            beta_by_channel={"coordinate": 0.5},
        )
        new_bundle = adapter.apply_restart_distribution(
            bundle, restart_policy,
        )
        assert AUDIT_FLOWMOL3_ATOM_TYPE_ENTROPY_RESTART in new_bundle.provenance

    def test_apply_restart_default_no_atom_audit(
        self, adapter
    ) -> None:
        """Default adapter does NOT emit the atom-type audit code."""
        from types import SimpleNamespace
        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        restart_policy = SimpleNamespace(
            policy_hash="test",
            beta_by_channel={"coordinate": 0.5},
        )
        new_bundle = adapter.apply_restart_distribution(
            bundle, restart_policy,
        )
        # The audit code should NOT be present in default mode.
        assert (
            AUDIT_FLOWMOL3_ATOM_TYPE_ENTROPY_RESTART
            not in new_bundle.provenance
        )
        # But the legacy restart-boundary audit code is preserved
        # (Wave 41 regression-vector byte-stability).
        assert "flowmol3_restart_boundary" in new_bundle.provenance


class TestFlowMol3PublicSurface:
    """Public symbol surface for Wave 49 Agent F additions."""

    def test_per_position_entropy_reduction_key_matches_lineageflow(
        self,
    ) -> None:
        from adaptive_reflow.adapters.lineageflow import (
            PER_POSITION_ENTROPY_REDUCTION as LF_KEY,
        )
        assert LF_KEY == PER_POSITION_ENTROPY_REDUCTION

    def test_atom_type_vocab_size_matches_v2_adapter(self) -> None:
        from adaptive_reflow.adapters.flowmol3_v2_adapter import (
            FLOWMOL3ADAPTER_N_ATOM_TYPES,
        )
        assert FLOWMOL3ADAPTER_N_ATOM_TYPES == FLOWMOL3_ATOM_TYPE_VOCAB_SIZE

    def test_factory_accepts_policy(self) -> None:
        policy = FlowMol3AtomTypeEntropyRestartPolicy()
        adapter = default_flowmol3_adapter(
            atom_type_entropy_restart_policy=policy,
        )
        assert isinstance(adapter, FlowMol3Adapter)
        assert (
            adapter._atom_type_entropy_restart_policy  # noqa: SLF001
            is policy
        )


# ---------------------------------------------------------------------------
# Wave 50 Agent A — ``force_mode`` kwarg + real-ckpt loader
# ---------------------------------------------------------------------------


class TestFlowMol3ForceModeFactory:
    """Regression suite for the Wave 50 Agent A factory fix.

    Before Wave 50, :func:`tools.run_real_ckpt_eval._resolve_adapter`
    called ``factory(force_mode=...)`` and crashed with
    ``TypeError: default_flowmol3_adapter() got an unexpected keyword
    argument force_mode``. After Wave 50, the factory accepts the kwarg
    and, when ``force_mode in {"real", "auto"}``, attempts to load the
    published FlowMol3 Lightning checkpoint at
    :data:`FLOWMOL3_REAL_CKPT_PATH`.
    """

    def test_default_factory_is_synthetic(self) -> None:
        """Omitting ``force_mode`` keeps byte-identical placeholder path."""
        adapter = default_flowmol3_adapter()
        assert adapter._force_mode == "synthetic"  # noqa: SLF001
        assert adapter._real_ckpt_meta is None  # noqa: SLF001
        assert isinstance(adapter, FlowMol3Adapter)

    def test_factory_explicit_synthetic_no_load(self) -> None:
        """``force_mode='synthetic'`` is byte-identical to default."""
        adapter = default_flowmol3_adapter(force_mode="synthetic")
        assert adapter._force_mode == "synthetic"  # noqa: SLF001
        assert adapter._real_ckpt_meta is None  # noqa: SLF001

    def test_factory_real_loads_published_ckpt(self) -> None:
        """``force_mode='real'`` loads the 65 MB published ckpt.

        The shipped ``data/flowmol3/weights_real/checkpoints/last.ckpt``
        is a PyTorch Lightning checkpoint with ``epoch=17`` and
        ``global_step=1547236``. We don't decode the tensors — only the
        envelope — to stay byte-stable on torch version drift.
        """
        if not os.path.isfile(FLOWMOL3_REAL_CKPT_PATH):
            pytest.skip(
                f"FlowMol3 real ckpt not shipped at {FLOWMOL3_REAL_CKPT_PATH}"
            )
        adapter = default_flowmol3_adapter(force_mode="real")
        assert adapter._force_mode == "real"  # noqa: SLF001
        assert adapter._real_ckpt_meta is not None  # noqa: SLF001
        assert (
            adapter._real_ckpt_meta["path"]  # noqa: SLF001
            == FLOWMOL3_REAL_CKPT_PATH
        )
        assert adapter._real_ckpt_meta["n_tensors"] > 0  # noqa: SLF001
        # The published ckpt has epoch=17; pin the contract so any
        # silent re-upload of a different snapshot breaks this test.
        assert adapter._real_ckpt_meta["epoch"] == 17  # noqa: SLF001

    def test_factory_auto_loads_real_when_available(self) -> None:
        """``force_mode='auto'`` tries real, succeeds when shipped."""
        if not os.path.isfile(FLOWMOL3_REAL_CKPT_PATH):
            pytest.skip(
                f"FlowMol3 real ckpt not shipped at {FLOWMOL3_REAL_CKPT_PATH}"
            )
        adapter = default_flowmol3_adapter(force_mode="auto")
        assert adapter._force_mode == "auto"  # noqa: SLF001
        assert adapter._real_ckpt_meta is not None  # noqa: SLF001
        assert (
            adapter._real_ckpt_meta["n_tensors"] > 0  # noqa: SLF001
        )

    def test_factory_auto_falls_back_to_synthetic_when_ckpt_missing(
        self,
    ) -> None:
        """``force_mode='auto'`` degrades gracefully when ckpt absent."""
        adapter = default_flowmol3_adapter(
            force_mode="auto",
            weights_path="/nonexistent/flowmol3/last.ckpt",
        )
        # force_mode is preserved verbatim so callers can distinguish
        # "user asked for auto" from "user asked for synthetic".
        assert adapter._force_mode == "auto"  # noqa: SLF001
        assert adapter._real_ckpt_meta is None  # noqa: SLF001

    def test_factory_real_raises_when_ckpt_missing(self) -> None:
        """``force_mode='real'`` is loud: raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="ckpt_missing"):
            default_flowmol3_adapter(
                force_mode="real",
                weights_path="/nonexistent/flowmol3/last.ckpt",
            )

    def test_factory_rejects_unknown_force_mode(self) -> None:
        """Unknown ``force_mode`` strings raise ``ValueError``."""
        with pytest.raises(ValueError, match="unknown_force_mode"):
            default_flowmol3_adapter(force_mode="bogus")

    def test_constructor_rejects_unknown_force_mode_directly(self) -> None:
        """``FlowMol3Adapter.__init__`` also rejects bogus tokens."""
        with pytest.raises(ValueError, match="unknown_force_mode"):
            FlowMol3Adapter(force_mode="bogus")

    def test_loaded_marker_constant_is_defined(self) -> None:
        """``FLOWMOL3_REAL_CKPT_LOADED_MARKER`` is exported and string."""
        assert isinstance(FLOWMOL3_REAL_CKPT_LOADED_MARKER, str)
        assert FLOWMOL3_REAL_CKPT_LOADED_MARKER == "flowmol3_real_ckpt_loaded"

    def test_ckpt_path_constant_points_at_shipped_artifact(self) -> None:
        """``FLOWMOL3_REAL_CKPT_PATH`` resolves to the shipped ckpt."""
        # Path should end in ``weights_real/checkpoints/last.ckpt`` and
        # the parent directory must exist (we do not require the ckpt
        # to exist so a missing-file scenario still resolves).
        assert FLOWMOL3_REAL_CKPT_PATH.endswith(
            "weights_real/checkpoints/last.ckpt"
        )
        assert os.path.isdir(os.path.dirname(FLOWMOL3_REAL_CKPT_PATH))

    def test_try_load_real_ckpt_helper_returns_meta_on_success(self) -> None:
        """Direct unit test of the internal loader."""
        if not os.path.isfile(FLOWMOL3_REAL_CKPT_PATH):
            pytest.skip(
                f"FlowMol3 real ckpt not shipped at {FLOWMOL3_REAL_CKPT_PATH}"
            )
        meta, err = _try_load_real_ckpt(FLOWMOL3_REAL_CKPT_PATH)
        assert err is None
        assert meta is not None
        assert meta["path"] == FLOWMOL3_REAL_CKPT_PATH
        assert meta["n_tensors"] > 0

    def test_try_load_real_ckpt_helper_returns_reason_on_missing(
        self,
    ) -> None:
        """Direct unit test of the missing-file path."""
        meta, err = _try_load_real_ckpt("/nonexistent/flowmol3/last.ckpt")
        assert meta is None
        assert err == "ckpt_missing"

    def test_real_ckpt_adapter_is_still_a_valid_adapter(self) -> None:
        """A real-ckpt adapter still produces placeholder state.

        The placeholder adapter always returns placeholder state — the
        ``force_mode='real'`` path only records that the ckpt loaded;
        it does NOT swap the state materializer. The v2 adapter is the
        one that runs inference through the real stack. This test
        guards against a future refactor accidentally regressing that
        separation of concerns.
        """
        if not os.path.isfile(FLOWMOL3_REAL_CKPT_PATH):
            pytest.skip(
                f"FlowMol3 real ckpt not shipped at {FLOWMOL3_REAL_CKPT_PATH}"
            )
        adapter = default_flowmol3_adapter(force_mode="real")
        bundle = adapter.build_initial_state(
            batch_id="b-wave50", sample_id="s-wave50"
        )
        ok, _ = validate_state_bundle(bundle)
        assert ok
        # Real-ckpt marker is exposed on the adapter as an audit hook.
        assert adapter._real_ckpt_meta is not None  # noqa: SLF001


# ---------------------------------------------------------------------------
# Wave 58 — NFE-adaptive restart gate
# ---------------------------------------------------------------------------


def _restart_policy(nfe_budget: object = _UNSET) -> object:
    """Minimal duck-typed restart policy for the gate tests.

    Carries a ``beta_by_channel`` over all three FlowMol3 channels so
    ``_restart_memory_fraction`` returns the paper-default ``m = 0.5``
    (the blend the gate exists to suppress). ``nfe_budget`` is attached
    only when supplied, so the default policy exercises the
    "policy does not carry a budget" branch.
    """
    from types import SimpleNamespace

    policy = SimpleNamespace(
        policy_hash="wave58-test",
        beta_by_channel={ch: 0.5 for ch in FLOWMOL3_CHANNELS},
    )
    if nfe_budget is not _UNSET:
        policy.nfe_budget = nfe_budget
    return policy


def _skip_codes(bundle: StateBundle) -> list[str]:
    """Provenance entries stamped by the low-NFE gate."""
    return [
        entry
        for entry in bundle.provenance
        if entry.startswith(AUDIT_FLOWMOL3_RESTART_SKIPPED_LOW_NFE)
    ]


class TestFlowMol3NfeAdaptiveRestartGate:
    """NFE-adaptive restart gate (Wave 58).

    FlowMol3's restart blend replaces ``1 - m`` of the state with fresh
    noise (``m = 0.5`` at the paper default). Wave 57 measured
    ``framework_improves=False`` on 9 real-ckpt cells with every NFE=10
    cell regressing, and Agent C traced it to that blend corrupting the
    CTMC chain when too few integration steps remain to re-absorb the
    noise. The gate skips the blend below
    :data:`FLOWMOL3_RESTART_MIN_NFE`.

    See ``docs/audit/wave58-nfe-adaptive-gate-impl.md``.
    """

    def test_low_nfe_skips_restart_and_leaves_state_unchanged(
        self, adapter
    ) -> None:
        """``nfe_budget=10`` ⇒ blend skipped, payload identical.

        "Unchanged" means every field the blend would have rewritten:
        the channel + mask refs, the source round, and — critically —
        ``native_state_digest``, which on the blended path becomes
        ``flowmol3:restart:<blended digest>``. Only ``provenance`` grows,
        by the audit entry that makes the skip visible downstream.
        """
        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        result = adapter.apply_restart_distribution(
            bundle, _restart_policy(), nfe_budget=10
        )

        assert result.native_state_digest == bundle.native_state_digest
        assert not result.native_state_digest.startswith("flowmol3:restart:")
        assert dict(result.channels) == dict(bundle.channels)
        assert dict(result.masks) == dict(bundle.masks)
        assert result.source_round == bundle.source_round
        assert result.detach_proof is True
        ok, errs = validate_state_bundle(result)
        assert ok, errs

        # Provenance: the prior trail is preserved verbatim and exactly
        # one skip entry is appended.
        assert result.provenance[: len(bundle.provenance)] == bundle.provenance
        assert len(_skip_codes(result)) == 1
        # The blend's own audit code must NOT appear — this round did
        # not restart, and an eval reading provenance must not be told
        # otherwise.
        assert "flowmol3_restart_boundary" not in result.provenance

    def test_high_nfe_applies_restart_blend(self, adapter) -> None:
        """``nfe_budget=200`` ⇒ normal blend, no skip audit code."""
        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        result = adapter.apply_restart_distribution(
            bundle, _restart_policy(), nfe_budget=200
        )

        assert result.native_state_digest.startswith("flowmol3:restart:")
        assert result.native_state_digest != bundle.native_state_digest
        assert "flowmol3_restart_boundary" in result.provenance
        assert _skip_codes(result) == []

    def test_unknown_nfe_budget_is_byte_identical_to_pre_wave58(
        self, adapter
    ) -> None:
        """No budget anywhere ⇒ the gate is inert (fail-open).

        This is the byte-stability guard for every pre-Wave-58 caller —
        the engine, and the pinned D.4 vectors in
        ``regression-vectors/flowmol3.json``. A gate that fired on an
        unknown budget would silently flatten the framework arm to
        baseline for all of them.
        """
        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        gated = adapter.apply_restart_distribution(
            bundle, _restart_policy(), nfe_budget=200
        )
        ungated = adapter.apply_restart_distribution(bundle, _restart_policy())

        assert ungated.native_state_digest == gated.native_state_digest
        assert ungated.provenance == gated.provenance
        assert _skip_codes(ungated) == []

    def test_threshold_boundary_is_exclusive(self, adapter) -> None:
        """The gate fires on ``nfe < min_nfe``, not ``<=``."""
        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        at_threshold = adapter.apply_restart_distribution(
            bundle, _restart_policy(), nfe_budget=FLOWMOL3_RESTART_MIN_NFE
        )
        below = adapter.apply_restart_distribution(
            bundle, _restart_policy(), nfe_budget=FLOWMOL3_RESTART_MIN_NFE - 1
        )

        assert at_threshold.native_state_digest.startswith("flowmol3:restart:")
        assert _skip_codes(at_threshold) == []
        assert below.native_state_digest == bundle.native_state_digest
        assert len(_skip_codes(below)) == 1

    def test_skip_audit_code_records_nfe_and_threshold(self, adapter) -> None:
        """The audit entry carries the numbers that drove the decision.

        A bare marker would make a v4 sweep un-auditable: the reader
        could see *that* a cell was gated but not at what budget or
        against which threshold (which is a constructor kwarg, so it
        varies per adapter).
        """
        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        result = adapter.apply_restart_distribution(
            bundle, _restart_policy(), nfe_budget=10
        )
        (code,) = _skip_codes(result)
        assert code == (
            f"{AUDIT_FLOWMOL3_RESTART_SKIPPED_LOW_NFE}"
            f":nfe=10:min_nfe={FLOWMOL3_RESTART_MIN_NFE}"
        )

    def test_gate_reads_budget_from_policy_attribute(self, adapter) -> None:
        """A duck-typed ``policy.nfe_budget`` drives the gate."""
        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        skipped = adapter.apply_restart_distribution(
            bundle, _restart_policy(nfe_budget=10)
        )
        blended = adapter.apply_restart_distribution(
            bundle, _restart_policy(nfe_budget=200)
        )

        assert len(_skip_codes(skipped)) == 1
        assert _skip_codes(blended) == []

    def test_gate_reads_budget_from_constructor_kwarg(self) -> None:
        """``FlowMol3Adapter(nfe_budget=...)`` drives the gate.

        This is the seam a per-cell eval harness uses: one adapter per
        ``(model, seed, nfe)`` cell, no change at the restart call site.
        """
        low = FlowMol3Adapter(nfe_budget=10)
        high = FlowMol3Adapter(nfe_budget=200)
        bundle = low.build_initial_state(batch_id="b", sample_id="s")

        assert len(
            _skip_codes(low.apply_restart_distribution(bundle, _restart_policy()))
        ) == 1
        assert _skip_codes(
            high.apply_restart_distribution(bundle, _restart_policy())
        ) == []

    def test_call_kwarg_outranks_policy_and_constructor(self) -> None:
        """Resolution order: call kwarg > policy attribute > constructor."""
        adapter = FlowMol3Adapter(nfe_budget=10)
        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")

        # Call kwarg (200) beats both the policy (10) and the ctor (10).
        assert _skip_codes(
            adapter.apply_restart_distribution(
                bundle, _restart_policy(nfe_budget=10), nfe_budget=200
            )
        ) == []
        # Policy attribute (200) beats the ctor (10).
        assert _skip_codes(
            adapter.apply_restart_distribution(
                bundle, _restart_policy(nfe_budget=200)
            )
        ) == []

    def test_restart_min_nfe_zero_disables_the_gate(self) -> None:
        """``restart_min_nfe=0`` restores the unconditional blend."""
        adapter = FlowMol3Adapter(nfe_budget=2, restart_min_nfe=0)
        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        result = adapter.apply_restart_distribution(bundle, _restart_policy())

        assert result.native_state_digest.startswith("flowmol3:restart:")
        assert _skip_codes(result) == []

    def test_custom_threshold_is_honoured(self) -> None:
        """The threshold is recalibratable, not a hard-wired literal.

        Wave 57 Agent B estimated 20 from n=3 per stratum, so the v4
        18-cell grid must be able to move it without a code edit.
        """
        adapter = FlowMol3Adapter(restart_min_nfe=100)
        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        result = adapter.apply_restart_distribution(
            bundle, _restart_policy(), nfe_budget=50
        )

        assert result.native_state_digest == bundle.native_state_digest
        assert _skip_codes(result) == [
            f"{AUDIT_FLOWMOL3_RESTART_SKIPPED_LOW_NFE}:nfe=50:min_nfe=100"
        ]

    def test_skipped_restart_suppresses_atom_type_entropy_audit(self) -> None:
        """A gated round emits no blend-side audit code at all.

        The Wave 49 atom-type-entropy policy stamps its own code from
        inside the blend path. When the gate fires that path never runs,
        so the code must be absent — otherwise an eval would attribute
        an atom-type-aware restart to a round that did not restart.
        """
        adapter = FlowMol3Adapter(
            atom_type_entropy_restart_policy=(
                FlowMol3AtomTypeEntropyRestartPolicy()
            ),
            nfe_budget=10,
        )
        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        result = adapter.apply_restart_distribution(bundle, _restart_policy())

        assert (
            AUDIT_FLOWMOL3_ATOM_TYPE_ENTROPY_RESTART not in result.provenance
        )
        assert "flowmol3_restart_boundary" not in result.provenance
        assert len(_skip_codes(result)) == 1

    @pytest.mark.parametrize("bad", ["fifty", 0, 1, -5, 17.5, True, object()])
    def test_invalid_explicit_budget_fails_closed(self, bad) -> None:
        """An explicitly-typed bad budget raises, both entry points.

        ``0``/``1`` are rejected because a budget that cannot be split
        across restart rounds is a caller bug, and ``17.5`` because
        silently truncating it to 17 would hide one.
        """
        with pytest.raises((ValueError, TypeError)):
            FlowMol3Adapter(nfe_budget=bad)

        adapter = FlowMol3Adapter()
        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        with pytest.raises((ValueError, TypeError)):
            adapter.apply_restart_distribution(
                bundle, _restart_policy(), nfe_budget=bad
            )

    @pytest.mark.parametrize("bad", ["fifty", 0, -5, None, object()])
    def test_junk_policy_budget_attribute_falls_through(self, bad) -> None:
        """An unusable ``policy.nfe_budget`` never breaks a restart.

        Unlike an explicit argument, this attribute is *discovered* on a
        third-party policy object — a same-named field meaning something
        else must degrade to "no budget here", not raise mid-round.
        """
        adapter = FlowMol3Adapter()
        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        result = adapter.apply_restart_distribution(
            bundle, _restart_policy(nfe_budget=bad)
        )

        assert result.native_state_digest.startswith("flowmol3:restart:")
        assert _skip_codes(result) == []

    @pytest.mark.parametrize("bad", [-1, "20", 20.0, True, None])
    def test_invalid_restart_min_nfe_rejected(self, bad) -> None:
        with pytest.raises((ValueError, TypeError)):
            FlowMol3Adapter(restart_min_nfe=bad)

    def test_factory_threads_gate_kwargs(self) -> None:
        """The registry factory exposes both gate knobs."""
        adapter = default_flowmol3_adapter(nfe_budget=10, restart_min_nfe=25)
        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        result = adapter.apply_restart_distribution(bundle, _restart_policy())

        assert _skip_codes(result) == [
            f"{AUDIT_FLOWMOL3_RESTART_SKIPPED_LOW_NFE}:nfe=10:min_nfe=25"
        ]

    def test_factory_default_leaves_gate_inert(self) -> None:
        """``default_flowmol3_adapter()`` is unchanged by Wave 58."""
        adapter = default_flowmol3_adapter()
        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        result = adapter.apply_restart_distribution(bundle, _restart_policy())

        assert result.native_state_digest.startswith("flowmol3:restart:")
        assert _skip_codes(result) == []


# ---------------------------------------------------------------------------
# Wave 63 Agent 2 — Bug B regression: source_round must be bumped
# ---------------------------------------------------------------------------


class TestFlowMol3RestartBumpsSourceRound:
    """Regression suite for Wave 63 Agent 1's Bug B.

    Bug B (root cause: ``docs/audit/wave63-root-cause.md`` §3): the
    :meth:`FlowMol3Adapter.apply_restart_distribution` path at
    ``adaptive_reflow/adapters/flowmol3.py:910-919`` did NOT bump
    ``state.source_round`` on the returned state. That meant the
    "_graph_payload_for("fresh", batch, sample, source_round=state.source_round)"
    seed on every subsequent restart boundary was identical to the
    first round's seed, so the framework's "fresh" noise injection was
    actually deterministic across rounds. The v2 adapter
    (``flowmol3_v2_adapter.py:2138``) bumps ``source_round = int(next_round)``
    on the same path, so the v1 behaviour was a divergence from the
    v2 / self_flow convention.

    The regression test below verifies that after a SUCCESSFUL blend
    (i.e. the low-NFE gate does NOT fire and ``apply_restart_distribution``
    runs the blend path), the returned bundle's ``source_round`` is
    exactly one greater than the input's. It also verifies that the
    blend path's payload is byte-different across two consecutive
    restart calls on the same input — the symptom Agent 1 traced as
    "constant_F drift" in §3.2 of the root-cause audit.
    """

    def test_blend_path_bumps_source_round_by_one(self, adapter) -> None:
        """A successful blend must increment ``source_round`` by exactly 1.

        Pre-fix: ``result.source_round == bundle.source_round`` (== 0)
        because the ``replace(...)`` call at line 910-919 didn't touch
        ``source_round`` — the rest of the wave's "fresh noise" was
        drawn from a constant seed.
        Post-fix: ``result.source_round == 1``.
        """
        bundle = adapter.build_initial_state(
            batch_id="wave63-bugb", sample_id="wave63-bugb",
        )
        # Pre-condition: build_initial_state sets source_round=0.
        assert bundle.source_round == 0

        result = adapter.apply_restart_distribution(
            bundle, _restart_policy(), nfe_budget=200,
        )

        # The blend ran (no skip audit code).
        assert _skip_codes(result) == []
        assert result.native_state_digest.startswith("flowmol3:restart:")
        # The fix: source_round bumped by exactly 1.
        assert result.source_round == bundle.source_round + 1
        assert result.source_round == 1

    def test_consecutive_blends_yield_distinct_fresh_payloads(
        self, adapter,
    ) -> None:
        """Two consecutive restart calls must yield DIFFERENT
        ``native_state_digest`` values.

        Pre-fix: both calls threaded the same ``source_round=0`` through
        ``_graph_payload_for("fresh", ...)``, so the "fresh" payload was
        the same Python object — ``blended.digest()`` was identical, so
        ``native_state_digest = f"flowmol3:restart:{blended.digest()}"``
        was identical on both calls. That is the Bug B "constant_F
        drift" Agent 1 described in §3.2: every restart pulled the
        trajectory toward the same fresh payload, so the framework
        drifted deterministically instead of injecting independent
        noise.
        Post-fix: round 2's ``source_round == 1`` changes the seed of
        ``_graph_payload_for("fresh", batch, sample, source_round=1)``
        so round 2's digest differs from round 1's.
        """
        bundle = adapter.build_initial_state(
            batch_id="wave63-bugb-chain", sample_id="wave63-bugb-chain",
        )

        # Round 1: source_round 0 -> 1
        round1 = adapter.apply_restart_distribution(
            bundle, _restart_policy(), nfe_budget=200,
        )
        assert round1.source_round == 1
        assert round1.native_state_digest.startswith("flowmol3:restart:")

        # Round 2: source_round 1 -> 2 — must use a DIFFERENT fresh payload.
        round2 = adapter.apply_restart_distribution(
            round1, _restart_policy(), nfe_budget=200,
        )
        assert round2.source_round == 2
        assert round2.source_round == round1.source_round + 1
        # Bug B's smoking gun: the digests must DIFFER. If they are
        # identical, the fresh payload is still constant across rounds.
        assert round2.native_state_digest != round1.native_state_digest

    def test_skipped_blend_does_NOT_bump_source_round(
        self, adapter,
    ) -> None:
        """The low-NFE gate skips the blend, so ``source_round`` MUST stay.

        This guards the orthogonal path: when the gate fires (nfe below
        threshold), ``apply_restart_distribution`` returns ``state``
        unchanged except for the skip audit code — including
        ``source_round``. Bumping it on the skip path would be wrong:
        no restart happened, so the round counter must not advance.
        """
        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        result = adapter.apply_restart_distribution(
            bundle, _restart_policy(), nfe_budget=10,
        )

        assert len(_skip_codes(result)) == 1
        # Skip path is unchanged by Bug B fix — source_round MUST stay 0.
        assert result.source_round == bundle.source_round
        assert result.source_round == 0


class TestFlowMol3ObserveProtocol:
    """``observe(...)`` returns a typed :class:`ObservationResult` tuple.

    Mirrors the Wave 68 Phase 1 ``AdapterObservationProtocol`` design.
    The v1 placeholder supports two of the four observation kinds
    (``ENDPOINT_BUNDLE`` and ``POSITION_ENTROPY_REDUCTION``); the
    remaining two are intentionally omitted (no discrete-token
    channel, no preserved native trajectory).
    """

    def _make_trace(self, adapter, seed: int = 0):
        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
        cond = ODEConditionDelta(
            delta_spec={"num_steps": 1},
            source="test_flowmol3_observe",
            target_round=1,
            calibration_artifact_hash="a" * 64,
        )
        return adapter.solve_ode(bundle, cond, seed=seed), bundle

    def test_observe_conforms_to_protocol(self, adapter) -> None:
        """``observe(...)`` satisfies the :class:`AdapterObservationProtocol` Protocol."""
        from adaptive_reflow.framework.interfaces import AdapterObservationProtocol
        assert isinstance(adapter, AdapterObservationProtocol)

    def test_observe_default_returns_two_results(self, adapter) -> None:
        """Default strategies → ``ENDPOINT_BUNDLE`` + ``POSITION_ENTROPY_REDUCTION``."""
        from adaptive_reflow.framework.interfaces import ObservationKind
        trace, bundle = self._make_trace(adapter, seed=0)
        results = adapter.observe(trace, bundle)
        kinds = {r.kind for r in results}
        assert kinds == {
            ObservationKind.ENDPOINT_BUNDLE,
            ObservationKind.POSITION_ENTROPY_REDUCTION,
        }
        # Length 2.
        assert len(results) == 2

    def test_observe_endpoint_only_returns_one_result(self, adapter) -> None:
        """Restricted ``strategies`` skips the entropy strategy."""
        from adaptive_reflow.framework.interfaces import ObservationKind
        trace, bundle = self._make_trace(adapter, seed=0)
        results = adapter.observe(
            trace, bundle, strategies=(ObservationKind.ENDPOINT_BUNDLE,)
        )
        assert len(results) == 1
        assert results[0].kind == ObservationKind.ENDPOINT_BUNDLE
        # Payload is the StateBundle from observe_endpoint.
        assert results[0].payload is bundle or hasattr(
            results[0].payload, "native_state_digest"
        )

    def test_observe_discrete_tokens_skipped_for_v1(self, adapter) -> None:
        """FlowMol3 v1 has no DISCRETE_TOKENS observation (no token index channel)."""
        from adaptive_reflow.framework.interfaces import ObservationKind
        trace, bundle = self._make_trace(adapter, seed=0)
        results = adapter.observe(
            trace, bundle, strategies=(ObservationKind.DISCRETE_TOKENS,)
        )
        assert results == ()

    def test_observe_trajectory_native_skipped_for_v1(self, adapter) -> None:
        """FlowMol3 v1 raises ``NotImplementedError`` on ``export_trajectory``."""
        from adaptive_reflow.framework.interfaces import ObservationKind
        trace, bundle = self._make_trace(adapter, seed=0)
        results = adapter.observe(
            trace, bundle, strategies=(ObservationKind.TRAJECTORY_NATIVE,)
        )
        assert results == ()

    def test_observe_entropy_reduction_byte_stable(self, adapter) -> None:
        """Two calls return identical POSITION_ENTROPY_REDUCTION results."""
        from adaptive_reflow.framework.interfaces import ObservationKind
        trace, bundle = self._make_trace(adapter, seed=42)
        r1 = adapter.observe(
            trace,
            bundle,
            strategies=(ObservationKind.POSITION_ENTROPY_REDUCTION,),
        )
        r2 = adapter.observe(
            trace,
            bundle,
            strategies=(ObservationKind.POSITION_ENTROPY_REDUCTION,),
        )
        assert r1 == r2
        assert r1[0].kind == ObservationKind.POSITION_ENTROPY_REDUCTION
        assert r1[0].units == "nats"
        assert r1[0].channel == PER_POSITION_ENTROPY_REDUCTION

    def test_observe_legacy_methods_still_work(self, adapter) -> None:
        """The legacy ``observe_endpoint`` / ``observe_entropy_reduction`` are unchanged."""
        trace, bundle = self._make_trace(adapter, seed=0)
        # Direct call to observe_endpoint → StateBundle.
        ep = adapter.observe_endpoint(trace, bundle)
        assert hasattr(ep, "native_state_digest")
        # Direct call to observe_entropy_reduction → dict[str, float].
        ent = adapter.observe_entropy_reduction(trace)
        assert PER_POSITION_ENTROPY_REDUCTION in ent


# ---------------------------------------------------------------------------
# Wave 54 Phase 2 fix: v1 (hash stub) FlowMol3 is first-class alongside v2
# (real integration) via the new
# ``FlowMatchingODEAdapterWithObservation`` Protocol declared in
# ``adaptive_reflow/framework/interfaces.py``.
class TestFlowMol3Wave54V1Protocol:
    """Wave 54 Phase 2 — v1 first-class Protocol conformance.

    The :class:`FlowMatchingODEAdapterWithObservation` Protocol
    (declared in
    :mod:`adaptive_reflow.framework.interfaces`) captures the structural
    surface both v1 (hash stub) and v2 (real integration) FlowMol3
    adapters satisfy. v1's hash-based behaviour is preserved
    byte-identically (the 9 D.4 regression vectors in
    ``regression-vectors/flowmol3.json`` must remain byte-stable).
    """

    def test_v1_satisfies_protocol(self, adapter) -> None:
        """v1 instance satisfies ``FlowMatchingODEAdapterWithObservation``."""
        from adaptive_reflow.framework.interfaces import (
            FlowMatchingODEAdapterWithObservation,
        )
        assert isinstance(adapter, FlowMatchingODEAdapterWithObservation)

    def test_v2_satisfies_protocol(self) -> None:
        """v2 instance satisfies ``FlowMatchingODEAdapterWithObservation``.

        The v2 adapter is imported here (not as a fixture) because
        v2 is constructed by :func:`default_flowmol3adapter` which is
        not exercised by the v1 test file. We construct it with the
        default numpy backend so the constructor does not require
        torch or upstream FlowMol3 source.
        """
        from adaptive_reflow.adapters.flowmol3_v2_adapter import (
            FlowMol3V2Adapter,
        )
        from adaptive_reflow.framework.interfaces import (
            FlowMatchingODEAdapterWithObservation,
        )
        v2 = FlowMol3V2Adapter(backend="numpy", num_steps=5)
        assert isinstance(v2, FlowMatchingODEAdapterWithObservation)

    def test_v1_byte_stable_after_protocol_add(self, adapter) -> None:
        """Adding the Protocol does NOT change v1's byte-stable surface.

        Verifies the three byte-stable artefacts:

        * :meth:`build_initial_state` initial digest for
          ``(batch_id="d4-b41", sample_id="d4-s41")`` matches
          ``flowmol3:e4ebda97374ef94f`` (D.4 vector condition 1).
        * :meth:`solve_ode` trace digest matches the D.4 vector for
          seed=41, nfe=5 (``flowmol3:ccf1613bd1d00bfc``).
        * :meth:`solve_ode` integrator config hash matches the D.4
          vector for seed=41, nfe=5 (``flowmol3:458e224249527046``).

        These SHAs are derived from ``_make_tensor_ref`` (flowmol3.py
        line 286) using the deterministic
        ``repr((label, sorted(parts.items())))`` encoding. The Protocol
        addition only added a structural declaration; it did not
        modify any method body.
        """
        # Initial state digest for D.4 condition 1 (seed=41).
        bundle = adapter.build_initial_state(
            batch_id="d4-b41", sample_id="d4-s41"
        )
        assert str(bundle.native_state_digest) == "flowmol3:e4ebda97374ef94f"

        # Trace digests for D.4 condition 1 (seed=41, nfe=5).
        cond = ODEConditionDelta(
            delta_spec={"num_steps": 5},
            source="test_wave54_byte_stable",
            target_round=1,
            calibration_artifact_hash="a" * 64,
        )
        trace = adapter.solve_ode(bundle, cond, seed=41)
        assert str(trace.native_state_digest) == "flowmol3:ccf1613bd1d00bfc"
        assert (
            str(trace.integrator_config_hash)
            == "flowmol3:458e224249527046"
        )

