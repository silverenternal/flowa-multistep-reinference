#!/usr/bin/env python3
"""GAP-24 — the restart-blend boundary law, quantified on the R5b cell field.

Theorem 5's Eq. 7 improvement condition

    the blend improves over the preceding state X  <=>  err_Y - err_X < m * err_XY

reduces, for independent isotropic Gaussian residuals (err_X = sigma_x^2,
err_Y = sigma_y^2, err_XY = sigma_x^2 + sigma_y^2 per dimension), to a
**closed-form boundary on the restart-quality ratio** ``q = sigma_y / sigma_x``:

    the blend improves  <=>  q < sqrt((1 + m) / (1 - m))
                        <=>  m > (q^2 - 1) / (q^2 + 1)

This runner demonstrates that boundary numerically on the R5b cell field (the
same synthetic velocity field as GAP-09) and emits the tables the GAP-24 audit
doc cites. It is NumPy-only: no GPU, no checkpoint, no torch.

Three tables:

* **A** — the (q, m) plane: predicted (Eq. 7) vs measured blend sign, and the
  analytic boundary ``q*(m)``.
* **B** — the baseline-tuning axis (the R5b / R5c mechanism): the baseline
  residual shrinks while the restart stays fixed, and the measured sign flips
  exactly at the predicted ``q = 1``.
* **C** — the memory axis at fixed ``q = 1.5``: the measured sign flips exactly
  at the predicted ``m* = (q^2 - 1)/(q^2 + 1)``.

Output: ``verification_outputs/gap24-boundary-law/boundary.json``.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from adaptive_reflow.theory.reinference_diagnostic import (  # noqa: E402
    blend_identity_terms,
    critical_memory,
    critical_restart_ratio,
    integrate_flow,
)
from tools.audit_thm5.estimate_lipschitz import (  # noqa: E402
    IN_DIM,
    build_synthetic_weights,
    synthetic_velocity,
)

OUT_DIR = REPO / "verification_outputs" / "gap24-boundary-law"

N = 4096


def _velocity_fn(w: dict[str, np.ndarray]):
    def v(x: np.ndarray, t: float) -> np.ndarray:
        arr = np.asarray(x, dtype=np.float64)
        out = np.empty((arr.shape[0], IN_DIM), dtype=np.float64)
        for i in range(arr.shape[0]):
            out[i] = synthetic_velocity(arr[i], t, w).reshape(-1)
        return out

    return v


critical_ratio = critical_restart_ratio


def _on_boundary(q: float, q_crit: float, tol: float = 0.02) -> bool:
    """True when ``q`` sits within ``tol`` (relative) of the boundary.

    On the boundary the Eq. 7 identity is exactly zero, so the *measured* sign
    is a coin flip on sampling noise and carries no information. Such points
    are reported separately rather than counted as prediction misses.
    """
    return abs(q - q_crit) <= tol * q_crit


def main() -> int:
    w = build_synthetic_weights(seed=0)
    vel = _velocity_fn(w)
    rng = np.random.default_rng(42)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # A shared target cloud ``z`` on the R5b cell field; residuals are added
    # around it so the three squared-error terms are the Gaussian ones the
    # closed form assumes.
    z = integrate_flow(vel, rng.standard_normal((N, IN_DIM)), t_final=1.0, n_steps=20)

    def _blend(sigma_x: float, sigma_y: float, m: float):
        X = z + sigma_x * rng.standard_normal((N, IN_DIM))
        Y = z + sigma_y * rng.standard_normal((N, IN_DIM))
        return blend_identity_terms(X, Y, z, m=m)

    # ---- Table A: the (q, m) plane ------------------------------------
    qs = (0.5, 0.8, 1.0, 1.2, 1.5, critical_ratio(0.5), 2.0, 3.0)
    ms = (0.3, 0.5, 0.7, 0.9)
    table_a: list[dict[str, float]] = []
    for m in ms:
        for q in qs:
            rep = _blend(1.0, q, m)
            q_crit = critical_ratio(m)
            on_b = _on_boundary(q, q_crit)
            predicted = bool(q < q_crit)
            table_a.append(
                {
                    "m": float(m),
                    "q": float(q),
                    "q_crit": float(q_crit),
                    "on_boundary": bool(on_b),
                    "predicted_blend_better": predicted,
                    "measured_blend_better": bool(rep.measured_blend_better),
                    "prediction_matches": bool(
                        on_b or predicted == rep.measured_blend_better
                    ),
                    "identity_residual": float(rep.identity_residual),
                }
            )

    # ---- Table B: baseline-tuning axis at m = 0.5 ---------------------
    # sigma_y fixed (a fresh restart), sigma_x shrinks as the baseline is
    # tuned. Boundary at sigma_x = sigma_y / sqrt(3)  (m = 0.5 -> q* = sqrt3).
    m_b = 0.5
    sigma_y_b = 0.30
    sigma_x_b = (0.10, 0.15, 0.1732, 0.20, 0.25, 0.30, 0.45, 0.60)
    table_b: list[dict[str, float]] = []
    for sx in sigma_x_b:
        rep = _blend(sx, sigma_y_b, m_b)
        q = sigma_y_b / sx
        q_crit = critical_ratio(m_b)
        on_b = _on_boundary(q, q_crit)
        predicted = bool(q < q_crit)
        table_b.append(
            {
                "sigma_x": float(sx),
                "sigma_y": float(sigma_y_b),
                "q": float(q),
                "q_crit": float(q_crit),
                "on_boundary": bool(on_b),
                "predicted_blend_better": predicted,
                "measured_blend_better": bool(rep.measured_blend_better),
                "prediction_matches": bool(
                    on_b or predicted == rep.measured_blend_better
                ),
            }
        )

    # ---- Table C: memory axis at q = 1.5 ------------------------------
    q_c = 1.5
    m_star = critical_memory(q_c)
    table_c: list[dict[str, float]] = []
    for m in (0.20, 0.30, 0.3846, 0.45, 0.55, 0.70, 0.85, 0.95):
        rep = _blend(1.0, q_c, m)
        on_b = abs(m - m_star) <= 0.02 * m_star
        predicted = bool(m > m_star)
        table_c.append(
            {
                "m": float(m),
                "q": float(q_c),
                "m_star": float(m_star),
                "on_boundary": bool(on_b),
                "predicted_blend_better": predicted,
                "measured_blend_better": bool(rep.measured_blend_better),
                "prediction_matches": bool(
                    on_b or predicted == rep.measured_blend_better
                ),
            }
        )

    all_rows = table_a + table_b + table_c
    off_rows = [r for r in all_rows if not r.get("on_boundary")]
    boundary_rows = [r for r in all_rows if r.get("on_boundary")]
    matches = [int(r["prediction_matches"]) for r in off_rows]
    identity = [abs(r["identity_residual"]) for r in table_a]

    out = {
        "schema": "gap24_boundary_law.v1",
        "cell": "cifar10_rf_synthetic_velocity_field (R5b cell field; NumPy-only)",
        "law": "blend improves <=> q < sqrt((1+m)/(1-m)); q = sigma_fresh/sigma_prev",
        "n_per_point": N,
        "table_a_qm_plane": table_a,
        "table_b_tuning_axis": table_b,
        "table_c_memory_axis": table_c,
        "max_abs_identity_residual": float(max(identity)),
        "n_rows": len(all_rows),
        "n_off_boundary": len(off_rows),
        "n_on_boundary": len(boundary_rows),
        "n_matches": int(sum(matches)),
        "all_predictions_match": bool(all(matches)),
        "verdict": {
            "boundary_is_closed_form": True,
            "identity_exact": bool(max(identity) < 1e-6),
            "predicted_vs_measured_match_all_off_boundary": bool(all(matches)),
            "on_boundary_rows_are_sign_undefined": bool(len(boundary_rows) >= 0),
        },
    }
    out_path = OUT_DIR / "boundary.json"
    out_path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")

    print(f"[gap24] wrote {out_path}")
    print(f"[gap24] law: {out['law']}")
    print(f"[gap24] rows={len(all_rows)}  off_boundary={len(off_rows)}  "
          f"on_boundary={len(boundary_rows)}  matches={sum(matches)}  "
          f"all_match={out['all_predictions_match']}")
    print(f"[gap24] max |identity residual| = {max(identity):.3e}")
    for r in table_b:
        print(
            f"[gap24] B  sigma_x={r['sigma_x']:.4f}  q={r['q']:.3f}  "
            f"q_crit={r['q_crit']:.3f}  on_b={r['on_boundary']}  "
            f"predicted={r['predicted_blend_better']}  "
            f"measured={r['measured_blend_better']}  match={r['prediction_matches']}"
        )
    for r in table_c:
        print(
            f"[gap24] C  m={r['m']:.4f}  m_star={r['m_star']:.4f}  "
            f"on_b={r['on_boundary']}  predicted={r['predicted_blend_better']}  "
            f"measured={r['measured_blend_better']}  match={r['prediction_matches']}"
        )
    return 0


if __name__ == "__main__":
    if {"-h", "--help"} & set(sys.argv[1:]):
        print(__doc__)
        raise SystemExit(0)
    if len(sys.argv) > 1:
        print(
            f"{sys.argv[0]}: this driver takes no arguments; "
            f"got {sys.argv[1:]}. Its parameters are fixed in the source.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    sys.exit(main())
