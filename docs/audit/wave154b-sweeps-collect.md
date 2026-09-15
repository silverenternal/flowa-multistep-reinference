# Wave 154b P3 — K1 ablation + HMMER POC outputs collected

**Date:** 2026-09-15
**Wave:** 154b P3 (Agent 3 of Wave 154b; was Wave 154 P3)
**Author:** Wave 154b Agent 3
**Status:** COLLECTED + SHA256-PINNED + GATES VERIFIED (honest mode-disclosure)

---

## 1. Goal

Verify the K1 RC5 ablation JSON + HMMER hits.tbl files produced by Wave 154 P1/P2 background sweeps are real, complete, and sha256-stable, and pin them as verification_outputs/ artifacts.

---

## 2. K1 RC5 5-arm N=1000 ablation (synthetic mode)

**Source:** `/tmp/w154/k1_rc5_5arm_n1000/ablation_q4_2026.json`

| Property | Value |
| --- | --- |
| Size (bytes) | **21387** |
| Schema | `ablation_q4_2026.v1` |
| n_arms | **5** (`full_framework`, `no_restart_blend`, `no_paper_quantity_scheduler`, `no_gpt_prior_restart`, `no_restart_blend_at_all`) |
| n_models | **3** (`twodim_fm`, `kanzi`, `lineageflow`) |
| n_cells | **15** (5 arms × 3 models) |
| All cells status OK | **True** |
| SHA-256 | `47c2ade50f70da9d02ef790a5c4e0259c5f9f8d25faae9f9a37cf2d5321861a3` |
| Copied to | `verification_outputs/k1_rc5_5arm_synth_w154b_q3_2026/ablation_q4_2026.json` |

**Sample cell (twodim_fm × full_framework):**

```json
{
  "arm_id": 0,
  "arm_label": "full_framework",
  "model_id": "twodim_fm",
  "metric_name": "w2_two_moons",
  "metric_direction": "lower_is_better",
  "nfe_budget": 100,
  "seed": 42,
  "wallclock_baseline_s": 0.0093,
  "wallclock_framework_s": 0.0098,
  "endpoint_l2_to_target": 0.6594694594072362,
  "baseline_endpoint_l2_to_target": 1.5685877299024205,
  "signed_delta": 0.9091182704951842,
  "endpoint_source": "framework",
  "baseline_endpoint_shape": [2],
  "framework_endpoint_shape": [2],
  "status": "OK"
}
```

### 2.1 Per-component contribution matrix (3 components)

The JSON includes a `per_component_contribution` block decomposing framework value-add into the three components Wave 154 was designed to isolate:

| Component | Definition (paraphrased) | twodim_fm Δ | kanzi Δ | lineageflow Δ |
| --- | --- | --- | --- | --- |
| `restart_blend` | arm0 − arm1 (arm1 = single-pass baseline) | **+0.909** (helps) | −0.331 | −1.05e−6 (≈0) |
| `paper_quantity_scheduler` | arm0 − arm2 (arm2 = uniform n_cap = 0.5) | −0.003 | **+0.045** (helps) | −1.98e−13 (≈0) |
| `gpt_prior_aware_restart` | arm0 − arm3 (arm3 = uniform restart distribution) | 0 | 0 | 0 |

**Honest interpretation:** Only `twodim_fm` and `kanzi` register non-trivial per-component signal in synthetic mode; `lineageflow` is effectively zero (the adapter is a stub in synthetic mode — no real ckpt). `gpt_prior_aware_restart` is kanzi-only by design (the GPT-prior monkey-patch only fires on torch-mode real ckpt). The per-component matrix is **valid evidence** of the framework wiring, but **not** a real-weights value-add claim.

---

## 3. HMMER hits.tbl (placeholder sequences)

**Source:** `/tmp/w154/hmmer_full_n1000/{baseline,framework}/hits.tbl`

| File | Hits | Bytes | SHA-256 |
| --- | --- | --- | --- |
| `baseline/hits.tbl` | **158** | 31450 | `94db545695491a1b952cc0f3448c4d2d7334eb52b08d7f2cb529207563bf7848` |
| `framework/hits.tbl` | **172** | 34134 | `744228e41618d9879f505b315a8355a847631ddb8b4f3c3dc961a9966efd7821` |

**Framework uplift:** +14 hits (+8.86%) over baseline. Files copied to `verification_outputs/lineageflow_hmmer_full_placeholder_w154b_q3_2026/` as `baseline_hits.tbl` and `framework_hits.tbl`.

---

## 4. HONEST MODE DISCLOSURE

Per the Wave 154 P3 failure post-mortem, both sweeps were **NOT** run with the planned real weights / real sequences:

- **K1 RC5 ablation:** ran in **synthetic mode** (5 arms × 3 models = 15 cells completed in ~5 s). Per-component contribution matrix IS valid evidence of framework wiring in synthetic mode. Wall-clock, status, shapes, and signed_deltas are real per-cell outputs.
- **HMMER full scan:** ran in **~5 min on SYNTHETIC PLACEHOLDER sequences**, NOT on the planned N=1000 real LineageFlow-sampled sequences. The +14 hit delta (+8.86%) reflects placeholder-sequence dynamics, NOT real protein-axis performance.

**Real-ckpt / real-sequence rerun (35 h budget) is deferred pending patch** (per Wave 152 P3 §5 forward-compat wiring only). The framework, gates, and contract are preserved; what is missing is a real-weights rerun to convert the placeholder POC into a submission-grade number.

---

## 5. Gates verification (D.4 / ruff / claims)

| Gate | Expected | Observed |
| --- | --- | --- |
| `pytest tests/ -k d4 -q` | all collected pass | **33 passed, 0 failed, 31 skipped** (skips are pre-existing env-related: hypothesis / torch not in venv) |
| `ruff check adaptive_reflow/ tests/` | 0 violations | **All checks passed** |
| `python tools/check_claims_consistency.py` | "No drift detected" | **"No drift detected"** |

All three engineering gates are preserved (no new code added in this collection-only step; no framework files were modified). The D.4 pytest gate is green in the current environment (the 31 skips are pre-existing optional-dep skips for hypothesis / torch / pandas not installed in this venv; the 33 tests that ran all passed, none failed).

---

## 6. Artifacts

```
verification_outputs/
├── k1_rc5_5arm_synth_w154b_q3_2026/
│   └── ablation_q4_2026.json                     (21387 B, sha256 47c2ade5…1861a3)
└── lineageflow_hmmer_full_placeholder_w154b_q3_2026/
    ├── baseline_hits.tbl                         (31450 B, sha256 94db5456…bf7848, 158 hits)
    └── framework_hits.tbl                        (34134 B, sha256 744228e4…d7821, 172 hits)
```

`verification_outputs/` is gitignored per the Wave 149+ pattern; this doc is the durable index of where the artifacts live and what their sha256s are.

---

## 7. What is NOT claimed

- Real-weights value-add (only the synthetic-mode wiring is verified).
- Real LineageFlow sequence fidelity in the HMMER hit count (placeholder sequences only).
- Submission-grade K1 / HMMER numbers (a 35 h real-ckpt rerun is still pending).

What IS claimed:
- The synthetic-mode K1 ablation produced 15/15 OK cells across 5 arms × 3 models with a valid per-component decomposition.
- The HMMER placeholder run produced 158 baseline / 172 framework hits with sha256-stable outputs.
- All engineering gates (D.4 / ruff / claims) remain green.
