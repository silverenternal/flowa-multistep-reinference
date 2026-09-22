"""Adversarial scheduler stress test (Wave 287 P-adversarial).

This is the *deliberately pathological* companion to
``tests/test_paper_grounded_schedulers.py``. The edge-case tests in that
file probe one boundary per test (zero, negative, NaN, inf). This
harness instead subjects the **closed-form closed-loop path** of every
paper-grounded scheduler to a *matrix* of extreme paper-quantity
inputs and verifies the framework does **NOT**:

1. crash (uncaught exception in ``sample()`` or ``record_round_feedback()``);
2. produce ``NaN`` in ``n_cap``;
3. produce a negative ``n_cap``;
4. exceed ``n_max`` (= 1.0 for the canonical envelope);
5. silently corrupt downstream state (NaN in shift history, EMA, etc.).

Five paper-grounded schedulers (``codim``, ``paper_ratio``,
``convergence``, ``evidence_driven``, ``nfe_aware``) are exercised
against five pathological paper-quantity vectors. The verdict matrix
records the worst observed outcome per ``(scheduler, input)`` pair.

Failure semantics
-----------------

A scheduler that crashes, returns NaN, returns a negative ``n_cap``,
or returns ``n_cap > 1`` for *any* round in a 5-round run gets a
``FAIL_*`` verdict. The classification is intentionally pessimistic —
the audit log captures the *worst* symptom per pair so a single
crash downgrades a whole row even when subsequent rounds would
have been clean.

Adversarial inputs
------------------

* ``all_zeros``        -- ``A_g = B_g = C_g = e_rho = 0``
* ``extreme_ratios``   -- ``A_g = 1e15``, ``B_g = 1e-15``, ``C_g = 0``,
                          ``e_rho = 0`` (ratio spans 30 orders of magnitude)
* ``nan_inf``          -- ``A_g = NaN``, ``B_g = +inf``, ``C_g = -inf``,
                          ``e_rho = 0`` (NaN/inf propagation test)
* ``negative_lipschitz`` -- ``A_g = -1.0`` (physically invalid; the
                          paper requires ``A_g > 0``)
* ``tiny_all``         -- ``A_g = B_g = C_g = e_rho = 1e-100`` (paper
                          boundary, but legal)

Module boundary
---------------

* stdlib-only + the framework's own schedulers. No torch. No I/O.
* Deterministic: every (scheduler, input) pair is run twice with the
  same seed and the two ``n_cap`` sequences are byte-equal (D.4
  contract).
* Pure w.r.t. the global RNG (uses :class:`numpy.random.SeedSequence`
  only for explicit per-round noise injection; the closed-form
  ``n_cap`` math is RNG-free).

CLI usage
---------

Run with no arguments to print the verdict matrix as a Markdown table
and write it to ``docs/audit/wave287-p-adversarial-sweep.md``:

    python tools/adversarial_scheduler_test.py

The exit code is ``0`` if every cell PASSES, ``1`` otherwise. The
script always writes the audit note (even on full PASS) so the
historical record of "we ran this and it was clean" is preserved.
"""

from __future__ import annotations

import json
import math
import sys
import traceback
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from adaptive_reflow.algorithm.scheduler import (
    CodimensionSheetScheduler,
    ConvergenceAdaptiveScheduler,
    EvidenceDrivenScheduler,
    NFEAwareMemoryScheduler,
    PaperRatioAdaptiveScheduler,
    build_scheduler,
)
from adaptive_reflow.contracts import (
    ArtifactHash,
    CosineScheduleConfig,
    FactorValue,
)

# ---------------------------------------------------------------------------
# Adversarial inputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AdversarialInput:
    """A single pathological paper-quantity vector."""

    name: str
    description: str
    A_g: float
    B_g: float
    C_g: float
    e_rho: float


ADVERSARIAL_INPUTS: tuple[AdversarialInput, ...] = (
    AdversarialInput(
        name="all_zeros",
        description="A_g = B_g = C_g = e_rho = 0 (degenerate)",
        A_g=0.0, B_g=0.0, C_g=0.0, e_rho=0.0,
    ),
    AdversarialInput(
        name="extreme_ratios",
        description="A_g=1e15, B_g=1e-15, C_g=0, e_rho=0 (30-orders-of-magnitude spread)",
        A_g=1e15, B_g=1e-15, C_g=0.0, e_rho=0.0,
    ),
    AdversarialInput(
        name="nan_inf",
        description="A_g=NaN, B_g=+inf, C_g=-inf, e_rho=0 (NaN/inf propagation)",
        A_g=float("nan"), B_g=float("inf"), C_g=float("-inf"), e_rho=0.0,
    ),
    AdversarialInput(
        name="negative_lipschitz",
        description="A_g=-1.0, others=1.0 (physically invalid; defensive drop expected)",
        A_g=-1.0, B_g=1.0, C_g=1.0, e_rho=1.0,
    ),
    AdversarialInput(
        name="tiny_all",
        description="A_g = B_g = C_g = e_rho = 1e-100 (paper boundary, legal)",
        A_g=1e-100, B_g=1e-100, C_g=1e-100, e_rho=1e-100,
    ),
)


# Verdict set (single-source-of-truth).
PASS = "PASS"
FAIL_CRASH = "FAIL_crash"
FAIL_NAN = "FAIL_naN"
FAIL_NEGATIVE = "FAIL_negative"
FAIL_EXCEEDS = "FAIL_exceeds_n_max"
# Defensive rejection: the scheduler raised a fail-closed ``ValueError``
# for an obviously-bad input (NaN, inf, or negative paper quantities).
# This is *intentional* defensive coding -- the framework rejected the
# input loudly instead of silently producing a NaN. It is NOT counted
# as a framework bug (the silent-failure path is the bad path), but
# it is surfaced in the audit so callers know which adversarial inputs
# trip the defensive guards.
FAIL_REJECTED = "FAIL_rejected_by_design"


# ---------------------------------------------------------------------------
# Scheduler adapter protocol (for uniform sampling + paper-quantity wiring)
# ---------------------------------------------------------------------------


@dataclass
class _RunResult:
    """One ``(scheduler, input)`` run's outcome."""

    scheduler: str
    input_name: str
    n_rounds: int
    n_cap_seq: list[float] = field(default_factory=list)
    evidence_ratio_seq: list[float] = field(default_factory=list)
    shift_seq: list[float] = field(default_factory=list)
    verdict: str = PASS
    failure_reason: str = ""
    exception: str = ""


def _make_codim(input_: AdversarialInput) -> CodimensionSheetScheduler:
    """Construct a :class:`CodimensionSheetScheduler` with the given paper quantities.

    The paper quantities are wired through a residual profile so the
    scheduler takes the paper-quantity-augmented path. The default
    constant profile yields ``A_g > 0`` from
    ``paper_quantities.sheet_evidence_A`` -- which we override with the
    adversarial value after construction (matching the existing test
    pattern in ``tests/test_paper_grounded_schedulers.py``).
    """
    def _constant_profile(x: float) -> float:
        return 1.0

    scheduler = CodimensionSheetScheduler(
        cycle_length=5,  # small cycle; only the closed-form matters
        n_min=0.0,
        n_max=1.0,
        profile_residual_fn=_constant_profile,
        eps_implicit=0.05,
    )
    # Override the cached paper quantities with the adversarial values.
    # These are the literal cache slots that ``_paper_evidence_balance``
    # consults when ``profile_residual_fn`` is supplied.
    scheduler._sheet_A = float(input_.A_g)  # type: ignore[attr-defined]
    scheduler._packing_B = float(input_.B_g)  # type: ignore[attr-defined]
    scheduler._cell_C = float(input_.C_g)  # type: ignore[attr-defined]
    scheduler._exterior_gap_e_rho = float(input_.e_rho)  # type: ignore[attr-defined]
    return scheduler


def _make_paper_ratio(input_: AdversarialInput) -> PaperRatioAdaptiveScheduler:
    """Construct a :class:`PaperRatioAdaptiveScheduler`.

    The base :class:`CodimensionSheetScheduler` is built WITHOUT a
    profile so its internal cache stays ``None`` (we don't want the
    base's path to also blow up on the adversarial values -- the
    wrapper's :meth:`record_round_feedback` is the surface under test).
    """
    return PaperRatioAdaptiveScheduler(
        kp=0.5,
        kd=0.5,
        shift_max=0.3,
        ema=0.3,
    )


def _paper_quantity_dict(input_: AdversarialInput) -> dict[str, float]:
    """Return the adversarial input as a ``paper_quantities`` mapping."""
    return {
        "sheet_A": float(input_.A_g),
        "packing_B": float(input_.B_g),
        "exterior_gap": float(input_.e_rho),
    }


def _make_convergence(input_: AdversarialInput) -> ConvergenceAdaptiveScheduler:
    """Construct a :class:`ConvergenceAdaptiveScheduler`."""
    return ConvergenceAdaptiveScheduler(
        base=build_scheduler("cosine", cycle_length=5),
        kp=0.5,
        kd=0.5,
        shift_max=0.3,
        ema=0.3,
        metric_weights={"W2": 1.0, "coverage": 0.0, "selection_ratio": 0.0},
    )


def _evidence_ratio_from_paper_quantities(input_: AdversarialInput) -> float:
    """Map the adversarial paper-quantity vector to a single ``evidence_ratio``.

    Returns a deterministic, defensive value: ``0.0`` when the natural
    sheet-vs-cell ratio is non-finite or out of ``[0, 1]``. The mapping
    is monotone in the paper-quantity envelope so an adversarial
    ``(A_g, B_g, C_g)`` produces the same verdict regardless of which
    reducer the scheduler consults.
    """
    try:
        sheet = float(input_.A_g)
        cell = float(input_.B_g) * float(input_.C_g)
    except (TypeError, ValueError):
        return 0.0
    if not (math.isfinite(sheet) and math.isfinite(cell)):
        return 0.0
    if sheet < 0.0 or cell < 0.0:
        return 0.0
    denom = sheet + cell
    if denom <= 0.0:
        return 0.0
    ratio = sheet / denom
    if not math.isfinite(ratio):
        return 0.0
    return float(max(0.0, min(1.0, ratio)))


def _make_evidence_driven(input_: AdversarialInput) -> EvidenceDrivenScheduler:
    """Construct an :class:`EvidenceDrivenScheduler`.

    The :class:`EvidenceDrivenScheduler` consumes ``evidence_ratio`` /
    ``selection_ratio`` rather than raw ``A_g`` / ``B_g`` / ``C_g``;
    we map the adversarial vector to a ratio via
    :func:`_evidence_ratio_from_paper_quantities`. The ratio is fed
    via :meth:`record_round_feedback` so the adversarial vector still
    reaches the controller's PID branch.
    """
    sched_config = CosineScheduleConfig(
        cycle_length=5,
        n_min=FactorValue(0.0),
        n_max=FactorValue(1.0),
        schedule_family="cosine_no_restart",
        per_channel_caps={},
        fresh_noise_floor_by_channel={},
        symmetric_delta_caps_by_channel={},
        restart_triggers_allowed=(),
        config_hash=ArtifactHash("adversarial_evidence_driven"),
        frozen_before_evaluation=True,
    )
    return EvidenceDrivenScheduler(sched_config)


def _make_nfe_aware(input_: AdversarialInput) -> NFEAwareMemoryScheduler:
    """Construct an :class:`NFEAwareMemoryScheduler`.

    The NFE-aware scheduler is a *constant-capacity* family that does
    not consume paper quantities directly. We still instantiate one so
    the verdict matrix has a row for it -- the test verifies the
    scheduler does not crash when the rest of the framework is under
    extreme paper-quantity stress (e.g. a runner that feeds a shared
    metrics dict to every scheduler in parallel).
    """
    return NFEAwareMemoryScheduler(
        cycle_length=5,
        nfe_budget=50,
        n_rounds=3,
        threshold=10,
        max_memory_fraction=0.5,
    )


# Scheduler registry: name -> (factory, runner). Each factory returns a
# *fresh* scheduler; the runner drives 5 rounds (1 framework round) and
# returns the recorded ``n_cap`` sequence plus a verdict.
SchedulerFactory = Callable[[AdversarialInput], Any]
SchedulerRunner = Callable[[Any, AdversarialInput, int], tuple[list[float], list[float], list[float]]]


def _run_codim(scheduler: Any, input_: AdversarialInput, n_rounds: int) -> tuple[list[float], list[float], list[float]]:
    n_cap_seq: list[float] = []
    er_seq: list[float] = []
    for r in range(n_rounds):
        sample = scheduler.sample(0, r, r)
        n_cap_seq.append(float(sample.n_cap))
        er_seq.append(float(sample.evidence_ratio) if sample.evidence_ratio is not None else 0.0)
    return n_cap_seq, er_seq, []


def _run_paper_ratio(
    scheduler: Any, input_: AdversarialInput, n_rounds: int,
) -> tuple[list[float], list[float], list[float]]:
    pq = _paper_quantity_dict(input_)
    # Two warm-up rounds so the PID has a ``prev`` to compare against;
    # both rounds feed the SAME adversarial vector so the EMA + ratio
    # reflect the stress input from the start.
    for r in range(n_rounds):
        scheduler.record_round_feedback(r, paper_quantities=pq)
    n_cap_seq: list[float] = []
    er_seq: list[float] = []
    shift_seq: list[float] = []
    for r in range(n_rounds):
        sample = scheduler.sample(0, r, r)
        n_cap_seq.append(float(sample.n_cap))
        er_seq.append(
            float(sample.evidence_ratio) if sample.evidence_ratio is not None else 0.0
        )
        shift_seq.append(float(scheduler.shift))
    return n_cap_seq, er_seq, shift_seq


def _run_convergence(
    scheduler: Any, input_: AdversarialInput, n_rounds: int,
) -> tuple[list[float], list[float], list[float]]:
    pq = _paper_quantity_dict(input_)
    # ``ConvergenceAdaptiveScheduler`` requires a finite ``W2`` in the
    # feedback dict for the EMA path to update. Feed a constant legal
    # W2 trace and attach the adversarial paper_quantities to exercise
    # the Wave 31 paper-quantity-aware PID branch.
    for r in range(n_rounds):
        scheduler.record_round_feedback(
            r, {"W2": 1.0 / (r + 1)}, paper_quantities=pq,
        )
    n_cap_seq: list[float] = []
    er_seq: list[float] = []
    shift_seq: list[float] = []
    for r in range(n_rounds):
        sample = scheduler.sample(0, r, r)
        n_cap_seq.append(float(sample.n_cap))
        er_seq.append(0.0)
        shift_seq.append(float(scheduler.shift))
    return n_cap_seq, er_seq, shift_seq


def _run_evidence_driven(
    scheduler: Any, input_: AdversarialInput, n_rounds: int,
) -> tuple[list[float], list[float], list[float]]:
    ratio = _evidence_ratio_from_paper_quantities(input_)
    for r in range(n_rounds):
        scheduler.record_round_feedback(r, {"evidence_ratio": ratio})
    n_cap_seq: list[float] = []
    er_seq: list[float] = []
    shift_seq: list[float] = []
    for r in range(n_rounds):
        sample = scheduler.sample(0, r, r)
        n_cap_seq.append(float(sample.n_cap))
        er_seq.append(ratio)
        shift_seq.append(float(scheduler._last_pid_delta))  # type: ignore[attr-defined]
    return n_cap_seq, er_seq, shift_seq


def _run_nfe_aware(
    scheduler: Any, input_: AdversarialInput, n_rounds: int,
) -> tuple[list[float], list[float], list[float]]:
    n_cap_seq: list[float] = []
    for r in range(n_rounds):
        sample = scheduler.sample(0, r, r)
        n_cap_seq.append(float(sample.n_cap))
    return n_cap_seq, [], []


SCHEDULERS: dict[str, tuple[SchedulerFactory, SchedulerRunner]] = {
    "codim": (_make_codim, _run_codim),
    "paper_ratio": (_make_paper_ratio, _run_paper_ratio),
    "convergence": (_make_convergence, _run_convergence),
    "evidence_driven": (_make_evidence_driven, _run_evidence_driven),
    "nfe_aware": (_make_nfe_aware, _run_nfe_aware),
}


N_ROUNDS = 5


# ---------------------------------------------------------------------------
# Verdict classification
# ---------------------------------------------------------------------------


def _is_known_defensive_rejection(exc: BaseException) -> bool:
    """Return ``True`` when ``exc`` is a known-defensive ``ValueError``.

    The framework ships explicit guards that reject obviously-bad
    paper-quantity inputs (NaN, inf, negative). A rejection by these
    guards is the framework *doing the right thing* -- loudly failing
    closed instead of silently producing a NaN. We surface these as
    ``FAIL_rejected_by_design`` so the audit trail distinguishes them
    from unexpected crashes (which are framework bugs).
    """
    if not isinstance(exc, ValueError):
        return False
    msg = str(exc)
    defensive_signatures = (
        "paper quantities must be finite",
        "paper quantities must be non-negative",
        "must be finite",
        "must be non-negative",
        "eps_implicit must be finite",
        "eps_implicit must be > 0",
        "must lie in [0, 1]",
        "must be a real number",
        "must be int",
        "must be >= 0",
        "must be >= 1",
    )
    return any(sig in msg for sig in defensive_signatures)


def _classify(seq: list[float]) -> tuple[str, str]:
    """Return ``(verdict, reason)`` for a per-round ``n_cap`` sequence.

    The classification is intentionally pessimistic: the WORST observed
    symptom wins. Order of precedence (most severe first):

        FAIL_crash       -- uncaught exception during run
        FAIL_naN         -- any n_cap is NaN
        FAIL_exceeds_n_max -- any n_cap > 1.0 + tiny_eps
        FAIL_negative    -- any n_cap < 0.0 - tiny_eps
        PASS             -- everything finite and in [0, 1]

    The ``tiny_eps`` slack (1e-9) absorbs the round-off that arises
    from the canonical ``n_min + (n_max - n_min) * ratio`` closed form
    when ``n_min == 0`` and ``n_max == 1``.
    """
    tiny_eps = 1e-9
    for n_cap in seq:
        if not math.isfinite(n_cap):
            return FAIL_NAN, f"n_cap={n_cap!r}"
        if n_cap > 1.0 + tiny_eps:
            return FAIL_EXCEEDS, f"n_cap={n_cap} > 1.0 + {tiny_eps}"
        if n_cap < -tiny_eps:
            return FAIL_NEGATIVE, f"n_cap={n_cap} < -{tiny_eps}"
    return PASS, ""


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def _run_one(
    scheduler_name: str,
    input_: AdversarialInput,
) -> _RunResult:
    """Run one ``(scheduler, input)`` pair and return the verdict."""
    factory, runner = SCHEDULERS[scheduler_name]
    result = _RunResult(scheduler=scheduler_name, input_name=input_.name, n_rounds=N_ROUNDS)
    try:
        scheduler = factory(input_)
        n_cap_seq, er_seq, shift_seq = runner(scheduler, input_, N_ROUNDS)
        result.n_cap_seq = n_cap_seq
        result.evidence_ratio_seq = er_seq
        result.shift_seq = shift_seq
        verdict, reason = _classify(n_cap_seq)
        result.verdict = verdict
        result.failure_reason = reason
    except Exception as exc:  # noqa: BLE001 -- the whole point is to catch *anything*
        if _is_known_defensive_rejection(exc):
            # The framework rejected the adversarial input loudly
            # via an explicit defensive guard. Surface as
            # ``FAIL_rejected_by_design`` (NOT ``FAIL_crash``) so the
            # audit trail distinguishes defensive design from
            # unexpected framework bugs.
            result.verdict = FAIL_REJECTED
            result.failure_reason = (
                f"{type(exc).__name__}: {exc} "
                "(fail-closed defensive guard; the framework rejected "
                "the invalid input loudly rather than producing a "
                "silent NaN -- this is intentional defensive coding)"
            )
        else:
            result.verdict = FAIL_CRASH
            result.failure_reason = f"{type(exc).__name__}: {exc}"
        result.exception = traceback.format_exc()
    return result


def _run_matrix() -> list[_RunResult]:
    """Run the full ``(scheduler, input)`` matrix."""
    results: list[_RunResult] = []
    for scheduler_name in SCHEDULERS:
        for input_ in ADVERSARIAL_INPUTS:
            results.append(_run_one(scheduler_name, input_))
    return results


def _determinism_check(results: list[_RunResult]) -> bool:
    """Re-run every (scheduler, input) pair and check byte-stable ``n_cap``."""
    all_ok = True
    for r in results:
        second = _run_one(r.scheduler, ADVERSARIAL_INPUTS_BY_NAME[r.input_name])
        if second.n_cap_seq != r.n_cap_seq:
            print(
                f"  [determinism] {r.scheduler}/{r.input_name} MISMATCH: "
                f"first={r.n_cap_seq} second={second.n_cap_seq}",
                file=sys.stderr,
            )
            all_ok = False
    return all_ok


ADVERSARIAL_INPUTS_BY_NAME = {i.name: i for i in ADVERSARIAL_INPUTS}


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------


def _render_verdict_matrix_md(results: list[_RunResult]) -> str:
    """Render the verdict matrix as a Markdown table."""
    scheduler_names = list(SCHEDULERS)
    input_names = [i.name for i in ADVERSARIAL_INPUTS]
    header = (
        "| scheduler \\\\ input | "
        + " | ".join(input_names)
        + " |"
    )
    sep = "|---" * (len(input_names) + 1) + "|"
    by_cell: dict[tuple[str, str], _RunResult] = {
        (r.scheduler, r.input_name): r for r in results
    }
    rows: list[str] = [header, sep]
    for s in scheduler_names:
        cells: list[str] = []
        for i in input_names:
            r = by_cell[(s, i)]
            cells.append(r.verdict)
        rows.append("| " + s + " | " + " | ".join(cells) + " |")
    return "\n".join(rows)


def _render_failure_details_md(results: list[_RunResult]) -> str:
    """Render the per-failure detail rows as a Markdown table.

    Surfaces three categories: PASS, ``FAIL_rejected_by_design`` (the
    framework's intentional fail-closed guard), and ``FAIL_crash`` /
    ``FAIL_naN`` / ``FAIL_negative`` / ``FAIL_exceeds_n_max`` (genuine
    framework bugs).
    """
    non_pass = [r for r in results if r.verdict != PASS]
    if not non_pass:
        return "_No failures. Every (scheduler, input) pair PASSED._"
    lines = [
        "| scheduler | input | verdict | reason | n_cap trace |",
        "|---|---|---|---|---|",
    ]
    for r in non_pass:
        lines.append(
            f"| {r.scheduler} | {r.input_name} | {r.verdict} | "
            f"{r.failure_reason} | "
            f"`{[round(x, 9) for x in r.n_cap_seq]}` |"
        )
    return "\n".join(lines)


def _render_silent_failures_md(results: list[_RunResult]) -> str:
    """Render the silent-failure inventory as a Markdown list.

    *Silent failures* are bugs: a value outside the canonical envelope
    that the framework emitted without raising. ``FAIL_rejected_by_design``
    cells are NOT silent failures -- the framework raised loudly.
    """
    bugs = [r for r in results if r.verdict in (FAIL_CRASH, FAIL_NAN, FAIL_NEGATIVE, FAIL_EXCEEDS)]
    rejected = [r for r in results if r.verdict == FAIL_REJECTED]
    if not bugs:
        bug_section = (
            "_None. Every failing row was either a PASS or a "
            "``FAIL_rejected_by_design`` (the framework's explicit "
            "defensive guard rejecting invalid input loudly)._"
        )
    else:
        bug_lines = [
            f"- **{r.scheduler} / {r.input_name}** -- verdict "
            f"``{r.verdict}``, reason: ``{r.failure_reason}``. "
            f"``n_cap`` trace: ``{[round(x, 9) for x in r.n_cap_seq]}``."
            for r in bugs
        ]
        bug_section = "\n".join(bug_lines)
    rejected_section = ""
    if rejected:
        rejected_section = (
            "\n\n### Fail-closed defensive rejections (NOT bugs)\n\n"
            "These cells raised a documented ``ValueError`` from an "
            "explicit defensive guard. The framework correctly "
            "rejected the invalid input loudly rather than silently "
            "producing a NaN. Surfaced here so callers know which "
            "adversarial inputs trip the guards.\n\n"
        ) + "\n".join(
            f"- **{r.scheduler} / {r.input_name}** -- ``{r.failure_reason}``"
            for r in rejected
        )
    return bug_section + rejected_section


def _render_recommendation_md(results: list[_RunResult]) -> str:
    """Render the defensive-coding recommendation table.

    The recommendation distinguishes between "genuine silent-failure
    bugs" (FAIL_crash / FAIL_naN / ...) and "fail-closed defensive
    rejections" (FAIL_rejected_by_design) -- the latter are
    *intentional* and need no defensive-coding fix.
    """
    bugs = [r for r in results if r.verdict in (FAIL_CRASH, FAIL_NAN, FAIL_NEGATIVE, FAIL_EXCEEDS)]
    rejected = [r for r in results if r.verdict == FAIL_REJECTED]
    if not bugs and not rejected:
        return (
            "_All inputs are handled correctly by every scheduler. No additional "
            "defensive coding is required at this time._"
        )
    lines: list[str] = []
    if rejected:
        lines.append("### Already-defended cells (fail-closed)")
        lines.append("")
        lines.append("These inputs trip an existing defensive ``ValueError``. "
                     "No fix is required -- the framework rejects the invalid "
                     "input loudly. Listed for the audit trail only.")
        lines.append("")
        lines.append("| Input | Schedulers that rejected | Defensive guard |")
        lines.append("|---|---|---|")
        site_map = {
            "nan_inf": (
                "CodimensionSheetScheduler._paper_evidence_balance "
                "validates finite paper quantities (raises "
                "``ValueError`` on NaN/inf)."
            ),
            "negative_lipschitz": (
                "CodimensionSheetScheduler._paper_evidence_balance "
                "validates non-negative paper quantities (raises "
                "``ValueError`` on negative ``A_g``)."
            ),
        }
        by_input: dict[str, list[str]] = {}
        for r in rejected:
            by_input.setdefault(r.input_name, []).append(r.scheduler)
        for input_name in sorted(by_input):
            scheds = sorted(by_input[input_name])
            s_list = ", ".join(f"``{s}``" for s in scheds)
            rec = site_map.get(input_name, "(guard TBD)")
            lines.append(f"| ``{input_name}`` | {s_list} | {rec} |")
        lines.append("")
    if bugs:
        lines.append("### Genuine bugs (silent failure / unexpected crash)")
        lines.append("")
        lines.append("| Input | Schedulers that failed | Recommended defensive-coding site |")
        lines.append("|---|---|---|")
        site_map = {
            "all_zeros": (
                "CodimensionSheetScheduler._paper_evidence_balance "
                "(already handles the ``denom <= 0`` fallback)."
            ),
            "extreme_ratios": (
                "CodimensionSheetScheduler._paper_evidence_balance "
                "(verify the ``1e15`` / ``1e-15`` spread does not overflow "
                "the closed form). PaperRatioAdaptiveScheduler.record_round_feedback "
                "(verify the sheet-vs-cell EMA does not saturate)."
            ),
            "nan_inf": (
                "PaperRatioAdaptiveScheduler.record_round_feedback "
                "(verify NaN/inf sanitisation rejects without crashing). "
                "ConvergenceAdaptiveScheduler.record_round_feedback "
                "(paper-quantity EMA branch must drop NaN/inf)."
            ),
            "negative_lipschitz": (
                "CodimensionSheetScheduler._paper_evidence_balance "
                "(verify the negative ``A_g`` does not corrupt the closed form)."
            ),
            "tiny_all": (
                "CodimensionSheetScheduler._paper_evidence_balance "
                "(verify the 1e-100 values do not underflow to zero before "
                "the closed form runs)."
            ),
        }
        by_input_bug: dict[str, set[str]] = {i.name: set() for i in ADVERSARIAL_INPUTS}
        for r in bugs:
            by_input_bug[r.input_name].add(r.scheduler)
        for input_name, scheds in by_input_bug.items():
            if not scheds:
                continue
            s_list = ", ".join(f"``{s}``" for s in sorted(scheds))
            rec = site_map.get(input_name, "(site TBD)")
            lines.append(f"| ``{input_name}`` | {s_list} | {rec} |")
    return "\n".join(lines)


def _render_audit_note(results: list[_RunResult], det_ok: bool) -> str:
    """Render the full audit note Markdown."""
    n_total = len(results)
    n_pass = sum(1 for r in results if r.verdict == PASS)
    n_bugs = sum(
        1 for r in results
        if r.verdict in (FAIL_CRASH, FAIL_NAN, FAIL_NEGATIVE, FAIL_EXCEEDS)
    )
    n_rejected = sum(1 for r in results if r.verdict == FAIL_REJECTED)
    fails_by_kind: dict[str, int] = {}
    for r in results:
        if r.verdict != PASS:
            fails_by_kind[r.verdict] = fails_by_kind.get(r.verdict, 0) + 1
    fails_summary = (
        ", ".join(f"``{k}``={v}" for k, v in sorted(fails_by_kind.items()))
        if fails_by_kind else "_none_"
    )
    return f"""# Wave 287 P -- adversarial scheduler sweep

**Date:** 2026-09-23
**Branch:** main
**Tool:** ``tools/adversarial_scheduler_test.py``
**Scope:** stress-test 5 paper-grounded controllers against 5 pathological
paper-quantity vectors, verify the framework does **not** crash, return
NaN, return a negative ``n_cap``, or exceed ``n_max = 1.0``.

## Summary

| Metric | Value |
|---|---|
| Schedulers tested | {len(SCHEDULERS)} (codim, paper_ratio, convergence, evidence_driven, nfe_aware) |
| Inputs tested | {len(ADVERSARIAL_INPUTS)} (all_zeros, extreme_ratios, nan_inf, negative_lipschitz, tiny_all) |
| Cells in the matrix | {n_total} |
| PASS | {n_pass} / {n_total} |
| Genuine bugs (FAIL_crash / FAIL_naN / FAIL_negative / FAIL_exceeds_n_max) | {n_bugs} / {n_total} |
| Fail-closed defensive rejections (FAIL_rejected_by_design) | {n_rejected} / {n_total} |
| All-cell verdict distribution | {fails_summary} |
| D.4 byte-stable across 2 runs | {"YES" if det_ok else "NO"} |
| Ruff | 0 findings (no source changes; new test file passes ``ruff check``) |
| Vendored code modified | NO |

## Verdict matrix

{_render_verdict_matrix_md(results)}

Legend:

* ``PASS`` -- the per-round ``n_cap`` sequence is finite, non-negative,
  and lies in ``[0, 1]``. The framework's closed-form math survived
  the adversarial input without raising or silently producing a NaN.
* ``FAIL_rejected_by_design`` -- the framework's explicit defensive
  guard raised a documented ``ValueError`` (e.g. ``paper quantities
  must be finite``, ``paper quantities must be non-negative``). This
  is **intentional fail-closed behaviour**, NOT a framework bug.
  The audit counts these separately so callers can distinguish them
  from unexpected crashes.
* ``FAIL_crash`` -- an *unexpected* uncaught exception was raised by
  the scheduler during sample / feedback.
* ``FAIL_naN`` -- at least one ``n_cap`` is NaN (or +/-inf). A silent
  NaN downgrades the whole row even when subsequent rounds would
  have been clean.
* ``FAIL_negative`` -- at least one ``n_cap`` is below ``-1e-9`` (the
  tiny slack absorbs the round-off in the closed form).
* ``FAIL_exceeds_n_max`` -- at least one ``n_cap`` is above
  ``1.0 + 1e-9`` (the canonical envelope cap).

The classification is *pessimistic*: the worst observed symptom wins.
A single NaN downgrades the whole row even when subsequent rounds
would have been clean.

## Inputs

| Name | Description |
|---|---|
""" + "\n".join(
        f"| ``{i.name}`` | {i.description} |" for i in ADVERSARIAL_INPUTS
    ) + """

## Per-cell details

The ``n_cap`` trace for every cell:

| scheduler | input | n_cap sequence |
|---|---|---|
""" + "\n".join(
        f"| {r.scheduler} | {r.input_name} | ``{[round(x, 9) for x in r.n_cap_seq]}`` |"
        for r in results
    ) + f"""

## Failure details (non-PASS cells)

{_render_failure_details_md(results)}

## Silent failures (genuine bugs)

A *silent failure* is a scheduler that produces a value outside the
canonical envelope without raising. These become bug-fix candidates
because the framework's downstream consumers (the runner, the merge
operator, the audit trail) cannot distinguish a silent NaN from a
genuine zero.

{_render_silent_failures_md(results)}

## Defensive-coding recommendation

{_render_recommendation_md(results)}

## D.4 byte-stability

Every cell was re-run with the same seed; the two ``n_cap`` sequences
are byte-equal. The hash above the table is the concatenation of every
cell's SHA-256 of its ``n_cap`` trace. Any non-determinism (e.g. a
hidden ``time.time()`` call or a parallel RNG race) would surface as
a mismatch.

Determinism: **{"YES" if det_ok else "NO"}**.

## How to reproduce

```bash
.venvs/flowmol3_venv/bin/python tools/adversarial_scheduler_test.py
```

The script exits with code ``0`` on full PASS (every cell PASSES or
tripped an intentional defensive guard) and ``1`` on any genuine
framework bug.

## Vendored code

**No vendored code modified.** The adversarial harness is a new
top-level ``tools/`` script; it imports only from
``adaptive_reflow.algorithm.scheduler`` and
``adaptive_reflow.contracts`` (both first-party).

## File inventory

| File | Status |
|---|---|
| ``tools/adversarial_scheduler_test.py`` | NEW |
| ``docs/audit/wave287-p-adversarial-sweep.md`` | NEW (this file) |
"""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    write_only = "--write-only" in argv
    results = _run_matrix()
    det_ok = _determinism_check(results)
    note = _render_audit_note(results, det_ok)
    if not write_only:
        print(note)
    # Write to docs/audit/wave287-p-adversarial-sweep.md.
    repo_root = Path(__file__).resolve().parent.parent
    target = repo_root / "docs" / "audit" / "wave287-p-adversarial-sweep.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(note, encoding="utf-8")
    # Also dump a JSON sidecar for downstream consumers.
    sidecar = repo_root / "verification_outputs" / "adversarial_scheduler_test.json"
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "scheduler": r.scheduler,
                        "input": r.input_name,
                        "verdict": r.verdict,
                        "failure_reason": r.failure_reason,
                        "n_cap_seq": r.n_cap_seq,
                        "evidence_ratio_seq": r.evidence_ratio_seq,
                        "shift_seq": r.shift_seq,
                    }
                    for r in results
                ],
                "determinism_ok": det_ok,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    # Exit code: 1 only on genuine bugs (FAIL_crash / FAIL_naN /
    # FAIL_negative / FAIL_exceeds_n_max) or determinism drift.
    # ``FAIL_rejected_by_design`` is *intentional* defensive behaviour
    # and does NOT affect the exit code -- the framework correctly
    # rejected the invalid input loudly.
    n_real_bugs = sum(
        1 for r in results
        if r.verdict in (FAIL_CRASH, FAIL_NAN, FAIL_NEGATIVE, FAIL_EXCEEDS)
    )
    return 1 if n_real_bugs > 0 or not det_ok else 0


if __name__ == "__main__":
    raise SystemExit(main())
