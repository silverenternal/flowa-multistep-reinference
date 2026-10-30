#!/usr/bin/env python3
"""GAP-09 — run the re-inference diagnostics (Theorem 4 + Theorem 5) on a cell.

Runs :mod:`adaptive_reflow.theory.reinference_diagnostic` against the
CIFAR-10 RF **synthetic** velocity field (the R5b cell's field; NumPy-only,
no GPU, no checkpoint). It reports:

* **Theorem 4** — the estimated flow-map Lipschitz constant ``K``, the
  contraction variable ``q = m K`` at several memory fractions ``m``, the
  empirically measured round-map contraction rate, and whether the rate
  tracks ``q`` (the criterion's prediction).
* **Theorem 5** — the exact blend identity residual and whether the Eq. 7
  improvement condition predicts the measured sign of the blend's squared
  error relative to ``X``.

Output: ``verification_outputs/gap09-reinference-diagnostic/diagnostic.json``.
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
    contraction_variable,
    estimate_flow_map_lipschitz,
    integrate_flow,
    round_map_contraction,
)
from tools.audit_thm5.estimate_lipschitz import (  # noqa: E402
    IN_DIM,
    build_synthetic_weights,
    synthetic_velocity,
)

OUT_DIR = REPO / "verification_outputs" / "gap09-reinference-diagnostic"


def _velocity_fn(w: dict[str, np.ndarray]):
    def v(x: np.ndarray, t: float) -> np.ndarray:
        # ``synthetic_velocity`` handles a single sample only, so apply it
        # row-wise over the batch and flatten each (3, 32, 32) result.
        arr = np.asarray(x, dtype=np.float64)
        out = np.empty((arr.shape[0], IN_DIM), dtype=np.float64)
        for i in range(arr.shape[0]):
            out[i] = synthetic_velocity(arr[i], t, w).reshape(-1)
        return out

    return v


def main() -> int:
    w = build_synthetic_weights(seed=0)
    vel = _velocity_fn(w)
    rng = np.random.default_rng(42)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ---- Theorem 4: contraction variable q = mK ------------------------
    x_batch = rng.standard_normal((64, IN_DIM)).astype(np.float64)
    k_report = estimate_flow_map_lipschitz(
        vel, x_batch, t_final=1.0, n_steps=20, eps=1e-3, n_directions=4, seed=0
    )

    m_values = (0.3, 0.5, 0.7, 0.9)
    q_rows: list[dict[str, float]] = []
    for m in m_values:
        rep = round_map_contraction(
            vel,
            x0=rng.standard_normal((8, IN_DIM)).astype(np.float64),
            fresh=rng.standard_normal((8, IN_DIM)).astype(np.float64),
            m=float(m),
            t_final=1.0,
            n_steps=20,
            n_iter=40,
        )
        q_rows.append(
            {
                "m": float(m),
                "q_mK_max": float(contraction_variable(m, k_report.k_max)),
                "q_mK_mean": float(contraction_variable(m, k_report.k_mean)),
                **rep.as_metrics(),
            }
        )

    # ---- Theorem 5: exact blend identity + Eq. 7 ------------------------
    # A controlled blend scenario on the same cell: a target endpoint z, a
    # preceding endpoint X with error, and a fresh state Y with error. The
    # Eq. 7 condition is exact, so we sweep the relative error magnitudes
    # and check the identity residual and the predicted-vs-measured match.
    n = 256
    x_true = rng.standard_normal((n, IN_DIM)).astype(np.float64)
    z = integrate_flow(vel, x_true, t_final=1.0, n_steps=20)

    def _flow(xx: np.ndarray) -> np.ndarray:
        return integrate_flow(vel, xx, t_final=1.0, n_steps=20)

    blend_rows: list[dict[str, float]] = []
    for sigma_x, sigma_y in ((0.30, 0.10), (0.10, 0.30), (0.20, 0.20), (0.05, 0.40)):
        X = _flow(x_true) + sigma_x * rng.standard_normal((n, IN_DIM))
        Y = _flow(x_true) + sigma_y * rng.standard_normal((n, IN_DIM))
        rep = blend_identity_terms(X, Y, z, m=0.5)
        blend_rows.append(
            {"sigma_x": float(sigma_x), "sigma_y": float(sigma_y), **rep.as_metrics()}
        )

    identity_residuals = [abs(r["blend_identity_residual"]) for r in blend_rows]
    matches = [int(r["blend_prediction_matches"]) for r in blend_rows]
    t4_holds = [int(r["round_map_contraction_holds"]) for r in q_rows]
    t4_contracts = [int(r["round_map_contracts_empirically"]) for r in q_rows]
    t4_tracks = [int(r["round_map_rate_tracks_q"]) for r in q_rows]

    out = {
        "schema": "gap09_reinference_diagnostic.v1",
        "cell": "cifar10_rf_synthetic_velocity_field (R5b cell field; NumPy-only)",
        "theorem4": {
            "flow_map_lipschitz": k_report.as_metrics(),
            "rows": q_rows,
            "contraction_holds_all_m": bool(all(t4_holds)),
            "contracts_empirically_all_m": bool(all(t4_contracts)),
            "rate_tracks_q_all_m": bool(all(t4_tracks)),
        },
        "theorem5": {
            "rows": blend_rows,
            "max_abs_identity_residual": float(max(identity_residuals)),
            "all_predictions_match": bool(all(matches)),
        },
        "verdict": {
            "theorem4_measured_on_cell": True,
            "theorem4_contraction_holds": bool(all(t4_holds)),
            "theorem4_contracts_empirically": bool(all(t4_contracts)),
            "theorem4_rate_tracks_q": bool(all(t4_tracks)),
            "theorem5_identity_exact": bool(max(identity_residuals) < 1e-6),
            "theorem5_predictions_match": bool(all(matches)),
        },
    }
    out_path = OUT_DIR / "diagnostic.json"
    out_path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")

    print(f"[gap09] wrote {out_path}")
    print(f"[gap09] K_max = {k_report.k_max:.4f}, K_mean = {k_report.k_mean:.4f}")
    for r in q_rows:
        print(
            f"[gap09] m={r['m']:.1f}  q=mK_max={r['round_map_q']:.3f}  "
            f"empirical_rate={r['round_map_empirical_rate']:.4f}  "
            f"contracts={bool(r['round_map_contracts_empirically'])}  "
            f"tracks_q={bool(r['round_map_rate_tracks_q'])}"
        )
    print(f"[gap09] Thm5 max |identity residual| = {max(identity_residuals):.3e}")
    print(f"[gap09] Thm5 all predictions match = {bool(all(matches))}")
    return 0


if __name__ == "__main__":
    if {"-h", "--help"} & set(sys.argv[1:]):
        print(__doc__)
        raise SystemExit(0)
    sys.exit(main())
