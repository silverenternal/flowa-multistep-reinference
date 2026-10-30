# 101 fragment links, 37 of them pointing at nothing

**Date:** 2026-10-30
**Scope:** every `page.md#anchor` link in `docs/`, the two root READMEs and
`tnnls_submission/`; `tools/check_doc_anchors.py`.
**Status:** 37 broken fragments repaired, gate added. No metric, claim, status
label, or verdict moved; no GPU was used.

---

## 1. The gap between two gates

`tools/check_doc_links.py` resolves the *file* half of a relative link and then
throws the fragment away — `target = match.group(2).strip().split("#")[0]`
(line 104). `mkdocs build --strict` validates that a target page exists and
that every doc is in `nav`, not that `#anchor` matches a heading on that page.

So 101 fragment links were checked by nothing. 37 of them pointed at no
heading at all.

## 2. Why the anchors are not guessable

The site renders with Python-Markdown's `toc` extension and no custom
`slugify`, so ids are ASCII-only:

```
## Headline Results / 头条结果        ->  id="headline-results"
## 1. 背景：paper 在解决什么问题       ->  id="1-paper"
## 目录                              ->  id="_1"
```

Every Chinese-only heading collapses to `_1`, `_2`, … in document order. A link
written `#背景` looks correct in the source and resolves to nothing in the
browser. That is why the checker renders each page with the same extension
stack as `mkdocs.yml` instead of reimplementing the slug rule — a reimplementation
would have been wrong in exactly the cases that matter.

Two hand-written anchor forms are also legal and are collected:

* `<a id="背景"></a>` before a heading (used throughout
  `docs/算法实现说明.md`);
* `## Claim {#CLM-059}` (`attr_list`, used throughout `docs/CLAIMS.md`).

Missing the first form was a bug in the checker's own first draft: it reported
eight false positives in `docs/算法实现说明.md` that were in fact fine.

## 3. What was broken

| File | Broken | Cause |
|---|---:|---|
| `README.zh.md` | 34 | every TOC entry was written as `#english--中文`, the GitHub convention, but the site strips the Chinese and the em dash, so the real id is `#english` (or `#english-<ascii tail>`) |
| `README.md` | 2 | `#complete-inventory-innovations--experiments` — the heading is `Complete Inventory: Innovations & Experiments`, whose id collapses the `&` |
| `docs/ALGORITHMS.md` | 1 | `../README.md#the-four-feedback-loops` — that README section was removed; the four loops now live in `docs/算法实现说明.md` §6 |

The repair was mechanical for the READMEs: strip the non-ASCII tail, then
resolve the remainder against the page's real ids, taking the unique prefix
match when the heading kept an ASCII token (`#paper-a-submission-status` →
`paper-a-submission-status-a`, because `论文 A 投稿状态` leaves the `A`).
`docs/ALGORITHMS.md` was repointed by hand at the section that actually
describes the four loops.

## 4. The gate

`tools/check_doc_anchors.py` renders each page with `["toc", "attr_list",
"md_in_html", "pymdownx.superfences"]` — the same list as `mkdocs.yml` — walks
`md.toc_tokens` for ids, adds `{#…}` and `<a id=…>` anchors from the source, and
resolves every fragment link against them. It reports
`OK: 101 fragment links resolve`.

It needs the `markdown` package, a mkdocs dependency. Without it the tool
prints `SKIP` and exits 0, so a bare interpreter can still call it; CI runs it
in the job that installs the docs toolchain.

`tests/test_tools/test_doc_anchors.py` (5 tests) pins: the repo is clean, a
bilingual heading yields the ASCII id, both hand-written anchor forms are
collected, a broken fragment is reported, and a resolving one is accepted.

## 5. Wiring

Entry 17 of `todo.json`'s `gate_chain`, part of CI Gate 7, and a line in
AGENTS.md's checker list and CONTRIBUTING's gate table.

## 6. A hazard found on the way, not fixed

Smoke-testing every `tools/*.py` with `--help` rewrote 16 evidence files and
`verification_outputs/MANIFEST.md`: several drivers (`wave195_p2_r_level_power`,
`wave196_*`, `wave208_p1_*`, `wave230_p2_*`, `build_verification_manifest`)
execute on invocation and ignore argv entirely, so `--help` is not a dry run.
The files were restored from git and `check_data_integrity` re-verified
(`703 files, 0 mismatches`), but the pattern is a trap for anyone who pokes a
tool to see what it does. Fixing it means adding an `argparse` front end to
each driver; that is a separate change, and this note records the hazard so the
next reader does not learn it the same way.
