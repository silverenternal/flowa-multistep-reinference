"""R2 / GAP-23 — valid paired Kanzi single-pass vs restart-blend (Eq. 1 vs Eq. 2).

Motivation
----------
The historical R2 headline (``paper-data/R2_kanzi_rmsd/``) paired two
*unrelated* quantities: the autoencoder round-trip of an **input**
record against the round-trip of a **generated** structure from a
random latent. ``corr(baseline_i, framework_i) ≈ 0`` proved the pairing
was spurious (``docs/audit/gap23-r2-paired-comparison-invalid.md``).

This driver rebuilds R2 as the **paper-canonical** comparison in
``docs/drafts/paper-A-final.md`` §2.2:

* baseline (Eq. 1) — single-pass ``x_T = Φ_T^{v_θ}(x_0)``;
* framework (Eq. 2) — restart blend
  ``x_0^{(k)} = B_m(x_T^{(k-1)}, x_0^{fresh,(k)})``,
  ``x_T^{(k)} = Φ_T^{v_θ}(x_0^{(k)})``, ``k = 1..n_rounds``;

**both arms start from the same per-record ``x_0``** and the framework's
total NFE budget equals the baseline's (no post-loop re-anchor). The
per-record metric is the Kanzi autoencoder round-trip Kabsch RMSD (Å)
of each arm's endpoint, mirroring ``tools/_kanzi_sweep_runner.py``
``:875-952``.

It reuses the canonical paired primitives in ``tools/eval/``
(``_build_initial_state_and_condition``, ``_solve_baseline``,
``_solve_framework``) rather than re-implementing the solver loop. The
two additive ``_solve_*`` kwargs this needs (``bundle``,
``restart_from_endpoint``, ``reanchor``) are documented there.

Outputs (``--output-dir``, default ``verification_outputs/
r2-kanzi-paired-restartblend-n1000``):

* ``records.jsonl`` — per-record rows (resume cursor);
* ``paired_per_record.csv`` — ``seq_idx,baseline_rmsd_A,framework_rmsd_A,paired_diff_A``;
* ``kanzi_n1000_baseline_paper_metrics.json`` /
  ``kanzi_n1000_framework_paper_metrics.json`` — each carrying
  ``per_seq_rmsd_A`` so the existing
  ``scripts/wave218_p3_paired_ttest.py`` runs unchanged.

This tool never overwrites a prior output directory's summary JSONs
unless ``--resume`` is passed (bounded, restartable, additive).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
_KANZI_SRC = _REPO_ROOT / "data" / "kanzi_upstream" / "src"

_DEFAULT_CKPT = _REPO_ROOT / "data" / "kanzi_ckpt" / "cleaned_model.pt"
_DEFAULT_OUT = _REPO_ROOT / "verification_outputs" / "r2-kanzi-paired-restartblend-n1000"

#: Fixed batch id so the per-record ``sample_id`` fully determines ``x_0``
#: (``KanziAdapter.build_initial_state`` seeds ``x0`` from
#: ``seed_from_ids(batch_id, sample_id, seed_offset)``).
_BATCH_ID = "kanzi_paired_restartblend"


def _ensure_sys_path() -> None:
    """Put the vendored ``kanzi`` src on ``sys.path`` (idempotent).

    Deferred to call time (not module import) so this module stays
    importable in the torch-free framework pytest env — importing
    ``adaptive_reflow.adapters.kanzi`` with the kanzi src on the path but
    without torch raises inside its ``_gpt_prior_already_installed`` probe.
    """
    kanzi_src_str = str(_KANZI_SRC)
    if kanzi_src_str not in sys.path:
        sys.path.insert(0, kanzi_src_str)



def _endpoint_array(adapter: Any, trace: Any) -> np.ndarray:
    """Return the trajectory endpoint (``trajectory[-1]``) of a solve trace.

    Reads the adapter's native-state cache directly (the same accessor the
    eval-package ``KanziGlue`` uses at ``tools/eval/metrics.py:1402``).
    """
    states = getattr(adapter, "_native_states", None)
    entry = states.get(str(trace.native_state_digest)) if states is not None else None
    if entry is None or "trajectory" not in entry:
        raise RuntimeError(
            f"missing native trajectory for digest {trace.native_state_digest!r}"
        )
    return np.asarray(entry["trajectory"], dtype=np.float64)[-1]


def _kanzi_roundtrip_rmsd_A(
    dae: Any,
    endpoint: Any,
    *,
    torch: Any,
    nfe_steps: int,
    device: Any,
    seed: int | None = None,
) -> float:
    """Kanzi autoencoder round-trip Kabsch RMSD (Å) of a ``(L, 3)`` nm endpoint.

    Mirrors ``tools/_kanzi_sweep_runner.py:875-952``: mean-centre the
    endpoint (nm) → ``dae.encode(preprocess=False)`` → ``dae.decode`` →
    mean-centre both in Å → ``kabsch_rmsd``.

    ``seed`` — the FSQ quantizer / decoder rollout consume the global
    torch RNG, so the round-trip is non-deterministic without a seed.
    When supplied, ``torch.manual_seed(seed)`` is applied before both the
    encode and the decode (the runner's per-record seeding contract), which
    makes the metric reproducible and gives both arms a common random
    number for the same record.
    """
    from kanzi import kabsch_rmsd  # type: ignore  # local import: sidecar dep

    coords_nm = np.asarray(endpoint, dtype=np.float32).reshape(-1, 3)
    L = int(coords_nm.shape[0])
    coords_BLD = coords_nm.reshape(1, L, 3)
    coords_BLD = coords_BLD - coords_BLD.mean(axis=1, keepdims=True)
    x_t = torch.as_tensor(coords_BLD, dtype=torch.float32, device=device)
    with torch.no_grad():
        if seed is not None:
            torch.manual_seed(int(seed))
        *_, idx_BL = dae.encode(x_t, preprocess=False)
        if seed is not None:
            torch.manual_seed(int(seed))
        recon = dae.decode(idx_BL, n_steps=int(nfe_steps)).detach().cpu().numpy() * 10.0
    recon_A = recon.reshape(-1, 3).astype(np.float64)
    pred_A = coords_nm.astype(np.float64) * 10.0
    recon_A = recon_A - recon_A.mean(axis=0, keepdims=True)
    pred_A = pred_A - pred_A.mean(axis=0, keepdims=True)
    return float(
        kabsch_rmsd(
            torch.from_numpy(pred_A.astype(np.float32)),
            torch.from_numpy(recon_A.astype(np.float32)),
        )
    )


def run_paired_sweep(
    *,
    output_dir: str | Path,
    seed: int = 42,
    max_records: int = 1000,
    nfe: int = 50,
    n_rounds: int = 3,
    ckpt_path: str | Path | None = None,
    resume: bool = False,
    adapter: Any = None,
    dae: Any = None,
    metric_fn: Any = None,
) -> dict[str, Any]:
    """Run the paired single-pass vs restart-blend sweep.

    ``adapter`` / ``dae`` / ``metric_fn`` are injection seams for the
    CPU test (they default to the real Kanzi adapter, the eval-package
    DAE, and :func:`_kanzi_roundtrip_rmsd_A`). Returns a summary dict.
    """
    from tools.eval.baseline import (
        _build_initial_state_and_condition,
        _solve_baseline,
    )
    from tools.eval.framework import _solve_framework

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    device: Any = "cpu"
    if adapter is None or dae is None or metric_fn is None:
        import torch

        _ensure_sys_path()
        device = "cuda" if torch.cuda.is_available() else "cpu"
        ckpt = Path(ckpt_path) if ckpt_path is not None else _DEFAULT_CKPT
        if adapter is None:
            from adaptive_reflow.adapters.kanzi import default_kanzi_adapter

            adapter = default_kanzi_adapter(
                weights_path=ckpt,
                force_mode="torch",
                num_steps=int(nfe),
                solver="euler",
            )
        # Place the velocity model on the target device. ``KanziAdapter``
        # leaves it on CPU (``kanzi.py:1599`` never moves ``self._model``),
        # even though ``_torch_velocity_field`` documents the intent that
        # it lives on CUDA (``kanzi.py:1147``, Wave 112.C-1). The per-record
        # ODE solve is ~126× slower on CPU (NFE=50: 324 s CPU vs 2.6 s
        # CUDA), so the placement is the difference between a ~14 h and a
        # ~2 h N=1000 run.
        _model = getattr(adapter, "_model", None)
        if _model is not None and hasattr(_model, "to") and str(device).startswith("cuda"):
            adapter._model = _model.to(device)
        if dae is None:
            from tools.eval.metrics import _load_kanzi_dae

            dae = _load_kanzi_dae(ckpt).to(device).eval()
        if metric_fn is None:

            def metric_fn(endpoint: Any, seq_idx: int | None = None) -> float:  # type: ignore[misc]
                return _kanzi_roundtrip_rmsd_A(
                    dae,
                    endpoint,
                    torch=torch,
                    nfe_steps=int(nfe),
                    device=device,
                    seed=(
                        int(seed) * 1_000_003 + int(seq_idx)
                        if seq_idx is not None
                        else None
                    ),
                )

    records_path = out / "records.jsonl"
    per_seq_base: dict[str, float] = {}
    per_seq_fw: dict[str, float] = {}
    if resume and records_path.exists():
        for line in records_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            per_seq_base[f"seq_{row['seq_idx']}"] = float(row["baseline_rmsd_A"])
            per_seq_fw[f"seq_{row['seq_idx']}"] = float(row["framework_rmsd_A"])

    n_processed = 0
    n_skipped = 0
    skip_reasons: dict[str, int] = {}
    t0 = time.monotonic()
    with records_path.open("a" if resume else "w", encoding="utf-8") as fh:
        for i in range(int(max_records)):
            key = f"seq_{i}"
            if key in per_seq_base:
                n_processed += 1
                continue
            try:
                # Same x_0 for both arms (per-record sample_id).
                bundle, _ = _build_initial_state_and_condition(
                    adapter,
                    seed=int(seed),
                    nfe=int(nfe),
                    batch_id=_BATCH_ID,
                    sample_id=f"rec{i}",
                )
                base_trace, _ = _solve_baseline(
                    adapter, nfe=int(nfe), seed=int(seed), bundle=bundle,
                )
                base_rmsd = float(
                    metric_fn(_endpoint_array(adapter, base_trace), seq_idx=i)
                )
                fw_trace, _ = _solve_framework(
                    adapter,
                    nfe=int(nfe),
                    seed=int(seed),
                    n_rounds=int(n_rounds),
                    bundle=bundle,
                    restart_from_endpoint=True,
                    reanchor=False,
                )
                fw_rmsd = float(
                    metric_fn(_endpoint_array(adapter, fw_trace), seq_idx=i)
                )
            except Exception as exc:  # noqa: BLE001
                n_skipped += 1
                reason = f"{type(exc).__name__}:{exc}"
                skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
                continue
            if not (np.isfinite(base_rmsd) and np.isfinite(fw_rmsd)):
                n_skipped += 1
                skip_reasons["non_finite_rmsd"] = skip_reasons.get("non_finite_rmsd", 0) + 1
                continue
            per_seq_base[key] = base_rmsd
            per_seq_fw[key] = fw_rmsd
            n_processed += 1
            fh.write(
                json.dumps(
                    {
                        "seq_idx": i,
                        "baseline_rmsd_A": base_rmsd,
                        "framework_rmsd_A": fw_rmsd,
                        "paired_diff_A": fw_rmsd - base_rmsd,
                    }
                )
                + "\n"
            )
            fh.flush()
    wall = time.monotonic() - t0

    keys = sorted(per_seq_base, key=lambda k: int(k.split("_")[1]))
    base_arr = np.array([per_seq_base[k] for k in keys], dtype=np.float64)
    fw_arr = np.array([per_seq_fw[k] for k in keys], dtype=np.float64)
    if base_arr.size > 1 and base_arr.std() > 0 and fw_arr.std() > 0:
        corr = float(np.corrcoef(base_arr, fw_arr)[0, 1])
    else:
        corr = float("nan")

    common_meta: dict[str, Any] = {
        "tool": "tools.sweep_kanzi_paired_restartblend",
        "measurement_scope": (
            "paper §2.2 Eq. 1 (baseline, single-pass) vs Eq. 2 "
            "(framework, restart-blend) from the SAME per-record x_0; "
            "metric = Kanzi autoencoder round-trip Kabsch RMSD (Å)"
        ),
        "seed": int(seed),
        "nfe_budget": int(nfe),
        "n_rounds_framework": int(n_rounds),
        "max_records": int(max_records),
        "n_records_processed": int(n_processed),
        "n_records_skipped": int(n_skipped),
        "skip_reasons": skip_reasons,
        "sweep_wallclock_s": float(wall),
        "device": str(device),
        "paired_pearson_r": corr,
    }
    baseline_json = dict(common_meta)
    baseline_json["arm"] = "baseline_single_pass"
    baseline_json["per_seq_rmsd_A"] = per_seq_base
    framework_json = dict(common_meta)
    framework_json["arm"] = "framework_restart_blend"
    framework_json["per_seq_rmsd_A"] = per_seq_fw
    (out / "kanzi_n1000_baseline_paper_metrics.json").write_text(
        json.dumps(baseline_json, indent=2), encoding="utf-8"
    )
    (out / "kanzi_n1000_framework_paper_metrics.json").write_text(
        json.dumps(framework_json, indent=2), encoding="utf-8"
    )
    csv_lines = ["seq_idx,baseline_rmsd_A,framework_rmsd_A,paired_diff_A"]
    for k in keys:
        idx = k.split("_")[1]
        csv_lines.append(
            f"{idx},{per_seq_base[k]:.6f},{per_seq_fw[k]:.6f},"
            f"{per_seq_fw[k] - per_seq_base[k]:.6f}"
        )
    (out / "paired_per_record.csv").write_text(
        "\n".join(csv_lines) + "\n", encoding="utf-8"
    )

    summary = {
        **common_meta,
        "output_dir": str(out),
        "baseline_mean_rmsd_A": (
            float(base_arr.mean()) if base_arr.size else float("nan")
        ),
        "framework_mean_rmsd_A": (
            float(fw_arr.mean()) if fw_arr.size else float("nan")
        ),
    }
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(_DEFAULT_OUT))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-records", type=int, default=1000)
    parser.add_argument("--nfe", type=int, default=50)
    parser.add_argument("--n-rounds", type=int, default=3)
    parser.add_argument("--ckpt", default=str(_DEFAULT_CKPT))
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)

    summary = run_paired_sweep(
        output_dir=args.output_dir,
        seed=int(args.seed),
        max_records=int(args.max_records),
        nfe=int(args.nfe),
        n_rounds=int(args.n_rounds),
        ckpt_path=args.ckpt,
        resume=bool(args.resume),
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
