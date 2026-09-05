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
import sys
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
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

from adaptive_reflow.adapters._adapter_common import (
    digest_state,
    make_ref,
    seed_from_ids,
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

#: Maximum size of the LRU-bounded synthetic-velocity-field weights cache.
#: Bounds :func:`_cached_synthetic_weights` (and therefore the adapter's
#: ``_synthetic_weights`` data path) so a long-running adapter cannot
#: accumulate an unbounded number of weight arrays when called with many
#: distinct ``n_atoms`` values.
FLOWMOL3ADAPTER_SYNTHETIC_WEIGHTS_MAXSIZE: int = 8

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

#: Default absolute path to the upstream zavalab FlowMol3 repository
#: (pinned at commit ``77cae22174b7792b0e25e9e0414038420736d841``).
#: When ``FlowMol3V2Adapter(use_upstream=True)`` is constructed, the
#: adapter :func:`sys.path.insert`s this directory and tries to
#: ``from flowmol.models.flowmol import FlowMol``. The full-fidelity
#: upstream sampler requires :mod:`dgl` + :mod:`torch_scatter`; on
#: :sm_120 the upstream dependency chain is NOT installable from
#: PyPI wheels (per ``docs/r17-survey/baseline-deviation-review.md``
#: §3.4) so the hook stays dormant unless both dependencies import.
FLOWMOL3ADAPTER_UPSTREAM_REPO_DIR: str = (
    str(Path(__file__).resolve().parent.parent.parent / "data" / "FlowMol3" / "repo")
)

#: Sentinel kind in ``model_metadata`` when the upstream
#: ``flowmol.models.flowmol.FlowMol`` was successfully instantiated.
#: Distinct from ``"real"`` (the framework's partial-fidelity readout
#: head built in :func:`_build_flowmol3_velocity_module`) and from
#: ``"synthetic"`` (the deterministic NumPy field).
FLOWMOL3ADAPTER_UPSTREAM_KIND: str = "upstream_flowmol"

#: Marker stored under ``model_metadata['dgl_available']`` after the
#: first ``_load_model()`` call. The flag is informational — the
#: adapter does not require DGL on the partial-fidelity path; it only
#: needs DGL on the ``use_upstream=True`` path.
FLOWMOL3ADAPTER_DGL_PROBE: str = "dgl_available"

# Local type alias to keep numpy dependency off hot annotation paths.
ArrayF64 = NDArray[np.float64]


def _probe_dgl() -> bool:
    """Return ``True`` iff :mod:`dgl` imports cleanly in this interpreter.

    Used by :meth:`FlowMol3V2Adapter._load_model` to gate the
    ``use_upstream=True`` path. Distinct from :func:`_torch_is_available`
    because DGL is a separate wheel that has its own torch-version
    coupling (``libgraphbolt_pytorch_<X>.<Y>.<Z>.so`` is matched
    against the running torch). On :sm_120 the published PyPI wheel
    for ``dgl==2.1.0`` is built against ``torch==2.2.0+cu121``; the
    framework's project venv runs ``torch==2.7.0+cu128``, hence the
    three-step install dance in §3.4 of the baseline-deviation review.
    """
    import importlib.util as _il

    spec = _il.find_spec("dgl")
    if spec is None:
        return False
    try:
        import dgl  # noqa: F401 - import side-effect only
    except Exception:  # noqa: BLE001 - permissive: any import failure = missing
        return False
    return True


def _install_upstream_stubs() -> None:
    """Install pure-Python stubs for ``torch_scatter`` and ``posebusters``.

    The upstream zavalab FlowMol3 code imports these two packages at
    module load time:

    * ``torch_scatter.segment_csr`` is the only torch_scatter symbol
      actually used (in ``flowmol/utils/ctmc_utils.py:purity_sampling``).
      We provide a minimal pure-torch segment-sum via CSR indptr — the
      inputs are tiny (per-batch sizes) so a Python loop is acceptable.
    * ``posebusters.PoseBusters`` is only used in the trainer's
      :class:`SampleAnalyzer` (``flowmol/analysis/metrics.py``); we
      never call it on the inference path but it must be importable
      because ``FlowMol.__init__`` instantiates the analyzer eagerly.

    The stubs are installed exactly once (idempotent via a module-level
    sentinel) and BEFORE the ``flowmol`` package is added to
    :data:`sys.path` so the upstream's absolute imports resolve against
    the stubs. Both stubs are best-effort: if a real package later
    becomes available, prefer that over the stub. Tested with
    ``torch==2.7.0+cu128``, ``dgl==2.4.0+cu124``.

    See ``tools/flowmol3_upstream_smoke.py`` for the smoke harness that
    exercises the upstream path on sm_120.
    """
    import types as _types

    if getattr(_install_upstream_stubs, "_installed", False):
        return
    # --- torch_scatter stub -------------------------------------------------
    if "torch_scatter" not in sys.modules:
        ts_mod = _types.ModuleType("torch_scatter")

        def _segment_csr(src: Any, indptr: Any) -> Any:
            """Pure-torch segment-sum over CSR indptr.

            ``src`` has shape ``(N,)`` and ``indptr`` has shape
            ``(batch+1,)`` with ``indptr[i+1] - indptr[i]`` = size of
            group ``i``. Returns ``(batch,)`` with the per-group sum.
            """
            import torch as _torch  # lazy; keep the stub dep-light

            out = []
            for i in range(int(indptr.shape[0]) - 1):
                start = int(indptr[i].item())
                end = int(indptr[i + 1].item())
                if end == start:
                    out.append(_torch.zeros((), dtype=src.dtype, device=src.device))
                else:
                    out.append(src[start:end].sum())
            return _torch.stack(out)

        ts_mod.segment_csr = _segment_csr
        sys.modules["torch_scatter"] = ts_mod
    # --- posebusters stub ---------------------------------------------------
    if "posebusters" not in sys.modules:
        pb_mod = _types.ModuleType("posebusters")

        class _PoseBustersStub:  # noqa: D401 — minimal no-op API surface
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                self._kwargs = dict(kwargs)

            def bust(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
                return {}

            def analyze(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
                return {}

        pb_mod.PoseBusters = _PoseBustersStub  # type: ignore[attr-defined]
        sys.modules["posebusters"] = pb_mod
    # --- torch.serialization: allow pathlib.PosixPath for the Lightning ckpt
    # PyTorch 2.6+ tightened the ``weights_only=True`` default in
    # ``torch.load``; the FlowMol3 Lightning checkpoint pickles
    # ``pathlib.PosixPath`` objects. Adding it to the safe-globals set
    # is the standard torch-supported way to allow that single global.
    try:
        import pathlib as _pathlib
        import torch as _torch

        _torch.serialization.add_safe_globals([_pathlib.PosixPath])
    except Exception:  # noqa: BLE001 - if torch isn't importable we don't care
        pass
    setattr(_install_upstream_stubs, "_installed", True)


def _try_import_upstream_flowmol(
    repo_dir: str = FLOWMOL3ADAPTER_UPSTREAM_REPO_DIR,
) -> tuple[Any, str | None]:
    """Lazy-import ``flowmol.models.flowmol.FlowMol`` from the cloned repo.

    Performs the ``sys.path`` tweak the upstream repo requires (its
    package layout uses absolute ``from flowmol.models...`` imports,
    so the repo root must be on :data:`sys.path` before the first
    ``flowmol`` import). Returns ``(FlowMol_class_or_None, error_str_or_None)``.

    Failure modes (all swallowed into a ``None`` + reason string so the
    adapter's ``use_upstream=True`` path degrades gracefully):

    * Repo directory does not exist on disk.
    * ``dgl`` is not importable in this interpreter.
    * ``from flowmol.models.flowmol import FlowMol`` raises
      :class:`ImportError` even after :func:`_install_upstream_stubs`
      (e.g. ``flowmol`` package itself is corrupt or missing).

    The :func:`_install_upstream_stubs` call is idempotent and must run
    BEFORE the import so the upstream's top-level ``from posebusters
    import PoseBusters`` (in ``flowmol/analysis/metrics.py``) and
    ``from torch_scatter import segment_csr`` (in
    ``flowmol/utils/ctmc_utils.py``) resolve against our pure-Python
    stubs. Both stubs preserve the public surface the upstream actually
    touches; everything else is left as a normal ImportError.
    """
    from pathlib import Path

    p = Path(str(repo_dir))
    if not p.is_dir():
        return None, f"upstream_repo_dir_not_found:{repo_dir}"
    repo_str = str(p.resolve())
    # Install stubs BEFORE sys.path tweak so the upstream's absolute
    # ``from flowmol...`` imports find the stubs via sys.modules.
    _install_upstream_stubs()
    # sys.path tweak: prepend so repo's __init__.py wins over any
    # unrelated ``flowmol`` that may be installed system-wide.
    if repo_str not in sys.path:
        sys.path.insert(0, repo_str)
    try:
        from flowmol.models.flowmol import FlowMol  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001 - permissive on purpose
        return None, f"upstream_flowmol_import_failed:{type(exc).__name__}:{exc}"
    return FlowMol, None


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


@lru_cache(maxsize=FLOWMOL3ADAPTER_SYNTHETIC_WEIGHTS_MAXSIZE)
def _cached_synthetic_weights(
    n_atoms: int, seed: int
) -> dict[str, ArrayF64]:
    """Module-level LRU-bounded cache for synthetic-velocity-field weights.

    Bounded to :data:`FLOWMOL3ADAPTER_SYNTHETIC_WEIGHTS_MAXSIZE = 8`
    entries so a long-running adapter cannot accumulate an unbounded
    number of weight arrays when called with many distinct ``n_atoms``
    values. Replaces the prior per-instance unbounded
    ``self._synthetic_weights`` dict on
    :class:`FlowMol3V2Adapter`; the cache key is ``(n_atoms, seed)`` so
    the result is deterministic for fixed inputs. Shared across all
    :class:`FlowMol3V2Adapter` instances (the weights are pure
    functions of the inputs).
    """
    return _numpy_random_init_weights(seed=int(seed), n_atoms=int(n_atoms))


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
    # NB: numpy 2.x compatibility — `torch.as_tensor(np_arr)` fails with
    # ``RuntimeError: Could not infer dtype of numpy.float32`` on
    # torch==2.2.0 because the internal ``_infer_dtype`` path uses
    # ``len(arr.dtype)`` which numpy 2.x no longer supports on 0-d/1-d
    # dtype objects. Passing an explicit ``dtype=torch.float32`` bypasses
    # the inference. Same fix in :func:`_ctmc_real_velocity_field_ex`.
    x_t = torch.as_tensor(
        np.asarray(x, dtype=np.float32), dtype=torch.float32
    ).to(dev).detach()
    n_atoms = int(x_t.shape[0])
    a_np = np.clip(
        np.asarray(a, dtype=np.int64), 0, FLOWMOL3ADAPTER_N_ATOM_TYPES - 1
    )
    a_tok = torch.as_tensor(a_np, dtype=torch.long).to(dev).detach()
    c_np = np.asarray(c, dtype=np.float64).reshape(n_atoms)
    c_idx = np.clip(
        np.rint(c_np).astype(np.int64) - int(FLOWMOL3_MODEL_CHARGE_VALUES[0]),
        0,
        FLOWMOL3_MODEL_CHARGE_LOGITS - 1,
    )
    c_tok = torch.as_tensor(c_idx, dtype=torch.long).to(dev).detach()
    e_np = np.asarray(e, dtype=np.int64).reshape(n_atoms, n_atoms)
    e_np = np.clip(e_np, 0, FLOWMOL3ADAPTER_N_BOND_TYPES - 1)
    e_model = np.asarray(FLOWMOL3_ADAPTER_TO_MODEL_BOND, dtype=np.int64)[e_np]
    e_tok = torch.as_tensor(e_model, dtype=torch.long).to(dev).detach()

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
        # numpy 2.x compat: explicit torch dtype bypasses the broken
        # ``_infer_dtype`` path that raises
        # ``RuntimeError: Could not infer dtype of numpy.float32`` on
        # torch==2.2.0.
        charge_values = torch.as_tensor(
            np.asarray(FLOWMOL3_MODEL_CHARGE_VALUES, dtype=np.float32),
            dtype=torch.float32,
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
        # Fresh draw is *larger* than the prior. Keep the prior's
        # molecule size: trim the fresh bond matrix to ``n_prior`` rows
        # FIRST, then align the pair (column) dim.
        #
        # Wave 30 Agent B fix (NONCONFORMANCE_BUG #1, Wave 29 Agent C):
        # the previous code concatenated ``(n_fresh - n_prior, n_fresh)``
        # pad rows onto ``fresh["e"]`` -- yielding a
        # ``(2 * n_fresh - n_prior, n_fresh)`` intermediate -- and then
        # concatenated a ``(n_fresh, 1)`` pad column on axis 1. Axis 0
        # then mismatched (``2 * n_fresh - n_prior != n_fresh``) and
        # numpy raised ``ValueError: all the input array dimensions
        # except for the concatenation axis must match exactly``.
        # Trimming to ``n_prior`` rows before the axis-1 concat removes
        # the mismatch, and is behaviour-preserving: every padded row
        # was discarded by the final ``[:n_prior, :n_prior]`` slice.
        fresh_e_full = np.asarray(fresh["e"], dtype=np.int64)[:n_prior]
        n_cols_fresh = int(fresh_e_full.shape[1])
        if n_cols_fresh < n_prior:
            # Defensive: a non-square fresh bond matrix still has to
            # reach the prior's pair dim. Pad the missing columns with
            # the no-bond sentinel.
            pad_e_col = np.full(
                (n_prior, n_prior - n_cols_fresh),
                int(FLOWMOL3ADAPTER_N_BOND_TYPES) - 1,
                dtype=np.int64,
            )
            fresh_e_full = np.concatenate([fresh_e_full, pad_e_col], axis=1)
        fresh_e = fresh_e_full[:n_prior, :n_prior]
        # ``fresh["a"]`` is longer than the prior — trim (the previous
        # zero-pad was likewise discarded by the ``[:n_prior]`` slice).
        fresh_a = np.asarray(fresh["a"], dtype=np.int64)[:n_prior]
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
# CTMC helpers (Stage 3 of Workflow R — paper-correct kernel swap)
# ---------------------------------------------------------------------------


def _build_ctmc_rate_matrix(p: ArrayF64) -> ArrayF64:
    """Build the canonical "jump-to-stationary" CTMC rate matrix from ``p``.

    The FlowMol3 paper parameterizes the discrete (a, c, e) channels via
    CTMC. The canonical rate matrix whose stationary distribution is
    ``p`` (with rows summing to 0) is::

        Q[i, j] = p[j]  for i != j
        Q[i, i] = -(1 - p[i])

    This is the simplest valid CTMC kernel — rows sum to zero, and the
    stationary distribution is ``p`` (verify: ``Q @ p = 0``).

    Parameters
    ----------
    p : ``(K,)`` float64 probability simplex
        The model's predicted marginal distribution. Will be clipped to
        ``[eps, 1-eps]`` and renormalized to ensure a well-conditioned
        rate matrix.

    Returns
    -------
    Q : ``(K, K)`` float64 rate matrix (rows sum to 0).
    """
    p_arr = np.asarray(p, dtype=np.float64).reshape(-1)
    K = int(p_arr.shape[0])
    if K < 2:
        raise ValueError(
            f"_build_ctmc_rate_matrix: K must be >= 2; got {K}"
        )
    # Defensive clip + renormalize for numerical safety.
    eps = 1e-9
    p_arr = np.clip(p_arr, eps, 1.0 - eps)
    p_arr = p_arr / float(p_arr.sum())
    # Build Q: off-diagonal = p[j], diagonal = -(1 - p[i]).
    Q = np.broadcast_to(p_arr, (K, K)).copy()
    diag = -(1.0 - p_arr)
    np.fill_diagonal(Q, diag)
    # Verify row sums ~ 0.
    row_sums = Q.sum(axis=1)
    if not np.allclose(row_sums, 0.0, atol=1e-9):
        # Last-resort correction.
        Q[np.diag_indices(K)] -= row_sums
    return Q


def _to_one_hot(labels: ArrayF64, K: int) -> ArrayF64:
    """Convert integer labels ``(N,)`` to one-hot ``(N, K)`` float64."""
    labels_arr = np.asarray(labels, dtype=np.int64).reshape(-1)
    return np.eye(int(K), dtype=np.float64)[labels_arr]


def _make_Q_condition(Q_per_position: ArrayF64) -> Any:
    """Build an ODEConditionDelta carrying ``Q_per_position`` for CTMCDynamics.

    The CTMC solver reads ``condition.delta_spec['Q_per_position']`` to
    drive per-position rates (atom-specific or bond-pair-specific). The
    returned carrier is a plain namespace with the ``delta_spec``
    attribute; the CTMC path never branches on the rest of the carrier
    (no condition injection for FlowMol3).
    """
    from types import SimpleNamespace

    return SimpleNamespace(delta_spec={"Q_per_position": Q_per_position})


def _ctmc_real_velocity_field_ex(
    module: Any,
    x: ArrayF64,
    a: ArrayF64,
    c: ArrayF64,
    e: ArrayF64,
    t: float,
    *,
    device: str,
) -> tuple[ArrayF64, ArrayF64, ArrayF64, ArrayF64, ArrayF64, ArrayF64]:
    """CTMC-flavored real-weight evaluator returning ``(v_x, c_pred, p_a, p_c, p_e, v_x)``.

    For the CTMC swap, we need:
    * ``v_x``: continuous coordinate velocity (same as linear-interpolant
      path — paper uses continuous coords, not CTMC on coords).
    * ``c_pred``: predicted expected formal charge (continuous target).
    * ``p_a``: ``(n_atoms, K_atom)`` atom-type marginal.
    * ``p_c``: ``(n_atoms, K_charge)`` charge marginal.
    * ``p_e``: ``(n_atoms, n_atoms, K_bond)`` bond marginal.
    * ``v_x``: equivariant coordinate endpoint velocity (same as the
      linear-interpolant path).

    Returns
    -------
    tuple of (v_x, c_pred, p_a, p_c, p_e, v_x).
    ``v_x`` is duplicated so the unpacking matches the caller's
    expectation; the second copy is unused.
    """
    import torch  # noqa: PLC0415

    dev = torch.device(str(device))
    # NB: numpy 2.x compatibility — `torch.as_tensor(np_arr)` fails with
    # ``RuntimeError: Could not infer dtype of numpy.float32`` on
    # torch==2.2.0 because the internal ``_infer_dtype`` path uses
    # ``len(arr.dtype)`` which numpy 2.x no longer supports on 0-d/1-d
    # dtype objects. Passing an explicit ``dtype=torch.float32`` bypasses
    # the inference. Same fix in :func:`_ctmc_real_velocity_field_ex`.
    x_t = torch.as_tensor(
        np.asarray(x, dtype=np.float32), dtype=torch.float32
    ).to(dev).detach()
    n_atoms = int(x_t.shape[0])
    a_np = np.clip(
        np.asarray(a, dtype=np.int64), 0, FLOWMOL3ADAPTER_N_ATOM_TYPES - 1
    )
    a_tok = torch.as_tensor(a_np, dtype=torch.long).to(dev).detach()
    c_np = np.asarray(c, dtype=np.float64).reshape(n_atoms)
    c_idx = np.clip(
        np.rint(c_np).astype(np.int64) - int(FLOWMOL3_MODEL_CHARGE_VALUES[0]),
        0,
        FLOWMOL3_MODEL_CHARGE_LOGITS - 1,
    )
    c_tok = torch.as_tensor(c_idx, dtype=torch.long).to(dev).detach()
    e_np = np.asarray(e, dtype=np.int64).reshape(n_atoms, n_atoms)
    e_np = np.clip(e_np, 0, FLOWMOL3ADAPTER_N_BOND_TYPES - 1)
    e_model = np.asarray(FLOWMOL3_ADAPTER_TO_MODEL_BOND, dtype=np.int64)[e_np]
    e_tok = torch.as_tensor(e_model, dtype=torch.long).to(dev).detach()

    with torch.no_grad():
        t_emb = _flowmol3_time_embedding(
            float(t), FLOWMOL3_MODEL_TIME_DIM, device=dev, torch_mod=torch
        ).expand(n_atoms, FLOWMOL3_MODEL_TIME_DIM)
        atom_logits, charge_logits, edge_logits = module(a_tok, c_tok, e_tok, t_emb)
        atom_logits = atom_logits.detach()
        charge_logits = charge_logits.detach()
        edge_logits = edge_logits.detach()

        # Per-channel marginals for the CTMC swap.
        # Atom marginal: drop the fake-atom class. Use 11-wide marginal
        # so it covers the checkpoint's atom logit width (10 elements +
        # fake), but the adapter's CTMC over 10 elements — collapse the
        # 11th onto the prior's no-bond fallback.
        p_atom_logits = torch.softmax(atom_logits.float(), dim=-1)
        # Pad / project to (n_atoms, FLOWMOL3ADAPTER_N_ATOM_TYPES=10).
        p_a_full = p_atom_logits[:, :FLOWMOL3ADAPTER_N_ATOM_TYPES]
        # Normalize (defensive — softmax already sums to 1 but if we
        # dropped entries the sum < 1).
        p_a_sum = p_a_full.sum(dim=-1, keepdim=True).clamp_min(1e-9)
        p_a = p_a_full / p_a_sum

        # Charge marginal -> expected formal charge + 6-class simplex.
        p_c_logits = torch.softmax(charge_logits.float(), dim=-1)
        # numpy 2.x compat — explicit torch dtype bypasses the broken
        # ``_infer_dtype`` path that raises
        # ``RuntimeError: Could not infer dtype of numpy.float32`` on
        # torch==2.2.0.
        charge_values = torch.as_tensor(
            np.asarray(FLOWMOL3_MODEL_CHARGE_VALUES, dtype=np.float32),
            dtype=torch.float32,
        ).to(dev)
        c_pred = (p_c_logits * charge_values).sum(dim=-1)
        p_c = p_c_logits  # already 6-wide, sum to 1

        # Bond marginal, symmetrized, re-indexed to adapter vocab.
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

        # Coordinate endpoint velocity (equivariant). Same as linear
        # path — continuous x is NOT CTMC'd per paper.
        diff = x_t.unsqueeze(0) - x_t.unsqueeze(1)  # diff[i, j] = x_j - x_i
        dist = diff.norm(dim=-1)
        safe_dist = dist.clamp_min(1e-3)
        p_bond = 1.0 - p_e[:, :, FLOWMOL3ADAPTER_N_BOND_TYPES - 1]
        target_sep = (
            FLOWMOL3_BONDED_SEPARATION_A * p_bond
            + FLOWMOL3_NONBONDED_SEPARATION_A * (1.0 - p_bond)
        )
        step = ((safe_dist - target_sep) / safe_dist).unsqueeze(-1) * diff
        weight = p_bond + 0.05
        weight = weight.masked_fill(eye, 0.0)
        weight = weight / weight.sum(dim=1, keepdim=True).clamp_min(1e-6)
        x_pred = x_t + (weight.unsqueeze(-1) * step).sum(dim=1)

    inv_dt = 1.0 / max(1.0 - float(t), 1e-3)
    v_x = (
        x_pred.cpu().numpy().astype(np.float64)
        - np.asarray(x, dtype=np.float64).reshape(n_atoms, 3)
    ) * inv_dt
    c_pred_np = c_pred.cpu().numpy().astype(np.float64)
    p_a_np = p_a.cpu().numpy().astype(np.float64)
    p_c_np = p_c.cpu().numpy().astype(np.float64)
    p_e_np = p_e.cpu().numpy().astype(np.float64)
    return (
        np.nan_to_num(v_x, nan=0.0, posinf=0.0, neginf=0.0),
        c_pred_np,
        p_a_np,
        p_c_np,
        p_e_np,
        np.nan_to_num(v_x, nan=0.0, posinf=0.0, neginf=0.0),
    )


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

    #: Class-level toggle for the paper-correct CTMC swap.
    #:
    #: When ``True`` (the default, set in Stage 3 of Workflow R),
    #: :meth:`solve_ode` uses CTMC rate-matrix dynamics over the
    #: discrete (a, c, e) channels with stochastic categorical sampling
    #: on the final state — the paper-correct path that closes one of
    #: the three architectural gaps identified by Workflow Q
    #: (linear-interpolant ODE → CTMC, greedy argmax → stochastic
    #: categorical). Set to ``False`` to recover the prior linear-
    #: interpolant ODE + greedy argmax path for ablation studies.
    #:
    #: The continuous (x, c) channels always use the velocity-field
    #: integrator regardless of this toggle — the paper's CTMC swap
    #: targets only the discrete channels.
    ctmc_enabled: bool = True

    def __init__(
        self,
        *,
        backend: str = "numpy",
        num_steps: int = FLOWMOL3ADAPTER_NUM_STEPS_DEFAULT,
        seed_offset: int = 0,
        blender: RestartBlenderProtocol | None = None,
        weights_path: Any = None,
        device: str = "cpu",
        ctmc_enabled: bool | None = None,
        use_upstream: bool = False,
        upstream_repo_dir: str | None = None,
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
        # ``use_upstream`` is a hook for the §3.4 repair plan: when
        # ``True`` the adapter, on first ``_load_model()`` call, tries
        # to instantiate the upstream ``flowmol.models.flowmol.FlowMol``
        # via :func:`_try_import_upstream_flowmol` and a ``sys.path``
        # tweak. Default ``False`` preserves the partial-fidelity
        # behaviour the baseline workflow has been exercising. The
        # flag does nothing on the ``backend='numpy'`` path because
        # the upstream FlowMol is fundamentally a torch / DGL model.
        if use_upstream and backend != "torch":
            raise ValueError(
                "use_upstream_requires_backend_torch"
            )
        self._backend = backend
        self._num_steps = int(num_steps)
        self._seed_offset = int(seed_offset)
        self._weights_path = str(weights_path) if weights_path is not None else None
        self._device = str(device)
        self._use_upstream = bool(use_upstream)
        self._upstream_repo_dir = (
            str(upstream_repo_dir)
            if upstream_repo_dir is not None
            else FLOWMOL3ADAPTER_UPSTREAM_REPO_DIR
        )
        # Sentinel kind for ``model_metadata['kind']`` set when the
        # upstream load succeeded. ``None`` until first ``_load_model``
        # call. The default behaviour (no upstream) keeps the
        # historical ``"real"`` / ``"synthetic"`` kinds.
        self._upstream_flowmol_cls: Any = None
        self._upstream_import_error: str | None = None
        self._native_states: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._caps = FlowMol3V2AdapterCapabilities()
        self._blender: RestartBlenderProtocol = (
            blender if blender is not None else LinearBlender()
        )
        # CTMC swap toggle (Stage 3 of Workflow R). The class attribute
        # is the default; the constructor kwarg overrides per-instance.
        if ctmc_enabled is not None:
            self.ctmc_enabled = bool(ctmc_enabled)
        # Cache for the (lazy) torch model handle + per-n_atoms weight
        # matrices for the synthetic velocity field. Both are populated
        # on first use.
        self._model: Any = None
        self._model_meta: dict[str, Any] = {}

    @property
    def use_upstream(self) -> bool:
        """Return ``True`` iff the adapter was constructed with ``use_upstream=True``.

        Informational; reflects the constructor flag, not whether the
        upstream load ultimately succeeded (see ``model_metadata``.
        ``['kind']`` for the runtime kind and ``['upstream_import_error']``
        for the failure reason if the upstream load failed).
        """
        return self._use_upstream

    @property
    def upstream_import_error(self) -> str | None:
        """Return the reason upstream load failed, or ``None`` on success / not attempted.

        Populated on first ``_load_model()`` call when
        ``use_upstream=True``. ``None`` when the upstream import
        succeeded OR when ``use_upstream=False``.
        """
        return self._upstream_import_error

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
        Caches the module on ``self._model` and the parsed metadata on
        ``self._model_meta``.

        When ``use_upstream=True`` (the §3.4 repair-plan hook), the
        first call dispatches to :func:`_try_import_upstream_flowmol`
        instead of the partial-fidelity readout head, attempting to
        instantiate the canonical
        ``flowmol.models.flowmol.FlowMol`` from the cloned repo at
        ``upstream_repo_dir``. The upstream path requires both
        :mod:`dgl` and :mod:`torch_scatter` to be importable; if
        either fails the adapter records the error under
        :attr:`upstream_import_error` and falls back to the
        partial-fidelity path so the adapter stays runnable.

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
            self._model_meta = {
                "kind": "synthetic",
                "weights_path": None,
                FLOWMOL3ADAPTER_DGL_PROBE: bool(_probe_dgl()),
                "use_upstream": bool(self._use_upstream),
            }
            return self._model
        # ------------------------------------------------------------------
        # use_upstream=True dispatch (the §3.4 hook)
        # ------------------------------------------------------------------
        # Tries the upstream zavalab FlowMol3 import + checkpoint load.
        # On any failure (missing dgl / missing torch_scatter /
        # missing repo) records the reason in
        # ``self._upstream_import_error`` and falls back to the
        # partial-fidelity path so the adapter stays runnable.
        if self._use_upstream:
            upstream_cls, upstream_err = _try_import_upstream_flowmol(
                self._upstream_repo_dir,
            )
            if upstream_cls is not None:
                try:
                    ckpt = self._weights_path
                    upstream_model = upstream_cls.load_from_checkpoint(
                        ckpt, map_location=self._device, strict=False
                    )
                    upstream_model.eval()
                    self._upstream_flowmol_cls = upstream_cls
                    self._model = upstream_model
                    self._model_meta = {
                        "kind": FLOWMOL3ADAPTER_UPSTREAM_KIND,
                        "weights_path": str(self._weights_path),
                        "device": str(self._device),
                        FLOWMOL3ADAPTER_DGL_PROBE: bool(_probe_dgl()),
                        "use_upstream": True,
                        "upstream_repo_dir": str(self._upstream_repo_dir),
                        "upstream_class": str(upstream_cls),
                    }
                    return self._model
                except Exception as exc:  # noqa: BLE001 - permissive
                    # Upstream load raised at construction or
                    # ``load_from_checkpoint`` time — record and fall
                    # through to the partial-fidelity path below.
                    self._upstream_import_error = (
                        f"upstream_load_from_checkpoint_failed:"
                        f"{type(exc).__name__}:{exc}"
                    )
            else:
                self._upstream_import_error = upstream_err
        # ------------------------------------------------------------------
        # Default partial-fidelity readout head (existing behaviour)
        # ------------------------------------------------------------------
        config = _load_flowmol3_config(self._weights_path)
        loaded = _load_flowmol3_state_dict(self._weights_path)
        module = _build_flowmol3_velocity_module(
            loaded["state_dict"], device=self._device
        )
        self._model = module
        meta_kind = "real"
        # If use_upstream was requested but failed, surface that fact
        # in the meta block so a downstream reader can see the
        # partial-fidelity fallback rather than inferring it.
        if self._use_upstream and self._upstream_import_error is not None:
            meta_kind = "real_fallback_after_upstream_failure"
        self._model_meta = {
            "kind": meta_kind,
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
            FLOWMOL3ADAPTER_DGL_PROBE: bool(_probe_dgl()),
            "use_upstream": bool(self._use_upstream),
            "upstream_repo_dir": str(self._upstream_repo_dir),
        }
        if self._upstream_import_error is not None:
            self._model_meta["upstream_import_error"] = (
                self._upstream_import_error
            )
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
        """Cache-by-(n_atoms, seed) random-init weights for the synthetic field.

        Delegates to the module-level LRU-bounded
        :func:`_cached_synthetic_weights` (maxsize =
        :data:`FLOWMOL3ADAPTER_SYNTHETIC_WEIGHTS_MAXSIZE` = 8) so a
        long-running adapter cannot accumulate an unbounded number of
        weight arrays. The bound replaces the prior per-instance
        unbounded ``self._synthetic_weights`` dict.
        """
        cache_key = int(n_atoms)
        effective_seed = int(seed) + cache_key * 31
        return _cached_synthetic_weights(cache_key, effective_seed)

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

    def detach_and_validate_endpoint(self, bundle: StateBundle) -> StateBundle:
        """Fail-closed detach gate.

        The FlowMol3 restart contract requires ``.detach()`` at every
        ``model.integrate`` / ``model.step`` entry; this method
        re-validates the bundle and rejects when ``detach_proof`` is
        not ``True``.
        """
        ok, errs = validate_state_bundle(bundle)
        if not ok:
            raise CapabilityMissingError(
                "detach_proof_must_be_true", context=",".join(errs)
            )
        if bundle.detach_proof is not True:
            raise CapabilityMissingError("detach_proof_must_be_true")
        return bundle

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

        Dispatch (Stage 3 of Workflow R — CTMC kernel swap):

        * ``self.ctmc_enabled is True`` (default) — paper-correct CTMC
          path: continuous (x, c) evolve via the linear-interpolant ODE
          velocity field; discrete (a, e) evolve on the probability
          simplex via CTMC rate matrices derived from the model's
          predicted marginals; final state is sampled via stochastic
          categorical sampling. Uses
          :class:`CTMCDynamics` + :class:`CTMCEulerHeunSolver` + the
          :func:`stochastic_categorical_sample` helper from D1.
        * ``self.ctmc_enabled is False`` — pre-Stage-3 fallback: linear-
          interpolant ODE + greedy ``argmax`` for ablation studies.
        * ``self._model_kind == 'upstream_flowmol'`` — full upstream
          GVP path: bypass the per-step velocity-field bridge (which
          calls into ``FlowMol.forward(g)`` expecting a dgl graph and
          raises a ``TypeError`` on the (x_t, t) call convention the
          protocol expects) and instead call the upstream's own
          end-to-end :meth:`FlowMol.sample` entrypoint with a single
          batch entry of size ``n_atoms``. The trajectory buffer is
          then populated from the resulting
          :class:`SampledMolecule` so
          :meth:`export_trajectory` + RDKit validity are well-defined.
        """
        # ------------------------------------------------------------------
        # Upstream GVP fast-path (closes P-22 forward()-signature gap).
        # ------------------------------------------------------------------
        # ``FlowMol.forward(self, g: dgl.DGLGraph)`` is the *training*
        # forward — it takes a dgl graph, samples interpolants, computes
        # losses. The protocol convention is a per-step velocity-field
        # call ``f(x_t, t) -> tensor`` that returns ``(v_x, v_c, v_e, v_a)``.
        # Bridging these requires building a dgl graph at every solver
        # step (the upstream has its own edge-batch indices via
        # ``build_edge_idxs`` + ``get_upper_edge_mask``), which is doable
        # but duplicative: the upstream already has an end-to-end
        # :meth:`FlowMol.sample` entrypoint that does prior sampling +
        # GVP inference + RDKit materialization in one shot. We route to
        # that. The per-step velocity-field bridge is only needed when
        # the upstream is unavailable (the partial-fidelity path) or the
        # caller asks for it explicitly (``ctmc_enabled=False``).
        if self._use_upstream and self._loaded_model_kind() == "upstream_flowmol":
            return self._solve_ode_upstream(state, condition, seed=int(seed))
        if self.ctmc_enabled:
            return self._solve_ode_ctmc(state, condition, seed=int(seed))
        return self._solve_ode_linear(state, condition, seed=int(seed))

    def _loaded_model_kind(self) -> str:
        """Return the kind label of the loaded model (or ``"synthetic"`` if none).

        Cached after first ``_load_model()`` call. Mirrors the values
        written to ``model_metadata['kind']`` so the upstream dispatch
        does not need to re-probe the model object on every
        :meth:`solve_ode` call.
        """
        if self._model is None:
            return "synthetic"
        return str(self._model_meta.get("kind", "synthetic"))

    def _solve_ode_upstream(
        self,
        state: StateBundle,
        condition: ODEConditionDelta,
        *,
        seed: int,
    ) -> ODEIntegratorTrace:
        """End-to-end upstream :meth:`FlowMol.sample` path (P-22 close-out).

        This is the *paper-correct* path: the upstream zavalab FlowMol3
        implementation owns its own prior sampling, CTMC step (when
        ``parameterization='ctmc'``), and ``integrate`` loop. Trying to
        re-implement those in the adapter would either rewrite the GVP
        from scratch (forbidden) or call into ``FlowMol.forward(g)``
        with a tensor instead of a dgl graph (the original P-22
        TypeError).

        Instead we delegate to ``self._model.sample`` with one batch
        entry of size ``n_atoms`` (drawn from the prior entry's
        ``n_atoms``). The resulting :class:`SampledMolecule` carries the
        final ``(x, a, c, e)`` plus its built ``rdkit_mol``; we
        extract the four channels back into the adapter's native-state
        lineage so :meth:`export_trajectory` + the protocol surface
        stay intact.

        Per the FlowMol3 restart contract, the entire call is wrapped
        in ``torch.no_grad()`` (FlowMol.sample is already decorated
        ``@torch.no_grad``) and we re-detach the cached tensors before
        the lineage is published.
        """
        import torch  # noqa: PLC0415 — torch backend only.
        try:
            from rdkit import Chem  # noqa: PLC0415 — only on upstream path.
        except Exception:  # noqa: BLE001 — RDKit absent means no SMILES cache.
            Chem = None  # type: ignore[assignment]

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
        n_atoms = int(prior_entry["n_atoms"])
        num_steps = int(condition.delta_spec.get("num_steps", self._num_steps))
        if num_steps <= 0:
            raise ValueError("num_steps_must_be_positive")

        # Hand the (x, a, c, e) prior to the upstream's sample() via the
        # ``prior`` dict — the upstream pads/aligns to its batched
        # graph's ndata shape. Convert to torch on the requested device.
        dev = torch.device(str(self._device))
        n = int(n_atoms)
        x0_np = np.asarray(prior_entry["x"], dtype=np.float32).reshape(n, 3)
        # Atom-type prior: shape (n, n_atom_types_upstream + 1). The
        # upstream's ``ctmc_masked_prior(n, d)`` produces ``(n, d+1)``
        # with the mask token at index ``d`` (= ``n_atom_types``).
        # ``n_atom_types`` already includes the fake-atom class when
        # ``fake_atoms=True`` (the published CTMC checkpoint was trained
        # with ``fake_atom_p > 0`` so ``n_atom_types == 11``).
        a_np = np.asarray(prior_entry["a"], dtype=np.int64).reshape(n)
        n_atom_types_upstream = int(getattr(self._model, "n_atom_types", 11))
        # We supply a "fully unmasked" prior — every atom starts at the
        # sampled adapter label (0..9), and we place the mask token at
        # its dedicated index so the CTMC step sees a clean one-hot for
        # each class.
        a0_one_hot = np.zeros(
            (n, n_atom_types_upstream + 1), dtype=np.float32
        )
        clipped = np.clip(a_np, 0, n_atom_types_upstream - 1)
        for i in range(n):
            a0_one_hot[i, int(clipped[i])] = 1.0
        # Charge prior: shape (n, n_atom_charges + 1) with the CTMC mask
        # at index ``n_atom_charges`` (== 6).
        c_np = np.asarray(prior_entry["c"], dtype=np.float64).reshape(n)
        c_idx = np.clip(
            np.rint(c_np).astype(np.int64) + 2, 0, int(
                getattr(self._model, "n_atom_charges", 6)
            ) - 1
        )
        n_charge_classes = int(getattr(self._model, "n_atom_charges", 6))
        c0_one_hot = np.zeros((n, n_charge_classes + 1), dtype=np.float32)
        for i in range(n):
            c0_one_hot[i, int(c_idx[i])] = 1.0
        # Edge prior: shape (n_pairs, n_bond_types + 1). The upstream's
        # ``explicit_aromaticity=False`` ⇒ ``n_bond_types == 4``; the
        # mask sits at index 4. The adapter's bond labels (0..4) fold
        # onto the upstream's 0..3 (0 = no-bond, 1 = single, 2 = double,
        # 3 = triple) via ``FLOWMOL3_ADAPTER_TO_MODEL_BOND``.
        e_np = np.asarray(prior_entry["e"], dtype=np.int64).reshape(n, n)
        e_np = np.clip(e_np, 0, FLOWMOL3ADAPTER_N_BOND_TYPES - 1)
        e_model_lbl = np.asarray(FLOWMOL3_ADAPTER_TO_MODEL_BOND,
                                  dtype=np.int64)[e_np]
        n_bond_types_upstream = int(getattr(self._model, "n_bond_types", 4))
        e0_one_hot_full = np.zeros(
            (n, n, n_bond_types_upstream + 1), dtype=np.float32
        )
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                e0_one_hot_full[i, j, int(e_model_lbl[i, j])] = 1.0
        upper_idx = np.triu_indices(n, k=1)
        e0_ut = e0_one_hot_full[upper_idx[0], upper_idx[1]]
        # FlowMol's dgl graph stores edges as upper-triangle first, then
        # lower-triangle (mirrored). ``build_edge_idxs`` returns
        # ``[upper, lower]`` concatenated — so the prior ``e_0`` must
        # carry both halves, NOT just the upper-triangle. Doubling the
        # upper-tensor here is the cheapest correct fix; the upstream's
        # ``integrate`` step symmetrises via ``e_t[~upper_edge_mask] =
        # e_t[upper_edge_mask]`` so duplicating is safe.
        e0_full = np.concatenate([e0_ut, e0_ut], axis=0)
        prior_dict: dict[str, Any] = {
            "x_0": torch.as_tensor(x0_np, dtype=torch.float32).to(dev),
            "a_0": torch.as_tensor(a0_one_hot, dtype=torch.float32).to(dev),
            "c_0": torch.as_tensor(c0_one_hot, dtype=torch.float32).to(dev),
            "e_0": torch.as_tensor(e0_full, dtype=torch.float32).to(dev),
            "fake_atoms": bool(getattr(self._model, "fake_atoms", False)),
        }

        n_atoms_tensor = torch.as_tensor([int(n)], dtype=torch.long,
                                          device=dev)
        with torch.no_grad():
            sampled = self._model.sample(
                n_atoms=n_atoms_tensor,
                n_timesteps=int(num_steps),
                device=str(self._device),
                prior=prior_dict,
            )
        # ``sampled`` is a list with one SampledMolecule (single-mol batch).
        mol = sampled[0]
        # The upstream ``SampledMolecule`` constructor already filters
        # out the CTMC mask + fake-atom tokens via ``extract_moldata_from_graph``
        # and exposes the *clean* arrays as ``positions`` (torch tensor),
        # ``atom_types`` (LIST of element-symbol STRINGS like
        # ``['H', 'C', 'N']``), ``atom_charges`` (torch tensor of formal
        # charges in [-2, +3]), and ``bond_types`` / ``bond_src_idxs`` /
        # ``bond_dst_idxs`` (tensors in the upstream's kekulized
        # vocabulary 0..3). Use those directly — bypassing the dgl graph's
        # ndata (which still carries the mask/fake tokens and would
        # produce shape mismatches on the post-CTMC atom count).
        n_final = int(mol.num_atoms)
        x_final = np.asarray(
            mol.positions.detach().cpu().numpy()
            if hasattr(mol.positions, "detach") else mol.positions,
            dtype=np.float64,
        ).reshape(n_final, 3)
        # Atom types are element SYMBOLS — map them to the adapter's
        # 10-wide integer vocabulary via the upstream's ``atom_type_map``.
        upstream_atom_map = list(getattr(self._model, "atom_type_map", []))
        # The model attribute already has the 10-element GEOM-Drugs vocab
        # (it appends 'Sn' / 'Se' at runtime for fake / mask tokens,
        # which have been filtered out by this point).
        elem_to_idx = {sym: i for i, sym in enumerate(upstream_atom_map)}
        a_idx = np.asarray(
            [int(elem_to_idx.get(str(s), 0)) for s in mol.atom_types],
            dtype=np.int64,
        ).reshape(n_final)
        # Atom charges — already decoded (subtract the +2 offset).
        c_idx_arr = np.asarray(
            mol.atom_charges.detach().cpu().numpy()
            if hasattr(mol.atom_charges, "detach") else mol.atom_charges,
            dtype=np.int64,
        ).reshape(n_final)
        c_final = c_idx_arr.astype(np.float64).reshape(n_final)
        # Edges: ``mol`` exposes ``bond_src_idxs`` / ``bond_dst_idxs`` /
        # ``bond_types`` in upstream class indices (kekulized: 0..3).
        # Reconstruct the symmetric ``(n, n)`` adapter bond label.
        e_full_model = np.full(
            (n_final, n_final),
            FLOWMOL3ADAPTER_N_BOND_TYPES - 1,
            dtype=np.int64,
        )
        b_src = np.asarray(
            mol.bond_src_idxs.detach().cpu().numpy()
            if hasattr(mol.bond_src_idxs, "detach") else mol.bond_src_idxs,
            dtype=np.int64,
        )
        b_dst = np.asarray(
            mol.bond_dst_idxs.detach().cpu().numpy()
            if hasattr(mol.bond_dst_idxs, "detach") else mol.bond_dst_idxs,
            dtype=np.int64,
        )
        b_types = np.asarray(
            mol.bond_types.detach().cpu().numpy()
            if hasattr(mol.bond_types, "detach") else mol.bond_types,
            dtype=np.int64,
        )
        # Clip to the upstream's emitted vocabulary (no CTMC mask on the
        # final graph; 0..3).
        b_types = np.clip(b_types, 0, int(n_bond_types_upstream) - 1)
        # Map upstream (kekulized) bond labels back to the adapter's
        # (single, double, triple, aromatic, no-bond) vocabulary.
        inv_map = np.asarray(FLOWMOL3_MODEL_TO_ADAPTER_BOND + (4,),
                              dtype=np.int64)
        adapter_labels = inv_map[b_types]
        # Mirror upper-triangle to lower-triangle (cosmetic — the RDKit
        # writer only reads the upper triangle).
        e_full_model[b_src, b_dst] = adapter_labels
        np.fill_diagonal(e_full_model, FLOWMOL3ADAPTER_N_BOND_TYPES - 1)
        # Atom-type labels: re-map to adapter's 10-wide vocabulary
        # (mask / fake already filtered by the upstream).
        n_atom_types_adapter = FLOWMOL3ADAPTER_N_ATOM_TYPES
        a_final = np.where(
            a_idx < n_atom_types_adapter, a_idx, 0
        ).astype(np.int64).reshape(n_final)

        # Build per-step trajectory lineage. The upstream does not expose
        # the per-step (x, a, c, e) lineage (only the final graph); we
        # record the final state at every step index so the trajectory
        # buffer has the right shape and ``export_trajectory`` returns
        # the same ``(num_steps+1, ...)`` shape as the linear path.
        traj_x = np.tile(x_final[None, :, :], (num_steps + 1, 1, 1))
        traj_c = np.tile(c_final[None, :], (num_steps + 1, 1))
        traj_e = np.tile(e_full_model[None, :, :], (num_steps + 1, 1, 1))
        traj_a = np.tile(a_final[None, :], (num_steps + 1, 1))
        t_grid = np.linspace(0.0, 1.0, num_steps + 1, dtype=np.float64)

        traj_digest = _digest_state(
            {
                "kind": "trajectory",
                "src_digest": str(state.native_state_digest),
                "backend": "torch-upstream",
                "num_steps": int(num_steps),
                "n_atoms": int(n_final),
                "x_final_hash": str(
                    hashlib.sha256(np.asarray(x_final).tobytes()).hexdigest()
                ),
                "c_final_hash": str(
                    hashlib.sha256(np.asarray(c_final).tobytes()).hexdigest()
                ),
                "e_final_hash": str(
                    hashlib.sha256(np.asarray(e_full_model).tobytes()).hexdigest()
                ),
                "seed": int(seed),
            }
        )
        self._put_native_state(
            traj_digest,
            {
                "traj_x": traj_x,
                "traj_c": traj_c,
                "traj_e": traj_e,
                "traj_a": traj_a,
                "t_grid": t_grid,
                "n_atoms": int(n_final),
                "audit": (AUDIT_FLOWMOL3_TRAJECTORY_BUILT,
                          "flowmol3adapter_upstream_gvp"),
                "rdkit_mol_smiles": (
                    str(Chem.MolToSmiles(mol.rdkit_mol))
                    if mol.rdkit_mol is not None
                    else ""
                ),
            },
        )
        cfg_blob = repr(
            (
                "flowmol3adapter_config",
                "torch-upstream",
                int(num_steps),
                int(seed),
                FLOWMOL3ADAPTER_PINNED_COMMIT,
                "upstream_sample",
            )
            + (
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

    def _solve_ode_linear(
        self,
        state: StateBundle,
        condition: ODEConditionDelta,
        *,
        seed: int,
    ) -> ODEIntegratorTrace:
        """Pre-Stage-3 fallback: linear-interpolant ODE + greedy argmax.

        Kept verbatim for ablation studies (set ``ctmc_enabled=False``).
        Identical to the Stage 2 implementation; the only thing that
        changed is the dispatch wrapper in :meth:`solve_ode`.
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

    def _solve_ode_ctmc(
        self,
        state: StateBundle,
        condition: ODEConditionDelta,
        *,
        seed: int,
    ) -> ODEIntegratorTrace:
        """Paper-correct CTMC path (Stage 3 of Workflow R).

        Discrete channels ``a`` (atom types) and ``e`` (bond types) are
        evolved on the probability simplex via :class:`CTMCDynamics`
        with a per-position rate matrix derived from the model's
        predicted marginal ``p``. The continuous channels ``x`` (coords)
        and ``c`` (formal charges) keep the linear-interpolant ODE
        velocity field (per the paper: only the discrete channels are
        CTMC'd).

        The integrator is :class:`CTMCEulerHeunSolver` with
        ``stochastic_sample=True`` — the final state is sampled via
        :func:`stochastic_categorical_sample`, replacing the pre-Stage-3
        greedy ``np.argmax``.

        Per-step lineage is preserved (the trajectory buffers hold the
        discrete labels post-sample, so
        :meth:`export_trajectory` returns the same shape as the linear
        path).
        """
        from adaptive_reflow.algorithm.dynamics import (
            CTMCDynamics,
            stochastic_categorical_sample,
        )
        from adaptive_reflow.algorithm.solver import CTMCEulerHeunSolver

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

        # Pre-compute the bond-logit cache for the synthetic backend.
        # The synthetic velocity field does not produce atom/bond/charge
        # marginals; for the CTMC path we need them. On the synthetic
        # path we use a uniform prior as the predicted marginal (which
        # makes CTMC equivalent to uniform categorical sampling — the
        # same behaviour as the linear interpolant's tie at the limit).
        is_torch_real = (
            self._backend == "torch"
            and self._weights_path is not None
            and _torch_is_available()
        )

        for i in range(1, num_steps + 1):
            t_cur = float(t_grid[i - 1])
            t_next = float(t_grid[i])
            dt = float(t_next - t_cur)
            # Detach before the velocity evaluation (restart contract).
            x_eval = np.asarray(x_cur, dtype=np.float64)
            c_eval = np.asarray(c_cur, dtype=np.float64)
            e_eval = np.asarray(e_cur, dtype=np.int64)
            a_eval = np.asarray(a_cur, dtype=np.int64)
            if is_torch_real:
                # Real-weights path: evaluate via the CTMC-flavored
                # helper which returns (v_x, c_pred, p_a, p_c, p_e, v_x).
                _vx, c_pred, p_a_marg, p_c_marg, p_e_marg, _vx_dup = (
                    _ctmc_real_velocity_field_ex(
                        self._model,
                        x_eval,
                        a_eval,
                        c_eval,
                        e_eval,
                        t_cur,
                        device=self._device,
                    )
                )
                # Continuous channels: linear-interpolant ODE.
                v_x = _vx
                v_c = (np.asarray(c_pred, dtype=np.float64) - c_eval) / max(
                    1.0 - t_cur, 1e-3
                )
                x_cur = x_cur + dt * v_x
                c_cur = c_eval + dt * v_c
                # Discrete channels: CTMC on the simplex. We evolve
                # the per-position categorical distribution via
                # CTMCDynamics.step with per-position Q derived from
                # p_a, p_e. CTMCEulerHeunSolver integrates the
                # simplex state; stochastic_categorical_sample at the
                # end produces the discrete label.
                # Atom types: per-atom Q via Q_per_position
                # (n_atoms, K_atom, K_atom).
                Q_a_per = np.empty(
                    (n_atoms, FLOWMOL3ADAPTER_N_ATOM_TYPES,
                     FLOWMOL3ADAPTER_N_ATOM_TYPES),
                    dtype=np.float64,
                )
                for k in range(n_atoms):
                    Q_a_per[k] = _build_ctmc_rate_matrix(p_a_marg[k])
                s_a = _to_one_hot(a_eval, FLOWMOL3ADAPTER_N_ATOM_TYPES)
                atom_dynamics = CTMCDynamics(
                    rate_matrix=Q_a_per[0],  # any one (will be overridden)
                    max_batch_size=int(max(n_atoms, 1)),
                )
                atom_solver = CTMCEulerHeunSolver(stochastic_sample=False)
                atom_traj = atom_solver.integrate(
                    atom_dynamics,
                    s_a,
                    np.asarray([t_cur, t_next], dtype=np.float64),
                    condition=_make_Q_condition(Q_a_per),
                    seed=int(seed) + i * 31,
                )
                s_a_final = np.asarray(atom_traj.states[-1], dtype=np.float64)
                a_cur = stochastic_categorical_sample(
                    s_a_final, seed=int(seed) + i * 31 + 7
                ).astype(np.int64)
                # Bond types (per-pair). Q_per_position is
                # (n_pairs, K_bond, K_bond).
                upper_idx = np.triu_indices(n_atoms, k=1)
                n_pairs = int(upper_idx[0].size)
                p_e_ut = p_e_marg[upper_idx[0], upper_idx[1]]
                Q_e_per = np.empty(
                    (n_pairs, FLOWMOL3ADAPTER_N_BOND_TYPES,
                     FLOWMOL3ADAPTER_N_BOND_TYPES),
                    dtype=np.float64,
                )
                for k in range(n_pairs):
                    Q_e_per[k] = _build_ctmc_rate_matrix(p_e_ut[k])
                s_e = _to_one_hot(
                    e_eval[upper_idx], FLOWMOL3ADAPTER_N_BOND_TYPES
                )
                bond_dynamics = CTMCDynamics(
                    rate_matrix=Q_e_per[0],  # any one (will be overridden)
                    max_batch_size=int(max(n_pairs, 1)),
                )
                bond_solver = CTMCEulerHeunSolver(stochastic_sample=False)
                bond_traj = bond_solver.integrate(
                    bond_dynamics,
                    s_e,
                    np.asarray([t_cur, t_next], dtype=np.float64),
                    condition=_make_Q_condition(Q_e_per),
                    seed=int(seed) + i * 31 + 13,
                )
                s_e_final = np.asarray(bond_traj.states[-1], dtype=np.float64)
                e_ut = stochastic_categorical_sample(
                    s_e_final, seed=int(seed) + i * 31 + 19
                ).astype(np.int64)
                e_new = np.full(
                    (n_atoms, n_atoms),
                    FLOWMOL3ADAPTER_N_BOND_TYPES - 1,
                    dtype=np.int64,
                )
                e_new[upper_idx] = e_ut
                # Mirror the upper-triangle draws to the lower triangle
                # via the transposed index (no double-counting). The
                # original ``e_new + e_new.T - diag`` doubled the
                # upper values (upper + lower = e_ut + 4 = up to 8).
                e_new[(upper_idx[1], upper_idx[0])] = e_ut
                # Force no self-bonds on the diagonal.
                np.fill_diagonal(e_new, FLOWMOL3ADAPTER_N_BOND_TYPES - 1)
                e_cur = e_new
            else:
                # Synthetic / fallback path: linear ODE + uniform
                # CTMC marginal. Falls back to greedy argmax on the
                # synthetic field's continuous-relaxation logits.
                v_x, v_c, v_e, v_a = self._velocity_field_ex(
                    x=x_eval,
                    c=c_eval,
                    e=e_eval,
                    t=t_cur,
                    n_atoms=n_atoms,
                    seed=int(seed),
                    a=a_eval,
                )
                x_cur = x_cur + dt * np.asarray(v_x, dtype=np.float64)
                c_cur = c_cur + dt * np.asarray(v_c, dtype=np.float64)
                e_logits = (
                    np.eye(
                        int(FLOWMOL3ADAPTER_N_BOND_TYPES), dtype=np.float64
                    )[e_cur]
                    + dt * np.asarray(v_e, dtype=np.float64)
                )
                e_cur = np.argmax(e_logits, axis=-1).astype(np.int64)
                if v_a is not None:
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
                        np.eye(
                            int(FLOWMOL3ADAPTER_N_ATOM_TYPES), dtype=np.float64
                        )[a_cur]
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
                "ctmc": True,
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
                "ctmc",
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
    ctmc_enabled: bool | None = None,
) -> FlowMol3V2Adapter:
    """Return a fresh :class:`FlowMol3V2Adapter` for tests + registry wiring.

    ``weights_path`` (with ``backend='torch'``) points at a published
    FlowMol3 PyTorch Lightning checkpoint — e.g.
    ``data/flowmol3/weights_real/checkpoints/last.ckpt``. Leave it
    ``None`` for the deterministic synthetic field.

    ``ctmc_enabled`` (Stage 3 of Workflow R) toggles the paper-correct
    CTMC swap (default ``True`` via the class attribute). Pass
    ``ctmc_enabled=False`` to recover the pre-Stage-3 linear-interpolant
    ODE path for ablation studies.
    """
    return FlowMol3V2Adapter(
        backend=str(backend),
        num_steps=int(num_steps),
        weights_path=weights_path,
        device=str(device),
        ctmc_enabled=ctmc_enabled,
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