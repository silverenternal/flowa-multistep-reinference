# Wave 251 P3 — Final Pre-Push Verification

**Date:** 2026-09-22
**Branch:** main (HEAD `cee777b`)
**Scope:** Wave 251 P3 — final 4-gate pre-push verification after Wave 251
P1 (CLM-053 NOT_OK decision doc) + Wave 251 P2 (status check on 3
confirmation items). No paper edits in Wave 251.

---

## 1. Verification gate results

| # | Gate | Expected | Observed | Status |
|---|------|----------|----------|--------|
| 1 | D.4 byte-stable regression suite | 30/30 PASS | 30 passed, 3 warnings in 5.62s | **PASS** |
| 2 | mkdocs strict build | 0 warnings | "Documentation built in 24.77 seconds" (no warnings) | **PASS** |
| 3 | claims_consistency no drift | No drift detected | "**No drift detected.**" | **PASS** |
| 4 | Abstract word count | <= 250 words | 183 words | **PASS** |
| 5 | Unpushed commits | informational | 130 commits ahead of origin/main | informational |

### 1.1 Verification commands run

```bash
$ timeout 30 .venvs/lineageflow_venv/bin/python -m pytest tests/test_d4_regression_vectors.py -q --no-header 2>&1 | tail -3
30 passed, 3 warnings in 5.62s

$ timeout 30 mkdocs build --strict 2>&1 | tail -5
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: /home/hugo/codes/flowa-multistep-reinference/site
INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.
INFO    -  Documentation built in 24.77 seconds
# (no warnings emitted; exit=0)

$ python3 tools/check_claims_consistency.py 2>&1 | tail -3
**No drift detected.**

$ awk '/^## Abstract/,/^---$/' docs/paper-final-neurips.md | sed '1d; /^---$/d' | wc -w
183

$ git log --oneline @{u}.. 2>&1 | wc -l
130
```

---

## 2. Diff from Wave 250 P6

| # | Gate | Wave 250 P6 | Wave 251 P3 | Delta |
|---|------|-------------|-------------|-------|
| 1 | D.4 PASS | 30/30 | 30/30 | unchanged |
| 2 | mkdocs warnings | 0 | 0 | unchanged |
| 3 | claims drift | none | none | unchanged |
| 4 | Abstract words | 225 | 183 | -42 (Wave 251 contains no paper edits; the abstract word count delta reflects the verification reading the canonical `docs/paper-final-neurips.md` source which is the current authoritative abstract, vs Wave 250 P6 reading a draft mirror) |
| 5 | Unpushed commits | 127 | 130 | +3 (Wave 251 P1 + P2 + this P3 verification doc) |

### 2.1 Why abstract dropped from 225 -> 183

Wave 250 P6 read `docs/drafts/paper-flattened-draft.md` (225 words, the
working draft that Wave 250 P1-P5 was appending CLMs into). Wave 251 P3
reads `docs/paper-final-neurips.md` (183 words, the canonical paper). Both
are <= 250, both PASS. The 225-word draft has not been promoted to
canonical since the Wave 250 P5 PROVISIONAL flag — the canonical paper is
the safer measurement for the pre-push gate.

---

## 3. Wave 251 deltas (informational)

| Commit | Subject |
|--------|---------|
| `836f35b` | Wave 251 P1: formal decision doc on CLM-053 NOT_OK to add (per Wave 249 P1 audit) |
| `cee777b` | Wave 251 P2: status check on 3 confirmation items + Wave 246/250/247 snapshot |
| (P3) | this verification doc |

Wave 251 contains NO paper edits. It is a confirmation + status wave
(CLM-053 NOT_OK formalization + 3 confirmation items status snapshot).
Wave 247 R5b P2-P5 + FlowMol3 seed-44 retry v3 remain in-flight (background).

---

## 4. CLM-053 NOT_OK decision (Wave 251 P1)

Per Wave 251 P1 doc, CLM-053 (4-baseline 全 WIN) was formally marked
NOT_OK to add to the paper. Rationale:

- Wave 249 P1 audit showed the 4-baseline claim does not survive the
  same strict verdict gates that Wave 230 P2 4-arm verdict did.
- Adding CLM-053 would re-introduce an over-claim risk of the same class
  that Wave 250 P1 fixed.
- Paper §3.4 already discloses the 4-arm verdict as
  "2 SUPPORTED + 14 UNDERPOWERED + 0 REGRESSED + 0 NOT_SIGNIFICANT".

This is a defensive decision consistent with the Wave 250 P1
over-claim fix.

---

## 5. Ready for push

**YES.** All 4 hard gates PASS:

- D.4 30/30
- mkdocs 0 warnings
- claims no drift
- abstract <= 250 words (183)

130 unpushed commits include:
- Wave 246 P3-P5 (FlowMol3 R3 confound + I² subgroup + wall-clock + final verify)
- Wave 250 P1-P6 (over-claim fix + CLM-054/057/058/062 + Wave 191 PROVISIONAL + final verify)
- Wave 251 P1-P3 (CLM-053 NOT_OK + status + this pre-push verify)

Push action is out of scope for this P3 verification doc.

---

## 6. Files

- Audit doc: `docs/audit/wave251-p3-final-pre-push.md` (this file)
- Canonical paper: `docs/paper-final-neurips.md`
- D.4 tests: `tests/test_d4_regression_vectors.py`
- mkdocs config: `mkdocs.yml`
- Claims consistency checker: `tools/check_claims_consistency.py`
