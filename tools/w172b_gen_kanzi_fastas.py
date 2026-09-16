#!/usr/bin/env python3
"""Wave 172b P1 — Generate Kanzi FASTAs at NFE = 50/100/200.

Strategy
--------

* **Baseline** arm — bare RNG draws over each family's Pfam AA bias
  (same approach as
  :func:`tools.gen_lineageflow_n1000_fastas._write_baseline_arm`).
* **Framework** arm — drives :class:`KanziAdapter` (synthetic mode,
  no GPU / ckpt required) end-to-end via the standard
  ``build_initial_state -> solve_ode -> export_endpoint ->
  apply_restart_distribution`` chain repeated ``n_rounds`` times.
  The trajectory's discrete-token-index channel (the AR prior's
  ``(L_z=64,)`` int array over the Kanzi codebook) is mapped to a
  length-L AA string via mod-20 (mirrors the Wave 166b
  ``_decode_lineageflow_idx_to_aa`` mapping). Per-record seeds are
  deterministic (``seed + i``).

Wave 172b P1 scope reduction: the task spec describes this script
as "Kanzi FASTAs" but Kanzi natively emits continuous latents /
CA-coordinates, not AA sequences. This script **exercises the
discrete_token_index channel** (Kanzi's AR-prior side channel,
``KANZI_AR_SEQ_LENGTH = 64`` tokens of ``KANZI_VOCAB_SIZE = 64``)
and emits those as a 64-residue FASTA. This is the closest Kanzi
analog to LineageFlow's per-position categorical; it preserves
the byte-stable baseline-vs-framework comparison.

Output
------

    /tmp/w172b/fastas/kanzi_nfe_<NFE>/baseline.fasta
    /tmp/w172b/fastas/kanzi_nfe_<NFE>/framework.fasta
    /tmp/w172b/fastas/kanzi_nfe_<NFE>/manifest.json
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

# Ensure the repo root is on ``sys.path`` so the inner ``from
# adaptive_reflow...`` and ``from tools.run_real_ckpt_eval import
# _solve_framework`` resolve when this script is invoked directly.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

AA_SET = "ACDEFGHIKLMNPQRSTVWY"

# Per-family amino acid composition bias (mirrors
# tools/gen_lineageflow_n1000_fastas.py FAMILY_PROFILES so the kanzi
# cells share a per-family bias distribution with the lineageflow
# cells — enables cross-model byte-comparison if needed).
FAMILY_PROFILES: dict[str, dict[str, dict[str, float]]] = {
    "PF00005.27": {"bias": {"A": 0.10, "L": 0.12, "V": 0.10, "G": 0.10, "I": 0.08, "S": 0.07, "K": 0.06, "T": 0.06}},
    "PF00072.24": {"bias": {"D": 0.12, "E": 0.10, "L": 0.08, "V": 0.08, "A": 0.08, "K": 0.07, "T": 0.07, "G": 0.07}},
    "PF00183.19": {"bias": {"L": 0.10, "E": 0.10, "V": 0.08, "K": 0.08, "A": 0.08, "G": 0.07, "D": 0.07, "I": 0.06}},
    "PF02517.18": {"bias": {"E": 0.14, "K": 0.12, "A": 0.10, "D": 0.08, "L": 0.07, "G": 0.07, "V": 0.06, "T": 0.06}},
}

# Per-record NFE budget (mirrors the lineageflow default of 10; the
# framework arm splits this across n_rounds=3 rounds). Value is
# overridden by --nfe in main().
NFE_PER_RECORD: int = 10
# Number of restart-blend rounds for the framework arm. Default 3
# preserves backward compat with the Wave 158 canonical path.
N_ROUNDS: int = 3


def _biased_aa(rng: random.Random, profile: dict[str, Any], n: int) -> str:
    bias = profile["bias"]
    pairs: list[tuple[str, float]] = []
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


def _build_kanzi_adapter(family_id: str, seed: int) -> Any | None:
    """Lazy-construct a synthetic-mode :class:`KanziAdapter`.

    Mirrors :func:`tools.gen_lineageflow_n1000_fastas._build_lineageflow_adapter`.
    Returns ``None`` when the adapter import is unavailable so the
    caller can fall back to the bare-RNG path.
    """
    try:
        from adaptive_reflow.adapters.kanzi import (  # type: ignore
            KanziAdapter,
        )
    except Exception:  # pragma: no cover — defensive only
        return None
    try:
        return KanziAdapter(
            family_id=family_id,
            num_steps=NFE_PER_RECORD,
            solver="euler",
            force_mode="synthetic",
            seed_offset=int(seed),
        )
    except Exception:
        return None


def _framework_emit_sequence(
    adapter: Any,
    *,
    family_id: str,
    length: int,
    seed: int,
) -> str | None:
    """Drive one framework multi-round pass and return a length-``length`` AA string.

    Mirrors :func:`tools.gen_lineageflow_n1000_fastas._framework_emit_sequence`
    but on :class:`KanziAdapter`. Uses
    :func:`tools.run_real_ckpt_eval._solve_framework` to chain
    ``solve_ode -> export_endpoint -> apply_restart_distribution``
    for ``n_rounds=N_ROUNDS`` rounds. Returns ``None`` when the
    framework glue path raises — caller falls back to bare RNG and
    surfaces the failure in the per-record manifest.

    The Kanzi adapter's :meth:`observe_token_indices` returns a
    ``(L_z, KANZI_VOCAB_SIZE)`` simplex-shaped categorical. We
    take the per-position argmax and map ``idx % 20`` to the
    20-standard-AA alphabet (matches the Wave 166b kanzi / lineageflow
    mapping).
    """
    try:
        from tools.run_real_ckpt_eval import _solve_framework  # type: ignore
    except Exception:
        return None
    try:
        trace, _wall = _solve_framework(
            adapter,
            nfe=NFE_PER_RECORD,
            seed=int(seed),
            n_rounds=N_ROUNDS,
        )
    except Exception:
        return None
    try:
        obs_dict = adapter.observe_token_indices(
            trace, paper_quantities=None,
        )
        idx_arr = obs_dict.get("discrete_token_index")
        if idx_arr is None:
            return None
    except Exception:
        return None
    K_aa = len(AA_SET)
    flat = idx_arr.reshape(-1)
    return "".join(AA_SET[int(v) % K_aa] for v in flat[: int(length)])


def _write_baseline_arm(
    out_path: Path,
    *,
    n: int,
    seed: int,
    family_ids: list[str],
    min_len: int,
    max_len: int,
) -> dict[str, int]:
    """Write the baseline arm: bare RNG draws over each family's AA bias."""
    baseline_rng = random.Random(int(seed))
    counts: dict[str, int] = {}
    with out_path.open("w") as f:
        for i in range(int(n)):
            family_id = family_ids[i % len(family_ids)]
            length = baseline_rng.randint(int(min_len), int(max_len))
            seq = _generate_sequence(baseline_rng, family_id, length)
            f.write(f">baseline_seed{i}|family={family_id}\n")
            f.write(f"{seq}\n")
            counts[family_id] = counts.get(family_id, 0) + 1
    return counts


def _write_framework_arm(
    out_path: Path,
    *,
    n: int,
    seed: int,
    family_ids: list[str],
    min_len: int,
    max_len: int,
    framework_rng: random.Random,
) -> tuple[dict[str, int], dict[str, int]]:
    """Write the framework arm: drives :class:`KanziAdapter` for each record."""
    per_family_count: dict[str, int] = {}
    fallback_count: dict[str, int] = {}
    with out_path.open("w") as f:
        for i in range(int(n)):
            family_id = family_ids[i % len(family_ids)]
            length = framework_rng.randint(int(min_len), int(max_len))
            seed_i = int(seed) + int(i)
            adapter = _build_kanzi_adapter(family_id, seed_i)
            seq = None
            fallback = False
            if adapter is not None:
                seq = _framework_emit_sequence(
                    adapter,
                    family_id=family_id, length=length, seed=seed_i,
                )
            if seq is None:
                seq = _generate_sequence(framework_rng, family_id, length)
                fallback = True
            f.write(f">framework_seed{seed_i}|family={family_id}\n")
            f.write(f"{seq}\n")
            per_family_count[family_id] = (
                per_family_count.get(family_id, 0) + 1
            )
            if fallback:
                fallback_count[family_id] = (
                    fallback_count.get(family_id, 0) + 1
                )
    return per_family_count, fallback_count


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--outdir", type=Path, required=True)
    p.add_argument("--n", type=int, default=32)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--min-len", type=int, default=30)
    p.add_argument("--max-len", type=int, default=64)
    p.add_argument(
        "--nfe", type=int, default=10,
        help=("Per-record NFE budget for the framework arm (default 10 "
              "to match Wave 81 + Wave 86 manifest)."),
    )
    p.add_argument(
        "--n-rounds", type=int, default=3,
        help=("Number of restart-blend rounds for the framework arm. "
              "Default 3 preserves Wave 158 backward compatibility."),
    )
    args = p.parse_args()

    global NFE_PER_RECORD, N_ROUNDS
    NFE_PER_RECORD = int(args.nfe)
    N_ROUNDS = int(args.n_rounds)
    args.outdir.mkdir(parents=True, exist_ok=True)

    baseline_seed = int(args.seed)
    framework_seed = int(args.seed) ^ 0x5A5A
    family_ids = list(FAMILY_PROFILES.keys())

    manifest: dict[str, Any] = {
        "model": "kanzi",
        "n": int(args.n),
        "seed": int(args.seed),
        "min_len": int(args.min_len),
        "max_len": int(args.max_len),
        "family_ids": family_ids,
        "nfe_per_record": int(NFE_PER_RECORD),
        "n_rounds": int(N_ROUNDS),
        "scope_note": (
            "Kanzi natively emits continuous latents / CA coordinates, "
            "not AA sequences. This script exercises kanzi's "
            "discrete_token_index AR-prior channel and emits those as "
            "a 64-residue FASTA via mod-20 AA-alphabet mapping."
        ),
    }

    print(f"[w172b-kanzi] outdir={args.outdir} n={args.n} nfe={args.nfe}",
          file=sys.stderr, flush=True)
    baseline_counts = _write_baseline_arm(
        args.outdir / "baseline.fasta",
        n=int(args.n),
        seed=baseline_seed,
        family_ids=family_ids,
        min_len=int(args.min_len),
        max_len=int(args.max_len),
    )
    manifest["baseline_per_family_count"] = baseline_counts

    framework_rng = random.Random(framework_seed)
    framework_counts, fallback_counts = _write_framework_arm(
        args.outdir / "framework.fasta",
        n=int(args.n),
        seed=int(args.seed),
        family_ids=family_ids,
        min_len=int(args.min_len),
        max_len=int(args.max_len),
        framework_rng=framework_rng,
    )
    manifest["framework_per_family_count"] = framework_counts
    manifest["framework_fallback_per_family_count"] = fallback_counts

    with (args.outdir / "manifest.json").open("w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    print(
        f"[w172b-kanzi] wrote {args.outdir / 'baseline.fasta'} "
        f"(n={int(args.n)}, counts={baseline_counts})",
        file=sys.stderr, flush=True,
    )
    print(
        f"[w172b-kanzi] wrote {args.outdir / 'framework.fasta'} "
        f"(n={int(args.n)}, counts={framework_counts}, "
        f"fallback={fallback_counts})",
        file=sys.stderr, flush=True,
    )
    print(
        f"[w172b-kanzi] wrote {args.outdir / 'manifest.json'}",
        file=sys.stderr, flush=True,
    )


if __name__ == "__main__":
    main()
