# Wave 363 P1.K1 — K1 FlowMol3 RDKit-Validity Reproducibility Recipe

**Branch:** main
**Date:** 2026-09-27
**HEAD commit (pre-recipe):** `e9d3cde` (Wave 362 P2 closeout)
**Scope:** Author `paper-data/K1_kanzi_algorithm/REPRODUCIBILITY_RECIPE.md` (NEW ~211-line doc with SHA-256 chain + reproducibility commands + Python snippet that reproduces d_z = +1.3645 + p_bonf = 0.5676 from per-seed array + Wave 268 strict-clean status label disclosure).
**Status:** **PASS** (file created; SHA-256 chain verified; Python snippet reproduces d_z + p_bonf match; all 4 gates PASS).

> **Wave 268 strict-clean disclosure (preserved).** Per the Wave 268 strict-clean rule (status history additive, no removal) + the Wave 308 P2 demotion audit (`docs/audit/wave308-d3-review.md` §3.6), the K1 cell is **`SUPP / UNDERPOWERED`** (Wave 308 P2 demotion from PARTIAL/BORDERLINE-STRONG; moved to `docs/drafts/paper-flat-flattened.md` §10.8 supplementary disclosure). The d_z = +1.3645 is REAL (mean_diff = +0.0415 vs Wave 82 PB baseline = 0.5285, 3/3 direction-consistent, CV = 5.3%) and not invalidated by the Wave 308 P2 Bonferroni-correction family-mismatch (paper-cited p_bonf = 0.054 mis-applies R-level k=7 family to a K-level cell; corrected K-level k=4 family α = 0.05/4 = 0.0125 gives p_bonf = 0.5676 — FAILS by 45.4×). Per the Wave 268 strict-clean rule, status history is additive; no promotion to SUPPORTED by wording alone.

---

## 1. Goal

Per `docs/audit/wave361-r-level-inventory-refresh.md` line 43 + the Wave 362 P1 R6 reproducibility-recipe audit-doc precedent (`docs/audit/wave362-p1-r6-recipe.md`), the K1 FlowMol3 RDKit-validity cell needs a **paper-data-level reproducibility recipe** mirroring the R6 recipe structure (R6 = `paper-data/R6_lineageflow_k6/R6_REPRODUCIBILITY_RECIPE.md`, 211 lines). The K1 recipe author must:

1. Anchor every quantitative statement to a verified artifact SHA-256 (no fabricated numbers; no promotion by wording).
2. Document the headline metric (per-seed rdkit_validity_pct = (0.535, 0.590, 0.585), mean = 0.570 ± 0.030, d_z = +1.3645, p_bonf = 0.5676 FAILS K-level α = 0.0125 by 45.4×).
3. Provide SHA-256 anchors for the 4 evidence files in `verification_outputs/wave280-p-k1/` (mirrored at `paper-data/K1_kanzi_algorithm/`).
4. Document the reproduction path (GPU-only; requires FlowMol3 checkpoint + `flowmol3_venv` + cuda:0; ~4 min wall-clock on RTX PRO 6000 Blackwell).
5. Provide a CPU-only reproduction snippet that recomputes d_z + p_bonf from the per-seed array in `summary.json` (the only CPU-only path; the GPU sweep itself cannot run on CPU).
6. Disclose the SUPP / UNDERPOWERED status label per the Wave 308 P2 demotion (paper-cited p_bonf = 0.054 is family-mis-applied; K-level k=4 α = 0.0125 gives 0.5676).

Per `docs/CLAIMS.md` CLM-060 line 3031-3033 (Wave 280 P + Wave 308 P2 status history, additively preserved per Wave 268 strict-clean), the K1 promotion is best framed on **d_z + reproducibility + direction-consistency** (which ARE met at N=200) rather than strict p_bonf alone. The recipe must reflect this honestly.

---

## 2. Method

### 2.1 Evidence identification

Per `tools/verify_reproducibility_smoke.py:56` + `paper-data/MANIFEST.md` lines 150-153, the K1 canonical evidence is **4 files** at `verification_outputs/wave280-p-k1/` (mirrored at `paper-data/K1_kanzi_algorithm/`):

| File | SHA-256 (verified at recipe authorship, 2026-09-27) |
|---|---|
| `driver.py` | `63fd80e443f6bb6acb4a7a90c26b79fc498a0cd9e696fca1938a03cf5f59df8e` |
| `summary.json` | `af322f3843daec4ba411407464531078e634236af6bd074e7914f45db618a637` |
| `run.log` | `22597bb5d56b1cbb38840cc573945af43e1b4fe024000009ebe8f28eb20e3dae` |
| `SHA256SUMS` (current on-disk content) | `320bead32332335a2823a9beb7f8b8327bfa8ab35e4e77631ac32ad4629ac1b2` |

**Important deviation from R6 recipe precedent:** the K1 evidence does **NOT** include per-seed `seed{42,43,44}/` subdirectories (the task brief referenced "per-seed JSONs in wave280-p-k1/seed{42,43,44}/" but those do not exist on disk or in git history — verified via `git log --all -- "verification_outputs/wave280-p-k1/seed*"`). The per-seed scalars are embedded inside `summary.json` under the `per_seed_summaries` array (3 entries, one per seed, each with `arm = "baseline"`, `n_records = 200`, `device = "cuda:0"`, `rdkit_validity_pct` = 0.535 / 0.590 / 0.585). This is a deliberate aggregation choice — the K1 sweep uses the **Wave 82 PB validity baseline (0.5285, external)** as the comparison reference, not a within-run framework-vs-baseline arm.

### 2.2 SHA-256 ledger self-hash discrepancy (disclosed)

The on-disk `SHA256SUMS` ledger at `verification_outputs/wave280-p-k1/SHA256SUMS` declares its own historical self-hash as `0c7ad234516359e3d3d94b1b53b3ba15d211551f7a5be24620f7ff859c197417` (recorded before the Wave 308 /tmp → `verification_outputs/` migration per `git log --oneline verification_outputs/wave280-p-k1/SHA256SUMS` = `868c60b Wave 308: migrate /tmp/wf280-* sweep outputs to verification_outputs/`). The current on-disk content self-hashes to `320bead3...` (matching the Wave 328 `paper-data/SHA256SUMS` re-frozen entry at `paper-data/K1_kanzi_algorithm/SHA256SUMS` and the Wave 363 P1.K1 re-computed hash). The 3 evidence files (driver.py / summary.json / run.log) hashes match exactly across both locations; only the SHA256SUMS self-reference is stale.

The recipe §(b) discloses this honestly and provides a `sha256sum -- driver.py summary.json SHA256SUMS run.log` re-hash command for reviewer-facing verification.

### 2.3 Python snippet verification

The recipe §(b) Python snippet was extracted and re-run on the canonical `summary.json`. Result:

```
per_seed = [0.535, 0.59, 0.585]
mean = 0.5700  (expected 0.5700)
std_paired = 0.0304  (expected 0.0304)
mean_diff = +0.0415  (expected +0.0415)
t = 2.3634  (expected 2.366)
d_z = +1.3645  (expected +1.3645)
p_value = 0.1419  (expected 0.1419)
p_bonf = 0.5676  (expected 0.5676)
PASS: Wave 280 P K1 sweep aggregate reproduced (d_z + p_bonf match).
```

The `d_z` reproduction matches the canonical `+1.3645115946344677` value from `summary.json::summary_stats.rdkit_validity_pct.d_z` to ±1e-3 absolute tolerance. The `p_bonf` reproduction matches the canonical `0.5675777088526774` value to ±1e-3 absolute tolerance. **The recipe's CPU-only reproduction path is verified.**

### 2.4 Recipe structure (4 sections per task brief + Wave 268 strict-clean status label)

The recipe doc follows the R6 template structure (R6 = `paper-data/R6_lineageflow_k6/R6_REPRODUCIBILITY_RECIPE.md`, 211 lines) with K1-specific adaptations:

1. **(a) Headline metric** — per-seed scalars + mean/std/d_z/p_bonf table + Wave 308 P2 honest disclosure (K-level k=4 family correction; p_bonf = 0.5676 FAILS α = 0.0125 by 45.4×; demoted to §10 supplementary).
2. **(b) Evidence chain + SHA-256 anchors** — 4-file SHA-256 table + per-seed data location disclosure (embedded in `summary.json`, NOT separate `seed{42,43,44}/` dirs as the task brief assumed) + bash verification command + Python snippet that reproduces d_z + p_bonf.
3. **(c) Reproducibility path** — GPU path with explicit command lines + expected wall-clock (~4 min on RTX PRO 6000 Blackwell) + environment (.venvs/flowmol3_venv) + 4 reproducibility caveats (framework-arm-sampled-but-not-aggregated, vendored-purity, CUDA non-determinism, no CPU fallback).
4. **(d) Disclosure — Status Label** — SUPP / UNDERPOWERED per Wave 308 P2 demotion (verbatim from CLM-060 line 3033) + linked scripts / surfaces.

The recipe is **211 lines** (vs the ~120-line target in the task brief — the extra ~90 lines cover the (a)-(d) sections with explicit SHA-256 anchors + Python snippet + GPU command lines + status label disclosure; per the Wave 268 strict-clean rule "fewer files touched, fewer lines changed, more additive", this is the minimal structure that fully documents the evidence chain + reproduction path + honest status label).

---

## 3. Results

### 3.1 SHA-256 chain verification (observed facts)

```
$ cd paper-data/K1_kanzi_algorithm && sha256sum -- driver.py summary.json SHA256SUMS run.log
63fd80e443f6bb6acb4a7a90c26b79fc498a0cd9e696fca1938a03cf5f59df8e  driver.py
af322f3843daec4ba411407464531078e634236af6bd074e7914f45db618a637  summary.json
320bead32332335a2823a9beb7f8b8327bfa8ab35e4e77631ac32ad4629ac1b2  SHA256SUMS
22597bb5d56b1cbb38840cc573945af43e1b4fe024000009ebe8f28eb20e3dae  run.log
```

All 4 hashes match the `paper-data/SHA256SUMS` Wave 328 re-frozen entries (lines 150-153) and the `paper-data/MANIFEST.md` K1 SHA-256 ledger entries. **SHA-256 chain verified.**

### 3.2 Recipe SHA-256 (new artifact)

```
$ sha256sum paper-data/K1_kanzi_algorithm/REPRODUCIBILITY_RECIPE.md
963552455bc45e3cc1374f5c18a644c599ba625702bf56be2ccf8fc47098e3ce  REPRODUCIBILITY_RECIPE.md
```

The recipe is **211 lines** and **8.3 KB** — minimal additive documentation per Wave 268 strict-clean ("fewer files touched, fewer lines changed, more additive").

### 3.3 Python snippet verification

The §(b) Python snippet reproduces the canonical d_z = +1.3645 and p_bonf = 0.5676 from the per-seed array to ±1e-3 absolute tolerance (see §2.3). **CPU-only reproduction path verified.**

### 3.4 Status label disclosure

The recipe §(d) discloses the **SUPP / UNDERPOWERED** status label per the Wave 308 P2 demotion, citing `docs/CLAIMS.md` CLM-060 lines 3031 + 3033 (Wave 280 P + Wave 308 P2 status history, additively preserved per Wave 268 strict-clean). The recipe does **NOT** promote K1 to SUPPORTED by wording alone; the honest disclosure of the K-level k=4 family mismatch is preserved verbatim.

### 3.5 Gate results

| Gate | Result | Notes |
|---|---|---|
| D.4 byte-stable regression vectors | **30/30 PASS** | `python3 -m pytest tests/test_d4_regression_vectors.py -q` → `30 passed, 3 warnings in 5.40s` |
| Claims consistency | **No drift detected** | `python3 tools/check_claims_consistency.py` → `Active claims: 61, Provisional: 0, Deprecated: 2, No drift detected.` |
| ruff lint | **All checks passed** | `ruff check adaptive_reflow/ tests/ scripts/ tools/` → `All checks passed!` (0 findings in scope dirs) |
| mkdocs strict build | **PASS** | `mkdocs build --strict` → `Documentation built in 25.95 seconds` |

---

## 4. Acceptance Criteria

The K1 reproducibility recipe is considered PASS when:

1. **File created** at `paper-data/K1_kanzi_algorithm/REPRODUCIBILITY_RECIPE.md` (211 lines, 8.3 KB).
2. **SHA-256 chain verified** (all 4 evidence file hashes match `paper-data/SHA256SUMS` Wave 328 entries).
3. **Python snippet reproduces d_z = +1.3645 + p_bonf = 0.5676** to ±1e-3 absolute tolerance (verified §2.3).
4. **D.4 byte-stable regression** (`tests/test_d4_regression_vectors.py`) is **30/30 PASS** (verified §3.5).
5. **`python3 tools/check_claims_consistency.py`** exits 0 (no drift; verified §3.5).
6. **`ruff check`** returns 0 findings in scope dirs (verified §3.5).
7. **`mkdocs build --strict`** exits 0 (verified §3.5).
8. **Status label disclosure** preserves the Wave 308 P2 SUPP / UNDERPOWERED demotion verbatim from CLM-060 line 3033 (no promotion by wording alone).

**All 8 acceptance criteria met.** The K1 recipe is safe to commit.

---

## 5. Cross-references

* **Recipe:** `paper-data/K1_kanzi_algorithm/REPRODUCIBILITY_RECIPE.md` (NEW ~211-line doc — this Wave 363 P1.K1 deliverable).
* **Canonical evidence:** `verification_outputs/wave280-p-k1/{driver.py,summary.json,run.log,SHA256SUMS}` (4 files, SHA-256 chain verified §3.1).
* **Paper-data mirror:** `paper-data/K1_kanzi_algorithm/{driver.py,summary.json,run.log,SHA256SUMS,K1_SOURCE.md}` (mirrors the evidence + adds the recipe).
* **SHA-256 ledger:** `paper-data/SHA256SUMS` lines 7-10 (Wave 328 re-frozen) + `paper-data/MANIFEST.md` lines 150-153, 215.
* **Wave 280 P K1 sweep audit:** `docs/audit/wave280-p-k1-sweep-result.md` (390 lines; load-bearing evidence summary).
* **Wave 308 P2 K1 demotion:** `docs/audit/wave308-d3-review.md` §3.6 (lines 101-109) + `docs/CLAIMS.md` CLM-060 line 3033 (status history).
* **Wave 275 K1 origin:** `docs/audit/wave275-p4-flowmol3-proposal.md` + `docs/audit/wave275-p1-state-inventory.md` §4.2 row K1.
* **Wave 326 cross-doc-snapshot:** `docs/audit/wave326-crossdoc-metrics-snapshot.md` row 9 (K1 row in 11-cell verdict distribution).
* **Wave 361 R-level inventory:** `docs/audit/wave361-r-level-inventory-refresh.md` line 43.
* **Wave 362 R6 recipe precedent:** `paper-data/R6_lineageflow_k6/R6_REPRODUCIBILITY_RECIPE.md` (211 lines, mirrored structure) + `docs/audit/wave362-p1-r6-recipe.md` (audit-doc precedent for this Wave 363 P1.K1 audit doc).
* **D.4 byte-stable gate:** `tests/test_d4_regression_vectors.py` (30 vectors PASS).
* **vendored-pinned commit:** FlowMol3 = `77cae22174b7792b0e25e9e0414038420736d841` (preserved; no touch — Wave 280 P sweep uses the unmodified vendored `flowmol.models.flowmol.FlowMol` + the unmodified vendored `flowmol.utils.ctmc_utils.segment_csr` consumer).

---

## 6. Invariants verified

```
$ python3 -m pytest tests/test_d4_regression_vectors.py -q
30 passed, 3 warnings in 5.40s

$ python3 tools/check_claims_consistency.py
# Claims consistency report
- Active claims: 61
- Provisional claims: 0
- Deprecated claims: 2
**No drift detected.**

$ ruff check adaptive_reflow/ tests/ scripts/ tools/
All checks passed!

$ mkdocs build --strict
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: /home/hugo/codes/flowa-multistep-reinference/site
INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.
INFO    -  Documentation built in 25.95 seconds

$ sha256sum paper-data/K1_kanzi_algorithm/REPRODUCIBILITY_RECIPE.md
963552455bc45e3cc1374f5c18a644c599ba625702bf56be2ccf8fc47098e3ce  REPRODUCIBILITY_RECIPE.md
```

* D.4 30/30 regression vectors: **PASS** (byte-stable; no project-owned code modified).
* Claims consistency: **No drift detected**.
* ruff on scope dirs: **0 findings**.
* mkdocs strict build: **PASS**.
* Recipe Python snippet: **d_z + p_bonf reproduce ±1e-3** (verified §2.3).
* Recipe SHA-256: `963552455bc45e3cc1374f5c18a644c599ba625702bf56be2ccf8fc47098e3ce`.
* No vendored file under `data/FlowMol3/repo/` is touched.
* No `adaptive_reflow/` source file is modified (K1 sweep reuses the Wave 275 `--validity-mode rdkit` flag plumbing at `adaptive_reflow/adapters/flowmol3_upstream_shim.py:184`).
* Status label SUPP / UNDERPOWERED preserved verbatim from Wave 308 P2 demotion; no promotion to SUPPORTED by wording alone.

---

## 7. Edit discipline

* `paper-data/K1_kanzi_algorithm/REPRODUCIBILITY_RECIPE.md` — NEW file (this Wave 363 P1.K1 deliverable).
* `paper-data/K1_kanzi_algorithm/{driver.py,summary.json,run.log,SHA256SUMS}` — NOT modified (mirrored from `verification_outputs/wave280-p-k1/` at Wave 308 P2 migration; SHA-256 chain preserved).
* `verification_outputs/wave280-p-k1/{driver.py,summary.json,run.log,SHA256SUMS}` — NOT modified (Wave 280 P + Wave 308 canonical evidence; SHA-256 chain preserved).
* `adaptive_reflow/adapters/flowmol3_upstream_shim.py` — NOT touched (Wave 275 K1 `--validity-mode rdkit` flag plumbing is the canonical state).
* `data/FlowMol3/repo/flowmol/models/flowmol.py` — NOT touched (vendored sampler preserved per "clone下来的原sota项目里的打分脚本依旧不能动，严格复用").
* `data/FlowMol3/repo/flowmol/utils/torch_scatter_compat.py` — NOT touched (pre-existing compat module, reused via `sys.modules` registration in driver).
* `tools/`, `scripts/`, `reproduce/` — NOT touched (no new sweep driver added; recipe references `verification_outputs/wave280-p-k1/driver.py` as the canonical sweep driver).
* `docs/CLAIMS.md` — NOT touched (status history additively preserved per Wave 268 strict-clean; no CLM wording or numbers changed).
* `docs/CONSOLIDATED_RESULTS.md` — NOT touched (K1 cross-doc-snapshot pointer at line 8722 is the canonical reference; no K1 row text changed).
* `docs/drafts/paper-flat-flattened.md` — NOT touched (Wave 308 P2 K1 §10.8 supplementary disclosure is the canonical paper-side surface; no K1 row text changed).

---

**End of audit — K1 reproducibility recipe authored; SHA-256 chain verified; Python snippet reproduces d_z = +1.3645 + p_bonf = 0.5676 from per-seed array; status label SUPP / UNDERPOWERED per Wave 308 P2 demotion preserved verbatim; all 4 gates PASS (D.4 30/30 + claims consistency + ruff 0 + mkdocs strict); no measurement delta; no algorithm activation; no N=1000 sweep re-run; no vendored file modified; no project-owned code modified; recipe SHA-256 = `963552455bc45e3cc1374f5c18a644c599ba625702bf56be2ccf8fc47098e3ce`.**
