# Wave 185 P4 — Empirical vs theoretical BL plot + paper §11 (Theory) update

**Date:** 2026-09-18
**Branch:** main
**Scope:** Render the Wave 185 P3 tightness table as two
publication-quality figures, and translate the findings into
a paper §11 (Theory) update that re-locates Theorem 1's
claim scope.

This is the **visual + paper-writeup half** of the Wave 185
tightness investigation. P1 designed the comparison, P2
measured the empirical BL distance (energy distance on the
pLDDT axis), P3 computed the Theorem 1 bound + tightness
ratios, **P4 renders both as figures and writes the §11
update** the paper needs in light of the finding.

**Plotter:** `tools/w185_p4_plot.py` (matplotlib, byte-stable
on identical CSV input).
**Figures:**
- `verification_outputs/wave185-p4-figure-bl-tightness.png`
- `verification_outputs/wave185-p4-figure-tightness-ratio.png`

---

## 1. Figures

### 1.1 Figure 1 — `wave185-p4-figure-bl-tightness.png`

Per-model empirical BL distance (1-D pLDDT energy distance,
with 95% bootstrap CI ribbon) overlaid on the Theorem 1
bound `B(NFE)` (single dashed curve, profile `g=sin(πx)`).

- X-axis: NFE ∈ {10, 50, 100, 150, 200, 300}, log scale.
- Y-axis: BL distance, log scale.
- Both axes log so the **3-orders-of-magnitude gap**
  between the bound (`~10^-4`) and the empirical values
  (`~10^0`) is visible at a glance.
- The Theorem 1 curve decays from `B(10) ≈ 4.98e-2` to
  `B(50..300) ≈ 1.24e-4` (residual floor).
- Empirical curves are non-monotone (the Wave 185 P2 §3.3
  rebound at NFE=150 is visible) — the bound does not
  capture this structure.
- CI ribbons overlap across the two models at every NFE;
  the **gap between the empirical curve and the bound is
  2-4 orders of magnitude**, robust to CI width.

### 1.2 Figure 2 — `wave185-p4-figure-tightness-ratio.png`

Tightness ratio `empirical_BL / B(NFE)` per model. Same
NFE axis (log), ratio on a log Y axis, value annotations on
each data point.

- The horizontal `tightness = 1×` reference is **never
  crossed** — the bound is uniformly too tight.
- Smallest ratio: **kanzi NFE=10 at 26×**.
- Largest ratio: **kanzi NFE=150 at 7,522×**.
- The pattern (smallest at NFE=10, largest at NFE=150) is
  the same for both models; magnitudes differ because
  kanzi's NFE=150 pLDDT gap is larger than lineageflow's.

### 1.3 Reproduction

```bash
python3 tools/w185_p4_plot.py
```

Both figures are deterministic given the
`wave185-p3-tightness.csv` input (matplotlib defaults,
no random state).

---

## 2. Paper §11 (Theory) update — claim-scope relocations

The Wave 185 P1-P4 chain establishes that Theorem 1's bound
`B(NFE)` is **structurally too tight** for the protein-axis
empirical energy distance. The paper §11 (Theory) needs to
relocate the theorem's claim scope to honestly describe
what it bounds. The proposed replacement is below.

### 2.1 Existing §11 wording (placeholder)

> **Theorem 1 (Bounded-Lipschitz convergence).** *For any
> profile `g: X → [0,1]` and any framework regime satisfying
> the conditions of §3, the bounded-Lipschitz distance
> between the framework's sampling distribution at `NFE`
> function evaluations and the infinite-NFE target is
> bounded by*
> `B(NFE) = A_g · exp(-NFE/B_g) + C_g · e_ρ`.

### 2.2 Proposed §11 wording (Wave 185 update)

> **Theorem 1 (Framework self-convergence in BL).** *For any
> profile `g: X → [0,1]` and any framework regime
> `(ρ, c, η)` satisfying the conditions of §3, the
> bounded-Lipschitz distance between the framework's
> sampling distribution at `NFE` function evaluations and
> the framework's infinite-NFE **self-target** (i.e., the
> limit of the framework's own sampling distribution as
> `NFE → ∞` along the same `(ρ, c, η)` regime) is bounded
> by `B(NFE) = A_g · exp(-NFE/B_g) + C_g · e_ρ`.
>
> *Theorem 1 bounds the framework's **self-convergence**
> to its own infinite-NFE limit, not the framework's
> distribution shift against any external baseline
> (e.g., an ungoverned `(ρ, c, η)` regime, or a different
> model class). On the protein axis, the
> framework-vs-baseline energy distance (the headline
> value-add metric reported in §10.29) is **structurally
> larger** than `B(NFE)` — by 25×–7,500× across the
> (model, NFE) grid in Wave 185 P3 — because the
> framework-vs-baseline shift and the framework's
> self-convergence are different quantities operating at
> different scales. The framework's value-add on protein
> is therefore an **empirical claim** (§10.29, P3.2),
> not a theorem-derived one.*

### 2.3 What changes (semantic diff)

| Before | After |
|---|---|
| "the bounded-Lipschitz distance ... to the infinite-NFE target" | "... to the framework's infinite-NFE **self-target** (along the same regime)" |
| (implicit: any target, including baseline) | (explicit: framework self-target only) |
| (silent on framework-vs-baseline) | (explicit: framework-vs-baseline shift is **outside** the theorem's scope and is structurally larger than `B(NFE)`) |

The proof is unchanged. The constants `(A_g, B_g, C_g, e_ρ)`
are unchanged. The empirical-claim text in §10.29 is
unchanged. **Only the scope of the theorem's claim is made
explicit** so a reader cannot read more into it than the
proof supports.

### 2.4 Why this is the right fix (not a weakening)

The theorem is correct as stated about framework self-distance.
Rephrasing is not a weakening — it is **honest claim
localization**:

1. The bound is **provably valid** for framework
   self-distance. Wave 11 conformance suite
   (`tests/test_theory/test_paper_quantities.py`) verifies
   the bound holds for the framework's own sampling
   distribution at every tested NFE.
2. The bound is **not valid** for framework-vs-baseline
   distance — Wave 185 P3 measures 25-7,500× violation
   across the (model, NFE) grid. Without this relocations,
   the paper risks the reader inferring that the theorem
   *bounds the empirical §10.29 numbers*, which it does
   not.
3. The fix preserves all empirical claims (§10.29
   framework-vs-baseline deltas are unchanged) and
   preserves the theorem (its proof is intact). Only the
   *wording* is updated.

This is the **minimal, honest** change.

---

## 3. What is **not** in this PR

1. **No new GPU eval.** The figures are pure rendering of
   the P3 CSV. No new FASTA generation, no new model
   inference, no new eval.
2. **No theorem proof change.** Only the claim-scope
   wording in §11. The bound form, constants, and
   proof structure are unchanged.
3. **No change to §10.29 (empirical results).** Wave 179
   P5 / Wave 183 P4 numbers stand as reported. The §11
   relocations do not contradict them.
4. **No claim that the theorem is wrong.** The theorem is
   correct about framework self-convergence. The relocations
   prevent over-reading of the theorem to cover
   framework-vs-baseline claims.

---

## 4. Limitations + scope notes

1. **Figures are 1-D pLDDT only.** The Wave 185 P2 2-D
   (pLDDT, scPerplexity) energy distance is a secondary
   metric and is not plotted — the qualitative finding
   (bound ≪ empirical) holds for 2-D too, but the 1-D plot
   is the cleaner visual.
2. **CI ribbons overlap across models.** Per Wave 185 P2
   §3.5, the 95% CIs span ~5-10× the point estimate
   (n=30 / n=90 per cell). The bound violation is
   unambiguous at the lower-CI endpoint (e.g., kanzi
   NFE=50 lower=0.118, bound=1.247e-4, ratio=946×).
3. **Profile `g = sin(πx)` is synthetic.** Per Wave 185
   P1 §7.2, the bound is computed for the Wave 11
   canonical reference profile. Model-derived `g` would
   under-determine the bound; the synthetic `g` is the
   correct, theory-faithful choice for the §11 cross-check.
4. **The bound is intentionally loose for the baseline
   regime too** (baseline regime's `B(NFE) ≈ 7.16e-3` at
   NFE ≥ 50 — still 13× to 130× too tight). The §11
   relocations apply to both regimes; the framework regime
   is just the more extreme violation.

---

## 5. Files referenced

| Source | Path |
|---|---|
| Design (P1) | `docs/audit/wave185-p1-design.md` |
| Empirical BL (P2) | `docs/audit/wave185-p2-empirical-bl.md` |
| Tightness table (P3) | `docs/audit/wave185-p3-tightness.md` |
| P3 CSV | `verification_outputs/wave185-p3-tightness.csv` |
| P4 plot script | `tools/w185_p4_plot.py` |
| P4 figure 1 | `verification_outputs/wave185-p4-figure-bl-tightness.png` |
| P4 figure 2 | `verification_outputs/wave185-p4-figure-tightness-ratio.png` |
| Paper §2.8.1 (bound form) | `docs/paper-draft.md` lines 266-284 |
| Paper §11 (Theory) | `docs/paper-draft.md` §11 |
| Wave 11 conformance | `tests/test_theory/test_paper_quantities.py` |
| Wave 169 theory audit | `docs/audit/wave169-theory-audit.md` |
| Wave 179 P5 figures (style reference) | `verification_outputs/wave179-p5-figure-*.png` |

---

## 6. Output JSON

```json
{
  "figures_generated": 2,
  "figure_paths": [
    "verification_outputs/wave185-p4-figure-bl-tightness.png",
    "verification_outputs/wave185-p4-figure-tightness-ratio.png"
  ],
  "paper_section_updated": "§11 (Theory) — claim-scope relocations drafted; the theorem is now explicitly bounded to framework self-convergence, not framework-vs-baseline distance",
  "central_finding": "The empirical framework-vs-baseline BL distance on protein is 25x-7500x larger than Theorem 1's framework-self-distance bound at every (model, NFE) cell; the paper §11 wording needs to relocate the theorem's claim scope to framework self-convergence. The figures make the gap visually unambiguous; the relocations prevent over-reading of the theorem."
}
```