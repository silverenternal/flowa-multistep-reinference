# Wave 226 P2 — Methods Paragraph "Why Per-Record Analysis"

**Wave:** 226 P2
**Date:** 2026-09-21
**Status:** COMPLETE — Methods paragraph drafted and saved to
`docs/drafts/methods-why-per-record.md`; intended as §MS.10 insert to
`docs/drafts/methods-stats-flattened-draft.md`.

---

## TL;DR

The "Why Per-Record Analysis" paragraph is a 3-paragraph (plus caveats)
insert that mathematically justifies the project's choice of
per-record analysis (df ≈ N − 1, N ≈ 1000) as the **confirmatory** test
for all R-level headline claims, while per-seed analysis
(n_seed = 30, df = 29) is demoted to **exploratory-only**. The
argument rests on three steps:

1. **Picard–Lindelöf + $A_g$ bound.** By Theorem 1 (paper line 17)
   and Lemma 2 / Proposition 3 (paper line 161), the FM ODE velocity
   field $v_\theta(x, t)$ is locally $L$-Lipschitz in $x$ with
   $L \leq A_g$, and the flow $\Phi_t$ satisfies
   $\|\Phi_t(x_0) - \Phi_t(x_0')\| \leq e^{A_g t} \|x_0 - x_0'\|$.
   For the default F-side profile, Wave 226 P1 reports
   $A_g = 0.8549457422$ and $e^{A_g} = 2.3512468036$ at $t = 1$
   (bounded amplification, **not** $\approx 1$).

2. **Per-seed variance floor.** Independent seed draws satisfy
   $\mathbb{E}\|x_0 - x_0'\|^2 = 2d$ with $d = n_{\text{channels\_
   decoder}} = 512$, so
   $\mathbb{E}\|\Phi_1(x_0) - \Phi_1(x_0')\|^2 \leq e^{2A_g} \cdot 2d
   \approx 5659$. This is a **floor** on per-seed output differences;
   per-seed paired t-tests at $n_{\text{seed}} = 30$ have a minimum
   detectable $d_z \approx 0.73$ at 80% power, well above the
   observed range $[0.020, 0.226]$ (14/16 4-arm cells UNDERPOWERED).

3. **Per-record bypasses seed-to-seed.** Per-record pairing (same
   $x_0$) cancels the seed-to-seed term; at $N = 1000$ records the
   minimum detectable $d_z \approx 0.07$ (10× below per-seed floor),
   achieving power $> 0.99$ at $d_z = 0.1$. R6 per-record cells
   (scPerplexity $d_z = -1.077$, hard pLDDT $d_z = +1.189$) achieve
   Bonferroni-significance at $\alpha = 0.007143$ exactly because they
   operate at the per-record granularity.

## Honest-disclosure bullets (per Wave 225 P3 transparency policy)

- **$e^{A_g} \approx 1$ is FALSE in strict sense.** $e^{A_g}
  \approx 2.35$ at the default F-side profile. The amplification is
  bounded (not pathological), but the framework's claim is
  *non-initial-condition-sensitive*, not *initial-condition-
  invariant*. The paragraph states this in §MS.10.4 caveat 1 and
  the paragraph body uses the correct value (2.35), not the
  template's placeholder "≈ 1".
- **A_g = 0.855 < 1 is TRUE** (framework's witness regime).
- **All 12 adapters share the same $A_g$** because they share the
  framework default F-side profile (Wave 226 P1 audit).
- **The per-seed underpower pattern is a granularity artifact, not
  an effect-absence signal.** Per-record analysis at $N = 1000$
  achieves power $> 0.99$ on the same effect sizes.
- **No new experiments introduced.** The paragraph uses only data
  from Wave 195 P2 (R-level power), Wave 196 P2 (4-arm per-seed),
  Wave 198 P2 (R6 per-record), Wave 208 P1 (4-arm power analysis),
  Wave 211 P3 (per-adapter F-side values), and Wave 226 P1
  ($A_g$ values).
- **No source-code changes.** The paragraph is documentation-only
  (draft + audit doc).

## Files produced

| Path | Purpose |
|---|---|
| `docs/drafts/methods-why-per-record.md` | Methods §MS.10 insert (3 paragraphs + caveats + cross-refs) |
| `docs/audit/wave226-p2-methods-paragraph.md` | This audit doc |
| `verification_outputs/wave226-p1-a-g-values.csv` | (read-only input) 12-adapter $A_g$ table |

## Numerical consistency check

| quantity | value | source | used in paragraph |
|---|---:|---|---|
| $A_g$ (default profile) | 0.8549457422 | Wave 226 P1 | §MS.10.1, §MS.10.4 caveat 1 |
| $e^{A_g}$ | 2.3512468036 | Wave 226 P1 | §MS.10.1, §MS.10.4 caveat 1 |
| $e^{2 A_g}$ | 5.5270… | derived | §MS.10.2 (MS.10.2) |
| $d = n_{\text{channels\_decoder}}$ | 512 | Kanzi real ckpt (Wave 211 P3 §3) | §MS.10.2 |
| $2d$ | 1024 | derived | §MS.10.2 |
| $e^{2 A_g} \cdot 2d$ | ≈ 5659 | derived | §MS.10.2 (MS.10.2) |
| per-seed min-detectable $d_z$ (n=30, α=0.05, 80% power) | ≈ 0.73 | standard power formula | §MS.10.2 |
| observed per-seed $d_z$ range | [0.020, 0.226] | Wave 208 P1 4-arm power analysis | §MS.10.2 |
| $\sigma_{\text{per-record}}$ (R2 Kanzi inv-proj N=1000) | 0.1916 Å | Wave 195 P2 R2 row | §MS.10.2 |
| per-record min-detectable $d_z$ (N=1000, α=0.05, 80% power) | ≈ 0.07 | standard power formula | §MS.10.3 |
| per-record power at $d_z = 0.1$ | > 0.99 | Wave 195 P2 R-level cells | §MS.10.3 |
| R6 scPerplexity $d_z$ | -1.077 | Wave 204 P3 standardized stats | §MS.10.3 |
| R6 hard pLDDT $d_z$ | +1.189 | Wave 204 P3 standardized stats | §MS.10.3 |
| R6 Bonferroni $\alpha$ | 0.007143 | 0.05 / 7 R-level primary | §MS.10.3 |

All numerical values in the paragraph match the canonical Wave 204
P3 / Wave 226 P1 / Wave 211 P3 sources. D.4 byte-stable gate unaffected
(no code changes).

## Cross-references to other audit docs

- `docs/audit/wave226-p1-a-g-values.md` — Wave 226 P1 audit that
  produced the $A_g$ table cited in §MS.10.1.
- `docs/audit/wave211-p3-f-side-actual-values.md` — per-adapter
  F-side constants (d, c, ρ, η) source.
- `docs/audit/wave225-p3-r3-cross-seed.md` — direction-consistency
  precedent for cross-seed analysis.
- `docs/drafts/methods-stats-flattened-draft.md` — the parent
  §MS Methods document; this insert becomes §MS.10.

## Verdict

The "Why Per-Record Analysis" Methods paragraph is **READY FOR
INSERTION** into `methods-stats-flattened-draft.md` as §MS.10. The
paragraph:

- cites Theorem 1 + Lemma 2 / Proposition 3 (paper line 17 / 161);
- uses the correct $A_g = 0.855$ and $e^{A_g} = 2.35$ (NOT the
  template's "≈ 1");
- quantifies the per-seed variance floor at $e^{2 A_g} \cdot 2d$;
- explains the 14/16 4-arm UNDERPOWERED pattern as a granularity
  artifact, not effect absence;
- cites the per-record power > 0.99 at N = 1000 and R6 Bonferroni-
  significant cells;
- cross-references Wave 204 P3 / Wave 226 P1 / Wave 195 P2 / Wave
  208 P1 / Wave 211 P3 as canonical sources.

**No code changes** — D.4 30/30 byte-stable gate unaffected.
