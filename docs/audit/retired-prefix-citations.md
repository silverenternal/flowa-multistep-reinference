# Citations into a directory that no longer exists

**Date:** 2026-10-30
**Scope:** `tnnls_submission/*.md`, `docs/README.md`, `tools/check_reviewer_pointers.py`
**Status:** 6 citations repointed, `todo` added to the checked prefixes

---

## 1. What happened

`AGENTS.md` §"Management & map surfaces" records that the `todo/` directory
was retired on 2026-10-13 and that "any reference to it is stale". The
directory is gone from the tree. Six backticked citations into it survived,
four of them in the shipped submission package:

| File | Citation |
|---|---|
| `tnnls_submission/submission_checklist.md:137` | `todo/PUSH-READY.md` |
| `tnnls_submission/SUBMISSION_READINESS.md:162` | `todo/PUSH-READY.md` |
| `tnnls_submission/SUBMISSION_READINESS.md:166` | `todo/RISK-REGISTER.md` R-019 |
| `tnnls_submission/SUBMISSION_READINESS.md:230` | `todo/RISK-REGISTER.md` R-019 |
| `tnnls_submission/MANIFEST.md:98` | `todo/WAVES.md`, `todo/SUBMISSION-GAP-CHECKLIST.md` |
| `docs/README.md:139` | `todo/PUSH-READY.md` |

`check_reviewer_pointers.py` was green throughout, because `todo` was not in
its `PATH_PREFIXES` — the tuple listed the directories that exist. That is the
same shape as the two defects before it: the gate checked the spellings it knew
and the retired prefix was not one of them.

## 2. Repairs

- **`todo/PUSH-READY.md` → `todo.json`.** The NO-PUSH policy moved into
  `todo.json` as `no_push: true` and `commit_footer: "(USER AUTHORIZED, NO
  PUSH)"`. Both checklist rows now cite those fields.
- **`todo/RISK-REGISTER.md` R-019 → `docs/audit/wave350-r6-live-attempt.md`.**
  R-019 was the R6 live-GPU re-verification deferral. `todo.json`'s `deferred`
  list carries four entries and none of them is R-019, so there is no
  consolidated successor; the audit record that documents the same deferral
  ("full live GPU DEFERRED to camera-ready", §1) does exist and is cited
  instead. Both call sites say plainly that the item moved.
- **`todo/WAVES.md`, `todo/SUBMISSION-GAP-CHECKLIST.md` (MANIFEST.md:98) →
  plain text.** This line is a historical description of the 2026-10-12
  terminology pass ("107 files updated: …"), not a pointer a reader is meant to
  follow. The two names are now unformatted and carry "both retired
  2026-10-13".
- **`docs/README.md:139` → "the retired `todo/` directory (`PUSH-READY.md`),
  removed 2026-10-13".** The sentence already says the file was removed; it now
  says so without presenting a path that resolves to nothing.

## 3. The gate

`todo` is now in `PATH_PREFIXES`. The token regex requires `todo/` + a name +
a known extension, so the two prose mentions of the directory itself
(`docs/README.md:13`, `AGENTS.md:13`) are not treated as pointers — they name a
retired directory, they do not promise a file.

`tests/test_tools/test_reviewer_pointers.py` gained
`test_the_retired_todo_directory_is_still_checked`, which asserts the prefix is
in the tuple and that two `todo/*.md` tokens are reported.

Current output: `checked=645 dead=0`.

## 4. Unresolved

- The `todo/` content itself is gone; only `todo.json` survives. A reader who
  wants the pre-2026-10-13 planning history has `docs/audit/todo-history.md`
  and `docs/audit/engineering/todo-refactor.md`, neither of which is cited from
  the submission package.
- `MANIFEST.md` and `submission_checklist.md` were re-hashed; `SHA256SUMS`
  regenerated (22 OK).
