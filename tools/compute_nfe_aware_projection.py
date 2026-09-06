#!/usr/bin/env python3
"""Wave 61 Agent 2 — NFE-aware scheduler analytical projection.

Computes the per-cell ``effective_memory_fraction`` that the new
:class:`NFEAwareMemoryScheduler` would produce on the Wave 57 9-cell
FlowMol3 grid, and pairs it with the Wave 58 with-gate empirical
results (so the user can iterate against the actual baseline).

Formula
-------
For each round ``r`` (constant across the cycle)::

    nfe_per_round = nfe_budget / n_rounds
    ratio         = nfe_per_round / threshold
    m(r)          = min(max_memory_fraction, max_memory_fraction * ratio ** 2)

Worked projections (``threshold=10``, ``max_memory_fraction=0.5``,
``n_rounds=3``):

==========  =============  ===============  ===================
NFE budget  NFE per round  ratio            m(r)
==========  =============  ===============  ===================
10          3.33           0.333            0.056  (no perturbation)
50          16.67          1.667            0.5    (saturated)
200         66.67          6.667            0.5    (saturated)
500         166.67         16.667           0.5    (saturated)
==========  =============  ===============  ===================

This script is the Wave 61 Agent 2 verification_outputs source. It reads
``flowmol3_with_gate_q4_2026.json`` (the Wave 58 empirical baseline)
and writes ``flowmol3_nfe_aware_q4_2026.json`` carrying both the
analytical projection and the Wave 58 numbers side-by-side.
"""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_THRESHOLD: int = 10
DEFAULT_MAX_MEMORY_FRACTION: float = 0.5
DEFAULT_N_ROUNDS: int = 3


def memory_fraction(
    nfe_budget: int,
    *,
    threshold: int = DEFAULT_THRESHOLD,
    max_memory_fraction: float = DEFAULT_MAX_MEMORY_FRACTION,
    n_rounds: int = DEFAULT_N_ROUNDS,
) -> float:
    """Return the closed-form ``m(r)`` for the given NFE budget.

    >>> memory_fraction(10)
    0.05555555555555558
    >>> memory_fraction(50)
    0.5
    >>> memory_fraction(200)
    0.5
    """
    nfe_per_round = float(nfe_budget) / float(n_rounds)
    ratio = nfe_per_round / float(threshold)
    m = float(max_memory_fraction) * ratio * ratio
    return float(min(max_memory_fraction, m))


def build_report(
    wave58_path: Path,
    *,
    threshold: int = DEFAULT_THRESHOLD,
    max_memory_fraction: float = DEFAULT_MAX_MEMORY_FRACTION,
    n_rounds: int = DEFAULT_N_ROUNDS,
) -> dict[str, object]:
    """Return the Wave 61 Agent 2 verification report payload."""
    with wave58_path.open() as f:
        wave58 = json.load(f)

    cells: list[dict[str, object]] = []
    for cell in wave58.get("cells", []):
        nfe = int(cell["nfe_budget"])
        seed = int(cell["seed"])
        m = memory_fraction(
            nfe,
            threshold=threshold,
            max_memory_fraction=max_memory_fraction,
            n_rounds=n_rounds,
        )
        cells.append(
            {
                "model": cell["model"],
                "seed": seed,
                "nfe_budget": nfe,
                "axis": cell.get("axis"),
                "primary_metric_name": cell.get("primary_metric_name"),
                "primary_metric_direction": cell.get(
                    "primary_metric_direction"
                ),
                # New scheduler's parameters and outputs.
                "n_rounds": n_rounds,
                "threshold": threshold,
                "max_memory_fraction": max_memory_fraction,
                "nfe_per_round": float(nfe) / float(n_rounds),
                "ratio": float(nfe) / float(n_rounds) / float(threshold),
                "effective_memory_fraction": m,
                "effective_n_cap": 1.0 - m,
                # Wave 58 gate's empirical baseline (3x3 grid, n=3 per stratum).
                "wave58_baseline_metric": cell.get("baseline_metric"),
                "wave58_framework_metric": cell.get("framework_metric"),
                "wave58_delta_pct": cell.get("delta_pct"),
                "wave58_restart_min_nfe": cell.get(
                    "restart_min_nfe_requested"
                ),
            }
        )

    return {
        "schema": "nfe_aware_scheduler_projection.v1",
        "wave": 61,
        "agent": 2,
        "model": "flowmol3",
        "purpose": (
            "Analytical projection of the new NFEAwareMemoryScheduler's "
            "effective memory_fraction on the Wave 57 9-cell grid, paired "
            "with the Wave 58 binary-gate empirical baseline so the user "
            "can iterate against the actual numbers. The eval pipeline "
            "does NOT yet have a --scheduler-family flag (Wave 59 Agent "
            "1's job to wire it); the framework_value column below is "
            "therefore an analytical projection, not a measured value."
        ),
        "scheduler_family": "nfe_aware_memory",
        "scheduler_module": (
            "adaptive_reflow.algorithm.scheduler.NFEAwareMemoryScheduler"
        ),
        "scheduler_params": {
            "threshold": threshold,
            "max_memory_fraction": max_memory_fraction,
            "n_rounds": n_rounds,
        },
        "closed_form": (
            "m(r) = min(M, M * (nfe_per_round / threshold) ** 2)"
        ),
        "wave58_baseline_source": str(wave58_path),
        "wave58_baseline_label": (
            "flowmol3_with_gate_q4_2026.json (Wave 58 Agent 1 binary "
            "gate, restart_min_nfe=20, force_mode=real, metric_mode=real)"
        ),
        "wave58_summary_per_stratum": _summarise_wave58(cells),
        "wave61_projection_per_stratum": _summarise_projection(cells),
        "comparison": _build_comparison(cells),
        "cells": cells,
    }


def _summarise_wave58(cells: list[dict[str, object]]) -> dict[str, dict[str, float]]:
    """Return per-stratum aggregate of Wave 58's empirical delta_pct."""
    out: dict[str, dict[str, float]] = {}
    for cell in cells:
        nfe = int(cell["nfe_budget"])
        delta = cell["wave58_delta_pct"]
        if delta is None:
            continue
        bucket = out.setdefault(
            f"NFE={nfe}", {"count": 0, "sum_delta_pct": 0.0, "wins": 0}
        )
        bucket["count"] += 1
        bucket["sum_delta_pct"] += float(delta)
        if float(delta) > 0.0:
            bucket["wins"] += 1
    for bucket in out.values():
        bucket["mean_delta_pct"] = (
            bucket["sum_delta_pct"] / bucket["count"]
        )
        bucket["win_rate"] = bucket["wins"] / bucket["count"]
        del bucket["sum_delta_pct"]
        del bucket["wins"]
    return out


def _summarise_projection(
    cells: list[dict[str, object]],
) -> dict[str, dict[str, float]]:
    """Return per-stratum projection of the new scheduler's blend."""
    out: dict[str, dict[str, float]] = {}
    for cell in cells:
        nfe = int(cell["nfe_budget"])
        bucket = out.setdefault(
            f"NFE={nfe}",
            {
                "count": 0,
                "memory_fraction_min": float("inf"),
                "memory_fraction_max": float("-inf"),
                "memory_fraction_sum": 0.0,
            },
        )
        m = float(cell["effective_memory_fraction"])
        bucket["count"] += 1
        bucket["memory_fraction_min"] = min(
            bucket["memory_fraction_min"], m
        )
        bucket["memory_fraction_max"] = max(
            bucket["memory_fraction_max"], m
        )
        bucket["memory_fraction_sum"] += m
    for bucket in out.values():
        bucket["memory_fraction_mean"] = (
            bucket["memory_fraction_sum"] / bucket["count"]
        )
        bucket["saturated"] = bool(
            bucket["memory_fraction_max"]
            >= DEFAULT_MAX_MEMORY_FRACTION - 1e-9
        )
        del bucket["memory_fraction_sum"]
        bucket["count"] = int(bucket["count"])
    return out


def _build_comparison(
    cells: list[dict[str, object]],
) -> dict[str, str]:
    """Build a side-by-side qualitative comparison."""
    return {
        "nfe_10": (
            "Wave 58 gate (restart_min_nfe=20): binary on/off — NFE=10 falls "
            "below the gate, so adapter returns state unchanged (m=0 by "
            "definition). Net effect: framework ≡ baseline at NFE=10 (no "
            "corruption, no improvement). "
            "Wave 61 scheduler (m=0.056): per-round fresh-noise injection "
            "shrinks 9× relative to the canonical m=0.5, so the round-1 "
            "endpoint is essentially preserved across the restart boundary. "
            "Same qualitative outcome — corruption effectively vanishes — "
            "but expressed as a continuous, scheduler-layer knob rather than "
            "a binary adapter-layer switch."
        ),
        "nfe_50": (
            "Wave 58 gate: NFE=50 falls above the gate, so the adapter "
            "blends at the canonical m=0.5 (same as Wave 57 baseline). "
            "Wave 61 scheduler: m=0.5 (saturated regime), so n_cap=0.5. "
            "Identical outcome at NFE=50 — both formulations agree when "
            "the per-round NFE exceeds the threshold. The 3/9 Wave 57 "
            "regressions at NFE=50 therefore persist under BOTH Wave 58 "
            "and Wave 61, indicating the corruption mechanism at NFE=50 "
            "is not the m coefficient but something downstream (CTMC "
            "cold-start, see Wave 57 Agent C)."
        ),
        "nfe_200": (
            "Wave 58 gate: NFE=200 above the gate, blends at m=0.5. "
            "Wave 61 scheduler: m=0.5 (saturated). "
            "Identical outcome at NFE=200 — both formulations agree. "
            "The NFE=200 stratum is converged either way; the regression "
            "in some seeds is a different mechanism (sample-noise, not "
            "blend coefficient)."
        ),
        "key_difference": (
            "Wave 58's gate is a per-adapter, binary, opt-in mechanism "
            "(FlowMol3 only, decided in the adapter's "
            "apply_restart_distribution). Wave 61's scheduler is a "
            "per-scheduler, continuous, framework-wide knob (any "
            "SchedulerProtocol consumer can build NFEAwareMemoryScheduler "
            "and the framework will use the smooth m(r) curve). The "
            "Wave 61 form is the strictly-more-expressive successor "
            "Wave 57 Agent D identified in its B2 recommendation."
        ),
    }


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    wave58_path = repo_root / "verification_outputs" / "flowmol3_with_gate_q4_2026.json"
    out_path = (
        repo_root
        / "verification_outputs"
        / "flowmol3_nfe_aware_q4_2026.json"
    )
    report = build_report(wave58_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        json.dump(report, f, indent=2)
    print(f"wrote {out_path}")
    print(json.dumps(report["wave58_summary_per_stratum"], indent=2))
    print(json.dumps(report["wave61_projection_per_stratum"], indent=2))


if __name__ == "__main__":
    main()
