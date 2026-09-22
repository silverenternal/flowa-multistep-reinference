# Wave 123: eight-adapter shim audit

**Date:** 2026-09-13  
**Method:** CPU-only source inventory and targeted symbol review  
**Status:** recommendations; no source changes

The plan's inventory counts are stale: the repository has six
`*_upstream_shim.py` files (not eight) and nine `run_sota_*.py` drivers. Kanzi,
LineageFlow and GraphBFN use native paths without a shim. This audit keeps the
eight model rows while recording that distinction explicitly.

## Findings

| Adapter | Surface | Finding | Sev. | Safe next action | Est. |
|---|---|---|---|---|---:|
| Kanzi | native | Latent→coordinate projection remains lossy at the codebook boundary; Wave 99.B records a significant RMSD regression. | P1 | Execute existing inverse-projection bridge plan; retain regression gate. | 80 LOC / 0 GPU |
| LineageFlow | native + glue | Decision metric is binary-saturated on several fixtures, limiting sensitivity. | P2 | Apply the existing BRAI metric calibration proposal; require per-cell CI. | 60 / 0 |
| FlowMol3 v2 | native + shim | Shim is a thin compatibility layer, but chemistry bridge still has partial-fidelity/placeholder paths documented in evaluator output. | P1 | Keep explicit provenance; add a native-vs-framework parity fixture before changing semantics. | 40 / 0 |
| HiDream-I1 | native + two shims | Upstream import and fallback shims are duplicated, but fallback provenance is surfaced in summaries. | P2 | Consolidate only after a shared image shim interface is specified. | 100 / 0 |
| Lumina 2.0 | native + shim | FID can use generated-sample placeholder stats when references are absent; this is prominently marked but not a paper result. | P1 | Require real reference stats for admitted runs; fail closed in paper-metric mode. | 20 / 0 |
| Wan2.2 | native + shim | Harness is intentionally a dependency-gated stub; no weights or executable paper sweep. | P3 | Resolve upstream metadata/weights first; no code refactor now. | external |
| GraphBFN | native | Registry commit/license fields are explicit TODO sentinels while weights are absent; adapter status is unsupported. | P2 | Preserve sentinels and admission gate; fill only after provenance lands. | 10 / 0 |
| ProtBFN/AbBFN | native + shim | Recovery metric uses a documented uniform-reference placeholder without held-out data. | P1 | Add held-out reference before interpreting recovery; keep placeholder marker. | 30 / 0 |

## Cross-adapter patterns

1. Six shims repeat import/fallback plumbing, but their upstream APIs differ;
   extracting a common base now would increase compatibility risk.
2. Placeholder statistics are used by Lumina and ProtBFN/AbBFN. Both record
   provenance; paper-metric admission should require real references.
3. Native adapters exceed 1,500 LOC in seven cases. File size alone is not a
   correctness defect; split work should follow interface tests and D.4 gates.
4. SOTA CLI parser duplication is real across nine drivers; the companion
   P1-C audit found incompatible option schemas, so extraction is deferred.

## Prioritized execution

1. Kanzi inverse-projection bridge (existing plan): highest measured effect,
   no new dependency.
2. Lumina/ProtBFN reference-stat admission checks: prevents misleading paper
   claims and needs no GPU.
3. FlowMol3 parity fixture: verifies bridge semantics before refactoring.
4. LineageFlow metric calibration: depends on the existing power-analysis
   outputs.
5. HiDream shim consolidation: defer until interface design is approved.

## Evidence and verification

Source counts were collected with `wc -l` on 2026-09-13 from the working tree;
all six shim files and eight named native adapter files were present. Existing
paper-metric and Wave 99 audit outputs were consulted; no long-running sweep
was rerun. The audit deliberately makes no claim that placeholder metrics are
paper-valid. Relative links in this document resolve to existing files.

