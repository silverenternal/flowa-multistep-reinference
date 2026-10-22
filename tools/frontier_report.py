#!/usr/bin/env python3
"""GAP-84 — the (quality, NFE) frontier report.

Pre-registration: ``docs/audit/gap84-inference-frontier.md`` §0. This module
implements §0.4–§0.6 and nothing else.

Input — ``frontier_input_v1``::

    {
      "schema": "frontier_input_v1",
      "model": "mnist_fm",
      "cell": "R5c",
      "metric": {"name": "projection_fid", "direction": "lower_is_better"},
      "n_records": 1000,
      "grid": [3, 5, 10, 25, 50, 100, 200],
      "baseline":  {"3": {"value": 11.10, "units": [...]}, ...},
      "framework": {"3": {"value": 11.12, "units": [...]}, ...}
    }

``units`` is the aligned list of paired unit values (chunk / record / seed).
Omitting it is allowed but forces ``INCOMPLETE``: §0.4 will not invent a CI.

Sign convention: ``delta = framework − baseline`` and
``improvement = delta_rel × (+1 for lower-is-better, −1 for higher-is-better)``,
so a **positive improvement is always good**. §0.5 then reads the same way for
both metric directions.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

SCHEMA_IN = "frontier_input_v1"
SCHEMA_OUT = "frontier_report_v1"

DEFAULT_MARGIN = 0.01  # §0.5: 1 % relative, the repo's standing effect floor
DEFAULT_PLATEAU_TOL = 0.01  # §0.5
DEFAULT_N_RESAMPLES = 10_000
DEFAULT_BOOTSTRAP_SEED = 0
MIN_RUNGS = 5  # §0.2
QUOTABLE_N = 1000  # §0.3
SPEED_WIN_RATIO = 0.5  # §0.6

_DIRECTIONS = ("lower_is_better", "higher_is_better")


class FrontierInputError(ValueError):
    """The input does not satisfy §0.2–§0.4."""


def _as_rungs(arm: dict[str, Any], grid: list[int], name: str) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for key, payload in arm.items():
        try:
            rung = int(key)
        except (TypeError, ValueError) as exc:
            raise FrontierInputError(f"{name}: rung key {key!r} is not an integer") from exc
        if rung not in grid:
            raise FrontierInputError(f"{name}: rung {rung} is not on the declared grid")
        if not isinstance(payload, dict) or "value" not in payload:
            raise FrontierInputError(f"{name}[{rung}]: expected {{'value': float, 'units': [...]}}")
        units = payload.get("units")
        if units is not None:
            units = [float(u) for u in units]
            if not units:
                raise FrontierInputError(f"{name}[{rung}]: 'units' is empty")
        out[rung] = {"value": float(payload["value"]), "units": units}
    return out


def _paired_ci(
    base_units: list[float],
    fw_units: list[float],
    n_resamples: int,
    seed: int,
) -> tuple[float, float]:
    """Percentile bootstrap CI of the paired mean difference (§0.4)."""
    b = np.asarray(base_units, dtype=np.float64)
    f = np.asarray(fw_units, dtype=np.float64)
    diffs = f - b
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, diffs.size, size=(n_resamples, diffs.size))
    means = diffs[idx].mean(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(lo), float(hi)


def _plateau(rungs: list[dict[str, Any]], tol: float) -> dict[str, Any]:
    """§0.5: mean of the last two rungs, plus whether that is flat."""
    last, prev = rungs[-1], rungs[-2]
    value = 0.5 * (last["baseline"] + prev["baseline"])
    denom = abs(prev["baseline"])
    rel_change = abs(last["baseline"] - prev["baseline"]) / denom if denom else float("inf")
    return {
        "value": value,
        "rungs_used": [prev["nfe"], last["nfe"]],
        "rel_change": rel_change,
        "flat": bool(rel_change < tol),
    }


def _first_at_or_better(rungs: list[dict[str, Any]], key: str, target: float,
                        tol: float, direction: str) -> int | None:
    """Smallest NFE whose ``key`` value reaches ``target`` within ``tol``."""
    for r in rungs:
        v = r[key]
        if direction == "lower_is_better":
            if v <= target * (1.0 + tol):
                return int(r["nfe"])
        elif v >= target * (1.0 - tol):
            return int(r["nfe"])
    return None


def build_report(spec: dict[str, Any], *, margin: float = DEFAULT_MARGIN,
                 plateau_tol: float = DEFAULT_PLATEAU_TOL,
                 n_resamples: int = DEFAULT_N_RESAMPLES,
                 bootstrap_seed: int = DEFAULT_BOOTSTRAP_SEED) -> dict[str, Any]:
    if spec.get("schema") != SCHEMA_IN:
        raise FrontierInputError(f"expected schema {SCHEMA_IN!r}, got {spec.get('schema')!r}")

    metric = spec.get("metric") or {}
    direction = metric.get("direction")
    if direction not in _DIRECTIONS:
        raise FrontierInputError(f"metric.direction must be one of {_DIRECTIONS}")
    # §0.5: a positive ``improvement`` is always good, so the sign flips the
    # delta only for the lower-is-better metrics.
    sign = -1.0 if direction == "lower_is_better" else 1.0

    grid = [int(n) for n in spec.get("grid", [])]
    if not grid:
        raise FrontierInputError("grid is empty")
    if grid != sorted(grid) or len(set(grid)) != len(grid):
        raise FrontierInputError("grid must be strictly increasing")
    if len(grid) < 3:
        raise FrontierInputError("grid needs at least 3 rungs to have a slope")

    n_records = spec.get("n_records")
    if not isinstance(n_records, int) or n_records <= 0:
        raise FrontierInputError("n_records must be a positive integer")

    base = _as_rungs(spec.get("baseline") or {}, grid, "baseline")
    fw = _as_rungs(spec.get("framework") or {}, grid, "framework")

    caveats: list[str] = []
    rungs: list[dict[str, Any]] = []
    for nfe in grid:
        b, f = base.get(nfe), fw.get(nfe)
        if b is None or f is None:
            missing = "baseline" if b is None else "framework"
            caveats.append(f"rung {nfe}: missing on {missing} — not a skipped rung (§0.2)")
            rungs.append({"nfe": nfe, "baseline": None, "framework": None,
                          "delta": None, "improvement": None, "ci95": None,
                          "missing": missing, "n_units": 0})
            continue

        delta = f["value"] - b["value"]
        denom = abs(b["value"])
        delta_rel = delta / denom if denom else float("inf")

        ci: tuple[float, float] | None = None
        n_units = 0
        if b["units"] is not None and f["units"] is not None:
            if len(b["units"]) != len(f["units"]):
                caveats.append(
                    f"rung {nfe}: unit counts differ ({len(b['units'])} vs "
                    f"{len(f['units'])}) — pairing is not defined, CI withheld"
                )
            else:
                lo, hi = _paired_ci(b["units"], f["units"], n_resamples, bootstrap_seed)
                ci = (lo, hi)
                n_units = len(b["units"])
        else:
            caveats.append(f"rung {nfe}: no paired units — CI withheld (§0.4)")

        improvement = sign * delta_rel
        improvement_ci = None
        if ci is not None:
            a, b_ = sign * ci[0] / denom, sign * ci[1] / denom
            improvement_ci = (min(a, b_), max(a, b_))

        rungs.append({
            "nfe": nfe,
            "baseline": b["value"],
            "framework": f["value"],
            "delta": delta,
            "delta_rel": delta_rel,
            "improvement": improvement,
            "improvement_ci95": improvement_ci,
            "ci95": ci,
            "missing": None,
            "n_units": n_units,
        })

    complete = [r for r in rungs if r["missing"] is None]
    if len(grid) < MIN_RUNGS:
        caveats.append(f"grid has {len(grid)} rungs; §0.2 needs ≥ {MIN_RUNGS}")

    plateau = _plateau(complete, plateau_tol) if len(complete) >= 2 else None
    if plateau is not None and not plateau["flat"]:
        caveats.append(
            f"baseline has not plateaued: last two rungs differ by "
            f"{100 * plateau['rel_change']:.3f} % (tol {100 * plateau_tol:.1f} %) (§0.6)"
        )

    # §0.5 dominance, evaluated only where a CI exists. ``improvement`` is
    # positive-is-good, so "not worse than the margin" is a LOWER bound test.
    violations: list[int] = []
    gain_rungs: list[int] = []
    no_ci: list[int] = []
    for r in complete:
        ci = r["improvement_ci95"]
        if ci is None:
            no_ci.append(r["nfe"])
            continue
        if ci[0] < -margin:
            violations.append(r["nfe"])
        if ci[0] > 0.0:
            gain_rungs.append(r["nfe"])
    if no_ci:
        caveats.append(f"rungs without a CI: {no_ci} — cannot establish dominance (§0.6)")

    speed: dict[str, Any] = {"nfe_to_baseline_plateau": None, "baseline_plateau_nfe": None,
                             "ratio": None}
    if plateau is not None:
        base_nfe = _first_at_or_better(complete, "baseline", plateau["value"],
                                       plateau_tol, direction)
        fw_nfe = _first_at_or_better(complete, "framework", plateau["value"],
                                     plateau_tol, direction)
        speed["baseline_plateau_nfe"] = base_nfe
        speed["nfe_to_baseline_plateau"] = fw_nfe
        if base_nfe and fw_nfe:
            speed["ratio"] = fw_nfe / base_nfe

    # §0.6 verdict.
    if len(complete) < len(grid) or len(grid) < MIN_RUNGS or no_ci or plateau is None \
            or not plateau["flat"]:
        verdict = "INCOMPLETE"
    elif violations:
        verdict = "LOSS"
    elif gain_rungs or (speed["ratio"] is not None and speed["ratio"] <= SPEED_WIN_RATIO):
        verdict = "WIN"
    else:
        verdict = "TIE"

    quotable = n_records >= QUOTABLE_N
    if not quotable:
        caveats.append(
            f"N = {n_records} < {QUOTABLE_N}: SCREEN_ONLY, not quotable (§0.3)"
        )

    return {
        "schema": SCHEMA_OUT,
        "model": spec.get("model"),
        "cell": spec.get("cell"),
        "metric": metric,
        "direction": direction,
        "n_records": n_records,
        "grid": grid,
        "margin": margin,
        "plateau_tol": plateau_tol,
        "rungs": rungs,
        "baseline_plateau": plateau,
        "dominance": {
            "weak_dominance": not violations and not no_ci and len(complete) == len(grid),
            "violations": violations,
            "strict_gain_rungs": gain_rungs,
            "rungs_without_ci": no_ci,
        },
        "speed": speed,
        "verdict": verdict,
        "quotable": quotable,
        "win": bool(verdict == "WIN" and quotable),
        "caveats": caveats,
    }


def render_markdown(rep: dict[str, Any]) -> str:
    lines = [
        f"### {rep.get('model')} / {rep.get('cell')} — {rep['metric'].get('name')}",
        "",
        f"N = {rep['n_records']} · direction `{rep['direction']}` · "
        f"verdict **{rep['verdict']}** · quotable `{rep['quotable']}` · "
        f"win `{rep['win']}`",
        "",
        "| NFE | baseline | framework | Δ | Δ% | improvement CI95 | units |",
        "|---:|---:|---:|---:|---:|---|---:|",
    ]
    for r in rep["rungs"]:
        if r["missing"]:
            lines.append(f"| {r['nfe']} | — | — | — | — | missing on {r['missing']} | 0 |")
            continue
        ci = r["improvement_ci95"]
        ci_txt = "—" if ci is None else f"[{ci[0]:+.4f}, {ci[1]:+.4f}]"
        lines.append(
            f"| {r['nfe']} | {r['baseline']:.6g} | {r['framework']:.6g} | "
            f"{r['delta']:+.6g} | {100 * r['delta_rel']:+.3f}% | {ci_txt} | {r['n_units']} |"
        )
    p = rep["baseline_plateau"]
    if p:
        lines += ["", f"Baseline plateau {p['value']:.6g} over NFE {p['rungs_used']}, "
                      f"last-two relative change {100 * p['rel_change']:.3f} % "
                      f"({'flat' if p['flat'] else 'NOT flat'})."]
    s = rep["speed"]
    if s["ratio"] is not None:
        lines.append(f"Framework reaches the baseline plateau at NFE "
                     f"{s['nfe_to_baseline_plateau']} vs {s['baseline_plateau_nfe']} "
                     f"(ratio {s['ratio']:.2f}).")
    if rep["caveats"]:
        lines += ["", "Caveats:"] + [f"- {c}" for c in rep["caveats"]]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", type=Path, required=True, help="frontier_input_v1 JSON")
    ap.add_argument("--out", type=Path, default=None, help="write frontier_report_v1 JSON here")
    ap.add_argument("--margin", type=float, default=DEFAULT_MARGIN)
    ap.add_argument("--plateau-tol", type=float, default=DEFAULT_PLATEAU_TOL)
    ap.add_argument("--n-resamples", type=int, default=DEFAULT_N_RESAMPLES)
    ap.add_argument("--bootstrap-seed", type=int, default=DEFAULT_BOOTSTRAP_SEED)
    args = ap.parse_args(argv)

    spec = json.loads(args.input.read_text())
    try:
        rep = build_report(spec, margin=args.margin, plateau_tol=args.plateau_tol,
                           n_resamples=args.n_resamples,
                           bootstrap_seed=args.bootstrap_seed)
    except FrontierInputError as exc:
        print(f"frontier_input_error: {exc}", file=sys.stderr)
        return 2

    print(render_markdown(rep))
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(rep, indent=1) + "\n")
        print(f"\nwrote {args.out}", file=sys.stderr)
    return 0 if rep["verdict"] != "INCOMPLETE" else 3


if __name__ == "__main__":
    raise SystemExit(main())
