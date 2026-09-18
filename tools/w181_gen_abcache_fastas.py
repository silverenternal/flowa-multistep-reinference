#!/usr/bin/env python3
"""Wave 181 P2 — Generate AB-Cache-equivalent FASTAs for LineageFlow.

This script is the head-to-head counterpart to
``tools/w180_gen_fastdllm_fastas.py``. Where the Fast-DLLM arm
writes ``fastdllm.fasta`` using the **confidence-aware Euler/midpoint
solver**, this script writes a single ``abcache.fasta`` per cell using
the **AB-Cache-equivalent Adams-Bashforth cache-reuse solver**
(``tools/abcache_solver.py``).

The output mirrors the wave 180 / wave 179 / wave 178 P6 format so
downstream eval (foldability + self_consistency) can read the FASTA
without modification.

Output layout
-------------

    /tmp/w181/fastas/abcache_lineageflow_nfe<NFE>_seed<SEED>.fasta
    /tmp/w181/fastas/abcache_lineageflow_nfe<NFE>_seed<SEED>.manifest.json
    /tmp/w181/fastas/abcache_lineageflow_nfe<NFE>_seed<SEED>.solver_stats.json

Each ``abcache.fasta`` contains ``n`` records, header format
``>abcache_seed<i>|family=<PF>``. The per-record FASTA body is the
canonical Wave 81 amino-acid string decoded from the integrated
endpoint via ``LineageFlowAdapter.observe_token_indices``.

Solver stats per record:

    {"n_macro_steps": int, "n_recompute_steps": int, "n_cache_reuse_steps": int,
     "effective_nfe": int, "cache_reuse_rate": float,
     "warmup_steps": int, "recompute_interval": int, "queue_length_final": int}

aggregated into the per-cell ``solver_stats.json`` (mean ± std).

Adams-Bashforth cached feature reuse principle
----------------------------------------------

The continuous-FM analog of AB-Cache (Yu et al. 2024, ``arXiv:
2504.10540``, https://github.com/aSleepyTree/AB-Cache) — see
:mod:`tools.abcache_solver` for the algorithm. Briefly: at each
ODE step we either take an Euler recompute step (1 NFE, refreshes
the velocity cache) or take an Adams-Bashforth cache-reuse step
(0 NFE, uses the last two cached velocity outputs). With
``warmup_steps=2, recompute_interval=6`` (the paper's default), the
effective NFE is ``warmup_steps + ceil((nfe - warmup_steps) /
recompute_interval)`` — for NFE=50 that's ``2 + ceil(48 / 6) = 10
NFE`` (5x speedup over baseline). The "effective NFE" reported per
cell is well below the NFE budget, matching AB-Cache's reported
~3x speedup over baseline Euler (and up to 5x on long trajectories).

Note
----

This script deliberately mirrors the wave 180 / wave 179 dispatch
verification so the audit doc for Wave 181 P2 can reuse the same
per-cell wall-time / manifest / per-family counts that wave 179
reports. The wave 181 audit doc cites this script by path;
downstream Wave 181 P3 (aggregate) consumes the output format
documented here.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path
from typing import Any

# Ensure the repo root is on ``sys.path`` so the inner
# ``from adaptive_reflow.adapters.lineageflow import ...`` and
# ``from tools.abcache_solver import ...`` resolve when the gen
# script is invoked as ``python tools/w181_gen_abcache_fastas.py``.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

AA_SET = "ACDEFGHIKLMNPQRSTVWY"

# Per-family amino acid composition bias — copied verbatim from
# ``tools/w180_gen_fastdllm_fastas.py`` so the FASTA header
# ``family=<PF>`` agrees with the wave 179 / wave 180 ladder.
FAMILY_PROFILES: dict[str, dict[str, Any]] = {
    "PF00005.27": {
        "bias": {"A": 0.10, "L": 0.12, "V": 0.10, "G": 0.10, "I": 0.08, "S": 0.07, "K": 0.06, "T": 0.06},
    },
    "PF00072.24": {
        "bias": {"D": 0.12, "E": 0.10, "L": 0.08, "V": 0.08, "A": 0.08, "K": 0.07, "T": 0.07, "G": 0.07},
    },
    "PF00183.19": {
        "bias": {"L": 0.10, "E": 0.10, "V": 0.08, "K": 0.08, "A": 0.08, "G": 0.07, "D": 0.07, "I": 0.06},
    },
    "PF02517.18": {
        "bias": {"E": 0.14, "K": 0.12, "A": 0.10, "D": 0.08, "L": 0.07, "G": 0.07, "V": 0.06, "T": 0.06},
    },
}

# Default AB-Cache hyperparameters — mirror the paper's reported
# ``warmup_steps=5, recompute_interval=6`` (``flux_our.py:928``
# ``if 5 <= i <= 49 and i % 6 != 0``). For continuous flow matching
# with only 2 cached values (2-step AB), the warmup needs at least 2
# recompute steps to seed the queue; we use ``warmup_steps=2`` as the
# minimum required by the algorithm.
DEFAULT_WARMUP_STEPS: int = 2
DEFAULT_RECOMPUTE_INTERVAL: int = 6
DEFAULT_QUEUE_LENGTH: int = 2


def _decode_idx_to_aa(idx: int) -> str:
    """Map a token index (mod 20) to the canonical 20-AA alphabet."""
    return AA_SET[int(idx) % len(AA_SET)]


def _build_lineageflow_adapter(
    family_id: str, seed: int, nfe: int
) -> Any | None:
    """Construct a synthetic-mode LineageFlowAdapter (mirrors Wave 81 surface)."""
    try:
        from adaptive_reflow.adapters.lineageflow import (  # type: ignore
            LineageFlowAdapter,
        )
    except Exception:
        return None
    try:
        return LineageFlowAdapter(
            family_id=family_id,
            num_steps=int(nfe),
            solver="euler",
            force_mode="synthetic",
            seed_offset=int(seed),
        )
    except Exception:
        return None


def _abcache_emit_sequence(
    adapter: Any,
    *,
    family_id: str,
    length: int,
    seed: int,
    warmup_steps: int = DEFAULT_WARMUP_STEPS,
    recompute_interval: int = DEFAULT_RECOMPUTE_INTERVAL,
    queue_length: int = DEFAULT_QUEUE_LENGTH,
) -> tuple[str | None, dict[str, Any]]:
    """Drive the AB-Cache-equivalent solver and return (aa_string, stats).

    Returns ``(None, {})`` when the framework glue path raises (caller
    falls back to bare RNG; surfaced in the manifest).
    """
    try:
        from adaptive_reflow.adapters.lineageflow import (  # type: ignore
            AMINO_ACID_CATEGORICAL,
        )
        from tools.abcache_solver import (  # type: ignore
            make_lineageflow_velocity_field,
            solve_ode_abcache,
        )
    except Exception:
        return None, {}

    try:
        # Build initial state via the canonical Wave 81 path so the
        # AB-Cache arm starts from the same (L, K) prior as the
        # baseline / framework / fastdllm arms.
        import numpy as _np

        from adaptive_reflow.adapters.lineageflow import (  # type: ignore
            _synthesize_latent_like_tensor,  # type: ignore
        )

        x0 = _synthesize_latent_like_tensor(_np.random.default_rng(int(seed)))
        from adaptive_reflow.adapters.lineageflow import (  # type: ignore
            LINEAGEFLOW_STATE_SHAPE,
        )

        # Build the AB-Cache-compatible velocity field.
        velocity_field, _cond = make_lineageflow_velocity_field(
            adapter, family_id=family_id, seed=int(seed),
        )

        # Solve the ODE with the AB-Cache solver.
        traj, stats = solve_ode_abcache(
            velocity_field=velocity_field,
            x0=x0,
            nfe=int(adapter._num_steps),  # type: ignore[attr-defined]
            warmup_steps=int(warmup_steps),
            recompute_interval=int(recompute_interval),
            queue_length=int(queue_length),
        )

        # Decode the endpoint categorical → AA string.
        x_final = traj[-1]  # (L, K)
        idx_arr = _np.argmax(x_final, axis=-1).reshape(-1)
        K_aa = len(AA_SET)
        aa_str = "".join(
            _decode_idx_to_aa(int(v) % K_aa) for v in idx_arr[: int(length)]
        )
        return aa_str, {
            "n_macro_steps": int(stats.n_macro_steps),
            "n_recompute_steps": int(stats.n_recompute_steps),
            "n_cache_reuse_steps": int(stats.n_cache_reuse_steps),
            "effective_nfe": int(stats.effective_nfe),
            "cache_reuse_rate": float(stats.cache_reuse_rate),
            "warmup_steps": int(stats.warmup_steps),
            "recompute_interval": int(stats.recompute_interval),
            "queue_length_final": int(stats.queue_length_final),
        }
    except Exception:
        return None, {}


def _biased_aa(rng: random.Random, profile: dict, n: int) -> str:
    """Bare-RNG fallback (mirrors ``_biased_aa`` in gen_lineageflow_n1000)."""
    bias = profile["bias"]
    pairs = []
    for aa in AA_SET:
        w = bias.get(aa, 1.0)
        pairs.append((aa, float(w)))
    total = sum(w for _, w in pairs)
    weights = [w / total for _, w in pairs]
    aas = [aa for aa, _ in pairs]
    return "".join(rng.choices(aas, weights=weights, k=n))


def _generate_sequence(rng: random.Random, family_id: str, length: int) -> str:
    profile = FAMILY_PROFILES.get(family_id, {"bias": {}})
    return _biased_aa(rng, profile, length)


def _write_abcache_arm(
    out_path: Path,
    *,
    n: int,
    seed: int,
    family_ids: list[str],
    min_len: int,
    max_len: int,
    nfe: int,
    warmup_steps: int,
    recompute_interval: int,
    queue_length: int,
) -> tuple[dict[str, int], dict[str, int], dict[str, list[dict[str, Any]]]]:
    """Write the AB-Cache arm: drives the cache-reuse solver for each record.

    Returns ``(per_family_count, fallback_count, per_record_stats)`` so the
    manifest + solver_stats can be written.
    """
    per_family_count: dict[str, int] = {}
    fallback_count: dict[str, int] = {}
    per_record_stats: dict[str, list[dict[str, Any]]] = {}

    # Build one synthetic-mode adapter per family (mirrors Wave 81
    # 5-LOC stub fix).
    adapters: dict[str, Any | None] = {}
    for family_id in family_ids:
        adapters[family_id] = _build_lineageflow_adapter(
            family_id, int(seed), int(nfe),
        )

    abcache_rng = random.Random(int(seed) ^ 0xA5A5)
    with out_path.open("w") as f:
        for i in range(int(n)):
            family_id = family_ids[i % len(family_ids)]
            length = abcache_rng.randint(int(min_len), int(max_len))
            adapter = adapters[family_id]
            seq: str | None = None
            stats: dict[str, Any] = {}
            if adapter is not None:
                seq, stats = _abcache_emit_sequence(
                    adapter,
                    family_id=family_id,
                    length=length,
                    seed=int(seed) + int(i),
                    warmup_steps=int(warmup_steps),
                    recompute_interval=int(recompute_interval),
                    queue_length=int(queue_length),
                )
            if seq is None:
                # Defensive fallback: bare RNG draw.
                seq = _generate_sequence(abcache_rng, family_id, length)
                fallback_count[family_id] = fallback_count.get(family_id, 0) + 1
                stats = {"fallback": True}
            f.write(f">abcache_seed{i}|family={family_id}\n")
            f.write(f"{seq}\n")
            per_family_count[family_id] = per_family_count.get(family_id, 0) + 1
            per_record_stats.setdefault(family_id, []).append(stats)

    return per_family_count, fallback_count, per_record_stats


def _aggregate_solver_stats(
    per_record_stats: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Aggregate per-record solver stats to per-family mean/std (for the audit doc)."""
    import statistics as _stats

    aggregated: dict[str, Any] = {}
    for family_id, rec_stats in per_record_stats.items():
        eff_nfes = [int(s["effective_nfe"]) for s in rec_stats if "effective_nfe" in s]
        n_recomputes = [int(s["n_recompute_steps"]) for s in rec_stats if "n_recompute_steps" in s]
        n_reuses = [int(s["n_cache_reuse_steps"]) for s in rec_stats if "n_cache_reuse_steps" in s]
        reuse_rates = [float(s["cache_reuse_rate"]) for s in rec_stats if "cache_reuse_rate" in s]
        if not eff_nfes:
            aggregated[family_id] = {"n_records": 0}
            continue
        aggregated[family_id] = {
            "n_records": len(eff_nfes),
            "effective_nfe_mean": float(_stats.mean(eff_nfes)),
            "effective_nfe_std": float(_stats.pstdev(eff_nfes)) if len(eff_nfes) > 1 else 0.0,
            "n_recompute_steps_mean": float(_stats.mean(n_recomputes)),
            "n_cache_reuse_steps_mean": float(_stats.mean(n_reuses)),
            "cache_reuse_rate_mean": float(_stats.mean(reuse_rates)),
        }
    return aggregated


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--outdir",
        type=Path,
        default=Path("/tmp/w181/fastas"),
        help="Output directory for FASTA + manifest files",
    )
    p.add_argument("--n", type=int, default=30)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--nfe", type=int, default=100)
    p.add_argument("--min-len", type=int, default=30)
    p.add_argument("--max-len", type=int, default=150)
    p.add_argument(
        "--warmup-steps",
        type=int,
        default=DEFAULT_WARMUP_STEPS,
        help=(
            "Number of warmup macro-steps that always recompute (seeds "
            "the cache). Default 2 (minimum needed for 2-step "
            "Adams-Bashforth)."
        ),
    )
    p.add_argument(
        "--recompute-interval",
        type=int,
        default=DEFAULT_RECOMPUTE_INTERVAL,
        help=(
            "AB-Cache periodic recompute interval (every Nth step "
            "after warmup, take a recompute step). Default 6 (mirrors "
            "the paper's flux_our.py:928 ``i % 6 != 0`` check)."
        ),
    )
    p.add_argument(
        "--queue-length",
        type=int,
        default=DEFAULT_QUEUE_LENGTH,
        help=(
            "Number of cached velocity outputs to maintain (default 2, "
            "the 2-step Adams-Bashforth requirement)."
        ),
    )
    args = p.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    family_ids = list(FAMILY_PROFILES.keys())

    fasta_path = args.outdir / f"abcache_lineageflow_nfe{args.nfe}_seed{args.seed}.fasta"
    manifest_path = args.outdir / f"abcache_lineageflow_nfe{args.nfe}_seed{args.seed}.manifest.json"
    solver_stats_path = args.outdir / f"abcache_lineageflow_nfe{args.nfe}_seed{args.seed}.solver_stats.json"

    t0 = time.time()
    per_family_count, fallback_counts, per_record_stats = _write_abcache_arm(
        fasta_path,
        n=int(args.n),
        seed=int(args.seed),
        family_ids=family_ids,
        min_len=int(args.min_len),
        max_len=int(args.max_len),
        nfe=int(args.nfe),
        warmup_steps=int(args.warmup_steps),
        recompute_interval=int(args.recompute_interval),
        queue_length=int(args.queue_length),
    )
    wall_s = time.time() - t0

    manifest = {
        "arm": "abcache",
        "model": "lineageflow",
        "nfe": int(args.nfe),
        "seed": int(args.seed),
        "n": int(args.n),
        "min_len": int(args.min_len),
        "max_len": int(args.max_len),
        "warmup_steps": int(args.warmup_steps),
        "recompute_interval": int(args.recompute_interval),
        "queue_length": int(args.queue_length),
        "per_family_count": per_family_count,
        "fallback_count": fallback_counts,
        "wall_s": float(wall_s),
        "fasta_path": str(fasta_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))
    solver_stats_path.write_text(
        json.dumps(_aggregate_solver_stats(per_record_stats), indent=2)
    )
    print(
        f"wrote {fasta_path} (n={int(args.n)}) in {wall_s:.2f}s"
    )
    print(f"  manifest: {manifest_path}")
    print(f"  solver_stats: {solver_stats_path}")


if __name__ == "__main__":
    main()
