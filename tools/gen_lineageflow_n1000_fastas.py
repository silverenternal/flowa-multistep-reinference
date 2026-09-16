#!/usr/bin/env python3
"""Generate 1000 FASTA per arm (baseline + framework) for LineageFlow N=1000 sweep.

Strategy
--------

* **Baseline** arm — bare RNG draws over each family's Pfam AA bias.
  This is the literal "no framework glue" path: each record is a
  single :func:`_generate_sequence` call from a per-arm RNG sub-stream.
* **Framework** arm — drives the real
  :class:`LineageFlowAdapter` end-to-end. For each FASTA record
  index ``i`` the gen script calls
  :func:`tools.run_real_ckpt_eval._solve_framework` with
  ``nfe=NFE, n_rounds=3`` so the per-record sequence is the result
  of ``solve_ode -> export_endpoint -> apply_restart_distribution``
  chained three times (the canonical Wave 45 multi-round path).
  Per-record seed offsets are deterministic (``seed + i``) so the
  framework arm is reproducible without contaminating baseline.

Wave 86 Agent B — closes Pitfall #2 surfaced in
``docs/audit/wave86-phase1-audit.md`` §1: the previous implementation
shared one ``random.Random`` between the two arms and never invoked
the framework glue at all, so ``framework.fasta`` was byte-identical
to ``baseline.fasta`` modulo the ``>header`` line.

Output
------

    data/lineageflow_n1000/baseline.fasta    (1000 seqs, >baseline_seed<N>|family=<PF>)
    data/lineageflow_n1000/framework.fasta   (1000 seqs, >framework_seed<N>|family=<PF>)
    data/lineageflow_n1000/manifest.json     (per-record metadata)
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

# Ensure the repo root (parent of this `tools/` script) is on
# ``sys.path`` so the inner ``from tools.run_real_ckpt_eval import
# _solve_framework`` resolves when the gen script is invoked as
# ``python tools/gen_lineageflow_n1000_fastas.py`` (Python prepends
# the SCRIPT'S directory, i.e. ``tools/``, to sys.path — leaving the
# repo root absent, which would silently force every framework record
# into the bare-RNG fallback and break the Wave 86 Agent B
# ``framework_fallback_per_family_count == {}`` invariant).
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

AA_SET = "ACDEFGHIKLMNPQRSTVWY"

# Per-family amino acid composition bias (rough mimicry of Pfam clan profiles)
FAMILY_PROFILES = {
    "PF00005.27": {  # ABC transporter — mixed
        "bias": {"A": 0.10, "L": 0.12, "V": 0.10, "G": 0.10, "I": 0.08, "S": 0.07, "K": 0.06, "T": 0.06},
    },
    "PF00072.24": {  # Response regulator receiver — polar + acidic
        "bias": {"D": 0.12, "E": 0.10, "L": 0.08, "V": 0.08, "A": 0.08, "K": 0.07, "T": 0.07, "G": 0.07},
    },
    "PF00183.19": {  # HSP90 — hydrophobic + charged mix
        "bias": {"L": 0.10, "E": 0.10, "V": 0.08, "K": 0.08, "A": 0.08, "G": 0.07, "D": 0.07, "I": 0.06},
    },
    "PF02517.18": {  # CP12 — basic + acidic
        "bias": {"E": 0.14, "K": 0.12, "A": 0.10, "D": 0.08, "L": 0.07, "G": 0.07, "V": 0.06, "T": 0.06},
    },
}

# Per-record NFE budget for the framework arm (matches the Wave 81
# upstream-eval default). The framework arm splits this across
# ``n_rounds=3`` rounds. ``NFE_PER_RECORD`` is a module-level binding
# kept here for backward compatibility with Wave 81/86 manifest
# (default 10) — the value actually used at runtime is the one
# supplied to ``--nfe`` on the CLI and assigned in ``main()`` below.
# Wave 168 P1: ``--nfe`` was being silently ignored because this
# module-level constant was hardcoded (Wave 167 P2 discovery).
NFE_PER_RECORD: int = 10  # legacy default; overridden by --nfe in main()
# Wave 170 P3: ``--n-rounds`` flag now allows overriding the
# module-level ``N_ROUNDS`` constant via CLI (was hardcoded
# ``n_rounds=3`` in Wave 158). Default 3 preserves backward compat
# with the Wave 81/86/158 manifest bytes. The baseline arm in the
# Wave 170 fair-baseline comparison uses ``--n-rounds 1`` to disable
# the framework's restart-blend glue (so the baseline arm exercises
# only ``solve_ode`` with no ``apply_restart_distribution`` chain).
N_ROUNDS: int = 3  # legacy default; overridden by --n-rounds in main()


def _biased_aa(rng: random.Random, profile: dict, n: int) -> str:
    """Sample n AAs from the family's bias (fallback to uniform if bias under-specifies)."""
    bias = profile["bias"]
    # Build (aa, weight) pairs and renormalise.
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


def _build_lineageflow_adapter(family_id: str, seed: int) -> Any | None:
    """Lazy-construct a synthetic-mode :class:`LineageFlowAdapter`.

    The adapter defaults to ``force_mode="auto"``, which falls back
    to ``"synthetic"`` when the published LineageFlow ckpt is not
    vendored on disk. We deliberately do NOT require ``torch`` for
    the gen script — the synthetic velocity field is deterministic
    NumPy and exposes the same ``solve_ode`` /
    ``apply_restart_distribution`` Protocol surface that the real
    torch adapter would (Wave 81 5-LOC stub fix). The framework arm
    therefore exercises the **real multi-round glue layer** even on
    cold-clone hosts.

    Returns ``None`` when the adapter import is unavailable (e.g.
    ``adaptive_reflow`` not on PYTHONPATH) so the caller can fall
    back to the bare-RNG path.

    Note: the LineageFlow adapter constructor takes ``seed_offset``
    and ``synthetic_seed`` (NOT a flat ``seed=`` kwarg) — the per-cell
    seed offset is layered onto the synthetic RNG via
    ``seed_offset=int(seed)`` so each adapter instance is keyed to a
    deterministic per-family seed stream.
    """
    try:
        from adaptive_reflow.adapters.lineageflow import (  # type: ignore
            LineageFlowAdapter,
        )
    except Exception as _exc:  # pragma: no cover — defensive only
        return None
    try:
        return LineageFlowAdapter(
            family_id=family_id,
            num_steps=NFE_PER_RECORD,
            solver="euler",
            force_mode="synthetic",
            seed_offset=int(seed),
        )
    except Exception:
        # Adapter may still raise on a host without the synthetic
        # velocity field — same fallback semantics.
        return None


def _framework_emit_sequence(
    adapter: Any,
    *,
    family_id: str,
    length: int,
    seed: int,
) -> str | None:
    """Drive one framework multi-round pass and return a length-``length`` AA string.

    Uses :func:`tools.run_real_ckpt_eval._solve_framework` to chain
    ``solve_ode -> export_endpoint -> apply_restart_distribution``
    for ``n_rounds=N_ROUNDS`` rounds at ``nfe=NFE_PER_RECORD`` each
    (the canonical Wave 45 multi-round path). The returned trace
    carries the per-position categorical at the integrated endpoint,
    which :meth:`LineageFlowAdapter.observe_token_indices` decodes
    to a ``(L,)`` int64 array via argmax. We then apply the
    canonical mod-20 AA-alphabet mapping (matches
    ``tools/run_real_ckpt_eval._decode_lineageflow_idx_to_aa``).

    Returns ``None`` when the framework glue path raises — the
    caller falls back to the bare-RNG draw and surfaces the failure
    in the per-record manifest so the auditor can detect failed
    cells.

    Note: the framework-side ``length`` argument is informational
    only — the adapter's per-position categorical has a fixed
    canonical length (``LINEAGEFLOW_MAX_LENGTH = 256``). We trim
    the returned AA string to ``length`` to honour the per-record
    length distribution captured in ``FAMILY_PROFILES`` + the
    command-line ``--min-len`` / ``--max-len`` flags.
    """
    try:
        from adaptive_reflow.adapters.lineageflow import (  # type: ignore
            AMINO_ACID_CATEGORICAL,
            LINEAGEFLOW_VOCAB_SIZE,
        )
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
        obs_dict = adapter.observe_token_indices(trace, paper_quantities=None)
        idx_arr = obs_dict.get(str(AMINO_ACID_CATEGORICAL))
        if idx_arr is None:
            return None
    except Exception:
        return None
    K_aa = len(AA_SET)
    flat = idx_arr.reshape(-1)
    aa_str = "".join(AA_SET[int(v) % K_aa] for v in flat[: int(length)])
    return aa_str


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
    """Write the framework arm: drives :class:`LineageFlowAdapter` for each record.

    Returns ``(per_family_count, fallback_count)``. ``fallback_count``
    tallies the records where the real framework path raised and we
    fell back to bare RNG — surfaced in the manifest so the auditor
    can detect failed cells.
    """
    per_family_count: dict[str, int] = {}
    fallback_count: dict[str, int] = {}

    # Build one synthetic-mode adapter per family. The adapter is
    # deterministic by ``family_id`` + ``seed`` so a single instance
    # per family preserves per-record byte-stability (each subsequent
    # solve_ode call is keyed by a per-record seed offset).
    adapters: dict[str, Any | None] = {}
    for family_id in family_ids:
        adapters[family_id] = _build_lineageflow_adapter(family_id, int(seed))

    with out_path.open("w") as f:
        for i in range(int(n)):
            family_id = family_ids[i % len(family_ids)]
            length = framework_rng.randint(int(min_len), int(max_len))
            adapter = adapters[family_id]
            seq: str | None = None
            if adapter is not None:
                seq = _framework_emit_sequence(
                    adapter,
                    family_id=family_id,
                    length=length,
                    seed=int(seed) + int(i),
                )
            if seq is None:
                # Defensive fallback: bare-RNG draw. The auditor
                # surfaces this via ``fallback_count`` so failed
                # cells are detectable (Pitfall #2 not closed for
                # that record only — the framework-side surface
                # remains exercised for every other record).
                seq = _generate_sequence(framework_rng, family_id, length)
                fallback_count[family_id] = (
                    fallback_count.get(family_id, 0) + 1
                )
            f.write(f">framework_seed{i}|family={family_id}\n")
            f.write(f"{seq}\n")
            per_family_count[family_id] = (
                per_family_count.get(family_id, 0) + 1
            )
    return per_family_count, fallback_count


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--outdir", type=Path, default=Path("data/lineageflow_n1000"))
    p.add_argument("--n", type=int, default=1000)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--min-len", type=int, default=30)
    p.add_argument("--max-len", type=int, default=150)
    p.add_argument(
        "--nfe",
        type=int,
        default=10,
        help=(
            "Per-record NFE budget for the framework arm "
            "(default: 10 to match Wave 81 + Wave 86 manifest). "
            "Wired into NFE_PER_RECORD via global reassignment in main()."
        ),
    )
    p.add_argument(
        "--n-rounds",
        type=int,
        default=3,
        help=(
            "Number of restart-blend rounds for the framework arm. "
            "Baseline arm: use 1 (no restart-blend glue, pure solve_ode). "
            "Framework arm: use 3 (Wave 158 canonical Wave 45 multi-round path). "
            "Default 3 preserves backward compatibility with Wave 81/86/158 manifest bytes."
        ),
    )
    args = p.parse_args()

    # Wire the CLI --nfe flag through to the module-level NFE_PER_RECORD
    # constant that ``_build_lineageflow_adapter`` and
    # ``_framework_emit_sequence`` read. Using ``global`` keeps the
    # change minimal — the alternative (passing ``nfe`` through every
    # call site) would touch every function signature in this file
    # without buying anything. The default value (10) preserves
    # backward compatibility with the Wave 81/86 manifest bytes.
    global NFE_PER_RECORD
    NFE_PER_RECORD = int(args.nfe)
    # Wave 170 P3: same minimal ``global`` wire-through pattern for
    # ``--n-rounds`` — keeps the constant readable from the call sites
    # in ``_build_lineageflow_adapter`` + ``_framework_emit_sequence``
    # without churning every function signature. Default 3 preserves
    # Wave 158 backward compat.
    global N_ROUNDS
    N_ROUNDS = int(args.n_rounds)
    args.outdir.mkdir(parents=True, exist_ok=True)

    # Distinct RNG sub-streams per arm so the framework arm cannot
    # contaminate the baseline (and vice versa). The framework arm's
    # RNG only feeds the rare defensive fallback (when the
    # adapter is unavailable for a record).
    baseline_seed = int(args.seed)
    framework_seed = int(args.seed) ^ 0x5A5A
    family_ids = list(FAMILY_PROFILES.keys())

    manifest: dict[str, Any] = {
        "n": int(args.n),
        "seed": int(args.seed),
        "min_len": int(args.min_len),
        "max_len": int(args.max_len),
        "family_ids": family_ids,
        "nfe_per_record": int(NFE_PER_RECORD),
        "n_rounds": int(N_ROUNDS),
    }

    # ---- Baseline arm (bare RNG, preserved byte-shape) -----------------
    baseline_counts = _write_baseline_arm(
        args.outdir / "baseline.fasta",
        n=int(args.n),
        seed=baseline_seed,
        family_ids=family_ids,
        min_len=int(args.min_len),
        max_len=int(args.max_len),
    )
    manifest["baseline_per_family_count"] = dict(baseline_counts)
    print(f"wrote {args.outdir / 'baseline.fasta'} (n={int(args.n)})")

    # ---- Framework arm (real LineageFlowAdapter multi-round pass) ------
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
    manifest["framework_per_family_count"] = dict(framework_counts)
    manifest["framework_fallback_per_family_count"] = dict(fallback_counts)
    print(f"wrote {args.outdir / 'framework.fasta'} (n={int(args.n)})")

    # Combined manifest field (Wave 81 shape, additive — preserves
    # the existing ``per_family_count`` key for downstream consumers).
    manifest["per_family_count"] = dict(baseline_counts)

    manifest_path = args.outdir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"wrote {manifest_path}")


if __name__ == "__main__":
    main()
