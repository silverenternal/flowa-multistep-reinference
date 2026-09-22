# Wave 275 P2 — Internal Metric Ledger (single source of truth)

**Branch:** main
**Date:** 2026-09-22
**HEAD commit:** `07ad48e` (Wave 274 P7) + uncommitted P2 ledger + nav fix
**Scope:** Phase 2 of the Wave 261 plan (internal-metric strict traceability).
Builds the **single machine-readable inventory** of every claim, headline
result, statistical output, insight, and engineering gate currently scattered
across `docs/CLAIMS.md` (3878 lines, 73 ACTIVE), `docs/CONSOLIDATED_RESULTS.md`
(8685 lines), `docs/INSIGHTS.md` (1403 lines), `verification_outputs/` (531
dirs), and the 5 engineering gates.

## 1. What shipped

- **`tools/build_metric_ledger.py`** (994 lines) — deterministic, idempotent
  builder. Walks CLAIMS.md, CONSOLIDATED_RESULTS.md, INSIGHTS.md, sampled
  verification_outputs/*, and 5 engineering gates. SHA-256s every source
  artifact path. Emits `docs/METRIC_LEDGER.{md,json}`.
- **`docs/METRIC_LEDGER.md`** — 162 lines, 108 rows. Human-readable ledger.
  Five kinds: CLAIM (73), HEADLINE (7), STATISTICAL (5), INSIGHT (18),
  ENGINEERING_GATE (5).
- **`docs/METRIC_LEDGER.json`** — machine-readable counterpart. 108 entries
  with full Metric dataclass fields.
- **`mkdocs.yml`** — added `Metric ledger` to nav (under "Results & records")
  to silence the strict-mode warning that surfaced during Phase 2.

## 2. Live engineering gates (captured at build)

| Gate | Status | Live value |
|---|---|---|
| G-D.4 | **PASS** | 30 passed, 3 warnings in 1.07s |
| G-RUFF | **FAIL** | 145 errors (1 newly-fixable; 144 deferred per Wave 274 P6) |
| G-MKDOCS | **PASS** | 0 errors (after nav fix) |
| G-CLAIMS_CONSISTENCY | **PASS** | "**No drift detected.**" |
| G-PYTEST | **PASS** | 5082 tests collected in 1.68s |

Phase 2 verify-phase surfaced 5 stale gates at first build (33/33, 0/0,
5155/196, etc. hardcoded) → refactored to `run_engineering_gates()` that
**executes each gate's command at build time** and captures exit-code +
stdout-tail. No snapshots; no stale drift.

## 3. Parse warnings (non-fatal)

- 2 CLAIM rows (CLM-018, CLM-022) carry annotated status
  `ACTIVE — INVERTED POST-cd70821 (see note)` — the annotation is a
  reminder that these claims were inverted at commit `cd70821` and the
  "ACTIVE" prefix preserves the metadata. Status is preserved verbatim.
- 7 CLAIM rows (CLM-070, 071, 072, 073, 074, 075, 076, 077) lacked the
  `- Status:` line entirely. The parser defaults UNKNOWN → ACTIVE per
  Wave 268 strict-clean (these are clearly-active by content; the file
  is just missing the metadata line).

## 4. Schema (Metric dataclass, abbreviated)

```python
@dataclass(frozen=True)
class Metric:
    metric_id: str                 # CLM-001 | HEADLINE-R1 | STAT-TOST-16 | G-D.4
    kind: str                      # CLAIM | HEADLINE | STATISTICAL | INSIGHT | ENGINEERING_GATE
    title: str                     # one-line
    status: str                    # ACTIVE | PROVISIONAL | DEPRECATED | PASS | FAIL | SKIP | UNDERPOWERED | ...
    claim_id: str                  # CLM-NNN
    baseline: str                  # framework baseline value
    framework: str                 # framework value
    delta_abs: str                 # absolute delta
    delta_pct: str                 # percentage delta
    p_value: str                   # p-value
    n: str                         # sample count
    seed: str                      # seed policy
    arm: str                       # which arm (control/framework/baseline)
    nfe: str                       # NFE count
    source_artifact_path: str      # relative path
    source_artifact_sha256: str    # sha256 of the source file (or empty)
    source_line: str               # line number in source
    section_ref: str               # docs/GATES.md + AGENTS.md §4.1
    notes: str                     # live value + verification command + source
```

## 5. Files NOT modified (per Wave 268 strict-clean)

- `docs/CLAIMS.md` — untouched (parse-only).
- `docs/CONSOLIDATED_RESULTS.md` — untouched (parse-only).
- `docs/INSIGHTS.md` — untouched (parse-only).
- `docs/audit/wave*.md` — untouched (Phase 1 inventory + Phase 2 are
  themselves added as new audit docs at
  `docs/audit/wave275-p{1,2}-*.md`).
- All framework / adapter / vendored code — untouched.

## 6. Files modified (Wave 275 P2)

- `tools/build_metric_ledger.py` — new (994 lines, full builder).
- `docs/METRIC_LEDGER.md` — new (162 lines, 108 rows).
- `docs/METRIC_LEDGER.json` — new (machine-readable ledger).
- `mkdocs.yml` — added "Metric ledger (single source of truth)" nav entry.
- `docs/audit/wave275-p1-state-inventory.md` — created by Phase 1 (already
  in tree from `wigiu1y7l`).
- `docs/audit/wave275-p2-metric-ledger.md` — this audit doc.

## 7. Determinism guarantee

- `python3 tools/build_metric_ledger.py` run twice on the same commit
  produces byte-identical `docs/METRIC_LEDGER.{md,json}` files.
- Verified by Phase 2 verify-phase `deterministicReRun: true`.

## 8. Verification spot-checks

- **Claim spot-checks** (3/3 statementMatch): CLM-016, CLM-052, CLM-076.
- **Headline spot-checks** (2/2 valuesMatch): R3, R6.
- **sha256 coverage** on rows with file-source: 100% (the only row
  without sha is G-PYTEST whose source is a directory, not a file).

## 9. Recommended next phase

Wave 275 P3 (Flattening + Governance):
- Apply Option C (archive 278 historical wave*.md → docs/ARCHIVE/audit-by-wave/).
- Apply Option B (rename 198 wave-prefixed active files → topic clusters:
  cifar/*, kanzi/*, flowmol3/*, lineageflow/*, governance/*).
- Remove mkdocs.yml `audit/wave*.md` glob (line 278).
- Trace every consumer (mkdocs/CLAIMS/CONSOLIDATED/README/cover_letter/
  supplementary/CHANGELOG/ROADMAP/AGENTS.md) of the 198 active files.
- Top-level INDEX per topic cluster with 1-paragraph summary per file.
- Final result: a reviewer can answer "what does the framework claim"
  from `docs/METRIC_LEDGER.md` (single doc, 162 lines) plus
  `docs/audit/<topic>/INDEX.md` (one per topic cluster), without ever
  needing to read a `waveNNN-` filename.