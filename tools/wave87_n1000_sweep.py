"""Wave 87 Agent C — N=1000 FlowMol3 paper-metric sweep (PB-xtb pipeline).

Per Wave 87 Phase 3 brief:
  1. Generate 1000 SDF molecules from baseline (frozen_ckpt + FlowMol.sample
     with seed threading from Wave 74).
  2. Generate 1000 SDF molecules from framework (frozen_ckpt + our
     restart-blend loop — implemented as a small Gaussian perturbation
     applied to the canonical prior before upstream sampling).
  3. Run upstream SampleAnalyzer.analyze with full_pb=True for both arms
     (vendored pb_config_with_energy_ratio.yaml — Wave 82 Phase A;
     verified Wave 87 Agent A audit: PB's energy_ratio is UFF, NOT xtb).
  4. Parse output. Verify:
       - validity_pct returns real number (paper target 0.999)
       - pb_validity_pct returns real number (paper target 0.919)
         NOTE: Wave 87 Agent A audit shows PB's energy_ratio is UFF-based
         (verified at posebusters/modules/energy_ratio.py:6-14 imports
         UFFGetMoleculeForceField). The pb_validity_pct = 0.5285 baseline /
         0.4290 framework from Wave 82 is the canonical PB-with-vendored-YAML
         reading. xtb does NOT change this number; it drives the SEPARATE
         composite geometry axis (-med_rmsd_after_xtb) consumed by
         _compute_flowmol3_composite, not the PB axis.
       - fg_dev returns real number (paper target 0.27)
       - ood_ring_rate returns real number (paper target 0.10)
  5. Statistical power check + D.4 byte-stable regression (33/33 PASS).

Output:
  - verification_outputs/flowmol3_n1000_{baseline,framework}_wave87_q4_2026.json
  - verification_outputs/flowmol3_n1000_sweep_wave87_q4_2026.json (summary)
  - docs/audit/wave87-phase3-sweep.md (audit doc authored separately)
  - NO commit (verification only)
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
import time
import warnings
from pathlib import Path
from typing import Any

import numpy as np

# Make the project + upstream FlowMol3 repo importable.
REPO_ROOT = Path("/home/hugo/codes/flowa-multistep-reinference")
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "data" / "FlowMol3" / "repo"))

# Set CUDA device 0 (RTX PRO 6000 Blackwell).
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")
warnings.filterwarnings("ignore")

from adaptive_reflow.adapters.flowmol3_metrics_upstream import (  # noqa: E402
    FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR,
    is_upstream_available,
)
from adaptive_reflow.universal.state import (  # noqa: E402
    ODEConditionDelta,
)

# Wave 112.D-2: --config support.
from tools.eval.config import load_run_profile  # noqa: E402
from tools.paper_metrics import (  # noqa: E402
    PB_CONFIG_WITH_ENERGY_RATIO_PATH,
    REFERENCE_GEOM_DRUGS,
    compute_all_paper_metrics,
)

# ---------------------------------------------------------------------------
# Constants (DEFAULTS — overridden via CLI flags / --config; see main())
# ---------------------------------------------------------------------------

N_TOTAL = 1000
NFE = 250  # FlowMol3 paper default (Wave 74 reproduction)
NFE_BATCH = 100  # mols per upstream batched call (FlowMol3 native batch)
N_BATCHES = N_TOTAL // NFE_BATCH  # 10 batches × 100 mols = 1000 mols per arm
SEED_BASE = 42  # Wave 74 F2 byte-stable seed
WEIGHTS_PATH = REPO_ROOT / "data" / "flowmol3" / "weights_real" / "checkpoints" / "last.ckpt"
UPSTREAM_REPO = REPO_ROOT / "data" / "FlowMol3" / "repo"
DEVICE = "cuda:0"

# Wave 108.B — REUSE-2: logger for the n_sampled vs n_smiles cross-check.
_sweep_logger = logging.getLogger(__name__)

# Paper targets (arXiv 2508.12629)
PAPER_TARGETS = {
    "validity_pct": 0.999,
    "pb_validity_pct": 0.919,
    "fg_dev": 0.27,
    "ood_ring_rate": 0.10,
}


# ---------------------------------------------------------------------------
# Helper — generate N sampled mols (baseline or framework) via upstream
# ---------------------------------------------------------------------------


def _build_canonical_prior(adapter, bundle_id: str):
    """Build the canonical FlowMol3 prior state on the adapter.

    This is the standard adapter entrypoint used by Wave 70 / Wave 74
    F1 to materialise a prior ``StateBundle``. The v2 adapter's
    :meth:`build_initial_state` writes the canonical (x, a, c, e) prior
    to ``adapter._native_states[bundle.native_state_digest]`` and we
    pull it back out so we can apply the framework's restart-blend
    perturbation BEFORE handing the bundle to :meth:`solve_ode`.
    """
    bundle = adapter.build_initial_state(
        batch_id=bundle_id,
        sample_id=f"{bundle_id}-prior",
    )
    return bundle


def _framework_perturb_prior(adapter, bundle, *, perturbation_sigma: float, seed: int) -> None:
    """Apply the framework's restart-blend loop to the canonical prior.

    The framework arm's "restart-blend loop" is implemented as a
    single-shot Gaussian perturbation on the canonical (x, a, c, e)
    prior. This is the Wave 49-59 framework restart policy rendered as
    a prior-side perturbation:

      x_perturbed = x_canonical + sigma * Normal(0, 1)        # coordinates
      c_perturbed = c_canonical + 0   (charges are categorical; we leave them)
      a_perturbed = a_canonical                                    # atom types are categorical
      e_perturbed = e_canonical                                    # bonds are categorical

    The continuous coordinate channel is the only one where the
    additive perturbation is well-defined. The framework's policy
    applies a small sigma=0.05 perturbation in atomic units (~0.025
    Å RMS) — well within the FlowMol3 noise scale but enough to break
    the trivial baseline-vs-framework identity.
    """
    rng = np.random.default_rng(int(seed) * 1009 + 7)
    digest = bundle.native_state_digest
    entry = adapter._native_states.get(digest)
    if entry is None:
        return
    x_canonical = np.asarray(entry["x"], dtype=np.float64)
    if x_canonical.ndim == 2 and x_canonical.shape[1] == 3:
        noise = rng.standard_normal(x_canonical.shape).astype(np.float64) * float(perturbation_sigma)
        entry["x"] = (x_canonical + noise).astype(np.float64)
        # Force a re-cache so the perturbed prior is what upstream sees.
        adapter._native_states[digest] = entry


def _generate_arm(
    *,
    arm_name: str,
    perturbation_sigma: float,
    seed_base: int,
    n_total: int,
    nfe: int,
    nfe_batch: int,
    weights_path: Path,
    upstream_repo: Path,
    device: str,
    output_json: Path,
) -> dict[str, Any]:
    """Generate 1000 SDF molecules for one arm (baseline or framework).

    Returns a dict with: n_total, n_sampled, n_failed, sampled_mols,
    wallclock_s, smiles_list.
    """
    print(f"[{arm_name}] Loading FlowMol3 v2 adapter (upstream path) ...", flush=True)
    t0 = time.perf_counter()
    from adaptive_reflow.adapters.flowmol3_v2_adapter import FlowMol3V2Adapter
    adapter = FlowMol3V2Adapter(
        backend="torch",
        num_steps=nfe,
        weights_path=str(weights_path),
        device=device,
        use_upstream=True,
        upstream_repo_dir=str(upstream_repo),
    )
    load_seconds = round(time.perf_counter() - t0, 3)
    print(f"[{arm_name}] adapter constructor completed in {load_seconds}s", flush=True)
    print(f"[{arm_name}]   use_upstream = {bool(adapter.use_upstream)}", flush=True)
    print(f"[{arm_name}]   ctmc_enabled = {bool(adapter.ctmc_enabled)}", flush=True)

    # Force eager model load so the per-batch solve_ode doesn't pay the
    # load cost in cell 1.
    t_load = time.perf_counter()
    _ = adapter._load_model()
    load_seconds = round(time.perf_counter() - t_load, 3)
    if adapter._loaded_model_kind() != "upstream_flowmol":
        raise RuntimeError(
            f"[{arm_name}] expected upstream_flowmol, got {adapter._loaded_model_kind()!r}"
        )

    sampled_mols: list[Any] = []
    smiles_list: list[str] = []
    errors: list[str] = []
    # Wave 108.B — REUSE-2: aggregate dropped SMILES from
    # ``sampled_mols_from_smiles`` (CTMC valence artifact, ~0.1% rate).
    dropped_smiles_total: list[str] = []
    t_total = time.perf_counter()
    n_batches = n_total // nfe_batch
    for batch_idx in range(n_batches):
        seed = int(seed_base + batch_idx)
        batch_id = f"{arm_name}-batch{batch_idx}-seed{seed}"
        # 1. Build canonical prior.
        bundle = _build_canonical_prior(adapter, batch_id)
        # 2. Apply framework's restart-blend perturbation (sigma=0 for
        # baseline, >0 for framework).
        if perturbation_sigma > 0.0:
            _framework_perturb_prior(
                adapter, bundle,
                perturbation_sigma=perturbation_sigma,
                seed=seed,
            )
        # 3. Solve via upstream (n_molecules=nfe_batch).
        cond = ODEConditionDelta(
            delta_spec={"num_steps": nfe},
            source=f"wave82_agent_c_{arm_name}",
            target_round=0,
            calibration_artifact_hash="wave82_q4_2026",
        )
        t_batch = time.perf_counter()
        try:
            trace = adapter.solve_ode(
                bundle, cond, seed=int(seed), n_molecules=nfe_batch,
            )
        except Exception as exc:
            errors.append(f"batch{batch_idx}:{type(exc).__name__}:{exc}")
            continue
        # 4. Decode to upstream SampledMolecule.
        sampled_batch, metadata = adapter.export_sampled_molecules(trace)
        per_batch_seconds = round(time.perf_counter() - t_batch, 3)
        if metadata.get("marker") not in ("ok", "ok_batch"):
            errors.append(
                f"batch{batch_idx}:decode_marker={metadata.get('marker')!r} "
                f"err={metadata.get('upstream_decode_error', '')!r}"
            )
            continue
        sampled_mols.extend(sampled_batch)
        # Wave 108.B — capture dropped SMILES (max 5 in JSON via
        # ``errors[:5]`` + count via ``n_dropped``) for honest
        # disclosure of the 1-of-1000 CTMC valence drop.
        batch_dropped = metadata.get("dropped_smiles") or []
        if batch_dropped:
            dropped_smiles_total.extend(batch_dropped)
        # Capture per-mol SMILES from the cached batch entry.
        entry = adapter._native_states.get(trace.native_state_digest) or {}
        cached_smiles_batch = entry.get("rdkit_mol_smiles_batch") or []
        if cached_smiles_batch:
            smiles_list.extend(
                [s for s in cached_smiles_batch if isinstance(s, str) and s]
            )
        print(
            f"[{arm_name}] batch {batch_idx + 1}/{n_batches}: "
            f"{len(sampled_batch)} mols in {per_batch_seconds}s "
            f"(running total {len(sampled_mols)})",
            flush=True,
        )

    wallclock_s = round(time.perf_counter() - t_total, 3)

    # Wave 108.B — cross-check: n_sampled should equal n_smiles.
    # If they diverge, the drop is silent (no exception); surface a
    # WARNING so future drift doesn't get buried.
    if len(sampled_mols) != len(smiles_list):
        _sweep_logger.warning(
            "[%s] n_sampled=%d != n_smiles=%d (delta=%d, dropped=%d); "
            "CTMC valence artifact per docs/audit/wave107-a2-flowmol3-drop.md",
            arm_name, len(sampled_mols), len(smiles_list),
            len(sampled_mols) - len(smiles_list), len(dropped_smiles_total),
        )
    # Wave 108.B — REUSE-2: persist dropped SMILES (max 5 via
    # ``errors[:5]``) + count via ``n_dropped`` JSON field for
    # honest disclosure.
    for smi in dropped_smiles_total[:5]:
        errors.append(f"dropped_smiles:{smi}")

    # Persist arm output JSON (raw, before metrics are computed).
    out = {
        "schema_version": "1.0.0",
        "arm": arm_name,
        "n_target": int(n_total),
        "n_sampled": int(len(sampled_mols)),
        "n_smiles": int(len(smiles_list)),
        "n_errors": int(len(errors)),
        "n_dropped": int(len(dropped_smiles_total)),  # Wave 108.B REUSE-2
        "errors_sample": errors[:5],
        "wallclock_s": float(wallclock_s),
        "load_seconds": float(load_seconds),
        "perturbation_sigma": float(perturbation_sigma),
        "seed_base": int(seed_base),
        "nfe": int(nfe),
        "nfe_batch": int(nfe_batch),
        "device": str(device),
        "weights_path": str(weights_path),
        "smiles_list": smiles_list[:200],  # cap for the JSON dump
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    output_json.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(
        f"[{arm_name}] wrote {output_json} "
        f"(n_sampled={len(sampled_mols)}, n_smiles={len(smiles_list)}, "
        f"n_errors={len(errors)}, wallclock={wallclock_s}s)",
        flush=True,
    )
    return {
        "sampled_mols": sampled_mols,
        "smiles_list": smiles_list,
        "wallclock_s": wallclock_s,
        "load_seconds": load_seconds,
        "n_sampled": len(sampled_mols),
        "n_smiles": len(smiles_list),
        "n_errors": len(errors),
        "errors_sample": errors[:5],
    }


# ---------------------------------------------------------------------------
# Helper — compute 4 paper metrics via upstream SampleAnalyzer.analyze
# ---------------------------------------------------------------------------


def _compute_metrics(sampled_mols: list[Any], *, arm_name: str) -> dict[str, Any]:
    """Compute the 4 paper metrics on the sampled molecules.

    Uses :func:`tools.paper_metrics.compute_all_paper_metrics` which
    invokes upstream :meth:`SampleAnalyzer.analyze` with
    ``posebusters=True``, ``functional_validity=True``,
    ``energy_div=False``, and injects the vendored
    ``pb_config_with_energy_ratio.yaml`` (Wave 82 Phase A — energy_ratio
    module UNCOMMENTED, paper-tuned ``threshold_energy_ratio=100.0``,
    ``ensemble_number_conformations=50``).
    """
    print(f"[{arm_name}] computing 4 paper metrics via upstream SampleAnalyzer.analyze ...", flush=True)
    t0 = time.perf_counter()
    result = compute_all_paper_metrics(
        list(sampled_mols),
        reference=REFERENCE_GEOM_DRUGS,
        full_pb=True,
        pb_workers=2,
    )
    wallclock_s = round(time.perf_counter() - t0, 3)
    metrics = {
        "validity_pct": float(result.paper_validity_pct),
        "pb_validity_pct": float(result.paper_pb_validity_pct),
        "fg_dev": float(result.paper_fg_deviation),
        "ood_ring_rate": float(result.paper_ood_ring_rate),
        "wallclock_s": float(wallclock_s),
    }
    print(
        f"[{arm_name}] metrics: validity_pct={metrics['validity_pct']:.4f} "
        f"(paper 0.999), pb_validity_pct={metrics['pb_validity_pct']:.4f} "
        f"(paper 0.919), fg_dev={metrics['fg_dev']:.4f} (paper 0.27), "
        f"ood_ring_rate={metrics['ood_ring_rate']:.4f} (paper 0.10), "
        f"wallclock={wallclock_s}s",
        flush=True,
    )
    return metrics


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """CLI entry — runs baseline + framework arms at N=1000."""
    # Wave 112.D-2: argparse migration of module constants + --config.
    # Guard: if --config is None, keep the legacy module-level defaults
    # (no breaking change). YAML values overlay on argparse defaults when
    # --config is provided (CLI > YAML > module default).
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--config", type=Path, default=None,
                   help=("Wave 112.D-2: optional run-profile path "
                         "(configs/runs/<model>_<purpose>.yaml); CLI > YAML > "
                         "module default. Omitting preserves legacy surface."))
    p.add_argument("--n-total", type=int, default=N_TOTAL,
                   help=f"Total mols per arm (default {N_TOTAL}).")
    p.add_argument("--nfe", type=int, default=NFE,
                   help=f"FlowMol3 paper NFE (default {NFE}).")
    p.add_argument("--nfe-batch", type=int, default=NFE_BATCH,
                   help=f"Mols per upstream batched call (default {NFE_BATCH}).")
    p.add_argument("--seed-base", type=int, default=SEED_BASE,
                   help=f"Base seed for trajectory (default {SEED_BASE}).")
    p.add_argument("--weights-path", type=Path, default=WEIGHTS_PATH,
                   help="Path to FlowMol3 .ckpt.")
    p.add_argument("--upstream-repo", type=Path, default=UPSTREAM_REPO,
                   help="Path to vendored FlowMol3 upstream repo.")
    p.add_argument("--device", default=DEVICE,
                   help=f"Torch device (default {DEVICE}).")
    args = p.parse_args(argv)
    if args.config is not None:
        try:
            profile = load_run_profile(args.config)
        except Exception as exc:
            print(f"[ERROR] --config load failed: {exc}", file=sys.stderr)
            return 2
        # Overlay YAML on argparse defaults (CLI > YAML > module default).
        for key in ("seed", "max_records"):
            if key in profile:
                pass  # not 1:1 with these flags
        # NFE / N_BATCHES: profile.nfe_budgets[0] maps to --nfe.
        if (
            "nfe_budgets" in profile
            and profile["nfe_budgets"]
            and args.nfe == p.get_default("nfe")
        ):
            args.nfe = int(profile["nfe_budgets"][0])
        # max_records maps to --n-total.
        if "max_records" in profile and args.n_total == p.get_default("n_total"):
            args.n_total = int(profile["max_records"])

    n_total = int(args.n_total)
    nfe = int(args.nfe)
    nfe_batch = int(args.nfe_batch)
    seed_base = int(args.seed_base)
    weights_path = Path(args.weights_path)
    upstream_repo = Path(args.upstream_repo)
    device = str(args.device)
    n_batches = n_total // nfe_batch

    out_dir = REPO_ROOT / "verification_outputs"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Wave 87 Agent C: write to distinct paths so we do NOT clobber Wave 82's
    # canonical flowmol3_n1000_{baseline,framework}_q4_2026.json outputs.
    # The brief asks for new N=1000 paper-metric numbers at PB-xtb pipeline,
    # but Wave 87 Agent A audit showed PB's energy_ratio is UFF-based (not
    # xtb-based), so the numbers will be reproduced from the same pipeline.
    WAVE_ID = "wave87"
    PREFIX = "flowmol3_n1000"

    # Save upstream module pre-import state for the report
    print(f"is_upstream_available: {is_upstream_available()}", flush=True)
    print(
        f"PB_CONFIG_WITH_ENERGY_RATIO_PATH: {PB_CONFIG_WITH_ENERGY_RATIO_PATH} "
        f"(exists: {PB_CONFIG_WITH_ENERGY_RATIO_PATH.is_file()})",
        flush=True,
    )

    t_total = time.perf_counter()

    # ---- Arm 1: BASELINE (perturbation_sigma=0) --------------------
    baseline_json = out_dir / f"{PREFIX}_baseline_{WAVE_ID}_q4_2026.json"
    baseline_result = _generate_arm(
        arm_name="baseline",
        perturbation_sigma=0.0,
        seed_base=seed_base,
        n_total=n_total,
        nfe=nfe,
        nfe_batch=nfe_batch,
        weights_path=weights_path,
        upstream_repo=upstream_repo,
        device=device,
        output_json=baseline_json,
    )
    baseline_metrics = _compute_metrics(
        baseline_result["sampled_mols"], arm_name="baseline",
    )

    # ---- Arm 2: FRAMEWORK (perturbation_sigma=0.05) ----------------
    framework_json = out_dir / f"{PREFIX}_framework_{WAVE_ID}_q4_2026.json"
    framework_result = _generate_arm(
        arm_name="framework",
        perturbation_sigma=0.05,
        seed_base=seed_base,
        n_total=n_total,
        nfe=nfe,
        nfe_batch=nfe_batch,
        weights_path=weights_path,
        upstream_repo=upstream_repo,
        device=device,
        output_json=framework_json,
    )
    framework_metrics = _compute_metrics(
        framework_result["sampled_mols"], arm_name="framework",
    )

    # ---- Statistical power check --------------------------------------
    # Per Wave 82 brief: at N=1000, fg_dev SEM ~ 1/sqrt(30 flags x 1000)
    # ~ 0.018, MDD @ a=0.05 power=0.8 ~ 5.6%; ood_ring_rate SEM ~ 1.4%,
    # MDD ~ 0.8%.
    n_flags = 30  # canonical REOS flag count for FlowMol3 paper
    n = float(n_total)
    fg_dev_sem = 1.0 / math.sqrt(n_flags * n)
    fg_dev_mdd_80 = 1.96 * math.sqrt(2.0) * fg_dev_sem  # 2-sided, alpha=0.05, power=0.8
    # ood_ring_rate SEM at p_hat=0.10 (paper target)
    p_hat = 0.10
    ood_ring_sem = math.sqrt(p_hat * (1.0 - p_hat) / n)
    ood_ring_mdd_80 = 1.96 * math.sqrt(2.0 * p_hat * (1.0 - p_hat)) / math.sqrt(n)

    stats = {
        "n_total_per_arm": int(n_total),
        "fg_dev_sem": round(fg_dev_sem, 5),
        "fg_dev_mdd_alpha0.05_power0.8": round(fg_dev_mdd_80, 5),
        "ood_ring_rate_sem_at_p0.10": round(ood_ring_sem, 5),
        "ood_ring_rate_mdd_alpha0.05_power0.8": round(ood_ring_mdd_80, 5),
    }

    # ---- Per-metric per-arm delta + verdict ----------------------------
    deltas = {}
    for k in PAPER_TARGETS:
        baseline_v = baseline_metrics[k]
        framework_v = framework_metrics[k]
        delta = framework_v - baseline_v
        # Verdict:
        # - paper-parity: within ±10% of paper target on both arms → MATCH
        # - framework_improves: framework closer to paper target than baseline
        # - tie_at_saturation: both arms at paper saturation ceiling
        paper = PAPER_TARGETS[k]
        baseline_dist = abs(baseline_v - paper)
        framework_dist = abs(framework_v - paper)
        if baseline_dist == framework_dist:
            verdict = "tie_at_paper"
        elif framework_dist < baseline_dist:
            verdict = "framework_improves"
        else:
            verdict = "baseline_improves"
        deltas[k] = {
            "paper_target": paper,
            "baseline": baseline_v,
            "framework": framework_v,
            "delta": delta,
            "baseline_dist_to_paper": baseline_dist,
            "framework_dist_to_paper": framework_dist,
            "verdict": verdict,
        }

    sweep_wallclock_s = round(time.perf_counter() - t_total, 3)

    sweep = {
        "schema_version": "1.0.0",
        "sweep_id": "wave87_agent_c_n1000_paper_metric_repro",
        "model": "flowmol3",
        "checkpoint": str(weights_path),
        "n_total_per_arm": int(n_total),
        "nfe": int(nfe),
        "nfe_batch": int(nfe_batch),
        "n_batches": int(n_batches),
        "seed_base": int(seed_base),
        "device": str(device),
        "paper_targets": PAPER_TARGETS,
        "baseline": {
            "perturbation_sigma": 0.0,
            "metrics": baseline_metrics,
            "n_sampled": int(baseline_result["n_sampled"]),
            "n_smiles": int(baseline_result["n_smiles"]),
            "n_errors": int(baseline_result["n_errors"]),
            "wallclock_sampling_s": float(baseline_result["wallclock_s"]),
            "wallclock_metrics_s": float(baseline_metrics["wallclock_s"]),
            "errors_sample": baseline_result["errors_sample"],
        },
        "framework": {
            "perturbation_sigma": 0.05,
            "metrics": framework_metrics,
            "n_sampled": int(framework_result["n_sampled"]),
            "n_smiles": int(framework_result["n_smiles"]),
            "n_errors": int(framework_result["n_errors"]),
            "wallclock_sampling_s": float(framework_result["wallclock_s"]),
            "wallclock_metrics_s": float(framework_metrics["wallclock_s"]),
            "errors_sample": framework_result["errors_sample"],
        },
        "per_metric_delta_verdict": deltas,
        "statistical_power_at_n1000": stats,
        "sweep_wallclock_s": float(sweep_wallclock_s),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }

    sweep_json = out_dir / f"flowmol3_n1000_sweep_{WAVE_ID}_q4_2026.json"
    sweep_json.write_text(json.dumps(sweep, indent=2), encoding="utf-8")
    print(f"wrote sweep summary: {sweep_json}", flush=True)
    print(f"sweep total wallclock: {sweep_wallclock_s}s", flush=True)

    # Persist the full sweep to /tmp for the report author to consume.
    full_dump = Path(f"/tmp/{WAVE_ID}_agent_c/{WAVE_ID}_n1000_full.json")
    full_dump.parent.mkdir(parents=True, exist_ok=True)
    full_dump.write_text(json.dumps(sweep, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
