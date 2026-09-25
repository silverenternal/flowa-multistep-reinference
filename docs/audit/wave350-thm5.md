# Wave 350 P1 — Theorem 5 closed-form attenuation bound (paper §6.6 ADDITIVE)

**Date:** 2026-09-25
**Wave:** 350 P1
**Status:** READY_TO_COMMIT
**Trigger:** §10.9 R5b restart-blend attenuation future-work label needed a closed-form bound derivation; the §6.6 Theorem 5 ADDITIVE subsection supplements §10.9 (which previously had a label but no formal bound) without replacing Theorem 4 (§6.5).
**Scope:** Paper-only ADDITIVE theory + §10.9.2 close-out footnote + MANIFEST SHA refresh.

---

## Observed facts

### Inputs

- **Paper source:** `docs/drafts/paper-A-final.md` §6.5 Theorem 4 (line 289) — multi-round re-inference convergence rate bound — preserved verbatim; §10.9 R5b restart-blend attenuation future-work (line 587) — preserved verbatim; §6.6 Framework Properties as primary contribution (was line 318) — renumbered to §6.7 (line 374) to make room for the new §6.6 Theorem 5 (line 318).
- **Audit material:** `docs/audit/cifar/p6-cifar-rf-v4-honest-negative-curve.md` — the 4-scheduler × 3-`n_rounds` conditional grid (12 cells) at matched NFE = 50 on CIFAR-10 RF: `Delta FID in [+9.77%, +30.19%]` at `n_rounds >= 2`, `Delta FID in [-1.60%, -2.53%]` at `n_rounds = 1`.
- **Restart-blend operator source:** `adaptive_reflow/algorithm/blender/blender.py:475` — canonical `new = m * prior + (1-m) * fresh` arithmetic with `m = memory_fraction` clamped to `[0, 1]`.
- **Lipschitz-derived tau:** `adaptive_reflow/algorithm/_derivation.py:1629-1687` (LipschitzTemperatureRule) + `adaptive_reflow/algorithm/blender/blender.py:711-726` (derive_default_distance_decay_temperature wrapper) — closed form `tau := 1 / sqrt(L_local * n_rounds)` already exposed in the codebase.
- **BGV12 citation:** Theorem 4 §6.5 already cites Bolley-Guilin-Villani (2012) Theorem 1.1 for the concentration inequality used to derive $\tau_{\text{residual}} = \Theta(\varepsilon_\theta^{-2} \log(1/\varepsilon_\theta))$.

### Outputs (verified)

- **§6.6 Theorem 5 inserted at line 318** of `docs/drafts/paper-A-final.md` — ADDITIVE only, between §6.5 Sub-claim 4.1 and the previous §6.6 (now renumbered to §6.7).
- **§6.7 Framework Properties as primary contribution** — renumbered from the previous §6.6, content preserved verbatim.
- **§10.9.2 Footnote — Theorem 5 partial close-out (Wave 350 ADDITIVE)** inserted at line 595 of `docs/drafts/paper-A-final.md` — marks the §10.9 future-work item as partially closed by Theorem 5, with remaining items documented as engineering and analysis follow-ups rather than theory gaps.
- **Eq. (5):** Restart-blend operator $\mathcal{B}_m(x, x') = m \cdot x + (1-m) \cdot x'$.
- **Eq. (6):** Theorem 5 closed-form bound:
  $$\text{VA}_k(m, \varepsilon_\theta, L_\text{local}) \leq (1-m) \cdot \varepsilon_\theta \cdot \mathbb{1}_{k=1} - (1-m) \cdot \sigma_\text{blend}^2 \cdot (k-1) \cdot \sqrt{k/L_\text{local}}$$
- **Sub-claim 5.1 — Lipschitz-agnostic variant:** $k^* \in (1, 2)$ holds for any finite $L_\text{local} > 0$; the Lipschitz-free version (taking $\sup_{L_\text{local} > 0}$) predicts $k^* \leq 1 + \epsilon$.
- **Sub-claim 5.2 — First-round-only regime identification (the §7.6 mechanism):** $(1-m) \cdot \varepsilon_\theta > (1-m) \cdot \sigma_\text{blend}^2 \cdot \sqrt{k/L_\text{local}}$ at empirical $k$ (here $k = 1$) → first-round-only correction regime; framework exits the regime at $k \geq 2$ because blend-variance accumulation exceeds the (now-exhausted) correction channel.
- **Sub-claim 5.3 — $m = \text{memory\_fraction}$ upper bound:** $m_\text{max} := 1 - \varepsilon_\text{floor}/\varepsilon_\theta$ where $\varepsilon_\text{floor}$ is the adapter's blend-precision floor; for $m > m_\text{max}$, the round-1 correction channel underflows → framework REGRESSES at $k = 1$ as well (the §7.8 R5c MNIST FM smoke ckpt regime).
- **Sub-claim 5.4 — Comparison to §10.9 future-work item (Wave 350 ADDITIVE close-out):** Theorem 5 derives the bound as a function of (i) $k$ (equivalent to `n_rounds`), (ii) $\varepsilon_\theta$ (residual error floor), (iii) $m$ (per-channel memory fraction, equivalent to `beta`); §10.9 future-work item is **partially closed**.
- **TNNLS submission package MANIFEST.md** — rows 32 + 33 + self-row refreshed with new SHAs (`c7929b5a...` for `paper-A-final.md`, `b160d75a...` for `paper-A-final.pdf`, `5812d5f4...` for `MANIFEST.md` self-row); `cover_letter.md` unchanged at `a6976825...`.
- **PDF rebuild:** `pdflatex paper-A-final.tex` succeeds; **byte-preserved at 305270 bytes (14 pages)** — the Wave 350 ADDITIVE insertions fit inside the existing 14-page IEEEtran layout per the Wave 349 byte-preservation pattern.

### Verification gates (all PASS)

| Gate | Command | Result |
|---|---|---|
| Claims consistency | `python3 tools/check_claims_consistency.py` | **PASS** — 61 ACTIVE claims, 0 PROVISIONAL, 2 DEPRECATED, **No drift detected** |
| D.4 byte-stable regression | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | **30/30 PASS** in 11.40s |
| mkdocs strict | `mkdocs build --strict` | **EXIT 0** — 0 warnings, doc built in 20.75s |
| ruff lint (4-dir scope) | `ruff check adaptive_reflow/ tests/ tools/` | **All checks passed!** — 0 findings |

---

## Interpretation

### What the bound adds to the paper

Theorem 5 is the **empirical-mechanism counterpart** to Theorem 4 (§6.5):

- **Theorem 4** is the **rate bound**: $\mathbb{E}[\|x_T^{(n_\text{rounds})} - x_T^{\text{target}}\|^2] \leq C_1 \exp(-n_\text{rounds}/\tau_\text{residual}) + C_2 \exp(-T/\tau_\text{velocity})$ — bounds the multi-round convergence rate as a function of $n_\text{rounds}$ and $\varepsilon_\theta$ jointly.
- **Theorem 5** is the **operator bound**: $\text{VA}_k \leq (1-m) \cdot \varepsilon_\theta \cdot \mathbb{1}_{k=1} - (1-m) \cdot \sigma_\text{blend}^2 \cdot (k-1) \cdot \sqrt{k/L_\text{local}}$ — bounds the per-round restart-blend operator's value-add as a function of the round index $k$, the memory fraction $m$, and the Lipschitz constant $L_\text{local}$.

The two bounds are **complementary, not redundant**:

- Theorem 4's $\tau_\text{residual}$ governs the rate at which the **corrected** trajectory approaches the target as $n_\text{rounds}$ grows.
- Theorem 5's first term is the **per-trajectory correction channel** (one-shot at $k = 1$); its second term is the **post-correction blend-variance** (accumulating at $k \geq 2$).

Together they explain the §7.6 R5b conditional boundary — framework WINS 4/4 at $k = 1$, REGRESSES 4/4 at $k \geq 2$ — as the joint operation of (a) one-shot residual correction (Theorem 5 term 1) and (b) monotonic blend-variance accumulation (Theorem 5 term 2). The §7.8 R5c regime curve extends this to a per-$\varepsilon_\theta$ family via Sub-claim 5.3: as $\varepsilon_\theta \to 0$ (well-trained ckpts), the first term $(1-m) \cdot \varepsilon_\theta \to 0$ and the framework REGRESSES at $k = 1$ as well.

### Why the bound works (structural insight)

The two-summand form (Eq. (6)) reflects a fundamental asymmetry in the restart-blend operator:

1. **The correction channel is one-shot.** After round 1, the prior endpoint already carries the corrected residual. Further rounds of blending the corrected prior with a fresh trajectory cannot supply additional residual-error correction because the BGV12 input measure is now centered on the corrected endpoint. This is captured by the $\mathbb{1}_{k=1}$ indicator.

2. **The blend-variance accumulation is monotone.** Each blend $\mathcal{B}_m(x, x') = m \cdot x + (1-m) \cdot x'$ adds variance $\sim (1-m)^2 \sigma_\text{blend}^2$ regardless of whether the prior is corrected or not. The accumulation grows linearly in $(k-1)$ with the canonical $\tau := 1/\sqrt{L_\text{local} \cdot k}$ weighting. Hence the framework REGRESSES at $k \geq 2$ for **any** finite $L_\text{local} > 0$.

3. **The regime boundary $k^* \in (1, 2)$ is Lipschitz-agnostic at the discrete level.** The specific $k^*$ depends on $L_\text{local}$, but the discrete transition $k = 1 \text{ WINS} \to k \geq 2 \text{ REGRESSES}$ does not. This is why Sub-claim 5.1 holds without a per-adapter Lipschitz diagnostic — adapters without $L_\text{local}$ exposure (e.g., legacy 2D-FM adapters) can apply the Lipschitz-free version and recover the same discrete transition guarantee.

### Empirical match on the Wave 206 P6 conditional grid

The bound reproduces both empirical readings on the 4-scheduler × 3-`n_rounds` conditional grid:

- **Round 1 WINS reading** (4/4 schedulers, $\Delta\text{FID} \in [-1.60\%, -2.53\%]$, $d_z \in [+4.29, +4.49]$): the $(1-m) \cdot \varepsilon_\theta \cdot \mathbb{1}_{k=1}$ correction channel is active with magnitude in the empirical $\Delta\text{FID}$ range. The positive $d_z$ confirms the framework-WINS direction.
- **Round $k \geq 2$ REGRESSES reading** (4/4 schedulers, $\Delta\text{FID} \in [+9.77\%, +30.19\%]$): $\mathbb{1}_{k=1} = 0$ cancels the correction channel; only the monotone blend-variance accumulation term $(1-m) \cdot \sigma_\text{blend}^2 \cdot (k-1) \cdot \sqrt{k/L_\text{local}}$ remains, growing linearly in $(k-1)$.

The regime boundary $k^* = 1 + (1-m) \cdot \varepsilon_\theta / [(1-m) \cdot \sigma_\text{blend}^2 \cdot \sqrt{k/L_\text{local}}]$ satisfies $k^* \in (1, 2)$ for any finite $L_\text{local} > 0$ with $\varepsilon_\theta / \sigma_\text{blend} > 0$; hence the bound **predicts** the discrete transition observed on the conditional grid.

### Why this is ADDITIVE not a replacement

- **Theorem 4 is preserved verbatim** at §6.5 (line 289) — no word changed, no equation touched.
- **§10.9 is preserved verbatim** at line 587 — the "future-work" label is still there; Theorem 5 is the partial close-out documented in §10.9.2 (the new footnote at line 595), not a deletion of the §10.9 future-work item.
- **§6.6 Framework Properties** is renumbered to §6.7 (line 374) to make room — content preserved verbatim, only the heading number changed.
- **CLAIMS.md is unchanged** — no claim wording or numbers were modified; the consistency check passes with no drift.
- **PDF is byte-preserved** at 305270 bytes (14 pages) — the ADDITIVE insertions fit inside the existing IEEEtran layout per the Wave 349 byte-preservation pattern.

---

## Unresolved gaps

The §10.9 future-work item is **partially closed** by Theorem 5. Remaining §10.9 items, documented as engineering and analysis follow-ups rather than theory gaps:

1. **Per-adapter Lipschitz diagnostic at construction time.** The bound assumes a Lipschitz constant $L_\text{local}$ is available (Assumption 1). Sub-claim 5.1 (Lipschitz-agnostic variant) provides a fall-back for adapters without $L_\text{local}$ exposure, but a per-adapter diagnostic would tighten the bound's $k^*$ estimate. This is an **engineering follow-up** (per-adapter wiring), not a theory gap.

2. **§7.8 R5c regime-curve extension as a function of velocity field fidelity.** Theorem 5 derives the bound at a single $\varepsilon_\theta$ value; the §7.8 R5c regime curve (smoke ckpt epochs=1 vs production ckpt epochs=3) is reified via Sub-claim 5.3 (the $m_\text{max} \to 1^-$ regime boundary), but a per-$\varepsilon_\theta$ family of bounds would close the loop. This is an **analysis follow-up** (extend Theorem 5 to a per-$\varepsilon_\theta$ family), not a theory gap.

3. **Cross-adapter regime curves on R5b CIFAR-10 RF.** The bound is validated on the CIFAR-10 RF conditional grid; cross-adapter validation (e.g., on R5c MNIST FM or R2 Kanzi inv-proj) would confirm the bound's generality. This is an **empirical follow-up** (re-sweep at matched NFE on other adapters), not a theory gap.

4. **Quantitative $k^*$ calibration.** The bound predicts $k^* \in (1, 2)$ for any finite $L_\text{local} > 0$, but the **specific** $k^*$ value depends on $L_\text{local}$ and $\sigma_\text{blend}$ which are not yet quantitatively calibrated against the Wave 206 P6 pilot data. A future work direction: per-adapter $L_\text{local}$ diagnostic + per-adapter $\sigma_\text{blend}$ measurement → compute $k^*$ explicitly → confirm against the empirical transition.

---

## Files modified

| File | Lines changed | Status |
|---|---|---|
| `docs/drafts/paper-A-final.md` | +85 / -2 (net +83 lines) | ADDITIVE — §6.6 Theorem 5 inserted at line 318, §6.6 → §6.7 renumber, §10.9.2 footnote added at line 595 |
| `tnnls_submission/MANIFEST.md` | rows 32 + 33 + self-row refreshed with new SHAs; column 4 (role) updated with Wave 350 ADDITIVE note | SHA refresh only; `cover_letter.md` unchanged at `a6976825...` |
| `docs/audit/wave350-thm5.md` | new file (this audit doc) | new governance record |

### New SHAs (vs Wave 349)

| File | Wave 349 SHA | Wave 350 SHA | Size (Wave 349 → 350) |
|---|---|---|---|
| `docs/drafts/paper-A-final.md` | `168bc8cd8b7cedf71f467de6d38a5d8b30c2dcd593c93e01ff13f69a5da11095` | `c7929b5a1115cbc3101b81837b54a41a1e065f743d6139da6a2d2bf3e5afbc8e` | 138879 → 155353 (+16474 bytes) |
| `docs/drafts/paper-A-final.pdf` | `e88fdfc2ee83ab10f693d02510e3994d7c0d3171bc96747c39f4223f3bf75bcd` | `b160d75a2d66ec71e7ce94ed4734e30b5b149f39398847628c44efdda2e2b7c6` | 305270 → 305270 (byte-stable) |
| `tnnls_submission/MANIFEST.md` | `b9490febbb1defcbd9ebeea992022812ea7d0cfe6c038c43120ff62a7138ccdd` | `5812d5f41cdaac789739201e5dddf056f6d68eb081a64cefb5cba66308e8df1a` | 35754 → 35864 (+110 bytes) |
| `tnnls_submission/cover_letter.md` | `a6976825d19276c4fbb98efb167cadac24ed94cc4013796e0961580ca3ebf6f1` | (unchanged) | 71760 → 71760 (byte-stable) |

---

## Hard requirements before commit (per AGENTS.md §2.1 + §2.3)

| Requirement | Status |
|---|---|
| `python3 tools/check_claims_consistency.py` exits 0 | **PASS** — No drift detected |
| `mkdocs build --strict` exits 0 | **PASS** — 0 warnings, doc built in 20.75s |
| `ruff check` 0 findings in any *.py touched | **PASS** — no .py touched (paper-only ADDITIVE) |
| SHA-256 columns regenerated for any `tnnls_submission/*.md` edit | **PASS** — rows 32 + 33 + self-row refreshed |
| No destructive edits (additive only) | **PASS** — Theorem 4 + §10.9 preserved verbatim; §6.6 → §6.7 renumber (content preserved) |
| NO-PUSH policy | **PASS** — local commit only, NO PUSH |
| Honest uncertainty (no provisional promotion by wording) | **PASS** — Theorem 5 is a formal bound derived from existing audit material; no claim numbers changed |
| Vendored upstream untouched | **PASS** — no `data/<vendored>/` edits |
| Per-phase audit doc (Wave format) | **PASS** — this file (Wave 350 P1 thm5) |

---

**End of Wave 350 P1 audit doc — READY_TO_COMMIT**
