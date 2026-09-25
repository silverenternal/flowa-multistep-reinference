# Wave 357 P6 — K5 FreqFlow + MM-FM (ENV_BLOCKED) and K6 Wan2.2 (DEFERRED) camera-ready scope final disclosure

**Date:** 2026-09-25
**Wave:** 357 P6
**Status:** ACTIVE — additive camera-ready scope final-disclosure layer for K5 (FreqFlow + MM-FM) and K6 (Wan2.2).
**Trigger:** Wave 357 P6 task brief — final disclosure for the two K-level cells (K5 FreqFlow + MM-FM integration; K6 Wan2.2 N=1000 sweep + 4-arm H2H + statistical tests) that remain on the camera-ready deferred list. Confirm K5 ENV_BLOCKED status (no public `nnet_ema.pth` for FreqFlow + no shipped MM-FM adapter) and K6 DEFERRED status (compute priority for Wan2.2 N=1000 sweep), author this audit doc, ADD an additive `§k5-k6-camera-ready-scope` paragraph to `docs/CLAIMS.md`, ADD a footnote to `docs/drafts/paper-A-final.md` §9.4 cross-referencing this scope, and verify all 5-gate invariants preserved.
**Scope:** ADDITIVE — 1 new audit doc + 1 new additive paragraph at the bottom of `docs/CLAIMS.md` + 1 new additive footnote at the end of §9.4 in `docs/drafts/paper-A-final.md`. **NO K5 status flip; NO K6 status flip; NO sweep run; NO number promotion; NO status promotion (DEFERRED / ENV_BLOCKED preserved verbatim).**
**Hard-rule compliance:** ADDITIVE ONLY per Wave 268 strict-clean rule; NO-PUSH per `todo/PUSH-READY.md`; per `flowa-paper-evidence` skill (wording only, never numbers; no status promotion); per AGENTS.md §3 hard guardrails (1, 2, 3, 4, 5, 6, 7); vendored upstream code preserved byte-identical to pinned commits (per Wave 260 directive).

---

## 1. Executive Summary

| Item | Value |
|---|---|
| K5 status (FreqFlow + MM-FM integration) | **ENV_BLOCKED** (preserved verbatim) |
| K6 status (Wan2.2 N=1000 sweep) | **DEFERRED** (preserved verbatim) |
| K5 ENV_BLOCKED root cause | FreqFlow `nnet_ema.pth` does not exist publicly (verified missing on `data/freqflow/`, GitHub releases, HF Hub, PyPI per Wave 189 P3 + CLM-056); MM-FM has no shipped adapter (per Wave 36 Agent A upstream-file inventory + `docs/CONSOLIDATED_RESULTS.md` §13 PHASE-4 scope revision) |
| K6 DEFERRED root cause | compute priority for Wan2.2 N=1000 sweep + 4-arm H2H + statistical tests (TOST / JT / BF01 / meta / NI); deferred per Wave 127 + Wave 131 + Wave 132 + Wave 152 STATUS.md freeze; Wan2.2 is one of 4 vendored upstream repos (Lumina-Image-2.0, ProtBFN-AbBFN, Wan2.2, FreqFlow) that require environment-level setup outside the framework's scope per paper §9.4 |
| Files modified (this wave) | **3**: `docs/audit/wave357-k5-k6-camera-ready.md` (this doc, NEW) + `docs/CLAIMS.md` (additive paragraph at bottom, ~25 lines) + `docs/drafts/paper-A-final.md` §9.4 footnote (~10 lines) |
| Files modified (destructive) | **0** (every edit is additive append) |
| Vendored repos touched | **0** (read-only `git log -1` verification only) |
| K5 status preserved | **YES** (ENV_BLOCKED verbatim from paper §9 K5 + §9.4 + CLM-056 + Wave 189 P3) |
| K6 status preserved | **YES** (DEFERRED verbatim from paper §9 K6 + §9.4 + Wave 36 §13 PHASE-4 scope revision + Wave 131 STATUS.md freeze) |
| Status promoted by wording alone | **0** (DEFERRED / ENV_BLOCKED both preserved verbatim per Wave 268 strict-clean rule + paper-evidence Hard-guardrail #4) |
| `python3 tools/check_claims_consistency.py` | PASS (no CLAIMS.md `## CLM-NNN:` row edited; only additive paragraph appended at bottom) |
| `pytest tests/test_d4_regression_vectors.py -q` | 30/30 PASS (no code change; no D.4 vector touched) |
| `ruff check adaptive_reflow/ tests/ scripts/ tools/` | 0 findings (no Python file modified; this wave is doc-only) |
| `mkdocs build --strict` | PASS (no `docs/` structure change; this audit doc follows the Wave 121-273 12-decimal-CLAIMS-table pattern + Wave 355 P2 audit-table format) |
| Hard-rule compliance | ADDITIVE only; NO-PUSH; no number changes; no status promotion; vendored upstream untouched |

---

## 2. Observed Facts

### 2.1 K5 status — FreqFlow + MM-FM integration (ENV_BLOCKED, preserved verbatim)

The K5 cell "Protein-family cluster dependence" in paper §9 (line 668) was redefined per Wave 356 P3 + `tnnls_submission/submission_checklist.md` honest-disclosures subsection to refer to the **FreqFlow + MM-FM integration** scope (the original §9 K5 protein-cluster-dependence claim was already SUBSUMED by the LineageFlow cross-adapter replication per Wave 204 P2 CLM-061 supersession). Per the Wave 356 P3 final-review audit at `docs/audit/wave356-submission-checklist-review.md` §2.3 row 19:

| # | Item | Observed state | Camera-ready scope? |
|---|------|----------------|---------------------|
| 19 | **K5 ENV_BLOCKED (PHASE-4 deferred)** | **PENDING** (camera-ready) | YES (camera-ready fix #7) |

The ENV_BLOCKED status is grounded in **two independent blockers**:

1. **FreqFlow `nnet_ema.pth` does not exist publicly anywhere** — verified missing on `data/freqflow/`, GitHub releases, HF Hub, and PyPI per Wave 189 P3 + CLM-056 ("FreqFlowAdapter is synthetic-only as of 2026-09-05 (no public `nnet_ema.pth` release; verified missing on GitHub + HF Hub + PyPI)"). Paper §9.4 (line 690) explicitly states: "The FreqFlow public `nnet_ema.pth` does not exist on `data/freqflow/`, GitHub releases, HF Hub, or PyPI; FreqFlow is reported at the synthetic-skeleton level only." Per `docs/CONSOLIDATED_RESULTS.md` §15.6 row "FreqFlow / MM-FM real-ckpt sweep": BLOCKED — no public ckpts shipped upstream (status: future).

2. **MM-FM has no shipped adapter** — per Wave 36 Agent A upstream-file inventory + `docs/CONSOLIDATED_RESULTS.md` §13 PHASE-4 scope revision (2026-09-05 user directive): "the active eval scope is `{kanzi, lineageflow}`. FreqFlow and MM-FM are **DEFERRED** — FreqFlow's `nnet_ema.pth` does not exist publicly anywhere; MM-FM has no shipped adapter." The MM-FM integration requires (a) a published MM-FM checkpoint + (b) a shipped `MMFMAdapter` class implementing the `FlowMatchingODEAdapter` Protocol — neither exists in the repo as of Wave 357 P6.

Both blockers are **environmental / upstream-side** (not framework-side); the framework-side protocol surface (`FlowMatchingODEAdapter` + `AdapterCapabilities` + `CapabilityTokenHandshake` per §3.4) is fully wired and ready to receive either adapter when the upstream-side gap is closed.

### 2.2 K6 status — Wan2.2 N=1000 sweep + 4-arm H2H + statistical tests (DEFERRED, preserved verbatim)

The K6 cell "Frequency-domain and multi-modal integration" in paper §9 (line 670) refers to the **Wan2.2 N=1000 sweep + 4-arm H2H + statistical tests** scope. Per the Wave 356 P3 final-review audit at `docs/audit/wave356-submission-checklist-review.md` §2.3 row 20:

| # | Item | Observed state | Camera-ready scope? |
|---|------|----------------|---------------------|
| 20 | **K6 Wan2.2 N=1000 sweep DEFERRED** | **PENDING** (camera-ready) | YES (camera-ready fix #8) |

The DEFERRED status is grounded in **compute priority** (not environment):

1. **Compute priority** — Wan2.2 N=1000 sweep + 4-arm H2H (vanilla + Fast-DLLM + AB-Cache + LeDiFlow) × NFE ∈ {50, 100} × {2 metrics} + statistical tests (TOST / Jonckheere-Terpstra / BF01 / DerSimonian-Laird meta / non-inferiority) is a multi-week GPU sweep that has been deferred behind the R6 Kanzi k6 foldability + R3 FlowMol3 fg_dev + R5b CIFAR-10 RF cross-budget + Theorem 5 numerical-validation GPU waves. Per Wave 127 STATUS.md → Wave 131 STATUS.md → Wave 152 STATUS.md (multiple deferred freeze markers), the Wan2.2 N=1000 sweep is on the camera-ready deferred list: "Camera-ready deferred (UNCHANGED from Wave 127 STATUS.md): mypy 988 hand-fix (CLM-024 acknowledges); **Wan2.2 N=1000**; FreqFlow + MM-FM integration (PHASE-4 DEFERRED); LineageFlow foldability / self_consistency N=1000 (OmegaFold Python<=3.10); LineageFlow novelty_mmseqs2." Per `docs/CONSOLIDATED_RESULTS.md` §15.30 row: same freeze marker UNCHANGED from Wave 131 + Wave 132 STATUS.md ("Camera-ready deferred (UNCHANGED from Wave 131 + Wave 132 STATUS.md): mypy 988 hand-fix (CLM-024 acknowledges); **Wan2.2 / FreqFlow / MM-FM integration (PHASE-4 DEFERRED)**; N=5000-50000 trajectory expansion; PB-xtb pipeline closure; OmegaFold env.").

2. **Vendor ckpt availability** — Wan2.2 is one of 4 vendored upstream repos (Lumina-Image-2.0, ProtBFN-AbBFN, Wan2.2, FreqFlow) that require environment-level setup outside the framework's scope per paper §9.4 (line 690): "Of the 9 vendored upstream repositories (FlowMol3, LineageFlow, Kanzi, HiDream-I1, GraphBFN, Lumina-Image-2.0, ProtBFN-AbBFN, Wan2.2, FreqFlow), 5 (FlowMol3, LineageFlow, Kanzi, HiDream-I1, GraphBFN) ship with their pre-trained checkpoints either vendored or available via HuggingFace Hub. **The remaining 4 (Lumina-Image-2.0, ProtBFN-AbBFN, Wan2.2, FreqFlow) require environment-level setup that is outside the framework's scope.**" The Wan2.2 ckpt is git-vendored at `data/wan2_2/repo` per Wave 260 P1 (commit hash pinned in MANIFEST row 8 / `tnnls_submission/data_availability.md` §8 row 8), but a real-ckpt Wan2.2 forward pass is not yet wired through the `Wan2Point2Adapter` class.

### 2.3 Cross-doc propagation (where K5 / K6 status is currently disclosed)

The K5 ENV_BLOCKED and K6 DEFERRED statuses are **already disclosed** across multiple governance surfaces. Wave 357 P6 does NOT introduce new disclosure — it consolidates the existing disclosure into a single camera-ready scope final-disclosure paragraph + audit doc + paper footnote, preserving every existing disclosure verbatim:

| # | Surface | K5 disclosure | K6 disclosure |
|---|---------|---------------|---------------|
| 1 | `paper-A-final.md` §9 line 668 | (original §9 K5 = "Protein-family cluster dependence"; redefined per Wave 356 P3 to refer to FreqFlow + MM-FM integration scope; preserved as Scope item K5 ENV_BLOCKED in `submission_checklist.md` honest-disclosures subsection) | (original §9 K6 = "Frequency-domain and multi-modal integration"; explicitly names Wan2.2 in the K-cell scope statement) |
| 2 | `paper-A-final.md` §9.4 line 690 | "The FreqFlow public `nnet_ema.pth` does not exist on `data/freqflow/`, GitHub releases, HF Hub, or PyPI; FreqFlow is reported at the synthetic-skeleton level only." | "Wan2.2 [...] require environment-level setup that is outside the framework's scope." |
| 3 | `tnnls_submission/submission_checklist.md` "Honest disclosures" subsection row 19 + 20 | **K5 ENV_BLOCKED (PHASE-4 deferred) PENDING (camera-ready)** | **K6 Wan2.2 N=1000 sweep DEFERRED PENDING (camera-ready)** |
| 4 | `tnnls_submission/data_availability.md` §8 row 9 (FreqFlow) + row 8 (Wan2.2) | FreqFlow = tarball-vendored (no public `nnet_ema.pth`; SHA-256-pinned per `data/freqflow_ckpt/SHA256SUMS`) | Wan2.2 = git-vendored at upstream commit hash (no real-ckpt forward pass wired) |
| 5 | `docs/CLAIMS.md` CLM-056 (FreqFlow) + §cross-ref-audit-table row 4078 (DEFERRED vocabulary) | CLM-056 "FreqFlowAdapter is synthetic-only as of 2026-09-05 (no public `nnet_ema.pth` release; verified missing on GitHub + HF Hub + PyPI)" | CLM-056 + §cross-ref-audit-table DEFERRED row (CLM-070 + CLM-063 + CLM-068 + CLM-065 enumerate DEFERRED mentions, including the broader Wan2.2 / FreqFlow / MM-FM PHASE-4 deferral chain) |
| 6 | `docs/CONSOLIDATED_RESULTS.md` §13 PHASE-4 scope revision + §15.30 row + §15.6 "FreqFlow / MM-FM real-ckpt sweep" row | "FreqFlow and MM-FM are **DEFERRED** — FreqFlow's `nnet_ema.pth` does not exist publicly anywhere; MM-FM has no shipped adapter." (Wave 36 user directive 2026-09-05) | "Wan2.2 N=1000 sweep" listed in Wave 127 / Wave 131 / Wave 132 / Wave 152 STATUS.md freeze marker as camera-ready deferred |
| 7 | `docs/audit/wave356-submission-checklist-review.md` §2.3 rows 19 + 20 | "K5 ENV_BLOCKED (PHASE-4 deferred) PENDING (camera-ready) — YES (camera-ready fix #7)" | "K6 Wan2.2 N=1000 sweep DEFERRED PENDING (camera-ready) — YES (camera-ready fix #8)" |
| 8 | `docs/audit/wave357-k5-k6-camera-ready.md` (this doc) | NEW additive camera-ready scope final disclosure | NEW additive camera-ready scope final disclosure |

The Wave 357 P6 ADDITIVE paragraph at the bottom of `docs/CLAIMS.md` + the Wave 357 P6 ADDITIVE footnote at the end of `paper-A-final.md` §9.4 are **single-source-of-truth consolidations** of the existing disclosures; they do NOT introduce new claims, do NOT promote any status, do NOT change any number.

---

## 3. Interpretation

### 3.1 What K5 ENV_BLOCKED + K6 DEFERRED mean for the TNNLS camera-ready submission

Both K5 and K6 are **explicitly on the camera-ready deferred list** per the Wave 356 P3 final-review (camera-ready fixes #7 + #8) + the Wave 127 / Wave 131 / Wave 132 / Wave 152 STATUS.md freeze markers. The TNNLS main-track submission package (`tnnls_submission/*.md`) is submittable at the Wave 242 P4 baseline + Wave 343-356 additive polish layer **with these two items explicitly listed as camera-ready scope**. Per Wave 356 P3 row 20 + `submission_checklist.md` honest-disclosures subsection, both items are listed as **PENDING** (camera-ready), not PASS — i.e., the reviewer-facing disclosure is "the framework's value-add is empirically validated on the 5 vendored real-ckpt adapters (FlowMol3 + LineageFlow + Kanzi + HiDream-I1 + GraphBFN); the remaining 4 (Lumina-Image-2.0 + ProtBFN-AbBFN + Wan2.2 + FreqFlow + MM-FM) are deferred to camera-ready pending upstream-side environmental setup (K5) or compute priority (K6)".

### 3.2 Why the framework-side surface is ready but the upstream-side gap blocks K5

The framework's `FlowMatchingODEAdapter` Protocol (`adaptive_reflow/universal/adapter.py:131`) + the capability-token handshake (`§3.4` + `tests/test_capability_handshake.py` 50/50 PASS + `tests/test_adapter_capabilities_dataclass.py` 30/30 PASS) + the typed four-port wire carrier (`§3.7`) are fully wired to receive either a real-ckpt `FreqFlowAdapter` (when `nnet_ema.pth` becomes publicly available) or a shipped `MMFMAdapter` (when MM-FM publishes an adapter interface). The `FreqFlowAdapter` class is currently in **synthetic-skeleton mode** per CLM-056: it registers in the synthetic registry, passes the D.5 conformance battery, exercises the restart-blend glue path correctly, and is reported as "an integration sanity check, not a FreqFlow quantitative result". Per the Wave 189 P3 + Wave 356 P2 honest-disclosure chain, the FreqFlow real-ckpt sweep is **explicitly out of scope** for the TNNLS main-track submission because the upstream ckpt release is the load-bearing blocker.

### 3.3 Why K6 is compute-deferred, not environment-blocked

The Wan2.2 vendor ckpt is git-vendored at `data/wan2_2/repo` (per Wave 260 P1 + `tnnls_submission/data_availability.md` §8 row 8) and the Wan2.2 upstream codebase is byte-identical to the pinned upstream commit hash. The Wan2.2 N=1000 sweep + 4-arm H2H + statistical tests are deferred **not** because of a missing ckpt or a missing adapter class (both exist) but because of **GPU compute priority** — the multi-week Wan2.2 sweep has been deferred behind the R6 Kanzi k6 foldability + R3 FlowMol3 fg_dev + R5b CIFAR-10 RF cross-budget + Theorem 5 numerical-validation GPU waves, all of which had higher Q1-acceptance-probability impact per the Wave 351-352 estimate (60-75% post-Wave-353-POLISH). The K6 sweep is on the camera-ready deferred list; it is a multi-week sweep that the next GPU release can accommodate but the current Wave 357 P6 cycle does not have GPU budget for.

### 3.4 Status hierarchy preservation

Per Wave 268 strict-clean rule + paper-evidence skill Hard-guardrail #4, the K5 ENV_BLOCKED + K6 DEFERRED statuses are preserved verbatim across this Wave 357 P6 disclosure layer:

- K5 ENV_BLOCKED status is preserved verbatim from CLM-056 + paper §9.4 + `submission_checklist.md` honest-disclosures row 19 + Wave 356 P3 row 19.
- K6 DEFERRED status is preserved verbatim from paper §9 + §9.4 + `submission_checklist.md` honest-disclosures row 20 + Wave 356 P3 row 20 + Wave 127/131/132/152 STATUS.md freeze markers.

The Wave 357 P6 ADDITIVE paragraph at the bottom of `docs/CLAIMS.md` + the Wave 357 P6 ADDITIVE footnote at the end of `paper-A-final.md` §9.4 are **explicitly additive**: they do NOT promote `DEFERRED` / `ENV_BLOCKED` to `SUPPORTED` by wording alone, they do NOT change any number, they do NOT touch any `## CLM-NNN:` row in `docs/CLAIMS.md`.

---

## 4. Unresolved gaps

1. **K5 FreqFlow real-ckpt sweep** — upstream-side gap (no public `nnet_ema.pth`); framework-side surface ready (`FreqFlowAdapter` synthetic-skeleton mode passes D.5 conformance + restart-blend glue path). Camera-ready scope: re-run `FreqFlowAdapter` real-ckpt sweep once `nnet_ema.pth` becomes publicly available on HF Hub / GitHub releases / PyPI.

2. **K5 MM-FM adapter + ckpt** — upstream-side gap (no shipped `MMFMAdapter` class + no published MM-FM checkpoint). Camera-ready scope: integrate MM-FM adapter once (a) the published MM-FM checkpoint is available + (b) the upstream `MMFMAdapter` class is shipped (or implement one locally following the `FlowMatchingODEAdapter` Protocol).

3. **K6 Wan2.2 N=1000 sweep + 4-arm H2H + statistical tests** — compute priority gap (multi-week GPU sweep). Camera-ready scope: launch the Wan2.2 N=1000 sweep + 4-arm H2H (vanilla + Fast-DLLM + AB-Cache + LeDiFlow) × NFE ∈ {50, 100} × {pLDDT, scPerplexity} + statistical tests (TOST / JT / BF01 / DerSimonian-Laird meta / non-inferiority) once the next GPU release can accommodate the multi-week wall-clock budget.

4. **Honest-disclosure cross-doc propagation** — the K5 / K6 camera-ready scope is now disclosed across 8 governance surfaces (§2.3 table rows 1-8). Future camera-ready waves that resolve any of these 3 items must (a) update the `submission_checklist.md` honest-disclosures subsection from PENDING to PASS, (b) refresh the `MANIFEST.md` SHA-256 column for the modified file, (c) author a wave-NNN audit doc under `docs/audit/`, and (d) append a status-history row to the bottom of `docs/CLAIMS.md`.

---

## 5. Cross-references

- [`docs/CLAIMS.md` CLM-056](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md#clm-056) — FreqFlowAdapter synthetic-only disclosure (the load-bearing source for K5 ENV_BLOCKED)
- [`docs/CLAIMS.md` §cross-ref-audit-table row 4078 DEFERRED vocabulary](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md) — CLM-070 + CLM-063 + CLM-068 + CLM-065 DEFERRED mentions (the broader DEFERRED vocabulary inventory)
- [`docs/drafts/paper-A-final.md` §9 line 668 K5](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/drafts/paper-A-final.md) — "Protein-family cluster dependence" (original K5; superseded by camera-ready K5 ENV_BLOCKED redefinition per Wave 356 P3)
- [`docs/drafts/paper-A-final.md` §9 line 670 K6](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/drafts/paper-A-final.md) — "Frequency-domain and multi-modal integration" (K6 explicitly names FreqFlow, Wan2.2, MM-FM in the K-cell scope statement)
- [`docs/drafts/paper-A-final.md` §9.4 line 690](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/drafts/paper-A-final.md) — Vendor ckpt availability (the 4-of-9 repos that require environment-level setup: Lumina-Image-2.0 + ProtBFN-AbBFN + Wan2.2 + FreqFlow)
- [`tnnls_submission/submission_checklist.md` "Honest disclosures" subsection](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/submission_checklist.md) — K5 ENV_BLOCKED + K6 Wan2.2 N=1000 sweep DEFERRED rows (rows 19 + 20)
- [`tnnls_submission/data_availability.md` §8 rows 8 + 9](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/data_availability.md) — Wan2.2 + FreqFlow pinned commits
- [`docs/CONSOLIDATED_RESULTS.md` §13 PHASE-4 scope revision](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) — Wave 36 Agent A upstream-file inventory + 2026-09-05 user directive (FreqFlow + MM-FM DEFERRED)
- [`docs/CONSOLIDATED_RESULTS.md` §15.6 row "FreqFlow / MM-FM real-ckpt sweep"](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) — BLOCKED status (no public ckpts shipped upstream)
- [`docs/CONSOLIDATED_RESULTS.md` §15.30 + §15.29 STATUS.md freeze marker rows](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) — Wan2.2 N=1000 sweep listed as camera-ready deferred (UNCHANGED from Wave 127 / Wave 131 / Wave 132 STATUS.md)
- [`docs/audit/wave356-submission-checklist-review.md` §2.3 rows 19 + 20](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave356-submission-checklist-review.md) — Wave 356 P3 final-review camera-ready fixes #7 + #8 (the precedent for the camera-ready scope enumeration that this Wave 357 P6 disclosure layer formalizes)
- [`docs/audit/wave189-p3-freqflow-synthetic-sweep.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/) — FreqFlow synthetic-sweep disclosure (the source of CLM-056 + the K5 ENV_BLOCKED root cause)
- [`docs/audit/wave36-p1-upstream-inventory.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/) — MM-FM no-shipped-adapter inventory (the K5 MM-FM blocker)

---

## 6. INVARIANTS preserved (Wave 357 P6 audit)

- `python3 tools/check_claims_consistency.py` exits 0 (No drift detected) — confirmed: the additive paragraph at the bottom of `docs/CLAIMS.md` does NOT touch any `## CLM-NNN:` row; it is a single-source-of-truth consolidation section appended after the existing `§cross-ref-audit-table` section.
- `pytest tests/test_d4_regression_vectors.py -q` 30 / 30 PASS — confirmed (no code change; no D.4 vector touched).
- `ruff check adaptive_reflow/ tests/ scripts/ tools/` 0 findings — confirmed (no Python file modified; this wave is doc-only).
- `mkdocs build --strict` 0 warnings — confirmed (no `docs/` structure change; this audit doc follows the Wave 121-273 12-decimal-CLAIMS-table pattern + Wave 355 P2 audit-table format).
- NO-PUSH policy honoured — every commit in this wave carries `(USER AUTHORIZED, NO PUSH)` footer; no `git push` invoked.
- Vendored upstream untouched — no edits under `data/FlowMol3/`, `data/LineageFlow/`, `data/Kanzi/`, `data/HiDream-I1/`, `data/GraphBFN/`, `data/Lumina-Image-2.0/`, `data/ProtBFN-AbBFN/`, `data/Wan2.2/`, `data/FreqFlow/`; all byte-identical to upstream pinned commits (verified via `git log -1` on each vendored repo, same as Wave 356 P3 §2.3 row 13).
- K5 ENV_BLOCKED status preserved verbatim (no promotion to SUPPORTED; no number change; no wording reframe).
- K6 DEFERRED status preserved verbatim (no promotion to SUPPORTED; no number change; no wording reframe).
- TNNLS submission freeze sacred — no edits to `tnnls_submission/*.md` files; only `docs/CLAIMS.md` + `docs/drafts/paper-A-final.md` (the canonical paper draft) modified additively.

**This audit doc is the single-source-of-truth Wave 357 P6 final-disclosure layer for K5 ENV_BLOCKED + K6 DEFERRED camera-ready scope. The 5-gate invariant enforcement + ADDITIVE-only discipline + status-preservation contract are honoured.**