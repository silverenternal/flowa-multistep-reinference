# R1 3-seed real-ckpt materialization — LineageFlow HMMER `hmmscan_total_hits`

**Date:** 2026-10-12
**Branch:** main
**Base commit:** `07098f6` (repo-wide R2 terminology unification, pass #10)
**Scope:** R1 cell (`hmmscan_total_hits`), 3 seeds × N=1000 × 2 arms
**Verdict:** direction-consistent framework-WINS on all 3 seeds; DL-meta Bonferroni-significant; **effect size below the 0.8 STRONG bar → R1 stays PARTIAL**

---

## 1. Purpose

The R1 cell's canonical headline (Wave 158: baseline 158 → framework 342, +116 %,
$d_z = +0.182$) is a **single-seed (seed = 42)** reading. The Wave 280 P 3-seed pool
that briefly promoted R1 to STRONG was **invalidated** (Wave 308 P1) by seed-43/44
framework-fallback contamination. The user directed **"先按 R1 3-seed 开工"** — start the
R1 3-seed materialization — and chose the **real-ckpt (torch)** basis for the framework
arm over forcing the synthetic field.

This audit records a fresh, zero-fallback, N=1000-per-arm, 3-seed materialization on the
real-ckpt basis, and the resulting per-seed + pooled statistics. It is **additive**: the
existing R1 status label (PARTIAL) and the existing manuscript numbers are preserved
verbatim (AGENTS.md §3 guardrail #4 — reframe wording, do not change numbers).

---

## 2. Observed facts

| Item | Value |
|---|---|
| Evidence directory | `verification_outputs/r1_3seed_real_ckpt_q4_2026/` (gitignored; force-added) |
| Seeds | 42, 43, 44 |
| Records per arm per seed | 1000 (baseline) + 1000 (framework) = 6000 total |
| Framework arm mode | **real-ckpt (torch)** — `force_mode="auto"` (Wave 349 P4) → ESM-2 + flow head, ckpt `data/lineageflow/lineageflow-rp55.ckpt` |
| Protocol | `--n 1000 --upstream-eval-len-bias short` (30–150 AA) `--nfe 10 --n-rounds 3 --temperature 1.0`, scheduler `cosine` |
| Hit counter | `hmmscan --noali --cpu 32 --tblout <out> --acc Pfam-A.hmm <fasta>`; hits = non-comment tblout lines (== vendored `hmmscan_total_hits`) |
| Fallback | `framework_fallback_per_family_count = {}` on **all 3 seeds** (zero fallback) |
| GPU | cuda:0 (RTX PRO 6000 Blackwell) |
| Baseline byte-identity | seed-42 baseline FASTA sha256 `4ef0ec94…` **== Wave 158 baseline** (baseline arm 158 hits, identical) |
| Framework divergence | seed-42 framework FASTA sha256 `4791db44…` **≠ Wave 158 framework** (271 vs 342 hits) — the basis fork (§6) |

---

## 3. Per-seed results (per-record paired $t$, $df = 999$)

| seed | baseline hits | framework hits | Δ | Δ % | mean diff/record | sd diff | $t$ | $p_\text{raw}$ | $d_z$ |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 42 | 158 | 271 | +113 | +71.52 % | 0.113 | 0.6875 | 5.197 | 2.45 × 10⁻⁷ | +0.164 |
| 43 | 159 | 213 | +54 | +33.96 % | 0.054 | 0.6289 | 2.715 | 6.73 × 10⁻³ | +0.086 |
| 44 | 174 | 230 | +56 | +32.18 % | 0.056 | 0.6952 | 2.547 | 1.10 × 10⁻² | +0.081 |

All three seeds are **direction-consistent (framework > baseline)** and individually
significant at raw α = 0.05. The seed-42 reading (+71.5 %) is the largest; seeds 43/44
land at ≈ +33 %.

---

## 4. Aggregation

Two aggregations are reported (the honest pooled effect is the second):

**(a) Seed-level pooled $t$ on the 3 per-seed totals** (n = 3, df = 2):

| quantity | value |
|---|---:|
| per-seed diffs | [+113, +54, +56] |
| mean diff | 74.33 |
| sd | 33.50 |
| $t$ | 3.843 |
| $p_\text{two-sided}$ | 0.06152 |
| $d_z$ | **+2.219** |
| $p_\text{Bonf, } k=7$ | 0.4307 (not significant) |

The seed-level $d_z = +2.219$ is **inflated by small-$n$ seed variance** (sd of 3 totals),
not a real per-record effect. It is reported for completeness only.

**(b) DerSimonian–Laird random-effects meta of the 3 per-seed $d_z$** (the honest pooled
effect):

| quantity | value |
|---|---:|
| per-seed $d_z$ | [+0.164, +0.086, +0.081] |
| $Q$ | 4.360 |
| $I^2$ | 54.13 % |
| $\tau^2$ | 0.001188 |
| $d_\text{pooled}$ | **+0.110** |
| se | 0.02705 |
| $z$ | 4.073 |
| $p_\text{two-sided}$ | 4.635 × 10⁻⁵ |
| $p_\text{Bonf, } k=7$ | **3.244 × 10⁻⁴** (significant) |
| $p_\text{Bonf, } k=16$ | 7.416 × 10⁻⁴ (significant) |

---

## 5. Verdict against the STRONG-promotion bar

The pre-registered STRONG bar is **3-seed pooled ∧ $d_z > 0.8$ ∧ Bonferroni $p < \alpha$ ∧
direction-consistent** (`docs/audit/wave298-p2-methodology-innovations.md:505`).

| clause | this run | pass? |
|---|---|---|
| 3-seed pooled | seeds 42/43/44, zero fallback | ✅ |
| $d_z > 0.8$ | DL $d_z = +0.110$ (seed-level +2.219 is small-$n$-inflated) | ❌ |
| Bonferroni $p < \alpha$ | $p_{\text{Bonf},k=7} = 3.24 \times 10^{-4} < 0.007143$ | ✅ |
| direction-consistent | 3/3 framework-WINS | ✅ |

**R1 does NOT meet the STRONG bar** — the pooled effect size ($d_z = +0.110$) is well below
0.8. **R1 status therefore remains PARTIAL.** What this run *does* establish is that the
direction is reproducible across 3 genuinely-independent zero-fallback seeds and that the
pooled effect is Bonferroni-significant at the R-level $k = 7$ family. It does **not**
rehabilitate R1 to STRONG.

---

## 6. The basis fork (synthetic → real-ckpt) — the load-bearing disclosure

The Wave 158 canonical headline (158 → 342, +116 %, $d_z = +0.182$) was generated with
`tools/gen_lineageflow_n1000_fastas.py` hardcoding `force_mode="synthetic"` — an **untrained
NumPy velocity field**, *not* a trained FM model (see the adapter docstring at
`adaptive_reflow/adapters/lineageflow.py:43-48`). Wave 349 P4 changed the gen script to
`force_mode="auto"` (`tools/gen_lineageflow_n1000_fastas.py`, `docs/audit/wave349-gpu-acceleration.md`
§2), which loads the real `lineageflow-rp55.ckpt` (10.5 GB, present on disk).

The **baseline arm is identical** between the two bases (seed-42 baseline FASTA
`4ef0ec94…`, 158 hits, byte-identical to Wave 158). The **framework arm differs**: the
real-ckpt basis yields 271 hits on seed 42 vs 342 on the synthetic basis. The framework
arm is deterministic in both modes (an N=8 two-run check is byte-identical), so the 271 vs
342 gap is a genuine basis effect, not run-to-run noise.

Consequence: the canonical R1 headline (+116 %) is a **synthetic-velocity-field** number;
the real-ckpt basis gives a smaller but still positive, direction-consistent improvement
(seed-42 +71.5 %, 3-seed DL $d_z = +0.110$). This audit records the fork; it does **not**
change the manuscript's cited number (the manuscript R1 row is preserved verbatim; an
additive disclosure footnote is appended in §7.2).

---

## 7. Guardrail compliance

| Guardrail (AGENTS.md §3) | Status |
|---|---|
| #1 vendored upstream byte-identical | ✅ untouched (no `data/` file changed) |
| #2 additive is the rule | ✅ new evidence dir + new audit doc + additive CLAIMS/footnote entries; no number or label rewritten |
| #3 NO-PUSH | ✅ commit only |
| #4 honest uncertainty — reframe wording, not numbers | ✅ R1 stays PARTIAL; the existing `d_z = +0.182` headline is preserved verbatim; the new run is disclosed additively |
| #5 TNNLS freeze | ✅ no `tnnls_submission/` number moved; submission SHA ledger untouched |
| #6 per-increment audit doc | ✅ this file |
| #7 stricter = cleaner | ✅ no long sweep re-run for a recorded result; a single fresh materialization; minimal surface touched |

---

## 8. Verification

| Gate | Result |
|---|---|
| `sha256sum --check SHA256SUMS` (evidence dir) | 10/10 OK |
| zero-fallback check (3 manifests) | `framework_fallback_per_family_count = {}` on all 3 |
| `n_records_processed == planned` | 1000/1000 per arm per seed |
| seed-42 baseline byte-identity vs Wave 158 | ✅ (`4ef0ec94…`, 158 hits) |
| `python3 tools/check_claims_consistency.py` | No drift detected |
| `python3 -m pytest tests/test_d4_regression_vectors.py -q` | 30 passed |
| `ruff check` | All checks passed |
| `mkdocs build --strict` | exit 0, 0 warnings |

---

## 9. Unresolved / noted

- **The manuscript R1 row is preserved verbatim.** The §7.2 `.md` / `.tex` R1 row still
  cites the Wave 158 single-seed synthetic-basis reading ($d_z = +0.182$, "3-seed pool
  invalidated"). A single **additive** footnote discloses the real-ckpt 3-seed run and the
  basis fork; no number, no status label moves.
- **The "single-seed-disclosed" qualifier is now superseded in fact** by this zero-fallback
  3-seed run, but the reviewer-facing label is left unchanged to avoid a freeze-time label
  edit. A label refresh (e.g. `PARTIAL / 3-seed real-ckpt`) is a possible follow-up, not
  taken here.
- **Seed-43/44 framework arms are materially weaker** than seed 42 (+33 % vs +72 %). This
  is the dominant source of the $I^2 = 54\%$ heterogeneity; the DL meta absorbs it. The
  honest pooled effect ($d_z = +0.110$) is therefore far below the seed-42 reading.
- **The Wave 349 N=20 retro-validation claim** ("Wave 280 P contamination falsified at both
  modes") was based on N=20 probes; this audit supersedes it with the full N=1000
  materialization, which is the conclusive evidence.
- **Evidence is gitignored.** `verification_outputs/` is gitignored; the 10 committed
  artifacts (3 manifests, 6 hit tables, `summary.json`) require `git add -f`. The 6 FASTAs
  are **not** committed (large).
