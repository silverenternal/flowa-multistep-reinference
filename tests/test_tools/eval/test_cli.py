"""Tests for tools/eval/cli.py — argparse + CLI flag tests (--n-molecules, --kanzi-framework-paper-metrics).

Wave 104 P2-A: split from tests/test_tools/test_run_real_ckpt_eval.py
(2409 LOC → 6 sub-files mirroring tools/eval/). All 3 tests preserved
byte-for-byte: same imports, same fixtures, same assertions, same names.
"""

from __future__ import annotations

import importlib
import sys
from typing import Any

import pytest

_TOOLS = "tools.run_real_ckpt_eval"


def _import_tools_module() -> Any:
    """Import tools.run_real_ckpt_eval (lazy to avoid module-level side effects)."""
    # Ensure repo root is importable.
    import os
    repo_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", ".."),
    )
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    return importlib.import_module(_TOOLS)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_placeholder_trace(adapter: Any) -> Any:
    """Build a minimal ODE trace stub for the placeholder adapter.

    The FlowMol3 placeholder adapter's ``observe_entropy_reduction``
    synthetic-mode fallback only consumes ``trace.native_state_digest``
    (a sha256-like hex string). Any object with that attribute works.
    """
    class _TraceStub:
        native_state_digest = "wave53-flowmol3-metric-test-stub"
    return _TraceStub()



def test_run_real_ckpt_eval_n_molecules_flag() -> None:
    """``--n-molecules N`` is accepted by the CLI and threaded into ``_run_cell``.

    Locks in the Wave 74 F1 wire: the new ``--n-molecules`` CLI flag
    (default 1) must be parseable via ``build_argparser().parse_args``
    AND must thread through ``_run_cell`` (captured via the
    ``_solve_baseline`` capture point — same pattern as the Phase-4
    sampled-molecules test).

    The stub adapter inherits the v1 placeholder's
    ``build_initial_state`` / ``solve_ode`` surface and adds an
    ``export_sampled_molecules`` method. ``_solve_baseline`` and
    ``_solve_framework`` are stubbed to record the kwargs they
    receive.
    """
    tools = _import_tools_module()
    # 1. CLI flag must parse (default 1).
    args_default = tools.build_argparser().parse_args(
        ["--model", "flowmol3", "--seeds", "42", "--nfe-budgets", "10",
         "--output", "/tmp/_wave74_f1_default.json"],
    )
    assert int(args_default.n_molecules) == 1, (
        f"--n-molecules default must be 1, got "
        f"{int(args_default.n_molecules)!r}"
    )
    # 2. CLI flag must accept --n-molecules 4.
    args_explicit = tools.build_argparser().parse_args(
        ["--model", "flowmol3", "--seeds", "42", "--nfe-budgets", "10",
         "--output", "/tmp/_wave74_f1_explicit.json", "--n-molecules", "4"],
    )
    assert int(args_explicit.n_molecules) == 4
    # 3. Negative value rejected at argparse cast — argparse accepts
    # any int but the value-validation guard is in ``main()``, not
    # argparse. Verify the type is accepted by argparse and that the
    # value is preserved (the runtime guard runs in main()).
    args_zero = tools.build_argparser().parse_args(
        ["--model", "flowmol3", "--seeds", "42", "--nfe-budgets", "10",
         "--output", "/tmp/_wave74_f1_zero.json", "--n-molecules", "0"],
    )
    assert int(args_zero.n_molecules) == 0, (
        "argparse must preserve the raw value; runtime guard in main() "
        "rejects 0 with the 'must be >= 1' error"
    )
    # 4. _run_cell must thread n_molecules to _solve_baseline +
    # _solve_framework. Stub the inner chain so the test only exercises
    # the wire.
    from adaptive_reflow.adapters.flowmol3 import default_flowmol3_adapter

    adapter = default_flowmol3_adapter(force_mode="synthetic")
    # attach the new export method the v1 placeholder does NOT ship
    def _stub_export(self: Any, trace: Any) -> tuple[list[Any], dict[str, Any]]:
        return [object(), object()], {"marker": "ok", "sanitize_status": "ok"}

    adapter.export_sampled_molecules = _stub_export.__get__(  # type: ignore[method-assign]
        adapter, type(adapter),
    )
    captured_baseline: dict[str, Any] = {}
    captured_framework: dict[str, Any] = {}
    captured_compute: dict[str, Any] = {}

    original_resolve = tools._resolve_adapter
    original_solve_baseline = tools._solve_baseline
    original_solve_framework = tools._solve_framework
    original_compute_metric = tools._compute_metric
    original_compute_flowmol3 = tools._compute_flowmol3_composite

    def _stub_resolve(
        model: str, force_mode: str = "synthetic",
        restart_min_nfe: int | None = None,
        nfe_budget: int | None = None,
        n_molecules: int = 1,
    ) -> tuple[Any, str]:
        return adapter, "synthetic"

    def _stub_solve_baseline(*args: Any, **kwargs: Any) -> tuple[Any, float]:
        captured_baseline.update(kwargs)
        return _make_placeholder_trace(adapter), 0.0

    def _stub_solve_framework(*args: Any, **kwargs: Any) -> tuple[Any, float]:
        captured_framework.update(kwargs)
        return _make_placeholder_trace(adapter), 0.0

    def _stub_compute_metric(*args: Any, **kwargs: Any) -> tuple[Any, str, dict[str, Any]]:
        return 1.0, "synthetic_fallback", {"value": 1.0}

    def _capturing_compute(**kwargs: Any) -> tuple[float | None, str, dict[str, Any]]:
        captured_compute.update(kwargs)
        return 0.0, "computed", {"chemistry_input_source": "neutral_zero_stub"}

    tools._resolve_adapter = _stub_resolve  # type: ignore[assignment]
    tools._solve_baseline = _stub_solve_baseline  # type: ignore[assignment]
    tools._solve_framework = _stub_solve_framework  # type: ignore[assignment]
    tools._compute_metric = _stub_compute_metric  # type: ignore[assignment]
    tools._compute_flowmol3_composite = _capturing_compute  # type: ignore[assignment]
    try:
        cell = tools._run_cell(
            model="flowmol3",
            seed=42,
            nfe=10,
            n_rounds=3,
            force_mode="synthetic",
            metric_mode="synthetic",
            composite_metric="real",
            n_molecules=4,
        )
    finally:
        tools._resolve_adapter = original_resolve  # type: ignore[assignment]
        tools._solve_baseline = original_solve_baseline  # type: ignore[assignment]
        tools._solve_framework = original_solve_framework  # type: ignore[assignment]
        tools._compute_metric = original_compute_metric  # type: ignore[assignment]
        tools._compute_flowmol3_composite = original_compute_flowmol3  # type: ignore[assignment]
    # ``_solve_baseline`` MUST have received ``n_molecules=4``.
    assert int(captured_baseline.get("n_molecules", -1)) == 4, (
        f"_solve_baseline did NOT receive n_molecules=4; got "
        f"{int(captured_baseline.get('n_molecules', -1))!r}"
    )
    # ``_solve_framework`` MUST have received ``n_molecules=4``.
    assert int(captured_framework.get("n_molecules", -1)) == 4, (
        f"_solve_framework did NOT receive n_molecules=4; got "
        f"{int(captured_framework.get('n_molecules', -1))!r}"
    )
    # ``sampled_molecules`` must still flow into the composite call
    # (the Wave 70 wire is intact).
    assert captured_compute.get("sampled_molecules") is not None
    # And the cell dict carries composite_marker='computed'.
    assert cell.get("composite_marker") == "computed"



def test_kanzi_framework_paper_metrics_flag_defaults_to_false() -> None:
    """``--kanzi-framework-paper-metrics`` is OFF by default (byte-stable).

    Phase 3 wire: the new flag is opt-in (default ``False``). When
    absent, the legacy Wave 79 ``--kanzi-upstream-eval`` path is
    unchanged — no extra upstream_eval subprocess, no bridge import,
    no ckpt read. Asserting ``args.kanzi_framework_paper_metrics ==
    False`` preserves the byte-stable contract that downstream
    consumers (D.4 vector tests, Phase 4 sweeps) rely on.
    """
    tools = _import_tools_module()
    args = tools.build_argparser().parse_args(
        ["--model", "kanzi", "--seeds", "42", "--nfe-budgets", "10",
         "--output", "/tmp/_wave91p3_default.json"],
    )
    assert hasattr(args, "kanzi_framework_paper_metrics"), (
        "build_argparser() must accept --kanzi-framework-paper-metrics "
        "(Wave 91 Phase 3 retry). The Phase 4 sweep cannot invoke the "
        "framework-arm bridge without it."
    )
    assert args.kanzi_framework_paper_metrics is False, (
        f"--kanzi-framework-paper-metrics must default to False "
        f"(byte-stable Wave 79 wire), got "
        f"{args.kanzi_framework_paper_metrics!r}"
    )


def test_kanzi_framework_paper_metrics_flag_in_help() -> None:
    """``--kanzi-framework-paper-metrics`` is documented in ``--help``.

    The Phase 3 help text references the Wave 91 Phase 2 bridge
    (``tools/kanzi_latent_to_coord.py``) and the framework-arm
    intent so future agents can find the wire without reading the
    audit doc. Locks in the help-text contract: the flag MUST
    appear in the parser's option-action map AND carry the
    framework-arm / bridge / Wave 91 Phase 2 reference in its
    help text.

    We deliberately avoid ``parser.format_help()`` (which trips
    over pre-existing ``100%`` literals in ``--composite-metric``'s
    help text under Python 3.14's stricter formatter — see
    ``argparse._HelpAction`` workaround at ``run_real_ckpt_eval.py:158``).
    Instead we read the help text from the parser's action map
    directly, which is the same data that ``format_help()`` would
    surface minus the unrelated formatting failure.
    """
    tools = _import_tools_module()
    parser = tools.build_argparser()
    actions_by_option: dict[str, Any] = dict(parser._option_string_actions)
    assert "--kanzi-framework-paper-metrics" in actions_by_option, (
        "--kanzi-framework-paper-metrics MUST be registered in the "
        "parser's option-string-actions map so downstream consumers "
        f"can invoke it. Registered options: {sorted(actions_by_option)!r}"
    )
    action = actions_by_option["--kanzi-framework-paper-metrics"]
    help_text = action.help or ""
    # The help text references the Wave 91 Phase 2 bridge + the
    # framework-arm intent. Asserting these tokens keeps the help
    # text informative for downstream consumers.
    assert "kanzi_latent_to_coord" in help_text or "Wave 91 Phase 2" in help_text, (
        "--kanzi-framework-paper-metrics help text must reference the "
        "Wave 91 Phase 2 latent->coord bridge so downstream agents "
        "understand the wire intent.\n"
        f"help_text:\n{help_text}"
    )
    # Also confirm the help text mentions the framework-arm intent
    # so the user understands the wire target.
    assert "framework arm" in help_text.lower(), (
        "--kanzi-framework-paper-metrics help text must mention the "
        "framework-arm intent so downstream consumers know the wire "
        "target.\n"
        f"help_text:\n{help_text}"
    )


# ---------------------------------------------------------------------------
# 6. Wave 95 Phase 1.D — symmetric weights_path threading (E5)
# ---------------------------------------------------------------------------
#
# The Wave 73 Agent 3 fix threaded ``weights_path`` only into the
# flowmol3 / flowmol3_v2 factory dispatch (closes the Wave 50 Tier-3
# metric-axis blocker for FlowMol3). Wave 95 Phase 1.D extends the
# same wire to the kanzi / lineageflow / hidream_i1 SOTA factories so
# the per-cell framework-vs-baseline eval can exercise real
# checkpoints instead of the synthetic field for those three models
# too. Each new entry is gated by ``weights_path in sig_params``
# (mirror line 977) so pre-existing factories whose signature does
# NOT accept the kwarg keep their byte-stable call shape.



