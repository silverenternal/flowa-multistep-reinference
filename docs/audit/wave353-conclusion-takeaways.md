# Wave 353 P7 — §11.2 key-takeaways bullet list (paper-A-final.md)

**Date:** 2026-09-25
**Wave:** 353 P7
**Status:** READY_TO_COMMIT
**Trigger:** §11 Conclusion had §11.1 Honest verdict paragraph (Wave 350 P5) but no reviewer-scannable bullet list. Per the Wave 353 P7 task brief, §11.2 is added with the **5-bullet key-takeaways** that crystallise: (a) 7 framework + reproducibility innovations, (b) `4 STRONG + 1 TIE + 6 PARTIAL/SUPP` empirical verdict at 11 headline benchmarks, (c) industry-leading reproducibility contract (5-gate + D.4 30/30 + Lean 4 + SHA-256 ledger), (d) camera-ready scope (R3 N=1000, R6 live GPU, K-cells n≥10, Theorem 5 slope-scaling).
**Scope:** Paper-only ADDITIVE §11.2 + 1 ADDITIVE Wave 353 P7 footnote. No code change. No number change. No main-text number change.

---

## 1. Executive Summary

| Item | Value |
|---|---|
| Section location | `docs/drafts/paper-A-final.md` §11.2 (between §11.1 line 745 and `---` separator at line 759) |
| §11.2 content (new) | **5-bullet key-takeaways** organised along Framework / Theory / Empirical / Reproducibility / Camera-ready scope axes |
| §11.2 bullets | 1. Framework architecture (§3) — typed-contracts + 4-port + 7 artefacts; 2. Theoretical foundation (§6) — 2 theorems + 3 lemmas; 3. Empirical evidence (§7) — `4 STRONG + 1 TIE + 6 PARTIAL/SUPP`; 4. Reproducibility (§8) — 5-gate + D.4 30/30 + Lean 4 + SHA-256 ledger; 5. Camera-ready scope (§10) — 4-item deferred list |
| Wave 353 P7 footnote | New ADDITIVE footnote at end of §11.2 documenting the bullet list's cross-reference surface (§3 / §6 / §7 / §8 / §10) and the §9.4 vendor availability note as the R3 RDKit environment unblock |
| Number change | **NONE** — every status label, theorem number, lemma number, cell count, and gate count preserved verbatim from §7.2 / §11.1 |
| Files modified | `docs/drafts/paper-A-final.md` (ADDITIVE §11.2 + Wave 353 P7 footnote) |
| New file | `docs/audit/wave353-conclusion-takeaways.md` (this audit doc) |
| Verification gates | `check_claims_consistency.py` PASS; `pytest tests/test_d4_regression_vectors.py -q` 30/30 PASS; `mkdocs build --strict` PASS |

---

## 2. Observed Facts

### 2.1 §11 status (predecessor wave)

Wave 350 P5 added §11.1 Honest verdict paragraph. After Wave 350 P5, §11 had:
- §11 (top-level) — overview paragraph (~line 741): FlowA as typed-contracts framework, 5 innovations, 5 vendored ckpts, 11 cells, 3 seeds × 4 Bonferroni × D.4, 2.5-10× NFE compression, 3 formal properties, matched-NFE boundary, framework-not-theory verdict.
- §11.1 Honest verdict (~line 743–745) — single paragraph: 11-cell verdict distribution `4 STRONG + 1 TIE + 6 PARTIAL/SUPP`, 4+3 = 7 innovations, industry-leading reproducibility, R6 tier-aware counterfactual ($d_z = +0.2235$), Theorem 5 supplement to Theorem 4, camera-ready scope.

§11 lacked a reviewer-scannable bullet list — the dense prose was thorough but did not surface the **5-axis contribution crystallisation** (Framework / Theory / Empirical / Reproducibility / Camera-ready) that a quick-scan reviewer needs.

### 2.2 §11.2 fill — 5-bullet key-takeaways

Wave 353 P7 adds §11.2 as a 5-bullet list that crystallises the §11.1 paragraph into scan-friendly bullets:

| Bullet | Section anchor | Content |
|---|---|---|
| 1. Framework architecture | §3 | Typed-contracts + 4-port composition + 4 §3.x framework innovations (§3.4–§3.7) + 1 §4.4 lazy-memoized cache = **7 artefacts** |
| 2. Theoretical foundation | §6 | Theorem 4 (§6.5) + Theorem 5 (§6.6) = **2 theorems**; Lemma 1 (§6.2) + Lemma 2 (§6.3) + Lemma 3 (§6.4) = **3 formal lemmas** |
| 3. Empirical evidence | §7 | `4 STRONG + 1 TIE + 6 PARTIAL/SUPP` at **11 headline benchmarks**; honest disclosure of 6 PARTIAL/SUPP cells (2 PARTIAL/single-seed R1/R3 + 4 SUPP-only K1/K4/K5/K7) |
| 4. Reproducibility contract | §8 | 5-gate invariants (§8.1) + D.4 30/30 (§8.2) + Lean 4 sidecar + SHA-256 ledger chain (§8.8); vendored upstream byte-identical (FlowMol3 `77cae22`, LineageFlow `ccef84a`, Kanzi `cfed9cf`) |
| 5. Camera-ready scope | §10 | 4-item deferred list: R3 N=1000 (RDKit env), R6 live GPU (env unblocked, CLM-073/R-019), K-cells n≥10 (compute-deferred, §10.7), Theorem 5 slope-scaling (§10.9 partial close-out) |

Each bullet preserves the **status labels verbatim** from §7.2 / §11.1 (`STRONG` / `TIE` / `PARTIAL/SUPP` / `UNDERPOWERED`); no status promotion by wording, no number change.

### 2.3 Wave 353 P7 ADDITIVE footnote

The §11.2 bullet list ends with the Wave 353 P7 ADDITIVE footnote at line 757:

> *Wave 353 P7 ADDITIVE footnote, no number change.* The §11.2 key-takeaways bullet list crystallises the 7 innovations + `4 STRONG + 1 TIE + 6 PARTIAL/SUPP` verdict + industry-leading reproducibility + camera-ready deferred scope into a reviewer-scannable summary that preserves every status label verbatim from §7.2 / §11.1; the bullet list cross-references §3 / §6 / §7 / §8 / §10 with no prose number change, and the camera-ready scope's parenthetical notes document the Wave 353 P6 vendor availability note (§9.4) as the unblock for R3's RDKit environment.

The footnote follows the established Wave 353 ADDITIVE pattern (P2 §A.2, P3 §3.5, P4 §7.7.1, P5 §3.4/§3.6/§3.7, P6 §9.4) — explicitly states "no number change" and references the cross-reference surface (§3 / §6 / §7 / §8 / §10).

---

## 3. Interpretation

### 3.1 Why §11.2 is ADDITIVE

§11.2 is ADDITIVE for three reasons:
1. **No §11 prose was modified.** The §11 overview paragraph and §11.1 Honest verdict paragraph are preserved verbatim at lines 741 and 743–745.
2. **No status labels were promoted.** The 6 PARTIAL/SUPP cells remain PARTIAL/SUPP, the 4 STRONG cells remain STRONG, the 1 TIE cell remains TIE.
3. **No number change.** Theorem 4 + Theorem 5 = 2; Lemma 1 + Lemma 2 + Lemma 3 = 3; framework innovations 4 + reproducibility innovations 3 = 7; gate counts (5-gate, D.4 30/30) preserved verbatim; R6 $d_z = +0.2235$ preserved verbatim.

The bullet list is a **restructuring**, not a **promotion**: the §11.1 paragraph's content is reformulated into scan-friendly bullets, with each bullet cross-referencing the source section (§3 / §6 / §7 / §8 / §10) so a reviewer can drill into the canonical source.

### 3.2 Camera-ready scope — environmental disclosure

The 5th bullet's parenthetical notes document the Wave 353 P6 vendor availability note (§9.4) as the unblock for R3's RDKit environment. This is the **honest disclosure** pattern from §8.7 (Honest Disclosure Protocol): the deferred item's environment status is named, not glossed over. The four-item camera-ready scope is bounded by §10.5 (R6 live GPU, the load-bearing CLM-073/R-019 deferred item), §10.7 (K-cells supplementary demotion), and §10.9 (Theorem 5 partial close-out via §6.6.1 honest slope-scaling disclosure).

### 3.3 §11.2 vs §11.1 — distinct purposes

| Section | Audience | Purpose |
|---|---|---|
| §11 overview | General reader | Frame the contribution |
| §11.1 Honest verdict | Reviewer + careful reader | Per-cell status + 7-innovation count + R6 + Theorem 5 supplement + camera-ready scope |
| **§11.2 Key takeaways** | **Reviewer scan** | **5-axis crystallisation: Framework / Theory / Empirical / Reproducibility / Camera-ready** |

§11.2 is **not** a substitute for §11.1 — §11.1 retains the per-cell verdict distribution, the R6 $d_z$, the Theorem 5 supplement explanation, and the prose verdict. §11.2 is the **scannable summary** that complements §11.1 for reviewers who scan before reading.

---

## 4. Edit Discipline

**Per Wave 268 strict-clean rule + Wave 353 ADDITIVE pattern:**
- §11.2 + Wave 353 P7 footnote are ADDITIVE only.
- No §11 / §11.1 prose change.
- No §3 / §6 / §7 / §8 / §9 / §10 cross-reference change.
- No `docs/CLAIMS.md` change.
- No `tnnls_submission/` change.
- No code change.
- No vendored upstream modification.

**Vendored scripts NOT modified in this wave:**
- `data/FlowMol3/` (byte-identical, pinned `77cae22`)
- `data/LineageFlow/` (byte-identical, pinned `ccef84a`)
- `data/Kanzi/` (byte-identical, pinned `cfed9cf`)
- `data/HiDream-I1/`, `data/GraphBFN/`, `data/Lumina-Image-2.0/`, `data/ProtBFN-AbBFN/`, `data/Wan2.2/`, `data/FreqFlow/` (byte-identical per Wave 260 directive)

---

## 5. Verification

```bash
# Gate 1: claims consistency (no drift, must exit 0)
$ python3 tools/check_claims_consistency.py
# Active claims: **61**
# Provisional claims: **0**
# Deprecated claims: **2**
# Forced to PROVISIONAL by `Disputed by` citation: CLM-040
# Cross-referenced from at least one governance surface: [61 CLMs listed]
# **No drift detected.**

# Gate 2: D.4 byte-stable regression suite (must be 30/30 PASS)
$ python3 -m pytest tests/test_d4_regression_vectors.py -q
# 30 passed, 3 warnings in 5.02s

# Gate 3: mkdocs build strict (must exit 0)
$ mkdocs build --strict
# INFO    -  Cleaning site directory
# INFO    -  Building documentation to directory: /home/hugo/codes/flowa-multistep-reinference/site
# INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.
# INFO    -  Documentation built in 24.68 seconds
```

All three pre-merge submission gates pass; ruff lint is N/A (no .py touched).

---

## 6. Cross-References

- **Paper section modified:** `docs/drafts/paper-A-final.md` §11.2 (new, ADDITIVE) + Wave 353 P7 ADDITIVE footnote (new)
- **Predecessor audit:** `docs/audit/wave350-p5-honest-verdict.md` (§11.1 paragraph)
- **Wave 353 sibling audits:**
  - `docs/audit/wave353-a1-theorem4-derivation.md` (P1, §A.1 Theorem 4 derivation)
  - `docs/audit/wave353-a2-placeholder-fill.md` (P2, §A.2 placeholder fill)
  - `docs/audit/wave353-ledger-examples.md` (P3, §3.5 hash-chained ledger SHA-256 example)
  - `docs/audit/wave353-h2h-ablation-refs.md` (P4, §7.7.1 Wave 183 figure cross-references)
  - `docs/audit/wave353-pseudocode-blocks.md` (P5, §3.4/§3.6/§3.7 pseudocode blocks)
  - `docs/audit/wave353-limitations-vendor-note.md` (P6, §9.4 vendor ckpt availability note)
- **Camera-ready scope anchors:** §10.5 (R6 live GPU), §10.7 (K-cells supplementary), §10.9 (Theorem 5 slope-scaling)
- **7-innovation ledger:** §3.4 + §3.5 + §3.6 + §3.7 + §4.4 + §8.5 + §8.7 + §8.8
- **5-gate invariant anchor:** §8.1 (D.4 30/30 + claims + ruff + mkdocs + vendored NOT touched)
- **Vendored upstream SHA-256 pins:** `tnnls_submission/data_availability.md` "Unmodified vendored upstream code" table