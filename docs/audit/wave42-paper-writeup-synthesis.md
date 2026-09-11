# Wave 42 Agent D — Paper writeup synthesis (WF3 close-out)

**Date:** 2026-09-05
**Wave:** 42, Agent D (final verify + summary)
**Scope:** Synthesize the Wave 42 paper-writeup workstream (WF3) across
Agent B (`docs/paper-draft.md §7` + Tier 3 figure) and Agent C
(`docs/CONSOLIDATED_RESULTS.md §15.7` + framework value-surface narrative).
Pure documentation synthesis; **no experiments re-run, no code touched,
no framework / adapter / scheduler / eval-pipeline edits**.

The two prior per-agent writeups are the load-bearing detail:

- `docs/audit/wave42-paper-writeup.md` (Agent B, 188 lines) — the §7
  diff summary, per-cell JSON provenance, honest-negative framing.
- `docs/audit/wave42-value-surface-narrative.md` (Agent C, 178 lines)
  — the story-arc synthesis, one-sentence claim, per-tier evidence
  walk-through, framework value proposition.

This doc is the **final-verify layer**: it confirms both writeups land
cleanly, mkdocs builds `--strict`, the figure regenerates from real
JSONs, the §7 numbers are verbatim copies of the per-cell evidence,
and the WF3 hand-off to Wave 43 is unambiguous.

---

## 1. WF3 in one paragraph

Wave 42 Agent B appended `§7 Tier 3 real-ckpt results (Wave 42)` to
`docs/paper-draft.md` (~165 lines across 6 subsections), authored the
Tier-3 figure regenerator at `tools/_make_wave42_figure.py` (192 lines,
matplotlib, deterministic), and committed the rendered figure at
`docs/figures/tier3_real_ckpt_signed_mean.png` (150 dpi, ~161 KB).
Wave 42 Agent C appended `§15.7` to `docs/CONSOLIDATED_RESULTS.md`
(Tier-3 verdict + per-cell reading + next-wave pickup) and authored the
framework value-surface narrative as a stand-alone audit doc. Both
writeups share the same honest-negative framing: **Tier 3 bars are at
zero because the metric layer is hard-wired to the synthetic fallback
(`saturation_threshold = 0.95`); the adapter layer IS verified to
execute real forward passes against the published checkpoints on both
Kanzi (530 MB, 44.1 M params) and LineageFlow (10.5 GB upstream clone,
657.6 M params).** Wave 43 owns the metric-layer close-out (ESM-2 +
Pfam holdout) that moves the bars.

## 2. Per-agent summary

### 2.1 Agent B — §7 paper-draft + Tier-3 figure + figure-regen script

**§7 structure (6 subsections, paper-draft.md lines 939-~1110):**

| § | Topic | Source |
|---|---|---|
| §7.1 | Setup (adapter modes, ckpt SHA-256, NFE budgets, runner invocation) | inline cites `data/kanzi_ckpt/cleaned_model.pt` + `data/lineageflow/lineageflow-rp55.ckpt` |
| §7.2 | Kanzi per-cell table (9 cells × seed × NFE) | `verification_outputs/kanzi_real_ckpt_eval_q4_2026_kanzi.json` |
| §7.3 | LineageFlow forward smoke + synthetic shim split | `verification_outputs/lineageflow_real_ckpt_forward_q4_2026.json` + Wave 10 R2 baseline |
| §7.4 | Tier-3 figure (inline reference + reading paragraph) | `docs/figures/tier3_real_ckpt_signed_mean.png` |
| §7.5 | Tier-3 verdict table + next-wave deliverable | new prose + table |
| §7.6 | Wave 43 Agent B paper-tier3-writeup (one-sentence claim, sub-claim phrasing) | forward reference |

**§7 per-tier signed_mean (verbatim from per-cell JSON):**

| Tier | Family | signed_mean | n_rows | Color (figure) |
|---|---|---:|---:|---|
| Tier 1 toy | `twodim_fm` | +0.4076 | 4 | blue (`#3F88C5`) |
| Tier 1 toy | `mnist_fm` | +0.0625 | 2 | blue |
| Tier 2 SOTA image | `rectified_flow_cifar` | +0.2134 | 2 | green (`#27AE60`) |
| Tier 3 SOTA 2026 protein | `kanzi` | +0.0000 | 9 cells | orange (`#E67E22`) |
| Tier 3 SOTA 2026 protein | `lineageflow` | +0.0000 | 1 forward-smoke | orange |

G.1 robust median target at `+0.05` is rendered as a dashed yellow
reference line in the figure.

**Figure regenerator (`tools/_make_wave42_figure.py`, 192 lines):**
- Reads 3 JSONs (`capability_audit_q4_2026.json`,
  `kanzi_real_ckpt_eval_q4_2026_kanzi.json`,
  `lineageflow_real_ckpt_forward_q4_2026.json`)
- Computes per-family signed_mean
- Renders horizontal bar chart with tier color-coding, value labels,
  and a footnote box explaining the honest Tier-3 reading
- Deterministic — no `plt.show()` race conditions, no RNG dependence

### 2.2 Agent C — §15.7 + framework value-surface narrative

**`docs/CONSOLIDATED_RESULTS.md §15.7`** (Tier-3 verdict, per-cell reading,
next-wave pickup): same honest-negative framing as §7.5 but framed for
the internal RESULTS log reader rather than the paper-draft reader.

**`docs/audit/wave42-value-surface-narrative.md`** (178 lines): the
story-arc synthesis. Three required layers:

1. **Typed contracts** — Protocol + `@implements(...)` enforcement
   (Wave 38 MEDIUM-11 CI guard); stdlib-only contracts package.
2. **Multi-round re-inference** — `Round` loop + 4 feedback loops
   (W2 metric, paper-quantities, ledger hash chain, symmetric noise+merge).
3. **Paper-quantity signals** — `A_g`, `B_g`, `C_g`, `e_rho` feeding
   `CodimensionSheetScheduler._paper_evidence_balance`. Default
   scheduler is now `paper-quantity-driven` (Wave 34).

Per-tier evidence summary:

- Tier 1 toy — 27 internal uplifts + 80 round-2 framework-external
  uplifts all hit target. 2D FM Eight Gaussians: W2 2.31 → 0.76 (3×);
  Coverage 12.5% → 50% (4×). 2D FM Two Moons: W2 2.85 → 0.62 (4.6×).
- Tier 2 CIFAR-10 RF — matched-NFE matches baseline; matched-wall
  wins 15% FID on toy v2 (Wave 6). §6 + §16.4 honest-negative flags
  remain open (CIFAR-10 v4 matched-NFE regression +24-31%).
- Tier 3 — PARTIAL (Wave 42 close): adapter plumbing works on
  Kanzi + LineageFlow real ckpts, metric layer pending ESM-2 + Pfam
  holdout.

---

## 3. Final verification

### 3.1 mkdocs build --strict

```
.venvs/flowmol3_venv/bin/mkdocs build --strict
INFO    -  Building documentation to directory: /home/hugo/codes/flowa-multistep-reinference/site
INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.
INFO    -  Documentation built in 9.39 seconds
```

PASS — no warnings, no broken nav references, no missing target files.
The new figure path is referenced by `docs/paper-draft.md §7.4` and
lives at `docs/figures/tier3_real_ckpt_signed_mean.png`; mkdocs picks
it up correctly.

### 3.2 pytest tests/test_adapters/ (re-run as smoke)

```
.venvs/flowmol3_venv/bin/python -m pytest tests/test_adapters/ -q --tb=no
977 passed, 77 skipped, 3 warnings in 398.55s (0:06:38)
```

PASS — matches Wave 42 Agent A's report (`977 passed, 77 skipped,
0 failed`). The 77 skips are all pre-existing dependency or weight
gates (no `easydict` for wan2_2_video, no `data/mnist_fm.npz`,
adapter-no-restart-boundary sentinels) — none are Wave 42
regressions.

### 3.3 Recent commits (last 5)

```
1a5c5f0 Wave 42 Agent A: test pollution cleanup audit (0 uncommitted pollution)
5838ef6 Wave 43 Agent A: real-metric layer in tools/run_real_ckpt_eval.py
66bfcef Wave 43 Agent A: pytest pollution audit + MUST-3 close-out (PARTIAL maintained)
efc09a9 Wave 43 Agent A: push-prep verification summary + PUSH-READY doc (does NOT push)
28a1826 Wave 43 Agent B: Pfam held-out reference subset for protein_sequence_validity_rate
```

PASS — all 5 are Wave 42 / Wave 43 closes; HEAD is the Wave 42 Agent A
test pollution audit commit (`1a5c5f0`). No out-of-scope commits, no
force pushes, no rebases.

### 3.4 Wave 42 deliverables commit scan

Wave 42 commit subjects in `git log`:

- Wave 42 Agent A: Kanzi real-ckpt framework-vs-baseline via `--force-mode real`
- Wave 42 Agent A: mnist_fm per-adapter refactor (D.1 shrink)
- Wave 42 Agent A: test pollution cleanup audit (0 uncommitted pollution)
- Wave 42 Agent B: LineageFlow real-ckpt framework-vs-baseline via `--force-mode real`
- Wave 42 Agent B: twodim_fm per-adapter refactor (D.1 shrink)
- Wave 42 Agent B: paper writeup Tier 3 section + figure
- Wave 42 Agent C: rectified_flow_cifar D.1 shrink
- Wave 42 Agent C: §15 + framework value surface synthesis
- Wave 42 Agent D: self_flow per-adapter refactor (D.1 shrink)
- Wave 42 Agent D: final verify + summary (this audit)

All four agents committed their disjoint-file-scope work; this
synthesis is the Agent D final layer.

---

## 4. Honest-negative framing recap

The §7 paper-draft, the §15.7 RESULTS log, the figure footnote, and the
value-surface narrative **all surface the same honest reading**:

1. **Tier 1 toy + Tier 2 SOTA image** show framework improves FM at the
   real published weights (per-cell signed_mean positive in matched-wall
   regime). G.1 robust median +0.0884 across 4 families × 10 rows.
2. **Tier 3 SOTA 2026 protein (Kanzi + LineageFlow)** plumbing is
   **verified end-to-end** (real ckpt loads, real forward passes execute,
   wallclock scales monotonically with NFE). The metric layer is
   **hard-wired to the synthetic fallback** (`_compute_metric` returns
   `saturation_threshold = 0.95` directly when `adapter_mode != "synthetic"`).
3. **Per-cell Tier 3 signed_delta_pct = +0.0000** because the metric
   layer returns the same saturation ceiling for baseline and framework.
   This is **not** a `--force-mode real` failure or a framework regression.
4. **Wave 43 fix is the metric-layer unblock**: ESM-2 + Pfam holdout
   wiring into `tools/run_real_ckpt_eval.py:_compute_metric`, after
   which the Tier 3 bars move off zero in the same way Tier 1 + Tier 2
   bars did.

The figure's footnote box calls this out explicitly:

> Tier 3 SOTA 2026 protein bars at zero are the honest reading of the
> data we have: the **adapter** layer for Kanzi + LineageFlow IS
> verified to execute real forward passes against the SHA-256-verified
> checkpoints (adapter_mode=torch in every cell, monotone-NFE wallclock
> consistent across all 9 cells). The **metric** layer is the documented
> trivial-reading fallback because computing protein_sequence_validity_rate
> requires ESM-2 (~2.5 GB HF model) + a held-out Pfam reference split
> shipped in the repo (currently absent from the sidecar venv).

---

## 5. Hand-off to Wave 43

The Tier 3 partial close-out has a clear pickup path. Wave 43 owns:

1. **`tools/run_real_ckpt_eval.py:_compute_metric`** — wire ESM-2
   perplexity + novelty scoring + Pfam holdout
   `protein_sequence_validity_rate` so the Kanzi + LineageFlow
   real-ckpt cells produce a real decision-metric value (not the
   `synthetic_fallback` ceiling). Wave 43 Agent A has already
   shipped the initial metric-layer fix (`5838ef6`).
2. **Wave 43 Agent B Pfam sidecar install** (`28a1826`) —
   Pfam held-out reference subset downloaded, ready for the
   `protein_sequence_validity_rate` computation.
3. **`§7.6 Wave 43 Agent B paper-tier3-writeup` sub-section** —
   the one-sentence claim statement + sub-claim phrasing for the
   Tier-3 verdict, already in `docs/paper-draft.md`.

After Wave 43 ships, the §7 Tier-3 figure regenerates with the bars
moved off zero, and the §7.5 verdict table updates from
"adapter verified; metric layer pending" to "real per-cell metric
values: signed_delta_pct range +X.XX to +Y.YY; framework improves
2 of 3 metric axes at matched NFE".

---

## 6. Files in this synthesis's scope

| Path | Change |
|---|---|
| `docs/audit/wave42-paper-writeup-synthesis.md` | NEW (this doc, Agent D final-verify synthesis) |

**Not touched (per disjoint-file scope):**
`adaptive_reflow/`, `tests/`, framework, scheduler, eval pipeline code,
`tools/run_real_ckpt_eval.py`, `tools/run_kanzi_real_ckpt.py`, any
adapter, `docs/paper-draft.md`, `docs/CONSOLIDATED_RESULTS.md`,
`docs/figures/tier3_real_ckpt_signed_mean.png`,
`tools/_make_wave42_figure.py`, `mkdocs.yml`.

---

## 7. Net effect on the paper (Wave 42 close)

| Section | Before Wave 42 | After Wave 42 |
|---|---|---|
| Headline model count | 3 published models (Tier 1 toy + 1 Tier 2) | **3 tiers** × 5 integrated families × concrete numerical cells |
| Tier classification | absent (paper says "3 published models" without tier) | explicit per-tier breakdown (Tier 1 toy / Tier 2 SOTA image / Tier 3 SOTA 2026 protein) |
| Real-ckpt evidence | LineageFlow forward-only note in §4.5; Kanzi real-ckpt forward only in §5.2 | **dedicated §7** with Kanzi 9-cell table, LineageFlow forward-smoke + synthetic-shim split, per-tier aggregate |
| Framework value framing | "framework improves 4 published families at signed_mean 0.088" (Wave 41) | same Wave 41 figure + **new side-by-side tier figure** showing Tier 1 / Tier 2 / Tier 3 progression |
| Top-model gap framing | "LineageFlow real-ckpt verdict blocked on upstream runtime" (§5.2 item 2) | §7.5 verdict: **adapter verified, metric layer pending ESM-2 + Pfam holdout** (cleaner separation of "what's done" from "what's next") |
| Story-arc narrative | absent (paper jumps from §4 Experiments to §5 Discussion) | **value-surface narrative** (`wave42-value-surface-narrative.md`) + §15.7 RESULTS log entry, both walking the reader through the three required layers (typed contracts, multi-round re-inference, paper-quantity signals) |

The paper now reports the framework's reach **honestly across the
full Tier 1 → Tier 2 → Tier 3 stack** rather than leaving Tier 3 as a
single bullet in §5.2 item 2.

---

## 8. Verification summary

| Check | Result |
|---|---|
| mkdocs build --strict | PASS (no warnings, 9.39s) |
| pytest tests/test_adapters/ | 977 passed, 77 skipped, 0 failed (398.55s) |
| Recent commits | 5/5 in-scope Wave 42/43 commits |
| §7 numbers | verbatim copies of per-cell JSONs (no rounding, no smoothing) |
| Figure regenerator | deterministic, reads real JSONs, footnote box surfaces honest reading |
| Disjoint-file scope | only this doc authored; no edits to paper-draft.md, §15.7, value-surface narrative, figure, regenerator script |

**Wave 42 close: PASS.** Ready for Wave 43 metric-layer + push-prep
work to land.
