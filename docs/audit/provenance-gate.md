# A provenance checker that was never a gate

**Date:** 2026-10-30
**Scope:** `tools/check_data_provenance.py`, `tests/test_tools/test_data_provenance.py`
**Status:** gate 20; 0 drifts, 3 disclosed

---

## 1. Observed facts

`tools/check_data_provenance.py` walks `docs/audit/wave*.md`, pairs each
cited sha256 with the `verification_outputs/` path beside it, and compares the
pair against the file on disk. It was written in Wave 342 and appears in no
chain: not `todo.json["gate_chain"]`, not CI, not
`verify_submission_readiness.py`. It also had no tests.

Run today it reported `citations=108 paths=66 drifts=3` and exited 1. The
three drifts are all `orphan_sha`:

| Record | Cited | On disk |
|---|---|---|
| `docs/audit/wave350-r6-live-attempt.md:82` | `e7fbee8a…` for `wave350-r6-live-smoke/foldability.jsonl` | `c0774132…` |
| `docs/audit/wave363-k1-recipe.md:45` | `0c7ad234…` for `wave280-p-k1/SHA256SUMS` | `320bead3…` |
| `docs/audit/wave363-k4-recipe.md:16` | `906420fb…` for `wave280-p-k4k5/SHA256SUMS` | `6ea0b3cb…` |

All three are **reconciled in place**, not false positives. Each record states
the run-time hash, then the current one, then why the bytes moved:

> The `foldability.jsonl` hash above is the value recorded at run time. The
> file on disk now hashes to `c0774132…`; … The JSONL was rewritten during the
> PDB consolidation …, which changes bytes without changing values.
> `verification_outputs/` is gitignored, so the original bytes are not
> recoverable and the run-time hash cannot be re-derived.

`docs/audit/wave342-claims-fixes.md` §4.2 called these "cartesian-product
parser false positives" and proposed a sequential-pairing rewrite. Reading the
three lines, the pairing is correct — the parser finds exactly one path and one
hash per clause — and the audit record's own account of the cause is the
accurate one. The Wave 342 note also recorded the fix as "out of scope for this
additive governance wave", which is why it stayed open.

## 2. Why it could not be a gate as written

A checker that exits 1 on a reconciled citation can never go green, so it was
never wired in. A checker that skipped stale hashes would not see a real one.
The distinction that matters is not *stale* but *unexplained*.

## 3. The rule

A stale citation is a **drift** unless the same document records the current
on-disk hash within `RECONCILE_WINDOW = 40` lines of the citation. When it
does, the citation is **disclosed**: still reported (so a reader sees it), not
a failure.

Proximity is required so an unrelated hash elsewhere in a long record cannot
silently excuse a stale citation. The three records in the tree put the
reconciling hash 4-14 lines below the citation, in a "Hash note".

`verify()` and `_extract_citations()` gained a `repo_root` parameter so the
tests can build a synthetic tree; the CLI behaviour is unchanged.

## 4. Result

```
provenance: citations=108 paths=66 drifts=0 disclosed=3
```

The three disclosed citations are listed under "Disclosed (not a failure)" in
the full report, with the same detail line a drift would carry.

`tests/test_tools/test_data_provenance.py` (8 cases): the repository is clean;
a matching citation is accepted; a stale citation with no note is a drift; a
stale citation with the current hash beside it is disclosed; a reconciling hash
outside the window is still a drift; a missing file is a drift; `-h`/`--help`
exit 0.

Added to `todo.json["gate_chain"]` (19 → 20), `AGENTS.md` §4.1 (thirteen →
fourteen checkers) and CI Gate 7.

## 5. Unresolved

- The extractor only reads `docs/audit/wave*.md`. Records filed under
  `docs/audit/<cluster>/` (e.g. `docs/audit/engineering/`, `stats_method/`)
  are not scanned, so the 108 citations are the `wave*` subset, not the whole
  audit tree. Widening the glob would need the same disclosure rule applied to
  a much larger set; not attempted here. **Closed 2026-10-30 — see §6.**
- A document could in principle carry an unrelated copy of the current hash
  within 40 lines. The window is a heuristic, not a proof.

---

## 6. Addendum (2026-10-30) — the scan is recursive

The limitation in §5 is closed. `verify()` now walks
`audit_dir.rglob("*.md")` instead of `audit_dir.glob("wave*.md")`, because
increments have filed under topic clusters since October: 243 top-level
`wave*.md` against 625 audit records in total.

| Reading | Before | After |
|---|---:|---:|
| citations parsed | 108 | **127** |
| unique paths cited | 66 | **83** |
| drifts | 0 | **0** |
| disclosed | 3 | **3** |
| not checkable | — | **8** |

The eight new non-results are not new drift; they are citations that cannot be
resolved to one file *by construction*, and §5's fear ("a much larger set")
did not materialise because they are only two shapes:

- **directory citations** — `close-w158.md:201-202` cite a whole run directory
  with a sha256 (`verification_outputs/lineageflow_hmmer_real_n1000_…/`);
- **elided paths** — `k6-verification.md:92-98` abbreviate the tree as
  `verification_outputs/.../baseline/summary.json`.

Both are now counted in `ProvenanceResult.unverifiable` and printed under
"Not checkable (not a failure)", rather than reported as `missing_file`. The
alternative — resolving `...` literally — would have manufactured eight false
drifts.

The disclosure heuristic (§5, second bullet) is unchanged, and the three
disclosed citations are the same three as before: widening the scan added no
drift and no new disclosure.

