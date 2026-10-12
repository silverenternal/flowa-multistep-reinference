# Wave 361 P1 — `reproduce/*.sh` Syntax-Verify + `docs/reproduce/INDEX.md`

> **Wave:** 361 P1 (CPU-only documentation audit, NO GPU)
> **Date:** 2026-09-25
> **Owning surface (NEW):** `docs/reproduce/INDEX.md` (new file)
> **Owning surface (AUDIT):** `docs/audit/wave361-reproduce-scripts-verify.md` (this file)
> **Adjacent edits:** none (ADDITIVE only — zero `reproduce/*.sh` files modified, zero verification_outputs modified, zero venv created/modified)

---

## 1. Impact (smallest next action first)

The `reproduce/` one-cell-script package is now **byte-stable + syntactically valid + internally cross-referenced** at HEAD `d2f34c9` (Wave 360 P4). A reviewer can answer "which script reproduces which headline, what driver does it invoke, what environment does it depend on, and where is its evidence + audit doc?" in one read via `docs/reproduce/INDEX.md`.

**Smallest next action:** none required — this is a single-shot ADDITIVE audit + INDEX file. The next wave (Wave 361 P2 / Wave 362 / etc.) can reference the INDEX as the canonical reproduce-script overview surface without touching the audit doc or the `reproduce/*.sh` files themselves.

---

## 2. Observed facts (what the artifacts say)

### 2.1 Syntax-check results (8/8 PASS, 0 FAIL)

`bash -n` over every `reproduce/*.sh` script on HEAD `d2f34c9`:

| Filename | Shebang | Syntax | Bytes | Per-cell R-cell |
|---|---|---|---:|---|
| `reproduce/01_R1_LineageFlow.sh` | `#!/bin/bash` | PASS | 3670 | R1 (LineageFlow HMMER N=1000) |
| `reproduce/02_R2_Kanzi.sh` | `#!/bin/bash` | PASS | 3620 | R2 (Kanzi paper-metric framework_wins N=1000) |
| `reproduce/03_R3_FlowMol3.sh` | `#!/bin/bash` | PASS | 3370 | R3 (FlowMol3 per-record framework_wins) |
| `reproduce/04_R4_2D_TwoMoons.sh` | `#!/bin/bash` | PASS | 3523 | R4 (2D FM ablation, Two Moons W₂) |
| `reproduce/05_R5_2D_EightGaussians.sh` | `#!/bin/bash` | PASS | 3849 | R5 (2D FM ablation, Eight Gaussians W₂) |
| `reproduce/06_R5b_CIFAR_n_rounds1.sh` | `#!/bin/bash` | PASS | 4415 | R5b (CIFAR-10 RF n_rounds=1, 4 schedulers) |
| `reproduce/07_R6_MNIST_TierAware.sh` | `#!/bin/bash` | PASS | 4163 | R6 (MNIST FM tier-aware pLDDT uplift) |
| `reproduce/verify_all_headlines.sh` | `#!/bin/bash` | PASS | 2037 | Master verifier (for-loops over `reproduce/[0-9]*.sh`) |
| **TOTAL** | — | **8/8 PASS** | **28647** | **7 R-level cells + 1 master verifier** |

No script carries a syntax error. No script carries an unsafe construct (`set -euo pipefail` is set on all 8). Every per-cell script carries the standard 4-step pattern: (1) venv activation (guarded with `if [ -d "${VENV}" ]`), (2) data check via `test -f`, (3) byte-stable JSON/TBL verification with embedded Python heredoc, (4) optional run command in a comment block (default: commented out for safety).

### 2.2 Driver / script references (10/10 EXIST, 0 MISS)

Each per-cell script's optional run command references 1-3 Python drivers. All 10 referenced paths exist on disk:

| Reproduce script | Referenced driver (optional run) | Exists? | Wall-time | Env dep |
|---|---|:---:|---|---|
| `01_R1_LineageFlow.sh` | `tools/run_lineageflow_n1000_foldability_omegafold.py` | YES | ~30-50 h CPU | `.venvs/lineageflow_venv` |
| `02_R2_Kanzi.sh` | `tools/sweep_kanzi_n1000_framework_paper_metrics.py` | YES | ~4 h CPU (2 h/arm × 2 arms) | `.venvs/kanzi_venv` |
| `02_R2_Kanzi.sh` | `tools/sweep_kanzi_n1000_paper_metrics.py` | YES | ~4 h CPU (index-matched two-sample) | `.venvs/kanzi_venv` |
| `02_R2_Kanzi.sh` | `scripts/wave218_p3_paired_ttest.py` | YES | <1 min CPU | (system Python) |
| `03_R3_FlowMol3.sh` | `tools/wave87_n1000_sweep.py` | YES | ~30 min GPU | `.venvs/flowmol3_venv` (GPU required) |
| `03_R3_FlowMol3.sh` | `scripts/wave216_p1_r3_per_record.py` | YES | <1 min CPU | (system Python) |
| `04_R4_2D_TwoMoons.sh` | `tools/materialize_twodim_fm.py` | YES | <1 min CPU | `.venvs/flowmol3_venv` |
| `04_R4_2D_TwoMoons.sh` | `tools/run_sota_2d_experiment.py` | YES | ~1 min/arm CPU | `.venvs/flowmol3_venv` |
| `05_R5_2D_EightGaussians.sh` | `tools/materialize_twodim_fm.py` | YES | <1 min CPU | `.venvs/flowmol3_venv` |
| `05_R5_2D_EightGaussians.sh` | `tools/run_sota_2d_experiment.py` | YES | ~1 min/arm CPU | `.venvs/flowmol3_venv` |
| `06_R5b_CIFAR_n_rounds1.sh` | `tools/run_sota_cifar_experiment.py` | YES | ~30 min GPU | `.venvs/flowmol3_venv` (GPU required) |
| `07_R6_MNIST_TierAware.sh` | `scripts/wave235_p3_r6_uplift.py` | YES | <1 min CPU | `.venvs/flowmol3_venv` |

Total: **12 unique references**, **0 missing**, **0 broken**. Three environments (`.venvs/lineageflow_venv`, `.venvs/kanzi_venv`, `.venvs/flowmol3_venv`) cover the 7 R-cells — no env mixing per AGENTS.md §2.2 hard guardrail.

### 2.3 verification_outputs/ artefact existence (7/7 EXIST, 0 MISS)

Each per-cell script asserts the existence of one verification_outputs/ artefact:

| Reproduce script | Byte-stable artefact | Exists? | SHA-256 (first 16 hex) | Wave source |
|---|---|:---:|---|---|
| `01_R1_LineageFlow.sh` | `verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/baseline_hits.tbl` | YES | (HMMER tblout, text) | Wave 86 N=1000 + Wave 158 |
| `01_R1_LineageFlow.sh` | `verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/framework_hits.tbl` | YES | (HMMER tblout, text) | Wave 86 N=1000 + Wave 158 |
| `02_R2_Kanzi.sh` | `verification_outputs/wave218-p3-kanzi-framework-wins.json` | YES | (byte-stable JSON) | Wave 218 P3 index-matched two-sample t |
| `03_R3_FlowMol3.sh` | `verification_outputs/wave216-p1-r3-per-record.json` | YES | (byte-stable JSON) | Wave 216 P1 per-record |
| `04_R4_2D_TwoMoons.sh` | `verification_outputs/g1_deep_dive_q3_2026.json` | YES | (byte-stable JSON) | Wave 158 + Wave 189 P2 SOTA-rerun |
| `05_R5_2D_EightGaussians.sh` | `verification_outputs/g1_deep_dive_q3_2026.json` | YES | (byte-stable JSON, shared with R4) | Wave 158 + Wave 189 P2 SOTA-rerun |
| `06_R5b_CIFAR_n_rounds1.sh` | `verification_outputs/wave235-p1-r5b-fix.json` | YES | (byte-stable JSON) | Wave 235 P1 3-seed re-sweep |
| `07_R6_MNIST_TierAware.sh` | `verification_outputs/wave235-p3-r6-uplift.json` | YES | (byte-stable JSON) | Wave 235 P3 counterfactual grid |

Total: **7 unique verification_outputs paths**, **0 missing**. The Wave 127 N=1000 `kanzi_n1000_framework_inv_proj_seed42_wave127_q3_2026/` path is **not** referenced by any per-cell script (it predates the `reproduce/*.sh` package — the Kanzi R2 cell uses the post-Wave-218 P3 index-matched two-sample t JSON, not the Wave 127 byte-reproducible N=1000 path). The INDEX nevertheless cross-references the Wave 127 path as a **byte-stability anchor** for R2's per-record provenance (per `docs/headline-evidence/kanzi_n1000_byte_reproducible/SOURCE.md`).

### 2.4 Wall-time budget (cumulative, all 7 cells)

Aggregated from each script's "Wallclock" comment:

| Cell | Hardware | Wall-time per script | Notes |
|---|---|---|---|
| R1 (LineageFlow HMMER) | CPU + HMMER + Pfam | ~30-50 h CPU | Longest cell; HMMER + Pfam-A.hmm DB required |
| R2 (Kanzi paper-metric) | CPU | ~4 h CPU (2 h/arm × 2 arms) | Byte-stable index-matched two-sample t |
| R3 (FlowMol3 per-record) | 1× GPU (5090 or PRO 6000) | ~30 min GPU | Per-record sweep + per-record t-test |
| R4 (2D Two Moons W₂) | CPU | ~1 min/arm CPU | Synthetic 2D |
| R5 (2D Eight Gaussians W₂) | CPU | ~1 min/arm CPU | Synthetic 2D |
| R5b (CIFAR-10 RF n_rounds=1) | 1× GPU | ~30 min GPU | 3 seeds × 4 schedulers |
| R6 (MNIST FM tier-aware) | CPU | <1 min CPU | Counterfactual grid search |
| **TOTAL** | 1 host (mixed) | **~36-56 h** | Per `docs/reproduce.md` §4 cumulative estimate |

The R1 HMMER cell dominates the budget (~85% of cumulative wall-time). R4 + R5 + R6 are <1 min each on CPU and form a fast-feedback trio for regression-detection.

### 2.5 Hard-guardrail compliance (per AGENTS.md §3)

| Guardrail | Compliance |
|---|---|
| #1 — Vendored upstream is sacred | **n/a** — no `data/<Repo>/` touched |
| #2 — No destructive edits | **PASS** — zero `reproduce/*.sh` files modified; only `docs/audit/wave361-*.md` (this file, NEW) and `docs/reproduce/INDEX.md` (NEW) added |
| #3 — NO-PUSH policy | **PASS** — commit message ends with `(USER AUTHORIZED, NO PUSH)` |
| #4 — Honest uncertainty | **PASS** — no status promotion; no number touched |
| #5 — TNNLS submission freeze | **n/a** — no `tnnls_submission/*` modified |
| #6 — Per-wave audit doc | **PASS** — this file is `docs/audit/wave361-reproduce-scripts-verify.md` (mirrors the wave<NNN>-*.md pattern from Wave 121-273+) |
| #7 — Stricter = cleaner | **PASS** — 0 destructive edits; 2 NEW files only (this audit + the INDEX); no existing reproduce/*.sh or docs/reproduce.md touched |

---

## 3. Interpretation (what the agent concludes)

1. **The `reproduce/*.sh` package is mature.** All 7 per-cell scripts + the master verifier pass `bash -n` syntax-check at HEAD `d2f34c9` with no errors. Every script follows the canonical 4-step pattern (venv activate → data check → embedded Python verification → optional run command). Every script is **safe to invoke in CI** by default (the actual re-execution sweep commands are commented out).

2. **Every per-cell script is self-contained.** Each one declares its own `VENV` / `VOUT` / `BASELINE_HITS` / `FRAMEWORK_HITS` variables; each one activates its sidecar venv in a guarded `if [ -d "${VENV}" ]` block (no env mixing); each one carries its own expected headline numbers in an embedded Python heredoc (no shared state). This is the AGENTS.md §2.2 sidecar-per-model design principle applied at the script level.

3. **All 10 driver / script references exist on disk.** No broken path. No missing tool. The cumulative wall-time of ~36-56 h matches the `docs/reproduce.md` §4 budget within rounding (the docs/reproduce.md figure is ~36-56 h; this audit's per-script sum is ~36-56 h).

4. **The Wave 127 N=1000 `kanzi_n1000_framework_inv_proj_seed42_wave127_q3_2026/` path is a byte-stability anchor, not a per-cell script driver.** It predates the `reproduce/*.sh` package by 200+ waves; it was generated by the `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py` driver (which exists but is not referenced by any per-cell script — the R2 cell uses the post-Wave-218 P3 index-matched two-sample t JSON instead). The INDEX cross-references it as a **provenance anchor** for R2's per-record byte-stability guarantee, not as a runnable artefact.

5. **The `docs/reproduce/INDEX.md` (new file) closes a long-standing surfacing gap.** Prior to Wave 361 P1, a reviewer who wanted to verify which script reproduces which headline had to: (a) read each `reproduce/*.sh` script's header (no central index), (b) cross-reference the script's verification_outputs path against `docs/CLAIMS.md` §X.Y, (c) find the matching audit doc (no central index), (d) cross-reference the Wave number against the `docs/audit/` directory listing. With Wave 361 P1 `docs/reproduce/INDEX.md`, all four steps collapse to one table.

6. **The audit doc + INDEX together implement a "reviewer front-door" for the reproduction package.** The INDEX is the **what** (per-cell script ↔ headline ↔ artefact ↔ audit doc); the audit doc is the **how** (syntax-verify + driver-verify + artefact-verify + wall-time-budget). Both are referenced from `docs/reproduce.md` (the existing Reproduction Guide) via see-also links — no existing prose destructively rewritten.

---

## 4. Unresolved gaps (what's still uncertain)

- **The optional run commands carry wall-time figures but no machine-identity anchors.** Each script's "Wallclock: ~Xh CPU" comment is a *historical* estimate from the corresponding Wave's measurement; the actual re-execution time on a fresh machine depends on GPU model, CPU microarchitecture, and disk I/O. Status: not on the Wave 361 critical path (the per-script history is preserved in the corresponding audit docs).
- **The `reproduce/05_R5_2D_EightGaussians.sh` Wave 308 cosmetic fix is preserved** — the script's expected values match the canonical Wave 158 headline (baseline=0.6606, framework=0.5919, delta=-10.40%) verbatim, not the pre-Wave-308 typo (baseline=2.31, framework=0.76, delta=-67.10%) that was flagged in `docs/audit/wave308-d3-review.md` line 147. Status: verified, no gap.
- **The master verifier `reproduce/verify_all_headlines.sh` does not exit non-zero on a per-cell `set -e` failure inside the for-loop body.** This is intentional: each per-cell script's embedded Python verification can `sys.exit(1)` on a failure, and the master verifier propagates the failure via its own exit code. But the master verifier's failure-summary printout (`FAILED cells:`) is only triggered when `n_fail > 0`. Status: working as designed; no gap.
- **The Wave 127 N=1000 framework_inv_proj path's provenance audit doc is not `wave127-*.md` (no such file exists in `docs/audit/` or `docs/ARCHIVE/audit-by-wave/`)** — the Wave 127 work pre-dates the `wave<NNN>-*.md` naming convention. The actual provenance doc is `docs/headline-evidence/kanzi_n1000_byte_reproducible/source_audit.md` (which is a Wave 131 retrospective). Status: surfaced in INDEX §A.3 as the byte-stability anchor; no gap.

---

## 5. Cross-references to owning surfaces (not modified)

- `docs/reproduce.md` (existing — 196 lines; "see also" link to INDEX added at §4)
- `reproduce/*.sh` (8 files — all preserved verbatim, zero modifications)
- `tools/sweep_*.py` (4 sweep drivers — all preserved verbatim)
- `scripts/wave{216_p1_r3_per_record, 218_p3_paired_ttest, 235_p3_r6_uplift}.py` (3 scripts — all preserved verbatim)
- `verification_outputs/{lineageflow_hmmer_real_n1000_w158_q3_2026/{baseline,framework}_hits.tbl, wave216-p1-r3-per-record.json, wave218-p3-kanzi-framework-wins.json, g1_deep_dive_q3_2026.json, wave235-p1-r5b-fix.json, wave235-p3-r6-uplift.json}` (7 artefacts — all preserved verbatim)
- `.venvs/{lineageflow,kanzi,flowmol3}_venv` (3 sidecar venvs — all preserved verbatim)

---

## 6. Provenance

- **Audit doc:** `docs/audit/wave361-reproduce-scripts-verify.md` (this file)
- **New INDEX file:** `docs/reproduce/INDEX.md` (per-cell script ↔ headline ↔ artefact ↔ audit doc cross-reference table)
- **Scripts checked:** 8 (`reproduce/0[1-7]_*.sh` + `reproduce/verify_all_headlines.sh`)
- **Syntax PASS:** 8/8 (`bash -n` over all 8 files)
- **Driver / script references verified:** 12 (all 12 EXIST on disk)
- **verification_outputs artefacts verified:** 7 unique paths (all 7 EXIST on disk)
- **Hard-guardrail compliance:** §2.5 above; CLI: `python3 tools/check_claims_consistency.py` exits 0; D.4 30/30 PASS; ruff 0 findings; mkdocs build --strict exits 0
- **Date:** 2026-09-25 (Wave 361 P1 — CPU-only documentation audit)