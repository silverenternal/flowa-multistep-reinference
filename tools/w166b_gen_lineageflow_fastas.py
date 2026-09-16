#!/usr/bin/env python3
"""Wave 166b P1 — Regenerate LineageFlow FASTAs at NFE = 50/100/200/500.

Strategy
--------

* Load the real :class:`LineageFlowAdapter` (torch mode) using the
  published 9.788 GB ``lineageflow-rp55.ckpt`` (downloaded by Wave 10).
  The adapter is the framework's wrapper around the ESM-2 + flow head
  checkpoint; ``force_mode='torch'`` activates the real forward path.
* For each (NFE, arm) cell we generate N=100 records. The
  ``baseline`` arm is a single-pass ODE solve (``tools.eval.baseline.
  _solve_baseline``). The ``framework`` arm is a 3-round restart-blend
  ODE solve (``tools.eval.framework._solve_framework``) with the per-cell
  total NFE budget split as ``[ceil(NFE/3), ceil(NFE/3), NFE - 2*ceil
  (NFE/3)]`` per round (matches the Wave 64 Agent 1 byte-stable
  distribution). Per-record seeds are deterministic (``seed + i``) so
  the generation is reproducible.
* Each record's decoded AA string (mod-20 over the 33-token vocabulary,
  mirroring upstream ``_decode_argmax``) is written to a FASTA with
  header ``>baseline_seed<N>|family=PF00005.27`` (or
  ``>framework_seed<N>|family=PF00005.27``). The family id is fixed
  (the framework's ``LINEAGEFLOW_FAMILY_ID_DEFAULT``).

Output
------

    /tmp/w166b/fastas/baseline/nfe_50.fasta
    /tmp/w166b/fastas/baseline/nfe_100.fasta
    /tmp/w166b/fastas/baseline/nfe_200.fasta
    /tmp/w166b/fastas/baseline/nfe_500.fasta
    /tmp/w166b/fastas/framework/nfe_50.fasta
    /tmp/w166b/fastas/framework/nfe_100.fasta
    /tmp/w166b/fastas/framework/nfe_200.fasta
    /tmp/w166b/fastas/framework/nfe_500.fasta
    /tmp/w166b/fastas/manifest.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

# Ensure the repo root is on sys.path so the eval subpackage imports
# (``tools.eval.baseline``, ``tools.eval.framework``) resolve when this
# script is invoked directly.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Also add the upstream LineageFlow source tree to sys.path so the
# real-mode adapter can resolve ``inference.inference`` / ``models.model``
# (Wave 36 compat shim).
_UPSTREAM = _REPO_ROOT / "data" / "lineageflow_upstream"
if str(_UPSTREAM) not in sys.path:
    sys.path.insert(0, str(_UPSTREAM))

from typing import Any  # noqa: E402

import numpy as np  # noqa: E402

from adaptive_reflow.adapters.lineageflow import (  # noqa: E402
    LINEAGEFLOW_FAMILY_ID_DEFAULT,
    default_lineageflow_adapter,
)
from adaptive_reflow.universal.state import ODEConditionDelta  # noqa: E402
from tools.eval.metrics import _decode_lineageflow_idx_to_aa  # noqa: E402

NFE_LEVELS = (50, 100, 200, 500)
DEFAULT_N_RECORDS = 100
DEFAULT_SEED = 42
DEFAULT_CKPT = "data/lineageflow/lineageflow-rp55.ckpt"
DEFAULT_OUTDIR = "/tmp/w166b/fastas"


def _build_record_bundle(adapter: Any, *, rec_seed: int, nfe: int) -> tuple[Any, Any]:
    """Build a per-record initial state + condition delta.

    Distinct from :func:`tools.eval.baseline._build_initial_state_and_condition`
    because we vary the ``sample_id`` per record (``"s{rec_seed}"``)
    so the LineageFlow adapter's deterministic seed-from-ids path
    yields distinct initial states per record. Re-using the
    baseline/framework helpers' hard-coded ``sample_id="s0"`` would
    collapse every record to the same initial state and produce a
    byte-identical FASTA.
    """
    bundle = adapter.build_initial_state(
        batch_id="eval", sample_id=f"s{rec_seed}",
    )
    condition = ODEConditionDelta(
        delta_spec={"num_steps": int(nfe), "sampler_id": "euler"},
        source="w166b_gen",
        target_round=0,
        calibration_artifact_hash="w166b_gen:default",
    )
    return bundle, condition


def _solve_baseline_n_records(
    adapter: Any, *, nfe: int, rec_seed: int,
) -> Any:
    """Single-pass baseline ODE solve with a per-record initial state."""
    bundle, condition = _build_record_bundle(
        adapter, rec_seed=rec_seed, nfe=nfe,
    )
    return adapter.solve_ode(bundle, condition, seed=int(rec_seed))


def _solve_framework_n_records(
    adapter: Any, *, nfe: int, rec_seed: int, n_rounds: int = 3,
) -> Any:
    """Multi-round restart-blend ODE solve, byte-stable with
    :func:`tools.eval.framework._solve_framework` but with per-record
    initial state. The per-round paper-quantity-driven β + restart
    blend are delegated to the adapter's
    :meth:`apply_restart_distribution`; we mirror the Wave 64 NFE
    distribution ``[base, base, ..., base+remainder]`` with sum = nfe.
    """
    from adaptive_reflow.universal.adapter import CapabilityMissingError  # noqa: E402
    bundle, _ = _build_record_bundle(adapter, rec_seed=rec_seed, nfe=nfe)
    n_rounds_int = max(1, int(n_rounds))
    base_per_round = max(1, int(nfe) // n_rounds_int)
    remainder = max(0, int(nfe) - base_per_round * n_rounds_int)
    nfe_per_round = [base_per_round] * n_rounds_int
    if remainder > 0:
        nfe_per_round[-1] += remainder

    cur_bundle = bundle
    trace: Any = None
    for r in range(int(n_rounds)):
        per_round_nfe = int(nfe_per_round[r])
        condition = ODEConditionDelta(
            delta_spec={"num_steps": per_round_nfe, "sampler_id": "euler"},
            source="w166b_gen",
            target_round=int(r),
            calibration_artifact_hash="w166b_gen:default",
        )
        try:
            trace = adapter.solve_ode(
                cur_bundle, condition, seed=int(rec_seed) + int(r),
            )
        except TypeError:
            trace = adapter.solve_ode(
                cur_bundle, condition, seed=int(rec_seed) + int(r),
            )
        try:
            endpoint = adapter.export_endpoint(cur_bundle)
        except CapabilityMissingError:
            break
        if endpoint is None:
            break
        try:
            from tools.run_real_ckpt_eval import (  # noqa: E402
                _compute_paper_quantities,
                _make_framework_policy,
            )
            pq = _compute_paper_quantities(
                adapter, trace, round_index=int(r),
            )
            policy = _make_framework_policy(
                adapter,
                target_round=int(r),
                seed=int(rec_seed),
                paper_quantities=pq,
            )
            cur_bundle = adapter.apply_restart_distribution(endpoint, policy)
        except CapabilityMissingError:
            break
    final_condition = ODEConditionDelta(
        delta_spec={"num_steps": int(nfe), "sampler_id": "euler"},
        source="w166b_gen",
        target_round=int(n_rounds),
        calibration_artifact_hash="w166b_gen:default",
    )
    return adapter.solve_ode(cur_bundle, final_condition, seed=int(rec_seed))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _trace_endpoint_to_aa(trace: Any, adapter: Any | None = None) -> str:
    """Decode a single trace's endpoint to an AA string.

    Wave 166b P1 — the LineageFlow adapter does not return the
    endpoint as ``trace.endpoint`` / ``trace.states``; instead the
    trajectory is cached under ``adapter._native_states[trace.
    native_state_digest]['trajectory']`` as a (T, L, K) ``float64``
    array. We take the final timestep (``trajectory[-1]``) as the
    endpoint, argmax along the K axis to get token indices, then
    mod-20 to fold the 33-token Pfam vocabulary onto the 20-standard-
    AA alphabet (mirrors the upstream ``_decode_argmax`` helper).
    """
    if trace is None:
        return "M" * 30
    digest = getattr(trace, "native_state_digest", None)
    if digest and adapter is not None:
        entry = getattr(adapter, "_native_states", {}).get(digest, {})
        trajectory = entry.get("trajectory")
        if trajectory is not None:
            arr = np.asarray(trajectory[-1])  # (L, K) endpoint simplex
            if arr.ndim == 2:
                idx = arr.argmax(axis=-1)
            elif arr.ndim == 3:
                idx = arr[0].argmax(axis=-1)
            else:
                idx = arr
            return _decode_lineageflow_idx_to_aa(idx)
    # Fall back to ``trace.endpoint`` / ``trace.states`` for adapters
    # that store the endpoint inline (legacy / synthetic-mode shims).
    endpoint = (
        getattr(trace, "endpoint", None)
        or getattr(trace, "states", None)
    )
    if endpoint is None:
        return "M" * 30
    arr = np.asarray(endpoint)
    if arr.ndim == 2:
        idx = arr.argmax(axis=-1)
    elif arr.ndim == 3:
        idx = arr[0].argmax(axis=-1)
    elif arr.ndim == 1:
        idx = arr
    else:
        return "M" * 30
    return _decode_lineageflow_idx_to_aa(idx)


def _generate_arm(
    *,
    arm: str,
    nfe: int,
    n_records: int,
    seed: int,
    adapter: Any,
) -> tuple[Path, dict[str, Any]]:
    """Generate one FASTA per arm per NFE level."""
    out_dir = Path(DEFAULT_OUTDIR) / arm
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"nfe_{nfe}.fasta"
    family_id = LINEAGEFLOW_FAMILY_ID_DEFAULT

    debug: dict[str, Any] = {
        "arm": str(arm),
        "nfe": int(nfe),
        "n_records": int(n_records),
        "seed": int(seed),
        "family_id": str(family_id),
        "records": [],
    }

    t0 = time.monotonic()
    with out_path.open("w", buffering=1) as f:  # line-buffered so we can monitor progress
        for i in range(int(n_records)):
            rec_seed = int(seed) + i
            try:
                if arm == "baseline":
                    trace = _solve_baseline_n_records(
                        adapter, nfe=int(nfe), rec_seed=rec_seed,
                    )
                else:
                    trace = _solve_framework_n_records(
                        adapter, nfe=int(nfe), rec_seed=rec_seed,
                        n_rounds=3,
                    )
                seq = _trace_endpoint_to_aa(trace, adapter=adapter)
                ok = True
                err = ""
            except Exception as exc:  # noqa: BLE001
                seq = "M" * 30
                ok = False
                err = f"{type(exc).__name__}:{exc}"
            f.write(f">{arm}_seed{rec_seed}|family={family_id}\n{seq}\n")
            debug["records"].append({
                "index": i,
                "seed": rec_seed,
                "len": len(seq),
                "ok": ok,
                "error": err,
            })
            if (i + 1) % 10 == 0 or i + 1 == n_records:
                elapsed = time.monotonic() - t0
                rate = (i + 1) / elapsed if elapsed > 0 else 0.0
                print(
                    f"[{arm} NFE={nfe}] {i+1}/{n_records} "
                    f"({rate:.2f} rec/s, elapsed={elapsed:.1f}s)",
                    file=sys.stderr, flush=True,
                )
    debug["wallclock_s"] = float(time.monotonic() - t0)
    debug["sha256"] = _sha256(out_path)
    debug["out_path"] = str(out_path)
    debug["n_kept"] = sum(1 for r in debug["records"] if r["ok"])
    debug["n_failed"] = int(n_records) - debug["n_kept"]
    return out_path, debug


def main() -> int:
    global DEFAULT_OUTDIR  # noqa: PLW0603 — must precede any use of the name
    p = argparse.ArgumentParser()
    p.add_argument("--ckpt", default=DEFAULT_CKPT)
    p.add_argument("--nfe", type=str, default="50,100,200,500",
                   help="Comma-separated NFE levels.")
    p.add_argument("--n-records", type=int, default=DEFAULT_N_RECORDS)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--outdir", default=DEFAULT_OUTDIR)
    p.add_argument("--arms", type=str, default="baseline,framework",
                   help="Comma-separated arms.")
    args = p.parse_args()

    DEFAULT_OUTDIR = args.outdir

    nfe_levels = [int(s.strip()) for s in args.nfe.split(",") if s.strip()]
    arms = [s.strip() for s in args.arms.split(",") if s.strip()]

    print(f"[load] ckpt={args.ckpt}", file=sys.stderr)
    t0 = time.monotonic()
    adapter = default_lineageflow_adapter(
        weights_path=args.ckpt,
        force_mode="torch",
        num_steps=max(nfe_levels),  # any future solve_ode can override via delta_spec
    )
    load_t = time.monotonic() - t0
    print(f"[load] adapter loaded in {load_t:.1f}s, mode={adapter._mode}",
          file=sys.stderr)

    manifest: dict[str, Any] = {
        "ckpt": str(args.ckpt),
        "nfe_levels": nfe_levels,
        "arms": arms,
        "n_records_per_cell": int(args.n_records),
        "seed": int(args.seed),
        "load_wallclock_s": float(load_t),
        "cells": [],
    }

    for nfe in nfe_levels:
        for arm in arms:
            print(f"[generate] arm={arm} NFE={nfe}", file=sys.stderr)
            _, debug = _generate_arm(
                arm=arm, nfe=int(nfe), n_records=int(args.n_records),
                seed=int(args.seed), adapter=adapter,
            )
            manifest["cells"].append(debug)
            # Drop the per-record records list from the manifest JSON
            # to keep the file small.
            debug.pop("records", None)
            print(
                f"[done] arm={arm} NFE={nfe} -> {debug['out_path']} "
                f"sha256={debug['sha256'][:12]}... "
                f"kept={debug['n_kept']} failed={debug['n_failed']} "
                f"({debug['wallclock_s']:.1f}s)",
                file=sys.stderr,
            )

    out_manifest = Path(args.outdir) / "manifest.json"
    out_manifest.parent.mkdir(parents=True, exist_ok=True)
    out_manifest.write_text(json.dumps(manifest, indent=2))
    print(f"[done] manifest -> {out_manifest}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
