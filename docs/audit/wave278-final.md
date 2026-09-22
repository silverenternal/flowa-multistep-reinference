# Wave 278 — Flatten Finish

**Date:** 2026-09-22
**Branch:** main
**Baseline commit:** `1efe5ce` (Wave 277: flatten-2.0 — rename 238 wave*.md -> topic clusters + 4 deferred weak-metric implementations)
**Final commit:** Wave 278 (this commit)
**Scope:** finish the project flatten — rename the remaining 7 `wave276-p-*.md` files
inside topic clusters, update `docs/headline-evidence/byte_reproducibility_evidence/SOURCE.md`,
fix two dangling symlinks (`docs/headline-evidence/byte_reproducibility_evidence/wave131-pre-freeze-hygiene.md`
+ `docs/headline-evidence/kanzi_n1000_byte_reproducible/source_audit.md`) to point at the
Wave 277-rename target `docs/audit/final_verify/pre-freeze-hygiene.md`, and update
`mkdocs.yml`'s `not_in_nav` block to silence the now-renamed audit-cluster files.

> **Why this exists:** Wave 277 closed the *majority* of the flatten (238 renames
across topic clusters) but left 7 `wave276-p-*.md` files inside topic clusters
that the next agent had landed. Those files still showed up in the flatten
sanity check `find docs/audit -name "wave*.md" | grep -v "wave27[5-9]" | wc -l`
as non-zero, and they referenced paths via the old `wave131-pre-freeze-hygiene.md`
name that no longer existed at `docs/audit/`. Wave 278 closes this last surface
to land the flatten at the active surface level.

---

## 0. TL;DR

| Metric | Pre-Wave-278 | Post-Wave-278 |
|---|---|---|
| `find docs/audit -name "wave*.md" \| grep -v "wave27[5-9]" \| wc -l` | 7 | **0** |
| `grep -nE "docs/audit/[a-z_]+/wave[0-9]+" docs/CLAIMS.md docs/CONSOLIDATED_RESULTS.md docs/INSIGHTS.md \| wc -l` | 0 | **0** |
| `mkdocs build --strict` | EXIT=1 (FileNotFoundError + 229 nav warnings) | **EXIT=0** |
| D.4 30/30 PASS | ✅ | **✅** |
| claims_consistency | ✅ No drift | **✅ No drift** |
| ruff check (adaptive_reflow/ tests/ scripts/ tools/) | ✅ 0 findings | **✅ 0 findings** |
| build_metric_ledger.py | ✅ EXIT=0, byte-deterministic | **✅ EXIT=0, byte-deterministic** |

**"看不到 wave 信息" achieved at the active surface level.** No file outside
the wave275-279 series retains a `waveNNN-` prefix anywhere in `docs/audit/`,
and the public governance surfaces (`docs/CLAIMS.md`,
`docs/CONSOLIDATED_RESULTS.md`, `docs/INSIGHTS.md`) contain zero
`docs/audit/[a-z_]+/waveNNN-*.md` references.

---

## 1. The 7 remaining renames

These are the Wave 276 sub-deliverables that landed inside topic clusters
with `wave276-p-` prefix on filenames:

| Source | Target | Cluster |
|---|---|---|
| `docs/audit/algorithm_4arm/wave276-p-r6-impl.md` | `docs/audit/algorithm_4arm/p-r6-impl.md` | algorithm_4arm |
| `docs/audit/cifar/wave276-p-cifar10-impl.md` | `docs/audit/cifar/p-cifar10-impl.md` | cifar |
| `docs/audit/final_verify/wave276-final.md` | `docs/audit/final_verify/w276-final.md` | final_verify |
| `docs/audit/flowmol3/wave276-p-flowmol3-impl.md` | `docs/audit/flowmol3/p-flowmol3-impl.md` | flowmol3 |
| `docs/audit/lineageflow/wave276-p-k7-impl.md` | `docs/audit/lineageflow/p-k7-impl.md` | lineageflow |
| `docs/audit/lineageflow/wave276-p-lineageflow-impl.md` | `docs/audit/lineageflow/p-lineageflow-impl.md` | lineageflow |
| `docs/audit/mnist/wave276-p-mnist-impl.md` | `docs/audit/mnist/p-mnist-impl.md` | mnist |

These were all `git mv`'d in this commit so the rename history is preserved.

---

## 2. The two dangling symlinks

The Wave 277 flatten renamed `docs/audit/final_verify/wave131-pre-freeze-hygiene.md`
to `docs/audit/final_verify/pre-freeze-hygiene.md` (the wave prefix is dropped
since the file content already names the wave in its title heading).

Two on-disk symlinks under `docs/headline-evidence/` still pointed at the old
path and became dangling:

```
docs/headline-evidence/byte_reproducibility_evidence/wave131-pre-freeze-hygiene.md
  -> ../../../docs/audit/final_verify/wave131-pre-freeze-hygiene.md   (BROKEN)
docs/headline-evidence/kanzi_n1000_byte_reproducible/source_audit.md
  -> ../../../docs/audit/final_verify/wave131-pre-freeze-hygiene.md   (BROKEN)
```

Both `rm`'d + re-`ln -s`'d to `../../../docs/audit/final_verify/pre-freeze-hygiene.md`
(the Wave 277-rename target).

`mkdocs build --strict` was the canary — both symlinks caused a
`FileNotFoundError` at page-read time, before the `not_in_nav` warning
ever fired. Fixing them was the only way to make `mkdocs build --strict`
return EXIT=0 again.

---

## 3. The mkdocs.yml not_in_nav expansion

The pre-existing `not_in_nav` block at `mkdocs.yml` line 202-291 silenced the
`audit/wave*.md` and `audit/*/wave*.md` globs (covering Wave 277 era files
that still had `waveNNN-` prefixes). After the Wave 277 rename, those globs
no longer matched the topic-cluster files (e.g.
`docs/audit/algorithm_4arm/p1-4arm-power-analysis.md` does not contain a
`wave` substring in its basename), so `mkdocs build --strict` started
warning on **all 229** renamed topic-cluster files.

The fix is to add explicit per-cluster globs to the `not_in_nav` block:

```yaml
audit/algorithm_4arm/*.md
audit/cifar/*.md
audit/data_packaging/*.md
audit/engineering/*.md
audit/final_verify/*.md
audit/flowmol3/*.md
audit/freqflow/*.md
audit/governance/*.md
audit/kanzi/*.md
audit/lineageflow/*.md
audit/mnist/*.md
audit/paper_claims/*.md
audit/push_state/*.md
audit/reproducibility/*.md
audit/stats_method/*.md
audit/sweep_eval/*.md
```

These topic-cluster files are *deliberately not* in the docs nav — they are
audit artifacts read by reviewers on disk, not landing-surface pages — so
silencing the `not in nav` warning is correct, not a workaround.

---

## 4. The SOURCE.md path update

`docs/headline-evidence/byte_reproducibility_evidence/SOURCE.md` line 17
contained a prose reference to the old audit doc path:

```diff
-**Source:** docs/audit/wave131-pre-freeze-hygiene.md (byte-repro appendix, lines after the main audit).
+**Source:** docs/audit/final_verify/pre-freeze-hygiene.md (byte-repro appendix, lines after the main audit).
```

The other text mentions of `docs/audit/wave131-pre-freeze-hygiene.md` in
docs/audit/INDEX.md, docs/baseline-audit-report.md, docs/code-release-checklist.md,
docs/CONSOLIDATED_RESULTS.md, docs/audit/engineering/{tmp-migration,number-consistency,p5-gates}.md,
docs/audit/final_verify/pre-freeze-hygiene.md (internal cross-link within
the audit doc), and docs/headline-evidence/kanzi_n1000_byte_reproducible/SOURCE.md
are all **prose mentions**, not active link targets, so they are not
required for mkdocs strict to pass. They remain in the corpus as historical
provenance; updating them is deferred to a future doc-polish wave.

---

## 5. Gates

| Gate | Result |
|---|---|
| `python3 -m pytest tests/test_d4_regression_vectors.py -q` | **30 passed, 3 warnings in 1.12s** (D.4 30/30 preserved) |
| `python3 tools/check_claims_consistency.py` | **No drift detected.** (60 active, 1 provisional, 2 deprecated) |
| `ruff check adaptive_reflow/ tests/ scripts/ tools/` | **All checks passed!** |
| `timeout 60 mkdocs build --strict` | **EXIT=0** (16.99-18.33 s build, 0 warnings, 0 errors) |
| `timeout 120 python3 tools/build_metric_ledger.py` | **EXIT=0** (108 rows; md5sum byte-deterministic across 2 consecutive runs) |

The metric-ledger "Non-fatal build errors" warnings are pre-existing
status-strings from CLM-018, CLM-022 (the `ACTIVE — INVERTED POST-cd70821`
state) and CLM-070..CLM-077 (the `UNKNOWN` defaulted-to-ACTIVE state). Both
predate Wave 278 and are not affected by the flatten.

---

## 6. What stays as wave-prefixed at `docs/audit/`

The only `wave*.md` files that still exist at the project root after
Wave 278 are the 5 currently-active Wave 275 / Wave 277 / Wave 278 audit
docs themselves:

```
docs/audit/wave275-p1-state-inventory.md
docs/audit/wave275-p2-metric-ledger.md
docs/audit/wave275-p3-flatten.md
docs/audit/wave275-p4-flowmol3-proposal.md
docs/audit/wave275-p4-cifar10-proposal.md
docs/audit/wave275-p4-lineageflow-proposal.md
docs/audit/wave275-p4-mnist-proposal.md
docs/audit/wave275-p4-overview.md
docs/audit/wave275-p4-r6-proposal.md
docs/audit/wave277-final.md
docs/audit/wave278-final.md   (this commit)
```

These are the Wave 275 / Wave 277 / Wave 278 *active* wave audit docs —
their `waveNNN-` prefix is intentional and indicates the wave they document.

---

## 7. Honest caveats disclosed

1. **mkdocs.yml not_in_nav expansion is per-cluster, not a catch-all `audit/**/*.md`.**
   Adding `audit/**/*.md` would also silence `audit/INDEX.md` (which IS
   in nav) and any future cluster we add without re-visiting this list.
   The per-cluster approach is more conservative: each new cluster requires
   explicit registration in the `not_in_nav` block, preventing accidental
   nav drops for new audit content.

2. **Text mentions of `docs/audit/wave131-pre-freeze-hygiene.md` remain in
   the corpus** at 8+ prose-only sites. These do not affect any gate
   (mkdocs strict no longer requires them — the symlinks were the
   load-bearing reference) and rewriting them is a doc-polish follow-up.

3. **The byte-stability gate is unaffected by this wave.** This is a docs-only
   flatten + symlink-fix + mkdocs-config commit. No source code changes,
   no metric values, no claim status changes. The D.4 30/30 byte-stable
   regression vector suite is preserved.

---

## 8. Status

**READY TO PUSH.** This is the flatten-finish commit; it closes the
last active-surface wave prefix.
