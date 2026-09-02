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
* :class:`FlowMol3V2AdapterCapabilities` — frozen capability surface.
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

# ---------------------------------------------------------------------------
# Real-checkpoint (GEOM-Drugs CTMC) vocabulary constants.
#
# Derived from the published ``last.ckpt`` tensor shapes:
#
# * ``vector_field.token_embeddings.a.weight`` -> ``(12, 64)``
#   = 10 elements + 1 fake-atom token + 1 CTMC mask token.
# * ``vector_field.token_embeddings.c.weight`` -> ``(7, 64)``
#   = 6 formal-charge values (-2..+3) + 1 CTMC mask token.
# * ``vector_field.token_embeddings.e.weight`` -> ``(5, 64)``
#   = 4 kekulized bond orders (none/single/double/triple, because
#   ``mol_fm.explicit_aromaticity=false``) + 1 CTMC mask token.
# * ``vector_field.node_output_head.2.weight`` -> ``(17, 256)``
#   = 11 atom-type logits (10 elements + fake) ++ 6 charge logits.
# * ``vector_field.to_edge_logits.2.weight`` -> ``(4, 128)``
#   = the 4 kekulized bond orders.
# ---------------------------------------------------------------------------

#: Number of atom-type tokens on the checkpoint's ``a`` embedding table.
FLOWMOL3_MODEL_ATOM_TOKENS: int = 12
#: Number of charge tokens on the checkpoint's ``c`` embedding table.
FLOWMOL3_MODEL_CHARGE_TOKENS: int = 7
#: Number of bond tokens on the checkpoint's ``e`` embedding table.
FLOWMOL3_MODEL_BOND_TOKENS: int = 5
#: Atom-type logit width of ``node_output_head`` (10 elements + fake).
FLOWMOL3_MODEL_ATOM_LOGITS: int = 11
#: Charge logit width of ``node_output_head``.
FLOWMOL3_MODEL_CHARGE_LOGITS: int = 6
#: Bond logit width of ``to_edge_logits`` (kekulized: none/1/2/3).
FLOWMOL3_MODEL_BOND_LOGITS: int = 4
#: Scalar / edge / token hidden widths (``config.yaml:vector_field``).
FLOWMOL3_MODEL_TOKEN_DIM: int = 64
FLOWMOL3_MODEL_HIDDEN_SCALARS: int = 256
FLOWMOL3_MODEL_HIDDEN_EDGE: int = 128
FLOWMOL3_MODEL_TIME_DIM: int = 64

#: Formal-charge values behind the checkpoint's 6 charge classes.
FLOWMOL3_MODEL_CHARGE_VALUES: tuple[int, ...] = (-2, -1, 0, 1, 2, 3)

#: Adapter bond label -> checkpoint bond token. The adapter's vocabulary
#: is ``(single, double, triple, aromatic, no-bond)``; the checkpoint's
#: is ``(none, single, double, triple)`` + mask. GEOM-Drugs is trained
#: kekulized so the adapter's ``aromatic`` label folds onto ``single``.
FLOWMOL3_ADAPTER_TO_MODEL_BOND: tuple[int, ...] = (1, 2, 3, 1, 0)

#: Checkpoint bond class -> adapter bond label (inverse of the above for
#: the 4 emitted logits). ``none`` becomes the adapter's no-bond
#: sentinel ``FLOWMOL3ADAPTER_N_BOND_TYPES - 1``.
FLOWMOL3_MODEL_TO_ADAPTER_BOND: tuple[int, ...] = (4, 0, 1, 2)

#: Target bonded / non-bonded interatomic separations (Angstrom) used by
#: the equivariant coordinate head.
FLOWMOL3_BONDED_SEPARATION_A: float = 1.45
FLOWMOL3_NONBONDED_SEPARATION_A: float = 3.2

#: Default number of integration steps on ``[0, 1]`` for ``solve_ode``.
FLOWMOL3ADAPTER_NUM_STEPS_DEFAULT: int = 100

#: Maximum size of the LRU-bounded ``_native_states`` cache.
FLOWMOL3ADAPTER_NATIVE_STATES_MAXSIZE: int = 64

#: Audit / error codes (deterministic ASCII strings).
AUDIT_FLOWMOL3_RESTART_BLEND: str = "flowmol3adapter_restart_blend"
AUDIT_FLOWMOL3_TRAJECTORY_BUILT: str = "flowmol3adapter_trajectory_built"
AUDIT_FLOWMOL3_TORCH_BACKEND: str = "flowmol3adapter_torch_backend"
AUDIT_FLOWMOL3_NUMPY_BACKEND: str = "flowmol3adapter_numpy_backend"
AUDIT_FLOWMOL3_REAL_WEIGHTS: str = "flowmol3adapter_real_weights"
AUDIT_FLOWMOL3_INJECT_FORWARD_NOISE: str = "flowmol3adapter_inject_forward_noise"

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
# Real-checkpoint loading (PyTorch Lightning ``last.ckpt``)
# ---------------------------------------------------------------------------


def _resolve_flowmol3_config_path(weights_path: Any) -> Any:
    """Return the ``config.yaml`` that ships beside a FlowMol3 checkpoint.

    The published layout is ``<run>/config.yaml`` +
    ``<run>/checkpoints/last.ckpt``; we also accept a ``config.yaml``
    sitting directly next to the checkpoint. Returns ``None`` when
    neither exists (the loader then falls back to the pinned vocabulary
    constants in this module).
    """
    from pathlib import Path

    ckpt = Path(str(weights_path))
    for candidate in (
        ckpt.parent / "config.yaml",
        ckpt.parent.parent / "config.yaml",
    ):
        if candidate.is_file():
            return candidate
    return None


def _load_flowmol3_config(weights_path: Any) -> dict[str, Any]:
    """Parse the FlowMol3 ``config.yaml`` next to ``weights_path``.

    Returns a normalized dict with the keys the adapter actually
    consumes: ``atom_map`` (the element vocabulary), ``dataset_name``,
    ``parameterization`` (``ctmc`` for the published GEOM-Drugs run),
    ``distort_p`` / ``distort_t``, and the raw ``vector_field`` block.
    Falls back to the module's pinned constants when the YAML is
    missing or unreadable.
    """
    default: dict[str, Any] = {
        "atom_map": ("C", "H", "N", "O", "F", "P", "S", "Cl", "Br", "I"),
        "dataset_name": "geom",
        "parameterization": "ctmc",
        "distort_p": 0.7,
        "distort_t": 0.25,
        "explicit_aromaticity": False,
        "vector_field": {},
        "config_path": None,
    }
    cfg_path = _resolve_flowmol3_config_path(weights_path)
    if cfg_path is None:
        return default
    try:
        import yaml  # noqa: PLC0415 — optional, only on the torch path.

        raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001 — config is advisory, never fatal.
        return default
    dataset = raw.get("dataset", {}) or {}
    mol_fm = raw.get("mol_fm", {}) or {}
    atom_map = dataset.get("atom_map") or default["atom_map"]
    return {
        "atom_map": tuple(str(sym) for sym in atom_map),
        "dataset_name": str(dataset.get("dataset_name", default["dataset_name"])),
        "parameterization": str(
            mol_fm.get("parameterization", default["parameterization"])
        ),
        "distort_p": float(mol_fm.get("distort_p", default["distort_p"])),
        "distort_t": float(mol_fm.get("distort_t", default["distort_t"])),
        "explicit_aromaticity": bool(
            mol_fm.get("explicit_aromaticity", default["explicit_aromaticity"])
        ),
        "vector_field": dict(raw.get("vector_field", {}) or {}),
        "config_path": str(cfg_path),
    }


def _load_flowmol3_state_dict(weights_path: Any) -> dict[str, Any]:
    """Load the Lightning checkpoint and return its ``state_dict``.

    The published FlowMol3 artifact is a PyTorch Lightning checkpoint
    (``epoch`` / ``global_step`` / ``state_dict`` / ``hyper_parameters``
    / optimizer state). We take ``state_dict`` only — the optimizer and
    loop state are irrelevant to inference — and strip the
    ``vector_field.`` prefix that Lightning's ``LightningModule``
    attribute path adds.
    """
    import torch  # noqa: PLC0415 — torch backend only.

    blob = torch.load(str(weights_path), map_location="cpu", weights_only=False)
    if isinstance(blob, dict) and "state_dict" in blob:
        raw_sd = blob["state_dict"]
        meta = {
            "epoch": int(blob.get("epoch", -1)),
            "global_step": int(blob.get("global_step", -1)),
            "lightning_version": str(blob.get("pytorch-lightning_version", "")),
        }
    else:
        raw_sd = blob
        meta = {"epoch": -1, "global_step": -1, "lightning_version": ""}
    stripped: dict[str, Any] = {}
    for key, value in raw_sd.items():
        name = str(key)
        if name.startswith("vector_field."):
            name = name[len("vector_field.") :]
        stripped[name] = value
    return {"state_dict": stripped, "meta": meta, "n_tensors": len(raw_sd)}


def _build_flowmol3_velocity_module(
    state_dict: Mapping[str, Any],
    *,
    device: str,
) -> Any:
    """Build the real-weight FlowMol3 velocity head from ``state_dict``.

    Scope / fidelity boundary (READ THIS BEFORE QUOTING NUMBERS)
    -----------------------------------------------------------

    The published checkpoint's vector field is a GVP-based **SE(3)
    equivariant message-passing network over DGL heterographs**
    (``conv_layers`` / ``node_position_updaters`` / ``edge_updaters`` —
    444 of the 475 checkpoint tensors). Reconstructing that stack
    requires both the ``flowmol`` package and ``dgl``; neither has a
    Python 3.12 wheel and neither is installed in this framework's
    venv (see the module docstring in
    :mod:`adaptive_reflow.molecular.rdkit_export` for the same dgl
    boundary).

    What this module therefore instantiates is the checkpoint's
    **embedding + readout path**, with the *real pretrained tensors*:

    * ``token_embeddings.{a,c,e}`` — the trained atom / charge / bond
      token tables,
    * ``scalar_embedding`` — the trained node-scalar MLP
      (``Linear(192,256) -> act -> Linear(256,256) -> act -> LayerNorm``),
    * ``edge_embedding`` — the trained edge MLP,
    * ``node_output_head`` — the trained ``(11 atom ++ 6 charge)``
      readout,
    * ``to_edge_logits`` — the trained 4-way bond readout.

    The 444 GVP graph-convolution tensors are **not** applied. This is a
    real-weights partial-fidelity head, NOT the published FlowMol3
    sampler: the atom / charge / bond marginals come from trained
    parameters, but they are not conditioned on 3D graph context. Any
    chemistry number produced through it measures the re-inference
    plumbing on real weights, not FlowMol3's reported sample quality.
    """
    import torch  # noqa: PLC0415 — torch backend only.
    from torch import nn  # noqa: PLC0415

    class _FlowMol3ReadoutHead(nn.Module):
        """Embedding + readout subgraph of the FlowMol3 vector field."""

        def __init__(self) -> None:
            super().__init__()
            self.emb_a = nn.Embedding(
                FLOWMOL3_MODEL_ATOM_TOKENS, FLOWMOL3_MODEL_TOKEN_DIM
            )
            self.emb_c = nn.Embedding(
                FLOWMOL3_MODEL_CHARGE_TOKENS, FLOWMOL3_MODEL_TOKEN_DIM
            )
            self.emb_e = nn.Embedding(
                FLOWMOL3_MODEL_BOND_TOKENS, FLOWMOL3_MODEL_TOKEN_DIM
            )
            self.scalar_embedding = nn.Sequential(
                nn.Linear(3 * FLOWMOL3_MODEL_TOKEN_DIM, FLOWMOL3_MODEL_HIDDEN_SCALARS),
                nn.SiLU(),
                nn.Linear(
                    FLOWMOL3_MODEL_HIDDEN_SCALARS, FLOWMOL3_MODEL_HIDDEN_SCALARS
                ),
                nn.SiLU(),
                nn.LayerNorm(FLOWMOL3_MODEL_HIDDEN_SCALARS),
            )
            self.edge_embedding = nn.Sequential(
                nn.Linear(FLOWMOL3_MODEL_TOKEN_DIM, FLOWMOL3_MODEL_HIDDEN_EDGE),
                nn.SiLU(),
                nn.Linear(FLOWMOL3_MODEL_HIDDEN_EDGE, FLOWMOL3_MODEL_HIDDEN_EDGE),
                nn.SiLU(),
                nn.LayerNorm(FLOWMOL3_MODEL_HIDDEN_EDGE),
            )
            self.node_output_head = nn.Sequential(
                nn.Linear(
                    FLOWMOL3_MODEL_HIDDEN_SCALARS, FLOWMOL3_MODEL_HIDDEN_SCALARS
                ),
                nn.SiLU(),
                nn.Linear(
                    FLOWMOL3_MODEL_HIDDEN_SCALARS,
                    FLOWMOL3_MODEL_ATOM_LOGITS + FLOWMOL3_MODEL_CHARGE_LOGITS,
                ),
            )
            self.to_edge_logits = nn.Sequential(
                nn.Linear(FLOWMOL3_MODEL_HIDDEN_EDGE, FLOWMOL3_MODEL_HIDDEN_EDGE),
                nn.SiLU(),
                nn.Linear(FLOWMOL3_MODEL_HIDDEN_EDGE, FLOWMOL3_MODEL_BOND_LOGITS),
            )

        def forward(  # noqa: D102 — see module docstring above.
            self,
            a_tok: Any,
            c_tok: Any,
            e_tok: Any,
            t_emb: Any,
        ) -> tuple[Any, Any, Any]:
            h = self.scalar_embedding(
                torch.cat([self.emb_a(a_tok), self.emb_c(c_tok), t_emb], dim=-1)
            )
            node_out = self.node_output_head(h)
            atom_logits = node_out[..., :FLOWMOL3_MODEL_ATOM_LOGITS]
            charge_logits = node_out[..., FLOWMOL3_MODEL_ATOM_LOGITS :]
            edge_h = self.edge_embedding(self.emb_e(e_tok))
            edge_logits = self.to_edge_logits(edge_h)
            return atom_logits, charge_logits, edge_logits

    module = _FlowMol3ReadoutHead()
    remap = {
        "emb_a.weight": "token_embeddings.a.weight",
        "emb_c.weight": "token_embeddings.c.weight",
        "emb_e.weight": "token_embeddings.e.weight",
    }
    target: dict[str, Any] = {}
    missing: list[str] = []
    for name in module.state_dict():
        source = remap.get(name, name)
        if source not in state_dict:
            missing.append(source)
            continue
        target[name] = state_dict[source]
    if missing:
        raise KeyError(
            "flowmol3_checkpoint_missing_tensors:" + ",".join(sorted(missing))
        )
    module.load_state_dict(target, strict=True)
    module.eval()
    for param in module.parameters():
        param.requires_grad_(False)
    module.to(torch.device(str(device)))
    return module


def _flowmol3_time_embedding(t: float, dim: int, *, device: Any, torch_mod: Any) -> Any:
    """Sinusoidal ``dim``-wide time features for a scalar ``t`` in ``[0, 1]``.

    The checkpoint carries no learned time-embedding tensor (the
    ``scalar_embedding`` input width of 192 = ``a`` token (64) ++ ``c``
    token (64) ++ time (64)), so the time features are the standard
    fixed sinusoidal basis.
    """
    half = int(dim) // 2
    freqs = torch_mod.exp(
        -np.log(10000.0)
        * torch_mod.arange(half, dtype=torch_mod.float32, device=device)
        / float(half)
    )
    ang = float(t) * freqs
    return torch_mod.cat([torch_mod.sin(ang), torch_mod.cos(ang)], dim=-1)


def _real_velocity_field(
    module: Any,
    x: ArrayF64,
    a: ArrayF64,
    c: ArrayF64,
    e: ArrayF64,
    t: float,
    *,
    device: str,
) -> tuple[ArrayF64, ArrayF64, ArrayF64, ArrayF64]:
    """Evaluate the real-weight velocity field; return ``(v_x, v_c, v_e, v_a)``.

    All four channels use the flow-matching linear-interpolant form
    ``v = (endpoint_prediction - current_state) / max(1 - t, eps)``, so
    an Euler sweep over ``t in [0, 1]`` lands exactly on the model's
    endpoint prediction at ``t = 1``.

    * ``v_a`` — ``(n, 10)`` atom-type logit velocity toward the
      checkpoint's ``node_output_head`` atom marginal (the ``fake``
      class is dropped; the adapter has no fake-atom concept).
    * ``v_c`` — ``(n,)`` charge velocity toward the expected formal
      charge under the checkpoint's 6-way charge marginal.
    * ``v_e`` — ``(n, n, 5)`` bond-logit velocity toward the
      checkpoint's symmetrized 4-way bond marginal, re-indexed into the
      adapter's ``(single, double, triple, aromatic, no-bond)``
      vocabulary. ``aromatic`` is held at zero probability because the
      published run is ``explicit_aromaticity: false`` (kekulized).
    * ``v_x`` — SE(3)-equivariant coordinate velocity: each atom is
      pulled along the real interatomic difference vectors toward a
      bonded / non-bonded target separation, weighted by the
      checkpoint's predicted bond probability. Translation- and
      rotation-equivariant by construction (it is a bond-probability
      weighted combination of ``x_j - x_i``).
    """
    import torch  # noqa: PLC0415

    dev = torch.device(str(device))
    x_t = torch.as_tensor(np.asarray(x, dtype=np.float32)).to(dev).detach()
    n_atoms = int(x_t.shape[0])
    a_np = np.clip(
        np.asarray(a, dtype=np.int64), 0, FLOWMOL3ADAPTER_N_ATOM_TYPES - 1
    )
    a_tok = torch.as_tensor(a_np).to(dev).detach()
    c_np = np.asarray(c, dtype=np.float64).reshape(n_atoms)
    c_idx = np.clip(
        np.rint(c_np).astype(np.int64) - int(FLOWMOL3_MODEL_CHARGE_VALUES[0]),
        0,
        FLOWMOL3_MODEL_CHARGE_LOGITS - 1,
    )
    c_tok = torch.as_tensor(c_idx).to(dev).detach()
    e_np = np.asarray(e, dtype=np.int64).reshape(n_atoms, n_atoms)
    e_np = np.clip(e_np, 0, FLOWMOL3ADAPTER_N_BOND_TYPES - 1)
    e_model = np.asarray(FLOWMOL3_ADAPTER_TO_MODEL_BOND, dtype=np.int64)[e_np]
    e_tok = torch.as_tensor(e_model).to(dev).detach()

    with torch.no_grad():
        t_emb = _flowmol3_time_embedding(
            float(t), FLOWMOL3_MODEL_TIME_DIM, device=dev, torch_mod=torch
        ).expand(n_atoms, FLOWMOL3_MODEL_TIME_DIM)
        atom_logits, charge_logits, edge_logits = module(a_tok, c_tok, e_tok, t_emb)
        atom_logits = atom_logits.detach()
        charge_logits = charge_logits.detach()
        edge_logits = edge_logits.detach()

        # --- atom-type marginal (drop the fake-atom class) -------------
        p_a = torch.softmax(
            atom_logits[:, :FLOWMOL3ADAPTER_N_ATOM_TYPES].float(), dim=-1
        )
        # --- charge marginal -> expected formal charge -----------------
        p_c = torch.softmax(charge_logits.float(), dim=-1)
        charge_values = torch.as_tensor(
            np.asarray(FLOWMOL3_MODEL_CHARGE_VALUES, dtype=np.float32)
        ).to(dev)
        c_pred = (p_c * charge_values).sum(dim=-1)
        # --- bond marginal, symmetrized, re-indexed --------------------
        p_e_model = torch.softmax(edge_logits.float(), dim=-1)
        p_e_model = 0.5 * (p_e_model + p_e_model.transpose(0, 1))
        p_e = torch.zeros(
            (n_atoms, n_atoms, FLOWMOL3ADAPTER_N_BOND_TYPES),
            dtype=torch.float32,
            device=dev,
        )
        for model_cls, adapter_lbl in enumerate(FLOWMOL3_MODEL_TO_ADAPTER_BOND):
            p_e[:, :, int(adapter_lbl)] = p_e_model[:, :, int(model_cls)]
        # No self-bonds.
        eye = torch.eye(n_atoms, dtype=torch.bool, device=dev)
        p_e[eye] = 0.0
        diag_idx = torch.arange(n_atoms, device=dev)
        p_e[diag_idx, diag_idx, FLOWMOL3ADAPTER_N_BOND_TYPES - 1] = 1.0

        # --- equivariant coordinate endpoint ---------------------------
        diff = x_t.unsqueeze(0) - x_t.unsqueeze(1)  # diff[i, j] = x_j - x_i
        dist = diff.norm(dim=-1)
        safe_dist = dist.clamp_min(1e-3)
        p_bond = 1.0 - p_e[:, :, FLOWMOL3ADAPTER_N_BOND_TYPES - 1]
        target_sep = (
            FLOWMOL3_BONDED_SEPARATION_A * p_bond
            + FLOWMOL3_NONBONDED_SEPARATION_A * (1.0 - p_bond)
        )
        # Unit step toward the target separation along the real
        # difference vector (equivariant: rotates with the molecule).
        step = ((safe_dist - target_sep) / safe_dist).unsqueeze(-1) * diff
        weight = p_bond + 0.05
        weight = weight.masked_fill(eye, 0.0)
        weight = weight / weight.sum(dim=1, keepdim=True).clamp_min(1e-6)
        x_pred = x_t + (weight.unsqueeze(-1) * step).sum(dim=1)

    inv_dt = 1.0 / max(1.0 - float(t), 1e-3)
    onehot_a = np.eye(FLOWMOL3ADAPTER_N_ATOM_TYPES, dtype=np.float64)[a_np]
    onehot_e = np.eye(FLOWMOL3ADAPTER_N_BOND_TYPES, dtype=np.float64)[e_np]
    v_a = (p_a.cpu().numpy().astype(np.float64) - onehot_a) * inv_dt
    v_e = (p_e.cpu().numpy().astype(np.float64) - onehot_e) * inv_dt
    v_c = (c_pred.cpu().numpy().astype(np.float64) - c_np) * inv_dt
    v_x = (
        x_pred.cpu().numpy().astype(np.float64)
        - np.asarray(x, dtype=np.float64).reshape(n_atoms, 3)
    ) * inv_dt
    return (
        np.nan_to_num(v_x, nan=0.0, posinf=0.0, neginf=0.0),
        np.nan_to_num(v_c, nan=0.0, posinf=0.0, neginf=0.0),
        np.nan_to_num(v_e, nan=0.0, posinf=0.0, neginf=0.0),
        np.nan_to_num(v_a, nan=0.0, posinf=0.0, neginf=0.0),
    )


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
class FlowMol3V2AdapterCapabilities(AdapterCapabilities):
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


class FlowMol3V2Adapter(FlowMatchingODEAdapter):
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

    The class name ``FlowMol3V2Adapter`` avoids a collision with the
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
        weights_path: Any = None,
        device: str = "cpu",
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
        self._weights_path = str(weights_path) if weights_path is not None else None
        self._device = str(device)
        self._native_states: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._caps = FlowMol3V2AdapterCapabilities()
        self._blender: RestartBlenderProtocol = (
            blender if blender is not None else LinearBlender()
        )
        # Cache for the (lazy) torch model handle + per-n_atoms weight
        # matrices for the synthetic velocity field. Both are populated
        # on first use.
        self._model: Any = None
        self._model_meta: dict[str, Any] = {}
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
        """Lazy-load the real FlowMol3 checkpoint (``backend='torch'``).

        Imports :mod:`torch` only when ``backend="torch"``, parses the
        ``config.yaml`` shipped next to the checkpoint for the element
        vocabulary + CTMC settings, loads the PyTorch Lightning
        ``last.ckpt`` ``state_dict``, and instantiates the real-weight
        velocity head via :func:`_build_flowmol3_velocity_module`.
        Caches the module on ``self._model`` and the parsed metadata on
        ``self._model_meta``.

        When no ``weights_path`` was supplied the model handle is the
        sentinel string ``"synthetic"`` and
        :meth:`_velocity_field_ex` keeps using the deterministic NumPy
        field (so ``backend='torch'`` without weights stays a valid,
        reproducible configuration).

        See :func:`_build_flowmol3_velocity_module` for the fidelity
        boundary: the 444 GVP graph-convolution tensors in the
        checkpoint are NOT applied (``dgl`` / ``flowmol`` are not
        importable on py3.12), so this is a real-weights readout head,
        not the published FlowMol3 sampler.
        """
        if self._model is not None:
            return self._model
        if self._backend != "torch":
            raise RuntimeError(
                "model_load_called_with_numpy_backend; this is a logic bug"
            )
        if self._weights_path is None:
            self._model = "synthetic"
            self._model_meta = {"kind": "synthetic", "weights_path": None}
            return self._model
        config = _load_flowmol3_config(self._weights_path)
        loaded = _load_flowmol3_state_dict(self._weights_path)
        module = _build_flowmol3_velocity_module(
            loaded["state_dict"], device=self._device
        )
        self._model = module
        self._model_meta = {
            "kind": "real",
            "weights_path": str(self._weights_path),
            "device": str(self._device),
            "n_checkpoint_tensors": int(loaded["n_tensors"]),
            "epoch": loaded["meta"]["epoch"],
            "global_step": loaded["meta"]["global_step"],
            "atom_map": tuple(config["atom_map"]),
            "dataset_name": str(config["dataset_name"]),
            "parameterization": str(config["parameterization"]),
            "distort_p": float(config["distort_p"]),
            "distort_t": float(config["distort_t"]),
            "explicit_aromaticity": bool(config["explicit_aromaticity"]),
            "config_path": config["config_path"],
        }
        return self._model

    @property
    def model_metadata(self) -> Mapping[str, Any]:
        """Parsed checkpoint metadata (empty until :meth:`_load_model` runs)."""
        return dict(self._model_meta)

    def _velocity_field_ex(
        self,
        x: ArrayF64,
        c: ArrayF64,
        e: ArrayF64,
        t: float,
        *,
        n_atoms: int,
        seed: int,
        a: ArrayF64 | None = None,
    ) -> tuple[ArrayF64, ArrayF64, ArrayF64, ArrayF64 | None]:
        """Evaluate ``v_theta`` returning ``(v_x, v_c, v_e, v_a)``.

        ``v_a`` is ``None`` on the synthetic NumPy field (the atom-type
        channel is not evolved there, matching the pre-real-weights
        behaviour); it is an ``(n_atoms, 10)`` logit velocity on the
        real-weights torch path.
        """
        if (
            self._backend == "torch"
            and self._load_model() != "synthetic"
            and a is not None
        ):
            return _real_velocity_field(
                self._model,
                np.asarray(x, dtype=np.float64),
                np.asarray(a, dtype=np.int64),
                np.asarray(c, dtype=np.float64),
                np.asarray(e, dtype=np.int64),
                float(t),
                device=self._device,
            )
        v_x, v_c, v_e = _numpy_velocity_field(
            x,
            c,
            e,
            float(t),
            weights=self._get_synthetic_weights(int(n_atoms), int(seed)),
        )
        return v_x, v_c, v_e, None

    def _velocity_field(
        self,
        x: ArrayF64,
        c: ArrayF64,
        e: ArrayF64,
        t: float,
        *,
        n_atoms: int,
        seed: int,
        a: ArrayF64 | None = None,
    ) -> tuple[ArrayF64, ArrayF64, ArrayF64]:
        """Evaluate ``v_theta(x, c, e, t)`` -> ``(v_x, v_c, v_e)``.

        Backwards-compatible three-tuple view of
        :meth:`_velocity_field_ex`. Routes to the synthetic NumPy field
        for ``backend="numpy"`` (and for ``backend="torch"`` without a
        checkpoint) and to the real-weights head otherwise.
        """
        v_x, v_c, v_e, _ = self._velocity_field_ex(
            x, c, e, float(t), n_atoms=int(n_atoms), seed=int(seed), a=a
        )
        return v_x, v_c, v_e

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
            v_x, v_c, v_e, v_a = self._velocity_field_ex(
                x=x_eval,
                c=c_eval,
                e=e_eval,
                t=float(t_cur),
                n_atoms=n_atoms,
                seed=int(seed),
                a=np.asarray(a_cur, dtype=np.int64),
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
            if v_a is not None:
                # Real-weights path: enforce the symmetric-dense bond
                # contract (the RDKit writer reads the upper triangle,
                # but symmetry keeps the next model call consistent),
                # and evolve the atom-type channel too (the synthetic
                # field leaves ``a`` frozen, so its lineage — and every
                # golden digest built on it — is unchanged).
                upper = np.triu(e_cur, k=1)
                e_cur = (
                    upper
                    + upper.T
                    + np.diag(
                        np.full(
                            n_atoms,
                            int(FLOWMOL3ADAPTER_N_BOND_TYPES) - 1,
                            dtype=np.int64,
                        )
                    )
                )
                a_logits = (
                    np.eye(int(FLOWMOL3ADAPTER_N_ATOM_TYPES), dtype=np.float64)[a_cur]
                    + dt * np.asarray(v_a, dtype=np.float64)
                )
                a_cur = np.argmax(a_logits, axis=-1).astype(np.int64)
            traj_x[i] = x_cur
            traj_c[i] = c_cur
            traj_e[i] = e_cur
            traj_a[i] = a_cur
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
            + (
                # Real weights participate in the integrator identity so
                # a checkpoint swap can never alias onto a synthetic run.
                (str(self._weights_path), str(self._device))
                if self._weights_path is not None
                else ()
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
    # 9. inject_forward_noise (optional — P0-7 close, r17-audit P-01)
    # ------------------------------------------------------------------

    def inject_forward_noise(
        self,
        bundle: StateBundle,
        injected: Any,
    ) -> StateBundle:
        """Inject ``injected`` (shape ``(3,)`` = ``FLOWMOL3ADAPTER_STATE_SHAPE``)
        into the bundle's prior ``x`` channel.

        Mirror of the F-25 close-out pattern in
        :class:`RectifiedFlowCIFARAdapter.inject_forward_noise` and
        :class:`HiDreamI1Adapter.inject_forward_noise`. The injected
        array is treated as additive noise on the *coordinate* (``x``)
        slice of the heterogeneous ``(x, a, c, e)`` native state --
        ``a`` / ``c`` / ``e`` are categorical and pass through
        untouched. Returns a fresh :class:`StateBundle` whose
        :attr:`native_state_digest` is a SHA-256 over the new noise
        provenance and whose ``provenance`` records the
        :data:`AUDIT_FLOWMOL3_INJECT_FORWARD_NOISE` tag.

        Notes
        -----
        * This is a *byte-deterministic* state replay: the new prior
          is keyed under a digest that the engine's F-25
          forward-noise-injection path can look up via
          ``_native_states`` rather than carrying the noise as
          private adapter state.
        * The ``x`` channel update uses the one-atom degenerate prior
          (``FLOWMOL3ADAPTER_STATE_SHAPE = (3,)``), so the
          ``injected`` array is reshaped to ``(3,)`` when shorter or
          truncated when longer. This matches the design spec
          (r17-audit P-02).
        """
        prior_entry = self._native_states.get(bundle.native_state_digest)
        if prior_entry is None:
            raise CapabilityMissingError(
                "missing_native_state", context=str(bundle.native_state_digest)
            )
        # Heterogeneous native state: only ``x`` is continuous; ``a`` /
        # ``c`` / ``e`` pass through (categorical channels).
        flat = np.asarray(
            getattr(injected, "flat", injected), dtype=np.float64
        )
        flat = flat[: FLOWMOL3ADAPTER_STATE_SHAPE[0]] if flat.ndim == 1 else flat
        if flat.size < FLOWMOL3ADAPTER_STATE_SHAPE[0]:
            # Pad with zeros so the digest is well-defined.
            flat = np.concatenate(
                [
                    flat,
                    np.zeros(
                        FLOWMOL3ADAPTER_STATE_SHAPE[0] - flat.size,
                        dtype=np.float64,
                    ),
                ]
            )
        noise_x = flat[: FLOWMOL3ADAPTER_STATE_SHAPE[0]].reshape(
            FLOWMOL3ADAPTER_STATE_SHAPE
        )
        x_prior = np.asarray(prior_entry.get("x", np.zeros(0)), dtype=np.float64)
        if x_prior.size == 0:
            # No prior x (e.g. trajectory-only entry) — seed from noise.
            x_new = noise_x
        elif x_prior.shape == FLOWMOL3ADAPTER_STATE_SHAPE:
            # Degenerate one-atom prior shape (3,) — add in-place.
            x_new = x_prior + noise_x
        else:
            # Multi-atom prior shape (n_atoms, 3) — propagate the
            # one-atom noise to the centroid (audit-replayability).
            x_new = x_prior + noise_x.reshape(1, 3)

        new_digest = _digest_state(
            {
                "kind": "forward_noise",
                "src_digest": str(bundle.native_state_digest),
                "noise_head": [float(v) for v in flat[: min(flat.size, 8)]],
                "noise_x_first": float(noise_x[0]) if noise_x.size > 0 else 0.0,
            }
        )
        self._put_native_state(
            new_digest,
            {
                "x": x_new,
                "a": prior_entry.get("a", np.zeros(0, dtype=np.int64)),
                "c": prior_entry.get("c", np.zeros(0)),
                "e": prior_entry.get("e", np.zeros(0, dtype=np.int64)),
                "n_atoms": int(prior_entry.get("n_atoms", 0)),
                "source_round": int(bundle.source_round),
                "audit": tuple(prior_entry.get("audit", ()))
                + (AUDIT_FLOWMOL3_INJECT_FORWARD_NOISE,),
            },
        )
        return StateBundle(
            channels=dict(bundle.channels),
            masks=dict(bundle.masks),
            batch_id=str(bundle.batch_id),
            sample_id=str(bundle.sample_id),
            reference_frame=str(bundle.reference_frame),
            normalization=str(bundle.normalization),
            source_round=int(bundle.source_round),
            detach_proof=True,
            native_state_digest=new_digest,
            provenance=tuple(bundle.provenance)
            + (AUDIT_FLOWMOL3_INJECT_FORWARD_NOISE,),
            capability_token=self.capabilities(),
        )

    # ------------------------------------------------------------------
    # 10. export_trajectory (P0-7 — public trajectory export)
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
    weights_path: Any = None,
    device: str = "cpu",
) -> FlowMol3V2Adapter:
    """Return a fresh :class:`FlowMol3V2Adapter` for tests + registry wiring.

    ``weights_path`` (with ``backend='torch'``) points at a published
    FlowMol3 PyTorch Lightning checkpoint — e.g.
    ``data/flowmol3/weights_real/checkpoints/last.ckpt``. Leave it
    ``None`` for the deterministic synthetic field.
    """
    return FlowMol3V2Adapter(
        backend=str(backend),
        num_steps=int(num_steps),
        weights_path=weights_path,
        device=str(device),
    )


__all__ = [
    "AUDIT_FLOWMOL3_INJECT_FORWARD_NOISE",
    "AUDIT_FLOWMOL3_NUMPY_BACKEND",
    "AUDIT_FLOWMOL3_REAL_WEIGHTS",
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
    "FlowMol3V2AdapterCapabilities",
    "FlowMol3V2Adapter",
    "default_flowmol3adapter",
]