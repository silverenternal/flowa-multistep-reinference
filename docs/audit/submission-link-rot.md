# Submission link rot: 40 of 253 reviewer-facing links do not resolve (2026-10-28)

CPU-only. `tnnls_submission/*.md` contains 253 unique
`github.com/.../blob/main/<path>` links. Resolved against the working tree,
**213 resolve, 40 do not**: 20 point at a file that was moved into
`docs/ARCHIVE/` by the Wave 266 reorganisation, 1 points at the wrong
directory, and 19 name a file that does not exist under any name.

This is a credibility issue, not a claim issue: none of the missing files
carries a number that the paper relies on. It is also cheap to fix — 21 of the
40 are a pure path rewrite. The submission is frozen, so nothing was edited.

Reproduce: `python3 tools/check_submission_links.py`.

## 1. Moved to `docs/ARCHIVE/` (20 links, 18 targets) — pure prefix fix

Replace `docs/audit/` with `docs/ARCHIVE/audit-by-wave/` (or
`docs/drafts/` with `docs/ARCHIVE/legacy-paper/` for `paper-draft.md`).

| cited path | actual path | cited from |
|---|---|---|
| `docs/audit/wave218-p1-fix-applied.md` | `docs/ARCHIVE/audit-by-wave/wave218-p1-fix-applied.md` | cover_letter |
| `docs/audit/wave229-p3-core-adapter-paper-quantities.md` | `docs/ARCHIVE/audit-by-wave/wave229-p3-core-adapter-paper-quantities.md` | cover_letter |
| `docs/audit/wave230-p2-real-4arm-per-record.md` | `docs/ARCHIVE/audit-by-wave/wave230-p2-real-4arm-per-record.md` | cover_letter |
| `docs/audit/wave233-p5-r5b-fix.md` | `docs/ARCHIVE/audit-by-wave/wave233-p5-r5b-fix.md` | cover_letter |
| `docs/audit/wave233-p6-wall-clock-opt.md` | `docs/ARCHIVE/audit-by-wave/wave233-p6-wall-clock-opt.md` | cover_letter |
| `docs/audit/wave234-p2-tost.md` | `docs/ARCHIVE/audit-by-wave/wave234-p2-tost.md` | cover_letter |
| `docs/audit/wave234-p4-bf01.md` | `docs/ARCHIVE/audit-by-wave/wave234-p4-bf01.md` | cover_letter |
| `docs/audit/wave234-p5-meta-analysis.md` | `docs/ARCHIVE/audit-by-wave/wave234-p5-meta-analysis.md` | cover_letter |
| `docs/audit/wave235-p2-r2-uplift.md` | `docs/ARCHIVE/audit-by-wave/wave235-p2-r2-uplift.md` | cover_letter, figures |
| `docs/audit/wave235-p4-flowmol3-3seed.md` | `docs/ARCHIVE/audit-by-wave/wave235-p4-flowmol3-3seed.md` | cover_letter |
| `docs/audit/wave237-p2-reverify.md` | `docs/ARCHIVE/audit-by-wave/wave237-p2-reverify.md` | MANIFEST |
| `docs/audit/wave238-p2-cuda-graph-verify.md` | `docs/ARCHIVE/audit-by-wave/wave238-p2-cuda-graph-verify.md` | cover_letter |
| `docs/audit/wave238-p4-final-verify.md` | `docs/ARCHIVE/audit-by-wave/wave238-p4-final-verify.md` | MANIFEST, submission_checklist |
| `docs/audit/wave242-p2-flowmol3-direction.md` | `docs/ARCHIVE/audit-by-wave/wave242-p2-flowmol3-direction.md` | cover_letter |
| `docs/audit/wave242-p4-final-verify.md` | `docs/ARCHIVE/audit-by-wave/wave242-p4-final-verify.md` | MANIFEST |
| `docs/audit/wave261-p1-inventory.md` | `docs/ARCHIVE/audit-by-wave/wave261-p1-inventory.md` | data_availability |
| `docs/audit/wave261-p5-final-audit.md` | `docs/ARCHIVE/audit-by-wave/wave261-p5-final-audit.md` | data_availability |
| `docs/drafts/paper-draft.md` | `docs/ARCHIVE/legacy-paper/paper-draft.md` | figures |

## 2. Wrong directory (1 link)

| cited path | actual path | cited from |
|---|---|---|
| `adaptive_reflow/profile_residual.py` | `adaptive_reflow/adapters/profile_residual.py` | cover_letter |

## 3. No file with that name (19 links) — needs the author

These are the ones I cannot repair mechanically. Four have a plausible
different-name candidate; the rest have none.

| cited path | cited from | note |
|---|---|---|
| `docs/audit/wave234-p6-non-inferiority.md` | cover_letter | likely `docs/audit/stats_method/p6-non-inferiority.md` |
| `docs/audit/wave235-p1-r5b-fix.md` | cover_letter, figures | likely `docs/audit/stats_method/p1-r5b-fix.md` |
| `docs/audit/wave235-p3-r6-uplift.md` | cover_letter, figures | likely `docs/audit/stats_method/p3-r6-uplift.md` |
| `docs/audit/wave349-r1-3seed-gpu.md` | tables | likely `docs/audit/r1-3seed-real-ckpt-materialize.md` |
| `docs/audit/wave233-p3-tier-aware.md` | cover_letter | no exact match; `wave225-p4-k6-tier-aware.md` and `wave245-p2-tier-aware-independence.md` are different waves |
| `docs/audit/wave236-p2-wallclock-fix.md` | cover_letter, figures | no exact match; `wave233-p6-wall-clock-opt.md` is a different wave |
| `docs/audit/wave238-p3-journal-decision.md` | submission_checklist | no match |
| `docs/audit/wave280-p-framework-fallback-contamination.md` | tables | no match |
| `docs/audit/wave343-manifest-rehash.md` | MANIFEST | no match |
| `docs/audit/wave348-cross-doc-github-urls.md` | MANIFEST | no match; `wave345-cross-doc-fixes.md` is a different wave |
| `docs/audit/wave146-cifar-v4-audit.md` | MANIFEST | no match |
| `docs/audit/wave157-close.md` | MANIFEST | no match; `wave157-push.md` is a different document |
| `docs/audit/wave213-p6-repo-naming.md` | cover_letter | no match |
| `docs/audit/wave262-p1-revert-all.md` | data_availability | no match |
| `docs/audit/wave262-p3-rerun.md` | data_availability | no match |
| `scripts/wave242_p1_flowmol3_rescue_single_mol.py` | cover_letter | script not in the tree |

(`wave234-p6-non-inferiority`, `wave235-p1-r5b-fix` and `wave235-p3-r6-uplift`
each appear twice, which is why 19 links cover 16 distinct targets.)

## 4. What was already repaired

`docs/audit/wave262-p2-verify.md` was cited by `data_availability.md` and did
not exist. It now exists, with the vendored-upstream MD5 table and a
reproduction command; see `docs/audit/wave262-p2-verify.md`.

## 5. Recommendation

The 21 mechanical fixes are one `sed` on the submission package, but that is a
frozen surface and needs authorisation. The 19 absent links need a decision per
link: repoint, or drop the sentence. Dropping is often right — a reviewer who
clicks a dead link learns nothing, and the underlying result is usually already
in `verification_outputs/`.

---

## 6. Resolution (2026-10-29) — authorised, and closed

The refresh in §5 was authorised. All 40 broken targets were repaired:
20 moved into `docs/ARCHIVE/` by the Wave 266 reorganisation (prefix
rewrite), 10 re-pointed by topic into the reorganised
`docs/audit/{engineering,stats_method,algorithm_4arm,sweep_eval}/` files,
5 re-pointed to the document that actually covers the subject, and 1 — the
Wave 242 rescue script — was never committed, so the hyperlink was removed and
the sentence now says so.

`tools/check_submission_links.py` now exits 1 on any absent target
(`KNOWN_ABSENT` is empty) instead of always exiting 0, and
`tests/test_submission_links.py` pins `absent=0`.

`links=242 absent=0 ok=242`.

The same audit was then run across the rest of the documentation tree —
see `docs/audit/doc-link-audit.md`.
