# Governance refresh post-push — living docs re-pointed at HEAD `0209002`

**Date:** 2026-10-11
**Status:** READY_TO_COMMIT
**Trigger:** After the 2026-10-11 push (`origin/main` `6036207` → `0209002`) and the
CI-gate repairs (mypy 988 → 0, pytest red → green), the living governance docs still
described the pre-push state. User directive: *"刷新治理文档到 HEAD"*.
**Scope:** Refresh the **current-state claims** in the living governance docs. Historical
audit records (`docs/audit/wave*.md`, `docs/ARCHIVE/**`) are left untouched — they record
the state at their own time. NO paper content change, NO number/verdict change, NO vendored
code change.

---

## Observed facts

### Stale claims (living docs only)

| Doc | Stale claim (pre-refresh) | Current fact |
|---|---|---|
| `todo/STATUS.md` | HEAD `061682c`; 188 unpushed; pytest `25 failed / 5166 passed`; mypy `988 errors` | HEAD `0209002`; 0 unpushed; pytest `5055 passed / 0 failed`; mypy `0 errors / 230 files` |
| `todo/WAVES.md` | HEAD `061682c`; 188 ahead; pytest/mypy disclosures | as above |
| `todo/README.md` | HEAD `061682c`; 188 ahead; `git push` pending | HEAD `0209002`; 0 ahead; push done |
| `todo/INDEX.md` | HEAD `061682c`; 188 ahead; `git push` pending | as above |
| `todo/PUSH-READY.md` | Wave-145-era "2 unpushed commits / READY TO PUSH" | obsolete → banner |
| `tnnls_submission/SUBMISSION_READINESS.md` | §6 inv #2 / §7 "NO-PUSH honoured (0 pushes since Wave 242)" | push complete (additive addendum) |

### Current facts captured (2026-10-11)

- **HEAD** = `0209002`; **`origin/main`** = `0209002`; **0 commits ahead**.
- **pytest** (CI subset `-m "not slow and not benchmark"`): `5055 passed / 171 skipped /
  50 deselected / 12 xfailed / 0 failed` (8m39s).
- **mypy**: `mypy --strict adaptive_reflow` → 0 errors in 230 files.
- **ruff**: `ruff check adaptive_reflow/ tests/` → All checks passed.
- **claims**: `tools/check_claims_consistency.py` → no drift.
- **mkdocs**: `mkdocs build --strict` → exit 0.

---

## Actions taken

- `todo/STATUS.md` — header/date, HEAD, unpushed (0), pytest, mypy, and the two
  out-of-scope lines (mypy repair + push) marked closed.
- `todo/WAVES.md` — date, repo-state bullets (HEAD/0-ahead), gate-results block, and the
  user-action push item marked done.
- `todo/README.md` — date, current-focus block, remaining user-gated actions, latest-audit
  pointer.
- `todo/INDEX.md` — title/date, historical note, current-execution state, user-gated
  actions, folder-layout heading.
- `todo/PUSH-READY.md` — SUPERSEDED banner prepended (body retained as provenance).
- `tnnls_submission/SUBMISSION_READINESS.md` — §10 addendum appended (ADDITIVE only; no
  existing line modified; §1/§2 counts unchanged). This file is **not** in the MANIFEST
  ledger, so no SHA refresh is required.

---

## Interpretation

These edits are **state-refresh, not history-rewrite**: each doc's factual claims about
*the present* are updated, while its record of *the past* (wave tables, audit links,
provenance chains) is preserved. The one frozen-surface edit
(`SUBMISSION_READINESS.md`) is strictly additive per AGENTS.md §3.5, and it does not enter
the SHA-256 ledger (§3.5: "numbers must not move; SHA-256s must be regenerated" — no
ledgered file's bytes changed).

`todo/TIMELINE.md` / `todo/LOOP.md` / `todo/GATES.md` were **not** edited: they define the
loop and gate *definitions* (e.g. G-OPS-PUSH = "empty unpushed set"), which are now
*satisfied* rather than stale — the definitions remain correct.

---

## Gaps / follow-ups

- **Tag push remains user-gated.** `v3.0-tnnls-ready` / `v3.1-tnnls-with-figure` are still
  local; the post-upload tag push per `tnnls_submission/README.md` §3 is a user action.
- **Only submission blocker unchanged:** the 17 `[USER TO FILL]` placeholders in
  `tnnls_submission/cover_letter.md` (31 grep hits = 17 fields + 14 doc pointers).

---

## Verification

```bash
# 1. Push state
git rev-parse HEAD origin/main           # both 0209002
git rev-list --count origin/main..HEAD   # 0

# 2. Gates
ruff check adaptive_reflow/ tests/                                   # All checks passed
.venv/bin/python -m mypy adaptive_reflow                             # Success: 0 issues, 230 files
PYTHONPATH=. python -m pytest tests/ -m "not slow and not benchmark" --no-header -q
# 5055 passed, 171 skipped, 50 deselected, 12 xfailed
python tools/check_claims_consistency.py                             # No drift detected
PYTHONPATH=. python tools/check_docs_against_code.py                 # OK: claims verified
mkdocs build --strict                                                # exit 0
```

---

## Files modified

- `todo/STATUS.md`, `todo/WAVES.md`, `todo/README.md`, `todo/INDEX.md`, `todo/PUSH-READY.md`
- `tnnls_submission/SUBMISSION_READINESS.md` (additive §10 only)
- `docs/audit/governance-refresh-post-push.md` — NEW audit doc (this file)
