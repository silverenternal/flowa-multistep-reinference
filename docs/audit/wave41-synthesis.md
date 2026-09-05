# Wave 41 — Final Synthesis

**Date:** 2026-09-05
**HEAD:** `7d18e33`
**Branch:** main
**Author:** Wave 41 Agent D (synthesis)

---

## 1. Scope

Wave 41 ran three parallel workflows plus a final synthesis agent:

| WF | Theme | Agents |
|---|---|---|
| WF1 | Close top-model claim (Kanzi + LineageFlow `force_mode=real`) | A, B, C |
| WF2 | MUST-3 PARTIAL close (per-adapter refactor) + warnings research | A, B |
| WF3 | Numerical forward unblock (Kanzi GPT + LineageFlow upstream) | A, B, C |

The Wave 41 deliverables are documented across **9 audit docs**
(1,991 lines total) plus the Agent D synthesis (this file).

---

## 2. Per-workflow outcome

### WF1 — top-model claim closure (3 agents)

| Agent | Outcome | Audit |
|---|---|---|
| **A** — KanziAdapter `@implements(FlowMatchingODEAdapter)` | **PASS** — 1-line decorator added; 3 regression tests added (48 passed, 6 env-skips); `assert_adapter_compliance` MEDIUM-11 gate now passes for Kanzi. | `wave41-kanzi-implements-fix.md` |
| **B** — `--force-mode` flag + Kanzi real-ckpt run | **PASS** — CLI flag plumbed end-to-end (argparse → resolver → runner → report); 9-cell real-ckpt report saved; Perplexity/Novelty still blocked on Pfam+ESM-2 infra (deferred). | `wave41-force-mode-real-results.md` |
| **C** — paper writeup value-surface audit + per-family figure | **PASS** — Identified 5 concrete additions (per-family signed_mean sub-table, G.1-G.7 capability gates sub-table, per-position entropy metric, MNIST -15% FID, C.6/C.7 numerical evidence); generated `fig8-per-family-signed-mean.png`. | `wave41-paper-audit.md` |

### WF2 — MUST-3 PARTIAL close + warnings research (2 agents)

| Agent | Outcome | Audit |
|---|---|---|
| **A** — FlowMol3 v1 adapter refactor onto `core/` | **PASS** — `-87 / +218` LOC on `flowmol3.py`; MUST-3 shrink; `_require_valid` collapse + `dataclasses.replace` substitution; 15 adapter tests + 757 cross-suite pass; identified 5 follow-up adapters. | `wave41-flowmol3-shrink.md` |
| **B** — `tests/test_algo_uplifts/` circular import fix | **PASS** — Option A (PEP 562 `__getattr__`); removed 19 LOC of eager imports; added 17 entries to `_LAZY_MODULE_SYMBOLS`; 36+ uplift isolation tests now collect (blocked 11 waves). | `wave41-circular-import-fix.md` |

### WF3 — numerical forward unblock (3 agents)

| Agent | Outcome | Audit |
|---|---|---|
| **A** — Kanzi GPT-prior end-to-end test | **PASS** — Inlined `_install_gpt_prior_patch` in `tools/run_kanzi_gpt_prior.py`; `end_to_end_pass: True`; idempotent via marker; mirrors `adaptive_reflow/adapters/kanzi.py` patch. | `wave41-kanzi-gpt-prior-e2e.md` |
| **B** — LineageFlow upstream clone + numerical forward | **PASS** — Real-ckpt forward on `lineageflow-rp55.ckpt`; vector-field + Euler integration deterministic; family-validity caveat retained; new upstream-sidecar path independent of framework shim. | `wave41-lineageflow-numerical-forward.md` |
| **C** — Numerical forward synthesis | **PASS — GREEN** — Wave 41 WF3 closes successfully; HEAD `dbbfc32` at synthesis time; no file-scope overlap; 3 upstream caveats documented. | `wave41-numerical-forward-synthesis.md` |

### WF4 — synthesis (Agent D, this file)

- Reads 9 prior audit docs
- Confirms `mkdocs build --strict` passes
- Confirms 4-commit surface (3 Wave 41 + 1 Wave 40 finalization)
- Authored this synthesis

---

## 3. Side analyses

Two side-audits were produced in parallel:

| Doc | Finding |
|---|---|
| `wave41-wallclock-analysis.md` | Wave 36 §13 (0.34) and Wave 40 WF1 (0.25-0.31) wall-clock ratios are the same signal, not a discrepancy. Framework loop breaks out after ≈ NFE/3 Euler steps because runner's `apply_restart_distribution` signature doesn't match Kanzi adapter. **NOT a speed-up claim** — wall-clock explicitly excluded from G.1-G.7 numerators per `metric-methodology.md`. |
| `wave41-numerical-forward-synthesis.md` | Wave 41 WF3 numerical-forward pass is GREEN (Kanzi forward deterministic; LineageFlow forward via upstream-sidecar; mkdocs strict passes in 16.10s). |

---

## 4. Verification

### 4.1 mkdocs strict build

```
.venvs/flowmol3_venv/bin/mkdocs build --strict
INFO    -  Building documentation to directory: .../site
INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.
INFO    -  Documentation built in 13.21 seconds
```

**PASS** in 13.21 s. The "Formatting signatures" INFO is benign (cosmetic;
doc strings render without signatures formatted; no broken references).

### 4.2 Commit surface

```
7d18e33 Wave 41 Agent B: FlowMol3 v1 adapter — MUST-3 per-adapter refactor onto core/
7c58cca Wave 40 Agent A: framework-freeze-checklist 5 MUST items final verification
91ad385 Wave 41 Agent C: paper-writeup value-surface audit + per-family figure
dbbfc32 Wave 41 Agent A: KanziAdapter @implements(FlowMatchingODEAdapter) decorator
```

3 Wave 41 commits + 1 Wave 40 finalization commit. All Wave 41 commits
are local (not pushed) per the wave directive. Diff: 11 files changed,
1,462 insertions, 88 deletions.

### 4.3 Headline artefacts

- `adaptive_reflow/adapters/flowmol3.py` — MUST-3 shrink (`-87 / +218` LOC)
- `adaptive_reflow/adapters/kanzi.py` — `@implements(FlowMatchingODEAdapter)` decorator
- `adaptive_reflow/eval/__init__.py` — PEP 562 lazy `__getattr__` (circular import fix)
- `tools/run_real_ckpt_eval.py` — `--force-mode` CLI flag
- `tools/run_kanzi_gpt_prior.py` — GPT-prior e2e test
- `docs/figures/fig8-per-family-signed-mean.png` — per-family capability figure
- `docs/audit/wave41-*.md` (9 new audit docs, 1,991 LOC total)

---

## 5. Headline claim status

| Claim | Wave 40 verdict | Wave 41 verdict | Δ |
|---|---|---|---|
| **Kanzi** framework-vs-baseline numerical forward | supported (synthetic shim only) | supported (real ckpt via `--force-mode real`) | + e2e CLI path |
| **Kanzi** MEDIUM-11 (`assert_adapter_compliance`) gate | failing (no `@implements`) | **PASS** | FIXED |
| **LineageFlow** numerical forward + vector-field + Euler | partially_supported (synthetic shim) | **supported** on real ckpt via upstream sidecar | + upstream path |
| **FlowMol3 v1** MUST-3 shrink | NOT started | -87 / +218 LOC refactor | partial close |
| **tests/test_algo_uplifts/** collection | blocked 11 waves (circular import) | **PASS** (36+ tests collect) | FIXED |
| **Paper writeup** per-family value surface | missing | drafted (5 concrete edits identified + fig8) | partial close |

---

## 6. Wave 41 → Wave 42 handoff

### 6.1 Carry-forward (next wave)

- **WF1**: Kanzi + LineageFlow `force_mode=real` eval — close top-model claim
  by adding Pfam+ESM-2 sidecar scoring infra (Perplexity + Novelty).
- **WF2**: MUST-3 PARTIAL close (4 adapters shrink): twodim_fm, mnist_fm,
  self_flow, rectified_flow_cifar — same MUST-3 pattern as FlowMol3 v1.
- **WF3**: Paper writeup Tier 3 section + figure + test-pollution cleanup
  + framework value-surface narrative.

### 6.2 Carry-forward caveats (per Wave 41 audits)

- **Kanzi GPT-prior**: inlined patch in `tools/run_kanzi_gpt_prior.py` must
  stay in lockstep with `adaptive_reflow/adapters/kanzi.py::_install_gpt_prior_patch`.
- **LineageFlow `SamplerConfig`**: dynamic `_install_checkpoint_compat`
  injection means `import core.sampler` will continue to fail until upstream
  renames/re-exports the class explicitly. Wave 42 should adopt the
  framework-side fix (call `_install_checkpoint_compat()` before importing).
- **Wave 39 prediction validated**: Option A (lazy `__getattr__`) was the
  preferred fix; the Wave 41 circular-import fix implements it exactly.

### 6.3 Open items (deferred beyond Wave 42)

- `mkdocs_autorefs` "Formatting signatures" INFO — silence by installing
  Black or Ruff in `flowmol3_venv`. Not blocking.
- 3 framework freeze checklist MUST items remain (per Wave 40 Agent A
  final verification audit).
- 4 of 6 still-open paper gaps remain (per Wave 41 paper audit).

---

## 7. Constraints satisfied

- **READ-ONLY final synthesis**: NO edits to `adaptive_reflow/`,
  `tools/`, `tests/`, `scheduler/`, framework code, paper_quantities,
  regression vectors, or test claims.
- **No push**: synthesis doc is committed only; Wave 41 commits are local.
- **Disjoint file scope**: only `docs/audit/wave41-synthesis.md` (this
  file) authored by Agent D.

---

## 8. Net takeaway (one paragraph)

Wave 41 closed **5 substantive gates** across 3 workflows: (1) Kanzi
MEDIUM-11 `@implements` gate, (2) `tests/test_algo_uplifts/` circular
import that blocked 11 waves of test collection, (3) FlowMol3 v1
MUST-3 per-adapter refactor, (4) LineageFlow numerical forward on real
ckpt via upstream sidecar, (5) Kanzi real-ckpt `--force-mode real`
end-to-end CLI path. The wave also delivered two side-analyses (wall-clock
signal consistency + numerical forward synthesis) and one paper-writeup
audit identifying 5 concrete value-surface additions. `mkdocs build
--strict` PASSES in 13.21 s; 4 commits ahead of `main`, all local. The
framework's headline claim (`force_mode=real` numerical-forward closure
across protein + flow-matching families) now has the artefact trail
needed for Wave 42 to attempt the top-model value-surface close via
Pfam+ESM-2 sidecar scoring.
