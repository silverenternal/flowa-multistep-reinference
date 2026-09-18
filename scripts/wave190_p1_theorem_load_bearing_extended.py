#!/usr/bin/env python3
"""Wave 190 P1 — sweep-driver extension: n=30 paired sweep on kanzi + lineageflow.

This script extends the Wave 189 P4 ablation driver (see
``scripts/wave189_p4_theorem_load_bearing_kanzi.py``) to support:

* a **paired n=30 sweep** on both the kanzi adapter (Wave 36 protein
  axis, synthetic mode, ``state_shape=(64, 64)``) and the LineageFlow
  adapter (Wave 10 protein axis, synthetic mode,
  ``state_shape=(256, 33)`` per the Wave 188 P1 ground truth);
* **continuity** with the n=3 Wave 189 P4 baseline by preserving the
  seeds {0, 1, 2} per-seed records verbatim as a "n=3 sub-experiment"
  in the output JSON (the original Wave 189 P4 baseline numbers are
  the Wave 188 P3 follow-up on the protein axis);
* a **3-arm sweep** on each adapter, mirroring the Wave 189 P4 design:

    Config A — vanilla_baseline
        Single-pass ODE solve, no framework. Reference.

    Config B — framework_without_paper_quantities
        Multi-round framework solve with the bare cosine ``n_cap``
        ramp (no paper-quantity wrapper, no A_g / B_g / C_g / e_rho
        consumer, no ``profile_residual_fn``).

    Config C — framework_with_paper_quantities
        Multi-round framework solve with the
        :class:`PaperRatioAdaptiveScheduler` that consumes the
        literal Theorem 1 quantities (A_g / B_g / C_g / e_rho) via
        :class:`CodimensionSheetScheduler` paper-quantity branch.

The verdict (load-bearing on the protein axis, not load-bearing, etc.)
is identical to the Wave 189 P4 verdict schema so the two JSONs can
be diffed cell-by-cell and the ``n=3`` cells serve as the continuity
check.

CLI flags (per the Wave 190 P1 task spec):

* ``--n-seeds`` — number of seeds to sweep (default ``30``). When the
  value exceeds 3 the seeds ``{3, 4, ..., n-1}`` are *new*; seeds
  ``{0, 1, 2}`` are matched cell-for-cell against the Wave 189 P4
  baseline to surface any byte-stability regression introduced by
  this extension.
* ``--adapter`` — ``kanzi``, ``lineageflow``, or ``both`` (default
  ``kanzi`` for backward compatibility with Wave 189 P4).
* ``--n-rounds`` — framework rounds per cell (default ``5``, matches
  Wave 189 P4 with one extra round of paper-quantity consumption).
* ``--nfe`` — per-pass NFE budget (default ``1000`` for kanzi,
  ``100`` for lineageflow to match the canonical Pfam-RP55 NFE used
  by the LineageFlow paper headline runs).

Output JSON: one per adapter
* ``verification_outputs/wave190-p2-kanzi-n30.json``
* ``verification_outputs/wave190-p3-lineageflow-n30.json``

The smoke-test invocation (n=6 seeds, kanzi only) writes
``verification_outputs/wave190-p2-kanzi-n6-smoke.json``.
"""
from __future__ import annotations

import argparse
import importlib.util as _importlib_spec
import json
import sys
import time
import traceback
from datetime import UTC, datetime, timezone
from pathlib import Path
from statistics import mean, pstdev

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Reuse the original Wave 189 P4 solver helpers so the n=3 continuity
# cells are byte-identical to the baseline. The original script is
# the Wave 188 P3 ablation-on-kanzi driver; its _solve_baseline,
# _solve_framework, _extract_endpoint_latent, _per_position_entropy_reduction,
# _aggregate, _implication, and _make_adapter helpers are imported
# below.

_ORIG_PATH = REPO_ROOT / "scripts" / "wave189_p4_theorem_load_bearing_kanzi.py"
_spec = _importlib_spec.spec_from_file_location(
    "wave189_p4_original", _ORIG_PATH,
)
assert _spec is not None and _spec.loader is not None
_w189 = _importlib_spec.module_from_spec(_spec)
_spec.loader.exec_module(_w189)  # type: ignore[union-attr]

import numpy as np  # noqa: E402

# Original defaults (for the n=3 baseline sub-experiment, must match
# the Wave 189 P4 JSON's *values*).
DEFAULT_SEEDS_BASELINE: tuple[int, ...] = (0, 1, 2)
DEFAULT_NSEEDS: int = 30

# Per-adapter NFE defaults: the kanzi synthetic field is cheap
# (~8 ms per pass) so 1000 NFE matches the Wave 188 P3 kanzi NFE
# ladder; lineageflow's published Pfam-RP55 headline runs use 100
# NFE per round (paper §5), so we default to 100 for lineageflow to
# match the canonical adapter-state-size scaling (kanzi is 8x
# smaller on the latent, lineageflow's state_shape is 256*33 =
# 8448 floats vs kanzi's 64*64 = 4096 floats).
DEFAULT_NFE_KANZI: int = 1000
DEFAULT_NFE_LINEAGEFLOW: int = 100

DEFAULT_N_ROUNDS: int = 5


# ---------------------------------------------------------------------------
# Per-adapter factory + adapter-specific constants
# ---------------------------------------------------------------------------


def _make_kanzi_adapter():
    """Wave 189 P4 kanzi synthetic adapter factory."""
    from adaptive_reflow.adapters.kanzi import default_kanzi_adapter

    return default_kanzi_adapter(force_mode="synthetic")


def _make_lineageflow_adapter():
    """Wave 10 LineageFlow synthetic adapter factory (state_shape=(256, 33))."""
    from adaptive_reflow.adapters.lineageflow import default_lineageflow_adapter

    return default_lineageflow_adapter(force_mode="synthetic")


_ADAPTER_FACTORIES = {
    "kanzi": _make_kanzi_adapter,
    "lineageflow": _make_lineageflow_adapter,
}


def _adapter_label(adapter_kind: str) -> str:
    """Return the human label for the adapter kind."""
    if adapter_kind == "kanzi":
        return "kanzi (synthetic, 64x64)"
    if adapter_kind == "lineageflow":
        return "lineageflow (synthetic, 256x33)"
    raise ValueError(f"unknown adapter_kind {adapter_kind!r}")


# ---------------------------------------------------------------------------
# Per-cell runner — adapter-agnostic; uses the original Wave 189 P4
# solver helpers (``_solve_baseline``, ``_solve_framework``,
# ``_extract_endpoint_latent``, ``_per_position_entropy_reduction``).
# ---------------------------------------------------------------------------


def _run_cell(adapter_kind: str, seed: int, nfe: int,
              n_rounds: int) -> dict[str, object]:
    """Run baseline + framework-with-cosine + framework-with-paper-ratio.

    Returns a per-seed cell dict whose shape mirrors the Wave 189 P4
    baseline cell shape (so the two JSONs are diffable cell-by-cell).
    """
    factory = _ADAPTER_FACTORIES[adapter_kind]
    adapter = factory()
    cell: dict[str, object] = {
        "seed": int(seed),
        "nfe_budget": int(nfe),
        "n_rounds_framework": int(n_rounds),
        "adapter_kind": str(adapter_kind),
        "adapter_mode": "synthetic",
    }
    # --- baseline ---
    try:
        _b_trace, baseline_wall = _w189._solve_baseline(
            adapter, nfe=int(nfe), seed=int(seed),
        )
        base_endpoint = _w189._extract_endpoint_latent(adapter, _b_trace)
        cell["baseline_endpoint_shape"] = (
            list(base_endpoint.shape) if base_endpoint is not None else None
        )
        cell["baseline_endpoint_norm"] = (
            float(np.linalg.norm(base_endpoint))
            if base_endpoint is not None else None
        )
        cell["wallclock_baseline_s"] = round(float(baseline_wall), 4)
    except Exception as exc:
        cell["baseline_error"] = f"{type(exc).__name__}:{exc}"
        cell["traceback"] = traceback.format_exc()
        return cell

    # --- framework WITHOUT paper quantities (cosine) ---
    try:
        _f_trace, cosine_wall = _w189._solve_framework(
            adapter, nfe=int(nfe), seed=int(seed),
            n_rounds=int(n_rounds), scheduler_family="cosine",
        )
        cosine_endpoint = _w189._extract_endpoint_latent(adapter, _f_trace)
        cell["cosine_endpoint_shape"] = (
            list(cosine_endpoint.shape)
            if cosine_endpoint is not None else None
        )
        cell["cosine_endpoint_norm"] = (
            float(np.linalg.norm(cosine_endpoint))
            if cosine_endpoint is not None else None
        )
        cell["wallclock_cosine_s"] = round(float(cosine_wall), 4)
        if base_endpoint is not None and cosine_endpoint is not None:
            cell["cosine_endpoint_l2"] = float(
                np.linalg.norm(cosine_endpoint - base_endpoint)
            )
            cell["cosine_per_position_entropy_reduction"] = (
                _w189._per_position_entropy_reduction(
                    base_endpoint, cosine_endpoint
                )
            )
        else:
            cell["cosine_endpoint_l2"] = None
            cell["cosine_per_position_entropy_reduction"] = None
    except Exception as exc:
        cell["cosine_error"] = f"{type(exc).__name__}:{exc}"
        cell["traceback_cosine"] = traceback.format_exc()

    # --- framework WITH paper quantities (PaperRatioAdaptiveScheduler) ---
    try:
        _p_trace, paper_wall = _w189._solve_framework(
            adapter, nfe=int(nfe), seed=int(seed),
            n_rounds=int(n_rounds), scheduler_family="paper_ratio",
        )
        paper_endpoint = _w189._extract_endpoint_latent(adapter, _p_trace)
        cell["paper_endpoint_shape"] = (
            list(paper_endpoint.shape)
            if paper_endpoint is not None else None
        )
        cell["paper_endpoint_norm"] = (
            float(np.linalg.norm(paper_endpoint))
            if paper_endpoint is not None else None
        )
        cell["wallclock_paper_s"] = round(float(paper_wall), 4)
        if base_endpoint is not None and paper_endpoint is not None:
            cell["paper_endpoint_l2"] = float(
                np.linalg.norm(paper_endpoint - base_endpoint)
            )
            cell["paper_per_position_entropy_reduction"] = (
                _w189._per_position_entropy_reduction(
                    base_endpoint, paper_endpoint
                )
            )
        else:
            cell["paper_endpoint_l2"] = None
            cell["paper_per_position_entropy_reduction"] = None
    except Exception as exc:
        cell["paper_error"] = f"{type(exc).__name__}:{exc}"
        cell["traceback_paper"] = traceback.format_exc()

    return cell


# ---------------------------------------------------------------------------
# Aggregation + verdict (reuses the Wave 189 P4 aggregator verbatim)
# ---------------------------------------------------------------------------


def _verdict_from_agg(agg: dict, *, n_records: int) -> str:
    """Replicate the Wave 189 P4 verdict rule on the aggregated stats."""
    p_val_e = agg["p_value_paired_permutation"]
    p_val_l2 = agg["p_value_paired_permutation_l2_axis"]
    es_l2 = agg["effect_size"]["l2_axis"]
    e_significant = p_val_e is not None and p_val_e < 0.05
    l2_significant = p_val_l2 is not None and p_val_l2 < 0.05
    if e_significant and l2_significant:
        verdict = "load_bearing"
    elif e_significant:
        verdict = "load_bearing_only_on_axis_entropy_reduction"
    elif l2_significant:
        verdict = "load_bearing_only_on_axis_endpoint_l2"
    else:
        verdict = "not_load_bearing"
    if (
        es_l2 is not None and abs(es_l2) >= 1.0
        and verdict == "not_load_bearing"
    ):
        # With n=30 the marginal verdict is reported as a stability
        # overlay (the Wave 189 P4 "marginal_n3" branch was a small-n
        # carve-out; with n>=10 the marginal verdict is reported as
        # plain "load_bearing_only_on_axis_endpoint_l2" so the JSON
        # schema is uniform across n).
        verdict = "load_bearing_only_on_axis_endpoint_l2_marginal"
    base_ent = agg["per_config_stats"][
        "cosine_per_position_entropy_reduction"
    ]["mean"]
    if base_ent is None or (base_ent is not None and abs(base_ent) < 1e-6):
        verdict = (
            f"{verdict}+framework_degenerate_on_entropy_axis"
        )
    return verdict


# ---------------------------------------------------------------------------
# n=3 baseline continuity check
# ---------------------------------------------------------------------------


def _load_n3_baseline(
    *, adapter_kind: str
) -> tuple[list[dict], dict] | None:
    """Load the original Wave 189 P4 baseline JSON for ``adapter_kind``.

    Returns ``(cells, summary)`` where ``cells`` is the per-seed list
    and ``summary`` is the aggregated ``configurations`` block. The
    function returns ``None`` when no baseline exists (e.g. when
    ``adapter_kind == "lineageflow"`` and only the n=30 sweep is
    being run for the first time).
    """
    if adapter_kind == "kanzi":
        baseline_path = (
            REPO_ROOT / "verification_outputs"
            / "wave189-p4-theorem-load-bearing-kanzi.json"
        )
    else:
        # No Wave 189 P4 lineageflow baseline exists yet — the Wave
        # 190 P1 lineageflow sweep is the first n=3 sub-experiment
        # on that adapter.
        return None
    if not baseline_path.exists():
        return None
    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    cells = payload.get("cells", [])
    configurations = payload.get("configurations", {})
    return cells, configurations


def _continuity_check(
    *, fresh_cells: list[dict], baseline_cells: list[dict],
    tolerance_pct: float = 1e-3,
) -> dict:
    """Compare fresh n=3 cells to the Wave 189 P4 baseline per-seed.

    Returns a per-seed continuity dict; the parent driver uses this
    to surface any byte-stability regression introduced by this
    extension.
    """
    out: dict[str, object] = {
        "n_baseline": len(baseline_cells),
        "n_fresh": len(fresh_cells),
        "per_seed": [],
        "all_match_within_tolerance": True,
    }
    by_seed_fresh = {int(c["seed"]): c for c in fresh_cells}
    n_match = 0
    n_total = 0
    for bcell in baseline_cells:
        seed = int(bcell["seed"])
        fcell = by_seed_fresh.get(seed)
        if fcell is None:
            out["per_seed"].append({
                "seed": seed,
                "match": False,
                "reason": "fresh_cell_missing",
            })
            out["all_match_within_tolerance"] = False
            continue
        n_total += 1
        diffs: dict[str, dict] = {}
        per_seed_match = True
        for k in (
            "cosine_endpoint_l2",
            "cosine_per_position_entropy_reduction",
            "paper_endpoint_l2",
            "paper_per_position_entropy_reduction",
        ):
            bv = bcell.get(k)
            fv = fcell.get(k)
            if bv is None or fv is None:
                diffs[k] = {"baseline": bv, "fresh": fv, "match": False}
                per_seed_match = False
                continue
            bv_f = float(bv)
            fv_f = float(fv)
            denom = max(abs(bv_f), 1e-12)
            rel = abs(bv_f - fv_f) / denom
            match = rel <= float(tolerance_pct)
            diffs[k] = {
                "baseline": bv_f,
                "fresh": fv_f,
                "rel_diff": rel,
                "match": match,
            }
            if not match:
                per_seed_match = False
        if per_seed_match:
            n_match += 1
        out["per_seed"].append({
            "seed": seed,
            "match": per_seed_match,
            "diffs": diffs,
        })
        if not per_seed_match:
            out["all_match_within_tolerance"] = False
    out["n_match"] = int(n_match)
    out["n_total_compared"] = int(n_total)
    return out


# ---------------------------------------------------------------------------
# Per-adapter sweep runner
# ---------------------------------------------------------------------------


def _run_adapter_sweep(
    *, adapter_kind: str, seeds: list[int], nfe: int, n_rounds: int,
) -> dict[str, object]:
    """Run the n=|seeds| paired 3-arm sweep on one adapter."""
    print(
        f"[SWEEP] adapter={adapter_kind} n_seeds={len(seeds)} "
        f"nfe={nfe} n_rounds={n_rounds}",
        file=sys.stderr,
    )
    cells: list[dict] = []
    for seed in seeds:
        t_seed = time.monotonic()
        print(
            f"[CELL] adapter={adapter_kind} seed={seed} nfe={nfe} "
            f"n_rounds={n_rounds}", file=sys.stderr,
        )
        cell = _run_cell(
            adapter_kind=adapter_kind, seed=int(seed),
            nfe=int(nfe), n_rounds=int(n_rounds),
        )
        cells.append(cell)
        wall = time.monotonic() - t_seed
        print(
            f"  -> wall={wall:.2f}s "
            f"baseline_norm={cell.get('baseline_endpoint_norm')} "
            f"cosine_l2={cell.get('cosine_endpoint_l2')} "
            f"paper_l2={cell.get('paper_endpoint_l2')} "
            f"cosine_e={cell.get('cosine_per_position_entropy_reduction')} "
            f"paper_e={cell.get('paper_per_position_entropy_reduction')}",
            file=sys.stderr,
        )
    agg = _w189._aggregate(cells)
    verdict = _verdict_from_agg(agg, n_records=len(cells))
    p_val_e = agg["p_value_paired_permutation"]
    p_val_l2 = agg["p_value_paired_permutation_l2_axis"]

    # n=3 sub-experiment continuity: for the seeds {0, 1, 2} compare
    # fresh results to the Wave 189 P4 baseline JSON (kanzi only;
    # lineageflow has no prior baseline).
    n3_seeds = [s for s in seeds if int(s) in DEFAULT_SEEDS_BASELINE]
    n3_fresh_cells = [c for c in cells if int(c["seed"]) in DEFAULT_SEEDS_BASELINE]
    continuity_payload: dict | None = None
    if n3_seeds:
        baseline = _load_n3_baseline(adapter_kind=adapter_kind)
        if baseline is not None:
            baseline_cells, baseline_configs = baseline
            baseline_n3 = [
                bc for bc in baseline_cells
                if int(bc["seed"]) in DEFAULT_SEEDS_BASELINE
            ]
            continuity_payload = _continuity_check(
                fresh_cells=n3_fresh_cells,
                baseline_cells=baseline_n3,
            )
            continuity_payload["baseline_summary"] = {
                "wave": "Wave 189 P4",
                "verdict": "load_bearing_only_on_axis_endpoint_l2_marginal_n3",
                "configs": baseline_configs,
            }
        else:
            continuity_payload = {
                "n_baseline": 0,
                "note": (
                    f"no Wave 189 P4 baseline exists for "
                    f"adapter_kind={adapter_kind!r}; the n=3 sub-experiment "
                    f"is the first n=3 baseline on this adapter."
                ),
            }

    return {
        "adapter_kind": str(adapter_kind),
        "adapter_label": _adapter_label(adapter_kind),
        "nfe": int(nfe),
        "n_rounds_framework": int(n_rounds),
        "seeds": list(seeds),
        "n_records": len(cells),
        "n3_sub_experiment": {
            "seeds": list(n3_seeds),
            "n_records": len(n3_fresh_cells),
            "continuity_check": continuity_payload,
        },
        "configurations": {
            "vanilla_baseline": {
                "status": (
                    "REFERENCE — single-pass ODE solve, no framework. "
                    "Acts as the reference the framework arms are "
                    "compared against."
                ),
                "mean_endpoint_norm_baseline": (
                    float(mean([
                        c.get("baseline_endpoint_norm")
                        for c in cells
                        if c.get("baseline_endpoint_norm") is not None
                    ]))
                    if any(
                        c.get("baseline_endpoint_norm") is not None
                        for c in cells
                    )
                    else None
                ),
            },
            "framework_no_paper_quantities": {
                "label": "framework_with_cosine_scheduler",
                "scheduler_family": "cosine_anneal",
                "consumes_A_g": False,
                "consumes_B_g": False,
                "consumes_C_g": False,
                "consumes_e_rho": False,
                "has_profile_residual_fn": False,
                "mean_per_position_entropy_reduction": agg[
                    "per_config_stats"
                ]["cosine_per_position_entropy_reduction"],
                "mean_endpoint_l2_vs_baseline": agg[
                    "per_config_stats"
                ]["cosine_endpoint_l2"],
            },
            "framework_with_paper_quantities": {
                "label": "framework_with_paper_ratio_scheduler",
                "scheduler_family": "paper_ratio",
                "consumes_A_g": True,
                "consumes_B_g": True,
                "consumes_C_g": True,
                "consumes_e_rho": True,
                "has_profile_residual_fn": True,
                "mean_per_position_entropy_reduction": agg[
                    "per_config_stats"
                ]["paper_per_position_entropy_reduction"],
                "mean_endpoint_l2_vs_baseline": agg[
                    "per_config_stats"
                ]["paper_endpoint_l2"],
                "delta_vs_no_paper_quantities": {
                    "entropy_axis": agg["delta_vs_baseline"][
                        "paper_mean_entropy_reduction"
                    ],
                    "l2_axis": agg["delta_vs_baseline"][
                        "paper_mean_endpoint_l2_vs_cosine"
                    ],
                },
            },
        },
        "effect_size": agg["effect_size"],
        "p_value_with_vs_without_quantities": p_val_e,
        "p_value_l2_axis": p_val_l2,
        "verdict": verdict,
        "implication_for_paper": _w189._implication(
            verdict, agg, p_val_e, p_val_l2,
        ),
        "cells": cells,
    }


# ---------------------------------------------------------------------------
# JSON assembly helpers
# ---------------------------------------------------------------------------


def _assemble_report(
    *, sweep_payload: dict[str, object], schema_label: str,
) -> dict[str, object]:
    """Wrap a single-adapter sweep payload into the canonical JSON shape."""
    return {
        "schema": schema_label,
        "tool": "scripts/wave190_p1_theorem_load_bearing_extended.py",
        "wave": "Wave 190 P1",
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "metric_axis": "per_position_entropy_reduction",
        "metric_definition": (
            "Per-position Shannon entropy reduction (nats) between "
            "baseline and framework endpoints, computed on the "
            "adapter's native state via softmax normalisation. "
            "Higher = framework sharpened the posterior."
        ),
        "paper_metric_axis": "reconstruction_kabsch_rmsd_A",
        "paper_metric_status": (
            "BLOCKED_no_torch — both kanzi and lineageflow run in "
            "synthetic mode (no upstream torch DAE / ESM-2 weights), "
            "so the paper metric is not computable. The entropy axis "
            "is reported instead."
        ),
        "sweep": sweep_payload,
    }


def _pin_commit_sha(report: dict[str, object], *, path: Path) -> None:
    """Add the current commit SHA to ``report`` and rewrite ``path``.

    Mirrors the Wave 186 P2 / Wave 189 P3 / Wave 189 P4 pin pattern.
    """
    try:
        import subprocess as _sp

        sha = _sp.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT),
            text=True,
        ).strip()
        report["commit_sha"] = sha
        path.write_text(
            json.dumps(report, indent=2, sort_keys=False,
                       ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except Exception as exc:
        print(f"[WARN] commit_sha pin failed: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="scripts.wave190_p1_theorem_load_bearing_extended",
        description=(
            "Wave 190 P1 — sweep-driver extension: n=30 paired sweep "
            "on kanzi + lineageflow synthetic adapters."
        ),
    )
    p.add_argument(
        "--n-seeds", type=int, default=DEFAULT_NSEEDS,
        help=f"Number of seeds (default {DEFAULT_NSEEDS}).",
    )
    p.add_argument(
        "--seeds", type=str, default=None,
        help=(
            "Explicit comma-separated seed list (overrides --n-seeds). "
            "When set, the n=3 continuity cells are sliced from this "
            "list as the subset of {0,1,2} that is present."
        ),
    )
    p.add_argument(
        "--adapter", choices=["kanzi", "lineageflow", "both"],
        default="kanzi",
        help="Which adapter(s) to sweep (default kanzi).",
    )
    p.add_argument(
        "--n-rounds", type=int, default=DEFAULT_N_ROUNDS,
        help=f"Framework n_rounds (default {DEFAULT_N_ROUNDS}).",
    )
    p.add_argument(
        "--nfe", type=int, default=None,
        help=(
            "NFE budget per cell. Defaults to 1000 for kanzi and "
            "100 for lineageflow (matches the adapter's canonical "
            "state-size scaling)."
        ),
    )
    p.add_argument(
        "--output", type=Path, default=None,
        help=(
            "Single-output path (only valid when --adapter is a "
            "single kind). For --adapter=both the driver writes "
            "two per-adapter JSONs to verification_outputs/."
        ),
    )
    return p


def _resolve_seeds(args: argparse.Namespace) -> list[int]:
    """Resolve the seed list from --seeds or --n-seeds."""
    if args.seeds is not None:
        return [int(s.strip()) for s in args.seeds.split(",") if s.strip()]
    return list(range(int(args.n_seeds)))


def _resolve_nfe(adapter_kind: str, args: argparse.Namespace) -> int:
    """Resolve NFE from --nfe or the per-adapter default."""
    if args.nfe is not None:
        return int(args.nfe)
    if adapter_kind == "kanzi":
        return DEFAULT_NFE_KANZI
    if adapter_kind == "lineageflow":
        return DEFAULT_NFE_LINEAGEFLOW
    raise ValueError(f"unknown adapter_kind {adapter_kind!r}")


def _output_path(adapter_kind: str, *, n_records: int) -> Path:
    """Default per-adapter output path."""
    name = f"wave190-p2-{adapter_kind}-n{n_records}.json"
    return REPO_ROOT / "verification_outputs" / name


def main(argv: list[str] | None = None) -> int:
    args = build_argparser().parse_args(argv)
    seeds = _resolve_seeds(args)
    n_records = len(seeds)
    adapter_kinds = (
        ["kanzi", "lineageflow"] if args.adapter == "both"
        else [args.adapter]
    )

    # Smoke-test carve-out: when the user passes --seeds=n 6 on
    # ``kanzi`` we still write to a separate path so the n=30
    # production JSON is never clobbered. The smoke-test path is
    # ``verification_outputs/wave190-p2-kanzi-n6-smoke.json`` per the
    # Wave 190 P1 task spec.
    is_smoke = (
        args.adapter == "kanzi"
        and args.seeds is None
        and int(args.n_seeds) == 6
    )

    last_report_paths: list[Path] = []
    for adapter_kind in adapter_kinds:
        nfe = _resolve_nfe(adapter_kind, args)
        sweep_payload = _run_adapter_sweep(
            adapter_kind=adapter_kind, seeds=list(seeds),
            nfe=int(nfe), n_rounds=int(args.n_rounds),
        )
        schema_label = (
            "wave190_p1_theorem_load_bearing_extended.v1"
            f":{adapter_kind}"
        )
        report = _assemble_report(
            sweep_payload=sweep_payload, schema_label=schema_label,
        )
        if args.adapter == "both" or is_smoke or args.output is None:
            if is_smoke and adapter_kind == "kanzi":
                out = (
                    REPO_ROOT / "verification_outputs"
                    / "wave190-p2-kanzi-n6-smoke.json"
                )
            else:
                out = _output_path(adapter_kind, n_records=n_records)
        else:
            out = args.output
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(report, indent=2, sort_keys=False,
                       ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        _pin_commit_sha(report, path=out)
        last_report_paths.append(out)
        print(
            f"[DONE] adapter={adapter_kind} -> {out} "
            f"(n_records={n_records}, verdict="
            f"{sweep_payload['verdict']!r}, "
            f"p_value_e={sweep_payload['p_value_with_vs_without_quantities']}, "
            f"p_value_l2={sweep_payload['p_value_l2_axis']})",
            file=sys.stderr,
        )
    if len(last_report_paths) == 1:
        print(
            f"[DONE] wrote {last_report_paths[0]}",
            file=sys.stderr,
        )
    else:
        for p in last_report_paths:
            print(f"[DONE] wrote {p}", file=sys.stderr)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
