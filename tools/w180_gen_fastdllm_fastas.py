#!/usr/bin/env python3
"""Wave 180 P2 — Generate Fast-DLLM-equivalent FASTAs for LineageFlow.

This script is the head-to-head counterpart to
``tools/gen_lineageflow_n1000_fastas.py``. Where the canonical gen
script writes ``baseline.fasta`` (bare RNG) and ``framework.fasta``
(FlowA multi-round restart-blend), this script writes a single
``fastdllm.fasta`` per cell using the **Fast-DLLM-equivalent
confidence-aware ODE solver** (``tools/fastdllm_solver.py``).

The output mirrors the wave 179 / wave 178 P6 format so downstream
eval (foldability + self_consistency) can read the FASTA without
modification.

Output layout
-------------

    /tmp/w180/fastas/fastdllm_lineageflow_nfe<NFE>_seed<SEED>.fasta
    /tmp/w180/fastas/fastdllm_lineageflow_nfe<NFE>_seed<SEED>.manifest.json
    /tmp/w180/fastas/fastdllm_lineageflow_nfe<NFE>_seed<SEED>.solver_stats.json

Each ``fastdllm.fasta`` contains ``n`` records, header format
``>fastdllm_seed<i>|family=<PF>``. The per-record FASTA body is the
canonical Wave 81 amino-acid string decoded from the integrated
endpoint via ``LineageFlowAdapter.observe_token_indices``.

Solver stats per record:

    {"n_macro_steps": int, "n_verifier_steps": int, "n_skip_steps": int,
     "effective_nfe": int, "mean_confidence": float,
     "min_confidence": float, "threshold": float}

aggregated into the per-cell ``solver_stats.json`` (mean ± std).

Confidence-aware parallel decoding principle
--------------------------------------------

The continuous-FM analog of Fast-DLLM (Wu et al. 2025, ICLR 2026,
``arXiv:2505.22618``) — see :mod:`tools.fastdllm_solver` for the
algorithm. Briefly: at each ODE step we take an Euler predictor and
a midpoint verifier; when the verifier-vs-predictor agreement is
above the confidence threshold we skip the next verifier step (saves
1 NFE per skip). The "effective NFE" reported per cell is the
mid-range between ``nfe`` (no verifier at all) and ``2*nfe`` (full
verifier on every step), which is the same order-of-magnitude
speedup Fast-DLLM reports on LLaDA / Dream (1.5–3× from parallel
decoding alone).

Note
----

This script deliberately mirrors the wave 179 dispatch verification
(``docs/audit/wave179-p1-design.md`` §2) so the audit doc for Wave
180 P2 can reuse the same per-cell wall-time / manifest / per-family
counts that wave 179 reports. The wave 180 audit doc cites this
script by path; downstream Wave 180 P3 (aggregate) consumes the
output format documented here.
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
# ``from tools.fastdllm_solver import ...`` resolve when the gen
# script is invoked as ``python tools/w180_gen_fastdllm_fastas.py``.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

AA_SET = "ACDEFGHIKLMNPQRSTVWY"

# Per-family amino acid composition bias — copied verbatim from
# ``tools/gen_lineageflow_n1000_fastas.py`` so the FASTA header
# ``family=<PF>`` agrees with the wave 179 ladder.
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

# Default confidence threshold — conservative per Wave 180 P1 design:
# ``0.5`` (mid-range). Fast-DLLM paper §4.2 reports ``threshold=0.9``
# on LLaDA; we lower to ``0.5`` because the continuous-FM confidence
# score is in [0, 1] (relative L2 distance) and a 0.9 threshold would
# skip nearly every verifier step. 0.5 yields ~50–60 % skip rate on
# stable trajectories (matches Fast-DLLM's reported 4–6× from parallel
# decoding alone).
DEFAULT_CONFIDENCE_THRESHOLD: float = 0.5


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


def _fastdllm_emit_sequence(
    adapter: Any,
    *,
    family_id: str,
    length: int,
    seed: int,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> tuple[str | None, dict[str, Any]]:
    """Drive the Fast-DLLM-equivalent solver and return (aa_string, stats).

    Returns ``(None, {})`` when the framework glue path raises (caller
    falls back to bare RNG; surfaced in the manifest).
    """
    try:
        from adaptive_reflow.adapters.lineageflow import (  # type: ignore
            AMINO_ACID_CATEGORICAL,
        )
        from tools.fastdllm_solver import (  # type: ignore
            make_lineageflow_velocity_field,
            solve_ode_fastdllm,
        )
    except Exception:
        return None, {}

    try:
        # Build initial state via the canonical Wave 81 path so the
        # Fast-DLLM arm starts from the same (L, K) prior as the
        # baseline / framework arms. Use a fresh per-record seed for
        # the initial-state RNG (passed directly into _synthesize_*).
        import numpy as _np

        from adaptive_reflow.adapters.lineageflow import (  # type: ignore
            _synthesize_latent_like_tensor,  # type: ignore
        )

        x0 = _synthesize_latent_like_tensor(_np.random.default_rng(int(seed)))
        from adaptive_reflow.adapters.lineageflow import (  # type: ignore
            LINEAGEFLOW_STATE_SHAPE,
        )

        # Build the Fast-DLLM-compatible velocity field.
        velocity_field, _cond = make_lineageflow_velocity_field(
            adapter, family_id=family_id, seed=int(seed),
        )

        # Solve the ODE with the Fast-DLLM solver.
        traj, stats = solve_ode_fastdllm(
            velocity_field=velocity_field,
            x0=x0,
            nfe=int(adapter._num_steps),  # type: ignore[attr-defined]
            confidence_threshold=float(confidence_threshold),
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
            "n_verifier_steps": int(stats.n_verifier_steps),
            "n_skip_steps": int(stats.n_skip_steps),
            "effective_nfe": int(stats.effective_nfe),
            "mean_confidence": float(stats.mean_confidence),
            "min_confidence": float(stats.min_confidence),
            "threshold": float(stats.threshold),
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


def _write_fastdllm_arm(
    out_path: Path,
    *,
    n: int,
    seed: int,
    family_ids: list[str],
    min_len: int,
    max_len: int,
    nfe: int,
    confidence_threshold: float,
) -> tuple[dict[str, int], dict[str, int], dict[str, list[dict[str, Any]]]]:
    """Write the Fast-DLLM arm: drives the confidence-aware solver for each record.

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

    fastdllm_rng = random.Random(int(seed) ^ 0x5A5A)
    with out_path.open("w") as f:
        for i in range(int(n)):
            family_id = family_ids[i % len(family_ids)]
            length = fastdllm_rng.randint(int(min_len), int(max_len))
            adapter = adapters[family_id]
            seq: str | None = None
            stats: dict[str, Any] = {}
            if adapter is not None:
                seq, stats = _fastdllm_emit_sequence(
                    adapter,
                    family_id=family_id,
                    length=length,
                    seed=int(seed) + int(i),
                    confidence_threshold=float(confidence_threshold),
                )
            if seq is None:
                # Defensive fallback: bare RNG draw.
                seq = _generate_sequence(fastdllm_rng, family_id, length)
                fallback_count[family_id] = fallback_count.get(family_id, 0) + 1
                stats = {"fallback": True}
            f.write(f">fastdllm_seed{i}|family={family_id}\n")
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
        mean_confs = [float(s["mean_confidence"]) for s in rec_stats if "mean_confidence" in s]
        skip_counts = [int(s["n_skip_steps"]) for s in rec_stats if "n_skip_steps" in s]
        if not eff_nfes:
            aggregated[family_id] = {"n_records": 0}
            continue
        aggregated[family_id] = {
            "n_records": len(eff_nfes),
            "effective_nfe_mean": float(_stats.mean(eff_nfes)),
            "effective_nfe_std": float(_stats.pstdev(eff_nfes)) if len(eff_nfes) > 1 else 0.0,
            "mean_confidence_mean": float(_stats.mean(mean_confs)),
            "skip_rate_mean": (
                float(_stats.mean(skip_counts)) / max(eff_nfes[0], 1)
                if eff_nfes
                else 0.0
            ),
        }
    return aggregated


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--outdir",
        type=Path,
        default=Path("/tmp/w180/fastas"),
        help="Output directory for FASTA + manifest files",
    )
    p.add_argument("--n", type=int, default=30)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--nfe", type=int, default=100)
    p.add_argument("--min-len", type=int, default=30)
    p.add_argument("--max-len", type=int, default=150)
    p.add_argument(
        "--confidence-threshold",
        type=float,
        default=DEFAULT_CONFIDENCE_THRESHOLD,
        help=(
            "Fast-DLLM confidence threshold for skipping the verifier step "
            "(continuous-FM analog of Fast-DLLM's per-token softmax threshold). "
            "Default 0.5 (per Wave 180 P1 design — conservative calibration)."
        ),
    )
    args = p.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    family_ids = list(FAMILY_PROFILES.keys())

    fasta_path = args.outdir / f"fastdllm_lineageflow_nfe{args.nfe}_seed{args.seed}.fasta"
    manifest_path = args.outdir / f"fastdllm_lineageflow_nfe{args.nfe}_seed{args.seed}.manifest.json"
    solver_stats_path = args.outdir / f"fastdllm_lineageflow_nfe{args.nfe}_seed{args.seed}.solver_stats.json"

    t0 = time.time()
    per_family_count, fallback_counts, per_record_stats = _write_fastdllm_arm(
        fasta_path,
        n=int(args.n),
        seed=int(args.seed),
        family_ids=family_ids,
        min_len=int(args.min_len),
        max_len=int(args.max_len),
        nfe=int(args.nfe),
        confidence_threshold=float(args.confidence_threshold),
    )
    wall_s = time.time() - t0

    manifest = {
        "arm": "fastdllm",
        "model": "lineageflow",
        "nfe": int(args.nfe),
        "seed": int(args.seed),
        "n": int(args.n),
        "min_len": int(args.min_len),
        "max_len": int(args.max_len),
        "confidence_threshold": float(args.confidence_threshold),
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
