#!/usr/bin/env python3
"""Wave 95 Phase 3.C — N=1000 framework paper-metric sweep via project_out⁻¹ bridge.

Mirrors :func:`tools.sweep_kanzi_n1000_framework_paper_metrics.main` but
**feeds the bridge a 512-d ``x_final``** (the framework trajectory endpoint
geometry — ``n_channels_decoder=512``, the post-``project_out`` space)
instead of the 64-d noise that the Wave 91 driver synthesises.

The Phase 3.B bridge (`tools.kanzi_latent_to_coord.kanzi_latent_to_coords`)
now strictly requires 512-d input because it routes through a *trained*
``Linear(512 → 4)`` inverse of ``project_out`` (see commit 378dc4a and
``tools/_kanzi_project_out_inv_train.py``). The Wave 91 sweep driver's
64-d noise synthesis pre-dates that wire — running it unchanged triggers
``RuntimeError: mat1 and mat2 shapes cannot be multiplied (64x64 and 512x4)``
on every record.

This driver keeps the bridge + paper-metric + per-record logic identical
to the Wave 91 driver (so the only variable is the x_final shape, 64→512);
the change is local to this script and never touches
``tools/kanzi_latent_to_coord.py`` (Phase 3.B owns that file).

Output JSON mirrors
``verification_outputs/wave88_kanzi_n1000_baseline/kanzi_n1000_paper_metrics.json``
(per-arm Δ vs Wave 88 N=1000 baseline arm).

Run from the repo root with the kanzi sidecar venv::

    .venvs/kanzi_venv/bin/python \\
        tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py \\
        --input verification_outputs/kanzi_n1000_coords.txt \\
        --ckpt data/kanzi_ckpt/cleaned_model.pt \\
        --output-dir verification_outputs/kanzi_n1000_framework_paper_metrics_inv_proj
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

_REPO_ROOT = Path(__file__).resolve().parent.parent
_KANZI_SRC = _REPO_ROOT / "data" / "kanzi_upstream" / "src"
sys.path.insert(0, str(_KANZI_SRC))

from kanzi import DAE, kabsch_rmsd  # noqa: E402

sys.path.insert(0, str(_REPO_ROOT))
from tools.kanzi_latent_to_coord import kanzi_latent_to_coords  # noqa: E402
from tools.paper_metrics_kanzi import (  # noqa: E402
    compute_codebook_entropy,
    compute_codebook_js_distance,
    compute_codebook_perplexity,
    compute_codebook_utilization,
)
# Wave 96.B — wire the real KanziAdapter.solve_ode trajectory endpoint
# (L2 norm ~180 per Trial C in tools/_wave96a_diagnose_collapse.py)
# instead of the σ=1e-3 synthetic noise in synthesize_x_final_512d
# (L2 norm ~0.18, 3 orders of magnitude too small to span the FSQ
# codebook — produces deterministic idx=500 collapse on every record).
from adaptive_reflow.adapters.kanzi import default_kanzi_adapter  # noqa: E402
from adaptive_reflow.universal.state import ODEConditionDelta  # noqa: E402


def parse_record(line: str) -> np.ndarray | None:
    """Parse a single ``coords_csv`` record line."""
    line = line.strip()
    if not line or line.startswith(">"):
        return None
    vals = [float(t) for t in line.split(",") if t.strip()]
    if len(vals) < 3 or len(vals) % 3 != 0:
        return None
    return np.asarray(vals, dtype=np.float64).reshape(-1, 3)


def synthesize_x_final_512d(record_idx: int, *, seed: int = 42,
                            codebook_dim: int = 512) -> np.ndarray:
    """Synthesize a deterministic 512-d framework endpoint.

    DEPRECATED (Wave 96.B): The σ=1e-3 ball has L2 norm ~0.18 — 3
    orders of magnitude below the smallest FSQ cell half-width (0.143)
    so the trained Linear(512→4) inverse projects it to ~0 in 4-d
    space and argmin always picks the same nearest-to-origin codebook
    index (idx=500). Use :func:`real_framework_x_final_512d` instead —
    it runs :meth:`KanziAdapter.solve_ode` and returns the real
    trajectory endpoint with L2 norm ~180 (verified diverse in
    ``tools/_wave96a_diagnose_collapse.py`` Trial C).
    """
    rng = np.random.default_rng(int(seed) * 1_000_003 + int(record_idx))
    L = 64  # KANZI_AR_SEQ_LENGTH (matches KanziAdapter)
    x = rng.standard_normal((L, int(codebook_dim))).astype(np.float64) * 1e-3
    return x


def real_framework_x_final_512d(adapter, record_idx: int, *,
                               seed: int = 42) -> np.ndarray:
    """Wave 96.B — return the REAL framework trajectory endpoint.

    Runs :meth:`KanziAdapter.build_initial_state` +
    :meth:`KanziAdapter.solve_ode` and extracts ``trajectory[-1]``
    (the post-Euler/Heun integration endpoint in
    ``(L=64, n_channels_decoder=512)`` space). The result has L2 norm
    ~180 — 3 orders of magnitude larger than the σ=1e-3 noise in
    :func:`synthesize_x_final_512d` — so it spans the FSQ codebook
    and produces per-record diversity (10/10 unique idx sequences in
    Trial C of the diagnostic).
    """
    batch_id = "wave96b"
    sample_id = f"rec{record_idx}"
    bundle = adapter.build_initial_state(
        batch_id=batch_id, sample_id=sample_id,
    )
    cond = ODEConditionDelta(
        delta_spec={"num_steps": 50, "sampler_id": "euler"},
        source="wave96b", target_round=0,
        calibration_artifact_hash="wave96b:default",
    )
    trace = adapter.solve_ode(bundle, cond, seed=int(seed) + int(record_idx))
    entry = adapter._native_states.get(trace.native_state_digest)  # type: ignore[attr-defined]
    if entry is None or "trajectory" not in entry:
        # Defensive fallback: initial state only (shouldn't happen for
        # a real solve_ode rollout).
        return np.asarray(
            entry.get("x0", np.zeros((64, 512), dtype=np.float64))
            if entry is not None else np.zeros((64, 512), dtype=np.float64),
            dtype=np.float64,
        )
    return np.asarray(entry["trajectory"][-1], dtype=np.float64)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--ckpt", type=Path,
                   default=_REPO_ROOT / "data" / "kanzi_ckpt" / "cleaned_model.pt")
    p.add_argument("--output-dir", type=Path,
                   default=_REPO_ROOT / "verification_outputs"
                          / "kanzi_n1000_framework_paper_metrics_inv_proj")
    p.add_argument("--n-steps-decoder", type=int, default=100)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--limit", type=int, default=1000)
    args = p.parse_args(argv)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[wave95-p3c] loading DAE from {args.ckpt} ...", file=sys.stderr)
    t0 = time.monotonic()
    dae = DAE.from_pretrained(str(args.ckpt)).eval()
    print(f"[wave95-p3c] DAE loaded in {time.monotonic() - t0:.1f} s",
          file=sys.stderr)

    vocab_size = int(getattr(dae.quantize, "codebook_size", 1000))
    n_decoder = int(dae.quantize.project_out.weight.shape[0])  # 512
    print(f"[wave95-p3c] vocab_size={vocab_size}, n_decoder={n_decoder}",
          file=sys.stderr)

    # Wave 96.B — construct the real KanziAdapter so the framework-arm
    # endpoints come from the actual ``solve_ode`` trajectory instead of
    # the σ=1e-3 synthetic noise (which collapses every record to the
    # same codebook index; see wave96a-collapse-diagnosis.md).
    print(f"[wave96b] constructing real KanziAdapter from {args.ckpt} ...",
          file=sys.stderr)
    t_ada = time.monotonic()
    kanzi_adapter = default_kanzi_adapter(
        weights_path=args.ckpt, force_mode="torch",
        num_steps=50, solver="euler",
    )
    print(f"[wave96b] KanziAdapter constructed in {time.monotonic() - t_ada:.1f} s",
          file=sys.stderr)

    per_seq_rmsd: dict[str, float] = {}
    all_idx: list[np.ndarray] = []
    n_processed = 0
    n_skipped = 0
    skip_reasons: dict[str, int] = {}
    t_sweep = time.monotonic()

    with args.input.open(encoding="utf-8") as fh:
        seq_idx = 0
        for line in fh:
            coords_angstrom = parse_record(line)
            if coords_angstrom is None:
                continue

            # 1. Framework endpoint (post-project_out, 512-d) — Wave 96.B
            # uses the REAL KanziAdapter.solve_ode trajectory endpoint
            # (L2 norm ~180; diverse per-record) instead of the σ=1e-3
            # synthetic noise (L2 norm ~0.18; collapses to idx=500).
            x_final = real_framework_x_final_512d(
                adapter=kanzi_adapter, record_idx=seq_idx,
                seed=int(args.seed),
            )

            # 2. Bridge: latent (512-d) → coords in Angstrom
            try:
                coords_pred_A = kanzi_latent_to_coords(
                    x_final, decoder=dae, fsq_quantizer=dae.quantize,
                    n_steps=int(args.n_steps_decoder), seed=int(args.seed),
                )
            except Exception as exc:  # noqa: BLE001
                n_skipped += 1
                reason = f"bridge_failed:{type(exc).__name__}"
                skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
                seq_idx += 1
                continue

            coords_pred_A = np.asarray(coords_pred_A).reshape(-1, 3)

            # 3. Re-encode for codebook metrics
            coords_pred_nm = coords_pred_A.astype(np.float32) / 10.0
            L_pred = int(coords_pred_nm.shape[0])
            coords_BLD = coords_pred_nm.reshape(1, L_pred, 3)
            coords_BLD = coords_BLD - coords_BLD.mean(axis=1, keepdims=True)
            try:
                with torch.no_grad():
                    *_, idx_BL = dae.encode(
                        torch.as_tensor(coords_BLD, dtype=torch.float32),
                        preprocess=False,
                    )
            except Exception as exc:  # noqa: BLE001
                n_skipped += 1
                reason = f"reencode_failed:{type(exc).__name__}"
                skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
                seq_idx += 1
                continue

            # 4. Reconstruction RMSD (round-trip identity)
            try:
                recon = dae.decode(idx_BL).detach().cpu().numpy() * 10.0
                recon_angstrom = recon.reshape(-1, 3).astype(np.float64)
                pred_angstrom = coords_pred_A.reshape(-1, 3).astype(np.float64)
                recon_angstrom = (
                    recon_angstrom - recon_angstrom.mean(axis=0, keepdims=True)
                )
                pred_angstrom = (
                    pred_angstrom - pred_angstrom.mean(axis=0, keepdims=True)
                )
                rmsd_val = float(kabsch_rmsd(
                    torch.from_numpy(pred_angstrom.astype(np.float32)),
                    torch.from_numpy(recon_angstrom.astype(np.float32)),
                ))
            except Exception as exc:  # noqa: BLE001
                n_skipped += 1
                reason = f"rmsd_failed:{type(exc).__name__}"
                skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
                seq_idx += 1
                continue

            per_seq_rmsd[f"seq_{seq_idx}"] = rmsd_val
            idx_np = idx_BL.detach().cpu().reshape(-1).to(torch.int32).numpy()
            all_idx.append(idx_np)
            seq_idx += 1
            n_processed += 1
            if args.limit is not None and n_processed >= int(args.limit):
                break
            if seq_idx % 50 == 0:
                print(
                    f"[wave95-p3c] {seq_idx} records processed "
                    f"({n_skipped} skipped, {time.monotonic() - t_sweep:.1f}s)",
                    file=sys.stderr,
                )

    sweep_wall = time.monotonic() - t_sweep
    print(
        f"[wave95-p3c] processed {n_processed} records (skipped {n_skipped}) "
        f"in {sweep_wall:.1f} s ({sweep_wall / max(1, n_processed):.3f} s/rec)",
        file=sys.stderr,
    )
    print(f"[wave95-p3c] skip reasons: {skip_reasons}", file=sys.stderr)

    rmsd_values = list(per_seq_rmsd.values())
    reconstruction_summary = {
        "n_seqs": float(len(rmsd_values)),
        "mean_rmsd_A": float(sum(rmsd_values) / max(1, len(rmsd_values))),
        "min_rmsd_A": float(min(rmsd_values)) if rmsd_values else 0.0,
        "max_rmsd_A": float(max(rmsd_values)) if rmsd_values else 0.0,
        "std_rmsd_A": float(np.std(np.asarray(rmsd_values), ddof=1))
        if len(rmsd_values) >= 2 else 0.0,
    }

    idx_concat = (np.concatenate(all_idx).astype(np.int64)
                  if all_idx else np.zeros((0,), dtype=np.int64))

    cb_entropy_bits = compute_codebook_entropy(
        idx_concat, vocab_size=vocab_size) if all_idx else 0.0
    cb_perplexity = compute_codebook_perplexity(
        idx_concat, vocab_size=vocab_size) if all_idx else 0.0
    cb_utilization = compute_codebook_utilization(
        idx_concat, vocab_size=vocab_size) if all_idx else 0.0

    if len(all_idx) >= 2 and all_idx[0].shape == all_idx[1].shape:
        idx_pair = np.stack([all_idx[0], all_idx[1]], axis=0).astype(np.int64)
        cb_js_distance = compute_codebook_js_distance(
            idx_pair, vocab_size=vocab_size)
    else:
        cb_js_distance = 0.0

    output = {
        "tool": "tools.sweep_kanzi_n1000_framework_paper_metrics_inv_proj",
        "model": "kanzi",
        "axis": "protein_fm",
        "paper": "ICLR 2026 (arXiv:2510.00351) - Shah et al.",
        "nfe_budget": (
            "50 NFE per record (KanziAdapter.solve_ode Euler rollout; "
            "Wave 96.B — was 'n/a' before the σ=1e-3 collapse fix)"
        ),
        "seed": int(args.seed),
        "input_file": str(args.input),
        "ckpt_path": str(args.ckpt),
        "vocab_size": int(vocab_size),
        "n_records_processed": int(n_processed),
        "n_records_skipped": int(n_skipped),
        "skip_reasons": skip_reasons,
        "sweep_wallclock_s": float(sweep_wall),
        "per_seq_wallclock_s": float(sweep_wall / max(1, n_processed)),
        "reconstruction_kabsch_rmsd_A": reconstruction_summary,
        "codebook_metrics": {
            "codebook_entropy_bits": float(cb_entropy_bits),
            "codebook_perplexity": float(cb_perplexity),
            "codebook_js_distance": float(cb_js_distance),
            "codebook_utilization": float(cb_utilization),
            "codebook_hamming_rotation_invariance": 0.0,
        },
        "codebook_metrics_notes": {
            "entropy": "computed across all N record indices concatenated",
            "perplexity": "2 ** entropy",
            "js_distance": "pair=records_0_1_L={}".format(
                all_idx[0].shape[0] if all_idx else 0
            ),
            "utilization": "computed across all N record indices concatenated",
            "hamming_rotation_invariance": (
                "skipped in sweep loop (encoder-only; would 2x runtime)"
            ),
        },
        "x_final_synthesis": (
            "Wave 96.B: real KanziAdapter.solve_ode trajectory endpoint "
            "(L2 norm ~180 per Trial C in tools/_wave96a_diagnose_collapse.py); "
            "shape (KANZI_AR_SEQ_LENGTH=64, n_channels_decoder=512); "
            "50 NFE Euler rollout, seeded by record_idx. Replaces the prior "
            "σ=1e-3 synthetic noise which collapsed every record to the same "
            "FSQ codebook index (idx=500)."
        ),
        "bridge": (
            "tools.kanzi_latent_to_coord.kanzi_latent_to_coords with "
            "Phase 3.B trained Linear(512 → 4) inverse of project_out "
            "(commit 378dc4a, per-sample RMSE 3.54e-3 << FSQ half-grid 0.5)"
        ),
        "n_steps_decoder": int(args.n_steps_decoder),
        "deterministic": True,
        "wave": "96.B",
        "verdict": {
            "arm": "framework_only_with_project_out_inv",
            "baseline_arm_source": (
                "verification_outputs/wave88_kanzi_n1000_baseline/"
                "kanzi_n1000_paper_metrics.json (Wave 88 N=1000 baseline "
                "arm: mean=0.902 Å, std=0.137, n=1000)"
            ),
            "metric_kind": "kanzi_paper_metrics",
        },
    }

    out_path = args.output_dir / "kanzi_n1000_framework_paper_metrics.json"
    out_path.write_text(json.dumps(output, indent=2, sort_keys=False) + "\n",
                        encoding="utf-8")
    print(f"[wave95-p3c] wrote {out_path}", file=sys.stderr)
    print(f"[wave95-p3c] framework-arm reconstruction RMSD: "
          f"mean={reconstruction_summary['mean_rmsd_A']:.4f} Å, "
          f"std={reconstruction_summary['std_rmsd_A']:.4f} Å, "
          f"n={int(reconstruction_summary['n_seqs'])}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
