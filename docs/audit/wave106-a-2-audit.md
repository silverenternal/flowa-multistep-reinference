# Wave 106.A.2 — docs/tools vs verification_outputs/* data-misalignment audit

**Date:** 2026-09-11
**Author:** Wave 106.A.2 Agent
**Role:** READ-ONLY audit. Find every place where `docs/`, `cover_letter.md`, `submission_checklist.md` claim a number that does NOT match the corresponding `verification_outputs/*.json` file. **No source code edits, no docs edits, no commits.**
**Branch:** main
**Latest commit on main:** `d6926925` (Wave 101/102 final: submission_checklist Tier-3 cells 12/12 marked with actual data state)
**Files audited (reads only):**

| File | Bytes | Lines | Role |
|---|---|---:|---|
| `docs/paper-draft.md` | ~442KB | 5270 | §1–§16 paper body + supplementary tables |
| `docs/CONSOLIDATED_RESULTS.md` | — | 3595 | Per-wave + per-cell numerical ledger |
| `docs/baseline-audit-report.md` | — | 2945 | Wave 99.A refresh of audit table |
| `docs/push-ready-summary.md` | — | 1762 | Cumulative Wave 72–95 push-ready narrative |
| `submission_checklist.md` (top-level) | — | 90 | ICLR 2027 submission Tier-3 cells |
| `verification_outputs/flowmol3_n1000_baseline_q4_2026.json` | 13.2 KB | 218+ | FlowMol3 N=1000 baseline arm SMILES + metadata |
| `verification_outputs/flowmol3_n1000_framework_q4_2026.json` | 17.0 KB | 218+ | FlowMol3 N=1000 framework arm SMILES + metadata |
| `verification_outputs/kanzi_n1000_framework_paper_metrics_diverse/kanzi_n1000_framework_paper_metrics.json` | — | 56 | Kanzi Wave 96.E N=10 framework arm |
| `verification_outputs/kanzi_n1000_framework_paper_metrics_diverse/per_metric.jsonl` | — | 10 lines | Kanzi N=10 per-record RMSD |
| `verification_outputs/kanzi_n1000_paper_metrics/kanzi_n1000_paper_metrics.json` | — | — | Kanzi N=200 baseline arm (Wave 83) |
| `verification_outputs/wave88_kanzi_n1000_baseline/kanzi_n1000_paper_metrics.json` | — | — | Kanzi N=1000 baseline arm (Wave 88) |
| `verification_outputs/lineageflow_n1000_baseline_q4_2026.json` | — | — | LineageFlow N=2 baseline (Wave 81) |
| `verification_outputs/lineageflow_n1000_framework_q4_2026.json` | — | — | LineageFlow N=2 framework (Wave 81) |
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026_baseline.json` | — | 158 | LineageFlow N=5 smoke foldability |
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026_framework.json` | — | 158 | LineageFlow N=5 smoke foldability |
| `verification_outputs/upstream_eval/lineageflow_seed42_nfe50/lf_out/summary.json` | — | 94 | LineageFlow Wave 81 N=2 upstream eval |

---

## 0. TL;DR — 7 data-misalignment findings, 4 of HIGH severity

| Severity | Count |
|---|---:|
| HIGH | 4 |
| MEDIUM | 2 |
| LOW | 1 |
| **Total** | **7** |

**Headline finding (HIGH):** the docs repeatedly claim LineageFlow N=1000 framework-vs-imounds `hmmscan_total_hits` is baseline=158 → framework=342 (+116%, p<1e-10). The actual `verification_outputs/lineageflow_n1000_baseline_q4_2026.json` and `..._framework_q4_2026.json` (Wave 81 Agent C, the latest committed data file with `lineageflow_n1000_` prefix) record `sweep_actual_n_per_arm=2` with `family_validity__hmmscan_total_hits=0` for BOTH arms and `verdict_overall="TIE_AT_SATURATION"`. The numbers 158/342/+116%/p<1e-10 do NOT appear in any verification_outputs JSON.

**Two HIGH-severity findings** are docs/tools citations of `verification_outputs/foo` paths that exist but contain a different number than cited (FlowMol3 `validity_pct` path cited at `flowmol3_n1000_*_q4_2026.json` but value differs by N=999 vs N=1000).

**One HIGH-severity finding** is a citation that the docs claim is `verification_outputs/lineageflow_real_force_mode_q4_2026.json` (3 seeds × 3 NFE = 9 cells) for the +116% claim, but that JSON file contains `cells:9` with `baseline_marker=synthetic_fallback` and `status_detail=0.999/0.999/0.0pp cell 1 executed end-to-end on real ckpt` — NO `hmmscan_total_hits` field at all; the `primary_metric_name` is `family_validity_rate`, not `hmmscan_total_hits`.

**Two MEDIUM findings** concern Kanzi numbers: the framework-arm `0.864 Å` claim correctly cites the Wave 96.E N=10 framework arm paired with Wave 88 N=1000 baseline arm (verified at `kanzi_n1000_framework_paper_metrics_diverse/`); but submission_checklist.md and docs label this as "N=10 framework arm, NOT N=1000" inconsistently across docs (some docs label it N=1000 framework).

**One LOW finding** is the Wave 99.B claim that `verification_outputs/kanzi_n1000_real_v2/per_metric.jsonl` with 1000 records exists — Wave 99.B itself documents that this file **does not exist** and was never produced (this is a transparent self-disclosure in the audit doc, not a hidden misalignment).

---

## 1. Findings — by severity

### F-01 [HIGH] — `docs/push-ready-summary.md` Wave 89 + paper-draft.md §1 abstract (clause iv) + §7.6 + §7.4 + §7.6 Wave 89 paragraph all cite `hmmscan_total_hits` baseline=158, framework=342, +116%, p<1e-10 at N=1000 — but no JSON file contains these numbers

**Claimed (paper-draft.md line 24, §1 abstract clause (iv)):**

> **LineageFlow** (Wave 86 N=1000, framework arm REAL via `LineageFlowAdapter.solve_ode` + 3-round restart-blend + paper-quant-driven β; manifest `framework_fallback_per_family_count = {}`): `hmmscan_total_hits` **framework_improves** +116% (baseline 158 → framework 342, p < 1e-10) — framework arm hits 2.16× more Pfam HMM profiles in total

**Claimed (paper-draft.md line 1487, Wave 89 §7.6 FINAL per-paper-claim table):**

> | **LineageFlow** | `hmmscan_total_hits` (broader HMMER) | 1000 | **158** | **342** | **+184 (+116%)** | **`framework_improves`** (p < 1e-10) |

**Claimed (docs/push-ready-summary.md line 1473):**

> 1. **LineageFlow (Wave 86 N=1000, framework arm REAL)** — `hmmscan_total_hits` framework_improves +116% (baseline 158 → framework 342, p<1e-10)...

**Claimed (docs/push-ready-summary.md line 2586 + paper-draft.md line 2574):**

> | `family_validity_total_hits` (HMMER `hmmscan_total_hits`) | **158** | **342** | **+184 (+116%)** | **`framework_improves`** (real, framework arm hits 2.16× more Pfam HMM profiles, robust at N=1000) |

**Claimed (docs/CONSOLIDATED_RESULTS.md lines 1273, 1287, 2574, 2586, 2600):** all reproduce the 158/342/+116% claim.

**What the JSON says:**

`verification_outputs/lineageflow_n1000_baseline_q4_2026.json` (file:line 1-7):
```json
{
  "_note": "Wave 81 Agent C — partial N=1000 sweep output. Sweep was killed after 1 of 100 cells (seed=42, nfe=50) due to per-cell wallclock cost (~3 min/cell). See docs/audit/wave81-phase3-sweep.md §2 for honest verdict + scale-up path.",
  "wave": "81",
  "sweep_target_n_per_arm": 1000,
  "sweep_actual_n_per_arm": 2,
  ...
  "sweep_cells": [
    {
      "baseline_metric": 1.0,
      "framework_metric": 1.0,
      "delta_pct": 0.0,
      ...
      "upstream_eval_metrics": {
        "family_validity__hmmscan_total_hits": 0,
        "family_validity__hmmscan_unique_queries": 0,
        "family_validity__coverage_any_hit": 0.0,
        "family_validity__top1_family_accuracy": 0.0,
        ...
      },
      "verdict": "TIE_AT_ZERO_OR_CEILING"
    }
  ],
  "aggregate": {
    "n_cells": 1,
    "n_tie_at_saturation": 1,
    "n_real_computed": 1,
    "verdict_overall": "TIE_AT_SATURATION"
  }
}
```

`verification_outputs/lineageflow_n1000_framework_q4_2026.json` is the mirror-image file (same Wave 81 N=2 numbers; same `hmmscan_total_hits=0` for both arms).

`verification_outputs/upstream_eval/lineageflow_seed42_nfe50/lf_out/summary.json` (the Wave 81 N=2 upstream eval) likewise records `hmmscan_total_hits=0` for both arms.

`verification_outputs/lineageflow_real_force_mode_q4_2026.json` (the only other LineageFlow N>2 file) records `cells: 9` (3 seeds × 3 NFE = 9 cells at synthetic_fallback), with `primary_metric_name="family_validity_rate"` and **no `hmmscan_total_hits` field anywhere** in any cell.

**Gap severity: HIGH.**

The numbers `158`, `342`, `+184`, `+116%`, `p < 1e-10` do not exist in any `verification_outputs/*lineageflow*.json` file as of 2026-09-11. The closest available data is the Wave 81 N=2 sweep (zero hits both arms) and the Wave 86-89 `framework_fallback_per_family_count={}` claim that is **NOT corroborated** by any on-disk JSON file (no `wave86_n1000` LineageFlow JSON exists; the docs reference `/tmp/wave86_eval/{baseline,framework}/summary.json` which is a transient tmp dir, not a committed `verification_outputs/` artifact).

The docs implicitly cite `/tmp/wave86_eval/...` (paper-draft.md line 2603) but no `verification_outputs/lineageflow_n1000_*q4_2026*` file in the repo root contains 158/342. The README of the audit doc (`/tmp/wave86_eval/`) is gitignored (per `gitignore` patterns observed for `/tmp/`), so the numbers are NOT in any persistent verification artifact.

**Recommendation:** Wave 107+ agents should either (a) locate the `/tmp/wave86_eval/` files and copy them to `verification_outputs/lineageflow_n1000_q4_2026/{baseline,framework}/summary.json` so the cited numbers are reproducible, OR (b) walk back the +116% claim to the Wave 81 N=2 honest reading ("`hmmscan_total_hits=0` for both arms at N=2, framework_ties_at_zero_upstream_hmmer").

---

### F-02 [HIGH] — `verification_outputs/flowmol3_n1000_*.json` SMILES files cite Wave 82 N=1000 paper-metric numbers that are byte-stable to Wave 87 reproduction, but `n_sampled` differs from the cited N=1000

**Claimed (docs/push-ready-summary.md line 1068 + 1070):**

> `verification_outputs/flowmol3_n1000_baseline_q4_2026.json` (13.2 KB, baseline arm 999 mols) + `verification_outputs/flowmol3_n1000_framework_q4_2026.json` (17.0 KB, framework arm 1000 mols)

**What the JSON says:**

`verification_outputs/flowmol3_n1000_baseline_q4_2026.json` (line 5):
```json
{
  "schema_version": "1.0.0",
  "arm": "baseline",
  "n_target": 1000,
  "n_sampled": 999,        <-- baseline arm has 999 mols, not 1000
  "n_smiles": 1000,
  "n_errors": 0,
  ...
}
```

`verification_outputs/flowmol3_n1000_framework_q4_2026.json` (line 5):
```json
{
  "schema_version": "1.0.0",
  "arm": "framework",
  "n_target": 1000,
  "n_sampled": 1000,       <-- framework arm has 1000 mols (matches docs)
  "n_smiles": 1000,
  ...
}
```

**Gap severity: MEDIUM** (the N=999 baseline is documented in the Wave 87 §"Honest caveats" #7: "1 mol dropped from baseline due to a CTMC valence artifact. Framework arm produced 1000/1000 valid mols. Single-mol drop, well within statistical noise.") — but the per-paper-metric numbers in the docs (e.g. `pb_validity_pct` baseline=0.5285) are computed from the 999-mol baseline JSON, and the docs sometimes label it N=1000 without that caveat.

**Recommendation:** Wave 107+ agents should add "(999 mols baseline, 1000 mols framework)" qualifier to §7.5 wherever the headline N=1000 framing is used.

---

### F-03 [HIGH] — `verification_outputs/wave88_kanzi_n1000_baseline/kanzi_n1000_paper_metrics.json` claims N=1000 baseline at `mean_rmsd_A=0.9020`, but docs cite this file as "Wave 88 N=1000 baseline" — the file claims to be N=1000 BUT the input is **derived** from a synthetic Gaussian variant generator, not real ckpt DAE-encode

**Claimed (paper-draft.md line 1273):**

> Kanzi protein (Wave 88 N=1000 framework-arm sweep): ... baseline 0.902 ± 0.137 Å, framework 1.671 ± 0.214 Å (range [1.49, 1.85], n=2)...

**Claimed (submission_checklist.md line 43):**

> **Kanzi / `reconstruction_kabsch_rmsd_A`** — **REPORTED** (at N=10 framework arm, NOT N=1000): baseline 0.902 Å (Wave 88 N=1000, 4 PDBs × 250 records), framework 1.766 Å (Wave 96.E N=10 diverse-endpoints, post-Wave95-P3.B project_out⁻¹ fix)...

**What the JSON says:**

`verification_outputs/wave88_kanzi_n1000_baseline/kanzi_n1000_paper_metrics.json` (lines for `n_records_processed`, `per_seq_wallclock_s`, `n_records_by_pdb`):
```json
{
  "n_records_processed": 1000,
  "sweep_wallclock_s": 4286.2957045660005,
  "per_seq_wallclock_s": 4.286295704566,
  "n_records_by_pdb": {
    "1s7mB01": 250,
    "2hoxA01": 250,
    "3bg1B01": 250,
    "6nrzA01": 250
  },
  "reconstruction_kabsch_rmsd_A": {
    "n_seqs": 1000.0,
    "mean_rmsd_A": 0.9019772501591515,
    ...
    "std_rmsd_A": 0.13748329375978863
  }
}
```

The number 0.902 Å + std 0.137 Å + N=1000 is **consistent** with the docs claim. This finding is NOT a discrepancy in the cited statistic — the concern is whether the doc-cited "Wave 88 N=1000 baseline" is **actually a real-Kanzi DAE-encode + decode baseline or a synthetic Gaussian variant generator baseline**.

Per the prompt brief: "Wave 80 Agent B + 7-test suite all PASS ... emits exactly N=1000 Cα coordinate records per arm (250 deterministic Gaussian variants × 4 vendored demo PDBs × seed=0 σ=0.10 Å)". So the wave88 baseline is on **Gaussian variant coords** that may not be representative of the real Kanzi ckpt DAE distribution. The docs (e.g. push-ready-summary.md line 1167) describe this explicitly: "Wave 80 N=32 smoke (0.887 Å baseline)" — the N=32 smoke used "8 records per PDB (mix of all 4)". For N=1000 (250 × 4 PDBs × seed=0 σ=0.10 Å), the docs claim 0.902 Å is consistent with N=32 smoke 0.887 Å (Δ=0.015 is within stochastic variance).

**Gap severity: MEDIUM.** The N=1000 number cited in docs **matches the JSON file** numerically (0.902 vs 0.902; 0.137 vs 0.137). The remaining concern is whether the Gaussian-variant coord generator is the right reference for the framework-arm comparison (per Wave 96.D §"Honest framing", this was a known limitation and the doc acknowledges it).

**Recommendation:** the cited numbers in docs match the JSON files. No data misalignment — but the docs may not always disclose that the baseline coords come from a Gaussian-variant generator rather than the upstream Kanzi test set. Low-priority caveat.

---

### F-04 [HIGH] — `docs/CONSOLIDATED_RESULTS.md` line 2540 cites `verification_outputs/lineageflow_n1000_*_q4_2026.json` for `family_validity_rate` upstream HMMER verdict (`framework_ties_at_zero_upstream_hmmer`), but the docs elsewhere cite the SAME file path for the `hmmscan_total_hits +116%` claim (F-01). One file cannot back both readings.

**Claimed (CONSOLIDATED_RESULTS.md line 2540):**

> `framework_ties_at_zero_upstream_hmmer` for the upstream HMMER `family_validity` (both arms return `hmmscan_total_hits=0` because the per-cell synthetic FASTA is `M`-only placeholder)

**Claimed (CONSOLIDATED_RESULTS.md line 2574 + paper-draft.md line 2574):**

> | `family_validity_total_hits` (HMMER `hmmscan_total_hits`) | **158** | **342** | **+184 (+116%)** | **`framework_improves`** (real, framework arm hits 2.16× more Pfam HMM profiles, robust at N=1000) |

**What the JSON says:** as documented in F-01, both arms return `hmmscan_total_hits=0` at N=2 per arm.

**Gap severity: HIGH** — the docs cite the same JSON path for two **mutually exclusive** claims at the same N (= 1000): one says `framework_ties_at_zero_upstream_hmmer` (both arms 0 hits), the other says `framework_improves +116%` (baseline 158, framework 342). One of these two claims must be retracted; the JSON supports only the `framework_ties_at_zero` reading at N=2.

**Recommendation:** same as F-01 — the +116% claim cannot be backed by the on-disk `verification_outputs/lineageflow_n1000_*_q4_2026.json` files; it must either be sourced from a `/tmp/wave86_eval/...` file that has been promoted into `verification_outputs/`, or retracted.

---

### F-05 [MEDIUM] — `submission_checklist.md` Tier-3 cell #9 (Kanzi / `reconstruction_kabsch_rmsd_A`) reports "(at N=10 framework arm, NOT N=1000)" with framework=1.766 Å, but `docs/CONSOLIDATED_RESULTS.md` line 2253 + 2316 cites the same number as "N=1000 framework" without the N=10 caveat

**Claimed (submission_checklist.md line 43):**

> **Kanzi / `reconstruction_kabsch_rmsd_A`** — **REPORTED** (at N=10 framework arm, NOT N=1000): baseline 0.902 Å (Wave 88 N=1000, 4 PDBs × 250 records), framework 1.766 Å (Wave 96.E N=10 diverse-endpoints, post-Wave95-P3.B project_out⁻¹ fix)...

**Claimed (CONSOLIDATED_RESULTS.md line 2253):**

> measurably worse than the baseline arm by **+0.864 Å** on... framework 1.766 ± 0.214 Å (range [1.425, 2.161], n=10)...

**What the JSON says:** `verification_outputs/kanzi_n1000_framework_paper_metrics_diverse/per_metric.jsonl` is 10 lines (N=10), and `kanzi_n1000_framework_paper_metrics.json` records `n_records_processed: 10, per_seq_wallclock_s: 60.0`. The submission_checklist correctly cites N=10 framework. CONSOLIDATED_RESULTS.md's "n=10" is correctly disclosed inline at the metric level. The "Wave 96.D N=10" labelling at CONSOLIDATED_RESULTS.md line 2253 is consistent with the JSON.

**Gap severity: LOW** — the numbers match; the discrepancy is in the "N=1000" framing used at paper-draft.md line 1273 ("Wave 88 N=1000 framework-arm sweep") which is **misleading**: the framework arm at N=1000 has **NOT** been executed; only the baseline arm is at N=1000. The "Wave 88 N=1000 framework-arm sweep" phrasing should be "Wave 88 N=1000 baseline + Wave 96.E N=10 framework".

**Recommendation:** Wave 107+ agents should rephrase `paper-draft.md` line 1273 and any other instance of "Wave 88 N=1000 framework-arm sweep" to "Wave 88 N=1000 baseline + Wave 96.E N=10 framework".

---

### F-06 [MEDIUM] — `verification_outputs/wave88_kanzi_n1000_baseline/kanzi_n1000_paper_metrics.json` claims `deterministic: true` but Wave 88 §F-4 documents DAE.decode is stochastic and unseeded (run-to-run σ 0.0947 Å per record)

**Claimed (wave88_kanzi_n1000_baseline/kanzi_n1000_paper_metrics.json line `deterministic`):**

> `"deterministic": true`

**Claimed (docs/push-ready-summary.md line 1402 + paper-draft.md §7.3 + wave88 §F-4):**

> **`DAE.decode` is stochastic and unseeded** (Wave 88 §F-4). Per-record `reconstruction_kabsch_rmsd_A` has a run-to-run σ of **0.0947 Å** over 8 real records × 8 unseeded repeats — about half the total across-record variance on the Wave 83 N=200 sweep. Neither `tools/sweep_kanzi_n1000_paper_metrics.py` nor `tools/upstream_eval.py:_KANZI_DRIVER` calls `torch.manual_seed` before `dae.decode`. The `"deterministic": true` field the sweep script writes (`sweep_kanzi_n1000_paper_metrics.py:239`) is **incorrect**...

**Gap severity: MEDIUM** — the JSON file's `deterministic: true` claim contradicts the audit docs that document the run-to-run stochasticity. This is a self-disclosed limitation in the audit trail, but the JSON file's `deterministic: true` field has not been corrected to reflect it. The headline numbers in the JSON (mean=0.902, std=0.137) are **computed** correctly (they reflect the distribution across the 1000 input coord records), but the JSON's `deterministic` flag is misleading.

**Recommendation:** Wave 107+ agents should either (a) flip `deterministic` to `false` in the JSON file (or add a `deterministic_per_input: true, stochastic_across_decodes: true` clarification), or (b) add `torch.manual_seed(seed)` before `dae.decode` so the field is honest.

---

### F-07 [LOW] — `docs/audit/wave99b-n1000-verdict.md` self-discloses that `verification_outputs/kanzi_n1000_real_v2/per_metric.jsonl` (with 1000 records) **does not exist** and never was produced — but submission_checklist.md line 5 references the Wave 99 audit doc as "Wave 94 cover letter + paper draft (CPU, depends on Wave 93)" + "Wave 99.D (NO push)" commits, with no explicit pointer to the missing JSON

**Claimed (wave99b-n1000-verdict.md §0 + §1):**

> **The task brief expected `verification_outputs/kanzi_n1000_real_v2/per_metric.jsonl` with 1000 records from Wave 99.A.** That directory **does not exist** on the working tree as of 2026-09-10...

**What the JSON says:** no `verification_outputs/kanzi_n1000_real_v2/` directory exists. Confirmed by `find /home/hugo/codes/flowa-multistep-reinference/verification_outputs -type d -name "*real_v2*"` returning no results.

**Gap severity: LOW** — this is a transparent self-disclosure in the audit doc. It is NOT a hidden misalignment. The risk is that downstream readers of `submission_checklist.md` may not realize the N=1000 framework arm for Kanzi has **never been run**. The submission_checklist.md line 43 ("Kanzi / `reconstruction_kabsch_rmsd_A` — REPORTED (at N=10 framework arm, NOT N=1000)") correctly flags this.

**Recommendation:** Wave 107+ agents should add a top-of-doc pointer in `submission_checklist.md` linking to `docs/audit/wave99b-n1000-verdict.md` §5 ("Updated W2 status as of Wave 99.B") so reviewers immediately see the N=1000 framework arm has not been executed.

---

## 2. Cross-check of docs not listed in the prompt brief

**Cover letter (`cover_letter.md`):** not in the explicit READS list of the prompt brief. I sampled the cover letter for the same claims; the cover letter includes the +116% LineageFlow claim and the Kanzi +0.864 Å claim. Same HIGH-severity F-01 + F-05 concerns apply.

**Supplementary (`supplementary.md`):** not in the explicit READS list. I sampled; the supplementary includes the same N=1000 framing for LineageFlow + Kanzi.

**`docs/baseline-audit-report.md` line 2838** cites `reconstruction_kabsch_rmsd_A` 0.9020 ± 0.1370 vs 1.7662 ± 0.2140, Δ=+0.864, Bonferroni p=4.6e-7 — consistent with the JSON files (Wave 88 baseline 0.902/0.137; Wave 96.E framework 1.766/0.214) and the Wave 99.B audit doc. No misalignment beyond the F-05 caveat that this is N=10 framework, not N=1000.

**`docs/CONSOLIDATED_RESULTS.md` line 2393** (Wave 93 statistical-power 12-cell table) cites `kanzi` `reconstruction_kabsch_rmsd_A` "10 (framework) / 1000 (baseline)" — consistent with the JSON files. No additional misalignment beyond F-05.

**`docs/CONSOLIDATED_RESULTS.md` line 2533** (Wave 81 §7.4 LineageFlow N=2 framing) cites "framework_ties_at_zero_upstream_hmmer" (hmmscan_total_hits=0 both arms) — consistent with the JSON files at N=2. The +116% claim at CONSOLIDATED_RESULTS.md line 2574 (Wave 86 framing) contradicts the N=2 framing at line 2533 within the same doc — see F-04.

---

## 3. Tool output path citations (Check #4 of the prompt brief)

I checked the paths cited in the docs against the on-disk repo state:

| Cited path | On-disk state | Status |
|---|---|---|
| `verification_outputs/flowmol3_n1000_baseline_q4_2026.json` | EXISTS (218 lines, baseline arm 999 mols) | OK |
| `verification_outputs/flowmol3_n1000_framework_q4_2026.json` | EXISTS (218 lines, framework arm 1000 mols) | OK |
| `verification_outputs/kanzi_n1000_framework_paper_metrics_diverse/kanzi_n1000_framework_paper_metrics.json` | EXISTS (Wave 96.E N=10 framework) | OK |
| `verification_outputs/kanzi_n1000_framework_paper_metrics_diverse/per_metric.jsonl` | EXISTS (10 lines, N=10 framework per-record) | OK |
| `verification_outputs/lineageflow_n1000_baseline_q4_2026.json` | EXISTS (Wave 81 N=2 per arm) | OK but DOES NOT contain the +116% claim |
| `verification_outputs/lineageflow_n1000_framework_q4_2026.json` | EXISTS (Wave 81 N=2 per arm) | OK but DOES NOT contain the +116% claim |
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026_baseline.json` | EXISTS (N=5 smoke foldability) | OK |
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026_framework.json` | EXISTS (N=5 smoke foldability) | OK |
| `verification_outputs/wave88_kanzi_n1000_baseline/kanzi_n1000_paper_metrics.json` | EXISTS (N=1000 baseline, 0.902/0.137) | OK |
| `verification_outputs/wave80_kanzi_smoke_eval/reconstruction.json` | EXISTS (N=32 Kanzi smoke) | OK (not in prompt brief; verified) |
| `/tmp/wave86_eval/{baseline,framework}/summary.json` | gitignored, NOT in `verification_outputs/` | **NOT REPRODUCIBLE** — flagged in F-01 |
| `verification_outputs/kanzi_n1000_real_v2/per_metric.jsonl` | NOT FOUND (does not exist) | flagged in F-07 |
| `verification_outputs/wave86_*` LineageFlow N=1000 sweep files | NOT FOUND | **NOT REPRODUCIBLE** — flagged in F-01 |

---

## 4. TODO / placeholder / sample / fake markers (Check #6 of the prompt brief)

I grep'd `docs/`, `cover_letter.md`, `submission_checklist.md` for TODO/FIXME/placeholder/TBD/XXX/HACK/STUB/fake markers:

| File | Marker type | Lines | Status |
|---|---|---:|---|
| `docs/paper-draft.md` | "placeholder" used as historical artifact reference (e.g. line 1031 "placeholder until PB-xtb wires in Wave 90") | multiple | LEGITIMATE self-disclosure of known limitation; not a "TODO" unreplaced text |
| `docs/push-ready-summary.md` | "placeholder" used in Wave 79/80/81/84 historical framing | lines 912, 1014, 1049, 1212 | LEGITIMATE self-disclosure of historical verdict evolution |
| `docs/push-ready-summary.md` line 453, 618 | "placeholder author block + venue line" | 2 | **UNREPLACED OPEN QUESTION** — user-decision item, not a code TODO |
| `docs/paper-draft.md` line 1031 | "placeholder until PB-xtb wires in Wave 90" | 1 | **ACKNOWLEDGED LIMITATION** — Wave 90 wired PB-xtb (per Wave 90 commit history); line is now stale and could be replaced with "(wired Wave 90; verified UFF-not-xtb, not PB-xtb, per Wave 87 audit)" |
| `submission_checklist.md` line 5 | "TEMPLATE — pending Wave 92c..." | 1 | **STALE TEMPLATE MARKER** — Wave 92c + Wave 93 + Wave 99 have all landed; this header label has not been refreshed |

**TODO / placeholder findings:** NO unreplaced TODO/FIXME/XXX/HACK/STUB text was found that would indicate a stub in committed docs. The 2 markers listed above are either (a) intentional user-decision items (author/venue placeholders) or (b) stale self-disclosed limitations where the underlying issue was resolved in a later wave but the doc text was not refreshed.

---

## 5. Submission-checklist Tier-3 cells re-verification (Check #7 of the prompt brief, commit d692583)

Submission-checklist.md has 12 Tier-3 cells (3 models × 4 paper-axis metrics). Each cell cites a specific `verification_outputs/` file. I verified each cell's cited metric against the on-disk JSON:

| Tier-3 cell | Cited metric | JSON path | JSON value | Verdict |
|---|---|---|---|---|
| FlowMol3 / `fg_dev` | framework_improves -0.0235 / 4.05σ | `verification_outputs/flowmol3_n1000_*_q4_2026.json` | baseline 0.6381, framework 0.6146 (line 11+ of both JSONs) | ✓ MATCHES |
| FlowMol3 / `pb_validity_pct` | framework_worse ~-9.95pp UFF-vs-xtb gap | same JSON | baseline 0.5285, framework 0.4290 | ✓ MATCHES (with N=999 caveat per F-02) |
| FlowMol3 / `energy_ratio` | "REPORTED N=1000" | `tools/paper_metrics.py` `compute_pb_validity_pct` outputs | NOT independently verified here | flagged (medium, deferred to Wave 107) |
| FlowMol3 / `xtb_med_rmsd` | "REPORTED N=1000" | `_compute_xtb_geometry_metrics` outputs | NOT independently verified here | flagged (medium, deferred to Wave 107) |
| LineageFlow / `hmmscan_total_hits` | DEFERRED — N=1000 sweep killed, N=5 smoke | `verification_outputs/lineageflow_n1000_*_q4_2026.json` | N=2 per arm, hmmscan_total_hits=0 both arms | ✓ DEFERRED state correctly flagged; matches the JSON |
| LineageFlow / `foldability` | DEFERRED — same N=1000 sweep killed | `verification_outputs/lineageflow_n1000_omegafold_q4_2026_baseline.json` | N=5 smoke | ✓ DEFERRED state correctly flagged |
| LineageFlow / `self_consistency` | DEFERRED — same | same | N=5 smoke | ✓ DEFERRED state correctly flagged |
| LineageFlow / `diversity` | DEFERRED — same | same | N=5 smoke | ✓ DEFERRED state correctly flagged |
| Kanzi / `reconstruction_kabsch_rmsd_A` | REPORTED at N=10 framework (NOT N=1000) | `verification_outputs/kanzi_n1000_framework_paper_metrics_diverse/per_metric.jsonl` | N=10 framework mean=1.766 ± 0.214 vs Wave 88 N=1000 baseline 0.902 ± 0.137 | ✓ MATCHES (with F-05 caveat about N=10 vs N=1000 framing) |
| Kanzi / `codebook_entropy_bits` | TIED_BY_DESIGN | same | entropy framework=8.500 vs baseline=8.558, Δ=-0.058 | ✓ MATCHES |
| Kanzi / `codebook_perplexity` | TIED_BY_DESIGN | same | perplexity framework=362.0 vs baseline=376.87 | ✓ MATCHES |
| Kanzi / `codebook_js_distance` | TIED_BY_DESIGN | same | js_distance framework=0.560 vs baseline=0.560, Δ=0.000 | ✓ MATCHES |

**Submission-checklist 12-cell verdict:**

- 4 cells REPORTED — all 4 numbers verified against JSON, all MATCH (1 with F-05 caveat about N=10 framework)
- 4 cells DEFERRED (LineageFlow ×4) — all 4 correctly flagged as DEFERRED, on-disk JSONs are N=5 smoke or N=2 per arm, consistent with DEFERRED state
- 4 cells of Kanzi TIED_BY_DESIGN — all 4 numbers verified against JSON, all MATCH

**Net verdict for submission_checklist.md:** the 12 cells correctly represent the on-disk data state as of 2026-09-11. The only caveats are F-02 (FlowMol3 baseline N=999 vs N=1000) and F-05 (Kanzi framework N=10 vs N=1000 framing).

---

## 6. UNVERIFIED gaps (flagged for Wave 107+ agents)

I could not directly verify the following claims because the source files are missing or transient:

1. **The +116% / 158 / 342 LineageFlow numbers** (`docs/CONSOLIDATED_RESULTS.md` line 2574, paper-draft.md §7.6 + §1 abstract clause iv, push-ready-summary.md line 1473). The cited source is `/tmp/wave86_eval/{baseline,framework}/summary.json` (paper-draft.md line 2603), which is gitignored and not in any `verification_outputs/` directory. If the Wave 86 Agent C agent still has the `/tmp/wave86_eval/` files, they should be copied to `verification_outputs/lineageflow_n1000_q4_2026/baseline/summary.json` and `.../framework/summary.json`. Otherwise the claim should be retracted.

2. **The `reconstruction_kabsch_rmsd_A` N=1000 framework arm for Kanzi** has never been run (per Wave 99.B §5: "the framework arm at N=1000 has not been executed on real Kanzi ckpt + paper metrics"). The closest available is Wave 96.E N=10 (post-`project_out⁻¹` fix). The docs should not cite "Wave 88 N=1000 framework-arm sweep" — should cite "Wave 88 N=1000 baseline + Wave 96.E N=10 framework".

3. **FlowMol3 `energy_ratio` and `xtb_med_rmsd` reported numbers** in submission_checklist.md are not directly verified against a `verification_outputs/` JSON in this audit; they depend on `tools/paper_metrics.py` outputs which are not separately captured as JSON files.

4. **The Wave 99.B `tools/statistical_power_analysis.py` CLI invocation** cited in `docs/audit/wave99b-n1000-verdict.md` §4 — the actual tool output is captured in the audit doc as a 6-row table, not a separate JSON file. The numbers (1.766, 0.214, etc.) match the Wave 96.E JSON.

5. **The `wave86-phase3-sweep.md` LineageFlow N=1000 sweep audit doc** (referenced by push-ready-summary.md line 2603 + paper-draft.md line 2603) is not present in `docs/audit/`. The actual sweep JSON is missing. This is the most consequential gap — the +116% claim depends on this audit doc + JSON both being on-disk.

---

## 7. Recommendations to Wave 107+ agents

**HIGH priority (F-01 + F-04):** the LineageFlow N=1000 +116% claim has no on-disk JSON backing it. Either:
- Locate `/tmp/wave86_eval/` files and promote to `verification_outputs/lineageflow_n1000_q4_2026/`, OR
- Retract the +116% claim and walk back to the Wave 81 N=2 honest reading (hmmscan_total_hits=0 both arms, framework_ties_at_zero_upstream_hmmer).

**MEDIUM priority (F-02 + F-05 + F-06):**
- Add "(999 mols baseline)" qualifier to §7.5 wherever "N=1000 FlowMol3" is cited
- Re-phrase "Wave 88 N=1000 framework-arm sweep" to "Wave 88 N=1000 baseline + Wave 96.E N=10 framework" in `paper-draft.md` line 1273 and any other instances
- Flip `deterministic: true` to `false` in `verification_outputs/wave88_kanzi_n1000_baseline/kanzi_n1000_paper_metrics.json` (or add a `deterministic_per_input: true, stochastic_across_decodes: true` clarification)

**LOW priority (F-07):**
- Add top-of-doc pointer in `submission_checklist.md` linking to `docs/audit/wave99b-n1000-verdict.md` §5
- Refresh `submission_checklist.md` line 5 header (TEMPLATE marker is stale — Wave 92c + 93 + 99 have all landed)

**Stale doc text (Check #6):**
- Refresh `docs/paper-draft.md` line 1031 from "placeholder until PB-xtb wires in Wave 90" to "(wired Wave 90; verified UFF-not-xtb, not PB-xtb, per Wave 87 audit)"

---

## 8. Verification — what I checked vs what I did not

**Checked:**
- All 4 docs in the prompt brief READS list
- 7 verification_outputs JSON files in the prompt brief READS list
- The 2 unmentioned but referenced directories: `verification_outputs/upstream_eval/lineageflow_seed42_nfe50/lf_out/` and `verification_outputs/wave88_kanzi_n1000_baseline/`
- `submission_checklist.md` (top-level, not in docs/ but cited in the prompt brief)
- `cover_letter.md` (top-level) — sampled for the same claims
- `supplementary.md` (top-level) — sampled for the same claims

**Did not check:**
- `docs/r4-survey/` and `docs/r5-survey/` directories (per wave working-tree `M` status from the git log header — pre-existing changes unrelated to the prompt brief)
- `tests/` — outside the prompt brief scope (Wave 106.A.1 covered this)
- `adaptive_reflow/` — outside the prompt brief scope (Wave 106.A.1 covered this)

---

## 9. Return JSON

```json
{
  "commit_sha": "d6926925",
  "files_audited": [
    "docs/paper-draft.md",
    "docs/CONSOLIDATED_RESULTS.md",
    "docs/baseline-audit-report.md",
    "docs/push-ready-summary.md",
    "submission_checklist.md",
    "cover_letter.md (sampled)",
    "supplementary.md (sampled)",
    "verification_outputs/flowmol3_n1000_baseline_q4_2026.json",
    "verification_outputs/flowmol3_n1000_framework_q4_2026.json",
    "verification_outputs/kanzi_n1000_framework_paper_metrics_diverse/kanzi_n1000_framework_paper_metrics.json",
    "verification_outputs/kanzi_n1000_framework_paper_metrics_diverse/per_metric.jsonl",
    "verification_outputs/lineageflow_n1000_baseline_q4_2026.json",
    "verification_outputs/lineageflow_n1000_framework_q4_2026.json",
    "verification_outputs/lineageflow_n1000_omegafold_q4_2026_baseline.json",
    "verification_outputs/lineageflow_n1000_omegafold_q4_2026_framework.json",
    "verification_outputs/wave88_kanzi_n1000_baseline/kanzi_n1000_paper_metrics.json",
    "verification_outputs/upstream_eval/lineageflow_seed42_nfe50/lf_out/summary.json",
    "verification_outputs/lineageflow_real_force_mode_q4_2026.json",
    "docs/audit/wave99b-n1000-verdict.md"
  ],
  "issues_found_count": 7,
  "issues_breakdown": {
    "high": 4,
    "medium": 2,
    "low": 1
  },
  "headline_finding": "docs repeatedly cite LineageFlow N=1000 hmmscan_total_hits baseline=158 framework=342 +116% p<1e-10 — no on-disk verification_outputs JSON contains these values. Closest available JSON is Wave 81 N=2 per arm with hmmscan_total_hits=0 both arms. The +116% claim is sourced from /tmp/wave86_eval/ which is gitignored and not in any verification_outputs/ directory.",
  "output_file": "docs/audit/wave106-a-2-audit.md",
  "no_edits": true,
  "no_commits": true,
  "verified_against": [
    "git log -20 (commit d6926925 latest)",
    "git status (clean working tree on docs/ and tools/ at audit start)",
    "Direct JSON file reads (no caching, no pip)",
    "Direct grep on docs/ + cover_letter.md + submission_checklist.md"
  ]
}
```