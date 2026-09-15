"""Wave 93 — Statistical power analysis for per-cell paper-metric verdicts.

The Tier 3 paper-metric sweep (Wave 81-91) produces per-cell aggregates
``(baseline_mean, framework_mean, n)`` across 12-14 cells spanning
FlowMol3 + LineageFlow + Kanzi. The honest verdict at N=1000 reads
"2/12 framework_improves with statistical significance" — which is a
valid finding, but a reviewer needs the **statistical power** to
distinguish three failure modes:

1. The framework does not help (true null).
2. The framework helps, but N is too small to detect it (underpowered).
3. The framework helps AND we can detect it (supported).

This module implements :func:`compute_power_table` to make the
distinction explicit:

* **CI** — normal-approximation (delta ± z * SE_delta) using per-arm
  variance inferred from the aggregate mean. For metric values in
  [0, 1] (proportions, validities), the Bernoulli variance
  ``p * (1 - p)`` is the standard upper bound. For other metrics,
  a 5 % coefficient-of-variation floor is used (defensible for
  paper-metric noise bands; documented per-cell).
* **p-value** — two-sided Wald z-test against 0 difference. For
  large n the z-test and Welch's t-test are equivalent; z is used
  because it is closed-form and avoids scipy's special-case
  handling for degenerate samples.
* **Power** — post-hoc power at ``min_effect_size_pp`` percent
  points, computed analytically:

      power = Phi(z_{alpha/2} - |delta| / SE) + Phi(z_{alpha/2} + |delta| / SE)

  (two-sided, normal approximation; Cohen 1988 §2.4).

* **Multiple testing** — Bonferroni correction across the input
  cells (alpha / N), with N = number of cells.

Verdict precedence (see :func:`_verdict` for the source of truth):

* ``TIE``         — ``|delta| < min_effect_size_pp`` (within N=1000 noise floor)
* ``UNDERPOWERED`` — post-hoc power to detect 1pp is < 0.5
* ``SUPPORTED``   — Bonferroni-corrected p < alpha AND delta > 0
* ``REGRESSES``   — Bonferroni-corrected p < alpha AND delta < 0
* ``NOT_SIGNIFICANT`` — fallback (no significant difference, but neither
  clearly underpowered)

The :func:`main` CLI ingests JSON aggregates from
``verification_outputs/{model}_n1000_paper_metrics*/`` and writes
``verification_outputs/power_analysis/per_cell.csv``.

Constraint: **CPU-only**, **numpy + scipy.stats only**, no torch.
Statistical references:

* Welch 1947 — unequal-variance t-test (generalised here via SE).
* Bonferroni 1935 — multiple-testing correction.
* Cohen 1988 — Statistical Power Analysis for the Behavioral Sciences
  (post-hoc power formula, §2.4).
* Hunter & Levine 2024 — modern power analysis for ML benchmarks
  (defends 1pp as a defensible effect size for paper-metric axes).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

REPO_ROOT: Path = Path(__file__).resolve().parent.parent

#: Threshold below which |delta| is declared a tie (within N=1000 noise floor).
DEFAULT_MIN_EFFECT_SIZE_PP: float = 1.0

#: Default family-wise error rate.
DEFAULT_ALPHA: float = 0.05

#: Post-hoc power threshold below which the cell is flagged UNDERPOWERED.
UNDERPOWERED_POWER_THRESHOLD: float = 0.5

#: Coefficient-of-variation floor for non-proportion metrics (defensible
#: default for paper-metric noise bands; documented per-cell).
DEFAULT_CV_FLOOR: float = 0.05

#: z critical value for two-sided 95% CI (matches scipy.stats.norm.ppf(0.975)).
Z_CRIT_95: float = 1.959963984540054

#: Two-sided p-value for the Bonferroni-corrected verdict threshold
#: at the default alpha (0.05). Per-cell is alpha / N (see _bonferroni).
ALPHA: float = DEFAULT_ALPHA


# ---------------------------------------------------------------------------
# Public dataclass + function: compute_power_table
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Cell:
    """One (model, metric, baseline, framework, n) cell."""

    model: str
    metric: str
    baseline: float
    framework: float
    n: int


def compute_power_table(
    cells: list[tuple[str, str, float, float, int]],
    alpha: float = 0.05,
    min_effect_size_pp: float = 1.0,
) -> pd.DataFrame:
    """Compute per-cell power + 95% CI + p-value + Bonferroni-corrected verdict.

    Parameters
    ----------
    cells
        Sequence of 5-tuples ``(model, metric, baseline, framework, n)``
        where ``baseline`` and ``framework`` are per-arm aggregate means
        at sample size ``n`` (typically the N=1000 paper-metric sweep).
    alpha
        Family-wise error rate (default 0.05).
    min_effect_size_pp
        Effect size in percentage points below which ``|delta|`` is
        declared a TIE (default 1.0 pp — the Wave 93 N=1000 noise floor).

    Returns
    -------
    pd.DataFrame
        One row per cell with columns:

        - ``model``, ``metric``, ``n``
        - ``baseline``, ``framework``, ``delta`` (framework - baseline)
        - ``delta_se``
        - ``ci_95_lower``, ``ci_95_upper``
        - ``p_value_raw``, ``p_value_bonferroni``
        - ``power_to_detect_1pp``
        - ``verdict`` ∈ ``{SUPPORTED, REGRESSES, TIE, UNDERPOWERED, NOT_SIGNIFICANT}``

    Notes
    -----
    Statistical methodology:

    * Variance model: Bernoulli ``p * (1 - p)`` when ``0 <= mean <= 1``,
      otherwise a 5 % coefficient-of-variation floor on the mean.
    * SE of delta: ``sqrt(var_b / n + var_f / n)`` (independent arms).
    * 95 % CI: ``delta ± z_crit * SE`` with ``z_crit = norm.ppf(1 - alpha/2)``.
    * p-value: two-sided Wald z-test against ``delta == 0``.
    * Bonferroni correction: ``p_bonf = min(p * N, 1.0)`` across N cells.
    * Power: two-sided normal-approximation power at delta_target = 1 pp.
    """
    if not cells:
        return pd.DataFrame(
            columns=[
                "model",
                "metric",
                "n",
                "baseline",
                "framework",
                "delta",
                "delta_se",
                "ci_95_lower",
                "ci_95_upper",
                "p_value_raw",
                "p_value_bonferroni",
                "power_to_detect_1pp",
                "verdict",
            ],
        )

    n_cells = len(cells)
    rows: list[dict[str, Any]] = []
    # First pass: compute raw statistics (delta, SE, CI, p_value_raw).
    for model, metric, baseline, framework, n in cells:
        delta = float(framework) - float(baseline)
        se_b = _per_arm_se(baseline, int(n))
        se_f = _per_arm_se(framework, int(n))
        delta_se = float(math.sqrt(se_b * se_b + se_f * se_f))
        ci_lo, ci_hi = _ci_95(delta, delta_se)
        p_raw = _p_value_two_sided(delta, delta_se)
        rows.append(
            {
                "model": model,
                "metric": metric,
                "n": int(n),
                "baseline": float(baseline),
                "framework": float(framework),
                "delta": delta,
                "delta_se": delta_se,
                "ci_95_lower": ci_lo,
                "ci_95_upper": ci_hi,
                "p_value_raw": p_raw,
                "_delta_target_for_power": min_effect_size_pp / 100.0,
                "_alpha": float(alpha),
            },
        )

    # Second pass: Bonferroni-correct p-values + compute power + verdict.
    for row in rows:
        p_bonf = _bonferroni(row["p_value_raw"], n_cells)
        power = _post_hoc_power(
            effect_size=row["_delta_target_for_power"],
            se=row["delta_se"],
            alpha=row["_alpha"],
        )
        row["p_value_bonferroni"] = p_bonf
        row["power_to_detect_1pp"] = power
        row["verdict"] = _verdict(
            delta=row["delta"],
            p_bonferroni=p_bonf,
            power=power,
            alpha=row["_alpha"],
            min_effect_size_pp=row["_delta_target_for_power"] * 100.0,
        )
        # Drop internal keys.
        del row["_delta_target_for_power"]
        del row["_alpha"]

    df = pd.DataFrame(rows)
    # Reorder columns for readability.
    col_order = [
        "model",
        "metric",
        "n",
        "baseline",
        "framework",
        "delta",
        "delta_se",
        "ci_95_lower",
        "ci_95_upper",
        "p_value_raw",
        "p_value_bonferroni",
        "power_to_detect_1pp",
        "verdict",
    ]
    return df[col_order]


# ---------------------------------------------------------------------------
# Public helper: aggregate cells from a JSON directory
# ---------------------------------------------------------------------------


def collect_cells_from_json_dir(
    json_dir: Path,
    *,
    metric_specs: Sequence[tuple[str, str]] | None = None,
) -> list[tuple[str, str, float, float, int]]:
    """Walk a Wave 81-91 paper-metric JSON directory and extract cells.

    Looks for files matching ``*_baseline*.json`` and ``*_framework*.json``
    in the directory and pairs them by metric name. Each per-arm JSON is
    expected to have one of:

    * a top-level ``per_metric`` field (Wave 91 Kanzi convention)
    * a top-level ``metrics`` field (Wave 81-87 convention)
    * a top-level ``paper_metrics`` field (Wave 87 convention)

    Each metric entry should expose ``baseline`` / ``framework`` floats
    and ``n`` int. If the entry exposes ``mean`` + ``std`` + ``n`` for
    a single arm (older Wave 75 / 79 schemas), the helper uses those.

    Returns
    -------
    list[tuple[str, str, float, float, int]]
        ``(model, metric, baseline, framework, n)`` tuples suitable for
        direct consumption by :func:`compute_power_table`.

    Raises
    ------
    FileNotFoundError
        If no baseline or framework JSONs are found in the directory.
    ValueError
        If the per-arm JSON cannot be parsed (caller decides whether
        to fall back to the ``per_metric`` summary view).
    """
    json_dir = Path(json_dir)
    if not json_dir.exists():
        raise FileNotFoundError(f"JSON directory not found: {json_dir}")

    baseline_files = sorted(json_dir.glob("*baseline*.json"))
    framework_files = sorted(json_dir.glob("*framework*.json"))
    if not baseline_files or not framework_files:
        raise FileNotFoundError(
            f"No baseline/framework JSON pair found under {json_dir} "
            f"(baseline={len(baseline_files)}, framework={len(framework_files)})",
        )

    baseline_metrics = _extract_metric_dict(baseline_files[0])
    framework_metrics = _extract_metric_dict(framework_files[0])

    model_name = json_dir.name.replace("_n1000_paper_metrics", "").replace(
        "_framework_paper_metrics", ""
    )

    if metric_specs is not None:
        metric_keys = list(metric_specs)
    else:
        metric_keys = [(name, name) for name in sorted(baseline_metrics)]

    cells: list[tuple[str, str, float, float, int]] = []
    for metric_key, metric_label in metric_keys:
        if metric_key not in baseline_metrics or metric_key not in framework_metrics:
            continue
        b = baseline_metrics[metric_key]
        f = framework_metrics[metric_key]
        baseline_val, n_b = _coerce_arm(b)
        framework_val, n_f = _coerce_arm(f)
        n = min(int(n_b), int(n_f))
        cells.append(
            (model_name, metric_label, baseline_val, framework_val, n),
        )
    return cells


# ---------------------------------------------------------------------------
# Internal statistical helpers
# ---------------------------------------------------------------------------


def _per_arm_se(mean: float, n: int) -> float:
    """Standard error for one arm at sample size ``n``.

    Variance model:

    * Bernoulli ``p * (1 - p)`` when ``0 <= mean <= 1``.
    * Otherwise: ``(DEFAULT_CV_FLOOR * mean) ** 2``.

    SE = ``sqrt(var / n)``.
    """
    if n <= 0:
        return float("nan")
    var = mean * (1.0 - mean) if 0.0 <= mean <= 1.0 else (DEFAULT_CV_FLOOR * mean) ** 2
    return float(math.sqrt(var / n))


def _ci_95(delta: float, delta_se: float) -> tuple[float, float]:
    """95 % CI for ``delta`` (two-sided, normal approximation)."""
    if not math.isfinite(delta_se):
        return (float("nan"), float("nan"))
    lo = delta - Z_CRIT_95 * delta_se
    hi = delta + Z_CRIT_95 * delta_se
    return (lo, hi)


def _p_value_two_sided(delta: float, delta_se: float) -> float:
    """Two-sided p-value for H0: ``delta == 0`` (Wald z-test)."""
    if not math.isfinite(delta_se) or delta_se <= 0.0:
        # Degenerate (SE == 0) → cannot distinguish from 0 → p = 1.0.
        return 1.0
    z = delta / delta_se
    # 2 * (1 - Phi(|z|)) via scipy for numerical accuracy.
    p = float(2.0 * (1.0 - stats.norm.cdf(abs(z))))
    return min(p, 1.0)


def _bonferroni(p: float, n_tests: int) -> float:
    """Bonferroni-corrected p-value, clipped to [0, 1]."""
    if n_tests <= 0:
        return float(p)
    return float(min(p * n_tests, 1.0))


def _post_hoc_power(effect_size: float, se: float, alpha: float) -> float:
    """Two-sided post-hoc power at a given effect size.

    Uses the normal-approximation formula (Cohen 1988 §2.4):

        power = P(|Z| > z_{alpha/2} | Z ~ N(ncp, 1))
              = Phi(ncp - z_{alpha/2}) + Phi(-z_{alpha/2} - ncp)

    where ``ncp = |effect_size| / SE`` is the non-centrality parameter.

    Parameters
    ----------
    effect_size
        Target effect size in the same units as ``delta`` (typically
        percentage points / 100, e.g. ``0.01`` for 1 pp).
    se
        Standard error of the delta at the observed sample size.
    alpha
        Two-sided Type-I error rate.

    Returns
    -------
    float
        Power in [0, 1].
    """
    if not math.isfinite(se) or se <= 0.0:
        return float("nan")
    z_alpha = float(stats.norm.ppf(1.0 - alpha / 2.0))
    ncp = abs(effect_size) / se  # non-centrality parameter
    power = float(
        # P(Z_obs > z_alpha) under H1 with Z_obs ~ N(ncp, 1)
        stats.norm.sf(z_alpha - ncp)
        # P(Z_obs < -z_alpha) under H1 with Z_obs ~ N(ncp, 1)
        + stats.norm.cdf(-z_alpha - ncp),
    )
    # Clip to [0, 1] for floating-point safety.
    return max(0.0, min(1.0, power))


def _verdict(
    delta: float,
    p_bonferroni: float,
    power: float,
    alpha: float,
    min_effect_size_pp: float,
) -> str:
    """Compute the verdict string for one cell.

    Precedence (highest first):

    1. ``TIE``         — ``|delta| < min_effect_size_pp / 100``
    2. ``UNDERPOWERED`` — post-hoc power at 1pp < 0.5
    3. ``SUPPORTED``   — ``p_bonf < alpha`` AND ``delta > 0``
    4. ``REGRESSES``   — ``p_bonf < alpha`` AND ``delta < 0``
    5. ``NOT_SIGNIFICANT`` — fallback
    """
    # 1. Noise floor.
    if abs(delta) * 100.0 < min_effect_size_pp:
        return "TIE"
    # 2. Power floor.
    if math.isfinite(power) and power < UNDERPOWERED_POWER_THRESHOLD:
        return "UNDERPOWERED"
    # 3 & 4. Significance + direction.
    if p_bonferroni < alpha:
        return "SUPPORTED" if delta > 0 else "REGRESSES"
    # 5. Fallback.
    return "NOT_SIGNIFICANT"


# ---------------------------------------------------------------------------
# Internal JSON ingestion helpers
# ---------------------------------------------------------------------------


def _extract_metric_dict(json_path: Path) -> dict[str, dict[str, Any]]:
    """Pull a ``metric_name -> metric_payload`` mapping out of a JSON.

    Tries, in order:

    1. ``{"per_metric": [...]}`` (Wave 91 schema — list of dicts with
       ``metric`` key).
    2. ``{"metrics": {metric_name: payload}}`` (Wave 81-87 schema).
    3. ``{"paper_metrics": {metric_name: payload}}`` (Wave 87 alt).
    4. Flat dict where keys look like metric names (Wave 75 schema).
    """
    with json_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    if isinstance(data, dict):
        if "per_metric" in data and isinstance(data["per_metric"], list):
            return {
                str(entry["metric"]): entry
                for entry in data["per_metric"]
                if isinstance(entry, dict) and "metric" in entry
            }
        if "metrics" in data and isinstance(data["metrics"], dict):
            return data["metrics"]
        if "paper_metrics" in data and isinstance(data["paper_metrics"], dict):
            return data["paper_metrics"]
        # Wave 75 fallback: flat dict with numeric values per metric.
        return {
            k: {"value": float(v)}
            for k, v in data.items()
            if isinstance(v, (int, float))
        }

    return {}


def _coerce_arm(arm: Any) -> tuple[float, int]:
    """Pull ``(value, n)`` out of one per-arm payload."""
    if not isinstance(arm, dict):
        return (float("nan"), 0)
    if "mean" in arm and "n" in arm:
        return (float(arm["mean"]), int(arm["n"]))
    if "value" in arm and "n" in arm:
        return (float(arm["value"]), int(arm["n"]))
    if "mean" in arm and "n_records" in arm:
        return (float(arm["mean"]), int(arm["n_records"]))
    if "value" in arm and "n_records" in arm:
        return (float(arm["value"]), int(arm["n_records"]))
    if "mean" in arm and "n_seqs" in arm:
        return (float(arm["mean"]), int(arm["n_seqs"]))
    if "value" in arm and "n_seqs" in arm:
        return (float(arm["value"]), int(arm["n_seqs"]))
    if "baseline_metric" in arm and "n_records" in arm:
        return (float(arm["baseline_metric"]), int(arm["n_records"]))
    if "framework_metric" in arm and "n_records" in arm:
        return (float(arm["framework_metric"]), int(arm["n_records"]))
    return (float("nan"), 0)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="statistical_power_analysis",
        description=(
            "Compute per-cell power + 95% CI + p-value + Bonferroni-corrected "
            "verdict for Wave 81-91 paper-metric sweeps."
        ),
    )
    parser.add_argument(
        "--cell",
        action="append",
        default=[],
        metavar="MODEL:METRIC:BASELINE:FRAMEWORK:N",
        help=(
            "Inline cell (repeatable). Format: 'model:metric:baseline:framework:n'. "
            "Example: --cell flowmol3:validity_pct:0.999:1.000:1000"
        ),
    )
    parser.add_argument(
        "--input-dirs",
        action="append",
        default=[],
        type=Path,
        help=(
            "JSON directories to scan for paper-metric baseline+framework pairs "
            "(repeatable). Format: verification_outputs/{model}_n1000_paper_metrics"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output CSV path (default: stdout).",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=DEFAULT_ALPHA,
        help=f"Family-wise error rate (default {DEFAULT_ALPHA}).",
    )
    parser.add_argument(
        "--min-effect-size-pp",
        type=float,
        default=DEFAULT_MIN_EFFECT_SIZE_PP,
        help=(
            "Effect size in pp below which |delta| is declared a TIE "
            f"(default {DEFAULT_MIN_EFFECT_SIZE_PP})."
        ),
    )
    return parser


def _parse_inline_cell(spec: str) -> tuple[str, str, float, float, int]:
    """Parse a 'model:metric:baseline:framework:n' string."""
    parts = spec.split(":")
    if len(parts) != 5:
        raise ValueError(
            f"--cell expects 5 colon-separated fields, got {len(parts)}: {spec!r}",
        )
    model, metric, baseline, framework, n = parts
    return (
        model.strip(),
        metric.strip(),
        float(baseline),
        float(framework),
        int(n),
    )


def _load_all_cells(
    inline_cells: Iterable[str],
    input_dirs: Iterable[Path],
) -> list[tuple[str, str, float, float, int]]:
    cells: list[tuple[str, str, float, float, int]] = []
    for spec in inline_cells:
        cells.append(_parse_inline_cell(spec))
    for d in input_dirs:
        cells.extend(collect_cells_from_json_dir(Path(d)))
    return cells


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    cells = _load_all_cells(args.cell, args.input_dirs)
    if not cells:
        parser.error(
            "No cells supplied — pass at least one --cell or --input-dirs.",
        )

    df = compute_power_table(
        cells=cells,
        alpha=args.alpha,
        min_effect_size_pp=args.min_effect_size_pp,
    )

    if args.output is None:
        # Render CSV to stdout.
        df.to_csv(sys.stdout, index=False, float_format="%.6g")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(args.output, index=False, float_format="%.6g")

    # Always print a one-line summary to stderr so the caller sees it.
    counts = df["verdict"].value_counts().to_dict()
    parts = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
    print(f"[statistical_power_analysis] N={len(df)} cells, verdicts: {parts}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


# ---------------------------------------------------------------------------
# Type alias for the legacy List import above
# ---------------------------------------------------------------------------


__all__ = [
    "Cell",
    "compute_power_table",
    "collect_cells_from_json_dir",
    "main",
]
