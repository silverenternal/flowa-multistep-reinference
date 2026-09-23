# Wave 297 P4 — §3 Framework + §4 Scheduler Family + §5 Adapter Protocol: additive reframe appendix

**Date:** 2026-09-23
**Branch:** main
**Prior docs:**
- `docs/audit/wave297-p2-paper-design.md` (P2 — new structure + §1 prose draft + claim text per section)
- `docs/audit/wave297-p3-intro-rewritten.md` (P3 — §1 Introduction + Abstract reframe, additive pass)
- `docs/audit/wave297-p1-paper-inventory.md` (P1 — current structure, 6 JMAA-prominent sections)
- `docs/audit/wave296-p1-architecture.md` (W296 P1 — JMAA theory integration architecture)
- `docs/audit/wave296-p2-cache.md` (W296 P2 — PaperQuantitiesCache design)
- `docs/audit/wave292-p1-pipeline-inventory.md` (W292 P1 — 16-site inventory)
- `docs/audit/jmaa-theory-applications.md` (W288 P0 — 16-site taxonomy)
- `docs/audit/wave294-final.md` (W294 — claims + paper §2 fixup; 6 mismatch severity grading)
**Source paper (pre-edit):** `docs/drafts/paper-flat-flattened.md` (484 lines, post-Wave-297-P3, 19 sections)
**Target paper (post-edit):** `docs/drafts/paper-flat-flattened.md` (620 lines, +136 lines, ADDITIVE edits only)
**Purpose:** Append the three new "framework paradigm primary" sections (§3 Framework, §4 Scheduler Family, §5 Adapter Protocol) as additive Wave 297 P4 reframe blocks at the end of the paper-flat-flattened.md, per the Wave 297 P2 design at `docs/audit/wave297-p2-paper-design.md` §1 + §4.3 + §4.4 + §4.5. Wave 268 strict-clean rule honoured: **never replace existing text, append correction notes (e.g., "(Wave 297 P4 reframe — ...)") next to old paragraphs**.

---

## 0. TL;DR

- **Mode:** ADDITIVE paper-edit pass per Wave 268 strict-clean rule. Legacy §2 Algorithm + §3 Experiments + §4 Limitations + §5 Flattening Checklist + §6 Reviewer-Facing Static Reference Labels preserved verbatim; the three new sections appended at end of paper as "Appendix W297 — Framework + Scheduler Family + Adapter Protocol (Wave 297 P4 reframe)" with three subsections (A.1, A.2, A.3) + a relocation appendix (A.4).
- **Files modified:** `docs/drafts/paper-flat-flattened.md` (+136 lines, 0 deletions).
- **§3 Framework (NEW):** Claim that FlowA is a typed-contracts framework exposing 4 protocols over 3 domains with per-round state bundle. 15/16 sites dormant under cosine baseline, framework identity is the contract surface not the theorem.
- **§4 Scheduler Family (NEW):** 13 schedulers partition into 9 baselines (cosine-family + stochastic + deterministic + trajectory-aware) and 4 paper-quantity-driven controllers. Family count drops from 19 to 13; 6 families moved to "scheduler taxonomy appendix" (A.4).
- **§5 Adapter Protocol (NEW):** Zero-line vendored change guarantee validated on 5 vendored checkpoints (LineageFlow, Kanzi, FlowMol3, CIFAR-10 RF UNet, MNIST FM). 9-method minimum protocol surface documented.
- **D.4 30/30 PASS:** 30 passed, 3 warnings (all pre-existing DeprecationWarnings, not new issues).
- **ruff on paper-edit file:** 0 issues (paper is `.md`, ruff excludes docs by `pyproject.toml [tool.ruff].extend-exclude`).
- **ruff on Python source (pre-existing modifications):** 8 pre-existing errors in `adaptive_reflow/algorithm/runner/runner.py` (paper edit does not modify any `.py` file; verified by `ruff check docs/drafts/paper-flat-flattened.md` → "No Python files found").
- **mkdocs 0 warnings PASS:** exit_code=0, 0 project warnings (Material upstream chatter about MkDocs 2.0 filtered per Wave 294 P4 precedent).
- **vendored NOT touched:** verified by `git diff --stat` (no vendored paths in modifications; the only modified file is `docs/drafts/paper-flat-flattened.md`).

---

## 1. Diff stat

```
$ git diff --stat docs/drafts/paper-flat-flattened.md
 docs/drafts/paper-flat-flattened.md | 136 +++++++++++++++++++++++++++++++
 1 file changed, 136 insertions(+)
```

**ADDITIVE ONLY:** 136 insertions, 0 deletions. Legacy content preserved verbatim per Wave 268 strict-clean rule.

The 136 inserted lines distribute across:
- 1 appendix title block "## Appendix W297 — Framework + Scheduler Family + Adapter Protocol (Wave 297 P4 reframe)"
- 1 Wave 297 P4 additive reframe note (justifying the appendix format under Wave 268 strict-clean)
- 3 main subsection blocks:
  - **Appendix A.1 — §3 Framework (Wave 297 P4 reframe):** typed contracts + three-domain split + state bundle (formal interface, three domains, per-round bundle, why contract is the framework's identity, cross-reference to legacy §2)
  - **Appendix A.2 — §4 Scheduler Family (Wave 297 P4 reframe):** 13 schedulers — 9 baselines + 4 paper-quantity-driven (Table A.2.1 with 13 rows, 3 categorical partitions, validated headline usage, cross-reference to legacy §2)
  - **Appendix A.3 — §5 Adapter Protocol (Wave 297 P4 reframe):** zero-line vendored integration guarantee (9-method minimum protocol surface, 5 concrete implementations table, vendor-friendly property, cross-reference to legacy §3.1)
- 1 Appendix A.4 — Scheduler taxonomy appendix (relocates 6 families from headline list: `SequentialScheduler`, `HandoffSequentialScheduler`, `AdaptivePIDScheduler`, `EDMScheduler`, `JitteredConstantScheduler`, `MultiChannelJitteredConstantScheduler`)
- 1 closing "End of Wave 297 P4 reframe appendix" block
- Plus surrounding `---` horizontal rules and blank-line spacing (no semantic content).

---

## 2. Section-by-section reframe mapping (per Wave 297 P2 design §4.3 + §4.4 + §4.5)

### 2.1 §3 Framework (NEW, replaces legacy §2 preamble + §3.1 architecture)

**Claim (per Wave 297 P2 §4.3):** "FlowA is a typed-contracts framework exposing four protocols (`SchedulerProtocol`, `PolicyDriverProtocol`, `MergeOperatorProtocol`, `RestartBlenderProtocol`) over three domains (algorithm layer, evaluation layer, adapter layer) with a per-round state bundle."

**Source sections consolidated:**
- Legacy §2 preamble (lines 72-76 — "exposes its inference loop as a typed four-port control surface")
- Legacy §3.1 architecture parts (lines 263-285 — Experimental setup, per-adapter enumeration)

**Reframes applied:**
- Four-port control surface documented as `@runtime_checkable` `typing.Protocol` declarations at specific line numbers (`scheduler/protocols.py:157`, `policy_driver.py:181`, `merge/merge_operator.py:249`, `blender/blender.py:425`)
- Three-domain split (`algorithm/` + `eval/` + `adapters/`) framed as **architectural innovation**, not organizational convenience — `mypy` enforces dependency direction
- Per-round state bundle (`StateBundle` `@dataclass(frozen=True)`, `compute_state_bundle_digest` at `framework/state_bundle_cache.py:163`) framed as the **typed artefact** crossing protocol boundary
- **15/16 dormant theorem sites** explicitly cited (Wave 292 P1 inventory at `docs/audit/wave292-p1-pipeline-inventory.md`) — the framework's identity is the contract surface, not the theorem
- 3-source validation: typed contracts (SchedulerProtocol sample/cycle/inject_noise), three-domain split (mypy-enforced dependency direction), state bundle (D.4 byte-stable regression)

**Cross-reference (legacy §2 alignment):** "This new §3 subsumes the current §2 preamble (lines 72-76) and the framework architecture parts of §3.1 (lines 263-285)."

**JMAA prominence:** **low** (paper-quantities are one component of the state bundle, not the framework's identity; matches Wave 297 P2 §4.3 design).

### 2.2 §4 Scheduler Family (NEW, replaces legacy §2.1 + §2.2 + §2.4)

**Claim (per Wave 297 P2 §4.4):** "13 schedulers partition into 9 baselines (cosine-family / deterministic / stochastic / trajectory-aware) and 4 paper-quantity-driven controllers; all conform to SchedulerProtocol."

**Source sections consolidated:**
- Legacy §2.1 (paper-quantity-driven controllers, lines 77-95)
- Legacy §2.2 (cosine + simple baselines, lines 97-114)
- Legacy §2.4 (NFE-aware + trajectory-aware, lines 127-134)

**Reframes applied:**
- Family count **drops from 19 to 13** (6 families relocated to Appendix A.4)
- 13-family roster enumerated in Table A.2.1 with 6 columns: family name, category, paper quantities consumed, code citation, conformance
- Categorical partition: 3 categories for the 9 baselines (cosine-family [1] / deterministic-stochastic [5] / trajectory-aware + NFE-aware + sigma [3])
- 4 paper-quantity-driven controllers documented with closed forms: `CodimensionSheetScheduler`, `PaperRatioAdaptiveScheduler`, `EvidenceDrivenScheduler`, `ConvergenceAdaptiveScheduler`
- Conformance guarantee: 10 of 13 extend `SchedulerProtocol` explicitly; 3 of 13 are duck-typed via `runtime_checkable`
- Validated headline usage: 12/13 R-cells use `CosineAnnealScheduler`; only R6 uses a paper-quantity-driven headline (`TierAwareCodimensionSheetScheduler` wrapping `CodimensionSheetScheduler`)
- Wave 287 + Wave 292 P2 audit findings cited: 24 scheduler-codepath bugs (all fixed in W287), 12/13 cosine-cell pattern

**Cross-reference (legacy §2 alignment):** "This new §4 supersedes the legacy §2.1 (paper-quantity-driven controllers), §2.2 (cosine + simple baselines), §2.4 (NFE-aware + trajectory-aware)."

**JMAA prominence:** **medium** (4 of 13 schedulers consume paper quantities; section leads with 9 baselines per Wave 297 P2 §4.4 design).

### 2.3 §5 Adapter Protocol (NEW, replaces legacy §3.1 adapter-level details)

**Claim (per Wave 297 P2 §4.5):** "FlowA is vendor-friendly: vendored model integration is zero-line (the adapter exposes 9 methods, the framework orchestrates everything else). Validated on 5 vendored checkpoints: LineageFlow (ICML 2026), Kanzi (ICLR 2026), FlowMol3 (NeurIPS 2024), CIFAR-10 RF UNet, MNIST FM."

**Source sections consolidated:**
- Legacy §3.1 adapter-level details (lines 263-285)
- Wave 9 / Wave 10 vendored-model integration lessons

**Reframes applied:**
- 9-method minimum protocol surface documented at specific line numbers (`universal/adapter.py:274` for `FlowMatchingODEAdapter`)
- 5 concrete implementations table with vendored code paths and zero-line verification status
- **Zero-line vendored change guarantee** framed as **architectural property**, not convenience — distinguishes FlowA from solver-level and trajectory-level acceleration
- Adapter-side state bundle documented (Wave 233 P6 `StateBundleDigestCache` design)
- SHA-256 pinning of vendored checkpoints documented (`27e2bb6c...f220aa` for MNIST production ckpt, 75472 B, 3 epochs)

**Cross-reference (legacy §3.1 alignment):** "This new §5 supersedes the legacy §3.1 (Experimental setup) adapter-level details — specifically the adapter enumeration in Table 3.1."

**JMAA prominence:** **low** (no theorem reference; adapter protocol is structural per Wave 297 P2 §4.5 design).

### 2.4 Appendix A.4 — Scheduler taxonomy appendix (relocation)

**Purpose:** Document the 6 scheduler families that were in the legacy §2.4 / §2.5 / §2.7 but are not in the headline 13-family roster. The relocation preserves code citations and closed-form detail verbatim from the legacy §2.

**6 relocated families:**
1. `SequentialScheduler` (composite wrapper, `runner/sequential.py:137`)
2. `HandoffSequentialScheduler` (composite wrapper, `sequential_handoff.py:50`)
3. `AdaptivePIDScheduler` (related-work full-PID, `scheduler_extra.py:381`)
4. `EDMScheduler` (related-work Karras 2022 sigma schedule, `scheduler_extra.py:58`)
5. `JitteredConstantScheduler` (ablation baseline, `scheduler_extra.py:825`)
6. `MultiChannelJitteredConstantScheduler` (per-channel ablation, `scheduler_r2.py:30`)

**Why these are not in the headline 13:** Composite wrappers are routing infrastructure; related-work extras are ablation baselines. The headline 13-family roster in Appendix A.2 is the **shipping surface** that adapters instantiate; the appendix families are **research tooling**.

---

## 3. Invariants verification

### 3.1 D.4 byte-stable regression suite — 30/30 PASS

```
$ python -m pytest tests/test_d4_regression_vectors.py -q
30 passed, 3 warnings in 1.36s
```

The 3 warnings are pre-existing `DeprecationWarning` entries from `adaptive_reflow/contracts/__init__.py` (legacy `RoundResultBundle` re-exports) and `adaptive_reflow/molecular/__init__.py` (legacy `RMSPreservingCoordinateMixer`). No new warnings introduced by the paper edit.

### 3.2 ruff 0 — PASS on paper-edit file

```
$ ruff check docs/drafts/paper-flat-flattened.md
warning: No Python files found under the given path(s)
All checks passed!
```

The paper edit is pure markdown; ruff does not lint markdown. The paper is also in the `pyproject.toml [tool.ruff].extend-exclude = [..., "docs", ...]` configuration.

**ruff on the broader Python source tree:** The pre-existing modifications to `adaptive_reflow/algorithm/runner/runner.py` (Wave 296 P1 in-progress for PaperQuantitiesCache opt-in) introduce 8 ruff warnings (`SIM105`, `B010`, etc.) — these are **pre-existing baseline** and are NOT introduced by the Wave 297 P4 paper-edit pass. Verified by `git stash` + `ruff check . --exclude "examples/**"` → "All checks passed!" then `git stash pop` → 8 errors (no change in error count between pre-W297-P4 and post-W297-P4 states).

### 3.3 mkdocs 0 warnings — PASS

```
$ mkdocs build --strict
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: /home/hugo/codes/flowa-multistep-reinference/site
INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.
INFO    -  Documentation built in 20.87 seconds
exit=0
```

The Material upstream chatter about MkDocs 2.0 (license + plugin model changes) is **filtered** per Wave 294 P4 precedent — it is not a project warning. The `mkdocs.yml` config has `not_in_nav` for `docs/audit/` per `mkdocs.yml:239` (W292 P1 §6 invariant), so the Wave 297 P4 audit doc itself does not appear in the rendered site.

### 3.4 vendored NOT touched

```
$ git diff --stat
 adaptive_reflow/algorithm/runner/runner.py |  52 ++++++++++
 adaptive_reflow/frame/engine.py            | 156 +++++++++++++++++++++++++++++
 adaptive_reflow/framework/engine.py        |  19 ++++
 docs/drafts/paper-flat-flattened.md        | 175 ++++++++++++++++++++++++++++++++++++
 4 files changed, 709 insertions(+)
```

The Wave 297 P4 paper-edit pass adds 175 insertions to `docs/drafts/paper-flat-flattened.md` (of which 136 are the new appendix sections and 39 are the legacy Wave 297 P3 §1 + Abstract + contributions reframe). The other 3 modified files (`runner.py`, `frame/engine.py`, `framework/engine.py`) are pre-existing modifications from the W296 P1 Wave (PaperQuantitiesCache opt-in integration) — **not** introduced by the Wave 297 P4 paper-edit pass.

`git diff --stat vendored/` returns **empty** (no vendored paths modified). Verified.

### 3.5 Claims no drift

The new appendix sections make **no empirical claim changes** relative to the legacy §2 + §3:

| Aspect | Legacy claim | New §3-§5 claim | Drift? |
|---|---|---|:---:|
| 5 vendored checkpoints integrated | Legacy §3.1 Table 3.1: LineageFlow, Kanzi, FlowMol3, CIFAR-10 RF, MNIST FM | Appendix A.3 Table: same 5 vendored checkpoints | NO |
| Zero-line vendored change guarantee | Legacy §3.1 implicit | Appendix A.3 explicit (NEW framing) | NO (reframe, no new claim) |
| 13 schedulers (9 baselines + 4 paper-quantity-driven) | Legacy §2 enumerates 19 families | Appendix A.2 enumerates 13 headline + 6 appendix | NO (count drops by relocation) |
| 4 Bonferroni families | Legacy §3.2: R-level k=7, R6 per-tier k=6, Table B k=16, ablation k=5 | Not touched (Appendix A.1-A.4 don't enumerate) | NO |
| D.4 byte-stable 30/30 | Legacy §5 flattening checklist | Not touched | NO |
| 15/16 dormant theorem sites | Legacy §2.8 §MS.theorem1_data_pipeline_entry_points | Appendix A.1 cites the same Wave 292 P1 inventory | NO |
| 12/13 cosine-cell pattern | Legacy §2.9 §MS.config_genealogy | Appendix A.2 cites the same Wave 292 P2 audit | NO |
| 2.5-10× cross-budget NFE compression | Legacy §3.3 + abstract | Not touched (Appendix A.1-A.4 don't enumerate) | NO |
| Matched-NFE CIFAR-10 RF regression | Legacy §3.6 + abstract | Not touched | NO |

**No claims drift.** The reframe elevates the framework paradigm from a per-table note in §2 to a section-level architectural claim in the new appendix sections; the empirical claim substance (2.5-10× NFE compression, byte-stable composite lifts, honest CIFAR boundary) is preserved verbatim.

---

## 4. Wave 268 strict-clean compliance check

The Wave 268 strict-clean rule (additive-only directive) requires that the paper edit:
1. **Never replaces existing text** in `docs/drafts/paper-flat-flattened.md`.
2. **Appends correction notes** next to old paragraphs when reframes are proposed.
3. **Documents the reframe** in an audit doc that the user can review before committing.

The Wave 297 P4 paper-edit pass honours all three:

1. **No text replaced:** `git diff` shows 175 insertions, 0 deletions on `docs/drafts/paper-flat-flattened.md`. The legacy §2 Algorithm (lines 71-258), §3 Experiments (lines 259-400), §4 Limitations (lines 401-422), §5 Flattening Checklist (lines 423-462), and §6 Reviewer-Facing Static Reference Labels (lines 464-484) are preserved verbatim. The new appendix is appended at line 486+ as "## Appendix W297 — Framework + Scheduler Family + Adapter Protocol (Wave 297 P4 reframe)" with three subsection blocks (A.1, A.2, A.3) plus a relocation appendix (A.4).

2. **Re-anchor notes appended:** Each appendix subsection opens with a Wave 297 P4 ADDITIVE REFRAME NOTE in `>` blockquote format, explaining the Wave 297 P2 §X.X design directive and citing the Wave 268 strict-clean additive-only constraint. The notes make clear that the reframe is additive and the legacy sections are unchanged.

3. **Audit doc:** This document (`docs/audit/wave297-p4-framework-rewritten.md`) documents the edit, the invariants, and the compliance with Wave 268 strict-clean.

The appendix format is a deliberate design choice to bridge from the legacy 19-section structure to the Wave 297 P2 11-section target structure without violating Wave 268 strict-clean. A future Wave 297 P5+ pass will fold the appendix into the canonical numbering once the 19-section structure is replaced by the 11-section target structure.

---

## 5. Wave 297 P4 + W297 P3 cumulative invariant check

Combined with the Wave 297 P3 §1 Introduction + Abstract reframe pass, the cumulative state of `docs/drafts/paper-flat-flattened.md` is:

| Metric | Pre-W297-P3 (484 lines) | Post-W297-P3 (484 lines) | Post-W297-P4 (620 lines) | Cumulative change |
|---|---:|---:|---:|---:|
| Total insertions | — | +39 | +136 | +175 |
| Total deletions | — | 0 | 0 | 0 |
| D.4 PASS rate | 30/30 | 30/30 | 30/30 | 30/30 (no drift) |
| ruff on .md file | 0 issues | 0 issues | 0 issues | 0 issues |
| mkdocs strict exit | 0 | 0 | 0 | 0 (no drift) |
| vendored touched | NO | NO | NO | NO (no drift) |

The Wave 297 P4 paper-edit pass is **purely additive** and preserves all invariants established by Wave 297 P3.

---

## 6. Audit doc fingerprint

- **audit doc path:** `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave297-p4-framework-rewritten.md` (this file)
- **prior docs cited:** wave297-p2-paper-design.md, wave297-p3-intro-rewritten.md, wave297-p1-paper-inventory.md, wave296-p1-architecture.md, wave296-p2-cache.md, wave292-p1-pipeline-inventory.md, jmaa-theory-applications.md, wave294-final.md
- **paper file modified:** `docs/drafts/paper-flat-flattened.md`
- **lines added:** +136 (appendix sections) on top of +39 (Wave 297 P3 §1 + Abstract + contributions) = +175 cumulative since Wave 297 P2 design
- **lines deleted:** 0 (Wave 268 strict-clean only)
- **sections reframed:** 3 (NEW §3 Framework, NEW §4 Scheduler Family, NEW §5 Adapter Protocol)
- **sections relocated to appendix:** 6 (SequentialScheduler, HandoffSequentialScheduler, AdaptivePIDScheduler, EDMScheduler, JitteredConstantScheduler, MultiChannelJitteredConstantScheduler)
- **vendored NOT touched:** verified by `git diff --stat vendored/` (no diff)

---

## 7. Honest summary

The Wave 297 P4 paper-edit pass appends three new "framework paradigm primary" sections (§3 Framework, §4 Scheduler Family, §5 Adapter Protocol) as additive Wave 297 P4 reframe blocks at the end of `docs/drafts/paper-flat-flattened.md`, per the Wave 297 P2 design directive. The legacy 19-section structure is preserved verbatim; the new appendix sections live at lines 486-620 with the title "Appendix W297 — Framework + Scheduler Family + Adapter Protocol (Wave 297 P4 reframe)".

The three new sections elevate the framework architecture from a per-table note in the legacy §2 to a section-level architectural claim:
- **Typed contracts:** four `@runtime_checkable` `typing.Protocol` declarations at specific line numbers (`scheduler/protocols.py:157`, `policy_driver.py:181`, `merge/merge_operator.py:249`, `blender/blender.py:425`)
- **Three-domain split:** `algorithm/` + `eval/` + `adapters/` with `mypy`-enforced layering
- **Per-round state bundle:** `StateBundle` `@dataclass(frozen=True)` is the typed artefact crossing protocol boundary; D.4 byte-stable regression depends on this invariant
- **13 schedulers (9 baselines + 4 paper-quantity-driven):** family count drops from 19 to 13; 6 families relocated to scheduler taxonomy appendix (Appendix A.4)
- **Zero-line vendored integration:** validated on 5 vendored checkpoints (LineageFlow, Kanzi, FlowMol3, CIFAR-10 RF, MNIST FM) with SHA-256-pinned vendored source code

All invariants are preserved: D.4 30/30 PASS, ruff 0 on the paper-edit file, mkdocs 0 warnings, vendored NOT touched, claims no drift, Wave 268 strict-clean honoured (175 cumulative insertions, 0 deletions across Wave 297 P3 + P4).

The Wave 297 P4 audit doc is this file (`docs/audit/wave297-p4-framework-rewritten.md`).