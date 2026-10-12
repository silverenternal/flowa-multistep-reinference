#!/usr/bin/env python3
"""R1 D-004B-ATTRIBUTION — init-only control arm for the LineageFlow HMMER cell.

Motivation
----------

The R1 cell compares a **bare-RNG family-biased draw** (baseline) against the
**framework multi-round restart-blend** arm (framework). With the D-004b fix the
framework wins (275 vs 158 on seed 42). A reviewer can ask: *is the win the
multi-round restart-blend, or would a single model pass from a per-record
random initial state already win?*

This driver builds the missing control:

* **init-only** — a per-record random-simplex initial state (``softmax(randn)``,
  the same noise convention the D-004b restart uses) fed through a **single**
  ``solve_ode`` pass (no restart, no blend), at the same per-record NFE, seed,
  N and length distribution as the framework arm.

Comparison (seed 42, N=1000, real-forward):

    A baseline (bare RNG, from gen_lineageflow_n1000_fastas.py)  -> 158 hits
    B init-only (this driver)                                    -> ?
    C framework (D-004b, from the same gen script)               -> 275 hits

* If ``B ~ C`` the win is the per-record random state (a single pass suffices);
  the multi-round restart-blend adds little.
* If ``B ~ A`` the single pass from a random init does not help; the
  restart-blend is the load-bearing mechanism.
* If ``A < B < C`` both the model pass and the blend contribute.

The init-only arm is a **diagnostic**: it monkey-patches the adapter's
initial-state sampler in-process only (no shipped code path changes), and
writes ``init_only.fasta``. It does NOT touch the framework arm or the
baseline arm.

Length / family matching
------------------------

The framework arm draws per-record lengths from ``random.Random(seed ^ 0x5A5A)``
(``gen_lineageflow_n1000_fastas.main``). This driver replays the **same** RNG
stream so the init-only lengths and family assignments are identical to the
framework arm's — the only variable is the arm itself.

Usage
-----

    python tools/r1_d004b_attribution.py --outdir /tmp/r1_d004b/init_only \\
        --n 1000 --seed 42 --nfe 10
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

AA_SET = "ACDEFGHIKLMNPQRSTVWY"


def _build_adapter(family_id: str, seed: int, nfe: int) -> Any:
    from adaptive_reflow.adapters.lineageflow import LineageFlowAdapter

    return LineageFlowAdapter(
        family_id=family_id,
        num_steps=int(nfe),
        solver="euler",
        force_mode="auto",
        seed_offset=int(seed),
    )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--outdir", type=Path, required=True)
    p.add_argument("--n", type=int, default=1000)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--nfe", type=int, default=10)
    p.add_argument("--min-len", type=int, default=30)
    p.add_argument("--max-len", type=int, default=150)
    p.add_argument(
        "--init-source",
        type=str,
        choices=("random-simplex", "latent-like"),
        default="random-simplex",
        help=(
            "Initial-state sampler for the single pass. ``random-simplex`` "
            "(default) = per-record softmax(randn) (the D-004b noise "
            "convention). ``latent-like`` = the canonical near-uniform "
            "1/K + U(0,1e-6) sampler (reproduces the D-004 collapse)."
        ),
    )
    args = p.parse_args()

    import numpy as np  # noqa: F401  (adapter needs numpy at import)

    import adaptive_reflow.adapters.lineageflow as lf
    from adaptive_reflow.adapters.lineageflow import AMINO_ACID_CATEGORICAL
    from adaptive_reflow.universal.state import ODEConditionDelta
    from tools.gen_lineageflow_n1000_fastas import FAMILY_PROFILES

    # In-process sampler swap (diagnostic only). ``build_initial_state`` calls
    # the module-global ``_synthesize_latent_like_tensor``; rebinding it here
    # makes the initial state a per-record random simplex.
    if args.init_source == "random-simplex":
        lf._synthesize_latent_like_tensor = lf._synthesize_random_simplex

    args.outdir.mkdir(parents=True, exist_ok=True)
    family_ids = list(FAMILY_PROFILES.keys())

    # Replay the framework arm's length RNG stream so lengths/families match.
    framework_rng = random.Random(int(args.seed) ^ 0x5A5A)

    adapters: dict[str, Any] = {
        fam: _build_adapter(fam, int(args.seed), int(args.nfe))
        for fam in family_ids
    }

    fallback: dict[str, int] = {}
    per_family: dict[str, int] = {}
    out_path = args.outdir / "init_only.fasta"
    with out_path.open("w") as f:
        for i in range(int(args.n)):
            family_id = family_ids[i % len(family_ids)]
            length = framework_rng.randint(int(args.min_len), int(args.max_len))
            adapter = adapters[family_id]
            seq: str | None = None
            try:
                # Per-record sample_id -> per-record seed -> per-record random x0.
                bundle = adapter.build_initial_state(
                    batch_id="eval", sample_id=f"s{i}"
                )
                cond = ODEConditionDelta(
                    delta_spec={"num_steps": int(args.nfe), "sampler_id": "euler"},
                    source="r1_d004b_attribution",
                    target_round=0,
                    calibration_artifact_hash="r1_d004b_attribution:default",
                )
                trace = adapter.solve_ode(
                    bundle, cond, seed=int(args.seed) + int(i)
                )
                obs = adapter.observe_token_indices(
                    trace, paper_quantities=None, temperature=1.0, rng=None,
                )
                idx = obs.get(str(AMINO_ACID_CATEGORICAL))
                if idx is None:
                    raise RuntimeError("observe_token_indices returned no AA channel")
                flat = idx.reshape(-1)
                seq = "".join(AA_SET[int(v) % len(AA_SET)] for v in flat[: int(length)])
            except Exception:
                seq = None
            if seq is None:
                fallback[family_id] = fallback.get(family_id, 0) + 1
                seq = "X" * int(length)
            f.write(f">init_only_seed{i}|family={family_id}\n")
            f.write(f"{seq}\n")
            per_family[family_id] = per_family.get(family_id, 0) + 1
            if (i + 1) % 200 == 0:
                print(f"  {i + 1}/{int(args.n)} records", flush=True)

    manifest = {
        "n": int(args.n),
        "seed": int(args.seed),
        "nfe_per_record": int(args.nfe),
        "min_len": int(args.min_len),
        "max_len": int(args.max_len),
        "arm": "init_only",
        "init_source": str(args.init_source),
        "family_ids": family_ids,
        "per_family_count": per_family,
        "fallback_per_family_count": fallback,
        "note": (
            "Single solve_ode pass from a per-record initial state; no restart, "
            "no blend. Lengths/families replayed from the framework arm's RNG "
            "stream (seed ^ 0x5A5A)."
        ),
    }
    (args.outdir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"wrote {out_path} (n={int(args.n)})")
    print(f"wrote {args.outdir / 'manifest.json'}")
    print(f"fallback_per_family_count={fallback}")


if __name__ == "__main__":
    main()
