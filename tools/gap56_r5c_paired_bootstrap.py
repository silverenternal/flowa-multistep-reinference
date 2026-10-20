"""GAP-56: paired record-level bootstrap on the *headline* FID.

The R5c driver reports two FID estimators:

* ``fid_headline`` — Fréchet distance between the arm's ``N`` projected
  features and the **full 10 000-image** MNIST test reference. This is the
  standard FID and the number quoted in tables.
* ``fid_chunks_mean`` — mean of ``k = 10`` chunk FIDs, each computed against
  a **20-image** reference chunk. The small reference makes this estimator
  strongly biased, and the bias depends on the arm's covariance, so the
  paired chunk test can disagree with the headline in **sign**.

This tool resolves that disagreement the correct way: keep the full
reference (unbiased FID) and bootstrap over *records*, resampling the same
indices for the baseline and the arm so the comparison stays paired. It is
the same estimator as ``fid_headline``, with a sampling distribution
attached.

Usage
-----
    python3 tools/gap56_r5c_paired_bootstrap.py \
        --run-dir verification_outputs/gap56-r5c-memory-t0/prop_eq \
        --cache-dir data/mnist_fm_train_cache \
        --out verification_outputs/gap56-r5c-memory-t0/prop_eq/paired_bootstrap.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from adaptive_reflow.adapters.mnist_fm import MNIST_FM_FLAT_DIM  # noqa: E402
from adaptive_reflow.eval.mnist_fid import (  # noqa: E402
    MnistFrechetProjectionEvaluator,
)

ARMS: tuple[str, ...] = ("cosine", "codimension_sheet", "evidence_driven")
N_BOOT: int = 2000
BOOT_SEED: int = 20261020
ALPHA_BONF: float = 0.05 / len(ARMS)


def _stats(feats: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return np.mean(feats, axis=0), np.cov(feats, rowvar=False)


def _fid_from_stats(
    mu_a: np.ndarray, sigma_a: np.ndarray, mu_b: np.ndarray, sigma_b: np.ndarray,
) -> float:
    """Fréchet distance from pre-computed moments (same formula as upstream)."""
    from scipy.linalg import sqrtm as _sqrtm

    diff = mu_a - mu_b
    covmean = _sqrtm(sigma_a @ sigma_b)
    if np.iscomplexobj(covmean):
        covmean = np.real(covmean)
    return float(
        diff @ diff
        + np.trace(sigma_a)
        + np.trace(sigma_b)
        - 2.0 * np.trace(covmean)
    )


def _load(run_dir: Path, arm: str) -> np.ndarray:
    path = run_dir / f"{arm}_samples.npz"
    with np.load(path) as z:
        key = "samples" if "samples" in z else z.files[0]
        arr = np.asarray(z[key], dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] != MNIST_FM_FLAT_DIM:
        raise ValueError(f"{path}: expected (N, {MNIST_FM_FLAT_DIM}), got {arr.shape}")
    return arr


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-dir", type=Path, required=True)
    ap.add_argument("--cache-dir", type=Path, default=REPO_ROOT / "data" / "mnist_fm_train_cache")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--n-boot", type=int, default=N_BOOT)
    ap.add_argument("--boot-seed", type=int, default=BOOT_SEED)
    args = ap.parse_args(argv)

    evaluator = MnistFrechetProjectionEvaluator(cache_dir=Path(args.cache_dir))
    ref = np.asarray(evaluator._ref_features, dtype=np.float64)  # noqa: SLF001
    proj = np.asarray(evaluator._projection, dtype=np.float64)  # noqa: SLF001

    base_samples = _load(Path(args.run_dir), "baseline")
    n = int(base_samples.shape[0])
    base_feats = base_samples @ proj
    ref_mu, ref_sigma = _stats(ref)

    out: dict[str, object] = {
        "run_dir": str(Path(args.run_dir)),
        "n_records": n,
        "n_boot": int(args.n_boot),
        "boot_seed": int(args.boot_seed),
        "alpha_bonferroni": float(ALPHA_BONF),
        "estimator": "fid_headline (full 10k reference) with record-level paired bootstrap",
        "arms": {},
    }

    rng = np.random.default_rng(int(args.boot_seed))
    idx_all = rng.integers(0, n, size=(int(args.n_boot), n))

    for arm in ARMS:
        samples = _load(Path(args.run_dir), arm)
        if samples.shape[0] != n:
            raise ValueError(f"{arm}: {samples.shape[0]} samples vs baseline {n}")
        feats = samples @ proj
        b_mu, b_sigma = _stats(base_feats)
        a_mu, a_sigma = _stats(feats)
        fid_base = _fid_from_stats(b_mu, b_sigma, ref_mu, ref_sigma)
        fid_arm = _fid_from_stats(a_mu, a_sigma, ref_mu, ref_sigma)
        deltas = np.empty(int(args.n_boot), dtype=np.float64)
        for b in range(int(args.n_boot)):
            idx = idx_all[b]
            bm, bs = _stats(base_feats[idx])
            am, as_ = _stats(feats[idx])
            deltas[b] = (
                _fid_from_stats(am, as_, ref_mu, ref_sigma)
                - _fid_from_stats(bm, bs, ref_mu, ref_sigma)
            )
        lo, hi = np.percentile(deltas, [2.5, 97.5])
        # two-sided bootstrap p: 2 * min(P(delta<=0), P(delta>=0)), capped at 1
        p_two = float(min(1.0, 2.0 * min((deltas <= 0.0).mean(), (deltas >= 0.0).mean())))
        p_bonf = float(min(1.0, p_two * len(ARMS)))
        out["arms"][arm] = {  # type: ignore[index]
            "fid_baseline": fid_base,
            "fid_arm": fid_arm,
            "delta": float(fid_arm - fid_base),
            "delta_pct": float((fid_arm - fid_base) / max(fid_base, 1e-12) * 100.0),
            "delta_mean_boot": float(deltas.mean()),
            "delta_ci95": [float(lo), float(hi)],
            "p_two_sided": p_two,
            "p_bonferroni": p_bonf,
            "bonferroni_significant": bool(p_bonf < ALPHA_BONF),
            "frac_boot_favouring_framework": float((deltas < 0.0).mean()),
        }

    if args.out is not None:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, indent=2) + "\n")

    print(f"{'arm':<18}{'baseline':>10}{'arm':>10}{'delta':>10}{'d%':>8}"
          f"{'CI95':>24}{'p':>10}{'p_bonf':>10}{'fav%':>8}")
    for arm in ARMS:
        r = out["arms"][arm]  # type: ignore[index]
        ci = f"[{r['delta_ci95'][0]:+.4f},{r['delta_ci95'][1]:+.4f}]"
        print(f"{arm:<18}{r['fid_baseline']:>10.4f}{r['fid_arm']:>10.4f}"
              f"{r['delta']:>+10.4f}{r['delta_pct']:>+8.2f}{ci:>24}"
              f"{r['p_two_sided']:>10.4f}{r['p_bonferroni']:>10.4f}"
              f"{r['frac_boot_favouring_framework']*100:>7.2f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
