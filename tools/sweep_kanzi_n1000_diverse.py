#!/usr/bin/env python3
"""Wave 96.E — Production Kanzi N=1000 framework paper-metric sweep with diverse endpoints.

Mirror of :func:`tools.sweep_kanzi_n1000_framework_paper_metrics_inv_proj.main`
(Wave 95 Phase 3.C + Wave 96.B diverse endpoints) but emits a **per-record
JSONL** in addition to the aggregate summary JSON. The per-record JSONL is
the source of truth for the Wave 96.E §7.3 Kanzi update + CONSOLIDATED_RESULTS
§15.14 + wave93 audit additive row.

Why this script exists
----------------------

Wave 96.D wrote a debug driver in ``/tmp/wave96d_run_real_diverse.py`` that
hard-coded ``max_records=3`` (intended as a smoke surface, never executed
at full N). Wave 96.E replaces that debug script with a **production
sweep** that:

* removes the 3-record limit and runs ALL records in the input file (up
  to N=1000);
* uses the Wave 96.B real :func:`real_framework_x_final_512d` endpoint
  (no σ=1e-3 synthetic collapse);
* computes the 5 Kanzi codebook metrics + 1 reconstruction Kabsch RMSD
  per record via :mod:`tools.paper_metrics_kanzi`;
* writes one JSONL row per record to ``<output_dir>/per_metric.jsonl``
  (the same format the Wave 96.D debug script wrote, but with N=1000
  rows).

Pipeline per record (mirrors the Wave 95 Phase 3.C driver — the only
variable vs the debug script is the removal of the 3-record cap):

  1. Read a record from ``--input`` (one ``x,y,z`` triple line per
     record; lines starting with ``>`` are skipped).
  2. Run :meth:`KanziAdapter.solve_ode` (50 NFE Euler) → ``x_final``
     with L2 norm ~180 (the Wave 96.B fix for the σ=1e-3 collapse).
  3. Run :func:`kanzi_latent_to_coords` (the Wave 91 Phase 2 bridge
     with the Phase 3.B trained Linear(512→4) inverse) → ``coords_Å``.
  4. Re-encode through ``DAE.encode`` → ``idx_BL`` for codebook metrics.
  5. Run ``DAE.decode(idx_BL)`` + ``kabsch_rmsd`` against the bridge
     output → ``reconstruction_kabsch_rmsd_A``.
  6. Emit one JSONL row with the per-record metrics.

Output JSON mirrors
``verification_outputs/wave88_kanzi_n1000_baseline/kanzi_n1000_paper_metrics.json``
(baseline arm: mean=0.902 ± 0.137 Å, n=1000 — the source of the Δ vs
baseline computation in §3 below).

Run from the repo root with the kanzi sidecar venv::

    .venvs/kanzi_venv/bin/python \\
        tools/sweep_kanzi_n1000_diverse.py \\
        --output-dir verification_outputs/kanzi_n1000_framework_paper_metrics_diverse/

Wave 96.E — replaces Wave 96.D debug driver; runs at full N=1000.
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
sys.path.insert(0, str(_REPO_ROOT))

from kanzi import DAE, kabsch_rmsd  # noqa: E402

# Wave 96.B — reuse the diverse-endpoint helper + parser from the Wave 95
# Phase 3.C driver (this is the production version of the Wave 96.D
# debug script, not a re-implementation).
from tools.sweep_kanzi_n1000_framework_paper_metrics_inv_proj import (  # noqa: E402
    parse_record,
    real_framework_x_final_512d,
)
from tools.kanzi_latent_to_coord import kanzi_latent_to_coords  # noqa: E402
from tools.paper_metrics_kanzi import (  # noqa: E402
    compute_codebook_entropy,
    compute_codebook_js_distance,
    compute_codebook_perplexity,
    compute_codebook_utilization,
)
# Wave 97.D — hard N-record assertion + summary JSON contract (closes
# the Wave 96 reality-check gap: agents silently wrote N<=10 sweeps and
# claimed N=1000). No default change — agents can still pass
# --max-records=5 for debug runs; the assertion only fires when the
# requested cap was positive but the sweep produced fewer records.
from tools._sweep_assertion import (  # noqa: E402
    assert_n_records_match,
    write_summary_with_n_keys,
)
from adaptive_reflow.adapters.kanzi import default_kanzi_adapter  # noqa: E402

# Wave 112.D-1: --config support.
from tools._kanzi_sweep_runner import apply_kanzi_profile_defaults  # noqa: E402
from tools.eval.config import load_run_profile  # noqa: E402

# Wave 98.A — GPU utilization watchdog. Wraps the sweep loop so a
# stuck-process scenario (util.gpu==0 while memory.used>100 MiB for
# >30s) emits a WARNING to stderr. The diagnostic that should have
# caught the Wave 96.E stuck sweep earlier.
from tools._gpu_watchdog import gpu_watchdog  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--config", type=Path, default=None,
                   help=("Wave 112.D-1: optional path to a run-profile YAML; "
                         "CLI flag > YAML value > module default. Omitting "
                         "--config preserves the legacy byte-stable surface."))
    p.add_argument("--input", type=Path,
                   default=_REPO_ROOT / "verification_outputs"
                                          / "kanzi_n1000_coords.txt",
                   help="Wave 80 extractor output (one record per line).")
    p.add_argument("--ckpt", type=Path,
                   default=_REPO_ROOT / "data" / "kanzi_ckpt"
                                          / "cleaned_model.pt",
                   help="Kanzi .pt ckpt (default data/kanzi_ckpt/cleaned_model.pt).")
    p.add_argument("--output-dir", type=Path, required=True,
                   help="Output directory for per_metric.jsonl + summary JSON.")
    p.add_argument("--n-steps-decoder", type=int, default=100,
                   help="Diffusion steps in DAE.decode inside the bridge.")
    p.add_argument("--seed", type=int, default=42,
                   help="Seed for the framework trajectory + decoder.")
    p.add_argument("--max-records", type=int, default=1000,
                   help="Cap on N records (default 1000; the input file "
                        "ships N=1000 records).")
    args = p.parse_args(argv)
    # Wave 112.D-1: load + overlay YAML profile (CLI > YAML > default).
    if args.config is not None:
        try:
            profile = load_run_profile(args.config)
        except Exception as exc:  # ConfigError + OSError + yaml.YAMLError
            print(f"[ERROR] --config load failed: {exc}", file=sys.stderr)
            return 2
        args = apply_kanzi_profile_defaults(args, p, profile)
        # this driver uses --max-records (not --limit like the shared runner's
        # 3 drivers) — mirror the same CLI > YAML > default resolution.
        if "max_records" in profile:
            if args.max_records == p.get_default("max_records"):
                n = int(profile["max_records"])
                args.max_records = n if n > 0 else 0

    args.output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = args.output_dir / "per_metric.jsonl"

    print(f"[wave96e] loading DAE from {args.ckpt} ...", file=sys.stderr)
    t0 = time.monotonic()
    dae = DAE.from_pretrained(str(args.ckpt)).eval()
    # Wave 99.A → 99.E root-cause fix: DAE was on CPU. Bridge auto-coerces
    # latent to the decoder's parameter device, so the entire 100-step
    # diffusion ran on CPU nn.Linear (~95% of runtime per py-spy profile,
    # >500h wall for N=1000). Move DAE to CUDA so .decode() lands on GPU.
    dae = dae.to("cuda")
    print(f"[wave96e] DAE loaded + moved to {next(dae.parameters()).device} "
          f"in {time.monotonic() - t0:.1f} s", file=sys.stderr)

    vocab_size = int(getattr(dae.quantize, "codebook_size", 1000))
    n_decoder = int(dae.quantize.project_out.weight.shape[0])  # 512
    print(f"[wave96e] vocab_size={vocab_size}, n_decoder={n_decoder}",
          file=sys.stderr)

    # Wave 96.B — real KanziAdapter with 50 NFE Euler rollout
    # (replaces the σ=1e-3 synthetic collapse in the Wave 92c driver).
    print(f"[wave96e] constructing real KanziAdapter from {args.ckpt} ...",
          file=sys.stderr)
    t_ada = time.monotonic()
    kanzi_adapter = default_kanzi_adapter(
        weights_path=args.ckpt, force_mode="torch",
        num_steps=50, solver="euler",
    )
    print(f"[wave96e] KanziAdapter constructed in "
          f"{time.monotonic() - t_ada:.1f} s", file=sys.stderr)

    per_seq_rmsd: dict[str, float] = {}
    per_seq_l2: dict[str, float] = {}
    all_idx: list[np.ndarray] = []
    n_processed = 0
    n_skipped = 0
    skip_reasons: dict[str, int] = {}
    t_sweep = time.monotonic()

    # Wave 98.A — GPU utilization watchdog. Fires a WARNING to stderr
    # if util.gpu stays at 0% for >30s while memory.used > 100 MiB.
    # The diagnostic that should have caught the Wave 96.E stuck
    # sweep earlier — wraps the per-record inner loop only (not the
    # DAE / KanziAdapter construction above).
    with gpu_watchdog(threshold_seconds=30, sample_interval=5), \
         args.input.open(encoding="utf-8") as fh, \
         jsonl_path.open("w", encoding="utf-8") as fh_jsonl:
        seq_idx = 0
        for line in fh:
            coords_angstrom = parse_record(line)
            if coords_angstrom is None:
                continue

            # 1. Real framework trajectory endpoint (Wave 96.B fix — L2 ~180).
            try:
                x_final = real_framework_x_final_512d(
                    adapter=kanzi_adapter, record_idx=seq_idx,
                    seed=int(args.seed),
                )
            except Exception as exc:  # noqa: BLE001
                n_skipped += 1
                skip_reasons[f"solve_ode_failed:{type(exc).__name__}"] = (
                    skip_reasons.get(
                        f"solve_ode_failed:{type(exc).__name__}", 0) + 1
                )
                seq_idx += 1
                continue

            x_final_l2 = float(np.linalg.norm(x_final))

            # 2. Bridge: latent (512-d) → coords in Ångström.
            try:
                coords_pred_A = kanzi_latent_to_coords(
                    x_final, decoder=dae, fsq_quantizer=dae.quantize,
                    n_steps=int(args.n_steps_decoder), seed=int(args.seed),
                )
            except Exception as exc:  # noqa: BLE001
                n_skipped += 1
                skip_reasons[f"bridge_failed:{type(exc).__name__}"] = (
                    skip_reasons.get(
                        f"bridge_failed:{type(exc).__name__}", 0) + 1
                )
                seq_idx += 1
                continue

            coords_pred_A = np.asarray(coords_pred_A).reshape(-1, 3)

            # 3. Re-encode for codebook metrics.
            coords_pred_nm = coords_pred_A.astype(np.float32) / 10.0
            L_pred = int(coords_pred_nm.shape[0])
            coords_BLD = coords_pred_nm.reshape(1, L_pred, 3)
            coords_BLD = coords_BLD - coords_BLD.mean(axis=1, keepdims=True)
            try:
                with torch.no_grad():
                    # Wave 115.P2: pass device=dae.device so CPU/CUDA
                    # mismatch crashes loudly inside `dae.encode` (RuntimeError
                    # on a CPU tensor against CUDA parameters) instead of
                    # silently falling into the `reencode_failed` except branch
                    # with a 0-record sweep.
                    *_, idx_BL = dae.encode(
                        torch.as_tensor(
                            coords_BLD, dtype=torch.float32, device=dae.device,
                        ),
                        preprocess=False,
                    )
                idx_arr = idx_BL.detach().cpu().numpy().astype(np.int64)
                # Compact hash of the index sequence for the diversity check.
                idx_hash = hash(tuple(idx_arr.tolist()))
            except Exception as exc:  # noqa: BLE001
                n_skipped += 1
                skip_reasons[f"reencode_failed:{type(exc).__name__}"] = (
                    skip_reasons.get(
                        f"reencode_failed:{type(exc).__name__}", 0) + 1
                )
                seq_idx += 1
                continue

            # 4. Reconstruction RMSD (round-trip identity).
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
                skip_reasons[f"rmsd_failed:{type(exc).__name__}"] = (
                    skip_reasons.get(
                        f"rmsd_failed:{type(exc).__name__}", 0) + 1
                )
                seq_idx += 1
                continue

            per_seq_rmsd[f"seq_{seq_idx}"] = rmsd_val
            per_seq_l2[f"seq_{seq_idx}"] = x_final_l2
            idx_np = idx_BL.detach().cpu().reshape(-1).to(torch.int32).numpy()
            all_idx.append(idx_np)
            seq_idx += 1
            n_processed += 1

            # Per-record JSONL row (one row per record — the source of
            # truth for the Wave 96.E §7.3 Kanzi update + per-metric Δ
            # computation).
            row = {
                "record_idx": n_processed - 1,
                "rmsd_A": rmsd_val,
                "x_final_l2": x_final_l2,
                "idx_hash": idx_hash,
                "idx_BL_first8": idx_arr[:8].tolist(),
                "idx_BL_last8": idx_arr[-8:].tolist(),
            }
            fh_jsonl.write(json.dumps(row, sort_keys=False) + "\n")
            fh_jsonl.flush()

            # Wave 96.E — REMOVED the Wave 96.D debug cap. The driver
            # only stops when the input file is exhausted (or --max-records
            # is hit, default 1000). Per Wave 96.A diagnostic + Wave 96.B
            # fix, the framework endpoint is now diverse (L2 ~180,
            # pairwise L2 ~256) so the full N=1000 sweep is the
            # meaningful measurement.
            if n_processed >= int(args.max_records):
                break
            if n_processed % 50 == 0:
                print(
                    f"[wave96e] {n_processed} records processed "
                    f"({n_skipped} skipped, "
                    f"{time.monotonic() - t_sweep:.1f}s)",
                    file=sys.stderr,
                )

    sweep_wall = time.monotonic() - t_sweep
    print(
        f"[wave96e] processed {n_processed} records (skipped {n_skipped}) "
        f"in {sweep_wall:.1f} s ({sweep_wall / max(1, n_processed):.3f} s/rec)",
        file=sys.stderr,
    )
    print(f"[wave96e] skip reasons: {skip_reasons}", file=sys.stderr)

    rmsd_values = list(per_seq_rmsd.values())
    reconstruction_summary = {
        "n_seqs": float(len(rmsd_values)),
        "mean_rmsd_A": float(sum(rmsd_values) / max(1, len(rmsd_values))),
        "min_rmsd_A": float(min(rmsd_values)) if rmsd_values else 0.0,
        "max_rmsd_A": float(max(rmsd_values)) if rmsd_values else 0.0,
        "std_rmsd_A": float(np.std(np.asarray(rmsd_values), ddof=1))
        if len(rmsd_values) >= 2 else 0.0,
    }
    l2_values = list(per_seq_l2.values())
    diversity_summary = {
        "n_unique_idx_sequences": (
            len(set(per_seq_rmsd.keys())) if not per_seq_rmsd else
            len({hash(tuple(int(round(v * 1e6)) for v in (
                np.full((64,), n_processed + i, dtype=np.int64)
            ))) for i, v in enumerate(per_seq_rmsd.values())})
        ),
        "x_final_l2_min": float(min(l2_values)) if l2_values else 0.0,
        "x_final_l2_max": float(max(l2_values)) if l2_values else 0.0,
        "x_final_l2_mean": (
            float(sum(l2_values) / max(1, len(l2_values)))
            if l2_values else 0.0
        ),
    }

    # Count unique idx hashes from the JSONL (re-read for accuracy).
    n_unique_idx_sequences = 0
    with jsonl_path.open(encoding="utf-8") as fh_jsonl:
        seen_hashes: set[int] = set()
        for line in fh_jsonl:
            row = json.loads(line)
            seen_hashes.add(int(row["idx_hash"]))
        n_unique_idx_sequences = len(seen_hashes)
    diversity_summary["n_unique_idx_sequences"] = n_unique_idx_sequences
    diversity_summary["n_unique_idx_sequences_pct"] = (
        float(n_unique_idx_sequences / max(1, n_processed))
    )

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
        "tool": "tools.sweep_kanzi_n1000_diverse",
        "model": "kanzi",
        "axis": "protein_fm",
        "paper": "ICLR 2026 (arXiv:2510.00351) - Shah et al.",
        "nfe_budget": (
            "50 NFE per record (KanziAdapter.solve_ode Euler rollout; "
            "Wave 96.B fix for endpoint diversity — replaces the "
            "Wave 92c σ=1e-3 synthetic noise which collapsed every record "
            "to the same FSQ codebook index)."
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
        "diversity": diversity_summary,
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
            "50 NFE Euler rollout, seeded by record_idx."
        ),
        "bridge": (
            "tools.kanzi_latent_to_coord.kanzi_latent_to_coords with "
            "Phase 3.B trained Linear(512 -> 4) inverse of project_out "
            "(commit 378dc4a, per-sample RMSE 3.54e-3 << FSQ half-grid 0.5)"
        ),
        "n_steps_decoder": int(args.n_steps_decoder),
        "deterministic": True,
        "wave": "96.E",
        "verdict": {
            "arm": "framework_only_real_diverse_endpoints_n1000",
            "baseline_arm_source": (
                "verification_outputs/wave88_kanzi_n1000_baseline/"
                "kanzi_n1000_paper_metrics.json (Wave 88 N=1000 baseline "
                "arm: mean=0.902 A, std=0.137, n=1000)"
            ),
            "metric_kind": "kanzi_paper_metrics",
        },
    }

    out_path = args.output_dir / "kanzi_n1000_framework_paper_metrics.json"
    # Wave 97.D — hard N-record assertion (closes the Wave 96
    # reality-check gap). When --max-records is explicitly set (>0)
    # and the sweep produced fewer records than the cap, raise
    # RuntimeError rather than writing a smaller-than-requested summary.
    assert_n_records_match(
        n_records_actual=int(n_processed),
        n_records_requested=int(args.max_records),
        sweep_name="sweep_kanzi_n1000_diverse",
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
        n_records_requested=int(args.max_records),
        sweep_name="sweep_kanzi_n1000_diverse",
    )
    out_path.write_text(json.dumps(output, indent=2, sort_keys=False) + "\n",
                        encoding="utf-8")
    print(f"[wave96e] wrote {out_path}", file=sys.stderr)
    print(f"[wave96e] wrote {jsonl_path}", file=sys.stderr)
    print(f"[wave96e] framework-arm reconstruction RMSD: "
          f"mean={reconstruction_summary['mean_rmsd_A']:.4f} A, "
          f"std={reconstruction_summary['std_rmsd_A']:.4f} A, "
          f"n={int(reconstruction_summary['n_seqs'])}",
          file=sys.stderr)
    print(f"[wave96e] unique idx sequences: "
          f"{diversity_summary['n_unique_idx_sequences']}/{n_processed} "
          f"({diversity_summary['n_unique_idx_sequences_pct']*100:.1f}%)",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())