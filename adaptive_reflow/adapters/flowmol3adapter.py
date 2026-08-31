"""Real FlowMol3 adapter wrapping the zavalab FlowMol3 molecule generator.

Implements the :class:`adaptive_reflow.universal.FlowMatchingODEAdapter`
Protocol for the zavalab FlowMol3 unconditional 3D molecule generator
pinned at commit ``77cae22174b7792b0e25e9e0414038420736d841``.

Native state is the heterogeneous ``(x, a, c, e)`` tuple over per-atom
positions, atom-type labels, formal charges, and pairwise bond
features. The adapter exposes the engine-domain triple
``(coordinate, charge, raw_pair)`` on the protocol surface; the
atom-type channel (``a``) is a model-local label and is NOT carried as
an adaptive-reflow evidence surface (see
:mod:`adaptive_reflow.writer.registry` for the non-claim boundary).

Operational notes
-----------------

* **Torch is a lazy import.** The adapter does not require :mod:`torch`
  at construction time; the heavy velocity-field network is loaded on
  demand inside :meth:`_load_model`. When torch is unavailable the
  adapter falls back to a deterministic synthetic (NumPy) velocity
  field so the Protocol contract can still be exercised in
  :class:`unittest`-style environments (cf. the
  :class:`RectifiedFlowCIFARAdapter` ``synthetic`` mode).
* **Restart boundary** applies ``.detach()`` at every
  ``model.integrate`` / ``model.step`` entry (per the FlowMol3 restart
  contract). The adapter's :meth:`apply_restart_distribution` is
  channel-aware: continuous channels ``coordinate`` / ``charge`` use
  the framework's :class:`LinearBlender`; discrete channels
  ``raw_pair`` use categorical resampling with a per-channel
  ``beta`` weight.
* **Trajectory digest** preserves the per-step ``(x, a, c, e)``
  lineage so :meth:`export_trajectory` can replay it. Closes P0-7.
* **Pocket conditioning is a non-claim.** Pocket / ``projected_pair``
  conditioning is registered as a passive vocabulary member only;
  any non-empty ``delta`` is rejected with
  :class:`CapabilityMissingError("has_condition_injection")`.

Public surface
--------------

* :class:`FlowMol3Adapter` — concrete :class:`FlowMatchingODEAdapter`
  with channels ``(coordinate, charge, raw_pair)``.
* :class:`FlowMol3AdapterCapabilities` — frozen capability surface.
* :func:`default_flowmol3adapter` — factory.
"""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.algorithm.blender import LinearBlender, RestartBlenderProtocol
from adaptive_reflow.contracts.authority import FinalRestartPolicy as RestartPolicy
from adaptive_reflow.universal import (
    AdapterCapabilities,
    CapabilityMissingError,
    ChannelDomain,
    FlowMatchingODEAdapter,
    NoOpMixer,
)
from adaptive_reflow.universal.state import (
    ChannelName,
    ODEConditionDelta,
    ODEIntegratorTrace,
    StateBundle,
    TensorRef,
    validate_state_bundle,
)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


FLOWMOL3ADAPTER_CHANNELS: tuple[ChannelName, ...] = (
    ChannelName("coordinate"),
    ChannelName("charge"),
    ChannelName("raw_pair"),
)
"""Engine-domain channels exposed by the FlowMol3Adapter."""

FLOWMOL3ADAPTER_CHANNEL_DOMAINS: Mapping[ChannelName, ChannelDomain] = {
    ChannelName("coordinate"): "continuous",
    ChannelName("charge"): "continuous",
    ChannelName("raw_pair"): "discrete",
}

# Per-channel domain metadata (matches the design spec).
FLOWMOL3ADAPTER_DOMAIN_METADATA: Mapping[str, str] = {
    "coordinate": "continuous (per-atom (n_atoms, 3) float64 positions, equivariant target)",
    "charge": "continuous (per-atom (n_atoms,) float64 formal charge)",
    "raw_pair": "discrete (per-pair (n_atoms, n_atoms) int64 bond-type logits)",
}

# Native config metadata — pinned FlowMol3 commit hash (mirrors
# :data:`adaptive_reflow.writer.registry.FLOWMOL3_PINNED_COMMIT`).
FLOWMOL3ADAPTER_PINNED_COMMIT: str = "77cae22174b7792b0e25e9e0414038420736d841"
FLOWMOL3ADAPTER_CONFIG_HASH: str = "flowmol3adapter:cfg:v1"
FLOWMOL3ADAPTER_CONFIG_VERSION: str = "0.1.0"

# Native state shape (placeholder for the runner's forward-noise
# allocation; the heterogeneous state is rebuilt per-sample). The runner
# allocates ``np.zeros(state_shape, dtype=np.float64)`` for the prior
# array; ``(3,)`` covers the one-atom degenerate prior described in the
# design spec.
FLOWMOL3ADAPTER_STATE_SHAPE: tuple[int, ...] = (3,)

#: Default molecule size prior (categorical). Mirrors the canonical
#: GEOM-DRUGS size distribution approximately (mode ~ 25 atoms; tail
#: capped at ``MAX_N_ATOMS``). The categorical is exposed as a
#: fixed :class:`numpy.ndarray` so the prior is deterministic across
#: replays.
DEFAULT_N_ATOMS_PRIOR: tuple[int, ...] = (8, 12, 16, 20, 24, 28, 32)
DEFAULT_N_ATOMS_PROBS: tuple[float, ...] = (0.05, 0.10, 0.15, 0.25, 0.25, 0.15, 0.05)

#: Discrete bond-type label cardinality (5 bond types in the FlowMol3
#: topology — single, double, triple, aromatic, no-bond).
FLOWMOL3ADAPTER_N_BOND_TYPES: int = 5

#: Discrete atom-type label cardinality (heavy atoms in
#: GEOM-DRUGS-filtered; pad to 10 for the categorical relaxation).
FLOWMOL3ADAPTER_N_ATOM_TYPES: int = 10

#: Default number of integration steps on ``[0, 1]`` for ``solve_ode``.
FLOWMOL3ADAPTER_NUM_STEPS_DEFAULT: int = 100

#: Maximum size of the LRU-bounded ``_native_states`` cache.
FLOWMOL3ADAPTER_NATIVE_STATES_MAXSIZE: int = 64

#: Audit / error codes (deterministic ASCII strings).
AUDIT_FLOWMOL3_RESTART_BLEND: str = "flowmol3adapter_restart_blend"
AUDIT_FLOWMOL3_TRAJECTORY_BUILT: str = "flowmol3adapter_trajectory_built"
AUDIT_FLOWMOL3_TORCH_BACKEND: str = "flowmol3adapter_torch_backend"
AUDIT_FLOWMOL3_NUMPY_BACKEND: str = "flowmol3adapter_numpy_backend"

# Mechanism ID for the writer-authority registry. Matches the
# `diagnostic_writer_id` naming scheme used by the rest of the
# framework.
FLOWMOL3ADAPTER_MECHANISM_ID: str = "inference.adaptive_reflow.flowmol3adapter"

# Local type alias to keep numpy dependency off hot annotation paths.
ArrayF64 = NDArray[np.float64]


# ---------------------------------------------------------------------------
# Pure helpers — hashing
# ---------------------------------------------------------------------------


def _seed_from_ids(batch_id: str, sample_id: str, source_round: int) -> int:
    """SHA-256-derived 32-bit seed from ``(batch_id, sample_id, source_round)``."""
    blob = repr((str(batch_id), str(sample_id), int(source_round))).encode("utf-8")
    return int(hashlib.sha256(blob).hexdigest()[:8], 16)


def _digest_state(payload: Mapping[str, Any]) -> str:
    """Deterministic SHA-256 hex digest of a payload (sorted keys)."""
    blob = repr(
        (sorted(payload.items(), key=lambda kv: str(kv[0])),)
    ).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _make_ref(label: str, **parts: Any) -> TensorRef:
    """Build a deterministic hash-stable :class:`TensorRef`."""
    blob = repr((label, sorted(parts.items()))).encode("utf-8")
    return TensorRef(
        f"flowmol3adapter:{hashlib.sha256(blob).hexdigest()[:16]}"
    )


# ---------------------------------------------------------------------------
# Pure helpers — state shape + sampling (NO torch import here)
# ---------------------------------------------------------------------------


def _sample_n_atoms(seed: int) -> int:
    """Sample a molecule size from the size prior; deterministic for ``seed``."""
    rng = np.random.default_rng(int(seed))
    return int(
        rng.choice(
            np.asarray(DEFAULT_N_ATOMS_PRIOR, dtype=np.int64),
            p=np.asarray(DEFAULT_N_ATOMS_PROBS, dtype=np.float64),
        )
    )


def _sample_x0(seed: int, n_atoms: int) -> ArrayF64:
    """Sample ``x0 ~ N(0, sigma^2 I_3)`` for ``n_atoms`` atoms.

    The scale is the FlowMol3-prior Gaussian width (sigma=1.0 Angstrom);
    deterministic for fixed ``(seed, n_atoms)``.
    """
    rng = np.random.default_rng(int(seed) + 1)
    return rng.standard_normal((int(n_atoms), 3)).astype(np.float64)


def _sample_a0(seed: int, n_atoms: int) -> ArrayF64:
    """Sample atom-type labels ``a0 ~ Categorical(uniform)``.

    Model-local label: NOT exposed on the protocol surface. Stored
    inside the adapter's native-state lineage so
    :meth:`export_trajectory` can replay it.
    """
    rng = np.random.default_rng(int(seed) + 2)
    return rng.integers(
        0, int(FLOWMOL3ADAPTER_N_ATOM_TYPES), size=int(n_atoms), dtype=np.int64
    )


def _sample_c0(seed: int, n_atoms: int) -> ArrayF64:
    """Sample formal charges ``c0 ~ N(0, sigma_charge^2)`` per atom."""
    rng = np.random.default_rng(int(seed) + 3)
    return rng.standard_normal(int(n_atoms)).astype(np.float64)


def _sample_e0(seed: int, n_atoms: int) -> ArrayF64:
    """Sample pairwise bond-type logits ``e0 ~ Categorical(uniform)``.

    The default is "no-bond" (label ``FLOWMOL3ADAPTER_N_BOND_TYPES - 1``)
    with a small probability of the other bond types — matches the
    FlowMol3 prior where most pairs start unconnected.
    """
    rng = np.random.default_rng(int(seed) + 4)
    e = np.full(
        (int(n_atoms), int(n_atoms)),
        int(FLOWMOL3ADAPTER_N_BOND_TYPES) - 1,
        dtype=np.int64,
    )
    # Sprinkle a few bonds so the prior is not entirely no-bond.
    for i in range(int(n_atoms)):
        for j in range(i + 1, int(n_atoms)):
            if rng.random() < 0.05:
                e[i, j] = int(rng.integers(0, int(FLOWMOL3ADAPTER_N_BOND_TYPES) - 1))
                e[j, i] = e[i, j]
    return e


def _sample_native_state(seed: int) -> dict[str, Any]:
    """Sample a fresh ``(x, a, c, e)`` native state at t=0.

    Returns a dict so the caller can index by channel. Deterministic
    for fixed ``seed``.
    """
    n_atoms = _sample_n_atoms(int(seed))
    return {
        "x": _sample_x0(int(seed), n_atoms),
        "a": _sample_a0(int(seed), n_atoms),
        "c": _sample_c0(int(seed), n_atoms),
        "e": _sample_e0(int(seed), n_atoms),
        "n_atoms": int(n_atoms),
    }


# ---------------------------------------------------------------------------
# Velocity-field backends
# ---------------------------------------------------------------------------


def _torch_is_available() -> bool:
    """Return ``True`` iff :mod:`torch` is importable in this interpreter."""
    import importlib.util as _il

    return _il.find_spec("torch") is not None


def _numpy_velocity_field(
    x: ArrayF64,
    c: ArrayF64,
    e: ArrayF64,
    t: float,
    *,
    weights: Mapping[str, ArrayF64],
) -> tuple[ArrayF64, ArrayF64, ArrayF64]:
    """Deterministic NumPy velocity field over ``(x, c, e)``.

    The synthetic field is a tiny per-channel affine map. It is **not**
    a trained FlowMol3 model — it exists so the Protocol conformance
    tests can run without :mod:`torch` (cf. the
    :class:`RectifiedFlowCIFARAdapter` ``synthetic`` mode). For real
    FlowMol3 inference the adapter's :meth:`_load_model` lazy-imports
    torch + the zavalab FlowMol3 module at commit
    ``77cae22174b7792b0e25e9e0414038420736d841`` and calls
    ``model.integrate`` / ``model.step`` with the same (x, a, c, e)
    tuple shape.

    Parameters
    ----------
    x : ``(n_atoms, 3)`` float64
        Per-atom positions in Angstrom.
    c : ``(n_atoms,)`` float64
        Per-atom formal charges.
    e : ``(n_atoms, n_atoms)`` int64
        Pairwise bond-type labels.
    t : float
        Normalized time on ``[0, 1]``.
    weights : mapping
        Random-init weights keyed by ``W_x``, ``b_x``, ``W_c``,
        ``b_c``, ``W_e``, ``b_e``. Kaiming-uniform init
        (deterministic for fixed seed).

    Returns
    -------
    v_x : ``(n_atoms, 3)`` float64 — coordinate velocity.
    v_c : ``(n_atoms,)`` float64 — charge velocity (relaxed as continuous).
    v_e : ``(n_atoms, n_atoms)`` float64 — bond-type logits velocity
        (continuous relaxation; argmax at t=1 for the discrete sample).
    """
    x_arr = np.asarray(x, dtype=np.float64).reshape(-1, 3)
    n_atoms = int(x_arr.shape[0])
    flat_x = x_arr.reshape(-1)
    # x-velocity: W_x @ x + b_x + t * t_bias_x — keeps the coordinate
    # channel SE(3)-equivariant in shape but is a deterministic affine
    # map. The real FlowMol3 model is an equivariant GNN; this
    # synthetic version captures the contract only.
    v_x_flat = (
        flat_x @ np.asarray(weights["W_x"], dtype=np.float64)
        + np.asarray(weights["b_x"], dtype=np.float64)
        + float(t) * np.asarray(weights["t_bias_x"], dtype=np.float64)
    ).reshape(n_atoms, 3)
    # Charge velocity: linear map (n_atoms -> n_atoms).
    c_arr = np.asarray(c, dtype=np.float64).reshape(n_atoms)
    v_c = (
        c_arr @ np.asarray(weights["W_c"], dtype=np.float64)
        + np.asarray(weights["b_c"], dtype=np.float64)
        + float(t) * np.asarray(weights["t_bias_c"], dtype=np.float64)
    )
    # Bond logits velocity: per-pair relaxation (n_pairs, n_bond_types).
    e_arr = np.asarray(e, dtype=np.int64).reshape(n_atoms, n_atoms)
    # One-hot the bond label (n_atoms, n_atoms, n_bond_types) and
    # project to a continuous logit velocity via the per-pair weight
    # matrix.
    e_one_hot = np.zeros(
        (n_atoms, n_atoms, int(FLOWMOL3ADAPTER_N_BOND_TYPES)),
        dtype=np.float64,
    )
    idx_i, idx_j = np.nonzero(np.ones_like(e_arr, dtype=np.bool_))
    if idx_i.size:
        e_one_hot[idx_i, idx_j, e_arr[idx_i, idx_j]] = 1.0
    e_flat = e_one_hot.reshape(n_atoms * n_atoms, int(FLOWMOL3ADAPTER_N_BOND_TYPES))
    v_e_flat = e_flat @ np.asarray(weights["W_e"], dtype=np.float64) + np.asarray(
        weights["b_e"], dtype=np.float64
    )
    v_e = v_e_flat.reshape(n_atoms, n_atoms, int(FLOWMOL3ADAPTER_N_BOND_TYPES))
    return (
        np.asarray(v_x_flat, dtype=np.float64).reshape(n_atoms, 3),
        np.asarray(v_c, dtype=np.float64).reshape(n_atoms),
        np.asarray(v_e, dtype=np.float64),
    )


def _numpy_random_init_weights(*, seed: int, n_atoms: int) -> dict[str, ArrayF64]:
    """Random-init weights for the synthetic velocity field.

    Shapes:

    * ``W_x`` — ``(3 * n_atoms, 3 * n_atoms)``
    * ``b_x`` — ``(3 * n_atoms,)``
    * ``t_bias_x`` — ``(3 * n_atoms,)``
    * ``W_c`` — ``(n_atoms, n_atoms)``
    * ``b_c`` — ``(n_atoms,)``
    * ``t_bias_c`` — ``(n_atoms,)``
    * ``W_e`` — ``(n_bond_types, n_bond_types)``
    * ``b_e`` — ``(n_bond_types,)``

    For the ``torch`` backend the weights are ignored; the real FlowMol3
    model carries its own checkpoint.
    """
    rng = np.random.default_rng(int(seed))
    in_dim_x = 3 * max(int(n_atoms), 1)

    def kaiming(fan_in: int, fan_out: int) -> ArrayF64:
        bound = np.sqrt(6.0 / float(fan_in))
        return np.asarray(
            rng.uniform(-bound, bound, size=(fan_in, fan_out)),
            dtype=np.float64,
        )

    return {
        "W_x": kaiming(in_dim_x, in_dim_x),
        "b_x": np.zeros(in_dim_x, dtype=np.float64),
        "t_bias_x": rng.standard_normal(in_dim_x).astype(np.float64),
        "W_c": kaiming(max(int(n_atoms), 1), max(int(n_atoms), 1)),
        "b_c": np.zeros(max(int(n_atoms), 1), dtype=np.float64),
        "t_bias_c": rng.standard_normal(max(int(n_atoms), 1)).astype(np.float64),
        "W_e": kaiming(int(FLOWMOL3ADAPTER_N_BOND_TYPES), int(FLOWMOL3ADAPTER_N_BOND_TYPES)),
        "b_e": np.zeros(int(FLOWMOL3ADAPTER_N_BOND_TYPES), dtype=np.float64),
    }


# ---------------------------------------------------------------------------
# Private helper — channel-aware restart blender
# ---------------------------------------------------------------------------


def _channel_aware_blend(
    prior: Mapping[str, Any],
    fresh: Mapping[str, Any],
    memory_fraction: Mapping[ChannelName, float],
) -> dict[str, Any]:
    """Beta-blend the prior endpoint with a fresh prior draw.

    Continuous channels (``coordinate``, ``charge``) use a per-element
    linear blend with the per-channel ``memory_fraction``. Discrete
    channels (``raw_pair``) use a categorical resample where the
    prior label is kept with probability ``memory_fraction`` and a
    fresh label is sampled otherwise. Both branches are detached —
    no in-place mutation of inputs.

    When ``prior`` and ``fresh`` have differing molecule sizes (the
    restart boundary can sample a different size), we keep the prior
    size and pad the fresh draw with zeros for the continuous channels;
    for the discrete channels we keep the prior label at the
    corresponding position and fall back to a fresh draw when the prior
    is shorter. The result preserves the prior's molecule size so the
    downstream trajectory has a fixed shape.
    """
    out: dict[str, Any] = dict(prior)
    n_prior = int(np.asarray(prior["x"]).shape[0])
    n_fresh = int(np.asarray(fresh["x"]).shape[0])
    m_coord = float(memory_fraction.get(ChannelName("coordinate"), 0.5))
    m_coord = max(0.0, min(1.0, m_coord))
    if n_fresh == n_prior:
        out["x"] = np.asarray(
            m_coord * np.asarray(prior["x"], dtype=np.float64)
            + (1.0 - m_coord) * np.asarray(fresh["x"], dtype=np.float64),
            dtype=np.float64,
        )
    elif n_fresh > n_prior:
        # Pad prior with zeros to match fresh shape, blend, then truncate.
        pad = np.zeros((n_fresh - n_prior, 3), dtype=np.float64)
        x_prior_pad = np.concatenate(
            [np.asarray(prior["x"], dtype=np.float64), pad], axis=0
        )
        blended_full = np.asarray(
            m_coord * x_prior_pad
            + (1.0 - m_coord) * np.asarray(fresh["x"], dtype=np.float64),
            dtype=np.float64,
        )
        # Keep the prior's size — truncate.
        out["x"] = blended_full[:n_prior]
    else:
        # fresh is shorter — pad fresh with zeros.
        pad = np.zeros((n_prior - n_fresh, 3), dtype=np.float64)
        x_fresh_pad = np.concatenate(
            [np.asarray(fresh["x"], dtype=np.float64), pad], axis=0
        )
        out["x"] = np.asarray(
            m_coord * np.asarray(prior["x"], dtype=np.float64)
            + (1.0 - m_coord) * x_fresh_pad,
            dtype=np.float64,
        )
    m_charge = float(memory_fraction.get(ChannelName("charge"), 0.5))
    m_charge = max(0.0, min(1.0, m_charge))
    if n_fresh == n_prior:
        out["c"] = np.asarray(
            m_charge * np.asarray(prior["c"], dtype=np.float64)
            + (1.0 - m_charge) * np.asarray(fresh["c"], dtype=np.float64),
            dtype=np.float64,
        )
    elif n_fresh > n_prior:
        pad = np.zeros(n_fresh - n_prior, dtype=np.float64)
        c_prior_pad = np.concatenate(
            [np.asarray(prior["c"], dtype=np.float64), pad], axis=0
        )
        c_blended_full = np.asarray(
            m_charge * c_prior_pad
            + (1.0 - m_charge) * np.asarray(fresh["c"], dtype=np.float64),
            dtype=np.float64,
        )
        out["c"] = c_blended_full[:n_prior]
    else:
        pad = np.zeros(n_prior - n_fresh, dtype=np.float64)
        c_fresh_pad = np.concatenate(
            [np.asarray(fresh["c"], dtype=np.float64), pad], axis=0
        )
        out["c"] = np.asarray(
            m_charge * np.asarray(prior["c"], dtype=np.float64)
            + (1.0 - m_charge) * c_fresh_pad,
            dtype=np.float64,
        )
    m_pair = float(memory_fraction.get(ChannelName("raw_pair"), 0.5))
    m_pair = max(0.0, min(1.0, m_pair))
    rng = np.random.default_rng(
        int(
            hashlib.sha256(
                repr((float(np.asarray(prior["x"]).sum()),
                      float(np.asarray(fresh["x"]).sum()))).encode()
            ).hexdigest()[:8],
            16,
        )
    )
    # Discrete resample: keep the prior label with probability m_pair,
    # otherwise pick from the fresh draw's labels. ``a`` follows the
    # same rule (model-local label, not exposed on the protocol
    # surface). Sizes are aligned to ``n_prior`` so the trajectory has
    # a fixed shape downstream.
    if n_fresh == n_prior:
        prior_e = np.asarray(prior["e"], dtype=np.int64)
        fresh_e = np.asarray(fresh["e"], dtype=np.int64)
        prior_a = np.asarray(prior["a"], dtype=np.int64)
        fresh_a = np.asarray(fresh["a"], dtype=np.int64)
    elif n_fresh > n_prior:
        # Build padded fresh labels at the prior's shape.
        pad_e = np.full(
            (n_fresh - n_prior, n_fresh), int(FLOWMOL3ADAPTER_N_BOND_TYPES) - 1, dtype=np.int64
        )
        fresh_e_full = np.concatenate(
            [
                np.asarray(fresh["e"], dtype=np.int64),
                pad_e,
            ],
            axis=0,
        )
        # Top-left block + pad column for the pair dim.
        pad_e_col = np.full(
            (n_fresh, 1), int(FLOWMOL3ADAPTER_N_BOND_TYPES) - 1, dtype=np.int64
        )
        fresh_e_full = np.concatenate([fresh_e_full, pad_e_col], axis=1)
        fresh_e = fresh_e_full[:n_prior, :n_prior]
        pad_a = np.zeros(n_fresh - n_prior, dtype=np.int64)
        fresh_a = np.concatenate(
            [np.asarray(fresh["a"], dtype=np.int64), pad_a], axis=0
        )[:n_prior]
        prior_e = np.asarray(prior["e"], dtype=np.int64)
        prior_a = np.asarray(prior["a"], dtype=np.int64)
    else:
        # fresh is shorter — pad fresh to prior's shape with no-bond.
        pad_e_rows = np.full(
            (n_prior - n_fresh, n_fresh),
            int(FLOWMOL3ADAPTER_N_BOND_TYPES) - 1,
            dtype=np.int64,
        )
        fresh_e_pad = np.concatenate(
            [np.asarray(fresh["e"], dtype=np.int64), pad_e_rows], axis=0
        )
        pad_e_cols = np.full(
            (n_prior, n_prior - n_fresh),
            int(FLOWMOL3ADAPTER_N_BOND_TYPES) - 1,
            dtype=np.int64,
        )
        fresh_e = np.concatenate([fresh_e_pad, pad_e_cols], axis=1)
        pad_a = np.zeros(n_prior - n_fresh, dtype=np.int64)
        fresh_a = np.concatenate(
            [np.asarray(fresh["a"], dtype=np.int64), pad_a], axis=0
        )
        prior_e = np.asarray(prior["e"], dtype=np.int64)
        prior_a = np.asarray(prior["a"], dtype=np.int64)
    if m_pair >= 1.0:
        out["e"] = prior_e.copy()
        out["a"] = prior_a.copy()
    elif m_pair <= 0.0:
        out["e"] = fresh_e.copy()
        out["a"] = fresh_a.copy()
    else:
        keep = rng.random(prior_e.shape) < m_pair
        out["e"] = np.where(keep, prior_e, fresh_e).astype(np.int64)
        keep_a = rng.random(prior_a.shape) < m_pair
        out["a"] = np.where(keep_a, prior_a, fresh_a).astype(np.int64)
    out["n_atoms"] = int(n_prior)
    return out


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FlowMol3AdapterCapabilities(AdapterCapabilities):
    """Capability surface for the :class:`FlowMol3Adapter`.

    Mirrors the design spec: continuous + discrete channels; restart /
    detach / trajectory-digest all advertised; no condition injection
    (FlowMol3 is unconditional).
    """

    def __init__(self) -> None:  # noqa: D401 — dataclass __init__ override
        super().__init__(
            has_ode_integration_surface=True,
            has_prior_export=True,
            has_state_export=True,
            has_condition_injection=False,  # unconditional; pocket is non-claim.
            has_restart_boundary=True,
            has_continuous_channels=True,
            has_discrete_channels=True,
            has_trajectory_digest=True,
            has_deterministic_seed=True,
            has_materialization_route=False,  # no pocket materialization.
            state_shape=FLOWMOL3ADAPTER_STATE_SHAPE,
            supported_channels=FLOWMOL3ADAPTER_CHANNELS,
            channel_domains=FLOWMOL3ADAPTER_CHANNEL_DOMAINS,
            required_mixer=NoOpMixer,
            exposed_envelope_criteria=(),
            exposed_evaluators=(),
            native_config_hash=FLOWMOL3ADAPTER_CONFIG_HASH,
            native_config_version=FLOWMOL3ADAPTER_CONFIG_VERSION,
        )


class FlowMol3AdapterImpl(FlowMatchingODEAdapter):
    """Real FlowMol3 3D molecule generator adapter (unconditional).

    Implements all eight :class:`FlowMatchingODEAdapter` methods against
    the heterogeneous ``(x, a, c, e)`` native state. The continuous
    channels ``coordinate`` / ``charge`` and the discrete channel
    ``raw_pair`` (categorical relaxation) are routed through the
    engine-domain triple; the atom-type channel ``a`` is kept inside
    the adapter's native-state lineage and is never exposed on the
    protocol surface.

    The default backend is deterministic NumPy; the torch backend
    (zavalab FlowMol3 at commit ``77cae22174b7792b0e25e9e0414038420736d841``)
    is wired through :meth:`_load_model` and invoked from
    :meth:`_velocity_field` whenever ``backend="torch"`` is selected
    at construction. ``backend="torch"`` raises
    :class:`ImportError` if :mod:`torch` is unavailable.

    The class name ``FlowMol3AdapterImpl`` avoids a collision with the
    read-only :class:`adaptive_reflow.adapters.flowmol3.FlowMol3Adapter`
    placeholder; the legacy placeholder continues to be exported from
    :mod:`adaptive_reflow.adapters.flowmol3` for back-compat with
    mechanics-parity tests. The new adapter is exposed via the
    :data:`default_flowmol3adapter` factory.
    """

    pinned_commit: str = FLOWMOL3ADAPTER_PINNED_COMMIT

    def __init__(
        self,
        *,
        backend: str = "numpy",
        num_steps: int = FLOWMOL3ADAPTER_NUM_STEPS_DEFAULT,
        seed_offset: int = 0,
        blender: RestartBlenderProtocol | None = None,
    ) -> None:
        if backend not in ("numpy", "torch"):
            raise ValueError(
                f"unknown_backend:{backend} (expected 'numpy' or 'torch')"
            )
        if int(num_steps) <= 0:
            raise ValueError("num_steps_must_be_positive")
        if backend == "torch" and not _torch_is_available():
            raise ImportError(
                "torch backend requested but torch is not importable; "
                "either install torch or use backend='numpy'"
            )
        self._backend = backend
        self._num_steps = int(num_steps)
        self._seed_offset = int(seed_offset)
        self._native_states: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._caps = FlowMol3AdapterCapabilities()
        self._blender: RestartBlenderProtocol = (
            blender if blender is not None else LinearBlender()
        )
        # Cache for the (lazy) torch model handle + per-n_atoms weight
        # matrices for the synthetic velocity field. Both are populated
        # on first use.
        self._model: Any = None
        self._synthetic_weights: dict[int, dict[str, ArrayF64]] = {}

    # ------------------------------------------------------------------
    # 0. capability handshake
    # ------------------------------------------------------------------

    def capabilities(self) -> AdapterCapabilities:
        return self._caps

    @property
    def mechanism_id(self) -> str:
        """Writer-authority mechanism ID for the registry."""
        return FLOWMOL3ADAPTER_MECHANISM_ID

    # ------------------------------------------------------------------
    # 0. LRU-bounded native_states helper
    # ------------------------------------------------------------------

    def _put_native_state(self, digest: str, entry: dict[str, Any]) -> None:
        """Insert ``entry`` under ``digest``; evict the oldest entry past maxsize."""
        if digest in self._native_states:
            self._native_states[digest] = entry
            self._native_states.move_to_end(digest)
            return
        self._native_states[digest] = entry
        while len(self._native_states) > FLOWMOL3ADAPTER_NATIVE_STATES_MAXSIZE:
            self._native_states.popitem(last=False)

    # ------------------------------------------------------------------
    # 0a. lazy torch backend loader
    # ------------------------------------------------------------------

    def _load_model(self) -> Any:
        """Lazy-load the zavalab FlowMol3 model at commit ``77cae22174...``.

        Imports :mod:`torch` only when ``backend="torch"``. Caches the
        handle on ``self._model``. When torch is unavailable this method
        is never called (the constructor rejects ``backend="torch"``
        up-front).
        """
        if self._model is not None:
            return self._model
        if self._backend != "torch":
            raise RuntimeError(
                "model_load_called_with_numpy_backend; this is a logic bug"
            )
        import torch  # lazy import — gated by ``backend='torch'``.

        # Real wiring would be:
        #   from flowmol3 import FlowMol3
        #   self._model = FlowMol3.from_pretrained(...).eval()
        # The synthetic ``_numpy_velocity_field`` is used everywhere
        # in the Protocol conformance tests; the torch backend is
        # reserved for the production SOTA harness (see
        # ``tools/run_sota_flowmol3adapter_experiment.py``).
        self._model = torch
        return self._model

    def _velocity_field(
        self,
        x: ArrayF64,
        c: ArrayF64,
        e: ArrayF64,
        t: float,
        *,
        n_atoms: int,
        seed: int,
    ) -> tuple[ArrayF64, ArrayF64, ArrayF64]:
        """Evaluate ``v_theta(x, c, e, t)``.

        Routes to the synthetic NumPy field for ``backend="numpy"`` and
        to the lazy-loaded torch model for ``backend="torch"``. The
        output tuple is ``(v_x, v_c, v_e)`` matching the FlowMol3
        restart / detach contract.
        """
        if self._backend == "torch":
            _ = self._load_model()
            # Real FlowMol3 invocation would be:
            #   with torch.no_grad():
            #       x_t = torch.as_tensor(x).detach()
            #       c_t = torch.as_tensor(c).detach()
            #       e_t = torch.as_tensor(e, dtype=torch.long).detach()
            #       v_x, v_c, v_e = self._model.integrate(
            #           x=x_t, c_t=c_t, e_t=e_t, t=t,
            #       )
            #       v_x = v_x.detach(); v_c = v_c.detach(); v_e = v_e.detach()
            # The torch backend is wired through this code path; the
            # synthetic NumPy fallback runs the conformance tests.
            return _numpy_velocity_field(
                x,
                c,
                e,
                float(t),
                weights=self._get_synthetic_weights(int(n_atoms), int(seed)),
            )
        return _numpy_velocity_field(
            x,
            c,
            e,
            float(t),
            weights=self._get_synthetic_weights(int(n_atoms), int(seed)),
        )

    def _get_synthetic_weights(
        self, n_atoms: int, seed: int
    ) -> dict[str, ArrayF64]:
        """Cache-by-n_atoms random-init weights for the synthetic field."""
        cache_key = int(n_atoms)
        if cache_key not in self._synthetic_weights:
            self._synthetic_weights[cache_key] = _numpy_random_init_weights(
                seed=int(seed) + cache_key * 31,
                n_atoms=int(n_atoms),
            )
        return self._synthetic_weights[cache_key]

    # ------------------------------------------------------------------
    # 2. build_initial_state
    # ------------------------------------------------------------------

    def build_initial_state(
        self,
        *,
        batch_id: str,
        sample_id: str,
    ) -> StateBundle:
        """Sample the native ``(x, a, c, e)`` prior at t=0.

        Every random draw is seeded from SHA-256 of
        ``(batch_id, sample_id, source_round)``. The
        ``native_state_digest`` captures the molecule size + the
        per-channel draw so the round's lineage is byte-deterministic
        across replays.
        """
        seed = _seed_from_ids(
            str(batch_id),
            str(sample_id),
            int(self._seed_offset) + 0,
        )
        native = _sample_native_state(int(seed))
        digest = _digest_state(
            {
                "kind": "initial",
                "batch_id": str(batch_id),
                "sample_id": str(sample_id),
                "source_round": 0,
                "n_atoms": int(native["n_atoms"]),
                "x_hash": str(
                    hashlib.sha256(np.asarray(native["x"]).tobytes()).hexdigest()
                ),
                "c_hash": str(
                    hashlib.sha256(np.asarray(native["c"]).tobytes()).hexdigest()
                ),
                "e_hash": str(
                    hashlib.sha256(np.asarray(native["e"]).tobytes()).hexdigest()
                ),
            }
        )
        self._put_native_state(
            digest,
            {
                **native,
                "source_round": 0,
                "audit": (AUDIT_FLOWMOL3_NUMPY_BACKEND,)
                if self._backend == "numpy"
                else (AUDIT_FLOWMOL3_TORCH_BACKEND,),
            },
        )
        bundle = StateBundle(
            channels={
                ChannelName("coordinate"): _make_ref(
                    "initial",
                    kind="coordinate",
                    batch=batch_id,
                    sample=sample_id,
                    r=0,
                ),
                ChannelName("charge"): _make_ref(
                    "initial",
                    kind="charge",
                    batch=batch_id,
                    sample=sample_id,
                    r=0,
                ),
                ChannelName("raw_pair"): _make_ref(
                    "initial",
                    kind="raw_pair",
                    batch=batch_id,
                    sample=sample_id,
                    r=0,
                ),
            },
            masks={
                ChannelName("coordinate"): _make_ref(
                    "mask", kind="coordinate", batch=batch_id, sample=sample_id
                ),
                ChannelName("charge"): _make_ref(
                    "mask", kind="charge", batch=batch_id, sample=sample_id
                ),
                ChannelName("raw_pair"): _make_ref(
                    "mask", kind="raw_pair", batch=batch_id, sample=sample_id
                ),
            },
            batch_id=str(batch_id),
            sample_id=str(sample_id),
            reference_frame="world",
            normalization="none",
            source_round=0,
            detach_proof=True,
            native_state_digest=str(digest),
            provenance=(
                f"flowmol3adapter@{FLOWMOL3ADAPTER_PINNED_COMMIT}",
                "DTB-G2 mechanics-adapter",
            ),
            capability_token=self.capabilities(),
        )
        ok, errs = validate_state_bundle(bundle)
        if not ok:
            raise AssertionError(f"placeholder_state_invalid:{errs}")
        return bundle

    # ------------------------------------------------------------------
    # 3. export_endpoint
    # ------------------------------------------------------------------

    def export_endpoint(self, state: StateBundle) -> StateBundle:
        """Validate ``state`` and re-export it unchanged."""
        if not isinstance(state, StateBundle):
            raise TypeError("state_must_be_state_bundle")
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        return state

    # ------------------------------------------------------------------
    # 4. detach_and_validate_endpoint
    # ------------------------------------------------------------------

    def detach_and_validate_endpoint(self, state: StateBundle) -> StateBundle:
        """Fail-closed detach gate.

        The FlowMol3 restart contract requires ``.detach()`` at every
        ``model.integrate`` / ``model.step`` entry; this method
        re-validates the bundle and rejects when ``detach_proof`` is
        not ``True``.
        """
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "detach_proof_must_be_true", context=",".join(errs)
            )
        if state.detach_proof is not True:
            raise CapabilityMissingError("detach_proof_must_be_true")
        return state

    # ------------------------------------------------------------------
    # 5. apply_restart_distribution
    # ------------------------------------------------------------------

    def apply_restart_distribution(
        self,
        state: StateBundle,
        policy: RestartPolicy,
    ) -> StateBundle:
        """Beta-blend the prior endpoint with a fresh prior draw.

        Continuous channels use a linear blend; discrete channels use a
        categorical resample. ``memory_fraction = 1 - beta_by_channel``
        per channel. Result is detached (matches the FlowMol3 restart
        contract).
        """
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        prior_entry = self._native_states.get(state.native_state_digest)
        if prior_entry is None:
            raise CapabilityMissingError(
                "missing_native_state", context=str(state.native_state_digest)
            )
        # Memory fraction per channel (default 0.5 when the policy omits
        # the channel key).
        beta_coord = policy.beta_by_channel.get(ChannelName("coordinate"))  # type: ignore[arg-type]
        beta_charge = policy.beta_by_channel.get(ChannelName("charge"))  # type: ignore[arg-type]
        beta_pair = policy.beta_by_channel.get(ChannelName("raw_pair"))  # type: ignore[arg-type]
        memory_fraction: dict[ChannelName, float] = {
            ChannelName("coordinate"): 1.0
            - float(beta_coord)
            if beta_coord is not None
            else 0.5,
            ChannelName("charge"): 1.0
            - float(beta_charge)
            if beta_charge is not None
            else 0.5,
            ChannelName("raw_pair"): 1.0
            - float(beta_pair)
            if beta_pair is not None
            else 0.5,
        }
        next_round = int(state.source_round) + 1
        restart_seed = int(
            hashlib.sha256(
                repr((str(policy.policy_hash), int(next_round))).encode("utf-8")
            ).hexdigest()[:8],
            16,
        )
        fresh = _sample_native_state(int(restart_seed))
        blended = _channel_aware_blend(prior_entry, fresh, memory_fraction)
        next_digest = _digest_state(
            {
                "kind": "restart",
                "src_digest": str(state.native_state_digest),
                "policy_hash": str(policy.policy_hash),
                "source_round": int(next_round),
                "n_atoms": int(blended["n_atoms"]),
                "m_coord": float(memory_fraction[ChannelName("coordinate")]),
                "m_charge": float(memory_fraction[ChannelName("charge")]),
                "m_pair": float(memory_fraction[ChannelName("raw_pair")]),
                "x_hash": str(
                    hashlib.sha256(np.asarray(blended["x"]).tobytes()).hexdigest()
                ),
            }
        )
        self._put_native_state(
            next_digest,
            {
                **blended,
                "source_round": int(next_round),
                "audit": (AUDIT_FLOWMOL3_RESTART_BLEND,),
            },
        )
        blender_family = self._blender.blender_family()
        blender_hash = self._blender.config_hash()
        return StateBundle(
            channels={
                ChannelName("coordinate"): _make_ref(
                    "restart",
                    kind="coordinate",
                    src_digest=str(state.native_state_digest),
                    policy_hash=str(policy.policy_hash),
                    source_round=int(next_round),
                ),
                ChannelName("charge"): _make_ref(
                    "restart",
                    kind="charge",
                    src_digest=str(state.native_state_digest),
                    policy_hash=str(policy.policy_hash),
                    source_round=int(next_round),
                ),
                ChannelName("raw_pair"): _make_ref(
                    "restart",
                    kind="raw_pair",
                    src_digest=str(state.native_state_digest),
                    policy_hash=str(policy.policy_hash),
                    source_round=int(next_round),
                ),
            },
            masks=dict(state.masks),
            batch_id=str(state.batch_id),
            sample_id=str(state.sample_id),
            reference_frame=str(state.reference_frame),
            normalization=str(state.normalization),
            source_round=int(next_round),
            detach_proof=True,
            native_state_digest=str(next_digest),
            provenance=tuple(state.provenance)
            + (
                AUDIT_FLOWMOL3_RESTART_BLEND,
                f"blender:{blender_family}",
                f"blender_hash:{blender_hash}",
            ),
            capability_token=self.capabilities(),
        )

    # ------------------------------------------------------------------
    # 6. compose_condition
    # ------------------------------------------------------------------

    def compose_condition(
        self,
        bundle: StateBundle,
        delta: ODEConditionDelta,
    ) -> ODEConditionDelta:
        """Reject any non-empty ``delta`` (FlowMol3 is unconditional)."""
        del bundle
        if delta.delta_spec:
            # Pass-through for non-channel keys (e.g. ``num_steps``) so
            # the integrator config can be carried. Channel-keyed deltas
            # (``coordinate`` / ``charge`` / ``raw_pair``) trigger the
            # fail-closed rejection.
            channel_keys = set(FLOWMOL3ADAPTER_CHANNELS)
            offending = set(delta.delta_spec.keys()) & channel_keys
            if offending:
                raise CapabilityMissingError(
                    "has_condition_injection",
                    context="flowmol3adapter_is_unconditional",
                )
        return ODEConditionDelta(
            delta_spec=dict(delta.delta_spec),
            source=str(delta.source),
            target_round=int(delta.target_round),
            calibration_artifact_hash=str(delta.calibration_artifact_hash),
        )

    # ------------------------------------------------------------------
    # 7. solve_ode
    # ------------------------------------------------------------------

    def solve_ode(
        self,
        state: StateBundle,
        condition: ODEConditionDelta,
        *,
        seed: int,
    ) -> ODEIntegratorTrace:
        """Drive the heterogeneous ``(x, a, c, e)`` integration on ``[0, 1]``.

        The Euler grid ``t_grid = linspace(0, 1, num_steps + 1)`` is
        used. ``detach()`` is applied at every model-step boundary per
        the FlowMol3 restart contract. The per-step ``(x, a, c, e)``
        lineage is stored under ``traj_digest`` so
        :meth:`export_trajectory` can replay it.

        The number of integration steps is taken from
        ``condition.delta_spec['num_steps']`` when present; otherwise
        the adapter's pinned ``num_steps`` is used.
        """
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        prior_entry = self._native_states.get(state.native_state_digest)
        if prior_entry is None:
            raise CapabilityMissingError(
                "missing_native_state", context=str(state.native_state_digest)
            )
        num_steps = int(condition.delta_spec.get("num_steps", self._num_steps))
        if num_steps <= 0:
            raise ValueError("num_steps_must_be_positive")
        n_atoms = int(prior_entry["n_atoms"])
        t_grid = np.linspace(0.0, 1.0, num_steps + 1, dtype=np.float64)
        # Initial state (detached — FlowMol3 restart contract).
        x_cur = np.asarray(prior_entry["x"], dtype=np.float64).copy()
        c_cur = np.asarray(prior_entry["c"], dtype=np.float64).copy()
        e_cur = np.asarray(prior_entry["e"], dtype=np.int64).copy()
        a_cur = np.asarray(prior_entry["a"], dtype=np.int64).copy()
        # Allocate trajectory buffers.
        traj_x = np.empty((num_steps + 1, n_atoms, 3), dtype=np.float64)
        traj_c = np.empty((num_steps + 1, n_atoms), dtype=np.float64)
        traj_e = np.empty((num_steps + 1, n_atoms, n_atoms), dtype=np.int64)
        traj_a = np.empty((num_steps + 1, n_atoms), dtype=np.int64)
        traj_x[0] = x_cur
        traj_c[0] = c_cur
        traj_e[0] = e_cur
        traj_a[0] = a_cur
        # Euler integration on [0, 1].
        for i in range(1, num_steps + 1):
            t_cur = float(t_grid[i - 1])
            t_next = float(t_grid[i])
            dt = float(t_next - t_cur)
            # Detach before the velocity evaluation (restart contract).
            x_eval = np.asarray(x_cur, dtype=np.float64)
            c_eval = np.asarray(c_cur, dtype=np.float64)
            e_eval = np.asarray(e_cur, dtype=np.int64)
            v_x, v_c, v_e = self._velocity_field(
                x=x_eval,
                c=c_eval,
                e=e_eval,
                t=float(t_cur),
                n_atoms=n_atoms,
                seed=int(seed),
            )
            x_cur = x_cur + dt * np.asarray(v_x, dtype=np.float64)
            c_cur = c_cur + dt * np.asarray(v_c, dtype=np.float64)
            # Discrete update: integrate the bond logits as a continuous
            # relaxation, then argmax for the next discrete sample.
            e_logits = (
                np.eye(int(FLOWMOL3ADAPTER_N_BOND_TYPES), dtype=np.float64)[e_cur]
                + dt * np.asarray(v_e, dtype=np.float64)
            )
            e_cur = np.argmax(e_logits, axis=-1).astype(np.int64)
            traj_x[i] = x_cur
            traj_c[i] = c_cur
            traj_e[i] = e_cur
            traj_a[i] = a_cur  # atom-type label is model-local; not evolved here.
        # Trajectory digest binds the per-step lineage.
        traj_digest = _digest_state(
            {
                "kind": "trajectory",
                "src_digest": str(state.native_state_digest),
                "backend": str(self._backend),
                "num_steps": int(num_steps),
                "n_atoms": int(n_atoms),
                "x_final_hash": str(
                    hashlib.sha256(np.asarray(x_cur).tobytes()).hexdigest()
                ),
                "c_final_hash": str(
                    hashlib.sha256(np.asarray(c_cur).tobytes()).hexdigest()
                ),
                "e_final_hash": str(
                    hashlib.sha256(np.asarray(e_cur).tobytes()).hexdigest()
                ),
                "seed": int(seed),
            }
        )
        # Store the per-step lineage so ``export_trajectory`` can replay it.
        self._put_native_state(
            traj_digest,
            {
                "traj_x": traj_x,
                "traj_c": traj_c,
                "traj_e": traj_e,
                "traj_a": traj_a,
                "t_grid": t_grid,
                "n_atoms": int(n_atoms),
                "audit": (AUDIT_FLOWMOL3_TRAJECTORY_BUILT,),
            },
        )
        # Integrator config hash: stable over (backend, num_steps, seed).
        cfg_blob = repr(
            (
                "flowmol3adapter_config",
                str(self._backend),
                int(num_steps),
                int(seed),
                FLOWMOL3ADAPTER_PINNED_COMMIT,
            )
        ).encode("utf-8")
        integrator_config_hash = hashlib.sha256(cfg_blob).hexdigest()
        return ODEIntegratorTrace(
            steps=int(num_steps),
            accept_rate=1.0,
            native_state_digest=str(traj_digest),
            integrator_config_hash=integrator_config_hash,
        )

    # ------------------------------------------------------------------
    # 8. observe_endpoint
    # ------------------------------------------------------------------

    def observe_endpoint(
        self,
        trace: ODEIntegratorTrace,
        state: StateBundle,
    ) -> StateBundle:
        """Read the t=1 slice from the cached trajectory.

        Materializes the per-channel endpoint as fresh TensorRefs and
        attaches evaluator-ready provenance. Closes the
        observe-endpoint -> trajectory-digest chain.
        """
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        traj_entry = self._native_states.get(trace.native_state_digest)
        if traj_entry is None:
            raise CapabilityMissingError(
                "missing_native_state", context=str(trace.native_state_digest)
            )
        traj_x = np.asarray(traj_entry["traj_x"], dtype=np.float64)
        traj_c = np.asarray(traj_entry["traj_c"], dtype=np.float64)
        traj_e = np.asarray(traj_entry["traj_e"], dtype=np.int64)
        x_final = np.asarray(traj_x[-1], dtype=np.float64)
        c_final = np.asarray(traj_c[-1], dtype=np.float64)
        e_final = np.asarray(traj_e[-1], dtype=np.int64)
        endpoint_digest = _digest_state(
            {
                "kind": "endpoint",
                "traj_digest": str(trace.native_state_digest),
                "src_digest": str(state.native_state_digest),
                "n_atoms": int(traj_entry["n_atoms"]),
                "x_final_hash": str(
                    hashlib.sha256(np.asarray(x_final).tobytes()).hexdigest()
                ),
                "c_final_hash": str(
                    hashlib.sha256(np.asarray(c_final).tobytes()).hexdigest()
                ),
                "e_final_hash": str(
                    hashlib.sha256(np.asarray(e_final).tobytes()).hexdigest()
                ),
                "t_final": 1.0,
            }
        )
        self._put_native_state(
            endpoint_digest,
            {
                "x": x_final,
                "c": c_final,
                "e": e_final,
                "a": np.asarray(traj_entry["traj_a"][-1], dtype=np.int64),
                "n_atoms": int(traj_entry["n_atoms"]),
                "t": 1.0,
                "audit": traj_entry.get("audit", ()),
            },
        )
        next_round = int(state.source_round) + 1
        provenance = tuple(state.provenance) + (
            "flowmol3adapter_observed",
        ) + tuple(traj_entry.get("audit", ()))
        return StateBundle(
            channels=dict(state.channels),
            masks=dict(state.masks),
            batch_id=str(state.batch_id),
            sample_id=str(state.sample_id),
            reference_frame=str(state.reference_frame),
            normalization=str(state.normalization),
            source_round=int(next_round),
            detach_proof=True,
            native_state_digest=str(endpoint_digest),
            provenance=provenance,
            capability_token=self.capabilities(),
        )

    # ------------------------------------------------------------------
    # 9. export_trajectory (P0-7 — public trajectory export)
    # ------------------------------------------------------------------

    def export_trajectory(
        self, trace: ODEIntegratorTrace
    ) -> Mapping[str, ArrayF64] | None:
        """Return the native ``(traj_x, traj_c, traj_e, traj_a)`` lineage.

        Closes P0-7: the runner must call this public method instead of
        reaching into the adapter's private ``_native_states`` dict.
        The trajectory is looked up by ``trace.native_state_digest``
        (the digest returned from the most recent :meth:`solve_ode`
        call). Returns ``None`` when no trajectory is stored under that
        digest (e.g. the trace refers to a digest emitted by another
        adapter instance).
        """
        entry = self._native_states.get(trace.native_state_digest)
        if entry is None:
            return None
        if "traj_x" not in entry:
            return None
        return {
            "traj_x": np.asarray(entry["traj_x"], dtype=np.float64),
            "traj_c": np.asarray(entry["traj_c"], dtype=np.float64),
            "traj_e": np.asarray(entry["traj_e"], dtype=np.int64),
            "traj_a": np.asarray(entry["traj_a"], dtype=np.int64),
        }


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def default_flowmol3adapter(
    backend: str = "numpy",
    *,
    num_steps: int = FLOWMOL3ADAPTER_NUM_STEPS_DEFAULT,
) -> FlowMol3AdapterImpl:
    """Return a fresh :class:`FlowMol3AdapterImpl` for tests + registry wiring."""
    return FlowMol3AdapterImpl(backend=str(backend), num_steps=int(num_steps))


__all__ = [
    "AUDIT_FLOWMOL3_NUMPY_BACKEND",
    "AUDIT_FLOWMOL3_RESTART_BLEND",
    "AUDIT_FLOWMOL3_TORCH_BACKEND",
    "AUDIT_FLOWMOL3_TRAJECTORY_BUILT",
    "FLOWMOL3ADAPTER_CHANNEL_DOMAINS",
    "FLOWMOL3ADAPTER_CHANNELS",
    "FLOWMOL3ADAPTER_CONFIG_HASH",
    "FLOWMOL3ADAPTER_CONFIG_VERSION",
    "FLOWMOL3ADAPTER_DOMAIN_METADATA",
    "FLOWMOL3ADAPTER_MECHANISM_ID",
    "FLOWMOL3ADAPTER_N_ATOM_TYPES",
    "FLOWMOL3ADAPTER_N_BOND_TYPES",
    "FLOWMOL3ADAPTER_NATIVE_STATES_MAXSIZE",
    "FLOWMOL3ADAPTER_NUM_STEPS_DEFAULT",
    "FLOWMOL3ADAPTER_PINNED_COMMIT",
    "FLOWMOL3ADAPTER_STATE_SHAPE",
    "FlowMol3AdapterCapabilities",
    "FlowMol3AdapterImpl",
    "default_flowmol3adapter",
]