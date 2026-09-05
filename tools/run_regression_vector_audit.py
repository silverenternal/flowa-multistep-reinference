#!/usr/bin/env python3
"""D.4 regression-vector audit tool (Wave 32 + Wave 33 batches 2 + 3, 12/18).

Generates and verifies pinned regression vectors for adapter conformance:

* :class:`adaptive_reflow.adapters.twodim_fm.TwoDimFMAdapter`
  (CPU-only; 2D rectified flow).
* :class:`adaptive_reflow.adapters.flowmol3_v2_adapter.FlowMol3V2Adapter`
  (NumPy backend; molecule generator).
* :class:`adaptive_reflow.adapters.lineageflow.LineageFlowAdapter`
  (synthetic mode; protein).
* :class:`adaptive_reflow.adapters.kanzi.KanziAdapter`
  (synthetic mode; protein flow-AE).
* :class:`adaptive_reflow.adapters.freqflow.FreqFlowAdapter`
  (synthetic mode; image SiT-XL/2).
* :class:`adaptive_reflow.adapters.mnist_fm.MnistFmAdapter`
  (CPU-only; MNIST rectified flow, RK4 integrator, random-init weights).
* :class:`adaptive_reflow.adapters.self_flow.SelfFlowAdapter`
  (synthetic mode; image SiT-XL/2, latent).
* :class:`adaptive_reflow.adapters.rectified_flow_cifar.RectifiedFlowCIFARAdapter`
  (synthetic mode; CIFAR-10 rectified flow).
* :class:`adaptive_reflow.adapters.toy_gaussian.ToyGaussianAdapter`
  (CPU-only; scalar Gaussian flow, 1D).
* :class:`adaptive_reflow.adapters.toy_linear.ToyLinearAdapter`
  (CPU-only; placeholder scalar flow).
* :class:`adaptive_reflow.adapters.graphbfn.GraphBFNAdapter`
  (synthetic mode; GraphBFN Bayesian update, QM9).
* :class:`adaptive_reflow.adapters.lumina_image_2_0.LuminaImage20Adapter`
  (synthetic mode; 16x128x128 latent flow matching).

Per the Wave 32 gap plan (``todo/gap-plan-wave32.md`` #1 + ``todo/algo-improvement-D4-regression-vectors.md``),
this is the Wave 33 Agent B **batch 2** of D.4 (7 of 18; Wave 32 batch 1
= 5; Wave 33 Agent C batch 3 = 6). After all 3 batches ship, D.4 is
**18/18 = MET** (HARD gate).

What a vector captures (per adapter):
* ``seed``: RNG seed (3 seeds swept: 41, 42, 43).
* ``input_id``: canonical ``batch_id`` + ``sample_id`` (synthetic).
* ``nfe``: ODE solver step count (3 NFEs swept: 5, 10, 50).
* ``host_fingerprint``: SHA-256 over the locked environment
  (``env_hash.txt`` composite_hash field).
* ``output_sha256``: SHA-256 over the canonicalised trajectory
  (initial state, trajectory, endpoint, integrator config).
* ``captured_at``: ISO 8601 UTC timestamp.

Each adapter produces 3 * 3 = **9 hashes** stored in
``regression-vectors/<adapter>.json``. The CI test
``tests/test_adapters/test_regression_vectors.py`` re-runs every
adapter with the same ``(seed, input, NFE)`` and asserts each hash
matches the recorded hash on the same host fingerprint.

Usage::

    python tools/run_regression_vector_audit.py generate    # write all 12 vectors
    python tools/run_regression_vector_audit.py verify      # re-run + assert match
    python tools/run_regression_vector_audit.py --adapter mnist_fm generate

Exit codes:

* 0 -- every recorded hash matches on verify; generate wrote valid vectors.
* 1 -- at least one recorded hash mismatched (regression); or generate
  failed to produce vectors for an adapter.

References:

* ``todo/algo-improvement-D4-regression-vectors.md`` (Wave 33 #1 plan).
* ``framework-internal-metrics.md`` rev 2 §1 D.4 (HARD gate).
* ``framework-freeze-checklist.md`` MUST-1 (D.4 is a HARD gate blocker).
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import subprocess
import sys
import time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Make `adaptive_reflow` importable when this script is invoked
# directly (not via ``python -m tools.run_regression_vector_audit``).
_ADAPTIVE_REFLOW_PARENT = _REPO_ROOT
if str(_ADAPTIVE_REFLOW_PARENT) not in sys.path:
    sys.path.insert(0, str(_ADAPTIVE_REFLOW_PARENT))


# ---------------------------------------------------------------------------
# Sweep configuration (3 seeds * 3 NFEs = 9 conditions per adapter)
# ---------------------------------------------------------------------------

SEEDS: tuple[int, ...] = (41, 42, 43)
NFES: tuple[int, ...] = (5, 10, 50)

# Canonical synthetic input ids used across all adapters. We use a
# fixed (batch_id, sample_id) per seed so the vector is fully
# reproducible from (adapter, seed, NFE) alone.
def _input_ids_for_seed(seed: int) -> tuple[str, str]:
    return (f"d4-b{seed}", f"d4-s{seed}")


# ---------------------------------------------------------------------------
# Adapter registry: a tiny dispatch table to keep generate/verify symmetric
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AdapterSpec:
    """Adapter configuration consumed by generate + verify."""

    name: str           # file-system name + adapter import key
    module: str         # dotted module path
    adapter_cls: str    # class name within module
    version_constant: str  # module-level config version string


# Twelve adapters across Wave 32 (5) + Wave 33 batch 2 (7) = 12/18.
# Wave 33 Agent B batch 2 (7 adapters) and Agent C batch 3 (6 adapters)
# combined complete the D.4 HARD gate (18/18 = MET).
# Each spec is loaded lazily inside the runner so a single broken
# import does not block the other adapters.
ADAPTER_SPECS: tuple[AdapterSpec, ...] = (
    AdapterSpec(
        name="flowmol3_v2",
        module="adaptive_reflow.adapters.flowmol3_v2_adapter",
        adapter_cls="FlowMol3V2Adapter",
        version_constant="FLOWMOL3ADAPTER_CONFIG_VERSION",
    ),
    AdapterSpec(
        name="twodim_fm",
        module="adaptive_reflow.adapters.twodim_fm",
        adapter_cls="TwoDimFMAdapter",
        version_constant="TWODIM_FM_CONFIG_VERSION",
    ),
    AdapterSpec(
        name="lineageflow",
        module="adaptive_reflow.adapters.lineageflow",
        adapter_cls="LineageFlowAdapter",
        version_constant="LINEAGEFLOW_CONFIG_VERSION",
    ),
    AdapterSpec(
        name="kanzi",
        module="adaptive_reflow.adapters.kanzi",
        adapter_cls="KanziAdapter",
        version_constant="KANZI_CONFIG_VERSION",
    ),
    AdapterSpec(
        name="freqflow",
        module="adaptive_reflow.adapters.freqflow",
        adapter_cls="FreqFlowAdapter",
        version_constant="FREQ_FLOW_CONFIG_VERSION",
    ),
    AdapterSpec(
        name="mnist_fm",
        module="adaptive_reflow.adapters.mnist_fm",
        adapter_cls="MnistFmAdapter",
        version_constant="MNIST_FM_CONFIG_VERSION",
    ),
    AdapterSpec(
        name="self_flow",
        module="adaptive_reflow.adapters.self_flow",
        adapter_cls="SelfFlowAdapter",
        version_constant="SELF_FLOW_CONFIG_VERSION",
    ),
    AdapterSpec(
        name="rectified_flow_cifar",
        module="adaptive_reflow.adapters.rectified_flow_cifar",
        adapter_cls="RectifiedFlowCIFARAdapter",
        version_constant="RF_CIFAR_CONFIG_VERSION",
    ),
    AdapterSpec(
        name="toy_gaussian",
        module="adaptive_reflow.adapters.toy_gaussian",
        adapter_cls="ToyGaussianAdapter",
        version_constant="NATIVE_CONFIG_VERSION",
    ),
    AdapterSpec(
        name="toy_linear",
        module="adaptive_reflow.adapters.toy_linear",
        adapter_cls="ToyLinearAdapter",
        version_constant="NATIVE_CONFIG_VERSION",
    ),
    AdapterSpec(
        name="graphbfn",
        module="adaptive_reflow.adapters.graphbfn",
        adapter_cls="GraphBFNAdapter",
        version_constant="GRAPHBFN_CONFIG_VERSION",
    ),
    AdapterSpec(
        name="lumina_image_2_0",
        module="adaptive_reflow.adapters.lumina_image_2_0",
        adapter_cls="LuminaImage20Adapter",
        version_constant="LUMINA_IMAGE_2_0_CONFIG_VERSION",
    ),
)


# ---------------------------------------------------------------------------
# Host fingerprint capture
# ---------------------------------------------------------------------------

def _read_env_composite_hash() -> str:
    """Return the composite_hash from ``env_hash.txt`` (or empty string)."""
    env_path = _REPO_ROOT / "env_hash.txt"
    if not env_path.exists():
        return ""
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("composite_hash="):
                return line.split("=", 1)[1].strip()
    except OSError:
        return ""
    return ""


def _git_short_sha() -> str:
    """Return the current git short SHA, or ``unknown`` if unavailable."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(_REPO_ROOT),
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        return out.decode("utf-8").strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return "unknown"


# ---------------------------------------------------------------------------
# Canonical-hash machinery (shared by generate + verify)
# ---------------------------------------------------------------------------

def _canonical_dumps(obj: Any) -> bytes:
    """Deterministic JSON dump used as the hash pre-image.

    We use ``sort_keys=True`` + ``separators=(",", ":")`` so the bytes
    stream is stable across Python invocations and platform line
    endings. The hash is over the canonical JSON form only.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def _sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _summarise_state_bundle(bundle: Any) -> dict[str, Any]:
    """Project a StateBundle into a JSON-friendly hash pre-image.

    We deliberately avoid hashing full numpy/tensor bytes: the
    contract is "summary statistics, deterministic across the same
    adapter+seed+input+NFE on the same host". The summary captures
    the bytes-stable identity surface (digest strings, source_round,
    channel keys, provenance tuple) and a digest over the
    underlying native-state entry's bytes when present.
    """
    summary: dict[str, Any] = {
        "kind": "state_bundle",
        "batch_id": str(bundle.batch_id),
        "sample_id": str(bundle.sample_id),
        "reference_frame": str(bundle.reference_frame),
        "normalization": str(bundle.normalization),
        "source_round": int(bundle.source_round),
        "detach_proof": bool(bundle.detach_proof),
        "native_state_digest": str(bundle.native_state_digest),
        "channels": sorted(str(k) for k in bundle.channels.keys()),
        "provenance": [str(p) for p in bundle.provenance],
    }
    return summary


def _summarise_trace(trace: Any) -> dict[str, Any]:
    return {
        "kind": "integrator_trace",
        "steps": int(trace.steps),
        "accept_rate": float(trace.accept_rate),
        "native_state_digest": str(trace.native_state_digest),
        "integrator_config_hash": str(trace.integrator_config_hash),
    }


def _summarise_trajectory(traj: Any | None) -> dict[str, Any]:
    """Hash-pinned summary of an exported trajectory.

    The summary preserves shape, dtype, and a checksum of the
    underlying bytes so that two adapters producing the same numerical
    trajectory yield identical hashes. ``None`` trajectories are
    recorded as ``None`` for diagnostic visibility.

    Some adapters (FlowMol3V2) return a Mapping ``{traj_x, traj_c,
    traj_e, traj_a}`` instead of a single ndarray. We accept both:
    a Mapping is summarised per-key, then folded into a stable hash
    over the keyed-bytes concatenation.
    """
    if traj is None:
        return {"present": False, "kind": "none"}
    # Mapping (dict-like) trajectory: per-key hash.
    if isinstance(traj, Mapping):
        import numpy as _np  # local import
        per_key: dict[str, dict[str, Any]] = {}
        # Sort keys for deterministic hashing across Python versions.
        for key in sorted(traj.keys()):
            arr = _np.asarray(traj[key])
            per_key[str(key)] = {
                "shape": list(arr.shape),
                "dtype": str(arr.dtype),
                "sha256": _sha256_hex(arr.tobytes()),
                "finite": bool(_np.all(_np.isfinite(arr))),
            }
        # Stable folded hash over the keyed-bytes concatenation.
        digest_input = json.dumps(
            per_key, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return {
            "present": True,
            "kind": "mapping",
            "keys": list(per_key.keys()),
            "per_key": per_key,
            "sha256": _sha256_hex(digest_input),
        }
    # Single-array trajectory (most adapters).
    import numpy as _np  # local import
    arr = _np.asarray(traj)
    return {
        "present": True,
        "kind": "ndarray",
        "shape": list(arr.shape),
        "dtype": str(arr.dtype),
        "sha256": _sha256_hex(arr.tobytes()),
        "finite": bool(_np.all(_np.isfinite(arr))),
    }


def _run_one_condition(
    *,
    adapter: Any,
    spec: AdapterSpec,
    seed: int,
    nfe: int,
) -> dict[str, Any]:
    """Run a single ``(adapter, seed, nfe)`` and return the hash record."""
    from adaptive_reflow.universal.state import ODEConditionDelta

    batch_id, sample_id = _input_ids_for_seed(seed)
    initial = adapter.build_initial_state(batch_id=batch_id, sample_id=sample_id)

    # Build the per-adapter ODEConditionDelta. Most adapters need a
    # *condition delta* injected before solve_ode with ``num_steps``
    # so the trajectory length varies by NFE.
    spec_extra: dict[str, object] = {}
    if spec.name == "flowmol3_v2":
        spec_extra = {"num_steps": int(nfe)}
    elif spec.name in {"lineageflow", "kanzi", "freqflow"}:
        spec_extra = {
            "num_steps": int(nfe),
            "sampler_id": "euler",
        }
    elif spec.name in {"twodim_fm", "mnist_fm", "self_flow",
                       "rectified_flow_cifar", "graphbfn"}:
        spec_extra = {"num_steps": int(nfe)}
    elif spec.name == "lumina_image_2_0":
        # Lumina's ``compose_condition`` requires a non-empty
        # ``prompt`` (Gemma2 text-encoding path); we supply a
        # deterministic placeholder so the synthetic velocity field
        # runs against a fixed text-embedding cache key.
        spec_extra = {
            "num_steps": int(nfe),
            "prompt": "d4-lumina-audit-placeholder",
            "negative_prompt": "",
        }
    elif spec.name == "toy_gaussian":
        # toy_gaussian reads ``target_mean`` from the delta_spec; the
        # NFE enters via ``self._num_steps`` set in the constructor.
        spec_extra = {"target_mean": 1.0, "num_steps": int(nfe)}
    elif spec.name == "toy_linear":
        # toy_linear's ``solve_ode`` ignores ``num_steps`` (it uses the
        # ``steps`` kwarg, hard-coded to 1 by the runner). The NFE
        # field is still recorded in the condition spec for symmetry
        # with the other 17 adapters, but it does not alter the hash.
        spec_extra = {"num_steps": int(nfe)}

    delta = ODEConditionDelta(
        delta_spec=spec_extra,  # type: ignore[arg-type]
        source=f"d4-audit-{spec.name}",
        target_round=1,
        calibration_artifact_hash="d4-audit",
    )

    # Some adapters require compose_condition first to attach the
    # per-channel cfg/family_id/class_label. We only call it when
    # the adapter declares has_condition_injection.
    caps = adapter.capabilities()
    if bool(getattr(caps, "has_condition_injection", False)):
        delta = adapter.compose_condition(initial, delta)

    trace = adapter.solve_ode(initial, delta, seed=int(seed))
    endpoint = adapter.observe_endpoint(trace, initial)
    traj: Any | None
    try:
        traj = adapter.export_trajectory(trace)
    except NotImplementedError:
        # Some adapters (e.g. ToyLinearAdapter, StochasticFMAdapter)
        # do not preserve a native trajectory. We record ``None`` for
        # ``trajectory`` rather than failing the vector capture, so
        # the regression vector still pins the trace + endpoint surface.
        traj = None

    record: dict[str, Any] = {
        "adapter": spec.name,
        "adapter_version": str(getattr(adapter, spec.version_constant, "")),
        "seed": int(seed),
        "nfe": int(nfe),
        "input_id": {"batch_id": batch_id, "sample_id": sample_id},
        "integrator": str(spec_extra.get("sampler_id", "default")),
        "trace": _summarise_trace(trace),
        "endpoint": _summarise_state_bundle(endpoint),
        "trajectory": _summarise_trajectory(traj),
    }
    record["output_sha256"] = _sha256_hex(_canonical_dumps(record))
    return record


# ---------------------------------------------------------------------------
# Adapter factories (one per spec) — kept tiny so generate + verify stay symmetric
# ---------------------------------------------------------------------------

def _make_twodim_fm(spec: AdapterSpec) -> Any:
    """CPU-only 2D adapter. Uses random-init weights to avoid loading .npz."""
    from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter
    return TwoDimFMAdapter(
        target="two_moons",
        init_random_weights=True,
        init_seed=12345,
        num_steps=10,
        seed_offset=0,
    )


def _make_flowmol3_v2(spec: AdapterSpec) -> Any:
    """NumPy backend; ``backend="numpy"`` keeps the test offline-friendly."""
    from adaptive_reflow.adapters.flowmol3_v2_adapter import FlowMol3V2Adapter
    return FlowMol3V2Adapter(backend="numpy", num_steps=10)


def _make_lineageflow(spec: AdapterSpec) -> Any:
    from adaptive_reflow.adapters.lineageflow import LineageFlowAdapter
    return LineageFlowAdapter(force_mode="synthetic", num_steps=10)


def _make_kanzi(spec: AdapterSpec) -> Any:
    from adaptive_reflow.adapters.kanzi import KanziAdapter
    return KanziAdapter(force_mode="synthetic", num_steps=10)


def _make_freqflow(spec: AdapterSpec) -> Any:
    from adaptive_reflow.adapters.freqflow import FreqFlowAdapter
    return FreqFlowAdapter(force_mode="synthetic", num_steps=10)


def _make_mnist_fm(spec: AdapterSpec) -> Any:
    """MNIST FM adapter; CPU, random-init weights to avoid .npz."""
    from adaptive_reflow.adapters.mnist_fm import MnistFmAdapter
    return MnistFmAdapter(
        integrator="rk4",
        num_steps=10,
        init_random_weights=True,
        init_seed=12345,
        seed_offset=0,
    )


def _make_self_flow(spec: AdapterSpec) -> Any:
    """Self-Flow adapter; synthetic mode (no torch ckpt)."""
    from adaptive_reflow.adapters.self_flow import SelfFlowAdapter
    return SelfFlowAdapter(
        force_mode="synthetic",
        num_steps=10,
        class_label=0,
        synthetic_hidden=64,
        synthetic_seed=0x5E1FF10,
    )


def _make_rectified_flow_cifar(spec: AdapterSpec) -> Any:
    """RectifiedFlowCIFAR adapter; synthetic mode (no torch ckpt)."""
    from adaptive_reflow.adapters.rectified_flow_cifar import (
        RectifiedFlowCIFARAdapter,
    )
    return RectifiedFlowCIFARAdapter(
        force_mode="synthetic",
        num_steps=2,
        synthetic_hidden=8,
        synthetic_seed=0x5F3759DF,
        solver="euler",
    )


def _make_toy_gaussian(spec: AdapterSpec) -> Any:
    """ToyGaussianAdapter; CPU-only scalar 1D Gaussian flow."""
    from adaptive_reflow.adapters.toy_gaussian import ToyGaussianAdapter
    return ToyGaussianAdapter(dt=0.25, num_steps=4)


def _make_toy_linear(spec: AdapterSpec) -> Any:
    """ToyLinearAdapter; minimal Protocol-bound placeholder."""
    from adaptive_reflow.adapters.toy_linear import ToyLinearAdapter
    return ToyLinearAdapter(drift=0.1)


def _make_graphbfn(spec: AdapterSpec) -> Any:
    """GraphBFNAdapter; synthetic mode (no torch ckpt)."""
    from adaptive_reflow.adapters.graphbfn import GraphBFNAdapter
    return GraphBFNAdapter(
        variant="iclr2025",
        dataset="qm9",
        num_steps=4,
        max_nodes=8,
        force_mode="synthetic",
    )


def _make_lumina_image_2_0(spec: AdapterSpec) -> Any:
    """Lumina-Image-2.0 adapter; synthetic mode (no torch ckpt)."""
    from adaptive_reflow.adapters.lumina_image_2_0 import LuminaImage20Adapter
    return LuminaImage20Adapter(
        force_mode="synthetic",
        num_steps=10,
        guidance_scale=1.5,
        cfg_trunc_ratio=0.25,
        cfg_normalization=True,
        synthetic_hidden=16,
        synthetic_seed=0xA5A5A5A5,
        solver="euler",
    )


def _factory_for(spec: AdapterSpec):
    factories = {
        "flowmol3_v2": _make_flowmol3_v2,
        "twodim_fm": _make_twodim_fm,
        "lineageflow": _make_lineageflow,
        "kanzi": _make_kanzi,
        "freqflow": _make_freqflow,
        "mnist_fm": _make_mnist_fm,
        "self_flow": _make_self_flow,
        "rectified_flow_cifar": _make_rectified_flow_cifar,
        "toy_gaussian": _make_toy_gaussian,
        "toy_linear": _make_toy_linear,
        "graphbfn": _make_graphbfn,
        "lumina_image_2_0": _make_lumina_image_2_0,
    }
    return factories[spec.name]


# ---------------------------------------------------------------------------
# Public generate / verify entry points
# ---------------------------------------------------------------------------

@dataclass
class VectorFile:
    """Schema for ``regression-vectors/<adapter>.json``."""

    schema_version: str
    captured_at: str
    git_sha: str
    host_fingerprint: str
    env_composite_hash: str
    adapter: str
    adapter_version: str
    seeds: list[int]
    nfes: list[int]
    conditions: list[dict[str, Any]] = field(default_factory=list)
    per_adapter_hash_count: int = 0

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "captured_at": self.captured_at,
            "git_sha": self.git_sha,
            "host_fingerprint": self.host_fingerprint,
            "env_composite_hash": self.env_composite_hash,
            "adapter": self.adapter,
            "adapter_version": self.adapter_version,
            "seeds": list(self.seeds),
            "nfes": list(self.nfes),
            "per_adapter_hash_count": self.per_adapter_hash_count,
            "conditions": list(self.conditions),
        }


SCHEMA_VERSION = "d4.v1"


def _build_vector_file(spec: AdapterSpec) -> VectorFile:
    """Generate the 9 conditions for one adapter."""
    factory = _factory_for(spec)
    adapter = factory(spec)
    # The version constant lives at module level, not on the instance.
    adapter_version = ""
    try:
        import importlib
        mod = importlib.import_module(spec.module)
        adapter_version = str(getattr(mod, spec.version_constant, ""))
    except Exception:  # noqa: BLE001
        adapter_version = ""
    captured_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conditions: list[dict[str, Any]] = []
    for seed in SEEDS:
        for nfe in NFES:
            rec = _run_one_condition(
                adapter=adapter,
                spec=spec,
                seed=int(seed),
                nfe=int(nfe),
            )
            conditions.append(rec)
    return VectorFile(
        schema_version=SCHEMA_VERSION,
        captured_at=captured_at,
        git_sha=_git_short_sha(),
        host_fingerprint=_read_env_composite_hash(),
        env_composite_hash=_read_env_composite_hash(),
        adapter=spec.name,
        adapter_version=adapter_version,
        seeds=list(SEEDS),
        nfes=list(NFES),
        conditions=conditions,
        per_adapter_hash_count=len(conditions),
    )


def _output_path(spec: AdapterSpec) -> Path:
    return _REPO_ROOT / "regression-vectors" / f"{spec.name}.json"


def generate_all(adapters: Iterable[str] | None = None) -> dict[str, Any]:
    """Write ``regression-vectors/<adapter>.json`` for each spec.

    Returns a per-adapter status dict suitable for JSON serialisation.
    """
    selected = _select_specs(adapters)
    results: dict[str, Any] = {}
    for spec in selected:
        started = time.monotonic()
        try:
            vector = _build_vector_file(spec)
        except Exception as exc:  # noqa: BLE001 — diagnostic surface
            results[spec.name] = {
                "status": "ERROR",
                "error": f"{type(exc).__name__}: {exc}",
                "wallclock_s": round(time.monotonic() - started, 3),
            }
            continue
        out_path = _output_path(spec)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(vector.to_json_dict(), indent=2, sort_keys=False)
            + "\n",
            encoding="utf-8",
        )
        results[spec.name] = {
            "status": "GENERATED",
            "output": str(out_path),
            "per_adapter_hash_count": vector.per_adapter_hash_count,
            "wallclock_s": round(time.monotonic() - started, 3),
        }
    return results


def verify_all(adapters: Iterable[str] | None = None) -> dict[str, Any]:
    """Re-run every recorded vector and assert hash match per condition."""
    selected = _select_specs(adapters)
    host_fp = _read_env_composite_hash()
    results: dict[str, Any] = {"host_fingerprint": host_fp, "adapters": {}}
    overall_ok = True
    for spec in selected:
        started = time.monotonic()
        out_path = _output_path(spec)
        if not out_path.exists():
            results["adapters"][spec.name] = {
                "status": "MISSING_VECTOR",
                "output": str(out_path),
            }
            overall_ok = False
            continue
        try:
            stored = json.loads(out_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            results["adapters"][spec.name] = {
                "status": "CORRUPT_VECTOR",
                "error": f"JSONDecodeError: {exc}",
            }
            overall_ok = False
            continue

        # Host-fingerprint guard: recorded on host A may legitimately
        # differ from current host B (RNG bytes may shift). We *report*
        # the mismatch but still attempt the verification so a reviewer
        # can see whether the adapter itself drifted (versus the host).
        stored_fp = str(stored.get("host_fingerprint", ""))
        host_match = (stored_fp == host_fp) if host_fp else True

        factory = _factory_for(spec)
        try:
            adapter = factory(spec)
        except Exception as exc:  # noqa: BLE001
            results["adapters"][spec.name] = {
                "status": "ERROR",
                "error": f"factory: {type(exc).__name__}: {exc}",
                "host_fingerprint_match": host_match,
            }
            overall_ok = False
            continue

        per_cond: list[dict[str, Any]] = []
        ok = True
        for cond in stored.get("conditions", []):
            try:
                fresh = _run_one_condition(
                    adapter=adapter,
                    spec=spec,
                    seed=int(cond["seed"]),
                    nfe=int(cond["nfe"]),
                )
            except Exception as exc:  # noqa: BLE001
                ok = False
                per_cond.append({
                    "seed": int(cond["seed"]),
                    "nfe": int(cond["nfe"]),
                    "match": False,
                    "error": f"{type(exc).__name__}: {exc}",
                })
                continue
            fresh_hash = fresh["output_sha256"]
            recorded_hash = str(cond.get("output_sha256", ""))
            cond_ok = (fresh_hash == recorded_hash)
            per_cond.append({
                "seed": int(cond["seed"]),
                "nfe": int(cond["nfe"]),
                "recorded": recorded_hash,
                "observed": fresh_hash,
                "match": cond_ok,
            })
            if not cond_ok:
                ok = False

        results["adapters"][spec.name] = {
            "status": "PASS" if ok else "FAIL",
            "per_condition": per_cond,
            "per_adapter_hash_count": len(per_cond),
            "host_fingerprint_recorded": stored_fp,
            "host_fingerprint_current": host_fp,
            "host_fingerprint_match": host_match,
            "wallclock_s": round(time.monotonic() - started, 3),
        }
        if not ok:
            overall_ok = False

    results["overall_ok"] = overall_ok
    return results


def _select_specs(adapters: Iterable[str] | None) -> list[AdapterSpec]:
    if not adapters:
        return list(ADAPTER_SPECS)
    selected: list[AdapterSpec] = []
    for name in adapters:
        match = next((s for s in ADAPTER_SPECS if s.name == name), None)
        if match is None:
            raise SystemExit(f"unknown_adapter:{name}")
        selected.append(match)
    return selected


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_regression_vector_audit",
        description=(
            "D.4 regression-vector audit tool. "
            "Generate pinned (seed, input, NFE) vectors for the 5 "
            "first-batch adapters, or verify the recorded hashes."
        ),
    )
    parser.add_argument(
        "mode",
        choices=("generate", "verify"),
        help="generate: write regression-vectors/<adapter>.json. "
             "verify: re-run every recorded vector and assert hash match.",
    )
    parser.add_argument(
        "--adapter",
        action="append",
        dest="adapters",
        choices=[s.name for s in ADAPTER_SPECS],
        help="restrict to one or more adapters (default: all 5).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    if args.mode == "generate":
        results = generate_all(args.adapters)
        print(json.dumps(results, indent=2, sort_keys=True))
        # Exit 0 iff every adapter reports GENERATED.
        ok = all(v.get("status") == "GENERATED" for v in results.values())
        return 0 if ok else 1
    results = verify_all(args.adapters)
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0 if bool(results.get("overall_ok", False)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
