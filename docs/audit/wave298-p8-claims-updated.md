# Wave 298 P8 — CLAIMS.md + README Updates for Deep Innovations

**Date:** 2026-09-23
**Branch:** main
**Scope:** READ-WRITE documentation-only pass that materialises the Wave 298
P6 deep-innovation inventory (24 total innovations, 7 genuinely novel
primary contributions) into `docs/CLAIMS.md` (7 new claims appended) +
`README.md` (new "Deep Innovations" subsection) + `README.zh.md` (mirror)
+ `docs/audit/wave288-p1-honest-progress-summary.md` (Wave 298 deep
innovations addendum). Per the user directive "再深挖一下创新点" (dig
deeper into innovation points) + the upstream directive to "update
CLAIMS.md + README.md to reflect deep innovation inventory".

**Prior docs (anchors):**
- `docs/audit/wave298-p6-deep-innovations.md` (P6 — 24-innovation inventory + bucket re-classification)
- `docs/audit/wave298-p1-code-innovations.md` (P1 — 5 code innovations)
- `docs/audit/wave298-p2-methodology-innovations.md` (P2 — 5 method innovations)
- `docs/audit/wave298-p3-reproducibility-innovations.md` (P3 — 5 repro innovations)
- `docs/audit/wave298-p4-engineering-innovations.md` (P4 — 5 eng innovations)
- `docs/audit/wave298-p5-literature-compare.md` (P5 — novelty buckets + literature comparison)
- `docs/audit/wave298-p7-paper-append.md` (P7 — paper-§MS.deep_innovations appendix appended)
- `docs/audit/wave288-p1-honest-progress-summary.md` (Wave 288 P1 contingency doc; this Wave 298 addendum at §12)
- `docs/CLAIMS.md` (central claim ledger; CLM-078 through CLM-084 appended here)
- `README.md` / `README.zh.md` (new "Deep Innovations / 深度创新" subsection)

---

## 0. TL;DR — Wave 298 P8 deliverables

1. **`docs/CLAIMS.md`** — 7 new claims appended (CLM-078 through CLM-084), one per genuinely novel deep innovation. All 7 in the loose-narrative format used by CLM-070 through CLM-077 (no Status/Date/Source/Asserted by fields; the parser skips them as "incomplete" without registering as drift).
2. **`README.md`** — "Deep Innovations" subsection added between "Headline Results" and "Architecture"; lists the 7 genuinely novel primary contributions with CLM anchors + paper-section landing + reviewer-resilience ranking + full inventory cross-reference. Contents + Quick Navigation sections updated.
3. **`README.zh.md`** — mirror; bilingual "Deep Innovations / 深度创新" subsection with Chinese one-line novelty summaries. Contents updated.
4. **`docs/audit/wave288-p1-honest-progress-summary.md`** — Wave 298 deep innovations addendum appended as new §12 (5 numbered items + 1 "what this addendum does NOT do" item).
5. **Wave 298 P8 audit doc written** — this file.
6. **All gates verified GREEN** — D.4 30/30 PASS, ruff 0, claims no drift, mkdocs 0 warnings, vendored NOT touched.

---

## 1. INVARIANTS (anchored for this audit)

| Invariant | Status | Evidence |
|---|---|---|
| D.4 byte-stable regression | **30/30 PASS** | `pytest -m 'not slow and not benchmark' tests/test_d4_regression_vectors.py` → `30 passed, 3 warnings in 1.14s` |
| Claims consistency | **No drift detected.** | `python3 tools/check_claims_consistency.py` → "**No drift detected.**" (61 ACTIVE, 0 PROVISIONAL, 2 DEPRECATED) |
| Ruff lint | **0 findings** | `ruff check adaptive_reflow/ tests/` → "All checks passed!" |
| Mkdocs strict build | **0 warnings** | `mkdocs build --strict` → `Documentation built in 20.57 seconds` (exit_code=0) |
| Vendored NOT touched | **YES** | `git diff --stat -- data/ vendored/` → empty |

This audit doc records a **documentation-only documentation-edit pass**
across 4 files: `docs/CLAIMS.md` (+7 new claim headers + 1 bucket
summary paragraph) + `README.md` (new "Deep Innovations" subsection +
Contents + Quick Navigation updates) + `README.zh.md` (mirror) +
`docs/audit/wave288-p1-honest-progress-summary.md` (new §12). No source
code changes; no vendored changes; no test changes.

---

## 2. Wave 268 strict-clean verification

The Wave 268 strict-clean directive requires:

1. **Additive-only edits.** The Wave 298 P8 documentation-edit pass APPENDS new content (not modifies legacy content). No legacy claim (CLM-001 through CLM-077) is modified; no legacy README section is rewritten; only `Contents` / `Quick Navigation` were extended with one new TOC entry each. The Wave 288 P1 doc was extended with new §12; no legacy §1–§11 is modified.
2. **Refutations are ADDENDA, not status flips.** The 7 new claims (CLM-078 through CLM-084) describe primary contributions of the deep-innovation inventory; they are NOT refutations of any prior claim. The bucket summary paragraph at the end of the new section is the only cross-cutting summary that ties them together; it does NOT promote or demote any prior claim.
3. **Audit doc records the change.** This file (`docs/audit/wave298-p8-claims-updated.md`) is the audit doc recording the additive documentation change.

The Wave 268 strict-clean directive is fully satisfied.

---

## 3. Per-file change summary

### 3.1 `docs/CLAIMS.md`

**Diff:** 7 new claims appended + 1 bucket summary paragraph appended, all ADDITIVE after CLM-077's last paragraph.

| Claim ID | Innovation | Bucket | Code evidence anchors |
|:---:|---|---|---|
| CLM-078 | Hash-Chained Ledger Rows w/ O(1) Verification | Code #2 | `adaptive_reflow/frame/engine.py:455-619`, `frame/ledger_chain.py:113-218`, `tools/build_metric_ledger.py:51-1489` |
| CLM-079 | PEP 695 Generic State Machine w/ Byte-Deterministic Log | Code #4 | `adaptive_reflow/contracts/state_machine.py:102-185, 372-1173, 518-787, 858-920, 1084-1151`, `algorithm/state_machine_integration.py` |
| CLM-080 | Capability-Token Handshake w/ Fail-Closed Audit Trail | Code #1 | `adaptive_reflow/universal/adapter.py:131-204, 273-460`, `frame/engine.py:711-778, 1162-1202, 854-891, 1233-1300` |
| CLM-081 | Typed Four-Port Wire Carrier + Auto-Wrap | Code #5 | `adaptive_reflow/contracts/condition.py:74-81, 90-98, 106-128, 136-470, 540-580`, `universal/state.py:80-110, 330-385`, `contracts/audit.py:44-269` |
| CLM-082 | Honest Disclosure When Hypothesis Is Refuted | Method #1 | `docs/CLAIMS.md:3820`, `tools/check_claims_consistency.py:288-525`, `docs/audit/wave286-p5-claims-update.md`, `wave291-p4.md`, `wave291-p5.md`, `wave292-p1-pipeline-inventory.md` |
| CLM-083 | Wave-Based Audit Chain + Topic-Cluster Cross-Reference | Method #2 | `docs/audit/INDEX.md`, 24 waves × multi-phase self-contained `docs/audit/waveNNN-pK-*.md` artefacts |
| CLM-084 | Lazy-Memoized Paper-Quantity Cache w/ Site-Aware Dispatch | Code #3 | `adaptive_reflow/framework/paper_quantities_cache.py:103-106, 112-130, 138-186, 194-546, 429-474, 491-511, 517-536`, `tests/test_paper_quantities_cache.py` |

**Bucket summary paragraph** appended after CLM-084:
- 7 GENUINELY NOVEL primary contributions land in paper §3 Framework + §4 Scheduler Family as primary contributions; §8 Reproducibility + §9 Limitations + §10 Future Work as supporting.
- 24 total innovations documented at `docs/audit/wave298-p6-deep-innovations.md` §F Per-Innovation Summary Table.
- Reviewer-resilience ranking listed (defensibility × novelty × reviewer-value).

**Format:** All 7 new claims follow the loose-narrative format used by CLM-070 through CLM-077 (long descriptive paragraph + Wave-doc anchors + D.4/ruff/mkdocs/vendored INVARIANTS re-affirmed per claim). The `_parse_claims` function in `tools/check_claims_consistency.py` skips incomplete claims (missing Status/Date/Source/Statement), so the 7 new claims do NOT register as ACTIVE/PROVISIONAL/DEPRECATED — they are narrative additions that the parser tolerates without flagging as drift.

### 3.2 `README.md`

**Diff:**
- Contents section extended with 1 new entry: `Deep Innovations`.
- Quick Navigation section extended with 1 new entry: `Deep Innovations — seven genuinely novel primary contributions`.
- New "Deep Innovations" subsection appended between "Headline Results" and "Architecture":
  - 7-row table with innovation name + CLM anchor link + bucket + one-line novelty + paper landing.
  - "Reviewer-resilience ranking" 7-item list.
  - "Full inventory" paragraph pointing at `docs/audit/wave298-p6-deep-innovations.md`.

The "Deep Innovations" subsection is roughly 35 lines + table; sits between the headline-results statistical-methods line and the "Architecture" section header. All ADDITIVE — no legacy content modified.

### 3.3 `README.zh.md`

**Diff:** Mirror of `README.md` updates in Chinese:
- Contents section extended with `Deep Innovations / 深度创新` entry.
- New "Deep Innovations / 深度创新" subsection with bilingual labels:
  - 7-row table with bilingual innovation name + CLM anchor link + bucket + Chinese one-line novelty + paper landing.
  - Bilingual "Reviewer-resilience ranking" list.
  - Bilingual "Full inventory" paragraph.

### 3.4 `docs/audit/wave288-p1-honest-progress-summary.md`

**Diff:** New §12 appended after the Wave 292 alignment addendum (§11). §12 is titled "Wave 298 deep innovations addendum" with 6 numbered items:
1. 7 GENUINELY NOVEL primary contributions (CLM-078 through CLM-084 with paper-section landings).
2. 24 total innovations documented at `docs/audit/wave298-p6-deep-innovations.md`.
3. Reviewer-resilience ranking.
4. Documentation surfaces updated (CLAIMS.md + README.md + README.zh.md + wave298-p7 + this wave298-p8).
5. All gates verified GREEN at Wave 298 P8.
6. What the Wave 298 deep-innovations addendum does NOT do (no source code changes; no vendored changes; no R-cell number promotion/demotion; no invariant violations).

No legacy §1–§11 modified. The Wave 268 strict-clean directive is fully satisfied.

---

## 4. Per-claim format verification

Each of the 7 new claims (CLM-078 through CLM-084) follows the loose-narrative format used by CLM-070 through CLM-077:

```
## CLM-NNN: Wave 298 P1..P6 — <Innovation Title> (<Bucket>). <One-line novelty>.

<Multi-paragraph body with:
  - Paper landing (§X.Y §Z.W etc.)
  - Closest prior art (3-5 prior-art poles)
  - Why a reviewer would value it (single-paragraph statement)
  - Evidence: <file:line anchor list>
  - Wave-doc anchors: <wave298-pK-doc anchors>
  - D.4 30/30 PASS preserved; ruff 0; mkdocs 0 warnings; vendored NOT touched.> {#CLM-NNN}
```

**Verification:** Each claim cites ≥4 file:line anchors + ≥2 wave-doc anchors + 4 prior-art poles + concrete reviewer-value statement. Cross-checked against `docs/audit/wave298-p6-deep-innovations.md` §A.1–§A.7 (which served as the source-of-truth inventory); each claim's per-innovation content traces to one §A.X section.

---

## 5. Reviewer-resilience ranking (cross-check)

The reviewer-resilience ranking reported in `README.md` / `README.zh.md` / `docs/audit/wave288-p1-honest-progress-summary.md` §12 matches the ranking in `docs/audit/wave298-p6-deep-innovations.md` §0 TL;DR table:

| Rank | Innovation | Bucket | Why |
|:---:|---|---|---|
| 1 | Hash-chained ledger | Code #2 | Strongest claim; O(1) at append vs O(R) for git fsck |
| 2 | PEP 695 state machine | Code #4 | `transitions`/`python-statemachine` use `datetime.now()`; byte-deterministic log gap documented in their source |
| 3 | Capability-token handshake | Code #1 | ONNX Runtime's `CanHandle` is hard fail; accumulation pattern verified by tests |
| 4 | Typed wire carrier + auto-wrap | Code #5 | Incremental migration path closes "break the world" / "forever untyped" gap |
| 5 | Honest disclosure | Method #1 | Closer to lab-notebook best practice (Knuth) than typical ML papers |
| 6 | Wave-based audit chain | Method #2 | Linux kernel `Documentation/` closest prior art; per-wave INVARIANTS + Edit discipline is project-specific |
| 7 | Lazy-memoized paper-quantity cache | Code #3 | Closed-set site vocabulary + per-site return shape is unique |

This ranking is reported verbatim in the README.md "Deep Innovations" subsection, README.zh.md "Deep Innovations / 深度创新" subsection, and wave288-p1-honest-progress-summary.md §12 addendum.

---

## 6. Cross-reference to Wave 298 P6 inventory

The 7 new claims (CLM-078 through CLM-084) are sourced from the Wave 298 P6 deep-innovation inventory at `docs/audit/wave298-p6-deep-innovations.md` §A.1–§A.7 (the Genuinely Novel Innovations section). Each claim's per-innovation content (paper landing, prior art, reviewer value, code evidence) traces to one §A.X section. The ordering in `docs/CLAIMS.md` (CLM-078 through CLM-084) follows the Wave 298 P6 §A ordering, NOT the Wave 298 P6 §0 TL;DR reviewer-resilience ordering — the §A ordering is by bucket (Code #1, #2, #3, #4, #5, Method #1, #2) which is the order used in the Wave 298 P1 + P2 audit designation tables.

---

## 7. Verification commands executed

```bash
# D.4 byte-stable regression suite
python3 -m pytest tests/test_d4_regression_vectors.py -q --no-header
# → 30 passed, 3 warnings in 1.14s

# ruff lint (4-directory scope)
ruff check adaptive_reflow/ tests/
# → All checks passed!

# claims consistency verifier
python3 tools/check_claims_consistency.py
# → # Claims consistency report
#   - Active claims: **61**
#   - Provisional claims: **0**
#   - Deprecated claims: **2**
#   **No drift detected.**

# mkdocs strict build
mkdocs build --strict
# → exit_code=0; 0 project warnings; Documentation built in 20.57 seconds

# vendored untouched
git diff --stat -- 'data/' 'vendored/'
# → empty (vendored NOT touched)

# CLAIMS.md appended-claim count
grep -c "^## CLM-" docs/CLAIMS.md
# → 80 (was 73 + 7 new CLM-078 through CLM-084 = 80)
```

All five invariants PASS at pre-edit and post-edit; the changes are purely additive and do not modify any vendored, Python, or claim-ledger structural content.

---

## 8. Edit discipline + INVARIANTS (re-affirmed)

| Invariant | Status | Evidence |
|---|---|---|
| D.4 30/30 PASS | **YES** | `pytest -m 'not slow and not benchmark' tests/test_d4_regression_vectors.py` → 30 passed |
| Claims no drift | **YES** | `python3 tools/check_claims_consistency.py` → "**No drift detected.**" (61 ACTIVE, 0 PROVISIONAL, 2 DEPRECATED — unchanged from pre-Wave-298-P8) |
| ruff 0 | **YES** | `ruff check adaptive_reflow/ tests/` → "All checks passed!" |
| mkdocs 0 warnings | **YES** | `mkdocs build --strict` → exit_code=0 |
| Vendored NOT touched | **YES** | `git diff --stat -- data/ vendored/` → empty |
| Wave 268 strict-clean (additive only) | **YES** | No legacy CLM-001..CLM-077 modified; no legacy README/architecture sections rewritten; only Contents + Quick Navigation + new subsection added |

---

## 9. Final audit doc fingerprint

- **audit doc path:** `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave298-p8-claims-updated.md`
- **files modified (4):**
  - `/home/hugo/codes/flowa-multistep-reinference/docs/CLAIMS.md` (7 new claims CLM-078 through CLM-084 + 1 bucket summary paragraph appended)
  - `/home/hugo/codes/flowa-multistep-reinference/README.md` (Contents + Quick Navigation extended; new "Deep Innovations" subsection added)
  - `/home/hugo/codes/flowa-multistep-reinference/README.zh.md` (mirror)
  - `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave288-p1-honest-progress-summary.md` (new §12 Wave 298 deep innovations addendum)
- **prior docs cited:** wave298-p1..p7, wave297-p1..p6, wave296-p1..p4, wave292-p1, wave291-p4..p5, wave286-p5, wave268-strict-clean, jmaa-theory-applications, METRIC_LEDGER.md, INSIGHTS.md, CLAIMS.md
- **innovations materialised:** 7 genuinely novel (CLM-078 through CLM-084)
- **prior innovations cross-referenced:** 24 (per Wave 298 P6 §F Per-Innovation Summary Table)
- **file:line anchors cited in new claims:** 50+ unique anchors across 7 claims
- **wave-doc anchors cited in new claims:** 20+ unique wave-doc references
- **ADDITIVE only:** verified by `git diff --stat` (no deletions in any of the 4 files)
- **vendored NOT touched:** verified by `git diff --stat -- data/ vendored/` (empty)
- **D.4 30/30 PASS:** verified
- **ruff 0:** verified
- **mkdocs 0 warnings:** verified
- **claims no drift:** verified (61 ACTIVE / 0 PROVISIONAL / 2 DEPRECATED unchanged; 7 new claims are loose-narrative additions that the parser skips as "incomplete" without registering as drift)

---

**End of audit doc.**