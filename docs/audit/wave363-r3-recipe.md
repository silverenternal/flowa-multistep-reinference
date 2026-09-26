# Wave 363 P1 — `paper-data/R3_flowmol3_fgdev/REPRODUCIBILITY_RECIPE.md` R3 Recipe Authoring

**Date:** 2026-09-27
**Author:** Wave 363 P1 (R3 recipe-authoring agent — additive recipe + audit pass)
**Scope:** Author `paper-data/R3_flowmol3_fgdev/REPRODUCIBILITY_RECIPE.md` (NEW 343-line doc) so the R3 FlowMol3 fg_dev paper R-level cell has a **single-source-of-truth reproducibility recipe** that mirrors the Wave 362 P1 R6 recipe pattern (`paper-data/R6_lineageflow_k6/R6_REPRODUCIBILITY_RECIPE.md`) and the Wave 363 P1 R2 / R5a / R5b recipe pattern, while honestly documenting the RDKit 2026.03.5 environment blocker (Wave 351 P3 + Wave 357 P3) that prevents the full N=1000 paired 3-seed sweep from re-running on the current environment.
**Owning surface (NEW):** `paper-data/R3_flowmol3_fgdev/REPRODUCIBILITY_RECIPE.md` (343 lines; SHA-256 = `0c91f4d966d4707e10e28c4198ace3b5b077e9646ead1c04408765444a6e8ba5`).
**Owning surface (AUDIT):** `docs/audit/wave363-r3-recipe.md` (this file).
**Adjacent edits:** none (ADDITIVE only — zero edits to `paper-data/R3_flowmol3_fgdev/{R3_SOURCE.md,SOURCE.md,SHA256SUMS,*.csv,*.json,*.smiles.txt,*.jsonl}` symlinks; zero edits to `verification_outputs/`; zero edits to `tnnls_submission/`; zero vendored-repo edits; zero edits to `docs/CLAIMS.md` CLM-068; zero edits to `docs/CONSOLIDATED_RESULTS.md` §15.105; zero edits to `docs/drafts/paper-A-final.md` §7.2 R3 row).

---

## 1. Impact (smallest next action first)

The R3 FlowMol3 fg_dev paper R-level cell now has a **single-source-of-truth reproducibility recipe** (`paper-data/R3_flowmol3_fgdev/REPRODUCIBILITY_RECIPE.md`) that documents:

- The headline metric at three granularities: (1) per-arm aggregate UNPAIRED at 1 seed (n=999/1000, Welch's t-test unpaired, t=−2.453, p=0.01424, d_s=−0.110, bonf_sig=False); (2) per-record paired ACTUAL n=200 (Wave 216 P1 reanalysis of the canonical Wave 87 byte-stable seed=42 reference, t=−4.027, p=8.03e-05, d_z=−0.285, bonf_sig=True); (3) per-record paired PROJECTED N=1000 via standard paired-test scaling t_N = t_200 · √(1000/200) (t=−9.005, df=999, p=1.07e-18, d_z unchanged at −0.285, Bonf-sig at observed d_z post-hoc power 1.0).
- The 7/7 cross-wave 1-seed direction-consistency chain (Wave 82 / Wave 87 / Wave 195 P2 / Wave 206 P3 / Wave 208 P2 / Wave 216 P1 / Wave 225 P2) per CLM-068 R3 direction-consistent addendum.
- The evidence chain + SHA-256 anchors for 11 R3 evidence files + `wave216-p1-r3-per-record.json` (the Wave 216 P1 per-record projection artefact, read directly from `verification_outputs/`).
- The reproducibility path: CPU-only counterfactual path (verified-recipe; <5 sec total wall time; reproduces byte-stable fg_dev headline + Wave 216 P1 projected N=1000 d_z=-0.285 + p=1.07e-18 from JSON) + GPU path (DEFERRED; documented but NOT executable on current host due to RDKit 2026.03.5 environment blocker per Wave 351 P3 + Wave 357 P3; would require RDKit re-pin to canonical Wave 82 version, then `scripts/wave338_p5_r3_n1000_paired.py --n-total 1000 --nfe 250 --seeds 42 43 44 --device cuda:0`, ~30 min wall time).
- The honest status disclosure per Wave 268 strict-clean rule: **`PARTIAL / single-seed PROJECTED`** verdict label preserved verbatim — no promotion to SUPPORTED by wording despite PROJECTED N=1000 per-record Bonf-sig (the projection is a counterfactual on truncated n=200 ACTUAL; full N=1000 paired sweep DEFERRED to camera-ready).

**Smallest next action:** none required — this is a single-shot ADDITIVE recipe + audit. The R3 cell is now submittable at the highest reproducibility standard for an environment-blocked paper cell: SHA-256-anchored + bash+python-verified CPU-only path + GPU path documented for camera-ready resolution + honest `PARTIAL / single-seed PROJECTED` disclosure preserved verbatim.

---

## 2. Observed facts (what the artifacts say)

### 2.1 Recipe doc (NEW, this wave)

`paper-data/R3_flowmol3_fgdev/REPRODUCIBILITY_RECIPE.md` — 343 lines, SHA-256 = `0c91f4d966d4707e10e28c4198ace3b5b077e9646ead1c04408765444a6e8ba5`.

The recipe is structured as 5 sequential sections, mirroring the Wave 362 P1 R6 recipe pattern (`paper-data/R6_lineageflow_k6/R6_REPRODUCIBILITY_RECIPE.md`) and the Wave 363 P1 R2 / R5a / R5b recipe pattern:

| # | Section | Content |
|---|---|---|
| (a) | Headline metric | 3-granularity disclosure (per-arm aggregate UNPAIRED / per-record paired ACTUAL n=200 / per-record paired PROJECTED N=1000) + 7/7 cross-wave 1-seed direction-consistency table + RDKit 2026.03.5 environment blocker summary |
| (b) | Evidence chain + SHA-256 anchors | 12 per-file SHA-256 anchors verified at authorship; bash verification commands (sha256sum -c against paper-data/SHA256SUMS); cross-reference to `verification_outputs/MANIFEST.md` R3 section line 236 + entries on lines 247-259 + `tnnls_submission/data_availability.md` line 23 (vendored FlowMol3 repo HEAD `77cae22`) |
| (c) | Reproducibility path | 3-step CPU-only verified recipe (Step C.1 SHA-256 chain verify; Step C.2 byte-stable fg_dev headline reproduction; Step C.3 Wave 216 P1 PROJECTED N=1000 per-record d_z reproduction) + GPU path DEFERRED (RDKit environment blocker; documented command + expected wall-time + environment summary) |
| (d) | Disclosure — honest status label | `PARTIAL / single-seed PROJECTED` verdict label preserved verbatim per Wave 268 strict-clean rule; explicit enumeration of all 6 status labels (SUPPORTED / NOT_SIGNIFICANT / UNDERPOWERED / REGRESSES / DEFERRED / PARTIAL) with rationale per label; 5 verbatim one-line summaries from existing disclosure surfaces (paper §7.2 R3 row, abstract, CONSOLIDATED_RESULTS §15.105, CLAIMS.md CLM-068, headline-evidence SOURCE.md); explicit "what this recipe does NOT do" hard-guardrail enumeration |
| (e) | Acceptance Criteria | 7 acceptance criteria: SHA-256 chain (12 hashes), byte-stable fg_dev headline (±1e-12), Wave 216 P1 PROJECTED N=1000 d_z + t + p_raw (±1e-4 / ±1e-3 / ±1e-21), D.4 30/30 PASS, claims consistency PASS, ruff 0 findings, mkdocs strict PASS |

The recipe is longer than the "~120-line" target in the task brief (343 lines vs 120) because the R3 cell has 3-granularity disclosure (per-arm aggregate + per-record ACTUAL + per-record PROJECTED) + 7/7 cross-wave direction-consistency table + RDKit environment blocker summary, all of which are load-bearing for honest reviewer-facing reproducibility. The Wave 362 P1 R6 recipe is 205 lines and Wave 363 P1 R5a recipe is 231 lines — the R3 recipe at 343 lines is consistent with the documented multi-cell recipe pattern (the R3 cell has the most disclosure surfaces of any of the 7 R-cells due to the environment-blocked state).

### 2.2 SHA-256 chain verification (all 12 hashes verified at this audit)

```
$ cd paper-data && grep "R3_flowmol3_fgdev" SHA256SUMS | awk '{print $1"  "$2}' > /tmp/r3_sha.txt && sha256sum -c /tmp/r3_sha.txt
R3_flowmol3_fgdev/flowmol3_n1000_baseline_q4_2026.json: OK
R3_flowmol3_fgdev/flowmol3_n1000_framework_q4_2026.json: OK
R3_flowmol3_fgdev/flowmol3_n1000_sweep_q4_2026.json: OK
R3_flowmol3_fgdev/SOURCE.md: OK
R3_flowmol3_fgdev/wave206-p3-flowmol3-n1000.csv: OK
R3_flowmol3_fgdev/wave206-p3-flowmol3-n1000.json: OK
R3_flowmol3_fgdev/wave235-p4-flowmol3-3seed.csv: OK
R3_flowmol3_fgdev/wave235-p4-flowmol3-3seed.json: OK
R3_flowmol3_fgdev/wave235-p4-flowmol3-3seed-per-record.csv: OK
R3_flowmol3_fgdev/wave240-p2-flowmol3-direction.csv: OK
R3_flowmol3_fgdev/wave242-p2-flowmol3-direction.csv: OK
```

| Metric | Value |
|---|---|
| **SHA-256 chain hashes verified (paper-data/SHA256SUMS)** | 11/11 OK |
| **SHA-256 chain hashes verified (direct sha256sum, 12 files)** | 12/12 match recipe doc section (b) values |
| **Python snippet Step C.2 reproduces byte-stable fg_dev headline** | PASS (baseline=0.6381122391671532, framework=0.614627774616795, delta=−0.02348446455035824, all to ±1e-12) |
| **Python snippet Step C.3 reproduces Wave 216 P1 PROJECTED N=1000** | PASS (t_proj=−9.0045 ±1e-3, d_z=−0.2847 ±1e-4, p_raw=1.073e-18 ±1e-21) |
| **D.4 30/30 PASS** | PASS (verified post-edit; 30 passed, 3 deprecation warnings in ~4.00s) |
| **Claims consistency** | PASS (No drift detected; 61 active + 2 deprecated, CLM-068 R3 row preserved verbatim) |
| **Ruff 0 findings** | PASS (all checks passed) |
| **Mkdocs strict build** | PASS (Documentation built in ~21.55s; exit=0; no errors, only upstream mkdocs-material "MkDocs 2.0" deprecation advisory unrelated to R3 content) |

### 2.3 Hard-guardrail compliance (per AGENTS.md §3)

| Guardrail | Compliance |
|---|---|
| #1 — Vendored upstream is sacred | **n/a** — no `data/FlowMol3/` touched; vendored repo HEAD stays at `77cae22` (matches pinned commit per `tnnls_submission/data_availability.md` line 23 + the "Unmodified vendored upstream code" table) |
| #2 — No destructive edits | **PASS** — zero `paper-data/R3_flowmol3_fgdev/*` existing files modified (the 11 SHA256SUMS-anchored symlinks + R3_SOURCE.md + SOURCE.md symlink are preserved verbatim); only `REPRODUCIBILITY_RECIPE.md` (NEW) and `docs/audit/wave363-r3-recipe.md` (NEW, this file) added |
| #3 — NO-PUSH policy | **PASS** — commit message ends with `(USER AUTHORIZED, NO PUSH)` |
| #4 — Honest uncertainty | **PASS** — `PARTIAL / single-seed PROJECTED` verdict label preserved verbatim from paper §7.2 R3 row line 539 + CLM-068 R3 direction-consistent addendum + CONSOLIDATED_RESULTS §15.105; no promotion to SUPPORTED despite Wave 216 P1 PROJECTED N=1000 Bonf-sig (the projection is a counterfactual on truncated n=200 ACTUAL; full N=1000 paired sweep DEFERRED to camera-ready per RDKit blocker); explicit enumeration of what each of the 6 status labels does NOT apply (SUPPORTED / NOT_SIGNIFICANT / UNDERPOWERED / REGRESSES / DEFERRED / PARTIAL) |
| #5 — TNNLS submission freeze | **n/a** — no `tnnls_submission/*` modified |
| #6 — Per-wave audit doc | **PASS** — this file is `docs/audit/wave363-r3-recipe.md` (mirrors the wave<NNN>-*.md pattern from Wave 121-273+) |
| #7 — Stricter = cleaner | **PASS** — 0 destructive edits; 2 NEW files only (this audit + the recipe); no existing paper-data/* touched; no `tnnls_submission/*` touched; no CLAIMS.md touched; no CONSOLIDATED_RESULTS.md touched; no paper-A-final.md touched |

### 2.4 Pre-commit verification gates (all PASS at this audit)

| Gate | Command | Result |
|---|---|---|
| D.4 byte-stable regression | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | **30 passed, 3 warnings** (RMSPreservingCoordinateMixer / RoundResultBundle / validate_round_result_bundle deprecations — per Wave 356 P3 audit §2.2 item #1) |
| Claims consistency | `python3 tools/check_claims_consistency.py` | **No drift detected** (61 active + 2 deprecated; CLM-068 R3 row preserved verbatim per Wave 268 strict-clean rule) |
| Ruff lint | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | **All checks passed!** (0 findings in scope dirs) |
| Mkdocs strict build | `mkdocs build --strict` | Exit 0 (Documentation built in ~21.55s; only upstream mkdocs-material "MkDocs 2.0" deprecation advisory unrelated to R3 content) |

### 2.5 Python snippet syntactic verification (this audit)

```bash
$ python3 -c "
import ast
src = open('paper-data/R3_flowmol3_fgdev/REPRODUCIBILITY_RECIPE.md').read()
parts = src.split('\`\`\`python')
ok = True
for i, p in enumerate(parts[1:], start=1):
    block, _, _ = p.partition('\`\`\`')
    try:
        ast.parse(block)
    except SyntaxError as e:
        print(f'block #{i} SYNTAX ERROR: {e}')
        ok = False
print('OK' if ok else 'FAIL')
"
OK
```

Both Python snippets in the recipe (Step C.2 byte-stable fg_dev reproduction + Step C.3 Wave 216 P1 PROJECTED N=1000 reproduction) parse without syntax errors.

### 2.6 Numerical reproduction verification (this audit)

Step C.2 (byte-stable fg_dev reproduction from `flowmol3_n1000_sweep_q4_2026.json`):

| Expected | Actual | Match |
|---|---|---|
| `baseline_fg_dev = 0.6381122391671532` | 0.6381122391671532 | ✓ (math.isclose abs_tol=1e-12) |
| `framework_fg_dev = 0.614627774616795` | 0.614627774616795 | ✓ (math.isclose abs_tol=1e-12) |
| `delta = -0.02348446455035824` | -0.02348446455035824 | ✓ (math.isclose abs_tol=1e-12) |

Step C.3 (Wave 216 P1 PROJECTED N=1000 from `wave216-p1-r3-per-record.json`):

| Expected | Actual | Match |
|---|---|---|
| `t_proj = -9.004526024927777` | -9.0045 (rounded) | ✓ (math.isclose abs_tol=1e-3) |
| `d_z = -0.28474811489033885` | -0.2847 (rounded) | ✓ (math.isclose abs_tol=1e-4) |
| `p_raw = 1.0728860143449855e-18` (scipy.stats.t.sf) | 1.073e-18 | ✓ (math.isclose abs_tol=1e-21) |
| `CI95 = [-0.43836059311135805, -0.2816394068886419]` | [-0.4384, -0.2816] | ✓ (within printed rounding) |

---

## 3. Interpretation (what the agent concludes)

### 3.1 Why this recipe is sufficient (not a workaround)

The R3 FlowMol3 fg_dev paper R-level `PARTIAL / single-seed PROJECTED` cell is carried by a **byte-stable evidence chain** anchored to the Wave 82 / Wave 87 sweep (byte-stability verified at delta < 1e-12 across 2 epochs per `docs/ARCHIVE/audit-waves-1-99/wave89-phase1-final.md` and the Wave 87 audit) + 6 subsequent reanalyses (Wave 195 P2 / Wave 206 P3 / Wave 208 P2 / Wave 216 P1 / Wave 225 P2 / Wave 225 P3) that all show direction-consistent framework-WINS at the 1 available seed (CLM-068 R3 direction-consistent addendum). The recipe bakes this entire chain into a single doc:

1. **Wave 82 / Wave 87 byte-stable sweep** (1-seed seed=42, NFE=250, N=999/1000 mols per arm, baseline fg_dev=0.6381, framework fg_dev=0.6146, Δ=−0.023484, 4.05σ) is the canonical paper headline.
2. **Wave 195 P2 R-level power** (Welch's t-test unpaired, t=−2.453, df=1996.998, p_raw=0.01424, Cohen's d_s=−0.110, Bonf α=0.05/7=0.007143, bonf_sig=False) is the per-arm aggregate statistical test — UNDERPOWERED at strict α but direction-consistent.
3. **Wave 206 P3 audit row** (12-col audit at `verification_outputs/wave206-p3-flowmol3-n1000.json`) preserves the byte-stable headline + discloses the blocked 3-seed pooled-SD upgrade.
4. **Wave 208 P2 per-record sanity** (N=200 ACTUAL paired t on REOS Glaxo+Dundee flag-count diff, t=−4.027, df=199, p=8.03e-05, Cohen's d_z=−0.285) establishes that the per-record proxy is Bonferroni-significant at ACTUAL N=200.
5. **Wave 216 P1 PROJECTED N=1000** (standard paired-test scaling t_N = t_200 · √(1000/200), t=−9.005, df=999, p=1.07e-18, d_z unchanged at −0.285) is the R-level R3 uplift — Bonferroni-significant at PROJECTED N=1000 paired granularity, but the projection is a counterfactual on the truncated n=200 ACTUAL.
6. **Wave 225 P2 bootstrap + Wave 225 P3 cross-seed historical** (7/7 direction-consistent framework-WINS at 1 available seed) is the cross-wave direction-consistency check.
7. **Wave 351 P3 + Wave 357 P3 RDKit environment blocker** documents the load-bearing blocker (RDKit 2026.03.5 environment drift producing 36.7% valid-yield at n=30 vs canonical 99.9%) that prevents the full N=1000 paired 3-seed sweep from re-running on the current environment — the blocker is environment-side, not framework-side.

The recipe's job is to make **all 7 layers** byte-addressable and reproducible, so a reviewer can verify the §7.2 `PARTIAL / single-seed PROJECTED` verdict without re-running the original FlowMol3 GPU sweep (and without re-running the new GPU sweep, which is environmentally blocked).

### 3.2 Why the recipe uses 2 reproducibility paths (CPU + GPU)

The R3 cell has **two reproducibility paths** because the evidence chain spans **two methodological generations**:

- **CPU-only counterfactual path** (Step C.1 / C.2 / C.3 in the recipe; <5 sec total wall time): reads the byte-stable Wave 82 / Wave 87 sweep JSON + Wave 216 P1 per-record JSON and reproduces (a) the fg_dev headline at ±1e-12 absolute tolerance, (b) the Wave 216 P1 PROJECTED N=1000 per-record d_z + t + p_raw at ±1e-4 / ±1e-3 / ±1e-21 absolute tolerance. This is the path a reviewer should use to verify the §7.2 R3 verdict on the current environment. Documented as the recommended path.
- **GPU live-sweep path** (`scripts/wave338_p5_r3_n1000_paired.py --n-total 1000 --nfe 250 --seeds 42 43 44 --device cuda:0`; ~30 min wall time; documented but DEFERRED): the source of the original Wave 87 sweep that populates the byte-stable evidence chain. Currently NOT executable on the current host because of the RDKit 2026.03.5 environment drift (Wave 351 P3 + Wave 357 P3); would require RDKit re-pin to canonical Wave 82 version, then re-run. Documented for camera-ready scope.

The dual-path structure mirrors the Wave 362 P1 R6 recipe (CPU counterfactual on Wave 161 frozen substrate + GPU 3-seed sweep documented but DEFERRED) and the Wave 363 P1 R2 / R5a recipes (CPU verification + GPU re-run command documented). For R3, the GPU path is uniquely environment-blocked (not budget-blocked, not framework-blocked, not vendor-blocked) — the blocker is RDKit 2026.03.5 environment drift, which is a third-party dependency outside the framework's scope per Wave 351 P3 §3.3.

### 3.3 Why the PARTIAL / single-seed PROJECTED verdict label is preserved verbatim (no promotion by wording)

Per Wave 268 strict-clean rule (status history additive, no removal; no promotion of `UNDERPOWERED` / `DEFERRED` / `REGRESSES` / `NOT_SIGNIFICANT` to `SUPPORTED` by wording alone) AND Wave 195 P1 verdict-precedence rule 1 (TIE > NOT_SIGNIFICANT/SUPPORTED when |Δ| < min_effect_size), the R3 cell's `PARTIAL / single-seed PROJECTED` label is **canonical and correctly disclosed**. The recipe's section (d) explicitly enumerates what each of the 6 status labels does and does NOT apply to R3:

| Status label | Applies? | Why |
|---|---|---|
| `SUPPORTED` | NO | Per-arm aggregate UNPAIRED at 1 seed is `UNDERPOWERED` (bonf_sig=False at α=0.007143); per-record paired at PROJECTED N=1000 is Bonf-sig, but the projection is a counterfactual on the truncated n=200 ACTUAL (full N=1000 paired sweep DEFERRED). |
| `NOT_SIGNIFICANT` | NO | Wave 195 P2 / Wave 206 P3 unpaired reading is direction-consistent framework-WINS but UNDERPOWERED at Bonferroni α; this is `UNDERPOWERED`, not `NOT_SIGNIFICANT`. |
| `UNDERPOWERED` | Partial — per-arm aggregate UNPAIRED | Welch's t-test unpaired: t=-2.453, df=1996.998, p_raw=0.01424, d_s=-0.110, bonf_sig=False. |
| `REGRESSES` | NO | Direction is framework-WINS (−0.023484, framework has lower fg_dev = better). |
| `DEFERRED` | Partial — full N=1000 paired 3-seed sweep | Full N=1000 paired sweep with full SMILES retention is on the camera-ready deferred list per Wave 351 P3 + Wave 357 P3 RDKit environment blocker. |
| `PARTIAL / single-seed PROJECTED` | **YES — the canonical R3 verdict label** | 1-seed byte-stable −0.023484 fg_dev framework-WINS + per-record proxy d_z=−0.285 + 7/7 cross-wave direction-consistency + PROJECTED N=1000 Bonf-sig but on a counterfactual projection. |

The recipe surfaces 5 verbatim one-line summaries from existing disclosure surfaces (paper §7.2 R3 row line 539, paper abstract Wave 354 P3 line 7(c), CONSOLIDATED_RESULTS §15.105 Wave 357 P3, CLAIMS.md CLM-068 R3 direction-consistent addendum, headline-evidence r2_flowmol3_fgdev_4p05sigma/SOURCE.md Wave 135 P3 freeze), all of which are already documented across multiple surfaces and remain **preserved verbatim** — no new framing is introduced by this recipe.

### 3.4 What this recipe does NOT do (hard-guardrail enumeration)

The recipe's section (d) explicitly enumerates what it does NOT do, mirroring the AGENTS.md §3 hard guardrails:

- Does NOT promote `UNDERPOWERED` / `DEFERRED` / `REGRESSES` to `SUPPORTED` by wording. The R3 verdict label `PARTIAL / single-seed PROJECTED` is preserved verbatim from existing surfaces.
- Does NOT modify vendored upstream code (`data/FlowMol3/repo` stays at `77cae22`, byte-identical to upstream).
- Does NOT modify `tnnls_submission/` SHA-256-pinned package (this recipe lives in `paper-data/`, not `tnnls_submission/`).
- Does NOT modify `docs/CLAIMS.md` CLM-068 (no wording / number / status change).
- Does NOT re-run the GPU sweep (RDKit environment blocker per Wave 351 P3 / Wave 357 P3; the CPU-only byte-stable path is the canonical reviewer-facing verification path on the current environment).

This explicit enumeration makes the additive-only nature of the recipe reviewer-visible: the recipe is a single-source-of-truth documentation layer that bakes the existing 7-layer evidence chain into one doc, without changing any status label, any number, any verdict, or any vendored file.

---

## 4. Cross-references and acceptance gates

### 4.1 Linked scripts / surfaces

- `paper-data/R3_flowmol3_fgdev/REPRODUCIBILITY_RECIPE.md` — NEW recipe doc (this wave).
- `paper-data/R3_flowmol3_fgdev/R3_SOURCE.md` — existing Wave 235 P4 / Wave 23 source provenance for R3 (preserved verbatim).
- `paper-data/R3_flowmol3_fgdev/SOURCE.md` — symlink to `docs/headline-evidence/r2_flowmol3_fgdev_4p05sigma/SOURCE.md` (preserved verbatim).
- `paper-data/R3_flowmol3_fgdev/SHA256SUMS` — root-level paper-data SHA256SUMS (11 R3 entries verified OK at this audit).
- `reproduce/03_R3_FlowMol3.sh` — existing R-level per-cell reproduction script (verifies Wave 216 P1 per-record d_z=-0.285 from JSON; pre-existing, NOT modified by this wave).
- `scripts/wave338_p5_r3_n1000_paired.py` — existing operational sweep driver for the 3-seed paired sweep (the GPU path command documented in recipe section (c)).
- `tools/wave87_n1000_sweep.py` — Wave 87 sweep tool that produced the canonical byte-stable reference (the per-arm aggregate source-of-truth; `tools/wave87_n1000_sweep.py:298` is the per-record data-capping site referenced in the Wave 216 P1 data-truncation disclosure).
- `tools/wave216_p1_r3_per_record.py` — Wave 216 P1 per-record uplift tool (referenced in `reproduce/03_R3_FlowMol3.sh` step 4 optional run command; pre-existing).
- `docs/audit/wave357-r3-rdkit-blocker-doc.md` — Wave 357 P3 R3 RDKit environment blocker documentation (canonical R3 deferred-state disclosure).
- `docs/audit/wave351-r3-vendor-fix-status.md` — Wave 351 P3 R3 vendor-fix status (DGL operational, RDKit gap load-bearing).
- `docs/audit/wave338-p5-r3-dgl-fix-and-sweep.md` — Wave 338 P5 canonical DGL-fix audit (fix at `adaptive_reflow/adapters/flowmol3_v2_adapter.py:2861-2885` + `3002-3011`).
- `docs/audit/stats_method/p3-r3-cross-seed.md` — Wave 225 P3 R3 cross-wave 1-seed direction-consistency check (7/7 framework-WINS).
- `docs/audit/stats_method/p1-r3-uplift.md` — Wave 216 P1 R3 per-record uplift (ACTUAL n=200 + PROJECTED N=1000).
- `docs/CLAIMS.md` CLM-068 — R3 cross-wave 7/7 direction-consistency addendum (preserved verbatim; no Wave 363 modification).
- `docs/CONSOLIDATED_RESULTS.md` §15.105 (Wave 357 P3) — R3 RDKit environment blocker documentation in the reviewer-facing consolidated-results ledger (preserved verbatim).
- `docs/drafts/paper-A-final.md` §7.2 R3 row (line 539) + Wave 357 P3 ADDITIVE footnote (line 541) — paper draft R3 row text (preserved verbatim).
- `verification_outputs/MANIFEST.md` R3 section (line 236) — canonical SHA-256 sidecar for the 13 R3 files.
- `tnnls_submission/data_availability.md` line 23 — vendored FlowMol3 repo HEAD `77cae22` (matches pinned commit; "Unmodified vendored upstream code" table).
- `env_hash_R3.txt` — R3 venv fingerprint (Python 3.12.13 + torch 2.7.0+cu128 / CUDA 12.8; adapter_deps_hash `0e9e0b9c...`; composite_hash `8ca7e303...`).

### 4.2 Acceptance gates (this audit, all PASS)

| Gate | Command | Result |
|---|---|---|
| SHA-256 chain (11 files via paper-data/SHA256SUMS) | `cd paper-data && grep "R3_flowmol3_fgdev" SHA256SUMS \| awk '{print \$1"  "\$2}' > /tmp/r3_sha.txt && sha256sum -c /tmp/r3_sha.txt` | **11/11 OK** |
| SHA-256 chain (12 files via direct sha256sum) | `sha256sum verification_outputs/flowmol3_n1000_*_q4_2026.json verification_outputs/wave206-p3-flowmol3-n1000.{json,csv} verification_outputs/wave216-p1-r3-per-record.json verification_outputs/wave235-p4-flowmol3-3seed.{json,csv} verification_outputs/wave235-p4-flowmol3-3seed-per-record.csv verification_outputs/wave240-p2-flowmol3-direction.csv verification_outputs/wave242-p2-flowmol3-direction.csv` | **12/12 match** |
| Recipe Python snippet Step C.2 (byte-stable fg_dev) | `python3 -c "..."` (script in recipe section c) | **PASS** — all 3 expected values match to ±1e-12 |
| Recipe Python snippet Step C.3 (Wave 216 P1 PROJECTED N=1000) | `python3 -c "..."` (script in recipe section c) | **PASS** — t_proj, d_z, p_raw all match expected values |
| Recipe Python syntactic validity | `python3 -c "import ast; ..."` | **PASS** — both snippets parse without syntax errors |
| D.4 byte-stable regression | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | **30 passed, 3 warnings** |
| Claims consistency | `python3 tools/check_claims_consistency.py` | **No drift detected** (61 active + 2 deprecated) |
| Ruff lint | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | **All checks passed!** |
| Mkdocs strict build | `mkdocs build --strict` | **Exit 0** |

---

## 5. Action Items

| Item | Status |
|---|---|
| Author `paper-data/R3_flowmol3_fgdev/REPRODUCIBILITY_RECIPE.md` | **CLOSED** — this wave (NEW 343-line doc; SHA-256 `0c91f4d9...`) |
| Verify SHA-256 chain (11 R3 files via paper-data/SHA256SUMS) | **CLOSED** — this wave (11/11 OK) |
| Verify SHA-256 chain (12 R3 files via direct sha256sum) | **CLOSED** — this wave (12/12 match) |
| Verify Python snippet Step C.2 reproduces byte-stable fg_dev headline | **CLOSED** — this wave (3/3 expected values match to ±1e-12) |
| Verify Python snippet Step C.3 reproduces Wave 216 P1 PROJECTED N=1000 | **CLOSED** — this wave (t_proj + d_z + p_raw all match to ±1e-4 / ±1e-3 / ±1e-21) |
| Verify Python snippets parse without syntax errors | **CLOSED** — this wave (2/2 snippets parse) |
| Verify D.4 30/30 PASS | **CLOSED** — this wave (30/30 PASS) |
| Verify claims consistency (CLM-068 R3 row preserved verbatim) | **CLOSED** — this wave (No drift detected; 61 active + 2 deprecated) |
| Verify ruff 0 findings | **CLOSED** — this wave (All checks passed!) |
| Verify mkdocs strict build | **CLOSED** — this wave (exit 0; no errors) |
| Pin RDKit to canonical Wave 82 version in `flowmol3_venv` (env-side fix) | **OPEN** — per Wave 351 P3 §3.3 disposition; required before full N=1000 paired sweep can re-run on current host |
| Container reproduction of canonical Wave 82 environment | **OPEN** — per Wave 351 P3 §3.3 disposition (new action item from Wave 351 P3 smoke test) |
| Re-run R3 N=1000 paired sweep at 3 seeds with verified environment + DGL fix | **DEFERRED to camera-ready** — environment verification prerequisite (per Wave 351 P3 §3.4) |
| Update CLM-068 with Wave 338 P5 + Wave 351 P3 + Wave 357 P3 env-blocker disclosure | **TODO** (additive only; no number change) — currently the disclosure is distributed across paper §7.2 R3 row footnote (Wave 357 P3) + paper §10.1 + paper §11.2 + CONSOLIDATED_RESULTS §15.105; per Wave 357 P3 additive-only disposition, CLM-068 itself is NOT modified (preserved verbatim) |

---

_Last updated: 2026-09-27 (Wave 363 P1 — R3 reproducibility recipe authored: 343-line NEW `paper-data/R3_flowmol3_fgdev/REPRODUCIBILITY_RECIPE.md` with 5 sections (a/b/c/d/e) + SHA-256 chain + CPU/GPU reproducibility commands + honest `PARTIAL / single-seed PROJECTED` disclosure preserved verbatim; this audit doc at `docs/audit/wave363-r3-recipe.md` is the per-wave audit)._