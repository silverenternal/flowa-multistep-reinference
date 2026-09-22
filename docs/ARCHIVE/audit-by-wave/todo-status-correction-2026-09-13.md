# TODO status correction audit (2026-09-13)

Applied two low-risk documentation corrections identified in the task
inventory:

* `todo/push-unpushed-commits.md` now distinguishes the historical Wave 12
  push (completed) from later commits that remain user-gated and deferred.
  No push or remote mutation was performed.
* `todo/inprogress/README.md` now explicitly states that the directory is
  empty and that Wave 75–78 historical plans live in `todo/completed/`.

Evidence: `git status --short` showed no active files under
`todo/inprogress/`; `todo/STATUS.md` records the later unpushed commit count.
Markdown relative-link scan after the edits reports zero broken links.
