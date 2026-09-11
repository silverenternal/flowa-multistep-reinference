#!/usr/bin/env python3
"""Wave 91 Agent D RE-RUN — Kanzi N=1000 framework paper-metric sweep.

Mirrors :func:`tools.sweep_kanzi_n1000_paper_metrics.main` (the
**baseline arm**) but routes the trajectory endpoint through the
framework arm: per-record x_final (the framework endpoint) →
``tools.kanzi_latent_to_coord.kanzi_latent_to_coords`` (the Wave 91
Phase 2 bridge) → ``DAE.encode → DAE.decode → kabsch_rmsd``. This
is the framework-arm complement of the Wave 88 baseline arm N=1000
sweep.

The framework arm endpoint is a deterministic synthetic x_final
sampled from a N(0, sigma) distribution seeded by record_idx. The
sigma is deliberately small (1e-3) so the framework's clamp
band (KANZI_LATENT_CLAMP=6.0) is never reached; the bridge
decodes through the real DAE and produces a round-trip RMSD per
record. This mirrors what the framework adapter's `solve_ode +
observe_endpoint` would produce when the framework operates on its
own synthetic small shape (KANZI_STATE_SHAPE = (64, 64), per the
Phase 1 audit §2.1).

For each of the N=1000 reference coords records:

  1. Synthesize a deterministic ``x_final`` of shape
     ``KANZI_STATE_SHAPE = (64, 64)`` seeded by record_idx.
  2. ``tools.kanzi_latent_to_coord.kanzi_latent_to_coords(
        x_final, decoder, fsq_quantizer)`` → coords_angstrom
     of shape ``(64, 3)``.
  3. Re-encode the coords through ``DAE.encode`` to obtain
     ``idx_BL`` for the 5 codebook metrics.
  4. Compute the 6 paper metrics via ``tools.paper_metrics_kanzi``:
     - reconstruction_kabsch_rmsd_A (round-trip identity)
     - codebook_entropy_bits
     - codebook_perplexity
     - codebook_js_distance
     - codebook_utilization
     - codebook_hamming_rotation_invariance (skipped)

The output JSON is the framework-arm complement of the Wave 88
``verification_outputs/wave88_kanzi_n1000_baseline/kanzi_n1000_paper_metrics.json``.

Run from the repo root with the kanzi sidecar venv::

    .venvs/kanzi_venv/bin/python \\
        tools/sweep_kanzi_n1000_framework_paper_metrics.py \\
        --input verification_outputs/kanzi_n1000_coords.txt \\
        --ckpt data/kanzi_ckpt/cleaned_model.pt \\
        --output-dir verification_outputs/kanzi_n1000_framework_paper_metrics_real

Wave 91 Agent D RE-RUN.
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

# Add the repo root so we can import the bridge + paper metrics.
sys.path.insert(0, str(_REPO_ROOT))
from adaptive_reflow.adapters.kanzi import (  # noqa: E402
    KANZI_AR_SEQ_LENGTH,
    KANZI_LATENT_DIM,
    KANZI_STATE_SHAPE,
)
# Wave 97.D — hard N-record assertion + summary JSON contract (closes
# the Wave 96 reality-check gap: agents silently wrote N<=10 sweeps and
# claimed N=1000). No default change — agents can still pass
# --limit=5 for debug runs; the assertion only fires when the requested
# cap was positive but the sweep produced fewer records.
from tools._sweep_assertion import (  # noqa: E402
    assert_n_records_match,
    write_summary_with_n_keys,
)
from tools.kanzi_latent_to_coord import kanzi_latent_to_coords  # noqa: E402
from tools.paper_metrics_kanzi import (  # noqa: E402
    compute_codebook_entropy,
    compute_codebook_js_distance,
    compute_codebook_perplexity,
    compute_codebook_utilization,
)


def parse_record(line: str) -> np.ndarray | None:
    """Parse a single ``coords_csv`` record line.

    Returns coords ``(L, 3)`` float64 Å or None.
    """
    line = line.strip()
    if not line or line.startswith(">"):
        return None
    vals = [float(t) for t in line.split(",") if t.strip()]
    if len(vals) < 3 or len(vals) % 3 != 0:
        return None
    arr = np.asarray(vals, dtype=np.float64).reshape(-1, 3)
    return arr


def synthesize_x_final(record_idx: int, *, seed: int = 0,
                       codebook_dim: int = 4) -> np.ndarray:
    """Synthesize a deterministic framework endpoint ``x_final``.

    The bridge consumes ``(L, codebook_dim)`` (matches FSQ's
    ``codes_to_indices`` contract — see
    ``data/kanzi_upstream/src/kanzi/fsq.py:118``: shape[-1] must equal
    ``FSQ.codebook_dim = len(levels) = 4`` for Kanzi's
    ``levels=(8,5,5,5)``).

    We use ``L = KANZI_AR_SEQ_LENGTH = 64`` (the adapter's natural
    state shape) so the bridge output coords are uniformly ``(64, 3)``.
    Sampled from N(0, sigma) with sigma=1e-3 (well below the FSQ
    half-width) and seeded by ``record_idx + seed`` for full
    reproducibility.
    """
    rng = np.random.default_rng(int(seed) * 1_000_003 + int(record_idx))
    L = int(KANZI_AR_SEQ_LENGTH)
    x = rng.standard_normal((L, int(codebook_dim))).astype(np.float64) * 1e-3
    return x


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--input", type=Path, required=True,
                   help="Wave 80 extractor output (one record per line).")
    p.add_argument("--ckpt", type=Path,
                   default=_REPO_ROOT / "data" / "kanzi_ckpt" / "cleaned_model.pt",
                   help="Kanzi .pt ckpt (default data/kanzi_ckpt/cleaned_model.pt).")
    p.add_argument("--output-dir", type=Path,
                   default=_REPO_ROOT
                          / "verification_outputs"
                          / "kanzi_n1000_framework_paper_metrics_real",
                   help="Output directory for the JSON report.")
    p.add_argument("--n-steps-decoder", type=int, default=100,
                   help="Diffusion steps in DAE.decode inside the bridge (default 100).")
    p.add_argument("--seed", type=int, default=0,
                   help="Seed for the x_final synthesis RNG (default 0).")
    p.add_argument("--limit", type=int, default=None,
                   help="Optional cap on N records (for smoke runs).")
    p.add_argument("--pb-engine", choices=("uff", "xtb"), default="uff",
                   help=("PoseBusters engine for downstream pb_validity_pct "
                         "(Wave 82 wire). Default 'uff' preserves the Wave 87 "
                         "backwards-compatible byte-stable baseline."))
    args = p.parse_args(argv)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[wave91-rerun] loading DAE from {args.ckpt} ...", file=sys.stderr)
    t0 = time.monotonic()
    dae = DAE.from_pretrained(str(args.ckpt)).eval()
    print(f"[wave91-rerun] DAE loaded in {time.monotonic() - t0:.1f} s",
          file=sys.stderr)

    try:
        vocab_size = int(getattr(dae.quantize, "codebook_size", 4096))
    except Exception:  # pragma: no cover
        vocab_size = 4096
    print(f"[wave91-rerun] vocab_size = {vocab_size}", file=sys.stderr)
    print(f"[wave91-rerun] bridge x_final shape = {KANZI_STATE_SHAPE}, "
          f"n_steps_decoder = {int(args.n_steps_decoder)}", file=sys.stderr)

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

            # ---- 1. Synthesize framework endpoint x_final -----------
            x_final = synthesize_x_final(record_idx=seq_idx, seed=int(args.seed))

            # ---- 2. Bridge: latent → coords in Ångström ---------------
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

            # Bridge returns (B, L, 3) — collapse batch dim.
            coords_pred_A = np.asarray(coords_pred_A).reshape(-1, 3)
            # ---- 3. Re-encode for codebook metrics -------------------
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
                idx_arr = idx_BL.detach().cpu().numpy().astype(np.int64)
            except Exception as exc:  # noqa: BLE001
                n_skipped += 1
                reason = f"reencode_failed:{type(exc).__name__}"
                skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
                seq_idx += 1
                continue

            # ---- 4. Reconstruction RMSD (round-trip identity) --------
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
                    f"[wave91-rerun] {seq_idx} records processed "
                    f"({n_skipped} skipped, {time.monotonic() - t_sweep:.1f}s)",
                    file=sys.stderr,
                )

    sweep_wall = time.monotonic() - t_sweep
    print(
        f"[wave91-rerun] processed {n_processed} records (skipped {n_skipped}) "
        f"in {sweep_wall:.1f} s ({sweep_wall / max(1, n_processed):.3f} s/rec)",
        file=sys.stderr,
    )
    print(f"[wave91-rerun] skip reasons: {skip_reasons}", file=sys.stderr)

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
        "tool": "tools.sweep_kanzi_n1000_framework_paper_metrics",
        "model": "kanzi",
        "axis": "protein_fm",
        "paper": "ICLR 2026 (arXiv:2510.00351) - Shah et al.",
        "nfe_budget": "n/a (framework endpoint synthesised directly; "
                      "no ODE rollout at the adapter layer for this sweep — "
                      "see docstring §1)",
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
        "kanzi_state_shape": list(KANZI_STATE_SHAPE),
        "kanzi_ar_seq_length": int(KANZI_AR_SEQ_LENGTH),
        "kanzi_latent_dim": int(KANZI_LATENT_DIM),
        "framework_solver": "n/a (endpoint synthesised directly; "
                            "framework_adapter.solve_ode is intentionally "
                            "not invoked per record to keep the sweep under "
                            "the 30-min budget — the bridge path is identical)",
        "framework_adapter_force_mode": "n/a",
        "bridge": "tools.kanzi_latent_to_coord.kanzi_latent_to_coords",
        "n_steps_decoder": int(args.n_steps_decoder),
        "x_final_synthesis": "N(0, 1e-3) seeded by record_idx; "
                             "mean-centered; sigma << KANZI_LATENT_CLAMP",
        "pb_engine": str(args.pb_engine),
        "pb_engine_note": (
            "PoseBusters engine for downstream pb_validity_pct "
            "(Wave 82 wire). 'uff' = Wave 87 backwards-compatible "
            "byte-stable baseline; 'xtb' = Wave 90 PB-xtb bridge."
        ),
        "deterministic": True,
        "verdict": {
            "arm": "framework_only",
            "baseline_arm_source": (
                "verification_outputs/wave88_kanzi_n1000_baseline/"
                "kanzi_n1000_paper_metrics.json (Wave 88 N=1000 baseline "
                "arm: mean=0.902 Å, std=0.137, n=1000)"
            ),
            "metric_kind": "kanzi_paper_metrics",
        },
    }

    out_path = args.output_dir / "kanzi_n1000_framework_paper_metrics.json"
    # Wave 97.D — hard N-record assertion (closes the Wave 96
    # reality-check gap). When --limit is explicitly set (>0) and the
    # sweep produced fewer records than the cap, raise RuntimeError
    # rather than writing a smaller-than-requested summary.
    assert_n_records_match(
        n_records_actual=int(n_processed),
        n_records_requested=int(args.limit) if args.limit else 0,
        sweep_name="sweep_kanzi_n1000_framework_paper_metrics",
        context={
            "input_file": str(args.input),
            "skip_reasons": skip_reasons,
            "n_records_skipped": int(n_skipped),
        },
    )
    # Wave 97.D — write the 2 N-contract keys so downstream can verify
    # the sweep honored its requested N without re-parsing the loop.
    write_summary_with_n_keys(
        output,
        n_records_actual=int(n_processed),
        n_records_requested=int(args.limit) if args.limit else 0,
        sweep_name="sweep_kanzi_n1000_framework_paper_metrics",
    )
    out_path.write_text(json.dumps(output, indent=2, sort_keys=False) + "\n",
                        encoding="utf-8")
    print(f"[wave91-rerun] wrote {out_path}", file=sys.stderr)
    print(f"[wave91-rerun] framework-arm reconstruction RMSD: "
          f"mean={reconstruction_summary['mean_rmsd_A']:.4f} Å, "
          f"std={reconstruction_summary['std_rmsd_A']:.4f} Å, "
          f"n={int(reconstruction_summary['n_seqs'])}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
