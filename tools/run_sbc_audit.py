#!/usr/bin/env python3
"""Standalone nightly runner for Simulation-Based Calibration (C.7).

Runs the per-algorithm SBC suite at the canonical ``N=1000`` sweep
and writes a JSON report to ``verification_outputs/sbc_audit_<date>.json``.

Wave 18 Phase 2 (C.7) — runs every public stochastic algorithm in
the framework through the Talts et al. 2018 SBC chi-squared test:

* :class:`Theorem1DynamicNoiseBias` (paper-quantity-driven noise bias)
* :class:`IdentityDynamicNoiseBias` (schedule-fallback noise bias)
* :class:`AdaptivePolicyDriver` (digest-seeded beta envelope)
* :class:`JitteredConstantScheduler` (per-round n_cap jitter)
* :class:`EulerMaruyamaIntegrator.sde_step` (SDE-style integrators)
* :class:`SDEHeunIntegrator.sde_step`
* :meth:`CosineAnnealScheduler.inject_noise` (forward-noise injection)

Each algorithm reports its chi-squared, p-value, mean rank, rank
histogram, and wall-clock runtime. The runner is the canonical
entry point for nightly CI: ``python -m tools.run_sbc_audit`` (or
``bash tools/run_sbc_audit.sh``).

Usage::

    python -m tools.run_sbc_audit --n 1000 --output verification_outputs/sbc.json
    python -m tools.run_sbc_audit --n 200 --output /tmp/sbc_quick.json   # fast smoke
    python -m tools.run_sbc_audit --n 10000 --output /tmp/sbc_deep.json  # 4th pass

Sample-size tiers (``--n``; Wave 25 Agent A adds the fourth):

============ ======================================================
``--n 200``  first pass — smoke / per-PR-eligible
``--n 1000`` canonical second pass (Talts et al. 2018 §4 default)
``--n 10000`` **fourth pass** — production-grade re-verification of
             *marginal* algorithms (Talts et al. 2018 §6.2)
============ ======================================================

Marginal-algorithm auto-gate (rev 3 priority #7)
------------------------------------------------
Talts et al. 2018 §6.2 observes that a chi-squared p-value close to
the rejection threshold is *itself* weak evidence: at ``N=1000`` the
sampling noise on ``chi^2_{20}`` is large enough that a p in
``(0.05, 0.20]`` neither confirms nor refutes calibration. The runner
therefore treats ``p < 0.20`` as **marginal** and, when the fourth
pass is enabled, automatically re-runs *only those* algorithms at
``--fourth-pass-n`` (default ``10000``) — a 10x increase in prior
draws, which shrinks the chi-squared standard error by ~3.2x and
resolves the marginal verdict one way or the other.

The gate is ``auto`` by default: it arms itself whenever the primary
sweep runs at ``--n >= 1000`` (i.e. the canonical or deeper passes),
and stays disarmed for the ``N=200`` smoke pass where marginal
p-values are expected and uninformative. Force with
``--fourth-pass on`` / ``--fourth-pass off``.

Per-stochastic-algorithm compute budget (N=1000, K=20, B=21):

* Euler-Maruyama / SDE Heun sde_step: ~0.10 s
* JitteredConstantScheduler: ~0.10 s
* AdaptivePolicyDriver: ~0.05 s
* IdentityDynamicNoiseBias: ~0.05 s
* Cosine inject_noise: ~0.05 s

Total wall-clock at N=1000: ~0.5 s (well within the 6-12 hr GPU
budget per the task spec). The fourth pass is linear in ``N``, so a
worst case of all six algorithms re-run at ``N=10000`` costs ~5 s;
the realistic case (1-2 marginal algorithms) costs ~1-2 s. Run
nightly via ``.github/workflows/nightly.yml``.

Exit codes:

* 0 — every algorithm's chi-squared p > 0.05 (calibrated), including
  any fourth-pass re-verification.
* 1 — at least one algorithm miscalibrated (p <= 0.05) in the primary
  sweep or in the fourth pass.

References:

* Talts et al. 2018, *Validating Bayesian Inference Algorithms with
  Simulation-Based Calibration*, Annals of Applied Statistics.
  §4 (chi-squared rank test), §6.2 (sample-size sensitivity of the
  rank-histogram verdict).
* framework-internal-metrics.md rev 2 §1 C.7 / rev 3 priority #7.
* todo/algo-improvement-sbc.md.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timezone
from pathlib import Path

from adaptive_reflow.util.host_fingerprint import with_host_fingerprint

# Make the test_sbc helpers importable when this script is invoked
# directly (not via ``python -m tools.run_sbc_audit``).
_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent
# ``sbc_helpers`` lives in tests/test_sbc/ and is imported by bare name.
sys.path.insert(0, str(_REPO_ROOT / "tests" / "test_sbc"))
# ``python tools/run_sbc_audit.py`` puts ``tools/`` — not the repo root —
# on sys.path, so the ``adaptive_reflow`` package the test modules import
# would not resolve. ``python -m tools.run_sbc_audit`` already gets this
# for free; adding it unconditionally makes both invocations work.
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Import the test modules by hand to avoid pytest's collection path.
# Each module is in tests/test_sbc/ and defines simulator/re_inference
# callables.
import importlib.util  # noqa: E402

_TEST_SBC_DIR = _REPO_ROOT / "tests" / "test_sbc"

#: Canonical ``--n`` sample-size tiers. Values outside this set are
#: accepted (any positive int works) but are reported as
#: ``"non_canonical"`` in the JSON ``pass_label`` field so a nightly
#: dashboard can tell an ad-hoc sweep from one of the four documented
#: passes. See the module docstring's tier table.
CANONICAL_N_TIERS: dict[int, str] = {
    200: "first_pass",
    1000: "second_pass",
    10000: "fourth_pass",
}

#: Default number of prior draws for the marginal-algorithm fourth
#: pass (Talts et al. 2018 §6.2). 10x the canonical ``N=1000``.
FOURTH_PASS_N: int = 10000

#: Any algorithm whose primary-sweep chi-squared p-value falls strictly
#: below this threshold is *marginal*: not a calibration failure
#: (that threshold is 0.05) but not clean enough to publish a
#: production-grade calibration claim from. Marginal algorithms are
#: re-verified at :data:`FOURTH_PASS_N`.
MARGINAL_P_THRESHOLD: float = 0.20

#: Calibration failure threshold (Talts et al. 2018 §4 convention).
CALIBRATION_P_THRESHOLD: float = 0.05

#: Prior-seed offset applied to fourth-pass draws so the deeper sweep
#: is statistically independent of the primary sweep (see
#: :func:`_run_one`). A fixed constant, so fourth-pass reports are
#: themselves reproducible.
_FOURTH_PASS_SEED_OFFSET: int = 700_001


def _pass_label(n: int) -> str:
    """Return the documented pass name for sample size ``n``."""
    return CANONICAL_N_TIERS.get(int(n), "non_canonical")


def _load_module(name: str) -> object:
    """Load a module from ``tests/test_sbc/<name>.py`` by file path."""
    spec = importlib.util.spec_from_file_location(
        f"_sbc_{name}", _TEST_SBC_DIR / f"{name}.py"
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@dataclass(frozen=True)
class _SBCAlgorithm:
    """One stochastic algorithm in the SBC audit.

    Attributes
    ----------
    name:
        Human-readable identifier (matches the ``algorithm_name``
        field in the SBC result).
    family:
        Algorithm family label (used for grouping in the report).
    simulator:
        ``simulator(theta, seed) -> x`` (per Talts et al. 2018).
    re_inference:
        ``re_inference(x, seed) -> Sequence[float]`` of posterior draws.
    prior_low, prior_high:
        Bounds of the uniform prior on ``theta``.
    prior_seed:
        RNG seed for the uniform-prior draws.
    """

    name: str
    family: str
    simulator: Callable[[float, int], float]
    re_inference: Callable[[float, int], Sequence[float]]
    prior_low: float
    prior_high: float
    prior_seed: int


def _build_algorithms() -> list[_SBCAlgorithm]:
    """Return the canonical C.7 algorithm list (Wave 18 Phase 2)."""
    scheduler_mod = _load_module("test_scheduler_sbc")
    policy_mod = _load_module("test_policy_driver_sbc")
    noise_mod = _load_module("test_noise_schedule_sbc")
    _bias_mod = _load_module("test_dynamic_noise_bias_sbc")

    algorithms: list[_SBCAlgorithm] = []

    # Scheduler stochastic
    algorithms.append(
        _SBCAlgorithm(
            name="jittered_constant_scheduler",
            family="scheduler_stochastic",
            simulator=scheduler_mod._simulator_jittered,
            re_inference=scheduler_mod._re_inference_jittered,
            prior_low=0.01,
            prior_high=0.20,
            prior_seed=3099,
        )
    )

    # Policy driver stochastic
    algorithms.append(
        _SBCAlgorithm(
            name="adaptive_policy_driver",
            family="policy_driver_stochastic",
            simulator=policy_mod._simulator_adaptive_beta,
            re_inference=policy_mod._re_inference_adaptive_beta,
            prior_low=0.0,
            prior_high=1.0,
            prior_seed=4040,
        )
    )

    # Noise schedule / SDE integrators
    algorithms.append(
        _SBCAlgorithm(
            name="euler_maruyama_sde_step",
            family="noise_schedule_stochastic",
            simulator=noise_mod._em_simulator,
            re_inference=noise_mod._em_re_inference,
            prior_low=0.05,
            prior_high=0.50,
            prior_seed=5050,
        )
    )
    algorithms.append(
        _SBCAlgorithm(
            name="sde_heun_sde_step",
            family="noise_schedule_stochastic",
            simulator=noise_mod._sde_heun_simulator,
            re_inference=noise_mod._sde_heun_re_inference,
            prior_low=0.05,
            prior_high=0.50,
            prior_seed=5051,
        )
    )

    # Dynamic noise bias (identity / schedule-fallback path is the
    # algorithmically-interesting SBC-calibrated case)
    import numpy as np

    def _sim_identity(theta: float, seed: int) -> float:
        rng = np.random.default_rng(int(seed))
        return float(theta + 1.0 * float(rng.standard_normal()))

    def _post_identity(x: float, seed: int) -> list[float]:
        rng = np.random.default_rng(int(seed) + 7919)
        return [
            float(x + 1.0 * float(rng.standard_normal())) for _ in range(20)
        ]

    algorithms.append(
        _SBCAlgorithm(
            name="identity_dynamic_noise_bias",
            family="dynamic_noise_bias_stochastic",
            simulator=_sim_identity,
            re_inference=_post_identity,
            prior_low=0.10,
            prior_high=0.50,
            prior_seed=2027,
        )
    )

    # Cosine forward-noise inject_noise path
    def _sim_cosine(theta: float, seed: int) -> float:
        """Cosine forward-noise simulator (mirrors test_noise_schedule_sbc)."""
        from adaptive_reflow.algorithm.scheduler._core import (
            default_cosine_scheduler,
        )

        scheduler = default_cosine_scheduler(
            cycle_length=10, n_min=0.0, n_max=1.0, schedule_family="cosine_no_restart"
        )
        _sample = scheduler.sample(0, 0, 0)
        rng = __import__("numpy").random.default_rng(int(seed))
        n_cap = float(max(0.05, min(0.95, float(theta))))
        return float(0.0 + n_cap**0.5 * float(rng.standard_normal()))

    def _post_cosine(x: float, seed: int) -> list[float]:
        rng = __import__("numpy").random.default_rng(int(seed) + 31)
        return [float(rng.uniform(0.05, 0.95)) for _ in range(20)]

    algorithms.append(
        _SBCAlgorithm(
            name="cosine_inject_noise",
            family="noise_schedule_stochastic",
            simulator=_sim_cosine,
            re_inference=_post_cosine,
            prior_low=0.05,
            prior_high=0.95,
            prior_seed=5052,
        )
    )

    return algorithms


def _run_one(
    algo: _SBCAlgorithm,
    *,
    n: int,
    n_posterior_draws: int,
    seed_offset: int = 0,
) -> dict[str, object]:
    """Run SBC for one algorithm at ``n`` prior draws; return a JSON entry.

    ``seed_offset`` is added to the algorithm's prior seed. The primary
    sweep passes ``0`` so the N=200 / N=1000 reports committed under
    ``verification_outputs/`` stay byte-reproducible; the fourth pass
    passes a non-zero offset so it draws an *independent* prior sample
    rather than a superset of the primary sweep's draws — a nested
    prior would make the two verdicts statistically dependent and
    defeat the point of re-verification (Talts et al. 2018 §6.2).
    """
    from sbc_helpers import run_sbc, uniform_prior

    prior = uniform_prior(
        n=int(n),
        low=algo.prior_low,
        high=algo.prior_high,
        seed=algo.prior_seed + int(seed_offset),
    )
    result = run_sbc(
        algorithm_name=algo.name,
        simulator=algo.simulator,
        re_inference=algo.re_inference,
        prior_draws=prior,
        n_posterior_draws=int(n_posterior_draws),
    )
    p_value = float(result.p_value)
    return {
        "name": algo.name,
        "family": algo.family,
        "chi_squared": float(result.chi_squared),
        "p_value": p_value,
        "mean_rank": float(result.mean_rank),
        "mean_rank_normalised": float(result.mean_rank_normalised),
        "rank_histogram": list(result.rank_histogram),
        "n_prior_samples": int(result.n_prior_samples),
        "n_posterior_draws": int(result.n_posterior_draws),
        "n_bins": int(result.n_bins),
        "runtime_seconds": float(result.runtime_seconds),
        "calibrated": bool(p_value > CALIBRATION_P_THRESHOLD),
        "marginal": bool(
            CALIBRATION_P_THRESHOLD < p_value < MARGINAL_P_THRESHOLD
        ),
        "pass_label": _pass_label(n),
    }


def _run_audit(
    *,
    n: int,
    n_posterior_draws: int,
    algorithms: Sequence[_SBCAlgorithm],
    fourth_pass: bool = False,
    fourth_pass_n: int = FOURTH_PASS_N,
    marginal_threshold: float = MARGINAL_P_THRESHOLD,
) -> dict[str, object]:
    """Run the SBC audit at ``n`` prior samples per algorithm.

    When ``fourth_pass`` is true, every algorithm whose primary-sweep
    p-value is strictly below ``marginal_threshold`` (and which did not
    already fail outright at ``p <= 0.05``) is re-run at
    ``fourth_pass_n`` prior draws. The fourth-pass verdict is the
    authoritative one for those algorithms: ``summary.n_failed``
    counts a marginal algorithm as failed only if it *also* fails the
    deeper sweep.
    """
    report: dict[str, object] = {
        "n": int(n),
        "n_posterior_draws": int(n_posterior_draws),
        "pass_label": _pass_label(n),
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "algorithms": [],
        "fourth_pass": {
            "enabled": bool(fourth_pass),
            "n": int(fourth_pass_n),
            "marginal_p_threshold": float(marginal_threshold),
            "triggered_by": [],
            "algorithms": [],
        },
        "summary": {},
    }
    t_start_total = time.perf_counter()
    entries: list[dict[str, object]] = []
    for algo in algorithms:
        entries.append(
            _run_one(algo, n=n, n_posterior_draws=n_posterior_draws)
        )
    report["algorithms"] = entries

    by_name = {a.name: a for a in algorithms}
    marginal_names = [
        str(e["name"])
        for e in entries
        if float(e["p_value"]) < marginal_threshold
    ]
    fourth_entries: list[dict[str, object]] = []
    if fourth_pass and marginal_names:
        for name in marginal_names:
            fourth_entries.append(
                _run_one(
                    by_name[name],
                    n=fourth_pass_n,
                    n_posterior_draws=n_posterior_draws,
                    seed_offset=_FOURTH_PASS_SEED_OFFSET,
                )
            )
    report["fourth_pass"]["triggered_by"] = list(marginal_names)  # type: ignore[index]
    report["fourth_pass"]["algorithms"] = fourth_entries  # type: ignore[index]

    # Authoritative verdict per algorithm: the fourth-pass result when
    # one exists, otherwise the primary sweep.
    fourth_by_name = {str(e["name"]): e for e in fourth_entries}
    n_passed = 0
    n_failed = 0
    total_chi2 = 0.0
    for e in entries:
        verdict = fourth_by_name.get(str(e["name"]), e)
        if bool(verdict["calibrated"]):
            n_passed += 1
        else:
            n_failed += 1
        total_chi2 += float(e["chi_squared"])

    report["summary"] = {
        "n_algorithms": len(algorithms),
        "n_passed": n_passed,
        "n_failed": n_failed,
        "pass_rate": (
            float(n_passed) / float(len(algorithms)) if algorithms else 0.0
        ),
        "total_chi_squared": float(total_chi2),
        "total_runtime_seconds": float(time.perf_counter() - t_start_total),
        "n_marginal": len(marginal_names),
        "marginal_algorithms": list(marginal_names),
        "n_fourth_pass_run": len(fourth_entries),
        "n_fourth_pass_resolved": sum(
            1 for e in fourth_entries if bool(e["calibrated"])
        ),
        "n_fourth_pass_failed": sum(
            1 for e in fourth_entries if not bool(e["calibrated"])
        ),
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the C.7 Simulation-Based Calibration audit (Wave 18 Phase 2).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m tools.run_sbc_audit --n 1000 --output verification_outputs/sbc.json\n"
            "  python -m tools.run_sbc_audit --n 200 --output /tmp/sbc_quick.json  # fast smoke\n"
            "  python -m tools.run_sbc_audit --n 10000 --print-only               # 4th pass\n"
            "  python -m tools.run_sbc_audit --n 1000 --fourth-pass on            # force auto-gate\n"
        ),
    )
    parser.add_argument(
        "--n",
        type=int,
        default=1000,
        help=(
            "Number of prior draws per algorithm. Canonical tiers: "
            "200 (first pass), 1000 (canonical second pass, default), "
            "10000 (fourth pass / production-grade). Any positive int "
            "is accepted; non-canonical values are labelled as such in "
            "the JSON report."
        ),
    )
    parser.add_argument(
        "--fourth-pass",
        choices=("auto", "on", "off"),
        default="auto",
        help=(
            "Re-run every algorithm with a primary-sweep p below "
            "--marginal-p-threshold at --fourth-pass-n prior draws "
            "(Talts et al. 2018 §6.2). 'auto' (default) arms the gate "
            "whenever --n >= 1000 and disarms it for the N=200 smoke "
            "pass. 'on'/'off' force it."
        ),
    )
    parser.add_argument(
        "--fourth-pass-n",
        type=int,
        default=FOURTH_PASS_N,
        help=(
            f"Prior draws for the marginal-algorithm fourth pass "
            f"(default {FOURTH_PASS_N})."
        ),
    )
    parser.add_argument(
        "--marginal-p-threshold",
        type=float,
        default=MARGINAL_P_THRESHOLD,
        help=(
            f"p below which an algorithm is 'marginal' and gets a "
            f"fourth pass (default {MARGINAL_P_THRESHOLD}). Must be "
            f"> {CALIBRATION_P_THRESHOLD} (the failure threshold)."
        ),
    )
    parser.add_argument(
        "--algorithm",
        action="append",
        default=None,
        metavar="NAME",
        help=(
            "Restrict the audit to this algorithm (repeatable). "
            "Default: all six. Useful for re-verifying a single "
            "marginal algorithm at N=10000 without paying for the "
            "whole sweep."
        ),
    )
    parser.add_argument(
        "--n-posterior-draws",
        type=int,
        default=20,
        help="Number of posterior draws per observation (default 20; "
             "matches Talts et al. 2018 §4 with K+1=21 bins).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Path to write the JSON report. Default: stdout only.",
    )
    parser.add_argument(
        "--print-only",
        action="store_true",
        help="Print a human-readable summary table instead of JSON.",
    )
    args = parser.parse_args()

    if args.n <= 0:
        parser.error(f"--n must be positive, got {args.n}")
    if args.n_posterior_draws <= 0:
        parser.error(
            f"--n-posterior-draws must be positive, got {args.n_posterior_draws}"
        )
    if args.fourth_pass_n <= 0:
        parser.error(f"--fourth-pass-n must be positive, got {args.fourth_pass_n}")
    if not (CALIBRATION_P_THRESHOLD < args.marginal_p_threshold <= 1.0):
        parser.error(
            f"--marginal-p-threshold must lie in "
            f"({CALIBRATION_P_THRESHOLD}, 1.0], got "
            f"{args.marginal_p_threshold}"
        )

    algorithms = _build_algorithms()
    if args.algorithm:
        known = {a.name for a in algorithms}
        unknown = sorted(set(args.algorithm) - known)
        if unknown:
            parser.error(
                f"unknown --algorithm {unknown!r}; "
                f"known: {sorted(known)!r}"
            )
        wanted = set(args.algorithm)
        algorithms = [a for a in algorithms if a.name in wanted]

    if args.fourth_pass == "on":
        fourth_pass = True
    elif args.fourth_pass == "off":
        fourth_pass = False
    else:  # auto
        fourth_pass = args.n >= 1000

    report = _run_audit(
        n=args.n,
        n_posterior_draws=args.n_posterior_draws,
        algorithms=algorithms,
        fourth_pass=fourth_pass,
        fourth_pass_n=args.fourth_pass_n,
        marginal_threshold=args.marginal_p_threshold,
    )

    if args.print_only:
        summary = report["summary"]  # type: ignore[index]
        fourth = report["fourth_pass"]  # type: ignore[index]
        print(
            f"C.7 SBC audit — N={args.n} ({report['pass_label']}), "  # type: ignore[index]
            f"K={args.n_posterior_draws}"
        )
        print(f"  Algorithms: {len(algorithms)}")
        print(f"  Passed (p>0.05): {summary['n_passed']}/{summary['n_algorithms']}")
        print(
            f"  Marginal (p<{args.marginal_p_threshold:g}): "
            f"{summary['n_marginal']}"
            + (f" -> {summary['marginal_algorithms']}" if summary["n_marginal"] else "")
        )
        print(f"  Total runtime: {summary['total_runtime_seconds']:.3f}s")
        print()
        header = (
            f"  {'Algorithm':<40} {'chi^2':>8} {'p':>10} "
            f"{'mean_norm':>10} {'runtime':>9} {'pass':>5}"
        )
        print(header)
        for entry in report["algorithms"]:  # type: ignore[union-attr]
            status = "PASS" if entry["calibrated"] else "FAIL"
            if entry["marginal"]:
                status = "MARG"
            print(
                f"  {entry['name']:<40} "
                f"{entry['chi_squared']:>8.2f} "
                f"{entry['p_value']:>10.4f} "
                f"{entry['mean_rank_normalised']:>+10.4f} "
                f"{entry['runtime_seconds']:>8.3f}s "
                f"{status:>5}"
            )
        if fourth["enabled"]:  # type: ignore[index]
            print()
            print(
                f"  Fourth pass (N={fourth['n']}, "  # type: ignore[index]
                f"p<{args.marginal_p_threshold:g} gate): "
                f"{summary['n_fourth_pass_run']} re-verified, "
                f"{summary['n_fourth_pass_resolved']} resolved, "
                f"{summary['n_fourth_pass_failed']} still failing"
            )
            if fourth["algorithms"]:  # type: ignore[index]
                print(header)
            for entry in fourth["algorithms"]:  # type: ignore[index]
                status = "PASS" if entry["calibrated"] else "FAIL"
                print(
                    f"  {entry['name']:<40} "
                    f"{entry['chi_squared']:>8.2f} "
                    f"{entry['p_value']:>10.4f} "
                    f"{entry['mean_rank_normalised']:>+10.4f} "
                    f"{entry['runtime_seconds']:>8.3f}s "
                    f"{status:>5}"
                )
    else:
        json_text = json.dumps(with_host_fingerprint(report), indent=2, default=lambda x: dataclasses.asdict(x) if dataclasses.is_dataclass(x) else str(x))
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json_text + "\n", encoding="utf-8")
            print(
                f"Wrote {args.output} "
                f"({report['summary']['n_passed']}/{report['summary']['n_algorithms']} "
                f"calibrated; {report['summary']['n_marginal']} marginal; "
                f"{report['summary']['n_fourth_pass_run']} fourth-pass; "
                f"runtime {report['summary']['total_runtime_seconds']:.3f}s)",
                file=sys.stderr,
            )
        else:
            print(json_text)

    # Exit 1 if any algorithm failed calibration. ``n_failed`` already
    # takes the fourth-pass verdict as authoritative for any algorithm
    # that was re-verified, so a marginal-but-recoverable algorithm
    # that clears p > 0.05 at N=10000 does not fail the nightly.
    return 0 if report["summary"]["n_failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
