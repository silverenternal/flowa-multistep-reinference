"""GAP-56: where does the single-pass baseline reach its FID floor?

Sweeps the Euler step count of the *baseline* arm only and reports FID plus
its two Fréchet components (mean bias and covariance trace). The point is to
find the NFE below which the baseline is no longer at the model's floor —
that is the only regime in which a sampler-side mechanism can be measured.

Usage
-----
    OMP_NUM_THREADS=1 python3 tools/gap56_nfe_floor.py \
        --nfe 1 2 3 5 8 10 15 20 25 50 --n 200 \
        --out verification_outputs/gap56-r5c-memory-t0/nfe_floor.json
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

from adaptive_reflow.adapters.mnist_fm import MNIST_FM_FLAT_DIM, MnistFmAdapter  # noqa: E402
from adaptive_reflow.eval.mnist_fid import (  # noqa: E402
    MnistFrechetProjectionEvaluator,
    _frechet_distance,
)
from adaptive_reflow.universal.state import ODEConditionDelta  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--nfe", type=int, nargs="+",
                    default=[1, 2, 3, 5, 8, 10, 15, 20, 25, 50])
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--ckpt", type=Path,
                    default=REPO_ROOT / "data" / "mnist_fm" / "production.ckpt.npz")
    ap.add_argument("--cache-dir", type=Path,
                    default=REPO_ROOT / "data" / "mnist_fm_train_cache")
    ap.add_argument("--batch-id", default="gap56-nfe-floor")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    ev = MnistFrechetProjectionEvaluator(cache_dir=Path(args.cache_dir))
    ref = np.asarray(ev._ref_features, dtype=np.float64)  # noqa: SLF001
    proj = np.asarray(ev._projection, dtype=np.float64)  # noqa: SLF001
    ref_mu = ref.mean(axis=0)

    rows: list[dict[str, float]] = []
    print(f"{'NFE':>4}{'FID':>10}{'Tr(S)':>10}{'bias':>9}")
    for nfe in args.nfe:
        ad = MnistFmAdapter(
            weights_path=str(args.ckpt), integrator="euler", num_steps=int(nfe),
        )
        xs = np.empty((int(args.n), MNIST_FM_FLAT_DIM), dtype=np.float64)
        for i in range(int(args.n)):
            bundle = ad.build_initial_state(
                batch_id=str(args.batch_id), sample_id=f"s{i:05d}",
            )
            cond = ODEConditionDelta(
                delta_spec={"t0": 0.0, "t1": 1.0, "num_steps": int(nfe)},
                source="gap56_nfe_floor",
                target_round=0,
                calibration_artifact_hash="cal-gap56-nfe-floor",
            )
            trace = ad.solve_ode(bundle, cond, seed=int(args.seed) + i)
            endpoint = ad.observe_endpoint(trace, bundle)
            xs[i] = np.asarray(
                ad._native_states[endpoint.native_state_digest]["x0"],  # noqa: SLF001
                dtype=np.float64,
            ).reshape(MNIST_FM_FLAT_DIM)
        feats = xs @ proj
        mu = feats.mean(axis=0)
        cov = np.cov(feats, rowvar=False)
        fid = float(_frechet_distance(feats, ref))
        rows.append({
            "nfe": int(nfe),
            "fid": fid,
            "trace_cov": float(np.trace(cov)),
            "bias": float((mu - ref_mu) @ (mu - ref_mu)),
        })
        print(f"{nfe:>4}{fid:>10.4f}{np.trace(cov):>10.3f}"
              f"{(mu - ref_mu) @ (mu - ref_mu):>9.3f}", flush=True)

    payload = {
        "checkpoint": str(args.ckpt),
        "n": int(args.n),
        "seed": int(args.seed),
        "batch_id": str(args.batch_id),
        "integrator": "euler",
        "reference": "mnist_fm_train_cache (10k projected features)",
        "rows": rows,
    }
    if args.out is not None:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=2) + "\n")
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
