"""Shared fixtures for the Wave 14 C 36-uplift isolation suite.

This conftest only exposes helpers -- it does not collect fixtures for
specific uplifts. Each parametrization in ``test_uplifts.py`` builds
its own minimal scenario so a single helper change cannot cascade
across unrelated tests.

The most important helper is :func:`_load_eval_modules` which seeds
the ``adaptive_reflow.eval.*`` submodules directly into
``sys.modules``. This bypasses the ``rdkit`` import in
``adaptive_reflow.eval.__init__`` (rdkit is not installed in the
CPU-only sandbox) so the non-rdkit-using eval submodules can be
imported in isolation. See F-6 of the upstream investigation report.
"""

from __future__ import annotations

import importlib.util
import statistics
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Import bypass helpers
# ---------------------------------------------------------------------------


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_EVAL_DIR = _REPO_ROOT / "adaptive_reflow" / "eval"


def _load_eval_submodule(name: str) -> None:
    """Load ``adaptive_reflow.eval.<name>`` directly from its file.

    Bypasses ``adaptive_reflow/eval/__init__.py`` which eagerly imports
    ``rdkit``-dependent modules (mmff_conformer etc.). The four eval
    submodules required by the uplift isolation suite have no rdkit
    dependency and can be loaded individually.
    """
    full = f"adaptive_reflow.eval.{name}"
    if full in sys.modules:
        return
    file_path = _EVAL_DIR / f"{name}.py"
    if not file_path.exists():
        raise ImportError(f"Missing eval submodule file: {file_path}")
    spec = importlib.util.spec_from_file_location(full, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load spec for {full}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[full] = module
    spec.loader.exec_module(module)


def ensure_eval_modules_loaded() -> None:
    """Seed the four non-rdkit eval submodules used by this suite."""
    for name in (
        "posterior_selection_evaluator",
        "w2",
        "coverage",
        "lipschitz_diagnostic",
        "twodim_fm_evaluator",
    ):
        _load_eval_submodule(name)


# ---------------------------------------------------------------------------
# MC noise helper
# ---------------------------------------------------------------------------


def paired_difference_sigma(samples: list[float]) -> float:
    """Standard error of the mean of the paired differences.

    For seed-dependent rows the test collects ``M_on[s] - M_off[s]``
    over ``S`` seeds and uses ``sigma = std(diff) / sqrt(S)`` as the
    MC noise term paired against ``|mean(diff)|``. Paired (not
    independent) because both arms share the seed; this form is the
    tightest available.
    """
    if len(samples) < 2:
        return 0.0
    mean = sum(samples) / len(samples)
    variance = sum((s - mean) ** 2 for s in samples) / (len(samples) - 1)
    return (variance ** 0.5) / (len(samples) ** 0.5)


def std_over_seeds(values: list[float]) -> float:
    """Sample standard deviation (ddof=1) of a list of scalars."""
    if len(values) < 2:
        return 0.0
    return statistics.stdev(values)


# ---------------------------------------------------------------------------
# Profile helpers (paper-quantity uplifts U-017..U-024)
# ---------------------------------------------------------------------------


def profile_sin(x: float) -> float:
    """``g_a(x) = sin(x)`` canonical residual profile."""
    import math
    return math.sin(float(x))


def profile_polynomial(x: float) -> float:
    """``g_b(x) = x^2 - 1`` profile with two roots at +/-1."""
    return float(x) * float(x) - 1.0


def profile_tanh_sin(x: float) -> float:
    """``g_c(x) = (1 + 0.25 * tanh(x)) * sin(x)`` profile."""
    import math
    return (1.0 + 0.25 * math.tanh(float(x))) * math.sin(float(x))


# ---------------------------------------------------------------------------
# FinalRestartPolicy builder reused by U-006 (ScheduleDerivedPolicyDriver)
# and U-007 (AdaptivePolicyDriver). Both drivers consult a fully-formed
# FinalRestartPolicy -- a NoneType in any required field will throw.
# ---------------------------------------------------------------------------


def build_bench_base_policy(
    *,
    policy_id: str,
    schedule_sample,
    target_round: int,
    writer_id: str = "bench",
    run_id: str = "bench-run",
    channel_name: str = "xy",
):
    """Build a fully-hashed FinalRestartPolicy for driver benchmarking.

    Imports are deferred so this helper stays import-clean even when
    rdkit-free. The caller passes the schedule_sample already
    constructed (cosine for U-006; None for U-007).
    """
    from adaptive_reflow.contracts import (
        ArtifactHash,
        ChannelName,
        FactorValue,
        FinalRestartPolicy,
        LedgerRowId,
        MechanismId,
        PolicyId,
        RunId,
        hash_policy_hash,
    )

    ch = ChannelName(channel_name)
    placeholder = FinalRestartPolicy(
        policy_id=PolicyId(policy_id),
        writer_id=MechanismId(writer_id),
        run_id=RunId(run_id),
        target_round=int(target_round),
        outer_cycle_id=0,
        beta_by_channel={ch: FactorValue(0.0)},
        alpha_by_channel={ch: FactorValue(1.0)},
        fresh_noise_floor_by_channel={ch: FactorValue(0.0)},
        schedule_sample=schedule_sample,
        freeze_admission_by_channel={ch: True},
        ledger_row_id=LedgerRowId(f"bench-ledger-{policy_id}"),
        policy_hash=ArtifactHash(""),
        created_at_round=0,
        beta_from_schedule=True,
    )
    return replace(placeholder, policy_hash=hash_policy_hash(placeholder))


# ---------------------------------------------------------------------------
# Goldens for the smoke-only paper-quantity rows (U-017..U-024)
# ---------------------------------------------------------------------------


# Golden values pinned from docs/benchmark-uplifts.md (Section 1) at
# the precision of the documentation. The doc row values are rendered
# to 6 decimal places; the test asserts the actual value matches the
# golden to 1e-6 (six decimal places).
UPLIFT_GOLDENS: dict[str, float] = {
    "U-017": 0.854085,        # A_g_sin (6 d.p. from doc row 17)
    "U-018": 0.765289,        # A_g_polynomial (6 d.p. from doc row 18)
    "U-019": 1.16971,         # B_g_sin_K32 (5 d.p. from doc row 19)
    "U-021": 1.2,             # drift_robustness_over_C_g_ratio (3 s.f.)
    "U-022": 1e-4,            # e_rho_default (1e-4 from doc row 22)
}


# ---------------------------------------------------------------------------
# Re-export for the suite
# ---------------------------------------------------------------------------

__all__ = [
    "ensure_eval_modules_loaded",
    "paired_difference_sigma",
    "std_over_seeds",
    "profile_sin",
    "profile_polynomial",
    "profile_tanh_sin",
    "build_bench_base_policy",
    "UPLIFT_GOLDENS",
]
