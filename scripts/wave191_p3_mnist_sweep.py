"""Wave 191 P3 — MNIST FM N=1000 framework-vs-baseline sweep.

Mirrors the Wave 191 P2 CIFAR protocol at matched NFE=50:
- Baseline: single-pass FM NFE=50, beta=0 (restart is a no-op).
- Framework arms (cosine + codimension_sheet + evidence_driven): 4 rounds
  with per-round num_steps = round(n_cap[r] * 12) so average per-round
  NFE = 12 (= 50/4, the matched-NFE anchor); restart-blend beta=0.5
  (memory_fraction=0.5).
- FID: framework-internal Fréchet-projection over 784 -> 128 random
  projection (MnistFrechetProjectionEvaluator). Reference = MNIST test
  (10K digits, the framework's canonical reference).

Paired chunk-FID t-test (k=10 disjoint chunks of N/10 samples) + Bonferroni
correction across 3 framework arms (alpha=0.05/3=0.0167).

Honest disclosure is added in the output JSON when:
- MNIST FM ckpt was materialized in smoke mode (1 epoch, base_channels=8,
  max_train_images=6000) instead of the production 3-epoch / base_channels=16
  recipe, OR
- N < 1000 (capped by wall-time budget).

The framework-side scheduler arms give DIFFERENT total NFE per sample at
this resolution because per-round num_steps is integer-truncated:
  cosine (cycle_length=4):       num_steps=[12, 9, 3, 0] = 24
  codimension_sheet (n=4):       num_steps=[12, 12, 12, 12] = 48
  evidence_driven (no PID fb):   num_steps=[12, 9, 3, 0] = 24

The 'matched NFE' anchor is the *average* per-round NFE (12.5 → 12), not
the total per-sample NFE. This mirrors the Wave 191 P2 audit's
'--match-nfe sample' protocol.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shlex
import sys
import time
import warnings
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Suppress the deprecated-default-cosine-scheduler DeprecationWarning
# (we explicitly want CosineAnnealScheduler + CodimensionSheetScheduler
# + EvidenceDrivenScheduler as 3 distinct arms).
warnings.filterwarnings("ignore", category=DeprecationWarning)

from adaptive_reflow.adapters.mnist_fm import (  # noqa: E402
    MNIST_FM_FLAT_DIM,
    MNIST_FM_NUM_STEPS,
    MnistFmAdapter,
)
from adaptive_reflow.adapters.mnist_fm_train import (  # noqa: E402
    _load_mnist_offline,
    load_weights,
)
from adaptive_reflow.algorithm.scheduler import (  # noqa: E402
    CodimensionSheetScheduler,
    CosineAnnealScheduler,
    CosineScheduleConfig,
    EvidenceDrivenScheduler,
)
from adaptive_reflow.contracts import (  # noqa: E402
    ArtifactHash,
    ChannelName,
    FactorValue,
    FinalRestartPolicy,
    LedgerRowId,
    PolicyId,
    RunId,
    hash_policy_hash,
)
from adaptive_reflow.contracts.authority import validate_final_restart_policy  # noqa: E402
from adaptive_reflow.eval.mnist_fid import (  # noqa: E402
    MnistFrechetProjectionEvaluator,
    _frechet_distance,
)
from adaptive_reflow.universal.state import (  # noqa: E402
    ODEConditionDelta,
    StateBundle,
)

SCHEMA_VERSION: str = "wave191_p3_mnist_n1000_v1"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_N_SAMPLES: int = 1000  # Wave 191 P3 target
FALLBACK_N_SAMPLES: int = 200  # Per task spec §6 if materialization blocked
N_ROUNDS: int = 4
BASELINE_NUM_STEPS: int = 50  # MNIST_FM_NUM_STEPS
FRAMEWORK_MAX_NUM_STEPS: int = 12  # = 50 / 4 (avg-per-round match)
BETA_FRAMEWORK: float = 0.5  # restart-blend memory_fraction=0.5
BETA_BASELINE: float = 0.0  # baseline: no restart-blend
K_CHUNKS: int = 10  # paired t-test on k disjoint chunks

ARM_LABELS: tuple[str, ...] = ("cosine", "codimension_sheet", "evidence_driven")

# Per-arm seed offset (mirrors Wave 191 P2 SCHEDULER_SEED_OFFSETS so each
# arm sees an independent noise stream). All arms use a different seed
# offset so they're not byte-identical.
ARM_SEED_OFFSETS: dict[str, int] = {
    "cosine": 0,
    "codimension_sheet": 1_000_000,
    "evidence_driven": 2_000_000,
}

#: Arm-keyed-prior fix (GAP-38 class, sibling of GAP-37): the legacy design
#: keys the prior on the arm name (``wave191-p3-baseline`` vs
#: ``wave191-p3-{arm}``), so the baseline and framework arms draw INDEPENDENT
#: ``x0`` — the baseline-vs-framework comparison is a two-sample test in
#: disguise. When ``--shared-prior`` is set both arms build this SAME prior
#: (and share the round-0 solver seed), so they differ only by the
#: restart-blend mechanism — the intended paired design.
SHARED_BATCH_ID: str = "wave191-p3"

#: Basenames known to be the 6k-image 1-epoch smoke materialization
#: (`tools/materialize_mnist_fm.py`). Every other checkpoint's recipe has to be
#: looked up rather than assumed; see ``ckpt_is_smoke`` in ``main``.
SMOKE_CKPT_BASENAMES: frozenset[str] = frozenset({"mnist_fm.npz"})


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


def classify_checkpoint(basename: str, width: int) -> bool | None:
    """Is this checkpoint the 6k-image 1-epoch smoke materialization?

    Tri-state because the file cannot always say. The smoke recipe and the
    `w8e3` recipe are both width 8 and 22,481 vs 22,654 bytes, so a size rule
    mislabels one of them; the old rule called all 42 `w8e3` cells smoke and
    wrote "epochs=1, 6,000 images" into their disclosure. ``True`` is reserved
    for the documented smoke artifact, ``False`` for a width the production
    recipe alone uses, and ``None`` for "the file does not say".
    """
    if basename in SMOKE_CKPT_BASENAMES:
        return True
    return False if width >= 16 else None


def git_provenance() -> tuple[str | None, bool | None]:
    """``(HEAD sha, tree dirty?)`` for the checkout this artifact was produced in.

    Recorded per cell because ``commit_sha`` used to be the literal string
    ``"PENDING"``: 540 of the 541 MNIST cells written before 2026-10-27 cannot be
    tied to a code version. Returns ``(None, None)`` when git is unavailable
    rather than failing the run — a missing sha is a caveat, not an error.
    """
    import subprocess

    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=10, check=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=10, check=True,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None, None
    return (sha or None), bool(status.strip())


# ---------------------------------------------------------------------------
# Policy construction
# ---------------------------------------------------------------------------


def beta_for_round(
    beta_total: float, round_idx: int, rounds: int, schedule: str,
) -> float:
    """GAP-55 root-cause fix — per-round fresh fraction from a total budget.

    The legacy driver applies ``beta`` **every round**, so at ``beta=0.5`` and
    ``rounds=4`` the retained signal after the last restart is
    ``0.5**3 = 12.5%`` — an effective fresh fraction of **93.75%**, not the
    50% the label suggests. ``equal_budget`` splits the total noise budget
    geometrically across the ``rounds - 1`` actual restarts (round 0 starts
    from the prior and has no restart), so the cumulative retention equals
    ``1 - beta_total``:

        beta_r = 1 - (1 - beta_total) ** (1 / (rounds - 1))

    ``constant`` reproduces the historical behaviour byte-for-byte.
    """
    if str(schedule) == "constant":
        return float(beta_total)
    if str(schedule) != "equal_budget":
        raise ValueError(f"unknown_beta_schedule:{schedule!r}")
    restarts = max(1, int(rounds) - 1)
    beta_total = max(0.0, min(1.0, float(beta_total)))
    return float(1.0 - (1.0 - beta_total) ** (1.0 / restarts))


def restart_t0_per_round(
    beta_total: float, rounds: int, beta_schedule: str, t0_mode: str,
    fixed_t0: float | None = None,
) -> list[float]:
    """GAP-56: the path time each round starts from.

    ``zero`` reproduces the legacy wiring (every round re-integrates
    ``[0, 1]``). ``memory`` starts round ``r >= 1`` at ``t = 1 - beta_r``,
    which is the time the restart blend actually lives at.

    GAP-74: ``fixed_t0`` pins round ``r >= 1`` to one time regardless of
    ``beta``, which is what the conditional-mean-bound sweep needs — it varies
    ``m`` at constant ``t0`` so the two channels are separable. Round 0 always
    starts at 0. Default ``None`` is the pre-GAP-74 behaviour.
    """
    if fixed_t0 is not None:
        _t = float(fixed_t0)
        if not np.isfinite(_t) or not 0.0 <= _t <= 1.0:
            raise ValueError(f"fixed_t0_must_be_finite_in_[0,1]:{fixed_t0!r}")
        return [0.0] + [_t] * (int(rounds) - 1)
    if str(t0_mode) == "zero":
        return [0.0] * int(rounds)
    if str(t0_mode) != "memory":
        raise ValueError(f"unknown_restart_t0_mode:{t0_mode!r}")
    out: list[float] = [0.0]
    for r in range(1, int(rounds)):
        beta_r = beta_for_round(float(beta_total), int(r), int(rounds), str(beta_schedule))
        out.append(float(1.0 - beta_r))
    return out


def make_policy(*, arm: str, beta: float, round_idx: int) -> FinalRestartPolicy:
    """Build a hash-valid :class:`FinalRestartPolicy` for ``(arm, beta, round_idx)``.

    Mirrors ``tools/experiments/run_mnist_migration.py::make_policy``.
    """
    channel = ChannelName("x")
    policy_id = f"policy-wave191-p3-{arm}-b{beta:.2f}-r{round_idx}"
    from dataclasses import replace
    draft = FinalRestartPolicy(
        policy_id=PolicyId(policy_id),
        writer_id="inference.adaptive_reflow",
        run_id=RunId(f"run-wave191-p3-{arm}"),
        target_round=int(round_idx),
        outer_cycle_id=0,
        beta_by_channel={channel: FactorValue(float(beta))},
        alpha_by_channel={channel: FactorValue(1.0)},
        fresh_noise_floor_by_channel={channel: FactorValue(0.0)},
        schedule_sample=None,
        freeze_admission_by_channel={channel: True},
        ledger_row_id=LedgerRowId(f"ledger-{policy_id}"),
        policy_hash=ArtifactHash(""),
        created_at_round=0,
        beta_from_schedule=False,
    )
    sealed = replace(draft, policy_hash=hash_policy_hash(draft))
    ok, errors = validate_final_restart_policy(sealed)
    if not ok:
        raise AssertionError(f"invalid_policy:{errors!r}")
    return sealed


# ---------------------------------------------------------------------------
# Scheduler factory (cycle_length=4 for matched NFE)
# ---------------------------------------------------------------------------


def _build_cosine_config(cycle_length: int) -> CosineScheduleConfig:
    config_hash = ArtifactHash(
        hashlib.sha256(
            repr(("cosine_no_restart", int(cycle_length), 0.0, 1.0)).encode("utf-8")
        ).hexdigest()
    )
    return CosineScheduleConfig(
        schedule_family="cosine_no_restart",
        cycle_length=int(cycle_length),
        n_min=FactorValue(0.0),
        n_max=FactorValue(1.0),
        per_channel_caps={},
        fresh_noise_floor_by_channel={},
        symmetric_delta_caps_by_channel={},
        restart_triggers_allowed=(),
        config_hash=config_hash,
        frozen_before_evaluation=True,
    )


def build_scheduler(name: str, cycle_length: int):
    """Return the named scheduler configured for ``cycle_length`` rounds.

    Three families:
    - CosineAnnealScheduler: cosine closed-form ramp (n_cap = 1, 0.75, 0.25, 0)
    - CodimensionSheetScheduler: paper-quantity-driven (n_cap near 1.0)
    - EvidenceDrivenScheduler: cosine + PID-lite offset
    """
    config = _build_cosine_config(cycle_length)
    if name == "cosine":
        return CosineAnnealScheduler(config)
    if name == "codimension_sheet":
        return CodimensionSheetScheduler(
            cycle_length=int(cycle_length),
            n_min=0.0,
            n_max=1.0,
            eps_implicit=0.05,
        )
    if name == "evidence_driven":
        return EvidenceDrivenScheduler(config=config)
    raise ValueError(f"unknown_scheduler:{name}")


def per_round_num_steps(name: str, cycle_length: int, max_num_steps: int) -> list[int]:
    """Return the per-round num_steps list for the named scheduler.

    Each round: num_steps[r] = round(n_cap[r] * max_num_steps) clipped to [1, max_num_steps].
    """
    sched = build_scheduler(name, cycle_length)
    out: list[int] = []
    for r in range(int(cycle_length)):
        sample = sched.sample(0, int(r), int(r))
        n_cap = float(sample.n_cap)
        ns = int(round(n_cap * float(max_num_steps)))
        ns = max(1, min(int(max_num_steps), ns))
        out.append(ns)
    return out


def effective_rounds(
    n_rounds: int, total_nfe: int, min_steps_per_round: int = 1,
) -> int:
    """GAP-84b: the round count the budget can actually support.

    ``_allocate_nfe_budget`` gives every round at least one step, so at
    ``total_nfe == n_rounds`` the allocation is ``[1, 1, 1, 1]`` no matter what
    the weights are — four one-step passes through re-noised states. Capping
    the rounds at ``total_nfe // min_steps_per_round`` keeps every round usable
    and, at the extreme, degrades to ``R = 1`` (the single-pass baseline)
    rather than to a degenerate restart.

    ``min_steps_per_round = 1`` returns ``n_rounds`` unchanged, including the
    legacy ``total_nfe < n_rounds`` edge, so every pre-GAP-84b run is
    byte-identical.
    """
    n_rounds = int(n_rounds)
    min_steps = max(1, int(min_steps_per_round))
    if min_steps <= 1:
        return n_rounds
    return min(n_rounds, max(1, int(total_nfe) // min_steps))


def per_round_num_steps_equal_budget(
    name: str,
    cycle_length: int,
    total_nfe: int,
    *,
    allocation: str = "scheduler",
    interval_lengths: list[float] | None = None,
) -> list[int]:
    """GAP-55: split a FIXED total NFE across rounds by scheduler ``n_cap`` weight.

    The legacy :func:`per_round_num_steps` applies ``max_num_steps`` as a
    *per-round cap*, so the arm totals differ from the baseline budget
    (measured: cosine 25, codimension_sheet 48, evidence_driven 25 vs a
    baseline of 50). This helper instead treats the scheduler ``n_cap``
    values as weights and apportions exactly ``total_nfe`` steps, so every
    arm matches the baseline's total inference budget.

    GAP-56 adds ``allocation`` because under ``--restart-t0-mode memory``
    each round only traverses ``[t0_r, 1]``, so the scheduler's ``n_cap``
    weights no longer describe how much path each round covers:

    ``scheduler``
        Legacy GAP-55 behaviour — weights are the scheduler ``n_cap``.
    ``uniform``
        Equal steps per round.
    ``proportional``
        Weights are the interval lengths ``1 - t0_r`` (round 0 covers the
        whole path), i.e. a constant Euler step size across every round.
        Requires ``interval_lengths``.
    """
    from tools.eval.framework import _allocate_nfe_budget  # local: keep import cost off cold start

    if allocation == "scheduler":
        sched = build_scheduler(name, cycle_length)
        weights: list[float] = []
        for r in range(int(cycle_length)):
            weights.append(float(sched.sample(0, int(r), int(r)).n_cap))
    elif allocation == "evidence":
        # The framework's OWN allocation (Wave 35 FIX-3): steps are apportioned
        # inversely to each round's eps_implicit, so the fine-eps terminal
        # refinement rounds get more steps than the coarse-eps early rounds.
        # Bounded to an 8x skew and exact in total NFE. Until now this lived
        # only in tools/run_controlled_audit.py; every headline cell allocated
        # by n_cap, which is ~1.0 for codimension_sheet and therefore uniform.
        from adaptive_reflow.algorithm.nfe_allocation import nfe_steps_for_evidence

        sched = build_scheduler(name, cycle_length)
        eps: list[float] = []
        for r in range(int(cycle_length)):
            sample = sched.sample(0, int(r), int(r))
            e = getattr(sample, "eps_implicit", None)
            eps.append(float(e) if e is not None else float("nan"))
        return nfe_steps_for_evidence(int(total_nfe), eps)
    elif allocation == "uniform":
        weights = [1.0] * int(cycle_length)
    elif allocation == "proportional":
        if interval_lengths is None:
            raise ValueError("proportional_allocation_requires_interval_lengths")
        if len(interval_lengths) != int(cycle_length):
            raise ValueError("interval_lengths_length_mismatch")
        weights = [float(w) for w in interval_lengths]
        if any(w < 0.0 for w in weights) or sum(weights) <= 0.0:
            raise ValueError("interval_lengths_must_be_non_negative_and_nonzero")
    else:
        raise ValueError(f"unknown_nfe_allocation:{allocation!r}")
    return _allocate_nfe_budget(weights, int(total_nfe), int(cycle_length))


# ---------------------------------------------------------------------------
# Sample generation
# ---------------------------------------------------------------------------


def run_baseline(
    *,
    adapter: MnistFmAdapter,
    n_samples: int,
    seed: int,
    verbose: bool = True,
    shared_prior: bool = False,
    num_steps: int = BASELINE_NUM_STEPS,
    batch_suffix: str = "",
    backend: Any | None = None,
) -> np.ndarray:
    """Generate ``n_samples`` baseline endpoints (1 round × ``num_steps``, beta=0).

    ``shared_prior`` (GAP-38) makes the baseline build the SAME ``x0`` prior as
    the framework arms (``SHARED_BATCH_ID``) instead of the arm-keyed
    ``wave191-p3-baseline`` key, so the comparison is paired.

    ``backend`` (additive, default ``None``) is a
    :class:`~adaptive_reflow.adapters.mnist_fm_torch.TorchMnistVelocity`. When
    supplied the per-sample loop is replaced by one batched RK4 over the whole
    population; the ``x0`` draws are still produced by
    :meth:`MnistFmAdapter.build_initial_state`, so the prior is bit-identical
    to the NumPy path and only the integration moves to the GPU.

    Returns ``(n_samples, 784)`` float64 endpoints.
    """
    batch_id = (SHARED_BATCH_ID if shared_prior else "wave191-p3-baseline") + str(batch_suffix)
    samples = np.empty((int(n_samples), MNIST_FM_FLAT_DIM), dtype=np.float64)
    t0 = time.perf_counter()
    if backend is not None:
        priors = np.empty((int(n_samples), MNIST_FM_FLAT_DIM), dtype=np.float64)
        for i in range(int(n_samples)):
            bundle = adapter.build_initial_state(batch_id=batch_id, sample_id=f"s{i:05d}")
            entry = adapter._native_states.get(bundle.native_state_digest, {})
            priors[i] = np.asarray(entry["x0"], dtype=np.float64).reshape(MNIST_FM_FLAT_DIM)
        samples = backend.numpy(
            backend.integrate_rk4(
                priors, t0=0.0, t1=1.0, num_steps=int(num_steps),
            )
        )
    else:
        for i in range(int(n_samples)):
            bundle = adapter.build_initial_state(batch_id=batch_id, sample_id=f"s{i:05d}")
            # No restart (beta=0); the policy doesn't matter — solve_ode uses the bundle's x0.
            condition = ODEConditionDelta(
                delta_spec={"t0": 0.0, "t1": 1.0, "num_steps": int(num_steps)},
                source="wave191_p3_baseline",
                target_round=0,
                calibration_artifact_hash="cal-wave191-p3",
            )
            trace = adapter.solve_ode(bundle, condition, seed=int(seed) + i)
            # Use the framework's observe_endpoint to fold the trajectory into an x0-bearing
            # endpoint bundle, then read x0 (the final sample).
            endpoint_bundle = adapter.observe_endpoint(trace, bundle)
            entry = adapter._native_states.get(endpoint_bundle.native_state_digest, {})
            samples[i] = np.asarray(entry["x0"], dtype=np.float64).reshape(MNIST_FM_FLAT_DIM)
    elapsed = time.perf_counter() - t0
    if verbose:
        print(
            f"[baseline] {n_samples} samples in {elapsed:.1f}s "
            f"({n_samples / elapsed:.1f} samples/s), NFE={int(num_steps)}",
            flush=True,
        )
    return samples


def run_framework_arm(
    *,
    arm_name: str,
    cycle_length: int,
    n_samples: int,
    num_steps_per_round: list[int],
    seed_offset: int,
    beta: float,
    weights_path: Path,
    verbose: bool = True,
    shared_prior: bool = False,
    beta_schedule: str = "constant",
    restart_t0_mode: str = "zero",
    batch_suffix: str = "",
    restart_noise_scale: float = 1.0,
    mean_preserve: bool = False,
    restart_t0: float | None = None,
    backend: Any | None = None,
) -> tuple[np.ndarray, dict[str, int]]:
    """Generate ``n_samples`` framework-arm endpoints (4 rounds × num_steps_per_round[r], beta=beta).

    Each round: build_initial_state → apply_restart_distribution (with beta)
    → compose_condition → solve_ode (num_steps=num_steps_per_round[r]).
    The next round's build_initial_state uses a fresh batch_id so the
    restart-blend sees a fresh source noise.

    ``shared_prior`` (GAP-38) keys round 0 on ``SHARED_BATCH_ID`` (the same
    prior as the baseline) instead of ``wave191-p3-{arm_name}``, so the
    baseline and framework arms start from the SAME ``x0`` — the paired design.

    ``mean_preserve`` (GAP-76, additive, default off) — centroid-anchored
    restart. GAP-77 measured that the restart displaces the batch mean away
    from the reference in 36/36 cells while contracting the covariance in
    36/36, and that the displacement is the whole measured regression. The
    fix applied here is reference-free: the final cloud is translated so its
    batch centroid equals the **round-0** centroid (a single-pass draw from
    the same prior, produced by the same run at no extra cost). A translation
    leaves the covariance untouched, so this keeps the contraction channel and
    removes only the first-moment defect. It is a batch operation, not a
    per-sample one.

    Returns ``(samples, telemetry)`` where ``telemetry`` carries total
    NFE per sample and wall-clock breakdown.
    """
    from dataclasses import replace as _replace

    # Wave 280 R5c sweep: weights_path is forwarded from the caller so the
    # production ckpt at data/mnist_fm/production.ckpt is consumed by every
    # framework arm (not the hardcoded smoke ckpt at data/mnist_fm.npz).
    adapter = MnistFmAdapter(
        weights_path=str(weights_path),
        num_steps=int(BASELINE_NUM_STEPS),  # default; overridden per round via condition
        restart_noise_scale=float(restart_noise_scale),
        restart_t0=restart_t0,  # GAP-74: None keeps the per-round t0
    )

    round0_batch_id = (
        SHARED_BATCH_ID if shared_prior else f"wave191-p3-{arm_name}"
    ) + str(batch_suffix)
    samples = np.empty((int(n_samples), MNIST_FM_FLAT_DIM), dtype=np.float64)
    round0_samples = (
        np.empty((int(n_samples), MNIST_FM_FLAT_DIM), dtype=np.float64)
        if mean_preserve
        else None
    )
    total_nfe = int(sum(num_steps_per_round))
    t0 = time.perf_counter()
    if backend is not None:
        # Batched backend: the prior, the restart blend and the schedule are
        # still produced by the adapter (same seeds, same digests), but the ODE
        # is integrated for the whole population in one call and the priors are
        # held in a NumPy array rather than in the adapter's 128-entry LRU.
        bundles = []
        priors = np.empty((int(n_samples), MNIST_FM_FLAT_DIM), dtype=np.float64)
        for i in range(int(n_samples)):
            # Build and read in the same iteration: the adapter's state cache is
            # an LRU of 128, so a population-sized batch must not rely on it
            # holding more than the entry it just produced.
            b = adapter.build_initial_state(
                batch_id=round0_batch_id, sample_id=f"s{i:05d}",
            )
            bundles.append(b)
            priors[i] = np.asarray(
                adapter._native_states.get(b.native_state_digest, {})["x0"],
                dtype=np.float64,
            ).reshape(MNIST_FM_FLAT_DIM)
        for r in range(int(cycle_length)):
            t_start = 0.0
            if r > 0:
                beta_r = beta_for_round(
                    float(beta), int(r), int(cycle_length), str(beta_schedule),
                )
                policy = make_policy(arm=arm_name, beta=beta_r, round_idx=int(r))
                next_priors = np.empty_like(priors)
                for j, b in enumerate(bundles):
                    nb = adapter.apply_restart_value(priors[j], b, policy)
                    next_priors[j] = np.asarray(
                        adapter._native_states.get(nb.native_state_digest, {})["x0"],
                        dtype=np.float64,
                    ).reshape(MNIST_FM_FLAT_DIM)
                    bundles[j] = nb
                priors = next_priors
                if str(restart_t0_mode) == "memory":
                    t_start = 1.0 - float(beta_r)
                if restart_t0 is not None:
                    t_start = float(restart_t0)
            num_steps = int(num_steps_per_round[r])
            endpoints = backend.numpy(
                backend.integrate_rk4(
                    priors, t0=float(t_start), t1=1.0, num_steps=num_steps,
                )
            )
            bundles = [
                adapter.observe_endpoint_value(endpoints[j], b)
                for j, b in enumerate(bundles)
            ]
            priors = endpoints
            if round0_samples is not None and r == 0:
                round0_samples[:] = endpoints
        samples = priors
    else:
        for i in range(int(n_samples)):
            # Round 0: build initial state (fresh Gaussian x0)
            bundle = adapter.build_initial_state(
                batch_id=round0_batch_id, sample_id=f"s{i:05d}",
            )
            # Subsequent rounds: apply_restart_distribution with beta
            for r in range(int(cycle_length)):
                t_start = 0.0
                if r > 0:
                    beta_r = beta_for_round(
                        float(beta), int(r), int(cycle_length), str(beta_schedule),
                    )
                    policy = make_policy(arm=arm_name, beta=beta_r, round_idx=int(r))
                    bundle = adapter.apply_restart_distribution(bundle, policy)
                    if str(restart_t0_mode) == "memory":
                        # GAP-56: the blend ``m*x1 + (1-m)*x0`` is the path state at
                        # t = m, so the round must integrate [m, 1], not [0, 1].
                        t_start = 1.0 - float(beta_r)
                num_steps = int(num_steps_per_round[r])
                condition = ODEConditionDelta(
                    delta_spec={
                        "t0": float(t_start),
                        "t1": 1.0,
                        "num_steps": int(num_steps),
                    },
                    source=f"wave191_p3_{arm_name}",
                    target_round=int(r),
                    calibration_artifact_hash="cal-wave191-p3",
                )
                seed_for_round = int(seed_offset) + i + r * 1_000_003
                trace = adapter.solve_ode(bundle, condition, seed=seed_for_round)
                # Use the framework's observe_endpoint to fold the trajectory
                # into an x0-bearing endpoint bundle (this is the canonical
                # round-to-round handoff the framework expects).
                bundle = adapter.observe_endpoint(trace, bundle)
                if round0_samples is not None and r == 0:
                    # GAP-76: keep the single-pass endpoint of the same run so the
                    # final cloud can be anchored to its centroid (reference-free).
                    round0_entry = adapter._native_states.get(
                        bundle.native_state_digest, {}
                    )
                    round0_samples[i] = np.asarray(
                        round0_entry["x0"], dtype=np.float64
                    ).reshape(MNIST_FM_FLAT_DIM)
            # Last round's endpoint x0 is the final sample.
            entry = adapter._native_states.get(bundle.native_state_digest, {})
            samples[i] = np.asarray(entry["x0"], dtype=np.float64).reshape(MNIST_FM_FLAT_DIM)
    if round0_samples is not None:
        # GAP-76 centroid anchoring: a pure translation, so the covariance is
        # unchanged and only the first moment moves.
        shift = samples.mean(axis=0) - round0_samples.mean(axis=0)
        samples = np.asarray(samples - shift, dtype=np.float64)
    elapsed = time.perf_counter() - t0
    if verbose:
        print(
            f"[{arm_name}] {n_samples} samples in {elapsed:.1f}s "
            f"({n_samples / elapsed:.1f} samples/s), NFE={total_nfe}/sample, "
            f"per-round={num_steps_per_round}, beta={beta}",
            flush=True,
        )
    return samples, {"total_nfe_per_sample": total_nfe, "wall_sec": float(elapsed)}


# ---------------------------------------------------------------------------
# FID scoring
# ---------------------------------------------------------------------------


def score_population(samples: np.ndarray, ref_features: np.ndarray, projection: np.ndarray) -> float:
    """Compute the framework-internal Fréchet-projection FID for ``samples``."""
    if samples.ndim != 2 or samples.shape[1] != MNIST_FM_FLAT_DIM:
        raise ValueError(f"samples must be (N, 784); got {samples.shape}")
    feats_g = np.asarray(samples @ projection, dtype=np.float64)
    return float(_frechet_distance(feats_g, ref_features))


def paired_ttest(diff: np.ndarray) -> tuple[float, int, float]:
    """Return ``(t_stat, df, p_two_sided)`` for a paired-difference array."""
    from scipy import stats
    n = int(diff.shape[0])
    if n < 2:
        return float("nan"), 0, float("nan")
    mean = float(diff.mean())
    std = float(diff.std(ddof=1))
    if std <= 0.0:
        return float("inf") if mean != 0 else 0.0, n - 1, 0.0 if mean != 0 else 1.0
    t = mean / (std / math.sqrt(n))
    p = float(2.0 * (1.0 - stats.t.cdf(abs(t), df=n - 1)))
    return float(t), n - 1, p


def cohens_dz(diff: np.ndarray) -> float:
    n = int(diff.shape[0])
    if n < 2:
        return float("nan")
    mean = float(diff.mean())
    std = float(diff.std(ddof=1))
    if std <= 0.0:
        return float("inf") if mean != 0 else 0.0
    return mean / std


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-samples", "--n-records", type=int, default=DEFAULT_N_SAMPLES,
                        dest="n_samples",
                        help="Number of samples per arm (alias --n-records, "
                             "Wave 280 R5c sweep)")
    parser.add_argument("--output-dir", type=Path,
                        default=REPO_ROOT / "verification_outputs" / "wave191-p3-mnist-n1000")
    parser.add_argument("--output-json", type=Path,
                        default=REPO_ROOT / "verification_outputs" / "wave191-p3-mnist-n1000.json")
    parser.add_argument("--cache-dir", type=Path, default=REPO_ROOT / "data" / "mnist_fm_train_cache")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--ckpt", type=Path, default=None,
                        help="Path to MNIST FM ckpt (.npz). Defaults to "
                             "data/mnist_fm.npz (the smoke ckpt). Wave 280 "
                             "R5c sweep passes data/mnist_fm/production.ckpt "
                             "for the production-ckpt re-materialization.")
    parser.add_argument("--k-chunks", type=int, default=K_CHUNKS)
    parser.add_argument("--shared-prior", action="store_true",
                        help="GAP-38: make the baseline and framework arms build "
                             "the SAME x0 prior (SHARED_BATCH_ID) and share the "
                             "round-0 solver seed, so the comparison is paired. "
                             "Legacy default keys the prior on the arm name.")
    parser.add_argument("--equal-total-nfe", action="store_true",
                        help=f"GAP-55: apportion the baseline's total NFE "
                             f"({BASELINE_NUM_STEPS}) across each arm's rounds "
                             f"by scheduler n_cap weight, so every arm runs the "
                             f"SAME total budget. Legacy default applies a "
                             f"per-round cap and totals 25/48/25 for "
                             f"cosine/codim/evidence.")
    parser.add_argument("--beta-schedule", choices=("constant", "equal_budget"),
                        default="constant",
                        help="GAP-55: how the restart fresh fraction is split "
                             "across rounds. 'constant' applies --beta every "
                             "round (legacy: 4 rounds at 0.5 retain only 12.5%% "
                             "of the signal). 'equal_budget' sets "
                             "beta_r = 1-(1-beta)^(1/rounds) so the cumulative "
                             "retention equals 1-beta.")
    parser.add_argument("--beta-framework", type=float, default=BETA_FRAMEWORK,
                        help=f"Total restart fresh fraction (default {BETA_FRAMEWORK}).")
    parser.add_argument("--restart-t0-mode", choices=("zero", "memory"),
                        default="zero",
                        help="GAP-56: where each post-restart round starts on the "
                             "probability-flow path. 'zero' (legacy) always starts "
                             "at t=0 even though the restart blend is the path "
                             "state at t=memory_fraction, so the velocity field is "
                             "evaluated at the wrong time and beta=0 is NOT a "
                             "no-op. 'memory' starts at t=memory_fraction, which "
                             "makes the blend exactly on-path and makes beta=0 an "
                             "exact no-op.")
    parser.add_argument("--nfe-allocation",
                        choices=("scheduler", "uniform", "proportional", "evidence"),
                        default="scheduler",
                        help="GAP-56: how --equal-total-nfe apportions steps "
                             "across rounds. 'scheduler' (legacy GAP-55) uses the "
                             "scheduler n_cap weights; 'uniform' gives every "
                             "round the same count; 'proportional' weights by the "
                             "path interval each round actually covers "
                             "(1 - t0_r), i.e. a constant Euler step size.")
    parser.add_argument("--total-nfe", type=int, default=BASELINE_NUM_STEPS,
                        help="GAP-56: shared inference budget. Sets both the "
                             "single-pass baseline's Euler step count and the "
                             f"total NFE apportioned across the framework arms "
                             f"(default {BASELINE_NUM_STEPS}). Lower it to probe "
                             "the regime where the baseline is NOT already at "
                             "the model's FID floor.")
    parser.add_argument("--baseline-num-steps", type=int,
                        default=None,
                        help="GAP-56 attribution control: run the single-pass "
                             "baseline with this many Euler steps instead of "
                             f"{BASELINE_NUM_STEPS}. The framework arms keep "
                             "their own budget, so a baseline at the framework's "
                             "per-round step count isolates the cost of the "
                             "starved first pass from the value of the restarts. "
                             "Defaults to --total-nfe.")
    parser.add_argument("--n-rounds", type=int, default=N_ROUNDS,
                        help="GAP-56 attribution: number of restart rounds. "
                             f"Default {N_ROUNDS}. Fewer rounds give round 0 a "
                             "larger share of the fixed total NFE, which is the "
                             "only lever that reduces the first pass's Euler "
                             "step at a matched budget.")
    parser.add_argument("--min-steps-per-round", type=int, default=1,
                        help="GAP-84b: cap the round count so every round keeps "
                             "at least this many Euler steps, i.e. "
                             "R = min(--n-rounds, total_nfe // this). At the "
                             "default 1 nothing changes. At total NFE = 4 and "
                             "--n-rounds 4 the legacy allocation is [1,1,1,1]; "
                             "with 2 it becomes R=2, [2,2]; with 4, R=1 (the "
                             "single-pass baseline) instead of a degenerate "
                             "restart. Recorded as n_rounds_effective.")
    parser.add_argument("--seed-keyed-prior", action="store_true",
                        help="GAP-56: fold --seed into the prior batch id. "
                             "Without this the prior is keyed only on "
                             "(batch_id, sample_id) and solve_ode discards its "
                             "seed argument, so --seed has NO effect on the "
                             "generated samples and a '3-seed' design produces "
                             "three byte-identical draws (measured: the Wave 280 "
                             "R5c seed42/43/44 npz files are bit-equal).")
    parser.add_argument("--restart-noise-scale", type=float, default=1.0,
                        help="GAP-67: scalar on the fresh restart noise. 1.0 "
                             "(default) leaves the convex blend byte-identical. "
                             "Values >1 restore the blend's second moment, which "
                             "the convex blend loses by m^2 (v_base - v_hat).")
    parser.add_argument("--restart-t0", type=float, default=None,
                        help="GAP-74: pin every restart round (r >= 1) to this "
                             "path time instead of t0 = 1 - beta_r. Needed to "
                             "measure the conditional contraction at fixed t0 "
                             "while m varies; without it the two are tied and "
                             "the deviation channel cannot be separated from "
                             "the marginal one. Round 0 always starts at 0. "
                             "Default (omitted) keeps the per-round t0.")
    parser.add_argument("--mean-preserve", action="store_true",
                        help="GAP-76: centroid-anchored restart. Translate each "
                             "framework arm's final cloud so its batch centroid "
                             "equals the round-0 centroid of the same run. The "
                             "translation leaves the covariance untouched, so it "
                             "removes only the first-moment defect GAP-77 "
                             "measured (36/36 cells, worth the whole regression). "
                             "Default off = byte-identical legacy path.")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--backend", choices=("numpy", "torch"), default="numpy",
                        help="Integration backend. 'numpy' (default) is the "
                             "historical per-sample float64 path and is "
                             "byte-identical to every recorded cell. 'torch' "
                             "batches the same RK4 over the population on a GPU; "
                             "the prior, the restart blend and the schedule are "
                             "still produced by the adapter, so only the "
                             "integration moves. Validated to float64 round-off "
                             "against the NumPy path "
                             "(tests/test_mnist_fm_torch_parity.py).")
    parser.add_argument("--torch-device", default="cuda:0",
                        help="Device for --backend torch (default cuda:0).")
    parser.add_argument("--torch-dtype", choices=("float64", "float32"),
                        default="float64",
                        help="Dtype for --backend torch. float64 (default) "
                             "reproduces the recorded NumPy artifacts; float32 "
                             "is ~17x faster and must not be compared against a "
                             "float64 cell.")
    args = parser.parse_args(argv)

    n_rounds = int(args.n_rounds)
    total_nfe = int(args.total_nfe)
    if total_nfe <= 0:
        raise SystemExit(f"total_nfe_must_be_positive:{total_nfe}")
    baseline_steps = total_nfe if args.baseline_num_steps is None else int(args.baseline_num_steps)
    batch_suffix = f"-s{int(args.seed)}" if bool(args.seed_keyed_prior) else ""
    if baseline_steps <= 0:
        raise SystemExit(f"baseline_num_steps_must_be_positive:{baseline_steps}")
    if n_rounds < 1:
        raise SystemExit(f"n_rounds_must_be_positive:{n_rounds}")

    # GAP-84b — the round count follows the budget. `_allocate_nfe_budget` gives
    # every round at least one step, so at total NFE = n_rounds the allocation
    # is [1,1,1,1] whatever the weights are: four one-step passes through
    # re-noised states, which is not the framework, it is a stub of it. Capping
    # the rounds at `total_nfe // min_steps_per_round` keeps every round usable
    # and, at the extreme, degrades to R=1 (the single-pass baseline) instead of
    # to a degenerate restart. Default 1 reproduces the pre-GAP-84b allocation
    # exactly.
    n_rounds_requested = n_rounds
    min_steps_per_round = max(1, int(args.min_steps_per_round))
    n_rounds = effective_rounds(n_rounds_requested, total_nfe, min_steps_per_round)

    n_samples = int(args.n_samples)
    output_dir = Path(args.output_dir)
    output_json = Path(args.output_json)
    # Wave 280 R5c sweep: if --output-json was not explicitly given AND the
    # --output-dir differs from the default, derive --output-json from
    # --output-dir so per-seed outputs land under the same dir without
    # overwriting the canonical Wave 191 P3 JSON.
    if args.output_json == REPO_ROOT / "verification_outputs" / "wave191-p3-mnist-n1000.json" \
            and output_dir != REPO_ROOT / "verification_outputs" / "wave191-p3-mnist-n1000":
        output_json = output_dir / "sweep_summary.json"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Resolve checkpoint path; surface a smoke disclosure if the ckpt is the
    # smoke 1-epoch / base_channels=8 / 6000-image materialization.
    if args.ckpt is not None:
        ckpt_path = Path(args.ckpt)
        if not ckpt_path.is_absolute():
            ckpt_path = (REPO_ROOT / ckpt_path).resolve()
    else:
        ckpt_path = REPO_ROOT / "data" / "mnist_fm.npz"
    if not ckpt_path.exists():
        raise SystemExit(f"checkpoint_not_found:{ckpt_path}")
    ckpt_size = int(ckpt_path.stat().st_size)
    ckpt_sha256 = hashlib.sha256(ckpt_path.read_bytes()).hexdigest()
    # Width is read from the weights, not guessed from the file size.
    ckpt_width = int(load_weights(ckpt_path)[0].shape[0])
    # Whether the checkpoint is the *smoke materialization* is NOT decidable from
    # the file: the 6k-image 1-epoch smoke recipe and the 60k-image 3-epoch w8e3
    # recipe are both width 8 and land within 200 bytes of each other (22,481 vs
    # 22,654). Until 2026-10-27 this field was ``size < 50_000``, which flagged
    # all 42 w8e3 cells as smoke and wrote a disclosure claiming epochs=1 and
    # 6,000 images for a checkpoint trained on 60,000. The flag is now tri-state:
    # False for width 16 (only the production recipe has that width here), None
    # for width 8 (undecidable from the file), True only for the documented smoke
    # artifact. The recorded recipe lives in
    # verification_outputs/gap35-mnist-regime/aggregate.json.
    ckpt_is_smoke: bool | None = classify_checkpoint(ckpt_path.name, ckpt_width)
    try:
        ckpt_rel = str(ckpt_path.resolve().relative_to(REPO_ROOT))
    except ValueError:  # pragma: no cover - out-of-tree ckpt
        ckpt_rel = str(ckpt_path)
    n_samples_used = n_samples
    n_samples_was_capped = False
    if n_samples_used > FALLBACK_N_SAMPLES * 5:
        # 1000 samples fits within budget; no cap needed. Keep as-is.
        pass

    if not args.quiet:
        print(f"[wave191-p3] ckpt={ckpt_path} sha256={ckpt_sha256[:16]} "
              f"size={ckpt_size} bytes width={ckpt_width} smoke={ckpt_is_smoke}")
        print(f"[wave191-p3] N={n_samples} NFE={BASELINE_NUM_STEPS} rounds={n_rounds} "
              f"framework-max-num-steps={FRAMEWORK_MAX_NUM_STEPS}")

    # ------------------------------------------------------------------
    # 1. Reference features (MNIST test, 10K images, 784 -> 128 random proj)
    # ------------------------------------------------------------------
    t0 = time.perf_counter()
    test_imgs = _load_mnist_offline(split="test", cache_dir=Path(args.cache_dir))
    test_imgs = np.asarray(test_imgs, dtype=np.float64)
    evaluator = MnistFrechetProjectionEvaluator(cache_dir=Path(args.cache_dir))
    ref_features = evaluator._ref_features  # (10000, 128) — already projected
    projection = evaluator._projection  # (784, 128)
    if not args.quiet:
        print(f"[wave191-p3] MNIST test loaded: {test_imgs.shape} "
              f"in {time.perf_counter() - t0:.1f}s; ref features: {ref_features.shape}")

    # ------------------------------------------------------------------
    # 2. Per-round num_steps for each framework arm
    # ------------------------------------------------------------------
    arm_num_steps: dict[str, list[int]] = {}
    t0_per_round = restart_t0_per_round(
        float(args.beta_framework), n_rounds,
        str(args.beta_schedule), str(args.restart_t0_mode),
        fixed_t0=(
            None if args.restart_t0 is None else float(args.restart_t0)
        ),
    )
    interval_lengths = [1.0 - float(t) for t in t0_per_round]
    for name in ARM_LABELS:
        if bool(args.equal_total_nfe):
            ns = per_round_num_steps_equal_budget(
                name, n_rounds, total_nfe,
                allocation=str(args.nfe_allocation),
                interval_lengths=interval_lengths,
            )
        else:
            ns = per_round_num_steps(name, n_rounds, int(FRAMEWORK_MAX_NUM_STEPS))
        arm_num_steps[name] = ns
        if not args.quiet:
            print(f"[wave191-p3] {name} per-round num_steps = {ns} "
                  f"(total NFE = {sum(ns)})")

    # ------------------------------------------------------------------
    # 3. Generate samples for baseline + 3 framework arms
    # ------------------------------------------------------------------
    t_total = time.perf_counter()
    backend: Any | None = None
    if str(args.backend) == "torch":
        from adaptive_reflow.adapters.mnist_fm_torch import TorchMnistVelocity

        backend = TorchMnistVelocity(
            str(ckpt_path),
            device=str(args.torch_device),
            dtype=str(args.torch_dtype),
        )
        if not args.quiet:
            print(f"[wave191-p3] backend=torch device={args.torch_device} "
                  f"dtype={args.torch_dtype}", flush=True)
    if not args.quiet:
        print(f"[wave191-p3] generating baseline ({n_samples} samples) ...")
    adapter_baseline = MnistFmAdapter(
        weights_path=str(ckpt_path), num_steps=int(BASELINE_NUM_STEPS),
    )
    baseline_samples = run_baseline(
        adapter=adapter_baseline,
        n_samples=int(n_samples),
        seed=int(args.seed),
        verbose=not args.quiet,
        shared_prior=bool(args.shared_prior),
        num_steps=int(baseline_steps),
        batch_suffix=batch_suffix,
        backend=backend,
    )

    arm_samples: dict[str, np.ndarray] = {}
    arm_telemetry: dict[str, dict[str, Any]] = {}
    for name in ARM_LABELS:
        if not args.quiet:
            print(f"[wave191-p3] generating {name} ({n_samples} samples) ...")
        # GAP-38: when shared, the framework's round-0 solver seed matches the
        # baseline's (``args.seed``), so round 0 is byte-identical and the arms
        # differ only by the restart-blend mechanism.
        seed_offset = int(args.seed) if args.shared_prior else ARM_SEED_OFFSETS[name]
        s, tel = run_framework_arm(
            arm_name=name,
            cycle_length=n_rounds,
            n_samples=int(n_samples),
            num_steps_per_round=arm_num_steps[name],
            seed_offset=seed_offset,
            beta=float(args.beta_framework),
            weights_path=ckpt_path,
            verbose=not args.quiet,
            shared_prior=bool(args.shared_prior),
            beta_schedule=str(args.beta_schedule),
            restart_t0_mode=str(args.restart_t0_mode),
            batch_suffix=batch_suffix,
            restart_noise_scale=float(args.restart_noise_scale),
            mean_preserve=bool(args.mean_preserve),
            restart_t0=(
                None if args.restart_t0 is None else float(args.restart_t0)
            ),
            backend=backend,
        )
        arm_samples[name] = s
        arm_telemetry[name] = tel

    wall_total = time.perf_counter() - t_total
    if not args.quiet:
        print(f"[wave191-p3] all 4 arms generated in {wall_total:.1f}s "
              f"({wall_total / 60:.1f} min)")

    # Save per-arm samples (npz compressed)
    np.savez_compressed(output_dir / "baseline_samples.npz", samples=baseline_samples)
    for name in ARM_LABELS:
        np.savez_compressed(output_dir / f"{name}_samples.npz", samples=arm_samples[name])

    # ------------------------------------------------------------------
    # 4. FID scoring (headline + chunk-level)
    # ------------------------------------------------------------------
    if not args.quiet:
        print("[wave191-p3] computing FID ...")
    headline_fid: dict[str, float] = {}
    headline_fid["baseline"] = float(score_population(baseline_samples, ref_features, projection))
    for name in ARM_LABELS:
        headline_fid[name] = float(score_population(arm_samples[name], ref_features, projection))
    if not args.quiet:
        for k, v in headline_fid.items():
            print(f"[wave191-p3] {k} FID = {v:.4f}")

    # Paired chunk-level FID: split each arm's N samples into K_CHUNKS disjoint
    # chunks of chunk_size = N / K_CHUNKS samples each. For each chunk k, the
    # FID(gen_chunk[k], ref_chunk[k]) is paired across arms.
    chunk_size = int(n_samples) // int(args.k_chunks)
    if chunk_size * int(args.k_chunks) != n_samples:
        # Trim to the largest multiple; use the first K_CHUNKS * chunk_size samples.
        n_used = chunk_size * int(args.k_chunks)
        if not args.quiet:
            print(f"[wave191-p3] trimming N from {n_samples} to {n_used} for paired chunking")
        n_samples = n_used
    chunk_fids: dict[str, list[float]] = {k: [] for k in ["baseline", *ARM_LABELS]}
    # The reference must also be split into k chunks of chunk_size to keep
    # the FID self-consistent (we use the same 10K reference split each time).
    ref_chunk_size = chunk_size  # use same chunk size for ref too
    rng = np.random.default_rng(int(args.seed) + 99)
    ref_perm = rng.permutation(ref_features.shape[0])
    for k_i in range(int(args.k_chunks)):
        ref_idx = ref_perm[k_i * ref_chunk_size : (k_i + 1) * ref_chunk_size]
        ref_chunk = ref_features[ref_idx]
        chunk_fids["baseline"].append(float(
            score_population(baseline_samples[k_i * chunk_size : (k_i + 1) * chunk_size],
                             ref_chunk, projection)
        ))
        for name in ARM_LABELS:
            chunk_fids[name].append(float(
                score_population(arm_samples[name][k_i * chunk_size : (k_i + 1) * chunk_size],
                                 ref_chunk, projection)
            ))
    if not args.quiet:
        for k_i in range(int(args.k_chunks)):
            line = f"[wave191-p3] chunk {k_i}: "
            for k in ["baseline", *ARM_LABELS]:
                line += f"{k}={chunk_fids[k][k_i]:.4f} "
            print(line, flush=True)

    # ------------------------------------------------------------------
    # 5. Paired t-test + Bonferroni correction
    # ------------------------------------------------------------------
    framework_arms_out: dict[str, dict[str, Any]] = {}
    arm_list_for_verdict: list[tuple[str, float, float, float]] = []
    for name in ARM_LABELS:
        baseline_chunk = np.asarray(chunk_fids["baseline"], dtype=np.float64)
        arm_chunk = np.asarray(chunk_fids[name], dtype=np.float64)
        diff = arm_chunk - baseline_chunk
        t, df, p = paired_ttest(diff)
        dz = cohens_dz(diff)
        delta_pct = float((arm_chunk.mean() - baseline_chunk.mean()) / max(baseline_chunk.mean(), 1e-9) * 100.0)
        bonf = min(float(p) * len(ARM_LABELS), 1.0)
        framework_arms_out[name] = {
            "fid_headline": float(headline_fid[name]),
            "fid_chunks_mean": float(arm_chunk.mean()),
            "fid_chunks_std": float(arm_chunk.std(ddof=1)),
            "delta_vs_baseline_pct": float(delta_pct),
            "p_value_raw": float(p),
            "p_value_bonferroni": float(bonf),
            "bonferroni_significant": bool(bonf < 0.05),
            "cohens_dz": float(dz),
            "t_stat": float(t),
            "df": int(df),
            "n_chunks": int(args.k_chunks),
            "chunk_fids": [float(x) for x in arm_chunk],
            "per_round_num_steps": arm_num_steps[name],
            "total_nfe_per_sample": int(sum(arm_num_steps[name])),
            "beta": float(BETA_FRAMEWORK),
            "telemetry": arm_telemetry[name],
        }
        arm_list_for_verdict.append((name, headline_fid[name], delta_pct, p))
        if not args.quiet:
            print(f"[wave191-p3] {name}: FID={headline_fid[name]:.4f} "
                  f"Δ_vs_baseline={delta_pct:+.4f}% p={p:.4g} "
                  f"(Bonf p={bonf:.4g}, sig={bonf < 0.05})")

    best = min(arm_list_for_verdict, key=lambda x: x[1])
    best_name, best_fid, best_delta, best_p = best
    baseline_fid = headline_fid["baseline"]

    if best_fid < baseline_fid and min(best_p * len(ARM_LABELS), 1.0) < 0.05:
        verdict = "framework_wins"
    elif best_fid > baseline_fid and min(best_p * len(ARM_LABELS), 1.0) < 0.05:
        verdict = "baseline_wins"
    else:
        verdict = "tie"

    # ------------------------------------------------------------------
    # 6. R5 implication
    # ------------------------------------------------------------------
    # Until 2026-10-27 every branch opened with a hardcoded parenthetical
    # describing the smoke recipe (1 epoch, base_channels=8, 6k images) and
    # closed by claiming the cell STRENGTHENED or REPLACED the R5 -15.01%
    # headline. Both were written
    # when the smoke checkpoint was the only one, and both are false for a
    # width-16 production cell. The text now names the checkpoint by its measured
    # width and reports only what this cell measured; the cross-protocol claim is
    # left to the R5c frontier, which is where it is actually made.
    ckpt_desc = f"N={n_samples}, width={ckpt_width}"
    if verdict == "framework_wins":
        r5 = (
            f"Wave 191 P3 MNIST FM ({ckpt_desc}) at matched NFE=50: the best "
            f"framework arm beats the single-pass baseline "
            f"({best_name} FID={best_fid:.4f} vs baseline {baseline_fid:.4f}, "
            f"Δ={best_delta:+.2f}%, Bonferroni p={min(best_p * 3, 1.0):.4f}). "
            f"Best of {len(ARM_LABELS)} arms, so this is a max-statistic under the "
            f"Bonferroni correction, not a claim about the headline arm alone. A "
            f"single-budget point comparison; it does not establish frontier "
            f"dominance."
        )
    elif verdict == "baseline_wins":
        r5 = (
            f"Wave 191 P3 MNIST FM ({ckpt_desc}) at matched NFE=50: the single-pass "
            f"baseline beats the best framework arm "
            f"({best_name} FID={best_fid:.4f} vs baseline {baseline_fid:.4f}, "
            f"Δ={best_delta:+.2f}%, Bonferroni p={min(best_p * 3, 1.0):.4f}). "
            f"A single-budget point comparison; the NFE grid, not this cell, is "
            f"what decides the R5c verdict."
        )
    else:
        r5 = (
            f"Wave 191 P3 MNIST FM ({ckpt_desc}) at matched NFE=50 returns a tie: "
            f"best framework arm {best_name} FID={best_fid:.4f} vs baseline "
            f"{baseline_fid:.4f}, Δ={best_delta:+.2f}% (not Bonferroni-significant). "
            f"A single-budget point comparison; it says nothing about the plateau."
        )

    # ------------------------------------------------------------------
    # 7. Assemble output JSON
    # ------------------------------------------------------------------
    commit_sha, commit_dirty = git_provenance()
    if ckpt_is_smoke is True:
        honest_disclosure = (
            f"SMOKE CKPT USED: {ckpt_rel} ({ckpt_size} bytes, sha256={ckpt_sha256[:16]}) "
            f"was materialized via tools/materialize_mnist_fm.py with epochs=1, "
            f"base_channels=8, max_train_images=6000 (production recipe is "
            f"epochs=3, base_channels=16, full 60K images; 30-40 min CPU). The "
            f"smoke ckpt is intentionally under-trained; absolute FID values are "
            f"high (~hundreds), but the paired baseline-vs-framework comparison "
            f"is valid because both arms use the same model. The smoke model is "
            f"a pragmatic time-budget choice within the 1-2 h Wave 191 P3 budget."
        )
    elif ckpt_is_smoke is False:
        honest_disclosure = (
            f"Width-{ckpt_width} checkpoint: {ckpt_rel} ({ckpt_size} bytes, "
            f"sha256={ckpt_sha256[:16]}). Width is read from the weight shapes; "
            f"the file carries no training metadata, so the epoch count and "
            f"training-set size are not asserted here."
        )
    else:
        honest_disclosure = (
            f"Width-{ckpt_width} checkpoint: {ckpt_rel} ({ckpt_size} bytes, "
            f"sha256={ckpt_sha256[:16]}). The file carries no training metadata, "
            f"and at this size it is consistent with either the 6k-image 1-epoch "
            f"smoke materialization (22,481 bytes) or the 60k-image 3-epoch w8e3 "
            f"recipe (22,654 bytes); both are width 8. The recipe that applies is "
            f"recorded per checkpoint in "
            f"verification_outputs/gap35-mnist-regime/aggregate.json, not in this "
            f"file, so this artifact does not claim one."
        )

    out: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "target": "mnist_fm",
        "n_records": int(n_samples),
        "nfe": int(total_nfe),
        "baseline_nfe": int(baseline_steps),
        "nfe_allocation_mode": (
            "equal_total_budget" if bool(args.equal_total_nfe) else "per_round_cap"
        ),
        "nfe_allocation_weights": str(args.nfe_allocation),
        "beta_schedule": str(args.beta_schedule),
        "restart_t0_mode": str(args.restart_t0_mode),
        "restart_noise_scale": float(args.restart_noise_scale),
        "mean_preserve": bool(args.mean_preserve),
        "restart_t0_override": (
            None if args.restart_t0 is None else float(args.restart_t0)
        ),
        "seed_keyed_prior": bool(args.seed_keyed_prior),
        "prior_batch_suffix": str(batch_suffix),
        "restart_t0_per_round": t0_per_round,
        "beta_total": float(args.beta_framework),
        "beta_per_round": [
            beta_for_round(
                float(args.beta_framework), r, n_rounds,
                str(args.beta_schedule),
            )
            for r in range(n_rounds)
        ],
        "baseline_fid": float(baseline_fid),
        # GAP-84 ADDITIVE (2026-10-25): the baseline's per-chunk FIDs were always
        # computed for the paired t-test but never persisted, so a chunk-level
        # (quality, NFE) reading could only be formed for the framework arm. Same
        # order and same chunk boundaries as ``framework_arms[*]["chunk_fids"]``.
        # Note the scale: a chunk FID is not the headline FID, so a frontier that
        # uses headline values must not mix these units in; they are for a
        # separate, explicitly-labelled chunk-level sensitivity check.
        "baseline_chunk_fids": [float(x) for x in chunk_fids["baseline"]],
        "framework_arms": framework_arms_out,
        "best_arm": best_name,
        "verdict": verdict,
        "r5_implication": r5,
        "wall_min": float(round(wall_total / 60.0, 2)),
        "commit_sha": commit_sha,
        "commit_dirty": commit_dirty,
        "alpha_bonferroni": float(0.05 / len(ARM_LABELS)),
        "n_chunks": int(args.k_chunks),
        "chunk_size": int(chunk_size),
        "statistical_test": (
            f"paired two-sided t-test (df={args.k_chunks - 1}) on chunk-level "
            f"FIDs (k={args.k_chunks} disjoint chunks of {chunk_size} samples each, "
            f"paired across arms and reference); Cohen's d_z on within-chunk "
            f"diffs; Bonferroni correction across {len(ARM_LABELS)} arms "
            f"(alpha=0.05/{len(ARM_LABELS)}={0.05/len(ARM_LABELS):.4f})"
        ),
        "headline_fids": {k: float(v) for k, v in headline_fid.items()},
        "summary_row_fids": {
            "baseline": float(baseline_fid),
            "CosineAnnealScheduler": float(headline_fid["cosine"]),
            "CodimensionSheetScheduler": float(headline_fid["codimension_sheet"]),
            "EvidenceDrivenScheduler": float(headline_fid["evidence_driven"]),
        },
        "checkpoint": str(ckpt_rel),
        "checkpoint_sha256": ckpt_sha256,
        "checkpoint_size_bytes": int(ckpt_size),
        "checkpoint_width": int(ckpt_width),
        # Tri-state since 2026-10-27: False (width >= 16, production recipe),
        # None (width 8 — the file cannot distinguish the 6k smoke recipe from
        # the 60k w8e3 recipe), True (explicitly the smoke artifact). The old
        # ``size < 50_000`` rule called every w8e3 cell a smoke materialization.
        "checkpoint_is_smoke_materialization": ckpt_is_smoke,
        "n_samples_requested": int(args.n_samples),
        "n_samples_used": int(n_samples),
        "n_samples_was_capped": bool(n_samples_was_capped),
        # The real invocation, not a template. Until 2026-10-27 this field was a
        # hardcoded string that named a fixed --output-dir and --seed and
        # dropped every other flag, so 370 of the 376 distinct MNIST cells in
        # this repository describe a command they were not run with. Artifacts
        # written before the fix keep the wrong string (history is not
        # rewritten); METADATA.txt and reproduce/*.sh are authoritative for
        # those. Every artifact written after it carries its own argv.
        "sweep_command": shlex.join([sys.executable, *sys.argv]),
        "backend": str(args.backend),
        "torch_device": str(args.torch_device) if str(args.backend) == "torch" else None,
        "torch_dtype": str(args.torch_dtype) if str(args.backend) == "torch" else None,
        "postprocessor": "scripts/wave191_p3_mnist_sweep.py",
        "per_arm_n_features": {k: int(n_samples) for k in ["baseline", *ARM_LABELS]},
        "honest_disclosure": honest_disclosure,
        "arm_seed_offsets": dict(ARM_SEED_OFFSETS),
        "shared_prior": bool(args.shared_prior),
        "shared_batch_id": (SHARED_BATCH_ID if args.shared_prior else None),
        "framework_max_num_steps_per_round": int(FRAMEWORK_MAX_NUM_STEPS),
        "n_rounds": n_rounds,
        "n_rounds_requested": n_rounds_requested,
        "min_steps_per_round": int(min_steps_per_round),
        "beta_framework": float(BETA_FRAMEWORK),
        "beta_baseline": float(BETA_BASELINE),
        "fid_metric": (
            "framework-internal Fréchet-projection over 784 -> 128 deterministic "
            "Gaussian random projection (seed=42); reference = MNIST test set "
            "(10K digits, same projection); MnistFrechetProjectionEvaluator "
            "(adaptive_reflow.eval.mnist_fid). This is NOT the literature "
            "InceptionV3 FID — the absolute numbers are framework-internal; the "
            "paired baseline-vs-arm comparison is valid since both arms use "
            "the same projection + reference."
        ),
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    with output_json.open("w") as f:
        json.dump(out, f, indent=2)
    if not args.quiet:
        print(f"[wave191-p3] wrote {output_json}")
        print(f"[wave191-p3] verdict={verdict} best_arm={best_name} "
              f"baseline_fid={baseline_fid:.4f} best_arm_fid={best_fid:.4f} "
              f"delta={best_delta:+.4f}% bonf_p={min(best_p * 3, 1.0):.4g}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
