# GAP-96 pre-registration — making room without removing a claim

**Status:** PLANNED, and unblocked on the measurement side. GAP-90 returned a
number on 2026-10-27 and the read-only build audit is done (§7, 2026-10-31).
The cut itself edits the frozen manuscript and remains user-gated.

---

## 1. The constraint, measured

The 2026-10-27 build is **12 pages, 0 overfull, 0 undefined references**. The
packaging pass already spent the slack it created: Figure 1 (2×2 frontier,
`0.88\textwidth`), the κ table, the frontier-coverage paragraph, and the new
§VI-D all went in, and two subsections were compressed to pay for them (the
site-aware cache, 226 → ~70 words; the "why the framework's identity is the
typed contract" subsection, 78 words, deleted).

Where the 12 pages currently go, from the compiled PDF:

| block | pages | words |
|---|---|---:|
| I Introduction + II Related work | 1–3 | 1,284 |
| III Framework | 3–4 | 2,086 |
| IV Scheduler family | 4–5 | 317 |
| V Adapter protocol | 6–7 | 400 |
| VI Framework properties | 7–8 | 987 |
| VII Empirical results | 8–11 | 3,233 |
| VIII Reproducibility | 11–12 | 428 |
| IX Limitations + X Conclusion | 12 | 386 |

Word counts refreshed 2026-10-31 against the current `.tex` (§7); page ranges
are from the 2026-10-27 build and were not re-derived.

**The earlier premise of this gap is stale.** It said the engineering surface
occupies "about three pages"; the measured figure is III–VI ≈ 5.5 pages (3,788 words) plus
VIII ≈ 1.5. Most of that is not padding — III-B carries the mechanism the paper
is about — so the cut list below is ordered by *what a TNNLS reviewer reads as
systems work*, not by word count alone.

## 2. What has to fit, and how much it costs

| item | pages |
|---|---:|
| GAP-90 dose figure (five optimizer-step levels, one panel) | ≈0.35 |
| GAP-90 second paragraph in §VII | ≈0.15 |
| GAP-94 frontier (if authorised) | ≈0.35 + a table row |
| GAP-93 outcome (one paragraph or one table) | ≈0.15 |

Worst case ≈ 1 page of new material. The target is therefore not "compress by
a third" but "recover one page without losing a claim".

## 3. The cut list, in order

Each item names the surface, the compression, and what must survive verbatim.

1. **III-A Typed-contracts framework architecture (739 words; 779 when this
   list was written).** Keep the
   component diagram, the six-step round loop, and every identifier. Move the
   per-component prose into a table of `component → responsibility → file`.
   *Survives:* every class and module name, every measured claim.
   *Recovers:* ≈0.3 page.
2. **VII-B Per-cell status (1,258 words; 959 when this list was written, and
   still the largest block in the paper).** It restates what Table III already
   carries. Keep the one sentence per
   cell that a reader cannot get from the table (the scope boundary), drop the
   restatement of the number. *Survives:* every status label and every scope
   boundary. *Recovers:* ≈0.35 page.
3. **VIII Reproducibility (428 words over six subsections).** Collapse to one
   table: gate → command → artifact → expected output. *Survives:* every gate
   name, every command, every SHA. *Recovers:* ≈0.3 page.
4. **V Adapter protocol (400 words).** Merge the minimum protocol surface and
   the vendor-friendly claim into one subsection. *Recovers:* ≈0.15 page.
5. **VI-A Mechanism-to-metric transfer (414 words).** This is load-bearing
   argument, not engineering. **Do not cut** unless items 1–4 fall short.

Items 1–4 together recover ≈1.1 page, which covers the GAP-90 material with
margin and covers GAP-94 without touching VI-A. Item 2 has grown 31% since
that estimate was made and item 1 has shrunk 5%, so the total is still about
right but the ordering matters more than it did.

## 4. Acceptance

* 12 pages held; **0 overfull hbox, 0 overfull vbox, 0 undefined references**
  (`grep -c Overfull paper-A-final.log` = 0 and a clean second pass). The
  2026-10-31 build already meets this (§7), so the check is "still true after
  the cut", not "make it true".
* **No claim, number, or status label removed.** Verified by diffing the
  markdown's `CLM-` set and the numbers cited in the manuscript against the
  pre-compression build — see §7 for why the `.tex` has no `CLM-` identifiers
  to diff.
* `python tools/check_claims_consistency.py` exits 0.
* `PYTHONPATH=. python tools/check_docs_against_code.py` still resolves every
  identifier that survives.
* The GAP-90 figure and the κ table are both present.
* `docs/drafts/paper-A-final.md` stays in sync with the `.tex` on the surfaces
  named in §7 (abstract, every number, every status label), not as whole files.

## 5. Ordering

Compressing before GAP-90 runs would spend the recovered space on nothing and
then have to be redone once the figure's real size is known. This gap therefore
runs **after** GAP-90 returns a number, and its first step is to typeset the
figure at its final size and measure, not to cut to a target.

## 6. Unresolved

1. **The 12-page limit itself.** If TNNLS permits a longer submission with the
   overflow as supplementary, the compression is unnecessary. This was not
   checked; the current build targets 12 pages because that is the number the
   submission package is built around, not because the venue was verified to
   require it.
2. **Cutting VII-B risks losing the per-cell caveats** that make the honest
   status labels legible. The acceptance clause is a diff against the old
   build, but a diff cannot tell whether a caveat became unreadable.

## 7. Read-only build audit (2026-10-31)

Run before any cut, on the tree at `8e891729`. Nothing was edited and nothing
was re-typeset in place: the `.tex` was copied to a scratch directory with its
two figure dependencies and built there.

**The build is clean.** `latexmk -pdf` exits 0 in an empty directory;
`pdfinfo` reports 12 pages; the log carries 0 `Overfull \hbox`, 0 `Overfull
\vbox`, 0 undefined references and 0 multiply-defined labels. The 143
`Underfull \hbox` warnings are loose interword spacing, not overflow.

**The shipped PDF is current.** `pdftotext` of the committed
`docs/drafts/paper-A-final.pdf` and of the fresh build are identical after
whitespace normalisation, so the PDF in the tree came from the `.tex` in the
tree and needs no regeneration before a cut.

**No negative-space hacks.** There is no `\vspace{-...}`, no
`\enlargethispage` and no `\linespread`. The only fit-forcing is `\resizebox`
on two figures (the architecture figure at `0.98\textwidth`, the mechanism
TikZ at `\columnwidth`), `\resizebox` on `tab:mechanism-evidence`, and
`\small` / `\footnotesize` on tables. If items 1–4 recover their page, those
three `\resizebox` calls can be dropped and the tables set at body size.

**The §3 word counts are stale for section VII.** Recounted from the current
`.tex`, keeping command arguments so caption and table text are counted:

| block | §3 said | measured now | delta |
|---|---:|---:|---:|
| III total | 2,152 | 2,086 | −3% |
| III-A typed-contracts architecture | 779 | 739 | −5% |
| V adapter protocol | 396 | 400 | +1% |
| VI-A mechanism-to-metric transfer | 422 | 414 | −2% |
| VII total | 2,701 | 3,233 | **+20%** |
| VII-B per-cell status | 959 | 1,258 | **+31%** |
| VIII reproducibility | 400 | 428 | +7% |

Everything outside VII reproduces within a few percent. VII grew because the
κ table, the frontier-coverage paragraph and the dose material were inserted
there after this record was written. The consequence is a reordering, not a
new plan: VII-B is now the largest single block in the paper at 1,258 words,
and III-A is 5% smaller than budgeted, so the recovery attached to item 1
should be read as optimistic and the recovery attached to item 2 as
understated.

**Three acceptance clauses cannot pass as written.**

- "`docs/drafts/paper-A-final.md` stays in sync with the `.tex`" has no
  operational definition, and is already false in a narrow sense: the abstract
  is word-identical, but the markdown carries nine Index Terms and the `.tex`
  carries five. The clause should name the surfaces that must match — abstract,
  every number, every status label — rather than the two files as wholes.
- "Diff the `CLM-` identifiers against the pre-compression build" compares 11
  identifiers in the markdown against 0 in the `.tex`: `CLM-NNN` appears only
  in the markdown's bibliography addendum, never in the typeset body. The
  clause should read "the markdown's `CLM-` set is unchanged", which is the
  property it is trying to protect.
- "`python docs/check_docs_against_code.py`" names a path that does not exist.
  The checker is `tools/check_docs_against_code.py`, and CI invokes it with
  `PYTHONPATH=.`.
