# Wave 353 P4 — §7.7.1 Wave 183 finer-NFE ladder — figures 3-5 cross-reference (paper ADDITIVE)

**Date:** 2026-09-25
**Wave:** 353 P4
**Status:** READY_TO_COMMIT
**Trigger:** §7.7 currently cites the 16-cell Table B family (FlowA vs vanilla + Fast-DLLM + AB-Cache + LeDiFlow at NFE ∈ {50, 100}) but does NOT cross-reference the 3 Wave 183 finer-NFE ladder figures that exist at `verification_outputs/wave183-p4-figure-*.png`. The figures were generated in Wave 183 P4 (`verification_outputs/wave183-p4-aggregate.py`, 110 DPI matplotlib Agg backend, byte-stable) and the figure artefacts have been in the repo since Wave 183, but their PNG SHA-256 + size had never been recorded in the TNNLS submission `MANIFEST.md`. Wave 353 P4 closes this gap by adding a §7.7.1 paragraph that cross-references the 3 figures with their renderer, source CSV, and SHA-256 (additive — no number change in §7.7's 16-cell Table B family verdict).
**Scope:** Paper-only ADDITIVE cross-reference + MANIFEST SHA refresh + 3 new figure rows.

---

## Observed facts

### Inputs

- **Paper §7.7 current state (line 481):** "The head-to-head cell compares FlowA against `vanilla` + `Fast-DLLM` + `AB-Cache` + `LeDiFlow` on the R6 foldability axes at NFE ∈ {50, 100}. FlowA wins both metrics at both NFE settings vs all four baselines. The 16-cell Table B family is Bonferroni-significant at α = 0.003125 for the scPerplexity axis across all four baselines and NFE settings. The four-baseline roster exhausts the canonical training-free acceleration design space (parallel-decoding + cache-reuse + distribution-guided prior-shift + vanilla), and FlowA wins all four families at both NFE settings on both R6 metrics." — preserved verbatim.
- **Wave 183 P4 figures (3 PNGs at 110 DPI matplotlib Agg backend, byte-stable):**
  - `verification_outputs/wave183-p4-figure-pLDDT-finer.png` — 146117 bytes, sha256 `0ac80722b7063f4acf2f73880a99593a1d52da9307157def93c825c9f9f809a0`.
  - `verification_outputs/wave183-p4-figure-scPerplexity-finer.png` — 133574 bytes, sha256 `f590c0b8ac6b82a17e77b6a21e28aa07b140e659ef6daec963298d0efbdeb961`.
  - `verification_outputs/wave183-p4-figure-deltas-finer.png` — 144560 bytes, sha256 `1412578cc63add7a33b98d7c25be33a032febea69487ef3cdd683c28c510eb9f`.
- **Wave 183 P4 renderer:** `verification_outputs/wave183-p4-aggregate.py` — Plot 1 (pLDDT), Plot 2 (scPerplexity), Plot 3 (ΔpLDDT + ΔscPerplexity with gold-star kanzi sweet-spot markers); matplotlib 3.11.2, ruff-clean, matplotlib.use("Agg") backend (no GUI dependency).
- **Wave 183 P4 data source:** `verification_outputs/wave183-p4-aggregation.csv` — 36 rows × 7 cols (`model`, `nfe`, `arm`, `plddt`, `scperp`, `delta_plddt`, `delta_scperp`) — 2 models × 9 NFEs × 2 arms; 18 framework cells per arm.
- **Wave 183 P4 NFE ladder:** `[10, 25, 50, 75, 100, 150, 200, 300, 500]` — finer than the §7.7 2-point ladder `{50, 100}`; finer than the Wave 181 5-point ladder `{10, 50, 100, 200, 500}`.
- **Existing MANIFEST row 32 description pattern:** "Wave 349 ADDITIVE: §7.8 Figure 1 R5c regime curve ... + Wave 350 ADDITIVE: §6.6 Theorem 5 ... + §7.6.2 R5b `n_rounds` conditional grid figure (Wave 350 P4 ADDITIVE 2-panel figure ref) ..." — Wave 353 P4 extends this pattern with §7.7.1 Wave 183 finer-NFE ladder figures cross-reference.
- **CLM-051 (Wave 183 finer-NFE finding):** "framework wins both metrics at 10/18 (model,NFE) cells with both-models intersection at NFE=75 only" — the §7.7.1 paragraph cross-references CLM-051 for the unique kanzi sweet-spot at NFE=75.

### Outputs (verified)

- **§7.7.1 Wave 183 finer-NFE ladder — figures (Wave 353 ADDITIVE, no number change) paragraph inserted at line 485** of `docs/drafts/paper-A-final.md` — between §7.7 (line 481) and §7.8 (now line 493).
  - **Refines the §7.7 2-point ladder `{50, 100}` at 9 NFE values** `[10, 25, 50, 75, 100, 150, 200, 300, 500]` across the two protein-flow-matching models `lineageflow` (R6 protein, LineageFlow) and `kanzi` (R5 protein, Kanzi), producing 18 model-NFE cells per arm.
  - **3 figures cross-referenced with renderer + source + SHA-256:**
    - **Figure 3** — pLDDT finer NFE curve (left panel `lineageflow`, right panel `kanzi`; x-axis NFE log-scale; primary y-axis pLDDT baseline dashed vs framework solid; secondary y-axis `ΔpLDDT = fw − baseline` dotted-black).
    - **Figure 4** — scPerplexity finer NFE curve (same layout for the scPerplexity axis; lower scPerplexity = better).
    - **Figure 5** — `ΔpLDDT` + `ΔscPerplexity` (left `ΔpLDDT`, right `ΔscPerplexity`, both per-model with `lineageflow` blue + `kanzi` red, log-scale NFE, gold `*` markers at `kanzi` sweet spots).
  - **Two qualitative findings:**
    - **(a) Saturation boundaries** — `lineageflow` reaches `ΔpLDDT ≤ 0.5` at `NFE = 500` (the largest NFE in the ladder, marking framework-utility-saturation); `kanzi` has NO saturation boundary in `[10, 500]` because `ΔpLDDT` oscillates between positive and negative values across the ladder.
    - **(b) kanzi unique sweet spot at `NFE = 75`** — the only NFE in the 9-point ladder where `kanzi` framework WINS both metrics simultaneously: `ΔpLDDT = +2.123` (framework-WINS) AND `ΔscPerplexity = -4.759` (framework-WINS, lower is better). Cross-referenced to CLM-051.
  - **No number change in §7.7** — the 16-cell Table B family verdict ("FlowA wins all four baselines at both NFE = 50 and NFE = 100 on both R6 metrics") is preserved verbatim per Wave 268 strict-clean "no number change" rule. This §7.7.1 paragraph is ADDITIVE only.

- **TNNLS submission package MANIFEST.md** — 3 new figure rows + row 32 + row 33 + self-row refreshed with new SHAs:
  - row 37 (new): `../verification_outputs/wave183-p4-figure-pLDDT-finer.png` — 146117 bytes, sha256 `0ac80722b7063f4acf2f73880a99593a1d52da9307157def93c825c9f9f809a0`. Wave 353 P4 ADDITIVE Figure 3.
  - row 38 (new): `../verification_outputs/wave183-p4-figure-scPerplexity-finer.png` — 133574 bytes, sha256 `f590c0b8ac6b82a17e77b6a21e28aa07b140e659ef6daec963298d0efbdeb961`. Wave 353 P4 ADDITIVE Figure 4.
  - row 39 (new): `../verification_outputs/wave183-p4-figure-deltas-finer.png` — 144560 bytes, sha256 `1412578cc63add7a33b98d7c25be33a032febea69487ef3cdd683c28c510eb9f`. Wave 353 P4 ADDITIVE Figure 5.
  - row 32 (`docs/drafts/paper-A-final.md`): SHA `06a11c91cbd2f93bc5bc130076faf277b1ddb137582f2e17239cf065abf9d9ea` → `cc0c91d73ba816bde7784d8e5b17eb30761e60c2529555e45b5c8b262cefb518`, size 194468 → 220635 bytes (Wave 353 P4 §7.7.1 ADDITIVE).
  - row 33 (`docs/drafts/paper-A-final.pdf`): SHA `b160d75a2d66ec71e7ce94ed4734e30b5b149f39398847628c44efdda2e2b7c6` preserved at 305270 bytes (PDF NOT regenerated in this wave; the .tex file is hand-maintained and out of scope per Wave 268 strict-clean rule; the displayed SHA + size are pre-Wave-353 values; reviewer re-verifies with `sha256sum docs/drafts/paper-A-final.pdf`).
  - self-row (`MANIFEST.md`): SHA `ace34bc6977d2455abcbacd6178c57a704587d03434549391b9a9668005ac91f` → `81f7d3ef995d7292dc26e407eb613854d44b3337a7a69ade119eb2ff535ebf0f`, size 41858 → 45379 bytes (pre-row-23-edit SHA; post-edit SHA becomes `b7caa380697e63e224056823d4a7f8f7cc99cd89ce004fda7c5bf286c3fa942c` per the standard self-referencing SHA pattern documented at MANIFEST row 23).

### Verification gates (all PASS)

| Gate | Command | Result |
|---|---|---|
| Claims consistency | `python3 tools/check_claims_consistency.py` | **PASS** — 61 ACTIVE claims, 0 PROVISIONAL, 2 DEPRECATED, **No drift detected** |
| D.4 byte-stable regression | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | **30/30 PASS** in 7.20s |
| mkdocs strict | `mkdocs build --strict` | **EXIT 0** — doc built in 24.45s |
| 3-figure sha256 (Wave 183 P4 PNGs) | `sha256sum verification_outputs/wave183-p4-figure-*.png` | **PASS** — 3 unique SHAs recorded in MANIFEST rows 37/38/39; byte-identical to the on-disk PNGs |

---

## Interpretation

### What the §7.7.1 paragraph adds to the paper

§7.7 currently reports the 4-arm head-to-head at the 2-point NFE ladder `{50, 100}` with 16 cells (FlowA vs vanilla + Fast-DLLM + AB-Cache + LeDiFlow). §7.7.1 extends the head-to-head narrative to the 9-point finer-NFE ladder `[10, 25, 50, 75, 100, 150, 200, 300, 500]` across the two protein-flow-matching models `lineageflow` (R6 protein, the framework's headline-positive cell) and `kanzi` (R5 protein, the framework's headline-mixed cell). The §7.7.1 paragraph provides:

1. **Visual reference for the 18-cell finer-NFE ladder** — 3 figures, byte-stable, 110 DPI matplotlib Agg backend, already in the repo since Wave 183 (but never formally cross-referenced from the paper text). The 3 figures cover (a) the absolute pLDDT curve, (b) the absolute scPerplexity curve, and (c) the Δ-verdict curves with gold-star kanzi sweet-spot markers.
2. **Two qualitative findings that contextualize the 4-arm H2H verdict:**
   - **Saturation boundary** — `lineageflow` ΔpLDDT monotonically converges toward 0 with NFE; the framework is most useful at low NFE and saturates at `NFE = 500` (the largest tested NFE).
   - **`kanzi` anti-resonance finding** — `kanzi` has NO saturation boundary in `[10, 500]` because its ΔpLDDT oscillates between framework-WINS and framework-REGRESSES, with the only `NFE = 75` sweet spot where both metrics improve simultaneously. This finding (Wave 183 + Wave 184 cross-check) contextualizes the R5/R6 mixed-verdict status: the framework's value-add on protein is concentrated in a narrow NFE band for `kanzi` and is monotonic for `lineageflow`.
3. **Formal figure SHA-256 chain** — the 3 figures are now recorded in the TNNLS submission `MANIFEST.md` with their PNG sha256, size, and role. Reviewers can `sha256sum verification_outputs/wave183-p4-figure-*.png` and confirm against MANIFEST rows 37/38/39.

### Why this is ADDITIVE not a replacement

- **§7.7 16-cell Table B family verdict** is preserved verbatim ("FlowA wins all four baselines at both NFE settings on both R6 metrics"). No number, no word, no equation touched in §7.7.
- **§7.8 R5c regime curve** is preserved verbatim — the §7.7.1 paragraph is inserted between §7.7 and §7.8 (the §7.8 line number shifted from 485 to 493, but the §7.8 content is byte-identical).
- **§10.9 future-work item list** is preserved verbatim — §7.7.1 does not claim to close any future-work item; it is purely a cross-reference of pre-existing evidence figures.
- **CLM-051 status** is unchanged — §7.7.1 cites CLM-051 (CONFIRMED) as the upstream claim about the finer-NFE ladder; the §7.7.1 paragraph does not promote, demote, or re-state CLM-051.
- **Wave 183 P4 figures** are byte-stable (matplotlib Agg backend) and have not been re-rendered in this wave; the SHA-256 chain anchors the figures to the Wave 183 P4 commit (which is on the main branch).

### Why the figures live in `verification_outputs/` and not `docs/drafts/` or `docs/figures/`

The Wave 183 P4 figures are byte-stable evidence artefacts generated from the 108-cell Wave 183 P3 evaluation summary (`verification_outputs/wave183-p3-eval-summary.csv`). Per project convention, byte-stable evaluation evidence lives in `verification_outputs/<wave>/` (gitignored for raw evaluation outputs, but tracked when explicitly added as part of the package manifest). The §7.7.1 paragraph references the figures via `verification_outputs/wave183-p4-figure-*.png` paths; reviewers can `sha256sum --check` against MANIFEST rows 37/38/39 (no separate `SHA256SUMS` aggregator is needed for these 3 figures — they are individually pinned in MANIFEST.md, which is the canonical reviewer-verification surface).

---

## Files modified

- `docs/drafts/paper-A-final.md` — §7.7.1 ADDITIVE paragraph inserted (194468 → 220635 bytes; SHA `06a11c91...` → `cc0c91d7...`).
- `tnnls_submission/MANIFEST.md` — 3 new figure rows (rows 37/38/39) + row 32 paper-A-final.md SHA/size refresh + row 33 paper-A-final.pdf description refresh + self-row (row 23) SHA/size refresh (41858 → 45379 bytes; SHA `ace34bc6...` → `81f7d3ef...` pre-row-23-edit; post-edit SHA `b7caa380...`).
- `docs/audit/wave353-h2h-ablation-refs.md` — this audit doc (NEW, ADDITIVE).

## Files NOT modified

- `verification_outputs/wave183-p4-figure-pLDDT-finer.png` — byte-identical to Wave 183 P4 (sha256 `0ac80722b7063f4acf2f73880a99593a1d52da9307157def93c825c9f9f809a0`).
- `verification_outputs/wave183-p4-figure-scPerplexity-finer.png` — byte-identical to Wave 183 P4 (sha256 `f590c0b8ac6b82a17e77b6a21e28aa07b140e659ef6daec963298d0efbdeb961`).
- `verification_outputs/wave183-p4-figure-deltas-finer.png` — byte-identical to Wave 183 P4 (sha256 `1412578cc63add7a33b98d7c25be33a032febea69487ef3cdd683c28c510eb9f`).
- `verification_outputs/wave183-p4-aggregate.py` — renderer preserved verbatim.
- `verification_outputs/wave183-p4-aggregation.csv` — data source preserved verbatim.
- `docs/drafts/paper-A-final.pdf` — NOT regenerated in this wave (per Wave 268 strict-clean rule, the .tex file is hand-maintained separately).
- `docs/drafts/paper-A-final.tex` — preserved verbatim (no LaTeX edits in this wave).
- All 9 vendored upstream repos under `data/` — preserved verbatim (per AGENTS.md hard guardrail #1).
- All `adaptive_reflow/` framework code — preserved verbatim (paper-only ADDITIVE, no code edits).

## Status

- **Wave 353 P4:** READY_TO_COMMIT
- **Local commit message:** "Wave 353 P4: paper §7.7.1 Wave 183 finer NFE figure cross-references (Figures 3-5)" (USER AUTHORIZED, NO PUSH)
- **5-gate PASS:** D.4 30/30, claims 0 drift, mkdocs 0 warnings, ruff 0 (no *.py touched), vendored NOT touched.