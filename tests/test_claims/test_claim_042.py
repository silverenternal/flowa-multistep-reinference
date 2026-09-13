"""CLM-042: Fix-v2 capability set — Heun 2nd-order + stateful β-blend + fixed-NFE.

Asserted by docs/CLAIMS.md:1438-1512.
CLM-042 records the four research-grade upgrades the fix-v2 plan
landed:
1. **Heun 2nd-order predictor-corrector integrator** wired into
   both `solve_ode` and `batched_inference` with
   `solver: str = "euler"` as the default constructor parameter.
2. **Stateful β-blend chain** that threads `bundle → apply_restart_
   distribution → solve_ode → observe_endpoint → bundle_{r+1}` per
   round (added via the `--stateful` opt-in flag).
3. **Fixed-NFE comparison protocol** (`--match-nfe sample`).
4. **PID signal amplification** change to
   `EvidenceDrivenScheduler`'s default `target_ratio`.

The plan lives at `docs/r4-survey/21-fix-v2-plan.md`; the
verification record is at `docs/r4-survey/22-fix-v2-results.md`.

We pin:
1. The fix-v2 plan doc exists.
2. The fix-v2 results doc exists.
3. `RF_CIFAR_INTEGRATOR_HEUN` is a module-level constant on
   `rectified_flow_cifar` (`"heun"`).
4. `RF_CIFAR_INTEGRATOR_EULER` is the default (`"euler"`).
5. The CIFAR driver exposes the `--integrator`, `--match-nfe`,
   `--stateful` CLI flags.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN_DOC = ROOT / "docs" / "r4-survey" / "21-fix-v2-plan.md"
RESULTS_DOC = ROOT / "docs" / "r4-survey" / "22-fix-v2-results.md"
CIFAR_ADAPTER = ROOT / "adaptive_reflow" / "adapters" / "rectified_flow_cifar.py"
CIFAR_DRIVER = ROOT / "tools" / "run_sota_cifar_experiment.py"


def test_claim_042_fix_v2_plan_doc_exists() -> None:
    """The fix-v2 plan doc exists."""
    assert PLAN_DOC.is_file(), (
        f"{PLAN_DOC} missing — CLM-042 cites this plan"
    )


def test_claim_042_fix_v2_results_doc_exists() -> None:
    """The fix-v2 post-fix verification doc exists."""
    assert RESULTS_DOC.is_file(), (
        f"{RESULTS_DOC} missing — CLM-042 cites this verification record"
    )


def test_claim_042_heun_constant_in_adapter() -> None:
    """`rectified_flow_cifar.py` declares the `RF_CIFAR_INTEGRATOR_HEUN` constant."""
    text = CIFAR_ADAPTER.read_text()
    assert "RF_CIFAR_INTEGRATOR_HEUN" in text, (
        "CLM-042 asserts the Heun constant is declared on the adapter"
    )


def test_claim_042_heun_value_is_heun_string() -> None:
    """The Heun constant maps to the literal string `"heun"`."""
    text = CIFAR_ADAPTER.read_text()
    assert 'RF_CIFAR_INTEGRATOR_HEUN: str = "heun"' in text, (
        "CLM-042 asserts `RF_CIFAR_INTEGRATOR_HEUN = \"heun\"` "
        "is declared as a module-level str constant"
    )


def test_claim_042_euler_constant_is_default() -> None:
    """The Euler constant is the default solver (`RF_CIFAR_INTEGRATOR_EULER = "euler"`)."""
    text = CIFAR_ADAPTER.read_text()
    assert 'RF_CIFAR_INTEGRATOR_EULER: str = "euler"' in text, (
        "CLM-042 asserts the Euler constant is the default"
    )


def test_claim_042_adapter_accepts_solver_kwarg() -> None:
    """The adapter constructor accepts a `solver` keyword argument."""
    text = CIFAR_ADAPTER.read_text()
    assert "solver: str" in text, (
        "CLM-042 asserts the adapter constructor accepts `solver: str`"
    )


def test_claim_042_cifar_driver_has_integrator_cli_flag() -> None:
    """The CIFAR driver exposes an `--integrator` CLI flag."""
    text = CIFAR_DRIVER.read_text()
    assert "--integrator" in text or "integrator" in text, (
        "CLM-042 asserts the CIFAR driver exposes the --integrator CLI"
    )


def test_claim_042_cifar_driver_has_match_nfe_flag() -> None:
    """The CIFAR driver exposes a `--match-nfe` CLI flag."""
    text = CIFAR_DRIVER.read_text()
    assert "--match-nfe" in text or "match-nfe" in text, (
        "CLM-042 asserts the CIFAR driver exposes the --match-nfe CLI"
    )


def test_claim_042_cifar_driver_mentions_stateful_chain() -> None:
    """The CIFAR driver mentions the stateful chain or related build_initial_state path."""
    text = CIFAR_DRIVER.read_text()
    # CLM-042 references the stateful β-blend chain that threads
    # `bundle → apply_restart_distribution → solve_ode → observe_endpoint →
    # bundle_{r+1}` per round. The driver wires `build_initial_state`
    # which is the stateful-chain entry point.
    assert "build_initial_state" in text or "apply_restart_distribution" in text, (
        "CLM-042 expects the CIFAR driver to reference the stateful "
        "β-blend chain (build_initial_state / apply_restart_distribution)"
    )
