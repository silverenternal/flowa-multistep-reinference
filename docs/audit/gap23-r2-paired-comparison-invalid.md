# GAP-23 — R2 paired comparison invalid (framework arm measures a generated structure, not the input)

**Date:** 2026-10-12
**Increment:** GAP-23 (new, from a live-manuscript measurement audit; supersedes the GAP-22 premise)
**Status:** OPEN — P0 (measurement integrity)
**Owner:** agent (fix path is GPU-gated)

---

## 1. Observed facts

1. **The R2 headline** (paper `docs/drafts/paper-A-final.md` §7.2; `docs/CLAIMS.md`
   CLM-060 / CLM-063 / CLM-073) is a *paired* test: "framework_inv_proj beats
   baseline by 0.0184–0.0190 Å, paired `t = 3.02`/`3.13`, `df = 999`,
   `p_raw = 0.00257`/`0.00179`, Cohen's `d_z = +0.096`/`-0.099`, framework-WINS,
   Bonferroni-significant at R-level `α = 0.007143`."

2. **The baseline arm measures the round-trip of the *input* record.**
   `tools/_kanzi_sweep_runner.py:777-783` sets `coords_pred_A = coords_angstrom`
   (the record parsed from `verification_outputs/kanzi_n1000_coords.txt`), and
   `:928-952` computes `kabsch_rmsd(input, dae.decode(dae.encode(input)))`.
   Source artifact: `verification_outputs/wave196-p3-kanzi-n1000-framework-inv-proj-baseline/kanzi_n1000_paper_metrics.json`
   (`tool = tools.w196_p3_kanzi_n1000_batched_baseline`, n=1000, mean 0.8982 Å).

3. **The framework arm measures the round-trip of a *generated* structure.**
   `tools/_kanzi_sweep_runner.py:_synthesize_x_final_real` (`:348-482`) builds
   `x0` from a fresh random Gaussian latent —
   `rng.standard_normal((L=64, 512))` seeded by `(seed, record_idx)` (`:448-450`) —
   runs the trained `project_out⁻¹` bridge + `adapter.solve_ode`, and returns the
   trajectory endpoint. `:789-830` then sets `coords_pred_A = x_final`, and
   `:928-952` computes `kabsch_rmsd(generated, dae.decode(dae.encode(generated)))`.
   The framework arm **never consumes input record *i***.

4. **The framework arm's own JSON says so.** Both arms carry
   `measurement_scope = "generated-coordinate autoencoder roundtrip; **not paired
   input reconstruction** or multi-round refinement"` and
   `x_final_synthesis = "seeded (64,512) latent -> inverse projection and DAE
   decode -> (64,3) nm coordinates -> configured single adapter rollout"`:
   - `verification_outputs/kanzi_n1000_framework_inv_proj_w149_q4_2026/kanzi_n1000_framework_paper_metrics.json`
     (n=1000, mean 0.8798 Å)
   - `verification_outputs/wave214-p2-kanzi-framework-inv-proj-n1000/kanzi_n1000_framework_paper_metrics.json`
     (n=1000, mean 0.8838 Å) — **the arm the Wave-218 headline actually used**
     (`paper-data/R2_kanzi_rmsd/wave218-p3-kanzi-framework-wins.json`
     `framework_source`).

5. **Empirical proof the pairing is spurious.** The Wave 196/218 "paired t-test"
   joins the two arms by the shared `seq_*` key (`tools/w196_p3_kanzi_finalize.py:88-92`),
   which matches on index only. But the per-record values are statistically
   **independent**:
   - `corr(baseline seq_i, framework seq_i) = +0.0003` (w149, n=1000)
   - `corr(baseline seq_i, framework seq_i) = +0.0196` (w214, n=1000)
   Two arms measuring the round-trip RMSD of the *same* input structures would be
   strongly correlated (the input's intrinsic difficulty drives both). Near-zero
   correlation confirms `framework seq_i` is not a function of input record *i*.
   (The marginals are near-identical — same deciles, mean, sd — which is why the
   defect is invisible in aggregate statistics.)

6. **Reproduction.** `wave218-p3-kanzi-framework-wins.json` reproduces exactly:
   `mean_diff = -0.01896`, `t = -3.131`, `df = 999`, `p_raw = 0.00179`,
   `d_z = -0.0990`, `bonf_sig = true`, `verdict = framework_wins`.

## 2. Interpretation

- **The R2 paired t-test is invalid.** It pairs *baseline round-trip of input *i**
  with *framework round-trip of a random latent seeded by *i*** — two unrelated
  quantities. The `df = 999` significance is an artifact of pairing two
  independent samples that happen to differ in mean by ~0.019 Å.
- **R2's STRONG framework-WINS label is unsupported.** `docs/CLAIMS.md` CLM-060
  (Wave 218 REGRESSES → SUPPORTED), CLM-063, CLM-073 and paper §7.2 all rest on
  this pairing. The §7.2 R2 row's "small but consistent framework-WINS on the
  per-record composite axis" is not established by the cited evidence.
- **Even as an *unpaired* comparison it is confounded.** "Generated-structure
  round-trip" and "input-structure round-trip" are different populations; if the
  framework's generated structures are intrinsically easier to round-trip, the
  framework looks better for free. There is no matched control.
- **This is the root cause behind GAP-22.** R2's `d_z = 0.099` is not a *small
  genuine effect* sitting below the 0.8 bar — it is a *spurious pairing artifact*.
  Fixing the rubric wording (GAP-22 options A/C) or re-labelling (B) would paper
  over a measurement defect.

## 3. Gap / fix paths

The user directive is **"fix the metric, not the document."** R2's metric is not
weak — it is invalid. A genuinely-strong R2 requires a *valid* measurement.

- **(F1) Valid paired framework arm — the principled fix (GPU-gated).** Feed
  input record *i* as the framework's initial state, run the restart-blend solve,
  and measure `kabsch_rmsd(framework_processed_input_i, decode(encode(...)))`,
  paired against the baseline round-trip of the same input *i*. Then re-do the
  paired t-test. This is the only design that measures "does the framework improve
  the round-trip of the *same* structure." Cost: a code path that seeds `x0` from
  the input coords (not a random latent) + a Kanzi N=1000 run
  (~75 min/arm on GPU 0; the DAE needs ~97 GB, so only GPU 0 fits).
- **(F2) Re-frame R2 as an unpaired generative-quality comparison.** Honest but
  weak and confounded; does not make the metric strong.
- **(F3) Drop R2 as an invalid cell.** Headline becomes 3 STRONG + 1 TIE + …;
  user-gated, changes a headline count.

## 4. Smallest next action

Decide F1 / F2 / F3 with the user. F1 is the only path that makes R2 genuinely
strong; it needs (a) an input-seeded framework `x0` path and (b) a GPU run.

## 5. Guardrail note

No number, status, or verdict was changed by this audit. It records a
measurement-integrity defect and flags the affected claims; the repair (if F1) is
a *measurement* change, not a wording change.
