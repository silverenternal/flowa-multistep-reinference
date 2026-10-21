"""GAP-67: does restoring the restart blend's second moment remove the R5c cost?

Mechanism under test (``docs/audit/gap67-covariance-preservation.md`` §1).
The restart writes the path state at ``t = m`` as

    y = m * x1_hat + (1 - m) * x0_fresh

which is under-dispersed by ``m^2 (v_base - v_hat)`` relative to the model's own
dispersion. Scaling the fresh noise by ``c`` restores it:

    c^2 = 1 + m^2 (v_base - v_hat) / (1 - m)^2

This tool re-runs ONE framework arm at ONE scale and reports

  * ``rho`` in the FID projection space (the GAP-64 quantity),
  * the pixel-space variance ratio (to check the contraction is isotropic),
  * the paired chunk-level FID delta against a reused baseline.

The baseline is NOT re-sampled: RK4 is deterministic and ``shared_prior`` makes
round 0 byte-identical, so ``baseline_samples.npz`` from the frozen
``gap57-equal-nfe-ladder-n1000`` run is the correct pairing partner.

Reads only existing artifacts for the baseline; needs one GPU (or CPU) pass for
the arm.

Example
-------
    python tools/gap67_noise_scale_screen.py \
        --ckpt data/mnist_fm/w16e1_5k.ckpt.npz \
        --baseline-npz verification_outputs/gap57-equal-nfe-ladder-n1000/w16e1_5k_s42/baseline_samples.npz \
        --scale 1.0599 \
        --out verification_outputs/gap67-noise-scale/w16e1_5k_c10599.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from adaptive_reflow.eval.mnist_fid import MnistFrechetProjectionEvaluator  # noqa: E402
from scripts.wave191_p3_mnist_sweep import (  # noqa: E402
    K_CHUNKS,
    paired_ttest,
    per_round_num_steps_equal_budget,
    restart_t0_per_round,
    run_framework_arm,
    score_population,
)

ARM = "cosine"
BETA = 0.5
N_ROUNDS = 4
TOTAL_NFE = 50
SEED = 42


def _load_npz(path: Path) -> np.ndarray:
    with np.load(path) as z:
        key = "samples" if "samples" in z.files else z.files[0]
        return np.asarray(z[key], dtype=np.float64)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ckpt", type=Path, required=True)
    ap.add_argument("--baseline-npz", type=Path, required=True)
    ap.add_argument("--scale", type=float, required=True,
                    help="restart noise scale c (1.0 = the frozen convex blend)")
    ap.add_argument("--label", default=None)
    ap.add_argument("--n-samples", type=int, default=1000)
    ap.add_argument("--cache-dir", type=Path,
                    default=_REPO_ROOT / "data" / "mnist_fm_train_cache")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    label = args.label or args.ckpt.stem.replace(".ckpt", "")
    ckpt = args.ckpt if args.ckpt.is_absolute() else (_REPO_ROOT / args.ckpt).resolve()
    baseline = _load_npz(args.baseline_npz if args.baseline_npz.is_absolute()
                         else _REPO_ROOT / args.baseline_npz)
    if baseline.shape[0] != args.n_samples:
        raise SystemExit(f"baseline_n_mismatch:{baseline.shape[0]}!={args.n_samples}")

    ev = MnistFrechetProjectionEvaluator(cache_dir=Path(args.cache_dir))
    ref = ev._ref_features
    projection = ev._projection
    tr_ref = float(np.trace(np.cov(ref, rowvar=False)))

    t0_per_round = restart_t0_per_round(BETA, N_ROUNDS, "equal_budget", "memory")
    interval_lengths = [1.0 - float(t) for t in t0_per_round]
    num_steps = per_round_num_steps_equal_budget(
        ARM, N_ROUNDS, TOTAL_NFE, allocation="scheduler",
        interval_lengths=interval_lengths,
    )

    if not args.quiet:
        t0_str = ", ".join(f"{t:.3f}" for t in t0_per_round)
        print(f"[gap67] {label} scale={args.scale:.4f} NFE/round={num_steps} "
              f"t0=[{t0_str}]", flush=True)
    t_start = time.perf_counter()
    samples, tel = run_framework_arm(
        arm_name=ARM,
        cycle_length=N_ROUNDS,
        n_samples=int(args.n_samples),
        num_steps_per_round=num_steps,
        seed_offset=int(SEED),
        beta=BETA,
        weights_path=ckpt,
        verbose=not args.quiet,
        shared_prior=True,
        beta_schedule="equal_budget",
        restart_t0_mode="memory",
        batch_suffix=f"-s{SEED}",
        restart_noise_scale=float(args.scale),
    )
    wall = time.perf_counter() - t_start

    # --- dispersion -------------------------------------------------------
    feats = samples @ projection
    rho = float(np.trace(np.cov(feats, rowvar=False))) / tr_ref
    rho_base = float(np.trace(np.cov(baseline @ projection, rowvar=False))) / tr_ref
    v_gen = float(samples.var(axis=0).mean())
    v_base = float(baseline.var(axis=0).mean())

    # --- paired chunk FID ------------------------------------------------
    chunk = int(args.n_samples) // int(K_CHUNKS)
    rng = np.random.default_rng(int(SEED) + 99)
    ref_perm = rng.permutation(ref.shape[0])
    base_fids: list[float] = []
    arm_fids: list[float] = []
    for k in range(int(K_CHUNKS)):
        ref_chunk = ref[ref_perm[k * chunk:(k + 1) * chunk]]
        base_fids.append(score_population(
            baseline[k * chunk:(k + 1) * chunk], ref_chunk, projection))
        arm_fids.append(score_population(
            samples[k * chunk:(k + 1) * chunk], ref_chunk, projection))
    base_arr = np.asarray(base_fids, dtype=np.float64)
    arm_arr = np.asarray(arm_fids, dtype=np.float64)
    diff = arm_arr - base_arr
    t_stat, df, p_raw = paired_ttest(diff)
    delta_pct = float((arm_arr.mean() - base_arr.mean()) / base_arr.mean() * 100.0)

    headline_base = score_population(baseline, ref, projection)
    headline_arm = score_population(samples, ref, projection)

    out = {
        "label": label,
        "checkpoint": str(ckpt.relative_to(_REPO_ROOT)),
        "arm": ARM,
        "restart_noise_scale": float(args.scale),
        "n_samples": int(args.n_samples),
        "total_nfe": TOTAL_NFE,
        "per_round_num_steps": num_steps,
        "restart_t0_per_round": t0_per_round,
        "beta": BETA,
        "seed": SEED,
        "rho": rho,
        "rho_base": rho_base,
        "rho_ratio": rho / rho_base if rho_base else float("nan"),
        "pixel_var": v_gen,
        "pixel_var_base": v_base,
        "pixel_var_ratio": v_gen / v_base if v_base else float("nan"),
        "fid_headline": headline_arm,
        "fid_headline_base": headline_base,
        "fid_chunks_arm": arm_fids,
        "fid_chunks_base": base_fids,
        "delta_vs_baseline_pct": delta_pct,
        "p_value_raw": p_raw,
        "p_value_bonferroni_3arm": min(float(p_raw) * 3.0, 1.0),
        "t_stat": t_stat,
        "df": int(df),
        "wall_sec": wall,
        "telemetry": tel,
    }
    print(f"[gap67] {label} c={args.scale:.4f} rho={rho:.4f} "
          f"rho_base={rho_base:.4f} ratio={out['rho_ratio']:.4f} "
          f"FID={headline_arm:.4f} (base {headline_base:.4f}) "
          f"delta={delta_pct:+.2f}% p_bonf={out['p_value_bonferroni_3arm']:.3g} "
          f"wall={wall:.0f}s", flush=True)

    if args.out is not None:
        out_path = args.out if args.out.is_absolute() else _REPO_ROOT / args.out
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out, indent=1))
        print(f"[gap67] wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
