# R3: CIFAR-10 Rectified Flow v2 FID -44.17% (NFE-averaged framework_improves)

**Headline:** baseline FID = 218.87, framework FID = 122.18, delta = -44.17% (NFE-averaged)
**N:** 250 (framework NFE=2 reaches baseline NFE=5 quality; 2.5x NFE speedup)
**Source-of-truth:** docs/CONSOLIDATED_RESULTS.md §4.3 (v2 row of CIFAR-10 RF ablation)

**Reproducibility:** The v2 sweep was a single-shot CPU run; not archived as a standalone
verification_outputs/ JSON. Re-run from the v2 row CLI in CONSOLIDATED_RESULTS.md §4.3.

---

## Post-Wave-151 P5 audit reconciliation note (2026-09-14)

The prose-text section reference in this SOURCE.md (lines 5, 10) points
to `docs/CONSOLIDATED_RESULTS.md §4.3`. **Wave 151 P5 audit correction:**
the CIFAR-10 RF v2 row (218.87 → 122.18 -44.17%) actually lives at
**§6 line 177** of `docs/CONSOLIDATED_RESULTS.md`, NOT §4.3. §4.3 is the
load-bearing test of the 2D FM ablation. The headline numbers are
correct (218.87 → 122.18, -44.17%) and DO appear at §6 line 177 — only
the section pointer is stale.

Note: this directory (R3) does NOT have a separate `source_audit.md` file
because the SOURCE.md is self-sufficient — it cites the v2 row of
CONSOLIDATED_RESULTS.md by line number (now corrected to §6 line 177
per this note). The Wave 135 Phase 4 (`docs/audit/wave135-headline-evidence.md`)
explicitly documents this design choice.

This note is **ADDITIVE only** — the existing prose references above are
preserved verbatim (no destructive edits to historical SOURCE.md text).
The headline numbers (218.87 → 122.18, -44.17%) are byte-stable across
Waves 135-151.

See `docs/audit/wave151-headline-evidence-audit.md` for the per-R
audit ledger and fix inventory.