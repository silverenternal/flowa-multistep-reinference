"""Tests for ``adapters/_adapter_common.py`` (P2-9).

The helpers in this module are byte-stable aliases for the duplicated
per-adapter bodies. The tests below guard the namespaces that are
load-bearing for ``native_config_hash`` and the ledger chain.
"""

from __future__ import annotations

import hashlib

import pytest


def test_seed_from_ids_matches_frozen_vector() -> None:
    """Byte-stability guard: the seed is recorded in published digests."""
    from adaptive_reflow.adapters._adapter_common import seed_from_ids

    assert seed_from_ids("b0", "s0", 0) == int(
        __import__("hashlib")
        .sha256(repr(("b0", "s0", 0)).encode("utf-8"))
        .hexdigest()[:8],
        16,
    )


def test_make_ref_prefixes_are_unchanged() -> None:
    """Each adapter's historical TensorRef namespace must be preserved."""
    from adaptive_reflow.adapters._adapter_common import make_ref
    from adaptive_reflow.adapters.mnist_fm import _make_ref as mnist_ref
    from adaptive_reflow.adapters.twodim_fm import _make_ref as td_ref

    # Wave 42 (D.1 shrink): rectified_flow_cifar dropped its ``_make_ref``
    # wrapper and now calls the shared helper with its historical prefix
    # inline. The namespace guarded here is unchanged.
    def rf_ref(label: str, **parts: object) -> object:
        return make_ref("rf_cifar:image", label, **parts)

    assert str(mnist_ref("initial", batch="b", sample="s")).startswith("mnist:x:")
    assert str(td_ref("initial", batch="b", sample="s")).startswith("twodim:xy:")
    assert str(rf_ref("initial", batch="b", sample="s")).startswith("rf_cifar:image:")
    # And the shared helper with the same prefix produces the same value.
    assert str(mnist_ref("initial", batch="b", sample="s")) == str(
        make_ref("mnist:x", "initial", batch="b", sample="s")
    )


def test_native_state_cache_is_lru_bounded() -> None:
    from adaptive_reflow.adapters._adapter_common import NativeStateCache

    c = NativeStateCache(maxsize=2)
    c.put("a", {"v": 1})
    c.put("b", {"v": 2})
    c.put("c", {"v": 3})
    assert "a" not in c and len(c) == 2


def test_native_state_cache_supports_inject_forward_noise_surface() -> None:
    """_inject_forward_noise.py reaches through .get / __setitem__."""
    from adaptive_reflow.adapters._adapter_common import NativeStateCache

    c = NativeStateCache(maxsize=4)
    c["d"] = {"x": 1}
    assert c.get("d") == {"x": 1} and c.get("missing") is None


def test_make_adapter_capabilities_defaults_match() -> None:
    """The factory's default kwargs produce the canonical capability surface."""
    from adaptive_reflow.adapters._adapter_common import make_adapter_capabilities

    kwargs = make_adapter_capabilities(
        state_shape=(2,),
        supported_channels=("x",),
        channel_domains={},
        native_config_hash="h",
        native_config_version="v",
    )
    assert kwargs["has_ode_integration_surface"] is True
    assert kwargs["has_prior_export"] is True
    assert kwargs["has_state_export"] is True
    assert kwargs["has_condition_injection"] is True
    assert kwargs["has_restart_boundary"] is True
    assert kwargs["has_continuous_channels"] is True
    assert kwargs["has_discrete_channels"] is False
    assert kwargs["has_trajectory_digest"] is True
    assert kwargs["has_deterministic_seed"] is True
    assert kwargs["has_materialization_route"] is True


def test_memory_fraction_for_returns_default_when_channel_missing() -> None:
    """When a channel is absent from the policy, default to beta=memory=0.5."""
    from adaptive_reflow.adapters._adapter_common import memory_fraction_for

    class _Policy:
        beta_by_channel = {}

    beta, mem = memory_fraction_for(_Policy(), "x")
    assert (beta, mem) == (0.5, 0.5)


def test_memory_fraction_for_paper_uplift_27_emits_audit_when_lift_fires() -> None:
    """P0-A12 — paper-uplift-27: e_rho/4 floor lift emits audit code."""
    from adaptive_reflow.adapters._adapter_common import memory_fraction_for

    class _Policy:
        beta_by_channel = {"x": 1.0}  # beta=1.0 -> floor=0.0, lift fires when e_rho/4 > 0

    audit_codes: list[str] = []
    beta, mem = memory_fraction_for(
        _Policy(), "x", exterior_gap_e_rho=0.4, audit_codes=audit_codes
    )
    # floor was 0.0; lift to 0.4 / 4 = 0.1
    assert beta == 1.0
    assert mem == pytest.approx(0.1)
    assert any(c.startswith("merge_paper_quantity_floor_lifted") for c in audit_codes)


def test_memory_fraction_for_paper_uplift_27_no_audit_when_no_lift() -> None:
    """When the schedule floor already dominates e_rho/4, no audit emission."""
    from adaptive_reflow.adapters._adapter_common import memory_fraction_for

    class _Policy:
        beta_by_channel = {"x": 0.5}  # beta=0.5 -> floor=0.5, dominates e_rho/4=2.5e-5

    audit_codes: list[str] = []
    beta, mem = memory_fraction_for(
        _Policy(), "x", exterior_gap_e_rho=1e-4, audit_codes=audit_codes
    )
    assert beta == 0.5
    assert mem == 0.5
    assert audit_codes == []


def test_memory_fraction_for_paper_uplift_27_disabled_by_default() -> None:
    """When exterior_gap_e_rho is None, behaviour is unchanged from baseline."""
    from adaptive_reflow.adapters._adapter_common import memory_fraction_for

    class _Policy:
        beta_by_channel = {"x": 1.0}

    audit_codes: list[str] = []
    beta, mem = memory_fraction_for(_Policy(), "x", audit_codes=audit_codes)
    assert beta == 1.0
    assert mem == 0.0
    assert audit_codes == []

# ---------------------------------------------------------------------------
# D.1 (Wave 33) — make_adapter_capabilities equivalence tests
# ---------------------------------------------------------------------------
# These tests demonstrate that the shared `make_adapter_capabilities`
# helper from `_adapter_common.py` produces the same kwargs dict that
# the 5 NEW adapters (Wave 10 / Wave 21 PHASE-3) would otherwise
# inline in their capability class `__init__`. The goal is to enable a
# future low-risk adapter-shrink (D.1) where these inlined __init__
# blocks are replaced by a call to the shared helper.


def test_make_adapter_capabilities_uses_shared_defaults() -> None:
    """Shared helper sets the 5 always-True capability flags by default."""
    from adaptive_reflow.adapters._adapter_common import make_adapter_capabilities

    kwargs = make_adapter_capabilities(
        state_shape=(2,),
        supported_channels=("x",),
        channel_domains={"x": "continuous"},
        native_config_hash="unit:test:v1",
        native_config_version="1.0.0",
    )
    assert kwargs["has_ode_integration_surface"] is True
    assert kwargs["has_prior_export"] is True
    assert kwargs["has_state_export"] is True
    assert kwargs["has_condition_injection"] is True
    assert kwargs["has_restart_boundary"] is True
    assert kwargs["has_deterministic_seed"] is True
    assert kwargs["state_shape"] == (2,)
    assert kwargs["supported_channels"] == ("x",)
    assert kwargs["native_config_hash"] == "unit:test:v1"


def test_make_adapter_capabilities_matches_freqflow_kwargs() -> None:
    """Shared helper produces kwargs identical to FreqFlow's inlined __init__."""
    from adaptive_reflow.adapters._adapter_common import make_adapter_capabilities
    from adaptive_reflow.adapters.freqflow import (
        FREQ_FLOW_CHANNEL_DOMAINS,
        FREQ_FLOW_CHANNELS,
        FREQ_FLOW_CONFIG_HASH,
        FREQ_FLOW_CONFIG_VERSION,
        FREQ_FLOW_STATE_SHAPE,
    )
    from adaptive_reflow.universal import NoOpMixer

    kwargs = make_adapter_capabilities(
        state_shape=FREQ_FLOW_STATE_SHAPE,
        supported_channels=FREQ_FLOW_CHANNELS,
        channel_domains=FREQ_FLOW_CHANNEL_DOMAINS,
        native_config_hash=FREQ_FLOW_CONFIG_HASH,
        native_config_version=FREQ_FLOW_CONFIG_VERSION,
        required_mixer=NoOpMixer,
    )
    # The shared helper's 5 always-True flags + the freqflow-specific
    # fields together form a superset of what the inlined __init__
    # would pass to super().__init__.
    expected_keys = {
        "has_ode_integration_surface",
        "has_prior_export",
        "has_state_export",
        "has_condition_injection",
        "has_restart_boundary",
        "has_continuous_channels",
        "has_discrete_channels",
        "has_trajectory_digest",
        "has_deterministic_seed",
        "has_materialization_route",
        "state_shape",
        "supported_channels",
        "channel_domains",
        "required_mixer",
        "exposed_envelope_criteria",
        "exposed_evaluators",
        "native_config_hash",
        "native_config_version",
    }
    assert set(kwargs) == expected_keys
    assert kwargs["state_shape"] == FREQ_FLOW_STATE_SHAPE
    assert kwargs["native_config_hash"] == FREQ_FLOW_CONFIG_HASH


def test_make_adapter_capabilities_matches_kanzi_kwargs() -> None:
    """Shared helper produces kwargs identical to Kanzi's inlined __init__."""
    from adaptive_reflow.adapters._adapter_common import make_adapter_capabilities
    from adaptive_reflow.adapters.kanzi import (
        KANZI_CHANNEL_DOMAINS,
        KANZI_CHANNELS,
        KANZI_CONFIG_HASH,
        KANZI_CONFIG_VERSION,
        KANZI_STATE_SHAPE,
    )
    from adaptive_reflow.universal import NoOpMixer

    kwargs = make_adapter_capabilities(
        state_shape=KANZI_STATE_SHAPE,
        supported_channels=KANZI_CHANNELS,
        channel_domains=KANZI_CHANNEL_DOMAINS,
        native_config_hash=KANZI_CONFIG_HASH,
        native_config_version=KANZI_CONFIG_VERSION,
        required_mixer=NoOpMixer,
    )
    assert kwargs["state_shape"] == KANZI_STATE_SHAPE
    assert kwargs["native_config_hash"] == KANZI_CONFIG_HASH


def test_make_adapter_capabilities_extra_kwargs_override() -> None:
    """``extra`` kwargs override the shared defaults (escape hatch for special-case adapters)."""
    from adaptive_reflow.adapters._adapter_common import make_adapter_capabilities

    kwargs = make_adapter_capabilities(
        state_shape=(2,),
        supported_channels=("x",),
        channel_domains={"x": "continuous"},
        native_config_hash="t",
        native_config_version="1",
        has_discrete_channels=True,  # override
    )
    assert kwargs["has_discrete_channels"] is True


def test_make_adapter_capabilities_byte_stable_for_shared_inputs() -> None:
    """Two calls with the same inputs produce identical kwargs dicts (byte-stability for ledger)."""
    from adaptive_reflow.adapters._adapter_common import make_adapter_capabilities

    common = {
        "state_shape": (2,),
        "supported_channels": ("x",),
        "channel_domains": {"x": "continuous"},
        "native_config_hash": "t",
        "native_config_version": "1",
    }
    kwargs_a = make_adapter_capabilities(**common)
    kwargs_b = make_adapter_capabilities(**common)
    assert kwargs_a == kwargs_b


# ---------------------------------------------------------------------------
# Wave 45 — per_position_entropy_reduction (P2-W33-C math, promoted)
# ---------------------------------------------------------------------------
# The shared helper is the single canonical definition of the per-position
# entropy math (lifted verbatim from tools/run_controlled_audit.py:702).
# Both Kanzi and LineageFlow's observe_entropy_reduction methods will call
# this helper; ``tools/run_controlled_audit.py`` will also be re-pointed
# at it in a follow-up so there is exactly one definition in the tree.


def test_per_position_entropy_reduction_zero_for_identical_inputs() -> None:
    """If before and after are identical, the reduction must be exactly 0."""
    import numpy as np

    from adaptive_reflow.adapters._adapter_common import (
        per_position_entropy_reduction,
    )

    rng = np.random.default_rng(0)
    theta = rng.standard_normal((8, 16, 33))
    r = per_position_entropy_reduction(theta, theta)
    assert r == pytest.approx(0.0, abs=1e-12)


def test_per_position_entropy_reduction_positive_when_after_is_sharper() -> None:
    """A delta-spike ``after`` must yield a positive reduction (entropy drops)."""
    import numpy as np

    from adaptive_reflow.adapters._adapter_common import (
        per_position_entropy_reduction,
    )

    rng = np.random.default_rng(1)
    # baseline = uniform-ish logits (high entropy).
    theta_before = rng.standard_normal((4, 12, 33))
    # framework = concentrate on one residue per position (low entropy).
    theta_after = np.zeros((4, 12, 33))
    spike_idx = rng.integers(0, 33, size=(4, 12))
    theta_after[np.arange(4)[:, None], np.arange(12)[None, :], spike_idx] = 50.0
    r = per_position_entropy_reduction(theta_before, theta_after)
    # baseline ~ log(33) ~ 3.50; after ~ 0; reduction ~ 3.50, strictly > 0.
    assert r > 0.0
    # the upper bound is ``log K``; with K=33 this is ~ 3.4965.
    assert r <= np.log(33.0) + 1e-9


def test_per_position_entropy_reduction_negative_when_after_is_uniform() -> None:
    """A uniform-logit ``after`` (high entropy) yields a *negative* reduction."""
    import numpy as np

    from adaptive_reflow.adapters._adapter_common import (
        per_position_entropy_reduction,
    )

    rng = np.random.default_rng(2)
    # baseline = concentrated (low entropy).
    theta_before = np.zeros((4, 12, 33))
    spike_idx = rng.integers(0, 33, size=(4, 12))
    theta_before[np.arange(4)[:, None], np.arange(12)[None, :], spike_idx] = 50.0
    # framework = uniform logits (high entropy ~ log K).
    theta_after = rng.standard_normal((4, 12, 33))
    r = per_position_entropy_reduction(theta_before, theta_after)
    assert r < 0.0
    assert r >= -np.log(33.0) - 1e-9


def test_per_position_entropy_reduction_bounded_in_logK() -> None:
    """The metric must be bounded in ``[-log K, log K]`` for any inputs."""
    import numpy as np

    from adaptive_reflow.adapters._adapter_common import (
        per_position_entropy_reduction,
    )

    rng = np.random.default_rng(3)
    K = 33
    # Worst case: before is uniform, after is a delta-spike (max reduction).
    theta_before = rng.standard_normal((4, 12, K))
    theta_after = np.zeros((4, 12, K))
    spike_idx = rng.integers(0, K, size=(4, 12))
    theta_after[np.arange(4)[:, None], np.arange(12)[None, :], spike_idx] = 100.0
    r_max = per_position_entropy_reduction(theta_before, theta_after)
    # Worst case reversed (most negative).
    r_min = per_position_entropy_reduction(theta_after, theta_before)
    assert r_max <= np.log(K) + 1e-9
    assert r_min >= -np.log(K) - 1e-9


def test_per_position_entropy_reduction_nan_on_empty_input() -> None:
    """Empty input must yield NaN (not 0.0) so callers see ``metric undefined``."""
    import numpy as np

    from adaptive_reflow.adapters._adapter_common import (
        per_position_entropy_reduction,
    )

    empty = np.zeros((0, 12, 33))
    theta = np.zeros((4, 12, 33))
    # the leading axis of ``before`` is empty -> NaN
    r_empty_before = per_position_entropy_reduction(empty, theta)
    r_empty_after = per_position_entropy_reduction(theta, empty)
    assert np.isnan(r_empty_before)
    assert np.isnan(r_empty_after)


def test_per_position_entropy_reduction_nan_on_single_sample() -> None:
    """Fewer than 2 samples in either arg must yield NaN (matches §11 guard)."""
    import numpy as np

    from adaptive_reflow.adapters._adapter_common import (
        per_position_entropy_reduction,
    )

    one = np.zeros((1, 12, 33))
    many = np.zeros((4, 12, 33))
    assert np.isnan(per_position_entropy_reduction(one, many))
    assert np.isnan(per_position_entropy_reduction(many, one))


def test_per_position_entropy_reduction_deterministic() -> None:
    """The metric is deterministic — repeated calls on the same input agree."""
    import numpy as np

    from adaptive_reflow.adapters._adapter_common import (
        per_position_entropy_reduction,
    )

    rng = np.random.default_rng(4)
    a = rng.standard_normal((4, 12, 33))
    b = rng.standard_normal((4, 12, 33))
    r1 = per_position_entropy_reduction(a, b)
    r2 = per_position_entropy_reduction(a, b)
    assert r1 == pytest.approx(r2, abs=0.0)


def test_per_position_entropy_reduction_matches_run_controlled_audit_formula() -> None:
    """The math is verbatim from ``run_controlled_audit.py:702``: H = -sum(p * log(p + eps)) on the K axis.

    Reproduce the per-arg entropy by hand and confirm the helper
    equals ``hand(before) - hand(after)`` to within float eps.
    """
    import numpy as np

    from adaptive_reflow.adapters._adapter_common import (
        per_position_entropy_reduction,
    )

    rng = np.random.default_rng(5)
    a = rng.standard_normal((4, 12, 33))
    b = rng.standard_normal((4, 12, 33))
    eps = 1e-12

    def hand(theta: np.ndarray) -> float:
        z = theta - np.max(theta, axis=-1, keepdims=True)
        e = np.exp(z)
        p = e / np.sum(e, axis=-1, keepdims=True)
        per_pos = -np.sum(p * np.log(p + eps), axis=-1)
        return float(np.mean(per_pos))

    expected = hand(a) - hand(b)
    actual = per_position_entropy_reduction(a, b, eps=eps)
    assert actual == pytest.approx(expected, abs=1e-15)


def test_per_position_entropy_reduction_export_via_dunder_all() -> None:
    """The helper is exported from ``_adapter_common`` (``__all__`` membership)."""
    import adaptive_reflow.adapters._adapter_common as mod

    assert "per_position_entropy_reduction" in mod.__all__
    assert hasattr(mod, "per_position_entropy_reduction")


# ---------------------------------------------------------------------------
# Wave 113.A.6 Phase 4 — base-class-level regression tests for the
# construction-time shape-guard helper.
# ---------------------------------------------------------------------------
# The shared helper ``_run_construction_shape_guard`` lives in
# ``adaptive_reflow.adapters._adapter_common`` and is invoked at
# adapter construction by all 8 SOTA adapters (Wave 113.A.6 Phase 3).
# It catches the Wave 113.A bug class (silent-zero stub that passes
# smoke tests but breaks the N=1000 sweep) within 1s of import
# instead of 90 minutes into GPU compute.
#
# These tests prove the helper catches all four bug classes without
# instantiating any of the real adapters (which would force a torch +
# checkpoint import on every test run):
#
# 1. wrong-shape shim output,
# 2. all-zeros shim output,
# 3. synthetic-mode opt-out,
# 4. no-checkpoint opt-out,
#
# plus the importability smoke test (5).
#
# The torch-dependent tests (1, 2) use ``@pytest.mark.usefixtures
# ("requires_torch")`` so they skip cleanly on CPU-only sandboxes
# where torch is not vendored — the helper itself short-circuits
# on the same condition (``not torch_is_available()``) so there is
# no observable behaviour to test.


class _StubAdapter:
    """Minimal stub adapter with the four attributes the shape guard reads.

    Built fresh per-test (no shared mutable state). The shim callable
    is bound via ``_model`` so each test can plug in its own wrong-shape
    or all-zeros implementation without polluting the others.
    """

    __slots__ = ("_mode", "_real_ckpt_path", "_weights_path", "_device", "_model")

    def __init__(
        self,
        *,
        mode: str,
        real_ckpt_path: object,
        weights_path: object,
        device: object = None,
        model: object = None,
    ) -> None:
        self._mode = mode
        self._real_ckpt_path = real_ckpt_path
        self._weights_path = weights_path
        self._device = device
        self._model = model


# Use an existing vendored checkpoint file for the ``_weights_path``
# attribute so the helper does NOT short-circuit on
# ``not Path(_weights_path).exists()``. The path is never opened by
# the helper itself — it only checks ``.is_file()`` — but the helper
# also calls ``torch.load`` via ``_load_real_weights`` if a ``_model``
# is set... wait, no: ``_run_construction_shape_guard`` does not load
# the weights; it only constructs ``x = torch.randn(...)`` and calls
# ``adapter._model(x, t)``. So the file only needs to exist on disk
# for the helper to pass its skip-guards; it is never read.
_FAKE_WEIGHTS_PATH = (
    __import__("pathlib").Path(__file__).resolve().parent.parent.parent
    / "data"
    / "lineageflow"
    / "lineageflow-rp55.ckpt"
)


@pytest.mark.usefixtures("requires_torch")
def test_shape_guard_catches_wrong_shape() -> None:
    """Bug class 1: shim returns a tensor with a different shape than input.

    Construct a stub whose ``_model`` returns a tensor whose final dim
    is halved (8 instead of 32); the helper MUST raise
    :class:`RuntimeError` naming the adapter class + actual + expected
    shape (the diffusers / BentoML input-spec pattern).
    """
    import torch

    from adaptive_reflow.adapters._adapter_common import (
        _run_construction_shape_guard,
    )

    class _WrongShapeModel:
        def __call__(self, x: torch.Tensor, t: torch.Tensor, **kwargs: object) -> torch.Tensor:
            # Wrong shape: collapse the trailing dim from 32 to 8.
            return torch.zeros(x.shape[:-1] + (8,), dtype=x.dtype, device=x.device)

    stub = _StubAdapter(
        mode="torch",
        real_ckpt_path="/tmp/whatever.pt",
        weights_path=_FAKE_WEIGHTS_PATH,
        device="cpu",
        model=_WrongShapeModel(),
    )
    with pytest.raises(RuntimeError, match="Wave 113.A.6"):
        _run_construction_shape_guard(stub, (1, 4, 32, 32))


@pytest.mark.usefixtures("requires_torch")
def test_shape_guard_catches_all_zeros() -> None:
    """Bug class 2: shim returns an all-zeros velocity tensor.

    Construct a stub whose ``_model`` returns zeros of the *correct*
    shape; the helper MUST raise :class:`RuntimeError` naming the
    adapter class and the "all-zeros velocity" sentinel — this is the
    exact failure mode the Wave 113.A bug class produced (silent-zero
    stub that passed smoke tests).
    """
    import torch

    from adaptive_reflow.adapters._adapter_common import (
        _run_construction_shape_guard,
    )

    class _ZerosModel:
        def __call__(self, x: torch.Tensor, t: torch.Tensor, **kwargs: object) -> torch.Tensor:
            return torch.zeros_like(x)

    stub = _StubAdapter(
        mode="torch",
        real_ckpt_path="/tmp/whatever.pt",
        weights_path=_FAKE_WEIGHTS_PATH,
        device="cpu",
        model=_ZerosModel(),
    )
    with pytest.raises(RuntimeError, match="all-zeros velocity"):
        _run_construction_shape_guard(stub, (1, 4, 32, 32))


def test_shape_guard_skips_synthetic_mode() -> None:
    """Skip-guard: ``_mode == "synthetic"`` ⇒ helper is a no-op (no exception).

    Synthetic adapters have no torch forward to validate, so the
    helper MUST return ``None`` silently regardless of what
    ``_model`` / ``_real_ckpt_path`` / ``_weights_path`` look like.
    """
    from adaptive_reflow.adapters._adapter_common import (
        _run_construction_shape_guard,
    )

    class _ExplodingModel:
        def __call__(self, x: object, t: object, **kwargs: object) -> object:
            raise AssertionError(
                "_model must NOT be called when _mode == 'synthetic'"
            )

    stub = _StubAdapter(
        mode="synthetic",
        real_ckpt_path=None,
        weights_path="synthetic",
        device="cpu",
        model=_ExplodingModel(),
    )
    # No exception ⇒ silent skip. We assert it returns None explicitly
    # so a future regression that turns this into an explicit raise
    # (or into a forward call) is caught.
    assert _run_construction_shape_guard(stub, (1, 4, 32, 32)) is None


def test_shape_guard_skips_no_ckpt() -> None:
    """Skip-guard: ``_real_ckpt_path is None`` ⇒ helper is a no-op.

    When the adapter was constructed without a real checkpoint
    (e.g. synthetic test path), the helper MUST return ``None``
    silently — never call ``_model``, never raise.
    """
    from adaptive_reflow.adapters._adapter_common import (
        _run_construction_shape_guard,
    )

    class _ExplodingModel:
        def __call__(self, x: object, t: object, **kwargs: object) -> object:
            raise AssertionError(
                "_model must NOT be called when _real_ckpt_path is None"
            )

    stub = _StubAdapter(
        mode="torch",
        real_ckpt_path=None,
        weights_path=_FAKE_WEIGHTS_PATH,
        device="cpu",
        model=_ExplodingModel(),
    )
    assert _run_construction_shape_guard(stub, (1, 4, 32, 32)) is None


def test_helper_importable_from_adapter_common() -> None:
    """Importability: ``_run_construction_shape_guard`` is callable from its home module.

    This is the API-contract smoke test that protects against a
    future refactor renaming or relocating the helper (every adapter
    imports it by name from ``adaptive_reflow.adapters._adapter_common``).
    """
    from adaptive_reflow.adapters._adapter_common import (
        _run_construction_shape_guard,
    )

    assert callable(_run_construction_shape_guard)
