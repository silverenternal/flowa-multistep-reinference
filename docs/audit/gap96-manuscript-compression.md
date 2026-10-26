# GAP-96 pre-registration — making room without removing a claim

**Status:** PLANNED. Blocked on GAP-90 (the figure that needs the room) and on
GAP-92's table (already inserted). Nothing here runs before those exist.

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
| I Introduction + II Related work | 1–3 | 556 + 656 |
| III Framework | 3–4 | 1,940 |
| IV Scheduler family | 4–5 | 311 |
| V Adapter protocol | 6–7 | 390 |
| VI Framework properties | 7–8 | 876 |
| VII Empirical results | 8–11 | 2,390 |
| VIII Reproducibility | 11–12 | 395 |
| IX Limitations + X Conclusion | 12 | 379 |

**The earlier premise of this gap is stale.** It said the engineering surface
occupies "about three pages"; the measured figure is III–VI ≈ 5 pages plus
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

1. **III-A Typed-contracts framework architecture (779 words).** Keep the
   component diagram, the six-step round loop, and every identifier. Move the
   per-component prose into a table of `component → responsibility → file`.
   *Survives:* every class and module name, every measured claim.
   *Recovers:* ≈0.3 page.
2. **VII-B Per-cell status (959 words).** This is the largest block in the
   paper. It restates what Table III already carries. Keep the one sentence per
   cell that a reader cannot get from the table (the scope boundary), drop the
   restatement of the number. *Survives:* every status label and every scope
   boundary. *Recovers:* ≈0.35 page.
3. **VIII Reproducibility (395 words over six subsections).** Collapse to one
   table: gate → command → artifact → expected output. *Survives:* every gate
   name, every command, every SHA. *Recovers:* ≈0.3 page.
4. **V Adapter protocol (390 words).** Merge the minimum protocol surface and
   the vendor-friendly claim into one subsection. *Recovers:* ≈0.15 page.
5. **VI-A Mechanism-to-metric transfer (422 words).** This is load-bearing
   argument, not engineering. **Do not cut** unless items 1–4 fall short.

Items 1–4 together recover ≈1.1 page, which covers the GAP-90 material with
margin and covers GAP-94 without touching VI-A.

## 4. Acceptance

* 12 pages held; **0 overfull hbox, 0 overfull vbox, 0 undefined references**
  (`grep -c Overfull paper-A-final.log` = 0 and a clean second pass).
* **No claim, number, or status label removed.** Verified by diffing the
  `CLM-` identifiers and the numbers cited in the manuscript against the
  pre-compression build.
* `python tools/check_claims_consistency.py` exits 0.
* `python docs/check_docs_against_code.py` still resolves every identifier that
  survives.
* The GAP-90 figure and the κ table are both present.
* `docs/drafts/paper-A-final.md` stays in sync with the `.tex`.

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
