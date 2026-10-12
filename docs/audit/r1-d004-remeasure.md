# R1 re-measure on the genuine real-forward basis (D-004 live) — the collapse

**Date:** 2026-10-12
**Branch:** main
**Base commit:** `bf66aa4` (fix: keep the D-004 real-classifier path live)
**Scope:** R1 cell (`hmmscan_total_hits`), 3 seeds × N=1000 × 2 arms, real-forward basis
**Verdict:** with the D-004 real-classifier path actually live, the framework arm produces **0 Pfam hits on all 3 seeds** (baseline 158/159/174). R1 on the genuine real-forward basis is a **massive regression**, not an improvement. Root cause: a near-uniform, per-record-identical initial state collapses the (now deterministic) real flow onto a single trajectory.

---

## 1. Purpose

`todo.json` gap `R1-REMEASURE-D004` (P0) called for re-running R1 with the
D-004-fixed adapter. The hypothesis was that the recorded R1 3-seed DL meta
(`d_z = +0.110`, PARTIAL) was a **lower bound**, because the adapter had been
integrating an all-zero velocity field — only the restart-blend moved the state
(`docs/audit/r1-3seed-real-ckpt-materialize.md`). This audit records the actual
re-measurement on the real-forward basis.

---

## 2. The D-004 liveness defect (found while launching the re-measure)

The D-004 fix (`a4b58de`) wired `_try_import_lineageflow_upstream` into the
adapter's torch path, but it was **inert in the eval pipeline**:

- `load_real_weights` installs `_install_checkpoint_compat()` **before** `_builder` runs;
- that shim registered a bare `types.ModuleType("core")` with **no `__path__`**;
- a non-package `core` shadowed the vendored upstream tree, so `models.model`'s
  `from core.hf_cache import ...` raised
  `ModuleNotFoundError: 'core' is not a package`;
- `_try_import_lineageflow_upstream()` then returned `None` and the adapter
  silently degraded to the bare-`EsmModel` **zero-velocity field**
  (`h.new_zeros((B, L, 33))`).

So every run labelled "real-ckpt (torch)" — including the pre-D-004 R1 3-seed
run and `wave349-r1-3seed-gpu/` — actually integrated a zero field.

**Fix** (`bf66aa4`, additive): give the fabricated `core` parent a `__path__`
pointing at `data/lineageflow_upstream/core/` when it exists, so real submodules
resolve while the `core.sampler.SamplerConfig` unpickling shim is preserved. No
behaviour change when the upstream tree is absent. After the fix the adapter's
`_model` is `models.model.LineageFlowClassifier` with
`_is_lineageflow_classifier=True`, and the real velocity field is non-zero
(abs-mean 1.4 × 10⁻⁴ to 4.6 × 10⁻⁴), finite, and simplex-tangent.

---

## 3. Observed facts

| Item | Value |
|---|---|
| Evidence directory | `verification_outputs/r1_3seed_d004_q4_2026/` (gitignored; force-added) |
| Seeds | 42, 43, 44 |
| Records per arm per seed | 1000 + 1000 = 6000 total |
| Framework arm mode | **real-forward** — `force_mode="auto"` → `models.model.LineageFlowClassifier` (D-004 live, `bf66aa4`) |
| Protocol | `--n 1000 --upstream-eval-len-bias short` (30–150 AA) `--nfe 10 --n-rounds 3 --temperature 1.0`, scheduler `cosine` |
| Hit counter | `hmmscan --noali --cpu 32 --tblout <out> --acc Pfam-A.hmm <fasta>`; hits = non-comment tblout lines |
| Fallback | `framework_fallback_per_family_count = {}` on all 3 seeds (zero fallback) |
| GPU | cuda:1 (RTX 5090, idle). Not a confound: the pre-D-004 framework arm integrated a zero field, so its output could not depend on the device. |
| Baseline byte-identity | all 3 baseline FASTAs == the pre-D-004 run (sha `4ef0ec94…` / `f0af2d2d…` / `692d523e…`), 158/159/174 hits — **the only variable is the framework arm** |
| Statistics tool | `tools/r1_d004_analysis.py` — validated to reproduce the pre-D-004 R1 3-seed summary **exactly** (`d_pooled=0.110175`, `z=4.0733`) |

---

## 4. Per-seed results (per-record paired $t$, $df = 999$)

| seed | baseline hits | framework hits | Δ | Δ % | mean diff/record | sd diff | $t$ | $p_\text{raw}$ | $d_z$ |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 42 | 158 | 0 | −158 | −100 % | −0.158 | 0.3948 | −12.735 | 1.55 × 10⁻³⁴ | −0.403 |
| 43 | 159 | 0 | −159 | −100 % | −0.159 | 0.3948 | −12.735 | 1.55 × 10⁻³⁴ | −0.403 |
| 44 | 174 | 0 | −174 | −100 % | −0.174 | 0.4242 | −12.973 | 1.11 × 10⁻³⁵ | −0.410 |

All three seeds are direction-consistent (**baseline > framework**) and
individually overwhelming.

---

## 5. Aggregation

**(a) Seed-level pooled $t$ on the 3 per-seed totals** (n = 3, df = 2):

| quantity | value |
|---|---:|
| per-seed diffs | [−158, −159, −174] |
| mean diff | −163.67 |
| $t$ | −31.628 |
| $p_\text{two-sided}$ | 9.98 × 10⁻⁴ |
| $p_\text{Bonf, } k=7$ | 6.99 × 10⁻³ (significant) |

**(b) DerSimonian–Laird random-effects meta of the 3 per-seed $d_z$**:

| quantity | value |
|---|---:|
| per-seed $d_z$ | [−0.403, −0.403, −0.410] |
| $Q$ | 0.172 |
| $I^2$ | 0.0 % |
| $\tau^2$ | 0.0 |
| $d_\text{pooled}$ | **−0.4013** |
| se | 0.01898 |
| $z$ | −21.15 |
| $p_\text{two-sided}$ | ≈ 0 |
| $p_\text{Bonf, } k=7$ | ≈ 0 (significant) |

---

## 6. Root cause — the real flow collapses to one trajectory

The framework's `build_initial_state` → `_synthesize_latent_like_tensor` draws a
**near-uniform** per-position simplex for every record
(`1/K + U(0, 1e-6)`, `adaptive_reflow/adapters/lineageflow.py:518-526`). The
per-record seed only perturbs the 10⁻⁶ jitter. Under the (now live)
**deterministic** real velocity field every record therefore follows the *same*
trajectory:

| arm (seed 42) | unique sequences / 1000 | unique 30-AA prefixes |
|---|---:|---:|
| framework (D-004 live) | 121 | **1** |
| baseline | 1000 | 1000 |

The 121 distinct framework sequences are just 121 distinct **lengths** (30–150
AA) — i.e. truncations of one collapsed sequence. That sequence is a
low-complexity poly-S/A/T string with no Pfam domain, hence 0 hits.

The pre-D-004 runs escaped the collapse only because the zero velocity field left
the **restart-blend perturbation RNG** as the sole source of per-record
diversity. Remove the zero-field accident (i.e. actually run the model) and the
framework arm has no stochastic input at all.

**Bounded diagnostic probe** (N=20, not a recorded result): monkeypatching the
init to a per-record random simplex `softmax(randn(L, K))` — the Wave-41 tool's
noise convention (`tools/run_lineageflow_real_ckpt.py:212-215`) — restores full
diversity (20/20 unique sequences, 20/20 unique 30-AA prefixes) and protein-like
output; HMMER at N=20 gives baseline 4 vs framework 3 (inconclusive at this n).

---

## 7. What this changes (and what it does not)

**Changes (fact):** the pre-D-004 R1 real-ckpt 3-seed gains (framework
271/213/230 vs baseline 158/159/174) were produced by a **zero velocity field**
plus restart-blend RNG — they are **not** evidence about the real LineageFlow
model. On the genuine real-forward basis the framework arm is degenerate
(0 hits).

**Does not change:** the frozen manuscript / CLAIMS / `tnnls_submission/` numbers
(AGENTS.md §3 guardrails #4–#5). The canonical R1 headline is a
**synthetic-basis** reading (`docs/audit/r1-3seed-real-ckpt-materialize.md` §6);
this audit is a **new, additive** observation and does not rewrite it. R1's
status label is untouched here.

**Implication:** R1 cannot be measured on a real-forward basis until the
framework arm has a valid stochastic initialization for the real flow. That is a
distinct follow-up (**D-004b**), recorded in `todo.json`; it is **not** applied
here (it is a framework/method change, not a recording step).

---

## 8. Guardrail compliance

| Guardrail (AGENTS.md §3) | Status |
|---|---|
| #1 vendored upstream byte-identical | ✅ untouched |
| #2 additive is the rule | ✅ new evidence dir + new audit doc + additive `todo.json`; no frozen number/label rewritten |
| #3 NO-PUSH | ✅ commit only |
| #4 honest uncertainty — reframe wording, not numbers | ✅ reports a regression; no frozen number changed |
| #5 TNNLS freeze | ✅ no `tnnls_submission/` number moved |
| #6 per-increment audit doc | ✅ this file |
| #7 stricter = cleaner | ✅ one fresh materialization; the only code change is the minimal D-004 liveness fix |

---

## 9. Verification

| Gate | Result |
|---|---|
| `sha256sum --check SHA256SUMS` (evidence dir) | 11/11 OK |
| zero-fallback check (3 manifests) | `framework_fallback_per_family_count = {}` on all 3 |
| 3 baseline byte-identity vs pre-D-004 | ✅ `4ef0ec94…` / `f0af2d2d…` / `692d523e…` |
| stats-tool reproduction of the pre-D-004 summary | ✅ exact (`d_pooled=0.110175`, `z=4.0733`) |
| `pytest tests/test_d4_regression_vectors.py -q` | 30 passed |
| `pytest tests/test_adapters/test_lineageflow_smoke.py -q` | 26 passed |
| `ruff check` | All checks passed |
| `python3 tools/check_claims_consistency.py` | No drift detected |

---

## 10. Unresolved / noted

- **D-004b (follow-up, not taken here):** give the real-classifier path a
  per-record stochastic initialization (random simplex), branching on
  `_is_lineageflow_classifier` so the synthetic-mode byte-stability (D.4 vectors)
  is untouched. Requires a fresh 3-seed N=1000 re-measure to know whether the
  real-forward basis is competitive with the baseline.
- **`alpha_h` remains a synthetic Dirichlet prior** — the released checkpoint
  ships no real Pfam priors (documented limitation of D-004,
  `docs/audit/lineageflow-real-forward-fix.md`).
- **FASTAs are not committed** (large); regenerate from the pipeline in
  `METADATA.txt`.
