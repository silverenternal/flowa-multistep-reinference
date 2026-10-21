"""GAP-64b: does the R5c cell have any NFE headroom?

The R5c (MNIST-FM projection-FID) cell regresses under *every* recorded
framework configuration (see ``tools/gap64_r5c_census.py``). Before that is
read as "the framework degrades a good model", this probe asks the prior
question: **is the single-pass baseline actually NFE-limited on this cell?**

If the baseline FID is already flat in NFE, then there is no integration
error for a restart mechanism to recover, and the measured ``delta%`` is
purely the *cost* of the restart perturbation — the cell cannot discriminate
sampler efficiency at all.

Design
------
* Baseline only (no framework arms), single pass, ``shared_prior`` so the
  prior ``x0`` is byte-identical across every NFE rung (paired ladder).
* ``NFE in {3, 5, 10, 25, 50, 100}`` x ``ckpt in {production, w16e1_5k}``.
* N=200 (screen), seed 42. Headline FID uses the full 10k reference.

Output: ``<out>/headroom.json`` + a markdown table on stdout.
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

from adaptive_reflow.adapters.mnist_fm import MnistFmAdapter  # noqa: E402
from adaptive_reflow.eval.mnist_fid import MnistFrechetProjectionEvaluator  # noqa: E402

sys.path.insert(0, str(_REPO_ROOT / "scripts"))
from wave191_p3_mnist_sweep import run_baseline, score_population  # noqa: E402

DEFAULT_CKPTS = (
    Path("data/mnist_fm/production.ckpt.npz"),
    Path("data/mnist_fm/w16e1_5k.ckpt.npz"),
)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ckpts", nargs="+", type=Path, default=list(DEFAULT_CKPTS))
    ap.add_argument("--nfe-ladder", nargs="+", type=int, default=[3, 5, 10, 25, 50, 100])
    ap.add_argument("--n-samples", type=int, default=200)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--cache-dir", type=Path, default=_REPO_ROOT / "data" / "mnist_fm_train_cache")
    ap.add_argument("--out", type=Path,
                    default=_REPO_ROOT / "verification_outputs" / "gap64b-nfe-headroom")
    args = ap.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)

    evaluator = MnistFrechetProjectionEvaluator(cache_dir=Path(args.cache_dir))
    ref_features = evaluator._ref_features
    projection = evaluator._projection

    results: dict[str, dict[str, float]] = {}
    for ckpt in args.ckpts:
        path = ckpt if ckpt.is_absolute() else (_REPO_ROOT / ckpt)
        if not path.exists():
            raise SystemExit(f"checkpoint_not_found:{path}")
        key = path.stem.replace(".ckpt", "")
        results[key] = {}
        for nfe in args.nfe_ladder:
            adapter = MnistFmAdapter(weights_path=str(path), num_steps=int(nfe))
            t0 = time.perf_counter()
            samples = run_baseline(
                adapter=adapter,
                n_samples=int(args.n_samples),
                seed=int(args.seed),
                verbose=False,
                shared_prior=True,
                num_steps=int(nfe),
            )
            fid = score_population(samples, ref_features, projection)
            results[key][str(nfe)] = float(fid)
            print(f"[headroom] {key:12s} nfe={nfe:4d} fid={fid:8.4f} "
                  f"({time.perf_counter() - t0:.1f}s)", flush=True)

    # Headroom = how much the FID still moves between the cheapest and the
    # most expensive rung. A flat ladder means the cell is NFE-saturated.
    print()
    print("| ckpt | " + " | ".join(f"NFE={n}" for n in args.nfe_ladder) + " | headroom |")
    print("|---|" + "|".join(["---:"] * (len(args.nfe_ladder) + 1)) + "|")
    summary: dict[str, dict[str, float]] = {}
    for key, row in results.items():
        vals = [row[str(n)] for n in args.nfe_ladder]
        headroom = (vals[0] - vals[-1]) / vals[-1] * 100.0
        summary[key] = {"fid": row, "headroom_pct": float(headroom)}
        print(f"| {key} | " + " | ".join(f"{v:.3f}" for v in vals) +
              f" | {headroom:+.2f}% |")

    (args.out / "headroom.json").write_text(json.dumps({
        "n_samples": int(args.n_samples),
        "seed": int(args.seed),
        "nfe_ladder": [int(n) for n in args.nfe_ladder],
        "shared_prior": True,
        "results": summary,
    }, indent=1))
    print(f"\nwrote {args.out / 'headroom.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
