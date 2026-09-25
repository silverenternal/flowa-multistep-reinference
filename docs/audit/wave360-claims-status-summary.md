# Wave 360 P1 — `docs/CLAIMS.md` §status-summary ADDITIVE Section

> **Wave:** 360 P1 (CPU-only documentation append, NO GPU)
> **Date:** 2026-09-25
> **Owning surface:** `docs/CLAIMS.md` (newly appended §status-summary section at row 4158)
> **Adjacent edits:** none (ADDITIVE only — no CLM row modified, no status label changed, no number touched)

---

## 1. Impact (smallest next action first)

`docs/CLAIMS.md` now carries a **top-level status distribution table** that lets a reader
answer "how many of the 84 CLMs are ACTIVE vs PROVISIONAL vs DEPRECATED, and how are they
grouped by topic section?" in one read. The §status-summary section (rows 4158-4190 of
`docs/CLAIMS.md`) preserves the existing §cross-ref-audit-table Wave 355 P2 section (rows
4038-4129) verbatim — the two sections answer complementary questions and co-exist.

**Smallest next action:** none required — this is a single-shot ADDITIVE append. The next
wave (Wave 360 P2 / P3 / etc.) can reference the §status-summary section as the
canonical status-distribution surface without touching it. If the CLM count changes in a
later wave, a follow-up §status-summary refresh audit doc should be opened (Wave 360+).

---

## 2. Observed facts (what the artifacts say)

### 2.1 Status distribution (84 CLMs)

Computed by reading `docs/CLAIMS.md` rows 42-4155 (84 `## CLM-NNN:` headers), parsing the
`Status:` field on each header block, and tallying:

| Status | Count | Provenance |
|---|---|---|
| `ACTIVE` | **82** | 61 parsed (file-literal `- Status: ACTIVE` with all required fields) + 2 extended-label (`CLM-018`, `CLM-022` carry `ACTIVE — INVERTED POST-cd70821 (see note)`) + 15 layout-skipped (`CLM-070..084` place the `- Status: ACTIVE` line before the header) + 3 heading-embedded (`CLM-086`, `CLM-087`, `CLM-088` carry `Status: ACTIVE (Wave 322 …)` inline) + 1 implicit-ACTIVE (`CLM-085`, documented as ACTIVE by the §6 Framework Properties bucket summary at row 3990 + by meta-claim `CLM-088`) |
| `PROVISIONAL` | **0** | No `## CLM-NNN:` row carries a file-literal `- Status: PROVISIONAL` field |
| `DEPRECATED` | **2** | `CLM-016`, `CLM-017` — both parsed-DEPRECATED with supersession markers preserved verbatim |
| **Total** | **84** | CLM-001..CLM-088 (gaps at CLM-035..038 deliberately never assigned) |

Sanity check: 82 + 0 + 2 = 84 = total CLM header count. Matches the §cross-ref-audit-table
Wave 355 P2 row 4049 + row 4067 ("Total `## CLM-NNN:` headers | **84**").

### 2.2 Verifier-driven annotation (recorded separately from top-level `Status:` field)

`tools/check_claims_consistency.py` exits 0 with output:
```
- Active claims: **61**
- Provisional claims: **0**
- Deprecated claims: **2**
- Forced to PROVISIONAL by `Disputed by` citation: CLM-040
```

The "Forced to PROVISIONAL by `Disputed by` citation: CLM-040" annotation is a
verifier-runtime observation, **not** a top-level `Status:` field change. `CLM-040`'s
file-literal `Status:` field remains `ACTIVE`; the verifier's `forced_provisional` count
records the auto-promotion separately. This is consistent with the §cross-ref-audit-table
Wave 355 P2 row 4051 + row 4070 ("61 ACTIVE / 0 PROVISIONAL (file) + 1 forced-PROVISIONAL
(CLM-040) / 2 DEPRECATED").

### 2.3 Per-section breakdown (12 topic buckets)

The 84 CLMs are grouped into 12 topic buckets by CLM number range + title keyword match.
Every bucket's tally preserves the verbatim `Status:` field of each row — no row was
moved between buckets to fit a status narrative.

| Section | CLM IDs | Count | ACTIVE | PROVISIONAL | DEPRECATED |
|---|---|---|---|---|---|
| Paper Theorem / Lemma statements | CLM-001..015 | 15 | 15 | 0 | 0 |
| DEPRECATED historical markers | CLM-016, CLM-017 | 2 | 0 | 0 | 2 |
| Scheduler family + framework contracts | CLM-018..034 | 17 | 17 | 0 | 0 |
| R-cells — early Wave empirical | CLM-039..047 | 9 | 9 | 0 | 0 |
| R-cells — Wave 180s protein + Theorem 1 | CLM-048..055 | 8 | 8 | 0 | 0 |
| K-cells / cross-adapter Theorem 1 | CLM-056, CLM-057, CLM-058 | 3 | 3 | 0 | 0 |
| R-cells — power analysis + statistical tests | CLM-059..064 | 6 | 6 | 0 | 0 |
| R-cells — eval pipeline + audit-grade stats | CLM-065..069 | 5 | 5 | 0 | 0 |
| R-cells — Wave 206+ uplift reversals | CLM-070..075 | 6 | 6 | 0 | 0 |
| Framework-internal governance | CLM-076, CLM-077 | 2 | 2 | 0 | 0 |
| Framework-internal deep-innovation inventory | CLM-078..084 | 7 | 7 | 0 | 0 |
| Path A formal verification lemmas | CLM-085..088 | 4 | 4 | 0 | 0 |
| **TOTAL** | CLM-001..088 | **84** | **82** | **0** | **2** |

### 2.4 Cross-reference to §cross-ref-audit-table Wave 355 P2

The §status-summary section does **not** replace the §cross-ref-audit-table Wave 355 P2
section above (rows 4038-4129). The two sections answer different questions:

| Question | Section | Row range |
|---|---|---|
| "How many CLMs, by top-level status, by section?" | **§status-summary** (this wave) | rows 4158-4190 |
| "Are all CLM-NNN references resolvable? Broken / orphan cross-refs?" | §cross-ref-audit-table Wave 355 P2 | rows 4056-4059 |
| "Are sub-cell verdicts (`SUPPORTED` / `REGRESSES` / etc.) internally consistent?" | §cross-ref-audit-table Wave 355 P2 §D | rows 4076-4115 |
| "Are there near-duplicate / consolidation opportunities?" | §cross-ref-audit-table Wave 355 P2 §E | rows 4117-4128 |
| "What does the §6 Framework Properties bucket summary say?" | §6 Framework Properties bucket summary | rows 3990-3994 |

Mutual consistency: §cross-ref-audit-table row 4049 ("84") matches §status-summary row
4183 ("TOTAL = 84"); §cross-ref-audit-table row 4067 ("61 ACTIVE / 0 PROVISIONAL / 2
DEPRECATED") matches §status-summary's parsed-ACTIVE 61 (the difference of 21 is the 21
layout-skipped headers enumerated in §cross-ref-audit-table row 4053).

### 2.5 Pre-merge gate verification (CPU-only)

```bash
$ python3 tools/check_claims_consistency.py
# Claims consistency report
- Active claims: **61**
- Provisional claims: **0**
- Deprecated claims: **2**
- Forced to PROVISIONAL by `Disputed by` citation: CLM-040
**No drift detected.**

$ python3 -m pytest tests/test_d4_regression_vectors.py -q
30 passed, 3 warnings in 5.99s

$ ruff check adaptive_reflow/ tests/ scripts/ tools/
All checks passed!

$ mkdocs build --strict
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: /home/hugo/codes/flowa-multistep-reinference/site
INFO    -  Documentation built in 25.60 seconds
```

All four pre-merge gates pass with zero findings. The mkdocs strict build produces no
warnings; the third-party "mkdocs-material version announcement" text in the build
output is from a plugin pre-install check, not from the project's own markdown.

---

## 3. Interpretation (what the counts mean)

### 3.1 The 82 / 0 / 2 split reflects "supersede-don't-deprecate" hygiene

The 82 ACTIVE / 0 PROVISIONAL / 2 DEPRECATED split (97.6% / 0.0% / 2.4%) shows that
the project maintains a **narrow DEPRECATED bucket by design** — claims that were
originally wrong (CLM-016's inverted `eps` exponents, CLM-017's
selection_ratio-converges-to-1 hypothesis) were explicitly marked DEPRECATED and replaced
by their successor claims (CLM-022 + CLM-046 respectively), not silently overwritten.
This preserves the audit trail (a reader can trace CLM-016 → CLM-022 as a supersession
pair) while keeping the ACTIVE bucket clean.

### 3.2 The 0 file-literal PROVISIONAL count is the post-Wave 195 P1 + Wave 268 steady state

Every claim is either canonical (ACTIVE), superseded (DEPRECATED), or carries a
verifier-driven `Disputed by` annotation. Only `CLM-040` carries a `Disputed by:`
reference — and that annotation is recorded under `forced_provisional` in the verifier
output, not as a top-level `Status:` field change. This preserves the Wave 195 P1
verdict-precedence + Wave 268 strict-clean rule that no claim status is changed by
verifier runtime alone — the verifier surfaces the contradiction, a human decides.

### 3.3 The Path A bucket went from "1 of 3 ACTIVE" (Wave 311 PARTIAL-APPLY) to "all 4 ACTIVE" (Wave 322 COMPLETE)

The Path A formal verification bucket (CLM-085..088) started with 1 of 3 lemmas ACTIVE
(Lemma 1 at Wave 311) and the other two as PLACEHOLDER rows slated for Wave 312 / Wave
313 insertions. By Wave 322, Lemmas 2 + 3 (CLM-086 + CLM-087) were upgraded in place
to ACTIVE, and the meta-claim CLM-088 was added to bundle all three. No DEPRECATED
rows were generated — the placeholder-to-formal transition was an **additive
evolution**, not a supersession. This is consistent with the §6 Framework Properties
bucket summary at row 3990.

### 3.4 The K-cells bucket mixes PHASE-4 model scope with cross-adapter Theorem 1 analysis

CLM-056 (FreqFlow synthetic-only) is the only pure K-cell claim (K5 = PHASE-4 model
scope). CLM-057 + CLM-058 are cross-adapter Theorem 1 load-bearing analyses spanning
kanzi + lineageflow — they are bucketed under "K-cells" because they reference K-cell
models but their headline is the cross-adapter Theorem 1 finding, not the per-model
status. This grouping is by **topic similarity**, not by **status semantics** — every
row preserves its verbatim `Status: ACTIVE` field.

---

## 4. Unresolved gaps (none introduced by this audit)

- No `## CLM-NNN:` row was edited (`Status:` / `Date:` / `Source:` / `Statement:` /
  `Asserted by:` / `Disputed by:` all unchanged).
- No number was touched.
- No status label was promoted, demoted, or removed.
- The `82 / 0 / 2` tally is an additive accounting of the **current** state — it does
  not change any CLM's status.
- The §status-summary section is ADDITIVE at the bottom of `docs/CLAIMS.md` — does not
  displace any existing content; does not change any cross-reference topology; does not
  change any R-cell / K-cell / framework-internal number.

---

## 5. INVARIANTS preserved (Wave 360 P1 audit)

- `python3 tools/check_claims_consistency.py` exits 0 ("No drift detected") — confirmed.
- `pytest tests/test_d4_regression_vectors.py -q` 30 / 30 PASS — confirmed.
- No `## CLM-NNN:` row was edited.
- No number was touched.
- No status label was promoted.
- ruff 0 across `adaptive_reflow/ tests/ scripts/ tools/` — confirmed.
- mkdocs strict 0 warnings — confirmed.
- vendored NOT touched (no edits under `data/`).
- NO-PUSH policy honoured (commit is local-only; no `git push` performed by the agent).

---

## 6. Cross-doc propagation summary

The §status-summary section propagates the same status distribution to one new surface
(`docs/CLAIMS.md` §status-summary) and zero existing surfaces. Existing surfaces that
already document the CLM status distribution (preserved verbatim):

1. `tools/check_claims_consistency.py` output (`61 ACTIVE / 0 PROVISIONAL / 2 DEPRECATED`)
2. `docs/CLAIMS.md` §cross-ref-audit-table Wave 355 P2 (rows 4038-4129)
3. `docs/CLAIMS.md` §k5-k6-camera-ready-scope Wave 357 P6 (rows 4131-4156)
4. `docs/CLAIMS.md` §6 Framework Properties bucket summary (rows 3990-3994)

No existing surface was modified. The §status-summary section is **only** an additive
appendix that answers "headline status distribution" in one read.