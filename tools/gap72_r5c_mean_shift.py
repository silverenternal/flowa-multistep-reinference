"""GAP-72: what is the R5c mean shift made of?

GAP-67's Frechet decomposition (``docs/audit/gap67-covariance-preservation.md``
§2.1) showed the R5c fidelity cost is carried by the **mean** term, not the
covariance term: +0.760 of production's +0.888 FID gap, +1.480 of
``w16e1_60k``'s +1.758. Nothing has looked at the mean itself.

This tool decomposes the restart's mean shift

    delta_mu = mean(arm) - mean(baseline)

in pixel space into three orthogonal parts:

  * **DC** — the all-ones direction, i.e. a uniform brightness / ink-mass
    offset. A single scalar fixes this.
  * **ink** — the reference mean image, i.e. "the same digits, more or less
    ink everywhere". Also a single scalar fixes this.
  * **residual** — everything else, i.e. a structured shift that no global
    correction can remove.

It reports the energy fraction of each part, plus the same decomposition of the
FID mean term (``||mean(arm) - mean(ref)||^2``) so the two can be compared.

Reads only frozen ``*_samples.npz``. No GPU.

Example
-------
    python tools/gap72_r5c_mean_shift.py \
        --out verification_outputs/gap72-r5c-mean-shift/decomposition.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from adaptive_reflow.eval.mnist_fid import MnistFrechetProjectionEvaluator  # noqa: E402

LABELS = ("production", "w16e1_10k", "w16e1_60k", "w16e1_5k")
SEEDS = (42, 43, 44)
ARMS = ("cosine", "codimension_sheet", "evidence_driven")
ROOT = _REPO_ROOT / "verification_outputs" / "gap57-equal-nfe-ladder-n1000"


def _load(path: Path) -> np.ndarray | None:
    if not path.exists():
        return None
    with np.load(path) as z:
        key = "samples" if "samples" in z.files else z.files[0]
        return np.asarray(z[key], dtype=np.float64)


def _decompose(delta: np.ndarray, ink: np.ndarray) -> dict[str, float]:
    """Energy fractions of ``delta`` along {ones, ink} and the residual."""
    d = float(delta @ delta)
    if d <= 0.0:
        return {"total_sq": 0.0, "dc_frac": 0.0, "ink_frac": 0.0,
                "residual_frac": 0.0, "dc_signed": 0.0}
    ones = np.ones_like(delta) / np.sqrt(delta.size)
    dc_coef = float(delta @ ones)
    dc_frac = dc_coef ** 2 / d

    ink_u = np.asarray(ink, dtype=np.float64).ravel()
    ink_u = ink_u - (ink_u @ ones) * ones          # orthogonalise against DC
    nrm = float(np.linalg.norm(ink_u))
    ink_frac = 0.0
    if nrm > 1e-12:
        ink_u = ink_u / nrm
        ink_frac = float(delta @ ink_u) ** 2 / d
    return {
        "total_sq": d,
        "dc_frac": float(dc_frac),
        "ink_frac": float(ink_frac),
        "residual_frac": float(max(0.0, 1.0 - dc_frac - ink_frac)),
        "dc_signed": float(dc_coef / np.sqrt(delta.size)),
    }


def _mean(rows: list[dict], *keys: str) -> float:
    """Mean of ``rows[i][keys[0]][keys[1]]`` (or ``rows[i][keys[0]]``)."""
    vals = []
    for r in rows:
        v = r[keys[0]]
        for k in keys[1:]:
            v = v[k]
        vals.append(float(v))
    return float(np.mean(vals))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cache-dir", type=Path,
                    default=_REPO_ROOT / "data" / "mnist_fm_train_cache")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    ev = MnistFrechetProjectionEvaluator(cache_dir=Path(args.cache_dir))
    projection = np.asarray(ev._projection, dtype=np.float64)

    import scripts.wave191_p3_mnist_sweep as S
    imgs = np.asarray(
        S._load_mnist_offline(split="test", cache_dir=Path(args.cache_dir)),
        dtype=np.float64,
    )
    mu_ref_px = imgs.mean(0)
    mu_ref_proj = np.asarray(ev._ref_features, dtype=np.float64).mean(0)

    cells: list[dict] = []
    for label in LABELS:
        for arm in ARMS:
            per_seed: list[dict] = []
            for seed in SEEDS:
                d = ROOT / f"{label}_s{seed}"
                base = _load(d / "baseline_samples.npz")
                arm_s = _load(d / f"{arm}_samples.npz")
                if base is None or arm_s is None:
                    continue
                mu_b = base.mean(0)
                mu_a = arm_s.mean(0)
                shift = mu_a - mu_b                    # the restart's own shift
                vs_ref = mu_a - mu_ref_px              # what FID sees
                dec_shift = _decompose(shift, mu_ref_px)
                dec_ref = _decompose(vs_ref, mu_ref_px)
                # FID mean term in projection space, and the restart's
                # contribution to it.
                fid_mean_arm = float(np.sum((mu_a @ projection - mu_ref_proj) ** 2))
                fid_mean_base = float(np.sum((mu_b @ projection - mu_ref_proj) ** 2))
                per_seed.append({
                    "seed": int(seed),
                    "_shift_vec": shift,
                    "shift_norm": float(np.linalg.norm(shift)),
                    "shift_vs_ref_norm": float(np.linalg.norm(vs_ref)),
                    "shift_decomposition": dec_shift,
                    "vs_ref_decomposition": dec_ref,
                    "fid_mean_term_arm": fid_mean_arm,
                    "fid_mean_term_base": fid_mean_base,
                    "fid_mean_delta": fid_mean_arm - fid_mean_base,
                })
            if not per_seed:
                continue

            cell = {
                "checkpoint": label,
                "arm": arm,
                "n_seeds": len(per_seed),
                "shift_norm": _mean(per_seed, "shift_norm"),
                "shift_vs_ref_norm": _mean(per_seed, "shift_vs_ref_norm"),
                "shift_dc_frac": _mean(per_seed, "shift_decomposition", "dc_frac"),
                "shift_ink_frac": _mean(per_seed, "shift_decomposition", "ink_frac"),
                "shift_residual_frac": _mean(per_seed, "shift_decomposition", "residual_frac"),
                "shift_dc_signed": _mean(per_seed, "shift_decomposition", "dc_signed"),
                "vs_ref_dc_frac": _mean(per_seed, "vs_ref_decomposition", "dc_frac"),
                "vs_ref_ink_frac": _mean(per_seed, "vs_ref_decomposition", "ink_frac"),
                "vs_ref_residual_frac": _mean(per_seed, "vs_ref_decomposition", "residual_frac"),
                "fid_mean_term_arm": _mean(per_seed, "fid_mean_term_arm"),
                "fid_mean_term_base": _mean(per_seed, "fid_mean_term_base"),
                "fid_mean_delta": _mean(per_seed, "fid_mean_delta"),
                "per_seed": per_seed,
            }
            cell["_shift_vec"] = np.mean(
                [p["_shift_vec"] for p in per_seed], axis=0
            )
            cells.append(cell)
            print(f"[gap72] {label:12s} {arm:18s} "
                  f"|dmu|={cell['shift_norm']:.3f} "
                  f"DC={cell['shift_dc_frac']:.2f} "
                  f"ink={cell['shift_ink_frac']:.2f} "
                  f"resid={cell['shift_residual_frac']:.2f} "
                  f"| FID mean {cell['fid_mean_term_base']:.2f} -> "
                  f"{cell['fid_mean_term_arm']:.2f} "
                  f"(d={cell['fid_mean_delta']:+.2f})", flush=True)

    # --- structure: spatial profile and cross-arm agreement ---------------
    for cell in cells:
        shift = np.asarray(cell.pop("_shift_vec"), dtype=np.float64)
        grid = shift.reshape(28, 28)
        e = grid ** 2
        total = float(e.sum())
        ring = np.zeros((28, 28), dtype=bool)
        ring[:2, :] = ring[-2:, :] = True
        ring[:, :2] = ring[:, -2:] = True
        cell["spatial_border_energy_frac"] = (
            float(e[ring].sum()) / total if total > 0 else 0.0
        )
        cell["spatial_border_area_frac"] = float(ring.mean())
        cell["spatial_concentration"] = (
            float(np.sort(e.ravel())[::-1][:78].sum() / total) if total > 0 else 0.0
        )

    by_label: dict[str, list[dict]] = {}
    for cell in cells:
        by_label.setdefault(cell["checkpoint"], []).append(cell)
    cross: list[dict] = []
    for label, group in by_label.items():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                # recover the direction from the per-seed rows
                va = np.mean([p["_shift_vec"] for p in a["per_seed"]], axis=0)
                vb = np.mean([p["_shift_vec"] for p in b["per_seed"]], axis=0)
                cos = float(va @ vb / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-12))
                cross.append({"checkpoint": label,
                              "arm_a": a["arm"], "arm_b": b["arm"],
                              "cosine": cos})
    for c in cross:
        print(f"[gap72] cross-arm {c['checkpoint']:12s} "
              f"{c['arm_a'][:8]:8s} vs {c['arm_b'][:8]:8s} cos={c['cosine']:+.3f}")
    for cell in cells:
        for p in cell["per_seed"]:
            p.pop("_shift_vec", None)
        print(f"[gap72] spatial {cell['checkpoint']:12s} {cell['arm']:18s} "
              f"border energy={cell['spatial_border_energy_frac']:.2f} "
              f"(area {cell['spatial_border_area_frac']:.2f}) "
              f"top-78 px={cell['spatial_concentration']:.2f}")

    if args.out is not None:
        p = args.out if args.out.is_absolute() else _REPO_ROOT / args.out
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"cells": cells, "cross_arm": cross}, indent=1))
        print(f"[gap72] wrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
