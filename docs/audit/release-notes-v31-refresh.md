# `docs/RELEASE-NOTES.md` — refresh to the `v3.1-*` tag state

**Date:** 2026-10-12
**Scope:** Refresh `docs/RELEASE-NOTES.md` from `v3.0-tnnls-ready` to the current
`v3.1-*` tag state, on user request (menu selection: "更新 RELEASE-NOTES.md").
Closes finding **F3** of `docs/audit/docs-legacy-inventory.md` ("stale, not
legacy"). Pure-documentation, **additive**; no headline number, claim status,
manuscript artifact, source module, or vendored-upstream file changed.
**Status:** COMPLETE. All gates green. Not pushed (NO-PUSH policy).

---

## 1. Observed facts (pre-edit)

- `docs/RELEASE-NOTES.md` (mtime 2026-09-22) declared `**Version:** v3.0-tnnls-ready`
  and `**Status:** ... frozen at commit `51e0aa4``. Commit `51e0aa4` is
  `2026-09-22` "Wave 251 P3: final pre-push verification" — **older than every
  `v3.1-*` tag** and not the commit the `v3.0-tnnls-ready` tag points at.
- The repo carries four `v3.x` tags (all ancestors of HEAD):

  | Tag | Commit | Date | Wave |
  |---|---|---|---|
  | `v3.1-tnnls-with-figure` | `490b388` | 2026-09-25 | 349 |
  | `v3.0-tnnls-ready` | `91663f6` | 2026-09-25 | 348 |
  | `v3.1-alignment-snapshot` | `e8e6f5b` | 2026-09-23 | 292 |
  | `v3.1-internal-publishable` | `27edab6` | 2026-09-23 | 291 |

- `git diff --stat v3.0-tnnls-ready..v3.1-tnnls-with-figure` (12 files, +638/−10)
  isolates the `v3.1` delta: the R5c regime-curve figure (`docs/figures/fig5_r5c_regime_curve.png`
  + auxiliary `docs/drafts/figure_r5c_regime_curve.png`), renderer
  `tools/render_r5c_regime_curve.py`, additive edits to `docs/drafts/paper-A-final.md`,
  `tnnls_submission/MANIFEST.md` rehash, and the `adaptive_reflow/adapters/lineageflow.py`
  + `tools/gen_lineageflow_n1000_fastas.py` GPU-dispatch changes.
- `docs/README.md` §2 described the file as "Release notes for the current
  source-tree freeze." `todo/WAVES.md` §1.1 pinned HEAD `a957906` / ahead 7
  (stale by 2 commits after `cefe6b0` and `2319c57`).

## 2. Interpretation

- The file is the **canonical** release-notes surface (it is in the mkdocs nav),
  so it must describe the *current* release. The prior pass (`docs-legacy-inventory.md`)
  correctly classified it **stale, not legacy** — it should be updated, not bannered.
- Because AGENTS.md hard guardrail #5 (submission-freeze) forbids moving numbers
  once the `v3.0-tnnls-ready` tag is cut, the update must be **additive**: describe
  the `v3.1` delta while preserving the frozen submission body verbatim.
- The `v3.1` delta is documentation + one figure + one defensive GPU-dispatch
  change. No headline number moved and no claim status was flipped; the eleven-cell
  distribution stays `4 STRONG + 1 TIE + 6 PARTIAL/SUPP`.

## 3. Changes (additive)

- `docs/RELEASE-NOTES.md`
  - Header: `**Version:**` → `v3.1-tnnls-with-figure (latest tag, `490b388`)`;
    `**Status:**` corrected from the stale `frozen at commit `51e0aa4`` to the
    current release statement; added a `**Tags in the v3.x series:**` block.
  - New section **"v3.1-tnnls-with-figure — changes since v3.0"** (scope note +
    8-row change table + R1-status paragraph + freeze-time-gate pointer).
  - One clarifying block-quote under `## Overview` noting the sections below
    describe the frozen submission.
  - **Everything below `## Overview` is preserved verbatim.**
- `docs/README.md` §2: the `RELEASE-NOTES.md` row now names the current tag.
- `todo/WAVES.md` §1.1: HEAD `a957906`→`2319c57`, ahead `7`→`11`; prior-reading
  list and the local-only narrative updated.
- `mkdocs.yml`: registered `audit/release-notes-v31-refresh.md` in `not_in_nav`.

### R1 honesty note

The `v3.1` tag message says "R1 3-seed retro-validated". The **live manuscript**
(`docs/drafts/paper-A-final.md` §7.2, line 556 + the 11-cell table line 662)
preserves the R1 verdict **PARTIAL / single-seed-disclosed** verbatim and does
**not** promote it. The release notes therefore state R1 status as unchanged and
point at `docs/audit/wave349-gap-audit.md` §2 for the probe record — no promotion
by wording (hard guardrail #4).

## 4. Gate results (acceptance record)

| Gate | Command | Result |
|---|---|---|
| readiness verifier | `python tools/verify_submission_readiness.py` | **READY_WITH_SKIPS: mypy_0** (exit 0) |
| claims consistency | `python tools/check_claims_consistency.py` | **PASS** — no drift (61 active) |
| docs-against-code | `python tools/check_docs_against_code.py` | **PASS** |
| D.4 byte-stable | `python -m pytest tests/test_d4_regression_vectors.py tests/test_adapters/test_regression_vectors.py -q` | **72 passed / 0 failed** |
| ruff | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | **PASS** — 0 findings |
| mkdocs strict | `mkdocs build --strict` | **PASS** — exit 0 |

## 5. File digests (post-edit)

| File | sha256 |
|---|---|
| `docs/RELEASE-NOTES.md` | `c047f18becfeddcbff5ee936bc07e34f2d68e4b11c45ad69bc5d4747977105f5` |
| `docs/README.md` | `184ccd2fe9f5fea298f9f7652498c51b8876a38bc68f9fcdbe7c7db4a44a28d6` |
| `mkdocs.yml` | `a0131927b42f1b931bc456b056a1a7e37bbe746bcde8060b5747669a69232f5c` |
| `todo/WAVES.md` | `b14c626af7485eb5cf81c5f7f8f9f70e5fa4e7d4d91fa0116b61eca4ae639c47` |

**Self-referencing-SHA convention.** `todo/WAVES.md` §1.1 pins the *pre-edit*
actual (`2319c57`); the post-edit actual is the commit that introduces this audit
doc (retrieve via `git log -1`).

## 6. Unresolved gaps / caveats

- **D.4 "30/30" vs "72/72".** The §4 table's 72 is the *combined* D.4 gate
  (`test_d4_regression_vectors.py` 30 + `tests/test_adapters/test_regression_vectors.py`
  42). `todo/WAVES.md` §1.2 and the manuscript cite the **30/30** figure, which is
  the first file alone. Both are green; the difference is the gate's scope, not a
  regression.
- **`docs/RELEASE-NOTES.md` §Submission Gates table** carries `v3.0` freeze-time
  readings (e.g. "Pytest 5155 passed / 196 skipped", "Mypy 0 errors"). These are
  retained verbatim as the freeze snapshot; the new §v3.1 section points readers at
  `todo/WAVES.md` §1.2 for the current gate state.
- **Tag linearity is not asserted.** The four `v3.x` tags are listed by date, not
  as a strict linear chain (the `v3.1-alignment-snapshot` / `v3.1-internal-publishable`
  wave numbers and tag dates are not monotone).
- **`docs/RELEASE-NOTES-v3.0.md`** is referenced by `adaptive_reflow/framework/engine.py:6`;
  that file does not exist (the canonical file is `docs/RELEASE-NOTES.md`). Left
  as-is — a source-code comment, out of scope for this pass.
