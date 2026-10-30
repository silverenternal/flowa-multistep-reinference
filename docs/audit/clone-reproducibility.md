# Clone reproducibility — the evidence tree did not survive a `git clone`

**Date:** 2026-10-29
**Scope:** `verification_outputs/`, `paper-data/`, `docs/headline-evidence/`,
`data/freqflow_ckpt/`, and the six package-integrity checkers.
**Status:** 107 files force-added (6.5 MB); two artifacts exempted with
reasons; new gate `tools/check_clone_integrity.py`. No metric, claim, status
label, or verdict moved; no GPU was used.

---

## 1. The defect

`verification_outputs/` is listed in `.gitignore` (line 64). Its contents reach
the repository only through ad-hoc `git add -f`, and
[`docs/audit/docs-inventory-2026-10-21.md`](docs-inventory-2026-10-21.md) §150
already recorded the consequence: *"There is no written rule for which subset
gets force-added; the tracked/untracked split (41,560 vs …) is arbitrary."*

The paper's evidence chain is built on that split. `paper-data/<cell>/<file>`
and `docs/headline-evidence/<cell>/<file>` are **symlinks** into
`verification_outputs/`. Git stores a symlink as its target string, so the link
survives a clone; the target only survives if that path was force-added.

It was not, for 29 of them.

Every existing gate passed anyway, because every existing gate runs in the
working tree, where the targets exist. The failure was invisible from the only
machine that could see it.

## 2. How it was found

A detached worktree at `HEAD` (`git worktree add --detach /tmp/clonetest HEAD`)
is an exact clone: tracked files only, no gitignored artifacts. Running the six
package-integrity checkers there produced:

| Checker | Working tree | Clean worktree |
|---|---|---|
| `check_submission_manifest.py` | rc=0 | **rc=1** — `unknown=1 ledger_drift=1` (`supplementary_bundle.zip` missing) |
| `check_submission_links.py` | rc=0 | **rc=1** — `absent=21 elsewhere=1 ok=220` |
| `check_data_integrity.py` | rc=0, 15 dirs | rc=0, **14 dirs** (`wave349-r1-3seed-gpu/` entirely untracked) |
| `check_doc_links.py` | rc=0, `broken=2` (both frozen) | **rc=1** — `broken=30 missing=27` |
| `check_paper_data_manifest.py` | rc=0, `56/56 110/110` | **rc=1** — `bad=7 source_bad=20` |
| `check_artifact_hashes.py` | rc=0 | rc=0 |

Four of six went red. The 21 absent submission links are the ones a reviewer
clicks first: `tnnls_submission/cover_letter.md`, `data_availability.md`,
`tables.md`, `submission_checklist.md`.

Separately, a symlink walk of the clone found **46 dangling links**: 29 into
`verification_outputs/` and 17 from `paper-figures/*` into `site/`.

## 3. What was added

107 files, 6.5 MB — 105 under `verification_outputs/`, two under `data/`. All
but one are artifacts the documentation already cites; the exception is a
placeholder README that keeps an intentionally-empty directory resolvable.
Grouped by the surface that cites them (a file can appear in more than one
group, so the groups overlap and do not sum to 107):

- **30 cited by `docs/paper-evidence.json`** — the register behind
  `docs/PAPER-EVIDENCE.md`. Four paths: `gap55-r1-nfe150-n1000/` (24 files),
  `flowmol3_fine_nfe_q4_2026.json`, `gap80-r5a-restart/` (4 files), and
  `wave247-p5-r5b-nfe-sweep-aggregate.json`.
- **13 cited by the submission package** — `wave230-p2-real-4arm-per-record.csv`,
  `wave234-p2-tost.csv`, `wave234-p5-meta-analysis.csv`,
  `wave234-p5-meta-summary.json`, `wave234-p6-non-inferiority.csv`,
  `wave235-p1-r5b-fix.{csv,json}`, `lineageflow_real_ckpt_forward_q4_2026.json`,
  `g1_deep_dive_q3_2026.json`, `gap84-cap-frontier/frontier_w16e1_5k.json`,
  `wave189-p2-post-cd70821-combined.json`, `wave351-p3-thm5-numerical/lipschitz_estimate.json`,
  `wave247-p3-r5b-n1000-n1/summary.json`.
- **17 cited by `docs/CLAIMS.md` and `docs/METRIC_LEDGER.md`** —
  `wave195-p{2,3,4}-*`, `wave196-p{2,4}-*`, `wave197-p3-root-cause-analysis.json`,
  `wave208-p{1,2}-*`, `wave225-p3-r3-cross-seed.{csv,json}`,
  `wave189-p2-post-cd70821-{two_moons,eight_gaussians}.json`.
- **The R2/R3/R5a/R5b/K7 `paper-data` targets** — `flowmol3_n1000_*_q4_2026.json`
  (6 files), `wave218-p3-kanzi-{baseline,framework}-n1000.log`,
  `novelty_pctid_w166_q3_2026/{baseline,framework}/n1000_full_loose.m8`,
  `wave214-p2-kanzi-*`, `wave88_kanzi_n1000_baseline/`,
  `wave206-p6-honest-negative-curve.json`, `noise_injection_*`,
  `wave189-p2-sota-2d-rerun/` (12 CSVs), `baseline_comparison_q4_2026.json`,
  `kanzi_nfe_scan_q4_2026.json`, `lineageflow_v2_aggregated_q4_2026.json`,
  `wave73_phase2_tier1_speedup.json`.
- **Three whole directories that were untracked** — `wave189-p2-sota-2d-rerun/`
  (12 files), `wave349-r1-3seed-gpu/` (3 files, cited by eight audit records),
  `novelty_pctid_w166_q3_2026/{baseline,framework}/`.
- **Two small data files** — `data/mnist_fm.npz` (22,481 bytes, the
  smoke-materialised MNIST FM checkpoint whose exact sha256
  `ded1fa70…f371634` CLM-059 quotes in its text; a clone that lacks the file
  cannot verify the digest it is being asked to trust) and
  `data/freqflow_ckpt/README.md` (2.4 KB — the file CLM-056 links to twice,
  recording that the FreqFlow checkpoint has no public release).
- **One placeholder** — `verification_outputs/wave199-p2-lineageflow-n1000/README.md`.
  `docs/CLAIMS.md` links to that directory and says in the prose that it is
  empty ("N=1000 sweep killed for CPU wallclock"). Git cannot track an empty
  directory, so the link could never resolve on a clone. The README restates
  the reason and points at where the live LineageFlow evidence actually is.

## 4. What was exempted, and why

Two artifacts are cited but deliberately not shipped. Both are now named in the
checker with the reason, so the exemption is reviewable rather than silent.

**`tnnls_submission/supplementary_bundle.zip`** — 148 MB archive built from
`paper-data/` plus the sidecar `SHA256SUMS`; `.gitignore` keeps it out by
design. `check_submission_manifest.py` now reports the row as
`packaging-output` instead of `MISSING`, and the row still records the hash the
packaging step must reproduce.

**`data/flowmol3/weights_real/checkpoints/last.ckpt`** — 68 MB model
checkpoint. No weight file is tracked anywhere under `data/`
(`git ls-files data | grep -E '\.(ckpt|pt|safetensors|bin)$'` returns nothing),
and committing this one would make the repository the distribution channel for
the weights. `check_submission_links.py` gained a `KNOWN_ABSENT` entry; the
frozenset had been declared and left empty since it was written.

## 4a. The register itself was red

`tools/paper_evidence.py --check` verifies that every cell in
`docs/paper-evidence.json` names an artifact that exists *and* contains the
number it quotes. It is the gate behind `docs/PAPER-EVIDENCE.md`, the single
cell-level evidence register the paper-work skill tells every agent to read
first.

It was wired nowhere. Not in `todo.json`'s `gate_chain`, not in CI, not in
`verify_submission_readiness.py`. On the clean worktree it exited 1 with six
failures across four of the eleven cells:

```
FAIL R1.point.artifact: path does not exist: verification_outputs/gap55-r1-nfe150-n1000/seed42/upstream_eval.json
FAIL R1.point: quote not found in artifact or audit: '275.0'
FAIL R3.frontier.artifact: path does not exist: verification_outputs/flowmol3_fine_nfe_q4_2026.json
FAIL R5a.point.artifact: path does not exist: verification_outputs/gap80-r5a-restart/aligned/r5a_restart.json
FAIL R5a.point: quote not found in artifact or audit: '"p": 0.287282358018507'
FAIL R5b.frontier.artifact: path does not exist: verification_outputs/wave247-p5-r5b-nfe-sweep-aggregate.json
```

The two `quote not found` failures are downstream of the missing artifacts —
the quote lives inside the artifact that was not there. Adding the four paths
(4.1 MB) turns all six green, in the working tree and in the clone.

The checker is now entry 14 of the gate chain, immediately after
`check_docs_against_code.py`.

## 5. The new gate

`tools/check_clone_integrity.py` walks `git ls-files --stage` for mode
`120000`, reads each target blob, and resolves it. Three outcomes are
acceptable:

| Status | Meaning |
|---|---|
| `ok` | target present in the working tree |
| `build-output` | target is under `site/`, which `mkdocs build` regenerates — accepted **only** if the source file it copies still exists |
| `exempt` | named in `KNOWN_DANGLING` with a reason (currently empty) |

Anything else is `broken` and fails the run. Locally: `ok=139`. In a clean
clone: `ok=122 build-output=17 broken=0`.

Verified to catch a regression: deleting
`verification_outputs/wave73_phase2_tier1_speedup.json` from the clone flips it
to `broken=1`, rc=1.

`tests/test_tools/test_clone_integrity.py` pins the gate (5 tests): no dangle,
every exemption names a tracked link, every `build-output` link has a source,
`_build_source` rejects a fabricated figure name, and nothing under
`paper-data/` may dangle.

## 5a. The gates are now in CI

All eight checkers existed and none of them ran in CI — which is how the
surfaces they cover drifted in the first place. `ci.yml` gains a seventh gate,
`package and evidence integrity`, in the `lint-types` job: the register check
plus the seven `tools/check_*.py` gates, in the same order as `todo.json`'s
`gate_chain`. They are stdlib-only and read tracked files, so the job needs no
install beyond Python and the whole step takes under 20 s.

Two related corrections in the same file:

* The header and `CONTRIBUTING.md` §2 both said "six pre-merge gates". Now
  seven, with row 7 naming the command and what it checks.
* The `Strip untracked symlink targets from docs/` step (Wave 273 P2) was added
  because two `docs/headline-evidence/` symlinks pointed at untracked
  artifacts. Both targets are force-added now, so the step is a no-op; its
  comment says so and points at `check_clone_integrity` as the gate that fails
  loudly instead of silently deleting the link.

The `data/` tree is still untracked by design (`.gitignore:9`), so CI has no
vendored upstream and no weights. Every gate above was run in a tracked-only
worktree (`/tmp/clonetest`) to confirm that this does not turn any of them red:
the one deliberate absence — the 68 MB FlowMol3 checkpoint — is exempted, and
the check reports `absent=1 ok=241`.

## 6. Gates

| Gate | Working tree | Clean worktree (after) |
|---|---|---|
| `check_submission_manifest.py` | rc=0 — `rows=26 unknown=0 ledger_drift=0` | rc=0 — same |
| `check_submission_links.py` | rc=0 — `links=242 ok=242` | rc=0 — `links=242 absent=1 ok=241` |
| `check_data_integrity.py` | rc=0 — 15 dirs, 703 files | rc=0 — 15 dirs, 703 files |
| `check_doc_links.py` | rc=0 — `checked=1154 broken=2` (frozen) | rc=0 — same |
| `check_paper_data_manifest.py` | rc=0 — `56/56 110/110` | rc=0 — `56/56 110/110` |
| `check_artifact_hashes.py` | rc=0 — `citations=8` | rc=0 — `citations=8` |
| `check_clone_integrity.py` | rc=0 — `ok=139` | rc=0 — `ok=122 build-output=17` |
| `paper_evidence.py --check` | rc=0 — 11 cells | rc=0 — 11 cells (was rc=1, 6 failures) |

Fourteen gates, all green in both trees. The clone's results are now identical
to the working tree's. That
equivalence is the point: a gate that only passes on the machine that produced
the artifacts is not a gate.

## 7. What this does not fix

`data/` as a whole is untracked (`.gitignore:9`), so a clone has no vendored
upstream trees and no model weights. That is a deliberate size decision, and
`tnnls_submission/data_availability.md` already pins each upstream to a commit
hash for re-cloning. The difference here is that the *evidence* — the numbers
the paper reports — now ships with the repository, while the *inputs* needed to
regenerate it are pinned rather than vendored.

The 17 `paper-figures/*` → `site/` links still require `mkdocs build` before
they resolve. That is unchanged and is now recorded rather than assumed.
