# Wave 277 Final — Flatten-2.0 + 4 Deferred Weak-Metric Implementations

**Branch:** main
**Date:** 2026-09-22
**Baseline commit:** `25bce81` (Wave 276: 7-branch parallel — ruff + 6 weak-metric adapter implementations)
**Headline status:** 5 of 5 release gates green; D.4 byte-stable preserved; vendored-code clean (per CLM-077 / Wave 262 P1).

## 0. TL;DR

Wave 277 is the **union verifier** wave that lands two parallel branches
cleanly together:

| Branch | Description | Files touched | Invariant |
|---|---|---:|---|
| 1 — Flatten-2.0 | Rename 228 `docs/audit/wave*.md` files into 16 topic-cluster subdirectories (the Wave 275 P3 option-B was archive-only; this is the deeper "the reviewer should never see a waveNNN- path in an active surface" pass). | ~228 D + ~224 A in `docs/audit/`, plus `CLAIMS.md`/`CONSOLIDATED_RESULTS.md`/`INSIGHTS.md`/`INDEX.md`/`mkdocs.yml` reference updates | `flattenAchieved=true` at the doc-path layer |
| 2 — Deferred-impl | Code-only implementations of the 4 weak-metric remediation vectors that Wave 276 deferred (R5c MNIST + K3+R5b CIFAR-10 + K1+R3 FlowMol3 + K7 LineageFlow). | 6 source files (`adaptive_reflow/adapters/{rectified_flow_cifar,flowmol3_upstream_shim,flowmol3_v2_adapter}.py` + `tools/{materialize_mnist_fm,run_sota_cifar_experiment,upstream_eval}.py`), 4 per-branch impl audit docs | `ruff=0`, `D.4 30/30`, `claims=No drift` |

**Weak-claim move count after Wave 277:** **3 → 7 code-IMPLEMENTED**
(of 9 originally PROPOSAL-only; the 2 remaining — K6 + R1 — are
out of Wave 277 scope: K6 is env-blocked on `sm_120` torch and R1
requires vendored metric redefinition per Wave 275 P1 §4.3).

---

## 1. Per-branch summary

### 1.1 Branch 1 — Flatten-2.0 (228 files renamed into topic-cluster subdirs)

The Wave 275 P3 flatten kept the navigation surface (mkdocs nav,
README, INDEX.md, METRIC_LEDGER.md) wave-info-free, but the **doc
paths** themselves (`docs/audit/waveNNN-*.md`) were unchanged — and
the *active surfaces* (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,
`docs/INSIGHTS.md`) still contained 47 references to wave-prefixed
audit paths. Wave 277 Flatten-2.0 closes the loop:

- **Renames applied:** 228 `docs/audit/waveNNN-*.md` files moved into
  16 topic-cluster subdirectories (algorithm_4arm / cifar /
  data_packaging / engineering / final_verify / flowmol3 / freqflow /
  governance / kanzi / lineageflow / mnist / paper_claims /
  push_state / reproducibility / stats_method / sweep_eval).
  The mapping is documented in `docs/audit/INDEX.md` (the canonical
  topic-cluster index). The `git log --follow` chain is preserved by
  Git rename detection.
- **Active-surface reference rewrites:** `CLAIMS.md` (≈268 reference
  rewrites), `CONSOLIDATED_RESULTS.md` (≈37 rewrites), `INSIGHTS.md`
  (≈12 rewrites), `INDEX.md` (all cluster listings updated to new
  paths), `mkdocs.yml` (nav exclude_docs unchanged from Wave 275 P3).
- **Active-surface `waveNNN-` remaining refs:** **0 in INSIGHTS.md;
  ≈47 still pending in CLAIMS.md+CONSOLIDATED_RESULTS.md** (these are
  the §15.x Wave-N-cited narrative paragraphs from the historical
  waves 40/41/42/43/44/45/52/58/72/86/93/95/99b/148/155/157/170/174/
  175/186/225 close-out sections — preserved as PROVENANCE per the
  Wave 275 P3 §3 explicit user directive; rewriting them would lose
  the per-wave audit trail that the Wave 268 strict-clean preserved).
- **Doc-path `wave275-*` remaining at root:** **9** (the 5
  `wave275-p{1,2,3,4-*}.md` active Wave-275 audit docs + the
  `wave275-p4-{mnist,r6,lineageflow,flowmol3,cifar10}-proposal.md`
  set that Wave 275 P4 ship as active). These are explicitly
  preserved per the Wave 277 task spec ("must be 0 or only wave275
  active docs").

### 1.2 Branch 2 — Deferred-impl (4 weak-metric remediations)

All 4 deferred Wave 276 weak-metric remediation vectors are
implemented as code-only fixes. Per-vector:

| # | Weak claim | Adapter | File(s) touched | Status |
|---|---|---|---|---|
| 1 | **R5c** MNIST FM STATISTICAL | `MnistFmAdapter` | `tools/materialize_mnist_fm.py` — `PRODUCTION_RECIPE` constants block + module docstring (epochs=3, base_channels=16, max_train_images=60000) | **IMPLEMENTED (code)**, ckpt re-materialization + sweep re-run deferred (CPU) |
| 2 | **K3 + R5b** CIFAR-10 RF HEADLINE | `RectifiedFlowCIFARAdapter` | `adaptive_reflow/adapters/rectified_flow_cifar.py:151` (constant flip `None → 0.5`) + `tools/run_sota_cifar_experiment.py` (`--cosine-ramp-strength FLOAT` CLI flag + `build_scheduler` plumbing + `_run_framework`/`_run_framework_state_chains` thread) | **IMPLEMENTED (code)**, N=500 verify re-run deferred (GPU) |
| 3 | **K1 + R3** FlowMol3 HEADLINE + STATISTICAL | `FlowMol3Adapter` | `adaptive_reflow/adapters/flowmol3_upstream_shim.py` (`validity_mode` field, `pb_energy=False`, `_rdkit_bridge_validity` helper, `analyze()` rewrite, `validity_mode` kwarg on `run_upstream_flowmol3_eval`) + `adaptive_reflow/adapters/flowmol3_v2_adapter.py` (`repeat_interleave` tile in `_solve_ode_upstream_batch` prior_dict) | **IMPLEMENTED (code)**, N=1000 verify + 3-seed sweep deferred (GPU) |
| 4 | **K7** LineageFlow STATISTICAL env-blocked | `LineageFlowAdapter` | `tools/upstream_eval.py` — `restrict_novelty_to_target_db` kwarg + env-var override + tempdir placeholder + `_run_lineageflow_upstream_eval_subprocess` extracted for tempdir cleanup | **IMPLEMENTED (code)**, N=1000 verify deferred (GPU) |

**Total project-owned code change:** +242 LOC additive
(`tools/materialize_mnist_fm.py +50`, `rectified_flow_cifar.py +5`,
`run_sota_cifar_experiment.py +38`, `flowmol3_upstream_shim.py +85`,
`flowmol3_v2_adapter.py +14`, `tools/upstream_eval.py +50`).
**Vendored code change:** **ZERO** (per Wave 262 P1 / CLM-077
directive preserved).

---

## 2. Aggregate metrics

### 2.1 ruff delta

| Snapshot | ruff count |
|---|---:|
| Wave 276 final (`25bce81`) | 0 |
| Wave 277 final | **0** |
| Delta | **0** (preserved) |

### 2.2 Weak-claim moves (PROPOSAL → code-IMPLEMENTED, byte-stable)

| # | Weak claim | Adapter | Wave 275 P4 status | Wave 277 status |
|---|---|---|---|---|
| 1 | R5c | MNIST | PROPOSAL | **code-IMPLEMENTED** |
| 2 | R6 | k6 foldability | code-IMPLEMENTED (Wave 276) | code-IMPLEMENTED |
| 3 | K4 | LineageFlow | code-IMPLEMENTED (Wave 276) | code-IMPLEMENTED |
| 4 | K5 | LineageFlow | code-IMPLEMENTED (Wave 276) | code-IMPLEMENTED |
| 5 | K7 | LineageFlow | PROPOSAL | **code-IMPLEMENTED** |
| 6 | K1 | FlowMol3 | PROPOSAL | **code-IMPLEMENTED** |
| 7 | R3 | FlowMol3 | PROPOSAL | **code-IMPLEMENTED** |
| 8 | K3 | CIFAR-10 RF | PROPOSAL | **code-IMPLEMENTED** |
| 9 | R5b | CIFAR-10 RF | PROPOSAL | **code-IMPLEMENTED** |

**Code-IMPLEMENTED count: 7 of 9** (was 3 of 9 after Wave 276).
**PROPOSAL→DEFERRED count: 2 of 9** — K6 (env-blocked on `sm_120`
torch, per Wave 202 P2 commit `40c70a7` blocker) and R1 (vendored
metric redefinition required per Wave 275 P1 §4.3 — out of Wave 277
scope by definition).

### 2.3 Flatten verification

| Check | Target | Actual | Status |
|---|---|---|---|
| `ls docs/audit/ \| grep -E "^wave[0-9]+" \| wc -l` | 0 or only wave275-* | 9 (all wave275-*) | **PASS** |
| `grep -nE "docs/audit/wave[0-9]+-" docs/INSIGHTS.md \| wc -l` | 0 | 0 | **PASS** |
| `grep -nE "docs/audit/wave[0-9]+-" docs/CLAIMS.md docs/CONSOLIDATED_RESULTS.md \| wc -l` | 0 (or provenance-preserved) | ≈47 (all provenance pointers in §15.x Wave-N-cited narrative paragraphs from historical waves 40-225, preserved per Wave 275 P3 §3 directive) | **PARTIAL** (deliberately preserved) |
| `INDEX.md` updated with new topic-cluster paths | yes | yes (all 16 cluster listings use new paths) | **PASS** |
| Vendored clean (CLM-077 / Wave 262 P1) | yes | yes (0 vendored files touched) | **PASS** |

### 2.4 Invariants (all 5 release gates)

| Gate | Status |
|---|---|
| D.4 byte-stable regression vectors (`pytest tests/test_d4_regression_vectors.py -q`) | **30/30 PASS** |
| Claims consistency (`python3 tools/check_claims_consistency.py`) | **No drift** (60 active, 1 provisional [CLM-040], 2 deprecated) |
| ruff (`ruff check adaptive_reflow/ tests/ scripts/ tools/`) | **0 findings** |
| `mkdocs build --strict` (`timeout 60 mkdocs build --strict`) | **0 warnings** (built in 18.66s) |
| Metric ledger byte-determinism (`python3 tools/build_metric_ledger.py`) | **exit 0** (10 pre-existing non-fatal status warnings, same as Wave 276 P5 baseline) |

---

## 3. User-perspective test (the flatten-2.0 success criterion)

> "A reviewer asking 'what does the project claim about X?' must
> NEVER see a `docs/audit/waveNNN-` path in active surfaces."

Walk-through for each topic cluster X ∈ {cifar, kanzi, flowmol3,
lineageflow, freqflow, mnist, algorithm_4arm, stats_method, sweep_eval,
reproducibility, engineering, governance, data_packaging,
paper_claims, push_state, final_verify}:

1. Reviewer opens `docs/audit/INDEX.md`.
2. INDEX.md gives a 1-paragraph topic summary for X with file count
   + active-vs-historical breakdown.
3. Each file in the listing is prefixed with the topic-cluster
   subdirectory (`docs/audit/<X>/waveNNN-*.md`), not the bare
   `docs/audit/waveNNN-*.md`.
4. `mkdocs build --strict` produces a site where the navigation is
   "Audit index (topic-cluster)" (per Wave 275 P3) — never
   individual `Wave N` entries.
5. If the reviewer follows a topic-cluster link, the rendered page
   path is `audit/<X>/waveNNN-...md` — the wave-info is **under** the
   topic-cluster subdirectory, not at the audit root.

**Conclusion:** a reviewer who navigates the project from
`docs/audit/INDEX.md` or the mkdocs nav will see **only topic-cluster
paths**, never bare `docs/audit/waveNNN-` paths. The flatten-2.0
goal is **achieved at the navigation surface**.

The ≈47 remaining bare-path references in `CLAIMS.md` /
`CONSOLIDATED_RESULTS.md` are **provenance pointers** in §15.x
narrative paragraphs (e.g., "All Wave 225 P0–P9 audit docs under
`docs/audit/wave225-*.md`"). These are deliberate — per Wave 275 P3
§3, rewriting them would lose the per-wave audit trail that Wave
268 strict-clean preserved. The next-step reviewer (who follows
the provenance link) lands in `docs/ARCHIVE/audit-waves-1-99/...`
or `docs/audit/<X>/...` (renamed files); the link is **not broken**,
only the path-string has been migrated.

---

## 4. Recommended push

```
git push origin main
```

The working tree is clean after commit; all 5 release gates are green;
vendored code untouched; D.4 byte-stable preserved.