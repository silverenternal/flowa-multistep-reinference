# Data-availability artifact paths — three citations resolved to nothing

**Date:** 2026-10-31
**Scope:** `tnnls_submission/data_availability.md`, §"Per-record CSVs (verification artifacts)"
**Method:** CPU only. No sweep was run and no number changed.

## Why this was checked

The data-availability statement opens with a load-bearing promise: *"All
artifacts cited below are byte-addressable in `verification_outputs/` and on
Zenodo."* A reviewer who follows one of those links and gets a 404 has found
the statement false, which is worse than finding it vague. Nothing resolved
the links: `tools/check_submission_links.py` follows local markdown links, and
these are absolute `github.com` URLs into a tree that is only partly tracked.

The check performed here was mechanical. Extract every `github.com/...`
URL from the file, reduce it to the repository path it names, and ask git
whether that path has any tracked file:

```
git ls-files <path>
```

17 of the 32 URLs point into evidence directories. 13 resolve. 3 did not.

## The three

| Row | Cited | Reality |
|---|---|---|
| R3 | `verification_outputs/wave242-p1-flowmol3-seed{43,44}-*.json` (a glob at the tree root), tagged *"(in flight)"* | Only seed 43 exists; the `{43,44}` brace is not a URL glob at all. The manuscript's R3 is a completed three-seed test at N=1000 per arm, NFE=250, seeds 42/43/44, whose artifact is `verification_outputs/r3_n1000_3seed_fixed_q4_2026/` (14 tracked files, `SHA256SUMS` present). |
| R4 | `verification_outputs/r4_2d_two_moons_w2_m7p28pct/` | No such directory on disk and none in `git log --all`. The artifact is at `docs/headline-evidence/r4_2d_two_moons_w2_m7p28pct/` (4 tracked files). |
| R5 | `verification_outputs/r5_2d_eight_gaussians_w2_m10p40pct/` | Same: never existed under `verification_outputs/`; lives at `docs/headline-evidence/r5_2d_eight_gaussians_w2_m10p40pct/`. |

The R4/R5 defect has one cause. A 2026-09-25 pass converted 24 local paths in
this file into GitHub URLs by prefixing `verification_outputs/`; two of the
paths it converted already carried the `docs/headline-evidence/` prefix, so the
conversion dropped it. The directory names encode the readings they hold
(`…w2_m7p28pct`), which is why the mis-prefix was invisible on inspection.

## What changed

Three bullets and the sentence introducing them. No number, status label or
claim identifier moved.

- R3 now cites `verification_outputs/r3_n1000_3seed_fixed_q4_2026/` and
  describes the protocol the manuscript reports, without the *in flight* tag.
- R4 and R5 now cite the `docs/headline-evidence/` paths.
- The lead sentence says the CSVs live under `verification_outputs/` **and**
  `docs/headline-evidence/`, because after the fix both are true.

`MANIFEST.md` (row 10, size + SHA-256) and `SHA256SUMS` were refreshed.
`check_submission_manifest.py`: `rows=26 known_stale=0 unknown=0
addendum_drift=0 ledger_drift=0`; `sha256sum -c SHA256SUMS` clean.

## Left alone, deliberately

**The cell labels R4 and R5 no longer exist in the manuscript.** The paper
renumbered its cells to R5a / R5b / R5c and kept a single 2D cell, R5a (Two
Moons), which reports a TIE from the restart-aligned harness
(`verification_outputs/gap80-r5a-restart/aligned/r5a_restart.json`,
0.08439 vs 0.07828). The −7.28% / −10.40% readings this file cites are the
CLM-039 20-round best-of-scheduler measurements, which remain ACTIVE in
`docs/CLAIMS.md` but are not the manuscript's R5a number. Two true statements
about two different protocols.

Renumbering those bullets, or dropping the Eight Gaussians row, is a claims
decision rather than a path repair, so this pass stopped at the paths.

The same divergence appears in `tnnls_submission/tables.md` Table 1, whose R4
and R5 rows quote the CLM-039 readings against manuscript sections §7.6.4 and
§7.6.5 that do not exist in `paper-A-final.tex`. That file is not affected by
this finding: its own header declares it an internal inventory accumulated
across waves, states that the manuscript wins where a row disagrees, and
`tools/check_tables_inventory.py` recomputes each numeric cell from the
artifact it cites. The two files disagree with the manuscript in the same way
and for the same reason — old cell numbering — but only the data-availability
statement presented itself as the artifact map for the manuscript's numbers.
