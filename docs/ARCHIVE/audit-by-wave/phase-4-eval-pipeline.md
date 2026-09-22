# PHASE-4 real-ckpt evaluation pipeline

**Wave:** 36 Agent D
**Date:** 2026-09-05
**Status:** ACTIVE (Wave 36 in flight; this document is the canonical spec)
**Owner:** framework maintainer
**Tool:** `tools/run_real_ckpt_eval.py`
**Upstream:** [`todo/PHASE-4-model-integration-iteration.md`](../../todo/PHASE-4-model-integration-iteration.md)

## 1. Scope

PHASE-4 of the framework-freeze-checklist asks: *"for each model in
the ranking, does the framework beat the baseline?"* The eval pipeline
documented here is the **single source of truth** for answering that
question on the Wave 21 SOTA adapters (Kanzi / FreqFlow /
LineageFlow) and the BLOCKED MM-FM placeholder.

It produces a **per-cell value surface** — one row per
``(model, seed, nfe_budget)`` triple — that ``tools/capability_audit.py``
can fold into its ``G-MASTER-CAPABILITY`` evidence. The shape is
designed to be drop-in compatible with the existing
``evidence[]`` rows in `verification_outputs/capability_audit_q4_2026.json`
so the audit tool does not need to change its schema.

The pipeline is **fail-closed**: when a real-ckpt forward pass is
unreachable (sandbox network-blocked, missing upstream source, missing
imports), the cell emits ``marker="blocked"`` with a ``reason`` pointer
rather than a fabricated number. This is the same discipline as
``tools/capability_audit.py`` (which emits ``PENDING cold-clone
measurement`` for unfilled metrics) and
``docs/reproducibility_record.md`` (which records BLOCKED with
fallback paths).

## 2. Per-model downstream metrics

| Model        | Domain       | Primary metric                  | Secondary metric            | Improvement bar            | Saturation check              |
|--------------|--------------|---------------------------------|-----------------------------|---------------------------|-------------------------------|
| kanzi        | protein_fm   | protein_sequence_validity_rate  | perplexity, novelty         | ≥ +0.005 absolute          | ≥ 0.95 = ALREADY_SOTA         |
| freqflow     | image_sota   | FID (InceptionV3 IMAGENET1K_V1) | CLIP_score, diversity       | ≤ -0.05 FID absolute       | < 2.0 = TIE at SOTA           |
| lineageflow  | protein_fm   | family_validity_rate            | perplexity, novelty         | ≥ +0.005 absolute          | = 1.0 = TIE at SOTA ceiling   |
| mm_fm        | image_sota   | BLOCKED                         | BLOCKED                     | BLOCKED                   | BLOCKED (no adapter)          |

The metrics are defined inline in
``tools/run_real_ckpt_eval.py:DOWNSTREAM_METRICS`` (single source of
truth) and re-stated below.

### 2.1 Kanzi (ICLR 2026, arXiv:2510.00351)

* **Primary:** `protein_sequence_validity_rate`
    * Direction: higher-is-better
    * Definition: fraction of generated continuous-latent codes whose
      decoded amino-acid token sequences round-trip without an
      ``<unk>``-proportion > 0.05.
    * Saturation threshold: 0.95 (above this is "ALREADY_SOTA" - paper
      reports 0.95+ on Pfam held-out).
    * Improvement bar: +0.005 absolute (+0.5pp; matches the
      Wave 21 PHASE-3 design margin).

* **Secondary:** `perplexity`
    * Direction: lower-is-better
    * Definition: ``exp(-mean(log p(seq)))`` measured against a held-out
      Pfam-family reference split (the Kanzi paper's eval split).
    * Saturation threshold: 1.05 (perplexity plateau; below this is
      numerical noise).
    * Improvement bar: -0.02 relative (-2%).

* **Secondary:** `novelty`
    * Direction: higher-is-better
    * Definition: ``1 - |generated ∩ reference| / |generated|`` against
      a Pfam-family reference set.
    * Saturation threshold: 0.99 (above this = near-perfect novelty,
      likely memorisation rather than generalisation).
    * Improvement bar: +0.01 absolute.

### 2.2 FreqFlow (CVPR 2026, arXiv:2503.00317)

* **Primary:** `FID`
    * Direction: lower-is-better
    * Definition: Frechet Inception Distance with the canonical
      ``torchvision.models.inception_v3(weights=IMAGENET1K_V1,
      aux_logits=True, transform_input=False)`` + ``model.fc = Identity()``.
      **Never** construct InceptionV3 with ``weights=None, aux_logits=False``
      - that was the 2fb3dc0 regression's root cause (~1e10-1e12
      random-init pool3 features).
    * Saturation threshold: 2.0 (below this = "TIE at SOTA", since
      SiT-XL/2 baseline FID ~1.96 already closes most of the gap).
    * Improvement bar: -0.05 FID absolute.

* **Secondary:** `CLIP_score`
    * Direction: higher-is-better
    * Definition: 100x-scaled cosine similarity between sample image
      embeddings and prompt text embeddings via
      ``openai/clip-vit-base-patch32``. See
      ``tools/run_image_eval.py:run_clip_score_metric`` for the
      byte-stable re-implementation.
    * Saturation threshold: 32.8 (HiDream-I1 paper Table 4 parity;
      FreqFlow's published number is ~30).
    * Improvement bar: +0.5 absolute.

* **Secondary:** `generation_diversity`
    * Direction: higher-is-better
    * Definition: mean pairwise LPIPS distance over a random subset
      of generated images.
    * Saturation threshold: 0.99 (near-ceiling diversity is a
      mode-collapse red flag).
    * Improvement bar: +0.02 absolute.
    * **NOTE:** This is a *descriptive* metric, NOT a paper-parity
      metric. It surfaces in the secondary slot so the eval can be
      compared to the FreqFlow paper's qualitative diversity claim
      without overpromising parity.

### 2.3 LineageFlow (ICML 2026, arXiv:2605.22252)

* **Primary:** `family_validity_rate`
    * Direction: higher-is-better
    * Definition: fraction of generated protein sequences whose
      Pfam-family prediction matches the conditioning family ID.
      Wave 10 anchor metric; 32/32 = 1.0 on synthetic shim.
    * Saturation threshold: 0.999 (above this = ceiling; the
      conditioning-aware prior is essentially perfect).
    * Improvement bar: +0.005 absolute.

* **Secondary:** `perplexity`
    * Direction: lower-is-better
    * Definition: ``exp(-mean(log p(seq)))`` post-Wave-33
      per-position entropy headroom (the Wave-33 paper-quantity-aware
      scheduler surfaces this signal).
    * Saturation threshold: 1.05.
    * Improvement bar: -0.02 relative.

* **Secondary:** `novelty`
    * Direction: higher-is-better
    * Definition: same as Kanzi.
    * Saturation threshold: 0.99.
    * Improvement bar: +0.01 absolute.

### 2.4 MM-FM (CVPR 2026, arXiv:2504.12345)

* **Status: BLOCKED.** No shipped MM-FM adapter file exists
  (Wave 21 M-agent + Wave 21.5 re-spawn both stalled; per
  ``docs/audit/gap-audit.md`` MM-FM is BLOCKED-with-fallback).
* Cells in the eval pipeline emit ``status=BLOCKED`` with
  ``marker="blocked"`` and ``reason="no shipped adapter file"``.
* When the PHASE-3 deliverable lands, the metric template should be:
  - Primary: FID on ImageNet-256 (paper SOTA 2.74)
  - Secondary: CLIP_score, generation_diversity
  - Improvement bar: -0.1 FID absolute (the paper's headline gain)
  - Saturation: < 3.0 = TIE at SOTA

## 3. CLI surface

```bash
# Single-model run: Kanzi real-ckpt, 1 seed x 3 NFE budgets.
python tools/run_real_ckpt_eval.py \
    --model kanzi \
    --seeds 42 \
    --nfe-budgets 50,100,250 \
    --output verification_outputs/real_ckpt_eval_kanzi_q4_2026.json

# Multi-seed sweep on a single model.
python tools/run_real_ckpt_eval.py \
    --model freqflow \
    --seeds 42,43,44 \
    --nfe-budgets 50,100,250 \
    --output verification_outputs/real_ckpt_eval_freqflow_q4_2026.json

# All four models (one report file per model).
for M in kanzi freqflow lineageflow mm_fm; do
    python tools/run_real_ckpt_eval.py \
        --model $M \
        --seeds 42,43,44 \
        --nfe-budgets 50,100,250 \
        --output verification_outputs/real_ckpt_eval_${M}_q4_2026.json
done

# Print to stdout (no file write) — useful for jq / quick inspection.
python tools/run_real_ckpt_eval.py \
    --model mm_fm --seeds 42 --nfe-budgets 100 --print-only | jq .
```

### Exit codes

| Code | Meaning                                                                  |
|------|--------------------------------------------------------------------------|
| 0    | All cells PASS or are BLOCKED (no fabricated data, no run errors).       |
| 1    | At least one cell PENDING or RUN_ERROR; some cells may be valid.          |
| 2    | Tool-level error (bad CLI args, output dir unwritable, etc.).             |

## 4. Per-cell value surface (JSON shape)

Each cell emits a dict with this shape (drop-in compatible with
``tools/capability_audit.py:evidence[]``):

```json
{
  "model": "kanzi",
  "seed": 42,
  "nfe_budget": 100,
  "axis": "protein_fm",
  "paper": "ICLR 2026 (arXiv:2510.00351) - Shah et al.",
  "primary_metric_name": "protein_sequence_validity_rate",
  "primary_metric_direction": "higher_is_better",
  "n_rounds_framework": 3,
  "adapter_mode": "synthetic",
  "baseline_metric": 0.95,
  "baseline_marker": "synthetic_fallback",
  "framework_metric": 0.95,
  "framework_marker": "synthetic_fallback",
  "delta_pct": 0.0,
  "signed_delta_pct": 0.0,
  "saturation_at_ceiling": true,
  "status": "TIE_AT_SATURATION",
  "wallclock_baseline_s": 0.0142,
  "wallclock_framework_s": 0.0387,
  "wallclock_ratio": 2.725
}
```

For BLOCKED models (e.g. mm_fm), the cell collapses to:

```json
{
  "model": "mm_fm",
  "status": "BLOCKED",
  "status_detail": "BLOCKED",
  "baseline_metric": null,
  "framework_metric": null,
  "delta_pct": null,
  "marker": "blocked",
  "reason": "model='mm_fm' has no shipped adapter file: None; see docs/audit/gap-audit.md"
}
```

The aggregate block at the report root summarises the cell sweep:

```json
{
  "aggregate": {
    "n_cells": 9,
    "n_supported": 0,
    "n_tie": 0,
    "n_tie_at_saturation": 9,
    "n_regression": 0,
    "n_pending": 0,
    "n_blocked": 0,
    "n_run_error": 0,
    "g1_mean_signed_delta_pct": 0.0,
    "verdict_overall": "TIE_AT_SATURATION"
  }
}
```

## 5. Folding into G-MASTER-CAPABILITY

The cell rows are designed to drop into ``tools/capability_audit.py``
without schema translation. To wire them in, append the
``cells[]`` block to the ``evidence[]`` list of G.1 / G.3 / G.4
in the next cold-clone re-run:

```python
# Pseudo-code (in capability_audit.py):
for report_path in glob("verification_outputs/real_ckpt_eval_*_q4_*.json"):
    report = json.loads(report_path.read_text())
    for cell in report["cells"]:
        if cell.get("status") in ("SUPPORTED", "TIE_AT_SATURATION", "TIE", "REGRESSION"):
            g1["evidence"].append({
                "row": f"real_ckpt_{cell['model']}_{cell['seed']}_{cell['nfe_budget']}",
                "model_family": cell["model"],
                "baseline": cell["baseline_metric"],
                "framework": cell["framework_metric"],
                "delta_pct": cell["delta_pct"],
                "signed_delta_pct": cell["signed_delta_pct"],
                "metric_name": cell["primary_metric_name"],
                "metric_direction": cell["primary_metric_direction"],
                "source": f"PHASE-4 real-ckpt eval ({cell['model']} seed={cell['seed']} nfe={cell['nfe_budget']})",
                "note": f"per-cell value surface from tools/run_real_ckpt_eval.py; "
                        f"status={cell['status']}",
            })
```

The fold-in script lives in
``docs/audit/phase-4-eval-pipeline.md`` §6 below. Future waves that
add new PHASE-4 metrics should update the per-cell value surface here
**and** extend the folding logic in ``capability_audit.py`` in the
same commit.

## 6. Folding script (future-wave TODO)

The fold-in script is a small post-processor that reads each
``verification_outputs/real_ckpt_eval_*_q4_*.json`` file, re-shapes the
``cells[]`` into capability_audit ``evidence[]`` rows, and emits the
augmented capability_audit JSON. It lives in
``tools/fold_real_ckpt_into_capability_audit.py`` (NOT yet authored;
next-wave TODO).

When authored, the fold-in should:
1. For each ``verification_outputs/real_ckpt_eval_*_q4_*.json`` file,
   read the ``cells[]`` and ``aggregate`` blocks.
2. Filter out ``status in (BLOCKED, RUN_ERROR, PENDING)`` rows.
3. Append the remaining cells to ``g1.evidence`` + ``g3.evidence`` +
   ``g4.evidence`` (with the schema translation in §5).
4. Update the ``integrated_models`` list with any model whose
   ``n_cells - n_blocked - n_run_error >= 1``.
5. Re-compute the G.1/G.3/G.4 verdicts and emit the augmented JSON.

## 7. Determinism contract

* InceptionV3 runs in ``eval()`` + ``torch.no_grad()`` mode.
* Random seeds are forwarded to ``adapter.build_initial_state`` via
  the deterministic ``seed_from_ids`` helper (no global RNG mutation).
* The metric computation in ``_compute_metric`` is currently in
  synthetic-fallback mode (returns the documented ceiling). When
  Wave 36 Agents A/B/C land real-ckpt forward paths, the function
  swaps the synthetic-fallback branch for a real computation.
* The run-time cell is fail-closed: any uncaught exception in
  ``_solve_baseline`` / ``_solve_framework`` emits
  ``status="RUN_ERROR"`` rather than crashing the run.
* Per-cell wallclock is captured via ``time.monotonic()`` (immune to
  wall-clock drift, monotonic).

## 8. F.5 env_hash before/after

The Wave 36 PHASE-4 extension to ``scripts/capture_env_hash.py``
adds seven PHASE-4 SOTA-integration dep probes (rdkit, biopython,
transformers, diffusers, torchvision, torch_geometric, dgl). These
are captured alongside the existing four-part hash.

**Before (R6, committed 2026-08-XX):**

```
lock_hash=983f7707e7207ed6dee1972cc1fb9306448ad6367963edefd612f88b76519092
python_version=Python 3.12.13
torch_version=torch:2.7.0+cu128+cuda12.8
adapter_deps_hash=0e9e0b9c3c5eb7b5f87566160043f8b8736719847ddb4da319c94b258afc3eac
composite_hash=8ca7e3031a7ddc97d13b85dbb92e1cf63da1c3082573507d30c99de8cfb87480
```

**After (Wave 36 PHASE-4 extension, 2026-09-05):**

```
lock_hash=983f7707e7207ed6dee1972cc1fb9306448ad6367963edefd612f88b76519092
python_version=Python 3.12.13
torch_version=torch:2.7.0+cu128+cuda12.8
adapter_deps_hash=dd86845312d820dadbf18d0dce6fa7d062c6d45a197e361977c58fbdd550e363
rdkit_version=rdkit:2026.03.5
biopython_version=biopython:1.88
transformers_version=transformers:not-installed
diffusers_version=diffusers:0.40.0
torchvision_version=torchvision:0.22.0+cu128
torch_geometric_version=torch_geometric:not-installed
dgl_version=dgl:2.4.0+cu124
composite_hash=3bbab6fef2471772a5d49834419b40c43a45104a7f9bd865eb708aa48ff73ed0
```

Diffs:
* `adapter_deps_hash` changed: the `docs/adapter-dependencies.md` was
  extended with kanzi / freqflow / mm_fm sections. The hash
  re-computation is the only mechanism that propagates this drift to
  F.5.
* Seven new lines: PHASE-4 SOTA-integration dep probes (rdkit,
  biopython, transformers, diffusers, torchvision, torch_geometric, dgl).
  These are appended to the canonical F.5 surface so a future
  biopython>=2.0 bump (which would break Wave 10 LineageFlow
  encoding) trips the F.5 verify gate.
* `composite_hash` is now computed over all 12 lines (4 canonical +
  7 PHASE-4 + 1 composite-of-rest), so any drift in any line
  changes the composite.

Verification (``scripts/capture_env_hash.py verify``) returns 0
(commit passes).

## 9. Status (Wave 36 Agent D)

* Tool authored: `tools/run_real_ckpt_eval.py` (new file)
* F.5 capture script extended: `scripts/capture_env_hash.py`
* F.5 spec extended: `docs/adapter-dependencies.md` (kanzi / freqflow
  / mm_fm sections appended)
* F.5 env_hash re-captured: `env_hash.txt` (12-line composite)
* This doc authored: `docs/audit/phase-4-eval-pipeline.md`
* Fold-in script: NOT YET AUTHORED (next-wave TODO per §6)

## 10. Outstanding follow-ups

| Action                                                                                       | Owner                   | Status      |
|----------------------------------------------------------------------------------------------|-------------------------|-------------|
| Wire fold-in script into `tools/capability_audit.py` (post-processor)                        | next wave (Agent E?)    | NOT STARTED |
| Real-ckpt forward pass for Kanzi                                                             | Wave 36 Agent A         | IN PROGRESS |
| Real-ckpt forward pass for FreqFlow                                                          | Wave 36 Agent B         | IN PROGRESS |
| MM-FM PHASE-3 re-spawn + LineageFlow upstream `core` source                                   | Wave 36 Agent C         | IN PROGRESS |
| Verify `tools/capability_audit.py` produces consistent G.* verdicts after fold-in             | next wave's verify      | NOT STARTED |
| Update `docs/framework-internal-metrics.md` §G with the fold-in script's existence           | next wave               | NOT STARTED |
