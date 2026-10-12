# R1 re-measure on the genuine real-forward basis (D-004b live) — the recovery

**Date:** 2026-10-12
**Branch:** main
**Base commit:** `1264cec` (fix(lineageflow): D-004b — per-record random restart state on the real path)
**Scope:** R1 cell (`hmmscan_total_hits`), 3 seeds × N=1000 × 2 arms, real-forward basis, per-record stochastic restart init
**Verdict:** with the D-004b per-record stochastic restart init on the real-classifier path, the framework arm **beats the baseline on all 3 seeds** (275/272/259 vs 158/159/174; mean **+105 hits**, DL $d_\text{pooled} = +0.156$, $z = 8.49$, $I^2 = 0$, Bonferroni-significant at $k=7$). This **reverses** the D-004 zero-collapse reading ($d_\text{pooled} = -0.4013$) and sits **above** the pre-D-004 contaminated run ($+0.110175$). The pooled effect stays below the 0.8 STRONG bar, so R1 remains a small-effect PARTIAL-class cell — but its **real-forward basis is now a WIN, not a collapse**.

---

## 1. Purpose

The D-004 re-measurement (`docs/audit/r1-d004-remeasure.md`) showed that on the genuine real-forward basis the framework arm **collapsed to 0 Pfam hits on all 3 seeds** ($d_\text{pooled} = -0.4013$): the eval pipeline built the same $x_0$ for every record (the `seed` argument of `_build_initial_state_and_condition` is never used), and the only per-record seed carrier — the restart perturbation — was too weak to matter once the real (deterministic) velocity field was live. The recorded follow-up **D-004b** was: branch the *restart* fresh-state sampler to a per-record random simplex on the real-classifier path, so the real flow sees a distinct initial condition per record. This audit records the actual re-measurement under that fix.

---

## 2. The D-004b fix

`adaptive_reflow/adapters/lineageflow.py` (commit `1264cec`, additive):

- `_install_checkpoint_compat` keeps the D-004 `core.__path__` shim (`bf66aa4`), so `_is_lineageflow_classifier` is `True` on the real path.
- A new helper `_synthesize_random_simplex(rng)` draws `softmax(randn(L, AA_VOCAB))` — the Wave-41 tool noise convention (`tools/run_lineageflow_real_ckpt.py:212-215`) — for the AA dimensions, with the special dimensions keeping their uniform share and the row renormalised.
- The restart path now branches:
  `if getattr(self._model, "_is_lineageflow_classifier", False): fresh_theta = _synthesize_random_simplex(fresh_rng) else: _synthesize_latent_like_tensor(...)`.

The **synthetic** path is byte-unchanged (the branch only fires on the real-classifier marker), so the D.4 byte-stable vectors are preserved. Tests: `tests/test_adapters/test_lineageflow_smoke.py` gains `test_checkpoint_compat_shim_preserves_upstream_core_package_path` and `test_d004b_real_classifier_path_uses_random_simplex_restart` (monkeypatch-counted: synthetic → uniform, real → random simplex).

**Why the restart site, not the init site.** A bounded N=20 probe first tried branching the *initial-state* sampler; it changed nothing (still 1 unique 30-AA prefix) because the init seed is constant per record. Branching the *restart* fresh-state sampler restored full diversity (20/20 unique sequences, 20/20 unique 30-AA prefixes). The lever is the restart fresh state, which already carries a per-record seed via the policy hash.

---

## 3. Observed facts

| Item | Value |
|---|---|
| Evidence directory | `verification_outputs/r1_3seed_d004b_q4_2026/` (gitignored; force-added) |
| Seeds | 42, 43, 44 |
| Records per arm per seed | 1000 + 1000 = 6000 total |
| Framework arm mode | **real-forward** — `force_mode="auto"` → `models.model.LineageFlowClassifier` (D-004 live) with the **D-004b per-record random restart init** |
| Protocol | `--n 1000 --upstream-eval-len-bias short` (30–150 AA) `--nfe 10 --n-rounds 3 --temperature 1.0`, scheduler `cosine` |
| Hit counter | `hmmscan --noali --cpu 32 --tblout <out> --acc Pfam-A.hmm <fasta>`; hits = non-comment tblout lines |
| Fallback | `framework_fallback_per_family_count = {}` on all 3 seeds (zero fallback) |
| Prior mix | `lineageflow_prior_mix = 0.0` on all 3 seeds (no synthetic family-prior mixing) |
| GPU | cuda:1 (RTX 5090, idle) |
| Baseline unchanged | hit counts 158/159/174 == the D-004 run and the pre-D-004 run; baseline **hit-lines byte-identical** to the D-004 run (whole-file sha differs only in the hmmscan comment header, which embeds the input path) |
| Statistics tool | `tools/r1_d004_analysis.py` — validated to reproduce the pre-D-004 R1 3-seed summary **exactly** (`d_pooled=0.110175`, `z=4.0733`) |

---

## 4. Per-seed results (per-record paired $t$, $df = 999$)

| seed | baseline hits | framework hits | Δ | Δ % | mean diff/record | sd diff | $t$ | $p_\text{raw}$ | $d_z$ |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 42 | 158 | 275 | +117 | +74.1 % | +0.117 | 0.6912 | 5.353 | 1.08 × 10⁻⁷ | +0.169 |
| 43 | 159 | 272 | +113 | +71.1 % | +0.113 | 0.6653 | 5.371 | 9.75 × 10⁻⁸ | +0.170 |
| 44 | 174 | 259 | +85 | +48.9 % | +0.085 | 0.6605 | 4.070 | 5.08 × 10⁻⁵ | +0.129 |

All three seeds are direction-consistent (**framework > baseline**) and individually significant.

---

## 5. Aggregation

**(a) Seed-level pooled $t$ on the 3 per-seed totals** (n = 3, df = 2):

| quantity | value |
|---|---:|
| per-seed diffs | [+117, +113, +85] |
| mean diff | +105.0 |
| sd | 17.44 |
| $t$ | 10.431 |
| $p_\text{two-sided}$ | 9.07 × 10⁻³ |
| $d_z$ | +6.022 |

**(b) DerSimonian–Laird random-effects meta of the 3 per-seed $d_z$**:

| quantity | value |
|---|---:|
| per-seed $d_z$ | [+0.169, +0.170, +0.129] |
| $Q$ | 1.102 |
| $I^2$ | 0.0 % |
| $\tau^2$ | 0.0 |
| $d_\text{pooled}$ | **+0.1559** |
| se | 0.01837 |
| $z$ | 8.486 |
| 95 % CI | [+0.120, +0.192] |
| $p_\text{two-sided}$ | ≈ 0 |
| $p_\text{Bonf, } k=7$ | ≈ 0 (significant) |

---

## 6. Comparison across the three R1 real-forward readings

| run | framework init | per-seed framework hits | DL $d_\text{pooled}$ | direction |
|---|---|---|---|---|
| pre-D-004 (contaminated) | zero velocity field + restart RNG | 271 / 213 / 230 | +0.110175 | framework > baseline |
| D-004 (live, uniform init) | real field, **record-identical** $x_0$ | 0 / 0 / 0 | −0.4013 | baseline > framework (collapse) |
| **D-004b (live, random restart init)** | real field, **per-record** random simplex | **275 / 272 / 259** | **+0.1559** | **framework > baseline** |

The pre-D-004 "gain" was a zero-field + restart-RNG artifact (it is not evidence about the real model). D-004 exposed the collapse. D-004b shows that, once the real flow sees a distinct per-record initial condition, the framework arm is a genuine, direction-consistent, Bonferroni-significant **win** — with a pooled effect (0.156) slightly larger than the contaminated run's and far above the collapse.

---

## 7. What this changes (and what it does not)

**Changes (fact):** R1 now has a **clean 3-seed real-forward basis** on which the framework WINS. The earlier statement "R1 cannot be measured on a real-forward basis" is resolved: with the D-004b restart init it can, and the direction is favourable.

**Does not change:** the frozen manuscript / CLAIMS / `tnnls_submission/` numbers (AGENTS.md §3 guardrails #4–#5). The canonical R1 headline remains the synthetic-basis reading; this audit is a **new, additive** observation. R1's status label is untouched here. The pooled effect (0.156) is **below** the 0.8 STRONG-promotion bar, so this does **not** by itself promote R1 to STRONG.

**Caveat (must travel with this result).** The D-004b restart init is a **tool-convention surrogate** (`softmax(randn)` simplex), **not** the upstream intervention/mutation sampler. A reviewer can reasonably ask whether the gain is driven by the framework's restart-blend or by the random init alone. The natural next control is an **init-only vs full-framework** arm at the same NFE to separate the two contributions. Until that control exists, this is evidence that the real-forward basis is a win — not yet a mechanism-attributed win.

---

## 8. Guardrail compliance

| Guardrail (AGENTS.md §3) | Status |
|---|---|
| #1 vendored upstream byte-identical | ✅ untouched |
| #2 additive is the rule | ✅ new evidence dir + new audit doc; no frozen number/label rewritten |
| #3 NO-PUSH | ✅ commit only |
| #4 honest uncertainty — reframe wording, not numbers | ✅ reports the win with its caveat; no frozen number changed |
| #5 TNNLS freeze | ✅ no `tnnls_submission/` number moved |
| #6 per-increment audit doc | ✅ this file |
| #7 stricter = cleaner | ✅ the only code change is the minimal D-004b restart branch (synthetic path byte-unchanged) |

---

## 9. Verification

| Gate | Result |
|---|---|
| `sha256sum --check SHA256SUMS` (evidence dir) | 11/11 OK |
| zero-fallback check (3 manifests) | `framework_fallback_per_family_count = {}` on all 3 |
| baseline hit-line byte-identity vs the D-004 run | ✅ identical on all 3 seeds |
| stats-tool reproduction of the pre-D-004 summary | ✅ exact (`d_pooled=0.110175`, `z=4.0733`) |
| `pytest tests/test_d4_regression_vectors.py -q` | 30 passed |
| `pytest tests/test_adapters/test_lineageflow_smoke.py -q` | 27 passed |
| `ruff check` | All checks passed |
| `python3 tools/check_claims_consistency.py` | No drift detected |

---

## 10. Unresolved / noted

- **Init-only vs full-framework control** (§7): the attribution of the win to the restart-blend vs the random init is not yet separated. This is the load-bearing follow-up for any R1 promotion.
- **The init seed is still not threaded per record.** `_build_initial_state_and_condition` (`tools/eval/baseline.py:44-65`) takes a `seed` argument it never uses. Fixing it would change the shared baseline path and every recorded cell, so it remains untouched; the D-004b restart branch is the freeze-safe lever.
- **`alpha_h` remains a synthetic Dirichlet prior** — the released checkpoint ships no real Pfam priors (documented limitation of D-004, `docs/audit/lineageflow-real-forward-fix.md`).
- **FASTAs are not committed** (large); regenerate from the pipeline in `METADATA.txt`.
