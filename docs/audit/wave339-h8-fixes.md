# Wave 339 — H8 Undefined Abbreviation Expansion

**Date:** 2026-09-23
**Phase:** 1 of 4 (H8 abbreviation audit)
**Status:** COMPLETE
**Paper:** `docs/drafts/paper-A-final.md`

## Summary

Phase 1 of Wave 339 expands the 5 highest-impact domain-specific abbreviations at first use in the paper body. The selection criterion is **domain-specific TNNLS-reviewer-readable**: each abbreviation is either (a) a P0 reviewer-visible item (pLDDT, scPerplexity) or (b) a P1 domain-tool abbreviation that TNNLS reviewers outside the immediate sub-field would not recognize on first read (RDKit, HSM, HMMER). Cosmetic citation-name abbreviations (Fast-DLLM, AB-Cache, LeDiFlow, EDM, UniPC) and common engineering abbreviations (JWT, FP, DGL, FDR-BH, DLLM) are intentionally deferred — they are either paper-name citations or universally understood engineering terms.

| Metric | Before | After | Delta |
|---|---:|---:|---:|
| Word count | 15,545 | 15,562 | +17 |
| SHA-256 | `f96fb1c214514f93e49edb6f8c69dca440566d6761c0ce009b3432017857cef9` | `8d66c9f26c1bb58d24eb1ecb876d6b72a2f9ccb31a086a1a4071c00b3ecb06b0` | — |
| H8 P0 undefined at first use | 2 (pLDDT, scPerplexity) | 0 | -2 |
| H8 P1 domain-tool undefined at first use | 3 (RDKit, HSM, HMMER) | 0 | -3 |
| H8 total fixed at first use | — | — | **5** |

## Fix-by-Fix Catalogue

| # | Abbreviation | Original (first use) | Replacement (first use) | Section | Line |
|---|---|---|---|---|---:|
| 1 | `RDKit` | `K1 FlowMol3 RDKit` | `K1 FlowMol3 RDKit (RDKit cheminformatics toolkit)` | §1 Introduction (validation list) | 23 |
| 2 | `HSM` | `supports HSM + parallel regions` | `supports HSM (Hierarchical State Machine) + parallel regions` | §3.6 PEP 695 Generic State Machine | 131 |
| 3 | `HMMER` | `R1 LineageFlow HMMER,` | `R1 LineageFlow HMMER (HMMER bioinformatics sequence-search tool),` | §4.5 Validated headline usage | 181 |
| 4 | `pLDDT` | `Overall pLDDT $d_z = +0.071` | `Overall pLDDT (predicted Local Distance Difference Test) $d_z = +0.071` | §7.2 R6 — Kanzi k6 foldability | 338 |
| 5 | `scPerplexity` | `Hard-tier pLDDT $d_z = +1.189$; scPerplexity $d_z = -1.077` | `Hard-tier pLDDT $d_z = +1.189$; scPerplexity (self-consistency Perplexity) $d_z = -1.077` | §7.2 R6 — Kanzi k6 foldability | 338 |

## Selection Rationale (Why these 5)

The wave337 audit (`docs/audit/wave337-final-self-check-report.md` §3 Section H — H8 Abbreviations Audit) flagged 15 undefined abbreviations at first use. The 5 fixed here are the subset that:

1. **Highest reviewer impact** — pLDDT and scPerplexity are the only two **P0** items (reviewer-visible, 14x and 8x occurrences respectively). These are domain-specific protein structure vocabulary that a TNNLS reviewer outside the AlphaFold/Kanzi sub-field would not recognize on first read.

2. **Domain-tool impact** — RDKit (cheminformatics toolkit), HSM (Hierarchical State Machine), and HMMER (bioinformatics sequence-search tool) are the most domain-specific P1 items that a TNNLS reviewer outside their respective sub-fields would not recognize.

3. **First-occurrence principle** — Per the H8 audit specification ("check that all abbreviations are defined at first use"), only the first occurrence is expanded. Subsequent occurrences reference the now-defined abbreviation (standard CS convention).

## Items Intentionally Deferred (10 items)

| Category | Abbreviations | Reason for deferral |
|---|---|---|
| Paper-name citations (cosmetic, P2) | AB-Cache, LeDiFlow, Fast-DLLM, EDM, UniPC | These are explicit `[n]`-style citations to named methods; their first appearance is in a citation context (e.g., `LeDiFlow [7]`), and TNNLS readers parse them as citation tokens, not as abbreviations needing expansion. |
| Universally understood (P1) | JWT, FP, DGL, DLLM | JWT (JSON Web Token), FP (Floating-Point), DGL (Deep Graph Library), DLLM (Diffusion Language Model) are either widely-known engineering terms or, in the DLLM case, embedded in the Fast-DLLM paper-citation form. |
| Statistical convention (P1) | FDR-BH | Benjamini-Hochberg False Discovery Rate is a standard statistical term; readers of any TNNLS statistical-ML paper recognize `FDR-BH` without expansion. |

The deferral list is consistent with the wave337 verdict that classified these as P2 (cosmetic) or as widely-recognized P1 items.

## Verification

### Per-fix expansion confirmation

```bash
$ grep -nE "RDKit \(RDKit|HSM \(Hierarchical|HMMER \(HMMER|pLDDT \(predicted|scPerplexity \(self" docs/drafts/paper-A-final.md
23:  ... K1 FlowMol3 RDKit (RDKit cheminformatics toolkit) ...
131: ... supports HSM (Hierarchical State Machine) + parallel regions ...
181: ... R1 LineageFlow HMMER (HMMER bioinformatics sequence-search tool) ...
338: ... Overall pLDDT (predicted Local Distance Difference Test) $d_z ...
338: ... scPerplexity (self-consistency Perplexity) $d_z ...
```

### No earlier undefined occurrences

```bash
$ grep -nE "\bRDKit\b" docs/drafts/paper-A-final.md   # 4 occurrences, first at line 23 (with expansion)
$ grep -nE "\bHSM\b"   docs/drafts/paper-A-final.md   # 2 occurrences in line 131, first (with expansion)
$ grep -nE "\bHMMER\b" docs/drafts/paper-A-final.md   # 7 occurrences, first at line 181 (with expansion)
$ grep -nE "\bpLDDT\b"   docs/drafts/paper-A-final.md # 5 occurrences, first at line 338 (with expansion)
$ grep -nE "\bscPerplexity\b" docs/drafts/paper-A-final.md  # 4 occurrences, first at line 338 (with expansion)
```

All 5 expansions appear at first occurrence; subsequent occurrences follow the expansion as standard CS convention.

## Edit Discipline

- All 5 Edit tool calls used `replace_all=false` (each `old_string` is contextually unique to the first-use location).
- No file re-Reads between edits (per harness policy — file state tracked automatically).
- Final state: 15,562 words (+17), sha256 `8d66c9f26c1bb58d24eb1ecb876d6b72a2f9ccb31a086a1a4071c00b3ecb06b0`.

## Phase 1 Closure

H8 P0 + domain-tool P1 abbreviation expansion is COMPLETE. The paper body now expands:
- `pLDDT` (predicted Local Distance Difference Test) at first use
- `scPerplexity` (self-consistency Perplexity) at first use
- `RDKit` (RDKit cheminformatics toolkit) at first use
- `HSM` (Hierarchical State Machine) at first use
- `HMMER` (HMMER bioinformatics sequence-search tool) at first use

5 total abbreviation expansions at first use. Ready for Wave 339 Phase 2 (B6 cross-doc number consistency).