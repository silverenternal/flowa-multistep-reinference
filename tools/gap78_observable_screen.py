#!/usr/bin/env python3
"""GAP-78 — can any reference-free observable gate the restart? (offline screen)

Pre-registration: ``docs/audit/gap78-dispersion-gate.md`` §0.

Reads only recorded ``baseline_samples.npz`` artifacts — no GPU, no sampling.
For each checkpoint it computes the candidate gate observables from the model's
**own** samples (no reference data), and then asks two different questions:

* **Q1 (rho proxy)** — does the observable order the four measured baseline
  ``rho`` values the same way? This is the question the pre-registration named.
* **Q2 (decision)** — does the observable separate the checkpoints the
  framework *wins* from the ones it *loses*, with a single threshold?

Q2 is reported but **is not admissible evidence on its own**: with four
checkpoints any statistic that is monotone in model quality separates them, and
GAP-67 §6.2 already showed that this cross-section is confounded by the same
latent variable. The tool prints that warning next to the result so the number
cannot be quoted without it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from adaptive_reflow.eval.mnist_fid import MnistFrechetProjectionEvaluator  # noqa: E402

DEFAULT_CACHE = _REPO_ROOT / "data" / "mnist_fm_train_cache"
PAIR_SUBSAMPLE = 400
NN_SUBSAMPLE = 300


def _load_samples(path: Path) -> np.ndarray:
    with np.load(path) as z:
        key = "samples" if "samples" in z.files else z.files[0]
        return np.asarray(z[key], dtype=np.float64)


def observables(feats: np.ndarray, mu_ref: np.ndarray, tr_ref: float,
                *, seed: int = 0) -> dict[str, float]:
    """Reference-free statistics of one sample cloud (``feats`` is N x d)."""
    cov = np.cov(feats, rowvar=False)
    lam = np.clip(np.linalg.eigvalsh(cov), 0.0, None)
    tr = float(lam.sum())

    rng = np.random.default_rng(seed)
    i = rng.integers(0, len(feats), PAIR_SUBSAMPLE)
    j = rng.integers(0, len(feats), PAIR_SUBSAMPLE)
    mpd = float(np.linalg.norm(feats[i] - feats[j], axis=1).mean())

    idx = rng.choice(len(feats), min(NN_SUBSAMPLE, len(feats)), replace=False)
    sub = feats[idx]
    d = np.linalg.norm(sub[:, None, :] - sub[None, :, :], axis=2)
    np.fill_diagonal(d, np.inf)

    return {
        # the two quantities GAP-64c already recorded, for continuity
        "rho": tr / tr_ref,
        "mean_shift": float(np.linalg.norm(feats.mean(0) - mu_ref)),
        # reference-free candidates
        "participation_ratio": float(tr**2 / (lam**2).sum()),
        "mean_nn_dist": float(d.min(1).mean()),
        "mean_pair_dist": mpd,
        "mean_norm": float(np.linalg.norm(feats.mean(0))),
    }


def separates(outcomes: dict[str, str], values: dict[str, float]) -> dict[str, Any]:
    """Is there a single threshold putting every WIN on one side of every LOSS?

    Returns the separating interval (if any) and the direction. A separation on
    four points is necessary, never sufficient (§3 of the audit).
    """
    wins = [values[k] for k, v in outcomes.items() if v == "WIN"]
    losses = [values[k] for k, v in outcomes.items() if v == "LOSS"]
    if not wins or not losses:
        return {"separates": False, "reason": "need at least one WIN and one LOSS"}
    if max(losses) < min(wins):
        return {"separates": True, "direction": "higher_wins",
                "threshold_in": [max(losses), min(wins)]}
    if min(losses) > max(wins):
        return {"separates": True, "direction": "lower_wins",
                "threshold_in": [max(wins), min(losses)]}
    return {"separates": False, "direction": None, "threshold_in": None}


def _kendall_tau(a: list[float], b: list[float]) -> float:
    """Kendall tau-a on two equally long sequences (a tie contributes 0)."""
    n = len(a)
    if n < 2:
        return float("nan")
    num = 0.0
    for i in range(n):
        for j in range(i + 1, n):
            da = np.sign(a[i] - a[j])
            db = np.sign(b[i] - b[j])
            num += 1.0 if da * db > 0 else (-1.0 if da * db < 0 else 0.0)
    return num / (n * (n - 1) / 2)


def screen(runs: dict[str, Path], outcomes: dict[str, str], rho_ref: dict[str, float],
           *, fw_runs: dict[str, Path] | None = None,
           cache_dir: Path = DEFAULT_CACHE, seed: int = 0) -> dict[str, Any]:
    ev = MnistFrechetProjectionEvaluator(cache_dir=Path(cache_dir))
    projection = ev._projection
    ref = ev._ref_features
    mu_ref = ref.mean(0)
    tr_ref = float(np.trace(np.cov(ref, rowvar=False)))

    per_ckpt: dict[str, dict[str, float]] = {}
    for label, path in runs.items():
        feats = _load_samples(Path(path)) @ projection
        per_ckpt[label] = observables(feats, mu_ref, tr_ref, seed=seed)

    if fw_runs:
        # kappa: the realised contraction of the restart, tr(Sigma_fw)/tr(Sigma_base).
        # This is the Monte-Carlo variance the R rounds average out, and it is
        # measurable at inference time without any reference data.
        absent = [k for k in runs if k not in fw_runs]
        if absent:
            raise ValueError(f"--framework-runs is missing: {absent}")
        for label, path in fw_runs.items():
            feats = _load_samples(Path(path)) @ projection
            lam = np.clip(np.linalg.eigvalsh(np.cov(feats, rowvar=False)), 0.0, None)
            tr_fw = float(lam.sum())
            per_ckpt[label]["contraction"] = tr_fw / (tr_ref * per_ckpt[label]["rho"])

    labels = list(runs)
    rho_known = [rho_ref[k] for k in labels]
    keys = list(next(iter(per_ckpt.values())).keys())

    q1: dict[str, Any] = {}
    q2: dict[str, Any] = {}
    for key in keys:
        vals = [per_ckpt[k][key] for k in labels]
        q1[key] = {"kendall_tau_vs_rho": _kendall_tau(vals, rho_known)}
        q2[key] = separates(outcomes, {k: per_ckpt[k][key] for k in labels})

    return {
        "schema": "gap78_observable_screen_v1",
        "labels": labels,
        "outcomes": outcomes,
        "per_checkpoint": per_ckpt,
        "q1_orders_rho": q1,
        "q2_separates_outcome": q2,
        "caveat": (
            "Q2 separates on n=4 and is CONFOUNDED: any statistic monotone in "
            "model quality separates these checkpoints (GAP-67 §6.2). Only a "
            "within-checkpoint dose-response can identify a gate."
        ),
    }


def render(rep: dict[str, Any]) -> str:
    labels = rep["labels"]
    keys = list(rep["per_checkpoint"][labels[0]].keys())
    head = "| observable | " + " | ".join(labels) + " | Q1 tau(rho) | Q2 sep |"
    lines = [head, "|---|" + "---:|" * len(labels) + "---:|:--:|"]
    for key in keys:
        cells = " | ".join(f"{rep['per_checkpoint'][k][key]:.4f}" for k in labels)
        tau = rep["q1_orders_rho"][key]["kendall_tau_vs_rho"]
        sep = rep["q2_separates_outcome"][key]
        sep_txt = (f"yes ({sep['direction']})" if sep["separates"]
                   else "no")
        lines.append(f"| `{key}` | {cells} | {tau:+.2f} | {sep_txt} |")
    lines += ["", f"outcomes: {rep['outcomes']}", "", f"CAVEAT: {rep['caveat']}"]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", nargs="+", required=True,
                    help="LABEL:PATH pairs to baseline_samples.npz")
    ap.add_argument("--outcomes", type=Path, required=True,
                    help='JSON {"ckpt": "WIN"|"LOSS"} from the GAP-76 grid')
    ap.add_argument("--framework-runs", nargs="*", default=None,
                    help="LABEL:PATH pairs to the framework arm's samples; adds "
                         "`contraction` = tr(Sigma_fw)/tr(Sigma_base)")
    ap.add_argument("--rho", type=Path, required=True,
                    help="gap64c dispersion.json (measured baseline rho)")
    ap.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    runs: dict[str, Path] = {}
    for spec in args.runs:
        label, _, path = spec.partition(":")
        if not path:
            print(f"bad --runs entry {spec!r}: expected LABEL:PATH", file=sys.stderr)
            return 2
        runs[label] = Path(path)

    outcomes = json.loads(args.outcomes.read_text())
    disp = json.loads(args.rho.read_text())
    rho_ref = {r["label"]: float(r["rho"]) for r in disp["rows"] if r["arm"] == "baseline"}
    missing = [k for k in runs if k not in outcomes or k not in rho_ref]
    if missing:
        print(f"missing outcome or rho for: {missing}", file=sys.stderr)
        return 2

    fw_runs: dict[str, Path] | None = None
    if args.framework_runs:
        fw_runs = {}
        for spec in args.framework_runs:
            label, _, path = spec.partition(":")
            if not path:
                print(f"bad --framework-runs entry {spec!r}", file=sys.stderr)
                return 2
            fw_runs[label] = Path(path)

    rep = screen(runs, outcomes, rho_ref, fw_runs=fw_runs, cache_dir=args.cache_dir)
    print(render(rep))
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(rep, indent=1) + "\n")
        print(f"\nwrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
