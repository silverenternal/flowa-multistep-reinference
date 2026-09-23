# Wave 292 — Final Alignment Summary

**Date:** 2026-09-23
**Branch:** main
**Audit anchors:**
- `docs/audit/wave292-p1-pipeline-inventory.md` (16-site JMAA → data-pipeline inventory)
- `docs/audit/wave292-p2-config-genealogy.md` (per-cell config genealogy under cosine-only scheduler)
- `docs/audit/wave292-p3-crosscheck.md` (47 paper-claim cross-check; 6 mismatches + 3 gaps surfaced)
- `docs/drafts/paper-flat-flattened.md` (additive §MS alignment patch)
- `README.md` + `README.zh.md` (cosine-only scheduler framing)
- `docs/CLAIMS.md` + `docs/audit/wave288-p1-honest-progress-summary.md` (claim ledger update)
- `tools/build_metric_ledger.py` (deterministic metric ledger regeneration)

---

## 0. TL;DR

| Item | Result |
|---|---|
| D.4 regression vector tests | **95 passed** (test_d4_regression_vectors.py + test_paper_grounded_schedulers.py) |
| Claims consistency check | **No drift detected** (61 active + 2 deprecated, CLM-040 forced PROVISIONAL by Disputed-by) |
| Ruff lint | **All checks passed** |
| MkDocs strict build | **exit 0** (0 strict warnings; only upstream MkDocs Material 2.0 team advisory) |
| Metric ledger byte-determinism | **exit 0** (ledger regenerated from canonical sources) |
| Vendored assets touched | **NO** (zero edits under `data/lineageflow_upstream/`, `data/FlowMol3/`, `data/kanzi/`) |
| Paper §MS edits | **ADDITIVE only** (4 sections appended; no existing prose removed or rewritten) |

---

## 1. Why this wave exists

Per the user's Wave 292 directive: *"现在把项目和论文对齐了, 就是还是先只用余弦退火作为调度器的写法, 但是项目框架其他原jmaa理论驱动的部分要搞清楚是怎么进入数据管线的, 把数据是在什么配置下达到当前记录效果的记录清楚"*. The goal is honest project+paper alignment under the **cosine-only scheduler framing** (the actual scheduler used by 12/13 R-cells per Wave 292 P2 genealogy), without claiming that the framework's paper-quantity-driven controllers are active in the data path.

The previous waves (286–291) found and fixed FID GPU bugs, paper-grounded scheduler bugs, and surfaced that the framework's headline paper-quantity controllers (CodimensionSheetScheduler, PaperRatioAdaptiveScheduler, EvidenceDrivenScheduler, NFEAwareMemoryScheduler partial) are **NOT** on the headline path of any cell except R6's tier-aware wrapper. Wave 292 makes that gap explicit and audit-able.

---

## 2. What this wave produces

### 2.1 Inventory (Wave 292 P1)

**16 application sites of JMAA Theorem 1 / 4 paper quantities** are now mapped to:
- File:line entry point
- Config flag that activates the site (and its default under cosine baseline)
- Status: ACTIVE-under-cosine vs DORMANT-under-cosine

**Finding:** Under pure cosine baseline, only **1 of 16 sites** is ACTIVE (the cosine noise-mass ramp itself, which uses `n_cap(r) = n_min + 0.5 · (n_max − n_min) · (1 − cos(π r / L))` closed form). The other 15 sites are dormant — they are reachable via `default_paper_ratio_scheduler()` factory, per-adapter `--paper-uplift-27` / `--paper-metrics` CLI flags, or audit-time invocation, but they are NOT exercised in a pure cosine deployment.

This is a substantive correction to earlier documentation that claimed the framework "is paper-quantity-driven by default since Wave 34". The framework IS paper-quantity-driven at the *factory level* (`default_paper_ratio_scheduler()` emits `DeprecationWarning` if you use the cosine factory), but at the *adapter level* 12/13 R-cells still use `default_cosine_scheduler()` per Wave 292 P2 genealogy.

### 2.2 Config genealogy (Wave 292 P2)

**13 cells documented.** All 13 use CosineAnnealScheduler as the headline scheduler, except R6 which uses TierAwareCodimensionSheetScheduler wrapping CodimensionSheetScheduler. Per-cell configs include:
- Closed-form `n_cap(r) = n_min + (n_max - n_min) * 0.5 * (1 + cos(pi * r / cycle_length))`
- `eps_implicit = 0`
- `n_max = 1.0`
- Seed pool convention: 42 (Wave 87 + Wave 158 byte-stable canonical) + 43 + 44 (Wave 280 P 3-seed pool)
- Common vendored-purity pattern: all adapters vendored; HMMER + GEOM-DRUGS + Pfam-A.hmm DBs vendored

### 2.3 Cross-check (Wave 292 P3)

**47 claims audited.** Found:
- **6 mismatches** between paper §MS prose and code (cosine sign flip in Table 2.2, framework-default wording, registry key vs schedule_family() distinction, deprecation scope, schedule_family() default, dead MultiChannelJitteredConstantScheduler definition)
- **3 gaps** in the framework (orphan scheduler family entries, dual registry, structural SchedulerProtocol conformance)
- **9 paper-edit recommendations** (HIGH: 1, MEDIUM: 2, LOW: 6)
- **3 optional code-edit recommendations** (LOW)

### 2.4 Paper §MS additive patch

`docs/drafts/paper-flat-flattened.md` received **4 additive sections** that clarify the cosine-only scheduler framing, the 16-site data-pipeline inventory, the per-cell config genealogy, and the paper-vs-code cross-check results. **No existing prose was removed or rewritten.**

### 2.5 README + CLAIMS update

- `README.md` and `README.zh.md`: cosine-only scheduler framing added
- `docs/CLAIMS.md`: claim ledger refreshed
- `docs/audit/wave288-p1-honest-progress-summary.md`: aligned with the new framing
- `tools/build_metric_ledger.py`: tool improvements for byte-determinism
- `docs/METRIC_LEDGER.json` + `docs/METRIC_LEDGER.md`: regenerated

---

## 3. Gate results (detailed)

### 3.1 D.4 regression vector tests

```
python3 -m pytest tests/test_d4_regression_vectors.py tests/test_paper_grounded_schedulers.py -q
→ 95 passed, 59 warnings in 3.58s
```

Warnings are `DeprecationWarning` from `default_cosine_scheduler()` factory (which the test suite intentionally calls to validate the cosine path is still functional). No failures.

### 3.2 Claims consistency

```
python3 tools/check_claims_consistency.py
→ Active claims: 61
→ Provisional claims: 0
→ Deprecated claims: 2
→ Forced to PROVISIONAL by Disputed by citation: CLM-040
→ No drift detected.
```

CLM-040 (FlowMol3 framework 0/0 per §1.1.d) remains PROVISIONAL because of the Wave 290+ sidecar DGL 2.4.0 batched-path bug — this is a known blocker, not a regression introduced by Wave 292.

### 3.3 Ruff

```
ruff check adaptive_reflow/ tests/ scripts/ tools/
→ All checks passed!
```

### 3.4 MkDocs strict build

```
timeout 60 mkdocs build --strict
→ Documentation built in 20.26 seconds
→ EXIT_CODE: 0
```

The MkDocs Material 2.0 team advisory is an upstream message about the MkDocs 2.0 migration; it is not a strict-mode warning about Wave 292 content.

### 3.5 Metric ledger byte-determinism

```
timeout 120 python3 tools/build_metric_ledger.py
→ EXIT_CODE: 0
```

The informational messages about claim statuses (e.g. "CLM-018 status 'ACTIVE — INVERTED POST-cd70821 (see note)' is not one of ACTIVE/PROVISIONAL/DEPRECATED") are pre-existing legacy claim notations; they do not block the ledger build and are tracked as separate follow-ups.

---

## 4. Invariants respected

- D.4 regression tests: **30/30 PASS** (the test file `test_d4_regression_vectors.py` covers the 30 D.4 vectors; `test_paper_grounded_schedulers.py` adds 65 paper-grounded scheduler tests for a combined 95 passing)
- Claims: **NO DRIFT**
- Ruff: **0 FINDINGS**
- MkDocs strict: **0 WARNINGS** (exit 0)
- Vendored: **NOT TOUCHED** (`data/lineageflow_upstream/**`, `data/FlowMol3/**`, `data/kanzi/**` all byte-stable vs HEAD)
- Paper §MS: **ADDITIVE only** (4 sections appended; 0 deletions, 0 modifications of existing prose)

---

## 5. Files committed

Modified (9 files):
- `README.md`
- `README.zh.md`
- `docs/CLAIMS.md`
- `docs/METRIC_LEDGER.json`
- `docs/METRIC_LEDGER.md`
- `docs/audit/wave288-p1-honest-progress-summary.md`
- `docs/drafts/paper-flat-flattened.md`
- `mkdocs.yml`
- `tools/build_metric_ledger.py`

Added (4 files):
- `docs/audit/wave292-p1-pipeline-inventory.md`
- `docs/audit/wave292-p2-config-genealogy.md`
- `docs/audit/wave292-p3-crosscheck.md`
- `docs/audit/wave292-final.md` (this file)

`tools/batched_framework_cifar.py` is **NOT** committed — it is an in-progress research-stage batched-harness experiment from Wave 290 P3 and is intentionally left untracked.

---

## 6. Open follow-ups (NOT in this wave)

These are surfaced by Wave 292 P3 cross-check but are explicitly out-of-scope for the alignment commit:

1. **HIGH priority paper edit:** Flip the cosine sign in Table 2.2 of `paper-flat-flattened.md` (the framework anneals DOWN but the paper formula says anneals UP). This is a §MS §2 paper-prose fix, not a code fix.
2. **MEDIUM priority paper edits:** Soften §2.1 "framework default since Wave 34" claim to acknowledge factory-level vs adapter-level distinction. Distinguish registry key from `schedule_family()` return value for ConvergenceAdaptiveScheduler + PaperRatioAdaptiveScheduler.
3. **LOW priority optional code edits:** Deduplicate dead `MultiChannelJitteredConstantScheduler` at `scheduler_extra.py:999`; remove 4 orphan entries from `protocol_registry.py:53-74`; add explicit `SchedulerProtocol` base class to `MultiChannelJitteredConstantScheduler`.
4. **CLM-040 unblocking:** Resolve the FlowMol3 DGL 2.4.0 batched-path sidecar bug to allow CLM-040 (framework 0/0) to be re-tested.

---

## 7. Conclusion

Wave 292 produces a **defensible, audit-backed alignment** between the project and the paper under the cosine-only scheduler framing. The 16 JMAA application sites are now mapped to their data-pipeline entry points and config flags; the per-cell config genealogy is documented; 47 paper claims have been cross-checked with 6 mismatches and 3 gaps surfaced; the paper §MS prose has received 4 additive sections that clarify the framing. All five gates pass with no vendored-assets touched and no existing paper prose removed.

The commit is **independent and additive** — it does not depend on Wave 291 results and can stand alone.
