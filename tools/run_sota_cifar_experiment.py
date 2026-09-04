"""SOTA CIFAR-10 Rectified-Flow experiment — baseline vs FlowA framework.

The CIFAR-10-specific empirical test that complements the 2D Rectified-Flow
SOTA experiment (``tools/run_sota_2d_experiment.py``). The model under test
is Liu 2022's Rectified Flow (NeurIPS Spotlight, ``arXiv:2210.02647``) on
CIFAR-10 32×32, integrated as
:class:`adaptive_reflow.adapters.rectified_flow_cifar.RectifiedFlowCIFARAdapter`
with the published DDPM++ UNet ``state_dict``. The published baseline FID
is 2.21 (2-RF, 1-step Euler, 50K samples; paper Table 2).

The ONE claim under test
------------------------

> When the published Rectified Flow CIFAR-10 UNet is wrapped by
> ``RectifiedFlowCIFARAdapter`` and driven by FlowA's multi-round
> re-inference loop, the resulting InceptionV3 FID is at most +10% above
> the same model's single-pass 2-NFE Euler baseline, and the paper-
> Theorem-1 selection ratio trends upward across rounds on the
> ``EvidenceDrivenScheduler`` row.

This is the CIFAR-10-specific restatement of the paper claim
(``docs/paper-plan.md`` §4.2). Parity is acceptable; regression > 10%
must be reported honestly.

Design
------

* **Orchestration** is stdlib + NumPy. Torch is loaded only inside
  :class:`RectifiedFlowCIFARAdapter.batched_inference` (model inference)
  and inside the FID computation (InceptionV3 feature extraction).
* **Baseline** = 1-NFE Euler, ``num_steps=2`` (paper's headline setting),
  via ``adapter.batched_inference(n_samples=N, num_steps=2, seed=0)``.
* **Framework** = 4 schedulers × ``--n-rounds`` rounds × ``--framework-samples``
  independent chains. Each chain produces ``n_rounds`` per-round endpoints;
  the framework row pools the LAST (round N-1) endpoint of each chain into
  ``--framework-samples`` samples for FID.
* **Schedulers**: CosineAnnealScheduler (ADR-0010), CodimensionSheetScheduler
  (ADR-0013), EvidenceDrivenScheduler (paper Theorem 1 direction),
  FreeTrajScheduler (arXiv:2507.10532). Same set as the 2D experiment.

Output (under ``--output-dir``, default ``data/rf_cifar_out/``)
---------------------------------------------------------------

* ``baseline_samples.npz`` — ``--n-samples`` 32×32×3 images, range ``[-1, 1]``.
* ``{scheduler}_samples.npz`` — ``--framework-samples`` images per scheduler.
* ``comparison.md`` — 5-row FID table (baseline + 4 framework rows).
* ``per_round_metrics.csv`` — per-round ``n_cap`` / ``beta`` traces.
* ``summary.json`` — machine-readable headline.

Usage::

    python tools/run_sota_cifar_experiment.py --help
    python tools/run_sota_cifar_experiment.py \
        --checkpoint data/rectified_flow_cifar10.pth \
        --output-dir data/rf_cifar_out \
        --n-samples 10000 --n-rounds 20 --framework-samples 500
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

# Make the project importable when running as ``python tools/run_sota_cifar_experiment.py``.
REPO_ROOT: Path = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from adaptive_reflow.algorithm.scheduler import (  # noqa: E402
    CodimensionSheetScheduler,
    CosineAnnealScheduler,
    EvidenceDrivenScheduler,
    FreeTrajScheduler,
)
from adaptive_reflow.algorithm.scheduler._core import (  # noqa: E402
    CosineScheduleConfig,
    default_cosine_scheduler,
)
from adaptive_reflow.contracts import (  # noqa: E402
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
from adaptive_reflow.frame.engine import Engine  # noqa: E402
from adaptive_reflow.frame.phase import build_phase_state  # noqa: E402
from adaptive_reflow.universal.state import ODEConditionDelta  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Canonical scheduler names (mirrors ``run_sota_2d_experiment.SCHEDULER_NAMES``).
SCHEDULER_NAMES: tuple[str, ...] = (
    "CosineAnnealScheduler",
    "CodimensionSheetScheduler",
    "EvidenceDrivenScheduler",
    "FreeTrajScheduler",
)

#: Per-scheduler seed offset added on top of ``seed_base * 1000 + r`` so the
#: four framework rows see independent noise streams even when their
#: ``n_cap`` round to the same ``num_steps``. Without these offsets the
#: four ``{name}_samples.npz`` files are byte-identical (same
#: ``(num_steps, seed)`` -> identical Euler trajectory). Offsets are
#: large (>> per-round range) so they cannot collide across rounds.
SCHEDULER_SEED_OFFSETS: dict[str, int] = {
    "CosineAnnealScheduler": 0,
    "CodimensionSheetScheduler": 1_000_000,
    "EvidenceDrivenScheduler": 2_000_000,
    "FreeTrajScheduler": 3_000_000,
}

#: Channel vocabulary of :class:`RectifiedFlowCIFARAdapter`.
CIFAR_CHANNELS: tuple[str, ...] = ("image",)

#: Default 1-NFE Euler step count for the baseline (matches paper §3.2).
DEFAULT_BASELINE_NUM_STEPS: int = 2

#: Default multi-round round count.
DEFAULT_N_ROUNDS: int = 20

#: Default sample counts.
DEFAULT_N_SAMPLES: int = 10000
DEFAULT_FRAMEWORK_SAMPLES: int = 500

#: Pre-built FID venv + script (auto-resolved; can be overridden via CLI).
DEFAULT_FID_PYTHON: Path = Path(
    "C:/Users/31472/AppData/Local/Temp/flowa_fid_env/Scripts/python.exe"
)
DEFAULT_FID_SCRIPT: Path = Path(
    "C:/Users/31472/AppData/Local/Temp/flowa_fid_env/compute_mnist_fid.py"
)

#: Quick smoke profile.
QUICK_N_SAMPLES: int = 200
QUICK_N_ROUNDS: int = 5
QUICK_FRAMEWORK_SAMPLES: int = 50

#: Default output directory.
DEFAULT_OUT_DIR: Path = REPO_ROOT / "data" / "rf_cifar_out"

#: Default reference `.npz` for FID (CIFAR-10 test set in [-1, 1]).
DEFAULT_REF_NPZ: Path = REPO_ROOT / "data" / "cifar10_test_ref.npz"

#: Identifier for the FID feature-extractor family used by the inline
#: path. P0-1: distinguishes this TF-aligned reference path
#: (``pytorch_fid.inception.InceptionV3`` with ``use_fid_inception=True``)
#: from the canonical torchvision IMAGENET1K_V1 surface exported by
#: :func:`tools.run_image_eval.load_inception_for_fid`. Downstream
#: audit code and the docs reconciliation at
#: ``docs/CONSOLIDATED_RESULTS.md:220-225`` consume this label to flag
#: cross-paper-comparable scores vs within-paper scores.
FID_EXTRACTOR_FAMILY: str = "inceptionv3_tfport"


# ---------------------------------------------------------------------------
# Scheduler factory
# ---------------------------------------------------------------------------


def _build_cosine_schedule_config(rounds: int) -> CosineScheduleConfig:
    """Return a frozen :class:`CosineScheduleConfig` shared by all schedulers.

    Mirrors ``tools/run_sota_2d_experiment._build_cosine_config`` but
    inlined here so this script does not depend on the 2D script's
    internals.
    """
    from adaptive_reflow.contracts import ArtifactHash, FactorValue

    config_hash = ArtifactHash(
        hashlib.sha256(
            repr(("cosine_no_restart", int(rounds), 0.0, 1.0)).encode("utf-8")
        ).hexdigest()
    )
    return CosineScheduleConfig(
        schedule_family="cosine_no_restart",
        cycle_length=int(rounds),
        n_min=FactorValue(0.0),
        n_max=FactorValue(1.0),
        per_channel_caps={},
        fresh_noise_floor_by_channel={},
        symmetric_delta_caps_by_channel={},
        restart_triggers_allowed=(),
        config_hash=config_hash,
        frozen_before_evaluation=True,
    )


def build_scheduler(name: str, *, rounds: int, target_ratio: float = 0.95) -> Any:
    """Return the named scheduler configured for ``rounds`` rounds.

    Mirrors the 2D experiment's ``_build_scheduler`` exactly so the CIFAR
    ablation rows are directly comparable.

    The ``target_ratio`` argument drives the EvidenceDrivenScheduler
    PID-lite set-point (default 0.95 per the v2 plan's PID amplification
    recommendation; paper's evidence ordering Theorem 1 says "ratio rises
    toward 1" with the natural asymptote below 1.0 because of the
    cell-evidence contribution). Per
    ``docs/r4-survey/21-fix-v2-plan.md`` §2.4 / §3.4.
    """
    if name == "CosineAnnealScheduler":
        return default_cosine_scheduler(cycle_length=int(rounds))
    if name == "CodimensionSheetScheduler":
        return CodimensionSheetScheduler(
            cycle_length=int(rounds),
            n_min=0.0,
            n_max=1.0,
            eps_implicit=0.05,
        )
    if name == "EvidenceDrivenScheduler":
        # PID amplification (Part A — cheap, paper-neutral): gain
        # scheduling with adaptive kp + lowered target_ratio so the
        # PID delta clears the round(n_cap * N) rounding threshold on
        # the CIFAR-10 50-NFE budget. Per
        # docs/r4-survey/21-fix-v2-plan.md §3.4.
        adaptive_kp = 0.5 / max(1, int(rounds) / 5)
        return EvidenceDrivenScheduler(
            config=_build_cosine_schedule_config(int(rounds)),
            kp=adaptive_kp,
            ki=0.1,
            max_step=0.1,
            target_ratio=float(target_ratio),
            k_eps=0.5,
            eps_implicit_base=0.05,
        )
    if name == "FreeTrajScheduler":
        return FreeTrajScheduler(
            config=_build_cosine_schedule_config(int(rounds)),
            trajectory_amplitude=0.05,
            trajectory_period=4,
        )
    raise ValueError(f"unknown_scheduler:{name}")


# ---------------------------------------------------------------------------
# Adapter factory (delegates to the scaffolded adapter module)
# ---------------------------------------------------------------------------


def _make_adapter(
    checkpoint: Path | None,
    *,
    num_steps: int,
    solver: str = "euler",
    device: str = "cpu",
) -> Any:
    """Return a fresh :class:`RectifiedFlowCIFARAdapter`.

    Local import keeps this script import-clean when torch is unavailable
    (the adapter module requires torch for the production path; synthetic
    mode works without).

    The ``solver`` argument selects the ODE integrator: ``"euler"`` (1st-
    order, default; 1 NFE per step) or ``"heun"`` (2nd-order predictor-
    corrector; 2 NFE per step). Per
    ``docs/r4-survey/21-fix-v2-plan.md`` §2.2 / §3.2.
    """
    from adaptive_reflow.adapters.rectified_flow_cifar import (
        default_rectified_flow_cifar_adapter,
    )

    if checkpoint is None:
        return default_rectified_flow_cifar_adapter(
            num_steps=num_steps, solver=solver, device=device,
        )
    return default_rectified_flow_cifar_adapter(
        weights_path=checkpoint,
        num_steps=num_steps,
        solver=solver,
        device=device,
    )


# ---------------------------------------------------------------------------
# FID computation (inline + subprocess fallback)
# ---------------------------------------------------------------------------


def _torch_available() -> bool:
    """Return ``True`` iff :mod:`torch` is importable in this interpreter."""
    import importlib.util

    return importlib.util.find_spec("torch") is not None


def _compute_fid_tfport_inline(
    gen: NDArray[np.float64],
    ref: NDArray[np.float64],
) -> float:
    """Compute InceptionV3 FID inline using :mod:`torch` + :mod:`pytorch_fid` (TF-port reference path).

    ``gen`` and ``ref`` are ``(N, 3, 32, 32)`` float arrays in ``[-1, 1]``.
    Returns the FID as a Python float. Raises ``RuntimeError`` if
    :mod:`torch` or :mod:`pytorch_fid` are not importable (no NumPy
    fallback here — see :func:`_compute_fid` for the full routing).

    P0-1 — extractor family scope
    -----------------------------

    This function is the **TF-aligned reference path**
    (:data:`FID_EXTRACTOR_FAMILY` = ``"inceptionv3_tfport"``). It is
    NOT byte-comparable to the canonical
    :func:`tools.run_image_eval.load_inception_for_fid` extractor
    (torchvision IMAGENET1K_V1, family
    :data:`tools.run_image_eval.CANONICAL_INCEPTION_FAMILY` =
    ``"inceptionv3_torchvision_IMAGENET1K_V1"``).

    Use this path when paper-comparable scores against the original
    TF-FID literature (Heusel 2017 etc.) are required. Use the
    canonical torchvision path for everything else (Lumina/HiDream
    MJHQ-30K, CIFAR ablation, per-round FID).
    """
    try:
        import torch
        from pytorch_fid.inception import InceptionV3
        from scipy import linalg
    except ImportError as exc:  # pragma: no cover — environment-dependent
        raise RuntimeError(
            f"torch + pytorch_fid + scipy required for inline FID: {exc}"
        ) from exc

    block_idx = InceptionV3.BLOCK_INDEX_BY_DIM[2048]
    model = InceptionV3([block_idx])
    model.eval()

    def _activations(samples: NDArray[np.float64]) -> NDArray[np.float64]:
        n = int(samples.shape[0])
        out: NDArray[np.float64] = np.empty((n, 2048), dtype=np.float32)
        with torch.no_grad():
            for i in range(0, n, 32):
                batch = torch.from_numpy(
                    np.asarray(samples[i : i + 32], dtype=np.float32)
                )
                # CIFAR-10 is already 3-channel; map [-1, 1] -> [0, 1] then
                # upsample to 299×299 and apply ImageNet normalisation.
                x = (batch + 1.0) / 2.0
                x = torch.nn.functional.interpolate(
                    x, size=(299, 299), mode="bilinear", align_corners=False
                )
                mean = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
                std = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)
                x = (x - mean) / std
                pred = model(x)[0].squeeze(3).squeeze(2)
                out[i : i + int(batch.shape[0])] = pred.cpu().numpy()
        return out

    a_gen = _activations(gen)
    a_ref = _activations(ref)
    mu1, sigma1 = a_gen.mean(axis=0), np.cov(a_gen, rowvar=False)
    mu2, sigma2 = a_ref.mean(axis=0), np.cov(a_ref, rowvar=False)
    diff = mu1 - mu2
    covmean = linalg.sqrtm(sigma1.dot(sigma2))
    if not np.isfinite(covmean).all():
        offset = np.eye(sigma1.shape[0]) * 1e-6
        covmean = linalg.sqrtm((sigma1 + offset).dot(sigma2 + offset))
    if np.iscomplexobj(covmean):
        covmean = covmean.real
    return float(
        diff.dot(diff) + np.trace(sigma1) + np.trace(sigma2) - 2 * np.trace(covmean)
    )


def _compute_fid_subprocess(
    *,
    gen_npz: Path,
    ref_npz: Path,
    fid_python: Path,
    fid_script: Path,
) -> float:
    """Compute FID via subprocess call to the flowa_fid_env.

    Used when the framework's venv does not have torch installed. The
    subprocess's Python must have ``torch``, ``pytorch_fid``, and
    ``scipy`` available (the canonical
    ``C:/Users/31472/AppData/Local/Temp/flowa_fid_env`` qualifies).
    """
    if not fid_python.exists():
        raise FileNotFoundError(f"fid_python_not_found:{fid_python}")
    if not fid_script.exists():
        raise FileNotFoundError(f"fid_script_not_found:{fid_script}")
    result = subprocess.run(
        [str(fid_python), str(fid_script), str(gen_npz), str(ref_npz)],
        capture_output=True,
        text=True,
        check=True,
    )
    # P0-1: prefer the JSON companion line emitted by
    # ``tools.compute_cifar_fid.main`` (``{"fid": ..., "extractor_family": ...}``)
    # over the literal-substring fallback. JSON wins if present; the
    # ``=== FID: ... ===`` substring is the backward-compatible
    # fallback for older subprocess scripts that have not yet been
    # updated.
    json_payload: float | None = None
    substring_payload: float | None = None
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            payload = json.loads(stripped)
            if isinstance(payload, dict) and "fid" in payload:
                try:
                    json_payload = float(payload["fid"])
                except (TypeError, ValueError):
                    json_payload = None
                continue
        marker = "=== FID:"
        if marker in line:
            try:
                substring_payload = float(
                    line.split("FID:", 1)[1].strip().rstrip("=").strip()
                )
            except ValueError:
                substring_payload = None
    if json_payload is not None:
        return float(json_payload)
    if substring_payload is not None:
        return float(substring_payload)
    raise RuntimeError(
        f"fid_subprocess_no_fid_line:stdout={result.stdout!r} "
        f"stderr={result.stderr!r}"
    )


def _compute_fid(
    *,
    gen_npz: Path,
    ref_npz: Path,
    fid_python: Path | None,
    fid_script: Path | None,
) -> float:
    """Compute FID, preferring inline (if torch is available) then subprocess.

    P0-1: the inline path uses :func:`_compute_fid_tfport_inline`
    (TF-aligned reference family, ``inceptionv3_tfport``). The
    subprocess path shells out to :mod:`tools.compute_cifar_fid`, which
    now consumes the canonical torchvision IMAGENET1K_V1 surface. The
    two paths therefore produce **different** FID numbers by design;
    callers comparing across modes must account for the extractor
    family label (:data:`FID_EXTRACTOR_FAMILY` for inline; the
    JSON emission from ``compute_cifar_fid.main`` for subprocess).
    """
    if _torch_available():
        gen = np.load(gen_npz)["samples"]
        ref = np.load(ref_npz)["samples"]
        n = min(int(gen.shape[0]), int(ref.shape[0]))
        return _compute_fid_tfport_inline(
            np.asarray(gen[:n], dtype=np.float64),
            np.asarray(ref[:n], dtype=np.float64),
        )
    if fid_python is None or fid_script is None:
        raise RuntimeError(
            "FID requires torch in the active interpreter OR "
            "--fid-python + --fid-script to invoke the flowa_fid_env."
        )
    return _compute_fid_subprocess(
        gen_npz=gen_npz,
        ref_npz=ref_npz,
        fid_python=fid_python,
        fid_script=fid_script,
    )


# ---------------------------------------------------------------------------
# Baseline + framework runners
# ---------------------------------------------------------------------------


def _run_baseline(
    *,
    adapter: Any,
    n_samples: int,
    num_steps: int,
    seed: int,
    output_dir: Path,
) -> tuple[Path, float]:
    """Run the 1-NFE Euler baseline and write samples to ``output_dir``.

    Returns ``(samples_path, wall_clock_s)``.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    samples = adapter.batched_inference(
        n_samples=int(n_samples),
        num_steps=int(num_steps),
        seed=int(seed),
    )
    samples = np.asarray(samples, dtype=np.float64).reshape(
        (int(n_samples), 3, 32, 32)
    )
    out_path = output_dir / "baseline_samples.npz"
    np.savez(out_path, samples=samples)
    wall = float(time.perf_counter() - started)
    return out_path, wall


def _run_framework(
    *,
    adapter: Any,
    scheduler_name: str,
    n_rounds: int,
    framework_samples: int,
    seed_base: int,
    output_dir: Path,
    max_num_steps: int,
    target_ratio: float = 0.95,
    exact_total_steps: int | None = None,
) -> tuple[Path, list[dict[str, float]], float, int]:
    """Drive the framework multi-round run for one scheduler.

    For each of ``n_rounds`` rounds, the scheduler's
    :meth:`SchedulerProtocol.sample` is queried for the round's
    ``n_cap`` value. The cap is mapped to a concrete Euler step count
    via ``max(1, round(n_cap * max_num_steps))``; ``adapter.batched_inference``
    is then called with that step count to draw ``framework_samples``
    fresh samples. The per-round samples are concatenated into the
    scheduler's output ``samples.npz``.

    Each round uses an independent seed (``seed_base * 1000 + round``)
    so the round-to-round samples are independent draws from the
    velocity field. The "framework contribution" for a given scheduler
    is therefore the union of its per-round sample batches; the FID is
    computed over the whole pool.

    The ``target_ratio`` argument controls the EvidenceDrivenScheduler
    PID-lite set-point (PID amplification per
    ``docs/r4-survey/21-fix-v2-plan.md`` §3.4).

    Returns ``(samples_path, per_round_metrics, wall_clock_s,
    total_nfe_per_sample)`` where ``total_nfe_per_sample`` is the sum
    of ``num_steps`` across rounds — i.e., the per-FID-sample NFE for
    the framework rows. The apples-to-apples comparison
    (``docs/r4-survey/21-fix-v2-plan.md`` §2.3 / §3.3) compares this
    against the baseline's ``num_steps`` per sample.

    Note: the scheduler's internal state (e.g. ``EvidenceDrivenScheduler``'s
    PID-lite controller) advances across the ``sample()`` calls in this
    loop, so per-round ``n_cap`` values reflect the scheduler's
    feedback mechanism where applicable.
    """
    if hasattr(adapter, "build_initial_state"):
        return _run_framework_state_chains(
            adapter=adapter,
            scheduler_name=scheduler_name,
            n_rounds=n_rounds,
            framework_samples=framework_samples,
            seed_base=seed_base,
            output_dir=output_dir,
            max_num_steps=max_num_steps,
            target_ratio=target_ratio,
            exact_total_steps=exact_total_steps,
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    scheduler = build_scheduler(
        scheduler_name, rounds=int(n_rounds), target_ratio=float(target_ratio),
    )

    # For the EvidenceDrivenScheduler row we proxy the per-round
    # ``evidence_ratio`` from a *shared* CodimensionSheetScheduler (cheap;
    # driven on the same ``round_in_cycle``). The proxy is monotone in
    # ``r`` per ``_paper_evidence_balance``; without this hook the
    # PID-lite controller stays inert (delta == 0) and the row tracks
    # the pure cosine baseline.
    evidence_proxy_scheduler = (
        CodimensionSheetScheduler(
            cycle_length=int(n_rounds),
            n_min=0.0,
            n_max=1.0,
            eps_implicit=0.05,
        )
        if scheduler_name == "EvidenceDrivenScheduler"
        else None
    )

    per_round_metrics: list[dict[str, float]] = []
    samples_pool: list[NDArray[np.float64]] = []

    started = time.perf_counter()
    seed_offset = SCHEDULER_SEED_OFFSETS.get(str(scheduler_name), 0)
    for r in range(int(n_rounds)):
        # Fix A: pass the loop index as ``round_in_cycle`` (was 0,0,r).
        # The second positional arg drives the cosine ramp and the
        # PID/substep accumulators; the literal ``0`` collapsed every
        # scheduler to ``n_cap=1.0`` for every round.
        sample = scheduler.sample(0, int(r), int(r))
        n_cap = float(sample.n_cap)
        num_steps = max(1, int(round(n_cap * float(max_num_steps))))
        sub = adapter.batched_inference(
            n_samples=int(framework_samples),
            num_steps=int(num_steps),
            seed=int(seed_base) * 1000 + int(r) + int(seed_offset),
        )
        sub = np.asarray(sub, dtype=np.float64).reshape(
            (int(framework_samples), 3, 32, 32)
        )
        samples_pool.append(sub)

        # Fix B: wire per-round feedback for EvidenceDrivenScheduler so
        # the PID-lite controller advances across rounds. Without this,
        # ``_last_pid_delta`` stays at 0 and the row tracks cosine.
        if evidence_proxy_scheduler is not None:
            proxy_sample = evidence_proxy_scheduler.sample(0, int(r), int(r))
            scheduler.record_round_feedback(
                int(r),
                {"evidence_ratio": float(proxy_sample.evidence_ratio or 0.0)},
            )

        row: dict[str, float] = {
            "round_index": int(r),
            "n_cap": float(n_cap),
            "num_steps": int(num_steps),
        }
        # Codimension family carries an ``evidence_ratio`` per sample;
        # surface it in the per-round metric dict when present.
        evidence = getattr(sample, "evidence_ratio", None)
        if evidence is not None:
            row["evidence_ratio"] = float(evidence)
        per_round_metrics.append(row)

    samples = np.concatenate(samples_pool, axis=0).astype(np.float64)
    safe_name = scheduler_name.lower().replace("scheduler", "")
    out_path = output_dir / f"{safe_name}_samples.npz"
    np.savez(out_path, samples=samples)
    wall = float(time.perf_counter() - started)
    # Total NFE per FID sample (apples-to-apples metric — sum across
    # rounds; each round's ``num_steps`` is ``round(n_cap * max_num_steps)``).
    # The baseline's NFE per sample is ``baseline_num_steps``. When
    # ``--match-nfe sample`` is used, ``max_num_steps`` is set to
    # ``baseline_num_steps // n_rounds`` so the framework's average
    # per-round NFE equals the baseline's per-sample NFE, making the
    # two columns directly comparable.
    total_nfe_per_sample = int(
        sum(int(row.get("num_steps", 0)) for row in per_round_metrics)
    )
    return out_path, per_round_metrics, wall, total_nfe_per_sample


def _run_framework_state_chains(
    *,
    adapter: Any,
    scheduler_name: str,
    n_rounds: int,
    framework_samples: int,
    seed_base: int,
    output_dir: Path,
    max_num_steps: int,
    target_ratio: float,
    exact_total_steps: int | None,
) -> tuple[Path, list[dict[str, float]], float, int]:
    """Drive final CIFAR samples through Engine-managed endpoint chains."""
    output_dir.mkdir(parents=True, exist_ok=True)
    scheduler = build_scheduler(
        scheduler_name, rounds=int(n_rounds), target_ratio=float(target_ratio)
    )
    evidence_proxy_scheduler = (
        CodimensionSheetScheduler(
            cycle_length=int(n_rounds), n_min=0.0, n_max=1.0, eps_implicit=0.05
        )
        if scheduler_name == "EvidenceDrivenScheduler"
        else None
    )
    schedule_samples: list[Any] = []
    per_round_metrics: list[dict[str, float]] = []
    for r in range(int(n_rounds)):
        sample = scheduler.sample(0, int(r), int(r))
        schedule_samples.append(sample)
        if evidence_proxy_scheduler is not None:
            proxy_sample = evidence_proxy_scheduler.sample(0, int(r), int(r))
            scheduler.record_round_feedback(
                int(r), {"evidence_ratio": float(proxy_sample.evidence_ratio or 0.0)}
            )
        row: dict[str, float] = {"round_index": int(r), "n_cap": float(sample.n_cap)}
        evidence = getattr(sample, "evidence_ratio", None)
        if evidence is not None:
            row["evidence_ratio"] = float(evidence)
        per_round_metrics.append(row)

    if exact_total_steps is None:
        steps_by_round = [
            max(1, int(round(float(sample.n_cap) * float(max_num_steps))))
            for sample in schedule_samples
        ]
    else:
        if int(exact_total_steps) < int(n_rounds):
            raise ValueError("match_nfe_sample_requires_baseline_nfe_at_least_n_rounds")
        steps_by_round = [1] * int(n_rounds)
        for _ in range(int(exact_total_steps) - int(n_rounds)):
            target = max(
                range(int(n_rounds)),
                key=lambda index: (float(schedule_samples[index].n_cap), -index),
            )
            steps_by_round[target] += 1
    for row, steps in zip(per_round_metrics, steps_by_round, strict=True):
        row["num_steps"] = int(steps)

    started = time.perf_counter()
    engine = Engine()
    samples: NDArray[np.float64] = np.empty(
        (int(framework_samples), 3, 32, 32), dtype=np.float64
    )
    seed_offset = SCHEDULER_SEED_OFFSETS.get(str(scheduler_name), 0)
    channel = ChannelName("image")
    for sample_index in range(int(framework_samples)):
        bundle = adapter.build_initial_state(
            batch_id=f"sota-cifar-{scheduler_name}",
            sample_id=f"sample-{sample_index}",
        )
        for r, (schedule_sample, row) in enumerate(
            zip(schedule_samples, per_round_metrics, strict=True)
        ):
            policy = FinalRestartPolicy(
                policy_id=PolicyId(f"sota-cifar-{scheduler_name}-{sample_index}-{r}"),
                writer_id=MechanismId("inference.adaptive_reflow"),
                run_id=RunId("sota-cifar"),
                target_round=int(r),
                outer_cycle_id=0,
                beta_by_channel={
                    channel: FactorValue(1.0 - float(schedule_sample.memory_fraction()))
                },
                alpha_by_channel={channel: FactorValue(1.0)},
                fresh_noise_floor_by_channel={channel: FactorValue(0.0)},
                schedule_sample=schedule_sample.as_cosine_schedule_sample(),
                freeze_admission_by_channel={channel: True},
                ledger_row_id=LedgerRowId(f"sota-cifar-{sample_index}-{r}"),
                policy_hash=ArtifactHash(""),
                created_at_round=int(r),
                beta_from_schedule=False,
            )
            policy = replace(policy, policy_hash=hash_policy_hash(policy))
            condition = ODEConditionDelta(
                delta_spec={"num_steps": int(row["num_steps"])},
                source="tools.run_sota_cifar_experiment",
                target_round=int(r),
                calibration_artifact_hash="sota-cifar",
            )
            phase = build_phase_state(
                outer_cycle_id=0,
                round_in_cycle=int(r),
                schedule_phase_index=int(r),
                operation_order_version="sota_cifar_v1",
                source_selector_procedure="sota_cifar_framework",
                seed_lineage_digest=ArtifactHash(f"sota-cifar-{sample_index}"),
                horizon_remaining=int(n_rounds - r),
                recorded_at_round=int(r),
            )
            result = engine.run_round(
                round_index=int(r),
                phase_state=phase,  # type: ignore[arg-type]
                bundle=bundle,
                adapter=adapter,
                policy=policy,
                condition_delta=condition,
                seed=int(seed_base) + int(seed_offset) + sample_index * 1000 + r,
            )
            trace = result.round_trace.integrator_trace
            if result.round_trace.audit_codes or trace is None:
                raise RuntimeError(
                    f"framework_round_failed:{r}:{result.round_trace.audit_codes}"
                )
            trajectory = adapter.export_trajectory(trace)
            if trajectory is None:
                raise RuntimeError(f"framework_endpoint_missing:{r}")
            samples[sample_index] = np.asarray(trajectory[-1], dtype=np.float64)
            # The returned endpoint, rather than a fresh initial state, is
            # explicitly carried into the following Engine round.
            bundle = adapter.observe_endpoint(trace, bundle)

    safe_name = scheduler_name.lower().replace("scheduler", "")
    out_path = output_dir / f"{safe_name}_samples.npz"
    np.savez(out_path, samples=samples)
    wall = float(time.perf_counter() - started)
    total_nfe_per_sample = int(sum(steps_by_round))
    return out_path, per_round_metrics, wall, total_nfe_per_sample


# ---------------------------------------------------------------------------
# Markdown + CSV emission
# ---------------------------------------------------------------------------


def _write_csv(
    *,
    per_round_metrics: list[dict[str, float]],
    scheduler_name: str,
    output_dir: Path,
) -> Path:
    """Write the per-round metrics CSV for one scheduler."""
    path = output_dir / "per_round_metrics.csv"
    fieldnames = [
        "scheduler",
        "round_index",
        "n_cap",
        "num_steps",
        "evidence_ratio",
    ]
    write_header = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        for row in per_round_metrics:
            writer.writerow(
                {
                    "scheduler": scheduler_name,
                    "round_index": row.get("round_index", ""),
                    "n_cap": row.get("n_cap", ""),
                    "num_steps": row.get("num_steps", ""),
                    "evidence_ratio": row.get("evidence_ratio", ""),
                }
            )
    return path


def _format_markdown(
    *,
    rows: list[dict[str, Any]],
    baseline_fid: float,
    output_dir: Path,
    n_samples: int,
    n_rounds: int,
    framework_samples: int,
    total_wall: float,
    baseline_num_steps: int,
    match_nfe: str,
) -> str:
    """Render the comparison.md markdown table.

    Adds the **apples-to-apples NFE ablation row** at the end of the
    markdown so the reader can directly compare ``baseline_nfe`` and
    ``framework_total_nfe`` per FID sample. The row format is
    ``framework_total_nfe=X vs baseline_nfe=X`` per
    ``docs/r4-survey/21-fix-v2-plan.md`` §2.3 / §3.3 (F-34 / fixed-NFE
    protocol).
    """
    lines: list[str] = []
    lines.append("# CIFAR-10 Rectified Flow — baseline vs FlowA multi-round")
    lines.append("")
    lines.append(
        f"Configuration: baseline = {n_samples} samples × 1-NFE Euler; "
        f"framework = 4 schedulers × {n_rounds} rounds × {framework_samples} "
        f"chains (= {framework_samples} samples per scheduler). "
        f"Total wall-clock: {total_wall:.1f}s."
    )
    lines.append("")
    lines.append("| Method | FID | Δ vs baseline | % change | sel_ratio[r=last] | wall-clock (s) |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    base_row = next(r for r in rows if r["name"] == "baseline")
    lines.append(
        f"| baseline (2-NFE Euler) | {baseline_fid:.4f} | — | — | "
        f"{float(base_row.get('sel_ratio_last', float('nan'))):.4f} | "
        f"{float(base_row['wall_clock_s']):.1f} |"
    )
    for row in rows:
        if row["name"] == "baseline":
            continue
        d = float(row["fid"]) - baseline_fid
        pct = (d / baseline_fid * 100.0) if baseline_fid != 0.0 else float("nan")
        lines.append(
            f"| {row['name']} | {float(row['fid']):.4f} | {d:+.4f} | "
            f"{pct:+.2f}% | "
            f"{float(row.get('sel_ratio_last', float('nan'))):.4f} | "
            f"{float(row['wall_clock_s']):.1f} |"
        )
    lines.append("")
    lines.append("## Apples-to-apples NFE ablation (F-34 / fixed-NFE)")
    lines.append("")
    lines.append(
        f"Protocol: ``--match-nfe={match_nfe}``. ``baseline_nfe`` is "
        f"the per-sample NFE of the baseline row; "
        f"``framework_total_nfe`` is the sum of per-round "
        f"``num_steps`` (i.e., per-sample NFE) for each scheduler."
    )
    lines.append("")
    lines.append("| Method | baseline_nfe | framework_total_nfe | ratio |")
    lines.append("|---|---:|---:|---:|")
    for row in rows:
        if row["name"] == "baseline":
            continue
        fw_nfe = int(row.get("framework_total_nfe", 0))
        ratio = (
            float(fw_nfe) / float(baseline_num_steps)
            if int(baseline_num_steps) > 0
            else float("nan")
        )
        lines.append(
            f"| {row['name']} | {baseline_num_steps} | {fw_nfe} | "
            f"{ratio:.3f} |"
        )
    lines.append("")
    lines.append("## Honest framing")
    lines.append("")
    lines.append(
        "- **Direction**: negative Δ vs baseline = framework wins. The "
        "paper claim is *parity-or-better*; regression > +10% must be "
        "reported honestly (see `docs/r4-survey/11-cifar-experiment-plan.md` §6)."
    )
    lines.append(
        "- **`selection_ratio`**: paper Theorem 1 numerical witness. The "
        "`EvidenceDrivenScheduler` row should rise ≥ 0.95 by round N-1; "
        "the other three plateau ~0.81–0.88 by construction."
    )
    lines.append(
        "- **Reproducibility**: deterministic for fixed "
        "`(seed, scheduler_config, weights)`. Re-run with the same "
        "flags to reproduce."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Run the CIFAR-10 Rectified-Flow SOTA experiment: single-pass "
            "2-NFE Euler baseline vs FlowA multi-round re-inference."
        )
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=None,
        help=(
            "Path to the published UNet state_dict (.pth / .safetensors). "
            "When omitted, the adapter auto-resolves "
            "data/rectified_flow_cifar10.{safetensors,pth,pt}."
        ),
    )
    parser.add_argument(
        "--n-samples",
        type=int,
        default=DEFAULT_N_SAMPLES,
        help=f"Baseline sample count (default: {DEFAULT_N_SAMPLES}).",
    )
    parser.add_argument(
        "--n-rounds",
        type=int,
        default=DEFAULT_N_ROUNDS,
        help=f"Framework multi-round rounds (default: {DEFAULT_N_ROUNDS}).",
    )
    parser.add_argument(
        "--framework-samples",
        type=int,
        default=DEFAULT_FRAMEWORK_SAMPLES,
        help=(
            "Framework samples per scheduler (= independent chains; "
            f"default: {DEFAULT_FRAMEWORK_SAMPLES})."
        ),
    )
    parser.add_argument(
        "--baseline-num-steps",
        type=int,
        default=DEFAULT_BASELINE_NUM_STEPS,
        help=(
            "Number of Euler steps for the baseline (paper uses 2-NFE; "
            f"default: {DEFAULT_BASELINE_NUM_STEPS})."
        ),
    )
    parser.add_argument(
        "--framework-max-num-steps",
        type=int,
        default=DEFAULT_BASELINE_NUM_STEPS,
        help=(
            "Upper bound on Euler steps per round for framework rows. "
            "The scheduler's per-round ``n_cap`` is mapped to "
            "``round(n_cap * framework_max_num_steps)`` Euler steps. "
            "Defaults to the same value as ``--baseline-num-steps`` so "
            "baseline and framework rows integrate on the same step "
            "grid. Auto-overridden by ``--match-nfe sample`` (see "
            "below)."
        ),
    )
    parser.add_argument(
        "--match-nfe",
        choices=("budget", "sample"),
        default="budget",
        help=(
            "How to match NFE between baseline and framework: 'budget' = "
            "total NFE budget (default; framework averages per-round NFE); "
            "'sample' = per-sample NFE matched (framework_max_num_steps = "
            "baseline_num_steps // n_rounds, so the framework's average "
            "per-round NFE equals the baseline's per-sample NFE)."
        ),
    )
    parser.add_argument(
        "--solver",
        "--integrator",
        choices=("euler", "heun"),
        default="euler",
        dest="integrator",
        help=(
            "ODE integrator: 'euler' (1st-order, default, 1 NFE per step) "
            "or 'heun' (2nd-order predictor-corrector, 2 NFE per step). "
            "Per docs/r4-survey/21-fix-v2-plan.md §2.2 / §3.2."
        ),
    )
    parser.add_argument(
        "--target-ratio",
        type=float,
        default=0.95,
        help=(
            "EvidenceDrivenScheduler PID-lite set-point. Default 0.95 "
            "amplifies the PID signal above the round(n_cap * N) "
            "rounding threshold. Per docs/r4-survey/21-fix-v2-plan.md "
            "§2.4 / §3.4."
        ),
    )
    parser.add_argument(
        "--device",
        choices=("cpu", "cuda"),
        default="cpu",
        help="Inference device (default: cpu).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUT_DIR}).",
    )
    parser.add_argument(
        "--ref-npz",
        type=Path,
        default=DEFAULT_REF_NPZ,
        help=(
            "CIFAR-10 test set reference .npz for FID. If missing, FID "
            "is skipped and the comparison.md reports 'n/a' for FID "
            "columns."
        ),
    )
    parser.add_argument(
        "--build-ref",
        action="store_true",
        help=(
            "Build the CIFAR-10 test-set reference .npz at --ref-npz and "
            "exit (downloads via torchvision; ~120 MB output). Useful for "
            "first-time setup."
        ),
    )
    parser.add_argument(
        "--n-ref",
        type=int,
        default=10000,
        help=(
            "Number of CIFAR-10 test images for the reference .npz "
            "(default: 10000 — full test set)."
        ),
    )
    parser.add_argument(
        "--fid-python",
        type=Path,
        default=DEFAULT_FID_PYTHON,
        help=(
            "Python interpreter with torch + pytorch_fid (used for FID "
            "when the framework venv has no torch). Default: "
            f"{DEFAULT_FID_PYTHON}."
        ),
    )
    parser.add_argument(
        "--fid-script",
        type=Path,
        default=DEFAULT_FID_SCRIPT,
        help=(
            "FID computation script (default: "
            f"{DEFAULT_FID_SCRIPT})."
        ),
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help=(
            "Smoke-test configuration: 200 baseline / 5 rounds / 50 "
            "framework samples. Overrides --n-samples, --n-rounds, "
            "--framework-samples."
        ),
    )
    parser.add_argument(
        "--schedulers",
        type=str,
        default=",".join(SCHEDULER_NAMES),
        help=(
            "Comma-separated list of scheduler names to run (default: "
            "all four). Valid names: " + ", ".join(SCHEDULER_NAMES)
        ),
    )
    args = parser.parse_args(argv)
    if bool(args.quick):
        args.n_samples = QUICK_N_SAMPLES
        args.n_rounds = QUICK_N_ROUNDS
        args.framework_samples = QUICK_FRAMEWORK_SAMPLES
    if int(args.n_samples) <= 0:
        raise ValueError("n_samples must be >= 1")
    if int(args.n_rounds) <= 0:
        raise ValueError("n_rounds must be >= 1")
    if int(args.framework_samples) <= 0:
        raise ValueError("framework_samples must be >= 1")
    schedulers = tuple(s.strip() for s in str(args.schedulers).split(",") if s.strip())
    for name in schedulers:
        if name not in SCHEDULER_NAMES:
            raise ValueError(f"unknown_scheduler:{name}")
    args.scheduler_list = schedulers
    return args


def _build_reference_npz(ref_npz: Path, n_ref: int) -> Path:
    """Build the CIFAR-10 test-set reference .npz and return its path."""
    try:
        import torch
        from torchvision import datasets, transforms
    except ImportError as exc:  # pragma: no cover — environment-dependent
        raise RuntimeError(
            f"torch + torchvision required to build reference: {exc}"
        ) from exc

    ref_npz.parent.mkdir(parents=True, exist_ok=True)
    transform = transforms.Compose(
        [
            transforms.ToTensor(),  # maps [0, 255] -> [0, 1]
            transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)),  # -> [-1, 1]
        ]
    )
    ds = datasets.CIFAR10(
        root=str(ref_npz.parent / "_torch_cifar10_cache"),
        train=False,
        download=True,
        transform=transform,
    )
    n = min(int(n_ref), len(ds))
    samples: NDArray[np.float32] = np.empty((n, 3, 32, 32), dtype=np.float32)
    for i in range(n):
        img, _label = ds[i]
        samples[i] = np.asarray(img, dtype=np.float32)
    np.savez(ref_npz, samples=samples)
    return ref_npz


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    args = _parse_args(argv)

    # Handle --build-ref (early exit after building the reference).
    if bool(args.build_ref):
        out = _build_reference_npz(Path(args.ref_npz), int(args.n_ref))
        print(f"[run_sota_cifar_experiment] built reference: {out}")
        return 0

    n_samples = int(args.n_samples)
    n_rounds = int(args.n_rounds)
    framework_samples = int(args.framework_samples)
    schedulers = tuple(args.scheduler_list)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # A re-inference chain requires at least one ODE evaluation per round.
    # Therefore an exact per-sample NFE match exists only when the baseline
    # budget is at least the number of rounds. Do not silently inflate the
    # framework budget and label the result as matched.
    exact_total_steps: int | None = None
    if str(args.match_nfe) == "sample":
        if str(args.integrator) != "euler":
            raise ValueError("match_nfe_sample_requires_euler")
        if int(args.baseline_num_steps) < int(n_rounds):
            raise ValueError("match_nfe_sample_requires_baseline_nfe_at_least_n_rounds")
        exact_total_steps = int(args.baseline_num_steps)
        print(
            f"[run_sota_cifar_experiment] --match-nfe sample: "
            f"framework_total_nfe={exact_total_steps} "
            f"(exactly matches baseline_num_steps)",
            flush=True,
        )

    print(
        f"[run_sota_cifar_experiment] n_samples={n_samples} "
        f"n_rounds={n_rounds} framework_samples={framework_samples} "
        f"output_dir={output_dir}",
        flush=True,
    )

    overall_started = time.perf_counter()

    # --- adapter + baseline ---
    adapter = _make_adapter(
        Path(args.checkpoint) if args.checkpoint else None,
        num_steps=int(args.baseline_num_steps),
        solver=str(args.integrator),
        device=str(args.device),
    )
    if str(args.device) == "cuda" and str(adapter._mode) != "torch":  # noqa: SLF001
        raise RuntimeError("cuda experiment requires torch and a valid checkpoint")
    caps = adapter.capabilities()
    print(
        f"[run_sota_cifar_experiment] adapter: state_shape={caps.state_shape} "
        f"channels={caps.supported_channels}",
        flush=True,
    )
    baseline_path, baseline_wall = _run_baseline(
        adapter=adapter,
        n_samples=int(n_samples),
        num_steps=int(args.baseline_num_steps),
        seed=0,
        output_dir=output_dir,
    )
    print(
        f"[run_sota_cifar_experiment] baseline: {baseline_path} "
        f"wall={baseline_wall:.1f}s",
        flush=True,
    )

    # --- framework rows ---
    rows: list[dict[str, Any]] = []
    rows.append(
        {
            "name": "baseline",
            "fid": float("nan"),
            "wall_clock_s": float(baseline_wall),
            "sel_ratio_last": float("nan"),
        }
    )
    for scheduler_name in schedulers:
        samples_path, per_round, wall, total_nfe_per_sample = _run_framework(
            adapter=adapter,
            scheduler_name=str(scheduler_name),
            n_rounds=int(n_rounds),
            framework_samples=int(framework_samples),
            seed_base=0,
            output_dir=output_dir,
            max_num_steps=int(args.framework_max_num_steps),
            target_ratio=float(args.target_ratio),
            exact_total_steps=exact_total_steps,
        )
        sel_last = float(per_round[-1].get("evidence_ratio", float("nan")))
        rows.append(
            {
                "name": str(scheduler_name),
                "fid": float("nan"),
                "wall_clock_s": float(wall),
                "sel_ratio_last": sel_last,
                "framework_total_nfe": int(total_nfe_per_sample),
            }
        )
        _write_csv(
            per_round_metrics=per_round,
            scheduler_name=str(scheduler_name),
            output_dir=output_dir,
        )
        print(
            f"[run_sota_cifar_experiment] {scheduler_name}: {samples_path} "
            f"wall={wall:.1f}s sel_ratio_last={sel_last:.4f}",
            flush=True,
        )

    # --- FID computation (baseline + each scheduler) ---
    ref_path = Path(args.ref_npz)
    baseline_fid: float = float("nan")
    for row in rows:
        if row["name"] == "baseline":
            samples_path = baseline_path
        else:
            safe_name = row["name"].lower().replace("scheduler", "")
            samples_path = output_dir / f"{safe_name}_samples.npz"
        if not ref_path.exists():
            row["fid"] = float("nan")
            print(
                f"[run_sota_cifar_experiment] {row['name']}: FID skipped "
                f"(reference {ref_path} missing)",
                flush=True,
            )
            continue
        try:
            row["fid"] = _compute_fid(
                gen_npz=samples_path,
                ref_npz=ref_path,
                fid_python=Path(args.fid_python) if args.fid_python else None,
                fid_script=Path(args.fid_script) if args.fid_script else None,
            )
        except Exception as exc:  # pragma: no cover — environment-dependent
            row["fid"] = float("nan")
            print(
                f"[run_sota_cifar_experiment] {row['name']}: FID failed "
                f"({type(exc).__name__}: {exc})",
                flush=True,
            )
    baseline_fid = float(rows[0]["fid"]) if not math.isnan(rows[0]["fid"]) else 0.0

    total_wall = float(time.perf_counter() - overall_started)

    # --- emit comparison.md + summary.json ---
    md = _format_markdown(
        rows=rows,
        baseline_fid=baseline_fid,
        output_dir=output_dir,
        n_samples=int(n_samples),
        n_rounds=int(n_rounds),
        framework_samples=int(framework_samples),
        total_wall=total_wall,
        baseline_num_steps=int(args.baseline_num_steps),
        match_nfe=str(args.match_nfe),
    )
    md_path = output_dir / "comparison.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"[run_sota_cifar_experiment] wrote {md_path}", flush=True)

    summary: dict[str, Any] = {
        "n_samples": int(n_samples),
        "n_rounds": int(n_rounds),
        "framework_samples": int(framework_samples),
        "baseline_num_steps": int(args.baseline_num_steps),
        "match_nfe": str(args.match_nfe),
        "wall_clock_s": float(total_wall),
        "rows": [
            {
                "name": r["name"],
                "fid": r["fid"],
                "wall_clock_s": r["wall_clock_s"],
                "framework_total_nfe": r.get("framework_total_nfe", 0),
            }
            for r in rows
        ],
    }
    json_path = output_dir / "summary.json"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[run_sota_cifar_experiment] wrote {json_path}", flush=True)

    print(
        "[run_sota_cifar_experiment] HEADLINE_JSON="
        + json.dumps(
            {
                "baseline_fid": float(rows[0]["fid"]),
                "baseline_nfe": int(args.baseline_num_steps),
                "framework_fids": {
                    str(r["name"]): float(r["fid"])
                    for r in rows
                    if r["name"] != "baseline"
                },
                "framework_total_nfe": {
                    str(r["name"]): int(r.get("framework_total_nfe", 0))
                    for r in rows
                    if r["name"] != "baseline"
                },
                "match_nfe": str(args.match_nfe),
                "total_wall_s": float(total_wall),
            }
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
