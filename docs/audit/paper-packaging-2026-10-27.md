# 2026-10-27 — Manuscript packaging pass (P1–P5)

**Increment:** `paper-packaging-2026-10-27`
**Scope:** documentation and figure only. No sweep was launched, no model was
sampled, and **no measured number was changed**. Every quantitative statement
in the repackaged front matter is transcribed from an artifact that already
existed on disk before this pass.

**Trigger:** user instruction — *"现在就先想想怎么包装论文吧"* — resolved through
a two-question menu to **P1–P5 全做** and **标题改为 "Re-Inference Control"**.

---

## 1. Diagnosis (what was wrong with the packaging)

Four defects, each with a location:

1. **The abstract buried the finding.** 193 words, of which ~110 were a
   mechanism inventory (adapters / typed policies / scheduler / hash-linked
   bundle). The single number (`12.75%`) appeared after word 150 and the
   closing sentence was generic.
2. **The result was not a contribution.** The contribution list had four
   items: reformulation, identity, *typed integration with five adapters and
   zero edits to vendored code*, and *an eleven-cell evaluation organized
   around mechanism isolation*. Three were engineering properties; the
   headline evidence was filed as an evaluation sub-clause.
3. **The strongest quantitative result had no figure.** Figure 1 was the
   architecture diagram, Figure 2 and Figure 3 were mechanism maps, and the
   seven-rung × four-checkpoint frontier existed only as one row of Table III.
4. **Table III was half disclaimer.** Three of four scope cells read
   `One valid seed; small effect`, `Direction-consistent, n.s. at N=1000`,
   `Ties on the other three checkpoints` — a reviewer scanning the table saw
   a mostly-negative result where the paper has three STRONG cells.

## 2. Observed facts

### 2.1 The claim the paper is now organised around

> Moving the control variable from the **step count** to the **round
> boundary** changes what a frozen sampler can reach: at equal NFE the map
> lies below the one-shot baseline at all seven rungs on the least-trained
> MNIST checkpoint (plateau −3.12 FID, −12.75%) and returns a tie on three
> better-trained checkpoints from the same training family.

This is a mechanism claim, not an inventory claim. It has the additional
property of making the TIE cells evidence rather than failure: the same lever
is bounded by how much the checkpoint leaves on the table.

**Explicit non-claim.** The four MNIST checkpoints differ in architecture and
training-set size as well as in training duration
(`docs/drafts/paper-A-final.tex`, Limitations). The monotone-in-training-
completeness reading is therefore stated as a four-point hypothesis, never as
a law, and the paper does not claim a within-checkpoint dose-response for it.

### 2.2 Changes applied

| # | Surface | Change |
|---|---|---|
| P1 | `docs/figures/fig_r5c_frontier.png` (new, 203323 B, SHA-256 `f677c9b6…`) | 2×2 matched-rung frontier, one panel per checkpoint, ±1 sd bands, plateau window shaded, plateau Δ annotated per panel |
| P1 | `tools/render_r5c_frontier_figure.py` (new) | reads `verification_outputs/gap84-mnist-frontier/frontier_input_*.json`; asserts each computed plateau Δ against the manuscript value (±5e-4) so artifact drift fails loudly instead of silently producing a disagreeing figure |
| P1 | `paper-A-final.tex` | new `figure*` as **Figure 1**, placed in §I; architecture diagram renumbers automatically (all references are `\ref`) |
| P2 | `.tex` / `.md` abstract | 193 → 167 words; five sentences: budget statement → claim → mechanism → numbers → checkpoint-conditional conclusion |
| P3 | `.tex` / `.md` contributions | 4 → 3 items; matched-budget evidence promoted to (ii); typed contracts + zero-line vendoring + replay merged into (iii) |
| P4 | `.tex` / `.md` introduction | six hedges removed from the intro; the 2.5–10× extrapolation disclosure retained in place (it is the one number a reader could misread as a speedup); the rest moved to §VII-E (`.tex`) / §7.5 (`.md`) |
| P5 | `.tex` Table III | scope column compressed to phrases; R5c row gains the absolute `(−3.12)` alongside `−12.75%` |
| — | `.tex` | ten `\label{sec:…}` added; the intro's cross-references are now `\ref`-driven instead of literal |
| — | title | "Geometry-Aware State-Intervention Reformulation for Frozen Flow-Matching Checkpoints" → **"Re-Inference Control for Frozen Flow-Matching Checkpoints"**; propagated to `MANIFEST.md`, `cover_letter.md` (subject + packaging note), `README.md`, `README.zh.md` (H1, Paper ID, BibTeX), `.tex` header |

### 2.3 Figure provenance

Every plotted value is read from
`verification_outputs/gap84-mnist-frontier/frontier_input_<ckpt>_evidence_driven.json`
(`baseline[rung].value` / `.units`, `framework[rung].value` / `.units`).
The plateau is the mean of the last two rungs, matching
`tools/frontier_report.py`. The renderer asserts:

| checkpoint | computed plateau Δ | manuscript value | match |
|---|---|---|---|
| `w16e1_5k` | −3.1206 | −3.1206 | yes |
| `w16e1_10k` | −1.0036 | −1.0036 | yes |
| `w16e1_60k` | +0.0150 | +0.0150 | yes |
| `production` | −0.0335 | −0.0335 | yes |

Two consecutive renders produce the identical SHA-256
(`f677c9b69a99f8f3be6617182c2290503040c18fd47bd4f0e44846395cc486f1`).

## 3. Interpretation

**What changed is salience, not evidence.** The old text and the new text
report the same eleven cells with the same numbers. The old text asked a
reviewer to infer the thesis from an eleven-row audit; the new text states it
in the title, the abstract, contribution (ii), and Figure 1, then uses the
audit as support.

**Why the claim sentence is the right one.** It survives the three objections
that the previous framing invited:

- *"You are buying quality with compute."* The comparison is at matched NFE,
  rung by rung, so the budget is held fixed by construction.
- *"Your strong result is a single lucky checkpoint."* The three better-trained
  checkpoints are reported in the same figure with the same rule, and the
  paper states the tie rather than hiding it.
- *"Your nulls show the method does not work."* The nulls are the other end of
  the same control variable, and R6 supplies an independent instance of the
  mechanism (spending the *same* budget on hard records: hard tier 3/3 wins,
  easy tier 3/3 regresses).

**Why the title change is safe.** "Geometry-aware" was never formalised in
the paper — it named the adapter's native-coordinate bridge, which the text
calls *native-state alignment*. "Re-inference control" names the object
(control of a re-inference loop) and the mechanism (the round boundary), both
of which the paper defines.

## 4. Gates

| gate | result |
|---|---|
| `python3 tools/check_claims_consistency.py` | `No drift detected` (61 ACTIVE / 0 PROVISIONAL / 2 DEPRECATED) |
| `python3 tools/paper_evidence.py --check` | `OK … 11 cells, all paths and quotes verified` |
| `pytest tests/test_paper_evidence.py -q` | 7 passed |
| `pytest tests/test_d4_regression_vectors.py -q` | 30 passed |
| `ruff check tools/render_r5c_frontier_figure.py` | All checks passed (after adding `strict=` to five `zip` calls) |
| `mkdocs build --strict` | exit 0 |
| `python3 tools/check_docs_against_code.py` | `OK: 3371 claims verified` |
| `pdflatex` ×2 | exit 0, **12 pages**, 0 overfull hboxes, 0 undefined references |
| number preservation (`pdftotext` counts) | `24.4839`×2, `21.3632`×2, `12.75`×8, `0.0377`×2, `0.559`×2, `0.8393`×3, `1.1211`×3, `1.0036`×2, `0.984`×2 |

Artifacts after the pass:

| file | bytes | words | SHA-256 |
|---|---|---|---|
| `paper-A-final.md` | 223739 | 27361 | `60d8ca0c8d4f8a193ee04922af7cde93089937328058b1c87c1ae37e6d3c52ed` |
| `paper-A-final.tex` | 73276 | — | `16a6c864d6dbcd5f638fbfbd747c9511b5ac5bd4cb8d51397a87df2f8a5d76e2` |
| `paper-A-final.pdf` | 613629 | — | `740b1d8ce49dcd84f0fc537e09110e13a1be562892a468440881878c06d58658` |

## 5. Unresolved

1. **P6 not executed.** `tnnls_submission/highlights.md` still carries the
   withdrawn Theorem 4 convergence-rate and Theorem 5 attenuation formulas as
   Highlights 2 and 3 in its historical list, and `cover_letter.md` still opens
   with three stacked errata banners before the pitch. Both are packaging
   liabilities that an editor sees; neither was in the selected scope.
2. **Six of seven R-level cells still lack a (quality, NFE) grid.** The
   packaging pass makes R5c's frontier the visual anchor, which sharpens the
   contrast with the cells that have only a point estimate. This is the same
   structural gap recorded in `docs/audit/paper-refresh-2026-10-27.md` §6.
3. **Page count is at 12 with the new figure.** The figure was set to
   `0.88\textwidth` to hold 12 pages; a further full-page figure would push to
   13.
4. **Four historical banners still name the old title** (`MANIFEST.md` Wave 384
   banner, `submission_checklist.md` Wave 384 note, `SUBMISSION_READINESS.md`
   G31/G38 rows, and the `docs/audit/wave38*` records). Each is a dated
   historical record and each is explicitly superseded by a 2026-10-27 banner
   at the top of its file, so they were left as-is rather than rewritten. The
   MANIFEST page-count history now carries four values (8 / 10 / 11 / 12)
   behind the current banner.
