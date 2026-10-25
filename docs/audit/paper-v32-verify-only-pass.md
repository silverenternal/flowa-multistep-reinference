# Paper v3.2 — VERIFY-ONLY pass

**Date:** 2026-10-25
**Author:** paper-refresh agent (USER AUTHORIZED, NO PUSH)
**Scope:** `docs/audit/paper-v32-data-refresh.md` §3 rows **1, 2, 3, 4, 5, 7**.
Rows 6, 8, 9, 10 are REWRITE / REHASH and wait on GAP-84, so they are not
touched here.
**Rule applied:** VERIFY-ONLY — re-read the artifact, recompute the printed
digits, change **nothing**. No frozen surface (`docs/CLAIMS.md`,
`docs/CONSOLIDATED_RESULTS.md`, `docs/drafts/paper-A-final.*`,
`tnnls_submission/**`) was edited by this pass.

---

## 0. Result in one table

| # | § | table | digits | citation | verdict |
|---|---|---|---|---|---|
| 1 | 3.4.2 | capability-token SHA-256 | PASS | PASS | **PASS** |
| 2 | 3.5.1 | ledger SHA-256 chain (3 files) | PASS | **recipe command fails** | **PASS with a prose defect (F1)** |
| 3 | 3.10 | causal mechanism chain | RMSD PASS / round-count clause **FAILS** | **wrong source pointer** | **FAIL as written (F2)** |
| 4 | 5.3 | five adapter implementations | PASS | **3 of 5 vendored paths 404** | **PASS with broken links (F3)** |
| 5 | 6.1 | mechanism-to-metric transfer | no number | — | nothing to verify |
| 7 | 7.7 | NFE-matched boundary (4 rows) | PASS 4/4 | PASS | **PASS** |

---

## 1. Observed facts

### 1.1 Row 1 — §3.4.2 capability token (PASS)

```
$ cd verification_outputs/wave355-capability-token-example
$ wc -c synthetic_continuous_capability_token.json      → 762
$ sha256sum synthetic_continuous_capability_token.json
584f8e02c3eda4fde2bfe1f65651cca6ec2cb9063eea42c70ce15c0ae8b619c8
```

Paper: 762 B, `584f8e02…b619c8`. Byte count and digest both match. The inner
pretty-printed digest `a7e9620e…` is a claim about a re-serialisation, not a
file on disk; it is not re-derived here and no number depends on it.

### 1.2 Row 2 — §3.5.1 ledger chain (digits PASS, recipe FAILS)

```
$ wc -c seed42_manifest.json seed44_manifest.json SHA256SUMS  → 805 / 805 / 2642
$ sha256sum seed42_manifest.json
0861e4b156c1e64078f56561c093dfe10e22542aa9740efbb8f4a61d76552ce7
$ sha256sum seed44_manifest.json
cc4390bc4a02799dc2add0ad251e7e5ece08e29f1ec2322c8c6f28f813cf44ed
$ sha256sum SHA256SUMS
28aafe1c95195c0a2daa727150e4ea42651daa49cd5872443a81b88cfed15be2
$ printf '%s  %s\n%s  %s\n' <seed42 hash> seed42_manifest.json \
      <seed44 hash> seed44_manifest.json | sha256sum
206d69942a3325116c9a86062c3bb0f41302316fee48d6868d24bec50cc27cd8
```

All five printed values — two manifests, the aggregator, and the inner column
digest — reproduce exactly.

**F1.** The paper's recipe prints

```bash
sha256sum --check SHA256SUMS     # both manifests must print OK
```

`SHA256SUMS` is a **markdown document** (header, per-seed result table,
narrative, cross-references) with the two manifest hashes in a markdown table
at lines 19–20 — not a `sha256sum`-format file. Running the printed command
returns:

```
sha256sum: SHA256SUMS: no properly formatted checksum lines found
```

and exits 1. The *chain* is intact; the *command a reviewer is told to run*
does not execute. This is a reproducibility-surface defect, which is the one
class the paper's §3.5 argument cannot afford.

### 1.3 Row 3 — §3.10 mechanism chain (FAIL as written)

The table has four rows. Two are checked here.

**(a) Kanzi RMSD `0.9020 → 0.8798 Å` at N=1000 — PASS.** Sourced at
`docs/audit/kanzi/p3-kanzi-n1000-framework-inv-proj.md:62` (Wave 88 baseline,
n=1000, seed 0) and `:6` (framework mean 0.8798). The checklist points this row
at `docs/audit/mechanism-core-driver.md`; that file is a **reading note with no
numbers** (`grep 0.9020` → no match). The digits are fine; the pointer is not.

**(b) "fixed-NFE round-count study: the gain persists for
`n_rounds ∈ {1,2,3,5,7}` at NFE=100" — FAILS.** The only artifact in the repo
with that grid is `docs/audit/algorithm_4arm/p4-aggregate.md` (Wave 184 P3/P4,
NFE=100, 12 cells):

| model | arm | n_rounds | pLDDT | ΔpLDDT | ΔscPPL |
|---|---|---:|---:|---:|---:|
| lineageflow | baseline | 1 | 41.18 | — | — |
| lineageflow | framework | 1 | 41.99 | +0.81 | −4.00 |
| lineageflow | framework | 2 | 41.99 | +0.81 | −4.00 |
| lineageflow | framework | 3 | 41.99 | +0.81 | −4.00 |
| lineageflow | framework | 5 | 41.99 | +0.81 | −4.00 |
| lineageflow | framework | 7 | 41.99 | +0.81 | −4.00 |
| kanzi | baseline | 1 | 57.41 | — | — |
| kanzi | framework | 1 | 55.78 | **−1.63** | −1.83 |
| kanzi | framework | 2 | 55.25 | **−2.16** | −2.78 |
| kanzi | framework | 3 | 51.62 | **−5.79** | −3.02 |
| kanzi | framework | 5 | 56.72 | **−0.69** | −4.37 |
| kanzi | framework | 7 | 54.61 | **−2.81** | −2.91 |

Two separate problems:

1. **Kanzi pLDDT regresses at all five round counts** (−0.69 to −5.79). The
   unqualified clause "the gain persists" is false on that axis.
2. **The lineageflow rows are inert by construction**, not by measurement: the
   same audit states at §2.1 that the synthetic lineageflow adapter has no
   `profile_residual_fn`, so `n_rounds` never reaches the trace and all five
   cells emit the **identical FASTA**
   (`67d871ba…b416a3`). A constant +0.81 across rounds is a
   constant-β fallback, not evidence that "the gain persists across rounds".

The clause is defensible only when scoped: it holds for lineageflow
pLDDT/scPPL and for kanzi **scPPL**, and it does not hold for kanzi pLDDT.
The underlying audit already states it that way —
`docs/audit/engineering/p5-ground-truth-corrections.md:166` writes
"−3.99 scPerplexity … byte-stable across n_rounds ∈ {1, 2, 3, 5, 7}" for
lineageflow — so §3.10 lost the scope in compression, it did not invent one.

### 1.4 Row 4 — §5.3 five adapters (files PASS, 3 links 404)

All five adapter files exist and are non-empty. Three of the five "vendored
code path" cells do not resolve in this repo:

| paper path | actual path | state |
|---|---|---|
| `data/lineageflow_upstream/` | same | OK |
| `data/kanzi/upstream/` | `data/kanzi_upstream/` | **404** (different layout) |
| `data/flowmol3/repo/` | `data/FlowMol3/repo/` | **404** (case: `F` vs `f`; the directory is otherwise correct) |
| `data/cifar/` | `data/cifar10_rf.pth`, `data/rectified_flow_cifar10.pth` | **404** (no `cifar/` directory) |
| `data/mnist_fm.npz`, `data/mnist_fm/production.ckpt.npz` | same | OK |

The "zero-line edits: YES (verified)" column is unaffected — this finding is
about the clickable path, not about the claim.

### 1.5 Row 7 — §7.7 NFE-matched boundary (PASS 4/4)

Recomputed from the four artifacts, `Δ = framework/baseline − 1`:

| row | baseline FID | recomputed Δ range | paper | verdict |
|---|---:|---|---|---|
| `wave235-p1-r5b-fix.json` (rounds1) | 454.3853934 | −2.53% … −0.12% (4/4 negative) | −2.53% … −0.12% | PASS |
| `wave247-p3-r5b-n1000-n1/summary.json` | 48.4058511 | +0.33, +0.52, −0.49, −0.32 (2 up, 2 down) | two improve, two regress | PASS |
| `wave225-p7-r5b-reduced-rounds.json` | 458.5809343 | +9.77% … +16.62% (4/4 positive) | +9.77% … +16.62% | PASS |
| `wave206-p6-honest-negative-curve.json` | 83.0866 | +24.46% … +30.65% | +24.46% … +30.65% | PASS |

Sample sizes and round counts also match (200/1, 1000/1, 200/2, 500/20).

---

## 2. Interpretation

* **Rows 1 and 7 are clean.** Nothing to do, no prose change.
* **Row 2's numbers are clean; its recipe is not.** A reviewer who runs the
  printed command sees an error, not a mismatch — which reads as a broken
  artifact rather than a typo. Highest-value prose fix in this pass.
* **Row 3 is the only substantive finding.** The mechanism table is the
  paper's organizing claim; one of its four evidence cells overstates a
  measured result. The fix is a scope, not a retraction: state the metric and
  the model the study actually covers.
* **Row 4's links are cosmetic but visible.** Three dead paths in a table
  whose column is titled "Vendored code path" invites the reader to conclude
  the vendoring is not there.

None of these is a number change, so none of them touches a claim status.

---

## 3. Unresolved

1. Whether the "fixed-NFE round-count study" clause in §3.10 was intended to
   cite a *different* artifact that no longer exists. A repo-wide grep for the
   grid `{1,2,3,5,7}` finds only the Wave 184 ablation above; if another study
   exists outside the repo, the pointer must be supplied by the author.
2. §6.1 has no number and no artifact, so "VERIFY-ONLY" is vacuous there.
3. Rows 6/8/9/10 remain blocked on GAP-84, as recorded in the checklist §9.3.

---

## 4. Smallest next action per finding

| finding | action | surface | when |
|---|---|---|---|
| F1 | replace the `sha256sum --check` line with the two `sha256sum <file>` invocations that actually verify the chain (or emit a real `SHA256SUMS.check` file) | `docs/drafts/paper-A-final.md` §3.5.1 + `tnnls_submission/` mirror | with the §7 rewrite, one edit |
| F2 | scope the clause to "lineageflow pLDDT/scPPL and kanzi scPPL" **or** drop it; re-point the row's source to `kanzi/p3-kanzi-n1000-framework-inv-proj.md` | §3.10 | needs the author's call on which artifact was intended (§3.1) |
| F3 | update three paths to `data/kanzi_upstream/`, `data/FlowMol3/repo/` (case), `data/cifar10_rf.pth` | §5.3 | mechanical, with the §7 rewrite |
| — | none | rows 1, 5, 7 | — |

F2 is the only item that needs a decision before the v3.2 tag. F1 and F3 are
mechanical once that decision is made.
