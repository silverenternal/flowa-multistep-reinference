#!/usr/bin/env python3
"""Wave 96 Agent A — Kanzi framework endpoint collapse diagnosis.

Goal
----
Diagnose WHY the Wave 95 P3.C framework-arm sweep reports
``reconstruction_kabsch_rmsd_A = 2.5017 ± 0.0000 Å`` (zero variance across
N=1000 records) — i.e. ALL records collapse to the SAME codebook index.

Method
------
Run the sweep's own x_final synthesis (N(0, σ=1e-3)) on 10 records but log
the full intermediate state of the bridge so we can pinpoint exactly WHERE
the collapse happens:

  Stage 1 (synthesis):   x_final = N(0, σ=1e-3) shape (L, 512)
  Stage 2 (project_out⁻¹): x_4d = Linear_512→4(x_final)         shape (L, 4)
  Stage 3 (snap):         idx_BL = argmin(cdist(x_4d, codebook_4d))  shape (L,)
  Stage 4 (decode):       coords_pred = DAE.decode(idx_BL)

Logging
-------
For each of 10 records we log:

  * x_final L2 norm + per-position std  (Stage 1 fingerprint)
  * x_4d L2 norm + min L2 distance to nearest codebook center  (Stage 2+3)
  * idx_BL hash + whether it equals the previous record's idx_BL
  * coords_pred L2 norm vs coords_pred.mean()
  * pairwise L2 distances ||x_final[i] - x_final[j]||_2 across all records

Bonus tests
-----------
A. REAL-FRAMEWORK path: run KanziAdapter.solve_ode to get a real
   framework trajectory endpoint and verify its diversity. This isolates
   the bridge collapse from the synthesis collapse.
B. SCALE-UP path: scale x_final by 100× (σ=1e-1) and verify the collapse
   goes away, confirming the diagnosis.

Honest verdict
--------------
The collapse is NOT a framework-pipeline bug. It is a property of the
x_final synthesis step in the sweep driver
(``tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py``)
which generates x_final = N(0, σ=1e-3) — far too small to span the FSQ
codebook vocabulary. The trained Linear(512→4) inverse projects this
tiny noise to ~0 in 4-d space, and argmin over (1000,) codebook entries
always picks the same nearest-to-origin index.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

# Repo + upstream on path
_REPO_ROOT = Path(__file__).resolve().parent.parent
_KANZI_SRC = _REPO_ROOT / "data" / "kanzi_upstream" / "src"
sys.path.insert(0, str(_KANZI_SRC))
sys.path.insert(0, str(_REPO_ROOT))

from kanzi import DAE  # noqa: E402
from tools.kanzi_latent_to_coord import (  # noqa: E402
    _apply_project_out_inv,
    _load_project_out_inv,
)


def _synthesize_x_final(
    record_idx: int, *, seed: int = 42, codebook_dim: int = 512,
    sigma: float = 1e-3,
) -> np.ndarray:
    """Mirror the sweep driver: N(0, σ) seeded by record_idx, shape (64, 512)."""
    rng = np.random.default_rng(int(seed) * 1_000_003 + int(record_idx))
    L = 64
    return (rng.standard_normal((L, int(codebook_dim))).astype(np.float64)
            * float(sigma))


def _stage1_fingerprint(x: np.ndarray) -> dict[str, float]:
    return {
        "l2_norm": float(np.linalg.norm(x)),
        "max_abs": float(np.max(np.abs(x))),
        "std": float(np.std(x)),
        "norm_per_row_max": float(np.max(np.linalg.norm(x, axis=-1))),
    }


def _stage2_3_fingerprint(
    x_t: torch.Tensor, codebook_4d: torch.Tensor,
) -> tuple[np.ndarray, np.ndarray]:
    """Apply trained project_out⁻¹ then argmin to codebook; return (idx, dist_to_nearest)."""
    x_4d = _apply_project_out_inv(x_t.reshape(-1, x_t.shape[-1]))  # (B*L, 4)
    dists = torch.cdist(x_4d, codebook_4d.float())                   # (B*L, 1000)
    idx = dists.argmin(dim=-1).cpu().numpy()
    min_dist = dists.gather(dim=-1, index=dists.argmin(dim=-1).unsqueeze(-1)
                            ).squeeze(-1).cpu().numpy()
    return idx, min_dist


def main(argv: list[str] | None = None) -> int:
    out_dir = _REPO_ROOT / "verification_outputs" / "wave96a_diagnose"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[wave96a] loading DAE from data/kanzi_ckpt/cleaned_model.pt ...", file=sys.stderr)
    t0 = time.monotonic()
    dae = DAE.from_pretrained(str(_REPO_ROOT / "data" / "kanzi_ckpt" / "cleaned_model.pt")).eval()
    print(f"[wave96a] DAE loaded in {time.monotonic() - t0:.1f} s", file=sys.stderr)

    fsq = dae.quantize
    codebook_4d = fsq.implicit_codebook.float().cpu()                  # (1000, 4)
    inv_blob = _load_project_out_inv()
    print(f"[wave96a] trained inverse: input_dim={inv_blob['input_dim']}, "
          f"output_dim={inv_blob['output_dim']}", file=sys.stderr)

    n_records = 10
    sweep_records: list[dict[str, Any]] = []  # type: ignore[name-defined]
    x_finals: list[np.ndarray] = []
    idx_sequences: list[np.ndarray] = []
    min_dists: list[np.ndarray] = []

    print(f"[wave96a] running sweep synthesis on {n_records} records (σ=1e-3)...",
          file=sys.stderr)
    for r in range(n_records):
        x_final = _synthesize_x_final(r, seed=42, sigma=1e-3)
        x_t = torch.as_tensor(x_final, dtype=torch.float32).unsqueeze(0)  # (1, 64, 512)
        idx, dist = _stage2_3_fingerprint(x_t, codebook_4d)
        rec = {
            "record_idx": r,
            "stage1_x_final": _stage1_fingerprint(x_final),
            "stage2_x_4d_l2_norm": float(
                np.linalg.norm(_apply_project_out_inv(
                    torch.as_tensor(x_final, dtype=torch.float32)
                ).cpu().numpy()),
            ),
            "stage3_idx_BL": idx.tolist(),
            "stage3_min_dist_to_nearest_codebook": dist.tolist(),
            "stage3_min_dist_mean": float(np.mean(dist)),
            "stage3_min_dist_max": float(np.max(dist)),
            "stage3_unique_codes": int(len(set(idx.tolist()))),
        }
        sweep_records.append(rec)
        x_finals.append(x_final)
        idx_sequences.append(idx)
        min_dists.append(dist)

    # Pairwise L2 distances between x_final across records
    print("[wave96a] computing pairwise L2 distances between x_final across records...",
          file=sys.stderr)
    pairwise_l2 = np.zeros((n_records, n_records))
    for i in range(n_records):
        for j in range(n_records):
            pairwise_l2[i, j] = float(np.linalg.norm(x_finals[i] - x_finals[j]))

    # Diversity of idx sequences
    unique_seqs = len({tuple(s.tolist()) for s in idx_sequences})
    identical_idx_count = int(sum(
        1 for i in range(n_records) for j in range(i + 1, n_records)
        if np.array_equal(idx_sequences[i], idx_sequences[j])
    ))

    sweep_summary = {
        "n_records": n_records,
        "n_records_with_identical_idx_to_other": identical_idx_count,
        "n_unique_idx_sequences": unique_seqs,
        "all_x_final_l2_norm_max": float(max(np.linalg.norm(x) for x in x_finals)),
        "all_x_final_l2_norm_min": float(min(np.linalg.norm(x) for x in x_finals)),
        "pairwise_l2_distances": {
            "min": float(pairwise_l2[pairwise_l2 > 0].min()),
            "max": float(pairwise_l2.max()),
            "mean_offdiag": float(
                pairwise_l2[np.triu_indices(n_records, k=1)].mean()
            ),
            "matrix_summary": "see pairwise_l2_matrix",
        },
        "pairwise_l2_matrix": pairwise_l2.tolist(),
        "min_dist_to_nearest_codebook_summary": {
            "record_0_min": float(min_dists[0].min()),
            "record_0_max": float(min_dists[0].max()),
            "record_9_min": float(min_dists[9].min()),
            "record_9_max": float(min_dists[9].max()),
            "all_records_max_min_dist": float(
                max(np.min(d) for d in min_dists)
            ),
        },
        "per_record": sweep_records,
    }

    (out_dir / "sweep_synthesis_collapse.json").write_text(
        json.dumps(sweep_summary, indent=2) + "\n", encoding="utf-8",
    )
    print(f"[wave96a] wrote {out_dir / 'sweep_synthesis_collapse.json'}", file=sys.stderr)

    # ---- BONUS A: real KanziAdapter.solve_ode endpoint ----
    print("[wave96a] BONUS A: real KanziAdapter.solve_ode endpoint diversity check...",
          file=sys.stderr)
    sys.path.insert(0, str(_REPO_ROOT))
    try:
        from adaptive_reflow.adapters.kanzi import default_kanzi_adapter
        adapter = default_kanzi_adapter(
            weights_path=str(_REPO_ROOT / "data" / "kanzi_ckpt" / "cleaned_model.pt"),
            force_mode="torch",
        )
        from adaptive_reflow.universal.state import ODEConditionDelta
        real_x_finals: list[np.ndarray] = []
        for r in range(n_records):
            bundle = adapter.build_initial_state(batch_id="wave96a", sample_id=f"rec{r}")
            cond = ODEConditionDelta(
                delta_spec={"num_steps": 50, "sampler_id": "euler"},
                source="wave96a", target_round=0,
                calibration_artifact_hash="wave96a:default",
            )
            trace = adapter.solve_ode(bundle, cond, seed=42 + r)
            # Pull the trajectory endpoint from the adapter's native-state cache
            entry = adapter._native_states.get(trace.native_state_digest)  # type: ignore[attr-defined]
            if entry is None or "trajectory" not in entry:
                # Some adapters store the per-round blend under 'x0' / 'blended'
                x_final = np.asarray(entry.get("x0", np.zeros((64, 512))))
            else:
                x_final = np.asarray(entry["trajectory"][-1])  # (L, 512)
            real_x_finals.append(x_final)
        real_pairwise = np.zeros((n_records, n_records))
        for i in range(n_records):
            for j in range(n_records):
                real_pairwise[i, j] = float(np.linalg.norm(
                    real_x_finals[i] - real_x_finals[j]
                ))
        real_summary = {
            "n_records": n_records,
            "x_final_l2_norm_per_record": [
                float(np.linalg.norm(x)) for x in real_x_finals
            ],
            "pairwise_l2_min_offdiag": float(
                real_pairwise[np.triu_indices(n_records, k=1)].min()
            ),
            "pairwise_l2_mean_offdiag": float(
                real_pairwise[np.triu_indices(n_records, k=1)].mean()
            ),
            "pairwise_l2_matrix": real_pairwise.tolist(),
        }
        (out_dir / "real_framework_diversity.json").write_text(
            json.dumps(real_summary, indent=2) + "\n", encoding="utf-8",
        )
        print(f"[wave96a] wrote {out_dir / 'real_framework_diversity.json'}", file=sys.stderr)
    except Exception as exc:
        print(f"[wave96a] BONUS A FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        (out_dir / "real_framework_diversity_FAILED.txt").write_text(
            f"{type(exc).__name__}: {exc}\n", encoding="utf-8",
        )

    # ---- BONUS B: scale up sweep x_final to σ=1e-1 — does collapse vanish? ----
    print("[wave96a] BONUS B: scale sweep x_final to σ=1e-1 (100× larger)...",
          file=sys.stderr)
    scaled_idx: list[np.ndarray] = []
    scaled_dists: list[np.ndarray] = []
    for r in range(n_records):
        x_final = _synthesize_x_final(r, seed=42, sigma=1e-1)
        x_t = torch.as_tensor(x_final, dtype=torch.float32).unsqueeze(0)
        idx, dist = _stage2_3_fingerprint(x_t, codebook_4d)
        scaled_idx.append(idx)
        scaled_dists.append(dist)
    scaled_unique_seqs = len({tuple(s.tolist()) for s in scaled_idx})
    scaled_summary = {
        "sigma": 1e-1,
        "n_unique_idx_sequences": scaled_unique_seqs,
        "record_0_idx_BL": scaled_idx[0].tolist()[:10],
        "record_9_idx_BL": scaled_idx[9].tolist()[:10],
        "record_0_min_dist_to_nearest_codebook_mean": float(
            np.mean(scaled_dists[0])
        ),
        "record_0_idx_first10_dist_to_origin": [
            float(torch.norm(codebook_4d[i]).item()) for i in scaled_idx[0][:10]
        ],
    }
    (out_dir / "scaled_synthesis_diversity.json").write_text(
        json.dumps(scaled_summary, indent=2) + "\n", encoding="utf-8",
    )
    print(f"[wave96a] wrote {out_dir / 'scaled_synthesis_diversity.json'}", file=sys.stderr)

    # ---- Final summary line ----
    print("\n=== Wave 96.A collapse diagnosis (verbose) ===", file=sys.stderr)
    print(f"records processed:               {n_records}", file=sys.stderr)
    print(f"unique idx sequences (σ=1e-3):  {unique_seqs}/{n_records}", file=sys.stderr)
    print(f"identical-idx pair count:        {identical_idx_count}/{n_records*(n_records-1)//2}",
          file=sys.stderr)
    print(f"x_final L2 norm range:           "
          f"[{sweep_summary['all_x_final_l2_norm_min']:.4f}, "
          f"{sweep_summary['all_x_final_l2_norm_max']:.4f}]", file=sys.stderr)
    print(f"pairwise x_final L2 (mean offdiag): "
          f"{sweep_summary['pairwise_l2_distances']['mean_offdiag']:.4f}", file=sys.stderr)
    print(f"min_dist to nearest codebook:    "
          f"rec0 mean={sweep_records[0]['stage3_min_dist_mean']:.6f}", file=sys.stderr)
    print("=============================================", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
