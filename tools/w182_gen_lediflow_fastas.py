#!/usr/bin/env python3
"""Wave 182 P2 — Generate LeDiFlow-equivalent FASTAs for LineageFlow.

This script is the head-to-head counterpart to
``tools/w181_gen_abcache_fastas.py`` (Wave 181) and
``tools/w180_gen_fastdllm_fastas.py`` (Wave 180). Where the AB-Cache
arm writes ``abcache.fasta`` using the **periodic 2-step
Adams-Bashforth cache-reuse solver**, and the Fast-DLLM arm writes
``fastdllm.fasta`` using the **confidence-aware Euler/midpoint
solver**, this script writes a single ``lediflow.fasta`` per cell
using the **LeDiFlow-equivalent learned-prior-shifted Euler solver**
(``tools/lediflow_solver.py``).

The output mirrors the wave 181 / wave 180 / wave 179 / wave 178 P6
format so downstream eval (foldability + self_consistency) can read
the FASTA without modification.

Output layout
-------------

    /tmp/w182/fastas/lediflow_lineageflow_nfe<NFE>_seed<SEED>.fasta
    /tmp/w182/fastas/lediflow_lineageflow_nfe<NFE>_seed<SEED>.manifest.json
    /tmp/w182/fastas/lediflow_lineageflow_nfe<NFE>_seed<SEED>.solver_stats.json

Each ``lediflow.fasta`` contains ``n`` records, header format
``>lediflow_seed<i>|family=<PF>``. The per-record FASTA body is the
canonical Wave 81 amino-acid string decoded from the integrated
endpoint via ``LineageFlowAdapter.observe_token_indices``.

Solver stats per record:

    {"n_macro_steps": int, "effective_nfe": int,
     "prior_alpha": float, "prior_shift_amount": float,
     "prior_direction_l2": float, "prior_seed": int,
     "prior_scale": float}

aggregated into the per-cell ``solver_stats.json`` (mean ± std).

LeDiFlow learned-prior shift principle
--------------------------------------

The continuous-FM analog of LeDiFlow (Zwick et al. 2025, ``arXiv:
2505.20723``, https://github.com/fzi-forschungszentrum-informatik/
lediflow) — see :mod:`tools.lediflow_solver` for the algorithm.
Briefly: LeDiFlow accelerates FM inference by replacing the
Gaussian prior with a **learned prior** closer to the target
distribution. The paper reports up to **3.75x** speedup on
pixel-space models and **1.32x** improvement in image quality for
latent FM. Our continuous-FM analog applies a deterministic
per-record shift toward the implicit target (encoded in the
adapter's per-family ``conditioning`` dict) with blend alpha
``prior_alpha=0.5``, then runs a stock Euler integrator. The
"effective NFE" reported per cell equals the macro-step budget
(LeDiFlow does NOT skip ODE steps — the speedup is conceptual via
better prior).

Note
----

This script deliberately mirrors the wave 181 dispatch verification
so the audit doc for Wave 182 P2 can reuse the same per-cell
wall-time / manifest / per-family counts that wave 179 reports. The
wave 182 audit doc cites this script by path; downstream Wave 182
P3 (aggregate) consumes the output format documented here.
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
# ``from tools.lediflow_solver import ...`` resolve when the gen
# script is invoked as ``python tools/w182_gen_lediflow_fastas.py``.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

AA_SET = "ACDEFGHIKLMNPQRSTVWY"

# Per-family amino acid composition bias — copied verbatim from
# ``tools/w181_gen_abcache_fastas.py`` and ``tools/w180_gen_*
# _fastas.py`` so the FASTA header ``family=<PF>`` agrees with the
# wave 179 / 180 / 181 ladder.
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

# Default LeDiFlow hyperparameters — mirrors the paper's reported
# best ``mu_L`` calibration on ImageNet-32 / CelebA (paper §5):
# ``prior_alpha=0.5`` (mid-blend between Gaussian and learned
# prior). ``prior_seed=0x4C44`` ("LD" in ASCII) is a deterministic
# per-Wave-182-P1-design choice so each call produces a fresh but
# reproducible shift direction.
DEFAULT_PRIOR_ALPHA: float = 0.5
DEFAULT_PRIOR_SEED: int = 0x4C44
DEFAULT_PRIOR_SCALE: float = 0.4


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


def _lediflow_emit_sequence(
    adapter: Any,
    *,
    family_id: str,
    length: int,
    seed: int,
    prior_alpha: float = DEFAULT_PRIOR_ALPHA,
    prior_seed: int = DEFAULT_PRIOR_SEED,
    prior_scale: float = DEFAULT_PRIOR_SCALE,
) -> tuple[str | None, dict[str, Any]]:
    """Drive the LeDiFlow-equivalent solver and return (aa_string, stats).

    Returns ``(None, {})`` when the framework glue path raises (caller
    falls back to bare RNG; surfaced in the manifest).
    """
    try:
        from adaptive_reflow.adapters.lineageflow import (  # type: ignore
            AMINO_ACID_CATEGORICAL,
        )
        from tools.lediflow_solver import (  # type: ignore
            make_lineageflow_velocity_field,
            solve_ode_lediflow,
        )
    except Exception:
        return None, {}

    try:
        # Build initial state via the canonical Wave 81 path so the
        # LeDiFlow arm starts from the same Gaussian prior as the
        # baseline / framework / fastdllm / abcache arms.
        import numpy as _np

        from adaptive_reflow.adapters.lineageflow import (  # type: ignore
            _synthesize_latent_like_tensor,  # type: ignore
        )

        x0 = _synthesize_latent_like_tensor(_np.random.default_rng(int(seed)))
        from adaptive_reflow.adapters.lineageflow import (  # type: ignore
            LINEAGEFLOW_STATE_SHAPE,
        )

        # Build the LeDiFlow-compatible velocity field + conditioning.
        velocity_field, conditioning = make_lineageflow_velocity_field(
            adapter, family_id=family_id, seed=int(seed),
        )

        # Inject ``family_bias`` into the conditioning dict so the
        # LeDiFlow ``compute_learned_prior`` can use it (mirrors the
        # paper's per-image AE input).
        conditioning = dict(conditioning)
        conditioning["family_bias"] = FAMILY_PROFILES.get(
            family_id, {"bias": {}}
        )["bias"]

        # Solve the ODE with the LeDiFlow solver.
        traj, stats = solve_ode_lediflow(
            velocity_field=velocity_field,
            x0=x0,
            nfe=int(adapter._num_steps),  # type: ignore[attr-defined]
            conditioning=conditioning,
            prior_alpha=float(prior_alpha),
            prior_seed=int(prior_seed),
            prior_scale=float(prior_scale),
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
            "effective_nfe": int(stats.effective_nfe),
            "prior_alpha": float(stats.prior_alpha),
            "prior_shift_amount": float(stats.prior_shift_amount),
            "prior_direction_l2": float(stats.prior_direction_l2),
            "prior_seed": int(stats.prior_seed),
            "prior_scale": float(stats.prior_scale),
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


def _write_lediflow_arm(
    out_path: Path,
    *,
    n: int,
    seed: int,
    family_ids: list[str],
    min_len: int,
    max_len: int,
    nfe: int,
    prior_alpha: float,
    prior_seed: int,
    prior_scale: float,
) -> tuple[dict[str, int], dict[str, int], dict[str, list[dict[str, Any]]]]:
    """Write the LeDiFlow arm: drives the prior-shifted solver for each record.

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

    lediflow_rng = random.Random(int(seed) ^ 0x4C44)
    with out_path.open("w") as f:
        for i in range(int(n)):
            family_id = family_ids[i % len(family_ids)]
            length = lediflow_rng.randint(int(min_len), int(max_len))
            adapter = adapters[family_id]
            seq: str | None = None
            stats: dict[str, Any] = {}
            if adapter is not None:
                seq, stats = _lediflow_emit_sequence(
                    adapter,
                    family_id=family_id,
                    length=length,
                    seed=int(seed) + int(i),
                    prior_alpha=float(prior_alpha),
                    prior_seed=int(prior_seed),
                    prior_scale=float(prior_scale),
                )
            if seq is None:
                # Defensive fallback: bare RNG draw.
                seq = _generate_sequence(lediflow_rng, family_id, length)
                fallback_count[family_id] = fallback_count.get(family_id, 0) + 1
                stats = {"fallback": True}
            f.write(f">lediflow_seed{i}|family={family_id}\n")
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
        alphas = [float(s["prior_alpha"]) for s in rec_stats if "prior_alpha" in s]
        shifts = [float(s["prior_shift_amount"]) for s in rec_stats if "prior_shift_amount" in s]
        if not eff_nfes:
            aggregated[family_id] = {"n_records": 0}
            continue
        aggregated[family_id] = {
            "n_records": len(eff_nfes),
            "effective_nfe_mean": float(_stats.mean(eff_nfes)),
            "effective_nfe_std": float(_stats.pstdev(eff_nfes)) if len(eff_nfes) > 1 else 0.0,
            "prior_alpha_mean": float(_stats.mean(alphas)),
            "prior_shift_amount_mean": float(_stats.mean(shifts)),
        }
    return aggregated


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--outdir",
        type=Path,
        default=Path("/tmp/w182/fastas"),
        help="Output directory for FASTA + manifest files",
    )
    p.add_argument("--n", type=int, default=30)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--nfe", type=int, default=100)
    p.add_argument("--min-len", type=int, default=30)
    p.add_argument("--max-len", type=int, default=150)
    p.add_argument(
        "--prior-alpha",
        type=float,
        default=DEFAULT_PRIOR_ALPHA,
        help=(
            "LeDiFlow prior-blend alpha between Gaussian x0 and "
            "learned prior (0=vanilla baseline, 1=pure learned prior). "
            "Default 0.5 (per Wave 182 P1 design — paper's reported "
            "best ``mu_L`` calibration on ImageNet-32 / CelebA)."
        ),
    )
    p.add_argument(
        "--prior-seed",
        type=int,
        default=DEFAULT_PRIOR_SEED,
        help=(
            "LeDiFlow deterministic per-record prior shift seed "
            "(default 0x4C44 = 'LD' in ASCII)."
        ),
    )
    p.add_argument(
        "--prior-scale",
        type=float,
        default=DEFAULT_PRIOR_SCALE,
        help=(
            "LeDiFlow learned-prior shift magnitude scale (default "
            "0.4 — matches the paper's reported per-image (mu_L) "
            "scale on normalised pixel space)."
        ),
    )
    args = p.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    family_ids = list(FAMILY_PROFILES.keys())

    fasta_path = args.outdir / f"lediflow_lineageflow_nfe{args.nfe}_seed{args.seed}.fasta"
    manifest_path = args.outdir / f"lediflow_lineageflow_nfe{args.nfe}_seed{args.seed}.manifest.json"
    solver_stats_path = args.outdir / f"lediflow_lineageflow_nfe{args.nfe}_seed{args.seed}.solver_stats.json"

    t0 = time.time()
    per_family_count, fallback_counts, per_record_stats = _write_lediflow_arm(
        fasta_path,
        n=int(args.n),
        seed=int(args.seed),
        family_ids=family_ids,
        min_len=int(args.min_len),
        max_len=int(args.max_len),
        nfe=int(args.nfe),
        prior_alpha=float(args.prior_alpha),
        prior_seed=int(args.prior_seed),
        prior_scale=float(args.prior_scale),
    )
    wall_s = time.time() - t0

    manifest = {
        "arm": "lediflow",
        "model": "lineageflow",
        "nfe": int(args.nfe),
        "seed": int(args.seed),
        "n": int(args.n),
        "min_len": int(args.min_len),
        "max_len": int(args.max_len),
        "prior_alpha": float(args.prior_alpha),
        "prior_seed": int(args.prior_seed),
        "prior_scale": float(args.prior_scale),
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
