# Wave 43 — Final verify + synthesis (cleanup + paper wave)

**Date:** 2026-09-05
**Agent:** Wave 43 Agent C (final verify + synthesis)
**Branch:** `main`
**Base for the Wave-43 diff:** `8dc4c3a` (Wave 42 Agent E — final verify + MUST-3 shrink synthesis)
**HEAD at synthesis:** `5838ef6` (Wave 43 Agent A — real-metric layer in `tools/run_real_ckpt_eval.py`)

---

## TL;DR

Wave 43 was scoped by `todo/wave43-problems-review.md` as six specific
problems left standing after Wave 42. Five of the six were worked; the
sixth (push) is user-gated by design and was deliberately left
un-executed.

| Wave 43 problem | Owner | Outcome |
|---|---|---|
| **P1** — `_compute_metric` always returns the synthetic ceiling (top-model-claim blocker) | WF1 Agent A | **PARTIAL-CLOSED** — real per-model metric layer shipped behind `--metric-mode {synthetic\|real\|auto}`; Kanzi 3/3 cells flip `synthetic_fallback` → `computed`; `framework_wins` still 0 (see §3) |
| **P2** — sidecar deps for real downstream metrics | WF1 Agent B | **CLOSED (Kanzi side)** — 200-sequence Pfam held-out reference staged at `data/pfam_holdout/random_clan.fasta` (100 547 B); LineageFlow ESM-2-650M mirror still pending |
| **P3** — pytest pollution from the Wave 42 D.1 shrink | WF2 Agent A | **CLOSED** — both flagged findings were already resolved by `1d3cd2f`; the third was a wall-clock flake, not pollution |
| **P4** — paper writeup with Tier 3 (Kanzi + LineageFlow) results + figure | WF3 Agent B | **CLOSED** — `docs/paper-draft.md` §7 gains a claim statement, an honest verdict block, cross-links to §15.8–§15.10, and a new §7.6; figure regenerated; README Tier 3 evidence section added |
| **P5** — push 156 (now 160) unpushed commits | WF3 Agent A | **NOT DONE BY DESIGN** — `todo/PUSH-READY.md` authored; push remains user-gated (Wave 33 Agent H protocol) |
| **P6** — MUST-3 PARTIAL → PASS | WF2 Agent A | **NOT FLIPPED (honest)** — gate needs ≥5 adapters importing `adaptive_reflow/core/`; actual count is 2 |

**Verification gates at Wave-43 close:**

| Gate | Result |
|---|---|
| `pytest tests/ -q --tb=line` | **FAIL** — 9 failed, 4678 passed, 110 skipped (41:00). All 9 reproduce in isolation; classified in §5.2. One is a real import cycle (`import adaptive_reflow.theory` cold-fails); two are caused by Wave 43's own doc additions |
| `mkdocs build --strict` | **PASS** — exit 0, built in 8.40 s, 0 warnings |
| MUST-3 (framework-core glue extracted) | **PARTIAL** (unchanged; honestly documented, not reframed) |
| Paper Tier 3 section present | **YES** — `docs/paper-draft.md` §7 (§7.1–§7.6) |
| Commits in `8dc4c3a..HEAD` | **5** |
| Files changed in `8dc4c3a..HEAD` | **17** (3 803 insertions / 25 deletions) |

---

## 1. Commits

```
5838ef6  Wave 43 Agent A: real-metric layer in tools/run_real_ckpt_eval.py
66bfcef  Wave 43 Agent A: pytest pollution audit + MUST-3 close-out (PARTIAL maintained)
efc09a9  Wave 43 Agent A: push-prep verification summary + PUSH-READY doc (does NOT push)
28a1826  Wave 43 Agent B: Pfam held-out reference subset for protein_sequence_validity_rate
a4060f8  Wave 43 Agent B: paper writeup Tier 3 (Kanzi + LineageFlow) section + figure + README Tier 3 evidence
```

Files touched (17):

```
.gitignore
README.md
data/pfam_holdout/README.md
data/pfam_holdout/random_clan.fasta
docs/CONSOLIDATED_RESULTS.md
docs/audit/wave43-metric-layer-fix.md
docs/audit/wave43-must3-finalize.md
docs/audit/wave43-paper-tier3-writeup.md
docs/audit/wave43-pfam-sidecar-install.md
docs/audit/wave43-push-prep-summary.md
docs/audit/wave43-pytest-pollution-fix.md
docs/figures/tier3_real_ckpt_signed_mean.png
docs/paper-draft.md
todo/PUSH-READY.md
todo/framework-freeze-checklist.md
tools/_make_wave42_figure.py
tools/run_real_ckpt_eval.py
```

The only non-doc, non-data source change in the whole wave is
`tools/run_real_ckpt_eval.py` (+498 lines). No file under
`adaptive_reflow/` and no file under `tests/` was modified by any
Wave 43 agent — the wave was, by construction, a cleanup + paper wave
sitting on top of the frozen framework surface.

---

## 2. What actually moved (the load-bearing delta)

### 2.1 Metric layer: `synthetic_fallback` → `computed`

`tools/run_real_ckpt_eval.py` gains a `--metric-mode` flag with three
values (`synthetic`, `real`, `auto`). In `real` mode:

- **Kanzi** lazy-loads `kanzi.DAE` from the SHA-256-verified
  `data/kanzi_ckpt/cleaned_model.pt`, runs the forward pass, decodes
  cluster indices via a mod-20 AA proxy, and runs a Pfam-strict
  round-trip against the new held-out reference.
- **LineageFlow** lazy-loads ESM-2-650M via `transformers`, generates
  B=8 token sequences, and reports the fraction with PLL perplexity
  ≤ 50.

Result (`verification_outputs/kanzi_real_metric_q4_2026.json`, seeds
42/43/44 at NFE 50): `adapter_mode=torch` and
`marker=computed` in **3/3** cells, with full per-cell provenance in
`baseline_debug` / `framework_debug`
(`decode_strategy`, `round_trip_via`, `pfam_reference`, `ckpt_path`,
`seed`, `nfe_budget`). `n_synthetic_fallback = 0`.

This is the first time the Tier 3 numbers in this repo are derived
from published upstream code plus a published checkpoint plus real
reference data rather than from a hard-coded constant.

### 2.2 Pfam held-out reference

`data/pfam_holdout/random_clan.fasta` — 200 reviewed Swiss-Prot
proteins from Pfam clan **CL0192 (GPCR_A)** via entry **PF00001
(7tm_1)**, 100 547 bytes, fetched from the UniProt REST API in a
single request. The canonical `Pfam-A.fasta.gz` (6.2 GB) was
rejected on bandwidth grounds; the provenance and a regeneration
recipe are recorded in `data/pfam_holdout/README.md`. A `.gitignore`
allow-list entry was needed because the parent-directory exclusion is
opaque to `!` negations.

### 2.3 Paper §7

`docs/paper-draft.md` §7 now carries a one-sentence claim statement,
the per-cell Kanzi table, the LineageFlow forward-smoke row, the Tier
1 / Tier 2 / Tier 3 signed-mean verdict table, an explicit
closed-vs-pending block, and a new §7.6 documenting the Wave 43
artefacts. The figure `docs/figures/tier3_real_ckpt_signed_mean.png`
was regenerated (note text only — the underlying rows did not change).
`README.md` gains a Tier 3 evidence section pointing at the same
trail.

---

## 3. The honest caveat that survives Wave 43

The metric layer produces real numbers, but **both arms compute the
same number**. Baseline and framework each call the same upstream
forward path with the same seed, so their metric values are identical
and `framework_wins = 0` — every Kanzi cell still reports
`TIE_AT_SATURATION`, now at 1.000 rather than the old synthetic 0.950.

The marker flipped; the *signal* did not. This is a genuine
improvement in evidence quality (real upstream code, real checkpoint,
real reference data, real provenance) and **not** a demonstration
that the framework beats the baseline at Tier 3.

Closing that gap requires an adapter-surface change that Wave 43's
disjoint-file-scope contract explicitly excluded: adding
`observe_token_indices(trace) -> ndarray` to `KanziAdapter` and
`LineageFlowAdapter` so the metric layer consumes the framework's
actual ODE-trajectory endpoint instead of re-running a fresh upstream
forward. Estimated at < 20 LOC per adapter. Until that lands, the
Tier 3 bars in
`docs/figures/tier3_real_ckpt_signed_mean.png` stay at zero, and §7.5
of the paper says so.

Secondary blocker: the LineageFlow branch of the metric layer is
implemented and reachable but was never executed end-to-end — the
ESM-2-650M download (≈ 2.5 GB) timed out inside
`.venvs/lineageflow_venv/`. `verification_outputs/lineageflow_real_metric_q4_2026.json`
is a stub documenting the network-blocked state.

---

## 4. MUST-3: why it stays PARTIAL

Wave 42 shipped four D.1 "shrink" commits and the wave brief described
them as MUST-3 progress. Wave 43 Agent A checked the actual import
graph and found a mismatch between the brief and the gate:

| Adapter | Shrink commit | Consumes `adaptive_reflow/core/`? |
|---|---|:--:|
| `mnist_fm` | `491eca3` | No (`_adapter_common`) |
| `twodim_fm` | `09c08c0` | No (`_adapter_common`) |
| `rectified_flow_cifar` | `1d3cd2f` | No (`_adapter_common`) |
| `self_flow` | `16c8c3a` | **Yes** (`core.ckpt_loader`, `core.diffusers_wrapper`) |
| `flowmol3` | `7d18e33` | **Yes** (`core.graph_wrapper`) |

The MUST-3 acceptance gate requires **≥5** adapters importing from
`adaptive_reflow/core/`. The real count is **2**. Three of the five
shrinks deduplicated inlined helpers into the older P2-9
`_adapter_common` module — a legitimate refactor, but a different one
from the framework-core glue adoption MUST-3 gates on.

`todo/framework-freeze-checklist.md` now carries a "Wave 43 verify
(post-Wave 42 D.1 shrink) — MUST-3" section recording this. The gate
was **not** flipped and the definition was **not** loosened to make it
pass. Three more adapters need `core/` adoption; the checklist names
them.

---

## 5. Verification run by this agent

### 5.1 `mkdocs build --strict`

```
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: .../site
INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.
INFO    -  Documentation built in 8.40 seconds
exit 0
```

**PASS.** No `WARNING` lines, so `--strict` did not trip. All Wave 43
doc additions (six new `docs/audit/wave43-*.md` files, the §7 paper
edits, the new §15.10 in `docs/CONSOLIDATED_RESULTS.md`, the README
section) build cleanly.

### 5.2 `pytest tests/ -q --tb=line`

```
9 failed, 4678 passed, 110 skipped, 1026 warnings in 2460.92s (0:41:00)
```

**FAIL.** This agent re-ran each failure in isolation to separate real
defects from cross-run contention (a second full-suite run from another
agent was live on the same host). **All 9 reproduce standalone** — none
is a concurrency artifact. They fall into three groups.

#### Group A — import cycle in `adaptive_reflow.theory` (3 failures) — **REAL BUG**

| Test | Symptom |
|---|---|
| `tests/test_contracts/test_paper_quantities.py::test_no_torch` | collection `ImportError` in isolation |
| `tests/test_tools/test_benchmark_internal_uplifts.py::test_round2_external_covers_expected_keys` | same |
| `tests/test_tools/test_benchmark_internal_uplifts.py::test_round2_external_every_target_is_achieved` | same |

Cold-import matrix (`.venvs/flowmol3_venv/bin/python -c "import <m>"`):

| Module | Result |
|---|:--:|
| `adaptive_reflow` | OK |
| `adaptive_reflow.framework` | OK |
| `adaptive_reflow.adapters` | OK |
| `adaptive_reflow.eval` | OK |
| **`adaptive_reflow.theory`** | **FAIL** |
| **`adaptive_reflow.contracts.paper_quantities`** | **FAIL** |

```
ImportError: cannot import name 'Theorem1Statement' from partially
initialized module 'adaptive_reflow.theory.checkers'
(most likely due to a circular import)
```

The cycle:

```
adaptive_reflow/theory/__init__.py:70          → theory.checkers
adaptive_reflow/theory/checkers.py:79          → eval.lipschitz_diagnostic
adaptive_reflow/eval/__init__.py:122           → eval.twodim_fm_evaluator
adaptive_reflow/eval/twodim_fm_evaluator.py:95 → adapters.twodim_fm
adaptive_reflow/adapters/__init__.py:9         → adapters.flowmol3
adaptive_reflow/adapters/flowmol3.py:68        → framework.interfaces
adaptive_reflow/framework/interfaces.py:63     → theory.checkers  ← partially initialized
```

`import adaptive_reflow.theory` cold-fails unconditionally. It only
survives the full suite because some earlier test imports
`adaptive_reflow.framework` first and primes the cycle — which is why
this shows up as a *test-order-dependent* failure rather than a
collection error across the board.

This is the same failure class Wave 41 Agent C fixed for
`test_algo_uplifts` (`8dc4c3a` lineage); the fix was applied at one
entry point, not at the cycle. The standard remedy already used
elsewhere in this repo is the lazy `__getattr__` pattern from
commit `28e3bf9` — applied here to `framework/interfaces.py:63` (defer
the `theory.checkers` import) or to `eval/__init__.py:122` (defer the
`twodim_fm_evaluator` import, which is what actually drags the whole
adapter package into the theory import).

**This is the one finding in Wave 43 that should gate the push.** It is
not caused by any Wave 43 commit — no Wave 43 commit touches
`adaptive_reflow/` — but it is a live defect in the code about to be
pushed, and `docs/audit/wave43-pytest-pollution-fix.md` reported
"0 uncommitted pytest pollution" on the strength of a `tests/test_adapters/`
run only (976 passed), which does not exercise this path.

#### Group B — doc-symbol checker, caused by Wave 43's own docs (2 failures) — **WAVE 43 REGRESSION**

| Test | Symptom |
|---|---|
| `tests/test_tools/test_check_docs_against_code.py::test_no_false_positives_on_current_repo` | 11 unresolvable inline symbols |
| `tests/test_tools/test_check_docs_against_code.py::test_self_test_quiet_mode_returns_zero_exit` | same root cause |

The 11 offending claims:

```
README.md:421                 `TIE_AT_SATURATION`
CONSOLIDATED_RESULTS.md:1020  `TIE_AT_SATURATION`
CONSOLIDATED_RESULTS.md:1247  `TIE_AT_SATURATION`
CONSOLIDATED_RESULTS.md:1273  `TIE_AT_SATURATION`
CONSOLIDATED_RESULTS.md:1347  `TIE_AT_SATURATION`
CONSOLIDATED_RESULTS.md:1403  `TIE_AT_SATURATION`
CONSOLIDATED_RESULTS.md:1436  `LineageFlowClassifier`
CONSOLIDATED_RESULTS.md:1468  `TIE_AT_SATURATION`
paper-draft.md:964            `TIE_AT_SATURATION`
paper-draft.md:1014           `TIE_AT_SATURATION`
paper-draft.md:1134           `TIE_AT_SATURATION`
```

Both names exist in the repo but neither is a *defined Python symbol*,
which is what the checker resolves against:

- `TIE_AT_SATURATION` appears only as a **string literal** in
  `tools/run_real_ckpt_eval.py` (lines 541, 1125, 1171, 1261) — a
  status value, never a module-level constant.
- `LineageFlowClassifier` is an **upstream** class imported by
  `tools/run_lineageflow_real_ckpt.py:94` from the cloned
  `models.model`, not defined in this repo.

Wave 41/42 introduced the first instances (CR:1020/1247/1273); Wave 43
Agent A and Agent B added four more (README:421, CR:1436/1468,
paper-draft:1134). Two clean fixes, both cheap: promote
`TIE_AT_SATURATION` to a real module-level constant in
`tools/run_real_ckpt_eval.py` and reference it, or add both names to
the checker's denylist the way Wave 39 did for other upstream symbols.

#### Group C — environment / harness, not code (4 failures) — **PRE-EXISTING**

| Test | Cause |
|---|---|
| `test_run_sota_hidream_i1_experiment.py::test_per_round_dumps_subdirs` | child process launches `.venv/bin/python`, which has no `torch`; suite was run under `.venvs/flowmol3_venv`. `ModuleNotFoundError: No module named 'torch'` |
| `test_run_sota_hidream_i1_experiment.py::test_per_round_dumps_n_rounds_one` | same |
| `test_run_rf_cifar_ablation.py::test_eval_rf_cifar_synthetic_smoke` | `ValueError: cannot coerce reference=PosixPath into features` at `adaptive_reflow/eval/run_eval.py:436` |
| `test_run_synthetic_image_eval.py::test_wrapper_without_baseline_dir` | singular-matrix FID path (`LinAlgWarning` at `eval/fid.py:608`) on the tiny synthetic fixture |

The two hidream failures are a hard-coded-interpreter artifact of
running the suite in the sidecar venv rather than `.venv`; they are not
a code regression. The other two are genuine but pre-date Wave 43 and
sit in the tools/eval layer, not in anything Wave 43 touched.

#### Verdict

`pytest_pass = false`. **0 of the 9 failures were introduced by a Wave
43 code change** (Wave 43 changed exactly one source file,
`tools/run_real_ckpt_eval.py`), but **2 of the 9 were introduced by Wave
43's documentation** and 3 more expose a live import cycle that the
wave's own pollution audit did not detect because it scoped its rerun to
`tests/test_adapters/`.

---

## 6. Push status

`todo/PUSH-READY.md` and `docs/audit/wave43-push-prep-summary.md`
record **160 unpushed commits** on `main` spanning Wave 11 → Wave 43.
Per the Wave 33 Agent H protocol no agent pushes; the user runs
`git push origin main` to authorize. The push-prep doc flags one
honest gap for the user to read before authorizing: Tier 3 real-ckpt
framework-vs-baseline had a synthetic metric layer at the time it was
written — §2.1 above is the update, and §3 is the caveat that
survives.

**This agent adds a second flag the user should see before authorizing
the push:** the full `pytest tests/` suite is **not** green at Wave 43
close (9 failed / 4678 passed, §5.2). The `PUSH-READY` verdict was
formed against a `tests/test_adapters/` rerun. Neither the import cycle
nor the doc-symbol failures were introduced by a Wave 43 commit, but
both are in the tree that would be pushed. Whether that gates the push
is the user's call; this doc's recommendation is to land the
Group A fix first, since a cold `import adaptive_reflow.theory` failing
is visible to anyone who clones the repo.

---

## 7. Carried into Wave 44

Ranked by expected effect on the headline claim:

0. **Break the `adaptive_reflow.theory` import cycle** (§5.2 Group A) —
   this is a live defect, not a test-harness quirk: `import
   adaptive_reflow.theory` cold-fails for any consumer who imports it
   first. Apply the `28e3bf9` lazy-`__getattr__` pattern at
   `adaptive_reflow/framework/interfaces.py:63` or defer
   `adaptive_reflow/eval/__init__.py:122`. Highest priority in Wave 44
   and arguably a push blocker.
0b. **Fix the 11 doc-symbol claims** (§5.2 Group B) — promote
   `TIE_AT_SATURATION` to a module-level constant in
   `tools/run_real_ckpt_eval.py` and denylist the upstream
   `LineageFlowClassifier`. Cheap; restores
   `test_check_docs_against_code`.
1. **`observe_token_indices` on `KanziAdapter` + `LineageFlowAdapter`**
   — the single change that can move `framework_wins` off zero at
   Tier 3. < 20 LOC per adapter, but it touches `adaptive_reflow/`,
   so it needs a wave whose scope contract admits framework files.
2. **Three more adapters onto `adaptive_reflow/core/`** — flips MUST-3
   from PARTIAL to PASS. Candidates named in
   `todo/framework-freeze-checklist.md`.
3. **ESM-2-650M mirror** into `.venvs/lineageflow_venv/` (one-time
   ≈ 2.5 GB) — unblocks the LineageFlow half of the real-metric layer.
4. **HMMER / BLAST round-trip** to replace the mod-20 AA proxy with a
   gold-standard `family_validity_rate`.
5. **Kanzi codebook AA mapping** — use
   `dae.codebook.cluster_centers` instead of mod-20 for a
   biophysically grounded decode.
6. **Push** (user-gated).

---

## 8. Cross-references

| Doc | Contents |
|---|---|
| `docs/audit/wave43-metric-layer-fix.md` | `--metric-mode` design, Kanzi per-cell results, honest caveat |
| `docs/audit/wave43-pfam-sidecar-install.md` | Pfam reference provenance + four attempted download paths |
| `docs/audit/wave43-pytest-pollution-fix.md` | Repro for the two Wave 40/41 findings + the wall-clock flake |
| `docs/audit/wave43-must3-finalize.md` | MUST-3 import-graph accounting |
| `docs/audit/wave43-paper-tier3-writeup.md` | Paper §7 file-scope contract + what changed |
| `docs/audit/wave43-push-prep-summary.md` | 160-commit per-wave breakdown |
| `docs/CONSOLIDATED_RESULTS.md` §15.8–§15.10 | Raw Tier 3 evidence |
| `docs/paper-draft.md` §7 | Paper-side Tier 3 digest |
| `todo/framework-freeze-checklist.md` | MUST-1..MUST-5 status |
| `todo/PUSH-READY.md` | Push authorization summary |
