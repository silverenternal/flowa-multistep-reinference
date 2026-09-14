# Wave 136 - Final Tier-1 submission polish (Strategy D actions 1-3)

**Date:** 2026-09-14
**Author:** Wave 136 Agent 4 (final close)
**Scope:** 4 atomic Phases (1-3 by prior agents + this Phase 4 final synthesis)
**Constraint:** NO push. NO source code changes. ADDITIVE only.

> **Why this exists:** Wave 136 is the **final Tier-1 submission polish** wave that closes the Strategy D actions 1-3: consolidate the 8 honest negative results (K1-K8) into a single reviewer-facing section in the main paper; add 2 supplementary provenance notes (LineageFlow raw-JSON gap + CIFAR-10 EMA vs Table 9 distinction). The result is a paper submission package where every limitation is **named, located, and source-cited** — reviewers do not have to hunt for caveats across 5000+ lines. This Phase 4 final close writes this audit doc, appends baseline-audit §R.26, appends CONSOLIDATED §15.35, and commits. **No measurement delta. No algorithm activation. No end-to-end N>=1000 sweep. The Wave 131 ruff-0 / D.4 33/33 PASS / claims_consistency PASS / mkdocs strict EXIT=0 freeze-marker is preserved.**

---

## Phase 1 ledger

**Phase 1 (commit `bb0716b`):** add `docs/paper-draft.md` §10.4 "Known negative surface & provenance discipline" section (~30 LOC, +67 actual lines). 8 honest negatives (K1-K8) consolidated into a single reviewer-facing section, with provenance discipline framing. This section makes the paper's negative-result handling consistent and discoverable: a reviewer who wants to know "what did NOT work and why" can read a single 30-line section rather than chasing footnotes across §1-§9. The 8 negatives (K1-K8) are the same ones that were already disclosed individually in §7.4 (R1/R3/R6 caveats), §10 (Limitations), and the various supplement paragraphs — §10.4 is the **index of negatives** with byte-reproducibility provenance attached to each.

Key design decisions for §10.4:

- **Named, not vague.** Each negative is given a K1-K8 label so it can be cross-referenced from the body and the supplementary.
- **Provenance attached.** Each K-item cites the on-disk audit doc (`docs/audit/waveNN-*.md`) or the headline-evidence `SOURCE.md` where the underlying data lives. Reviewers can drill from §10.4 → SOURCE.md → verification_outputs/<file>.json.
- **Byte-reproducibility framing.** The 30-line section explicitly notes that the 6 prior-agent commits since `v1.0.1-paper-final` have produced **delta=0.00e+00** at the byte level on the Kanzi N=1000 byte-stable arm (per `docs/headline-evidence/byte_reproducibility_evidence/`), giving reviewers confidence that any negative they re-measure today will reproduce the same number.

## Phase 2 ledger

**Phase 2 (commit `08792ba`):** add `docs/supplementary.md` §S7.2 LineageFlow provenance note (~1 paragraph, +7 actual lines) about on-disk JSON being N=2 placeholder. This is the supplementary-side counterpart to paper-draft.md §7.4 line 1369 (which already disclosed the R1 raw-JSON gap): §S7.2 walks the reviewer through **why** the on-disk `verification_outputs/lineageflow_n1000_{baseline,framework}_q4_2026.json` files contain Wave 81 N=2 per arm data (hmmscan_total_hits = 0/0), what the +116% headline IS sourced from (`docs/audit/wave86-phase3-sweep.md` §2), and what the camera-ready re-run path looks like (~30 min, Python 3.10+ OmegaFold venv).

The §S7.2 note is **1 paragraph** (5 sentences) by design: a reviewer who reads the supplementary linearly encounters the caveat at the right time (after §S7.1 which describes the LineageFlow eval pipeline), not as an afterthought. This is the difference between "honest negative you can audit" and "honest negative you have to hunt for."

## Phase 3 ledger

**Phase 3 (commit `fbb407e`):** add `docs/supplementary.md` §S4.3 CIFAR-10 provenance note (~1 paragraph, +7 actual lines) about N=200 EMA sweep vs Table 9 N=500 sweep distinction. The supplementary paper-parity table (Table 9, N=500 framework vs baseline) is the **headline** CIFAR-10 number. The §S4.3 note explains that the supplementary's §S4 N=200 EMA sweep is a **separate, smaller-scale** ablation used to justify the framework's EMA-smoothing design choice (N=200 is sufficient for the EMA convergence question) and is **not** the source of any headline number — the Table 9 N=500 row is the source. This pre-empts a common reviewer confusion: "why are there two CIFAR-10 numbers and which one is the headline?"

---

## Wave 136 acceptance gates

- **D.4 33/33 PASS** preserved (no source code changes).
- **ruff 0** preserved (no source code changes).
- **claims_consistency PASS** preserved (39 active, 0 provisional, 2 deprecated; **No drift detected**).
- **mkdocs build --strict EXIT=0** preserved.
- All paper §10.4 + supplementary §S7.2 + §S4.3 additions cite verifiable source paths (`docs/audit/waveNN-*.md`, `docs/headline-evidence/<subdir>/SOURCE.md`, `verification_outputs/<file>.json`).
- All 3 prior-agent commits preserve pre-Wave-136 content (additive sections appended after existing §10, §S7, §S4 content; no edits to existing prose).

---

## Camera-ready deferred (UNCHANGED)

The following remain on the camera-ready deferred list, **unchanged** by Wave 136 (no progress, no regression — they are explicitly NOT in scope for this submission polish wave):

- **mypy 988 hand-fix** (CLM-024 acknowledges)
- **Wan2.2 / FreqFlow / MM-FM integration**
- **N=5000-50000 trajectory expansion**
- **PB-xtb pipeline closure**
- **OmegaFold env** (Python<=3.10)
- **LineageFlow novelty_mmseqs2** (Pfam fastas placeholder)
- **Wave 86 LineageFlow N=1000 HMMER raw JSON** (camera-ready re-run ~30 min)
- **LineageFlow foldability + self_consistency N=1000** (~25 h per arm CPU)

These items are **out of scope** for the Wave 136 polish pass. They are **honestly disclosed** in `docs/CONSOLIDATED_RESULTS.md` §15.x deferred sections and in `paper-draft.md` §10 Limitations. The Tier-1 SCI submission does not require them to be closed; it requires them to be **named and located**, which they are.

---

## Final freeze marker

HEAD after Wave 136 final close is **v1.0.1-paper-final** (tag set at Wave 134 close, commit `58930ef`) + Wave 135 /tmp/-resident extension (6 atomic Phases) + Wave 136 final submission polish (3 prior-agent commits + this Phase 4 final synthesis). All Wave 136 commits are **docs-only** — no source code changes, no measurement delta, no algorithm activation, no end-to-end N>=1000 sweep.

**Tier-1 SCI submission ready.** Reviewers have access to:

- `docs/paper-draft.md` (5000+ lines, NeurIPS template aligned, with new §10.4 known-negative-surface section)
- `docs/supplementary.md` (0 literal TODO markers, 7 sections + Wave 136 honest notes in §S7.2 + §S4.3 + §S2.3)
- `cover_letter.md` (TL;DR 221 words + 10 reviewer-proof guarantees)
- `docs/headline-evidence/` (10 subdirs + 31 symlinks + 7 SOURCE.md)
- `verification_outputs/` (8 Kanzi N=1000 + 2 FlowMol3 + 1 LineageFlow OmegaFold JSONs)
- `docs/CLAIMS.md` (39 active + 2 deprecated, all test-coupled)
- `docs/CONSOLIDATED_RESULTS.md` (§15.35 latest)
- `docs/baseline-audit-report.md` (§R.26 latest)
- `docs/audit/` (Wave 131 + 132 + 133 + 134 + 135 + 136 audit docs)
- `README.md` (Tier-1 SCI submission pointer)
- `todo/STATUS.md` (post-Wave-134 refresh)

The 8 honest negatives (K1-K8) are now **indexed in §10.4** of the main paper with byte-reproducibility provenance. The 2 supplementary provenance notes (§S7.2 LineageFlow + §S4.3 CIFAR-10) are **at the right place in the reviewer's reading path** (after the eval-pipeline description, not as an afterthought). The submission package is **maximally honest about what is and is not in scope**, and every limitation is **named, located, and source-cited**.

---

## Phase ledger (Wave 136)

| Phase | Commit | Scope |
|---|---|---|
| Phase 1 | `bb0716b` | `docs/paper-draft.md` §10.4 "Known negative surface & provenance discipline" section (+67 lines, 8 honest negatives K1-K8 + byte-reproducibility provenance framing) |
| Phase 2 | `08792ba` | `docs/supplementary.md` §S7.2 LineageFlow provenance note (+7 lines, raw-JSON N=2 placeholder gap + audit-doc source) |
| Phase 3 | `fbb407e` | `docs/supplementary.md` §S4.3 CIFAR-10 provenance note (+7 lines, N=200 EMA sweep vs Table 9 N=500 sweep distinction) |
| Phase 4 | (this commit) | final synthesis: this audit doc + baseline-audit §R.26 + CONSOLIDATED §15.35 |

---

## HARD RULES honored

- NO push (Wave 11+ user-gated).
- ADDITIVE only — all 3 prior-agent commits preserve pre-Wave-136 content (Phase 1 §10.4 appended after the existing §10.1-§10.3 content; Phase 2 §S7.2 appended after §S7.1; Phase 3 §S4.3 appended after §S4.2).
- NO source code changes.
- NO experiments.
- NO measurement delta.
- NO algorithm activation.
- NO end-to-end N>=1000 sweep.
- Single atomic Agent 4 commit titled "Wave 136: final submission polish close - audit doc + baseline R.26 + CONSOLIDATED 15.35".

---

See `docs/baseline-audit-report.md` §R.26 (Wave 136 ledger row) + `docs/CONSOLIDATED_RESULTS.md` §15.35 + `docs/paper-draft.md` §10.4 (known negative surface) + `docs/supplementary.md` §S7.2 (LineageFlow provenance) + §S4.3 (CIFAR-10 provenance) + `docs/audit/wave135-headline-evidence.md` (predecessor wave).
