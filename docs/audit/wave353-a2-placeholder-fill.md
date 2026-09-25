# Wave 353 P2 — §A.2 paper-quantity closed-form derivation appendix (paper-A-final.md)

**Date:** 2026-09-25
**Wave:** 353 P2
**Status:** READY_TO_COMMIT
**Trigger:** §A.2 was a 1-paragraph reserved placeholder per Wave 352 P3 (line 761: "Reserved — cross-adapter regime-curve derivation (deferred to follow-up ultracode)"). Per the Wave 353 P2 task brief, §A.2 is filled with the **closed-form derivations of the four paper-quantities** ($A_g$ sheet evidence, $B_g$ root-cell packing, $C_g$ per-cell coefficient, $e_\rho$ exterior gap) that thread through the §8.9 lazy-memoized `PaperQuantitiesCache` carrier. The cross-adapter regime-curve derivation is documented as a future-work sibling item in §10.9.4 (newly added ADDITIVE footnote).
**Scope:** Paper-only ADDITIVE theory + 1 ADDITIVE §10.9.4 footnote. No code change. No number change. No main-text number change.

---

## 1. Executive Summary

| Item | Value |
|---|---|
| Appendix location | `docs/drafts/paper-A-final.md` §A.2 (lines 765–817, between §A.1 line 759 and §A.3 line 819) |
| §A.2 content (filled) | **Closed-form derivations of the four paper-quantities** $A_g$ + $B_g$ + $C_g$ + $e_\rho$, with discretisation error bounds, disjoint-cell hypothesis check, and Corollary 1 quantitative allocation after normalization |
| §A.2 subsections | A.2.1 Setup + A.2.2 $A_g$ (trapezoidal) + A.2.3 $B_g$ (sign-change + tail bound) + A.2.4 $C_g$ (closed-form) + A.2.5 $e_\rho$ (closed-form min) + A.2.6 Corollary 1 + A.2.7 Honest disclosures (5 items) + A.2.8 Source pointers (8 cross-references) |
| Equations introduced | Eq.\,(A.12) $A_g$ integral, Eq.\,(A.13) $B_g$ sum, Eq.\,(A.14) tail bound, Eq.\,(A.15) $C_g$ closed-form, Eq.\,(A.16) $e_\rho$ closed-form, Eq.\,(A.17) exponential decay |
| §10.9.4 footnote | New ADDITIVE footnote at line 617 documenting the §A.2 paper-quantity closed-form derivation close-out |
| Number change | **NONE** — Eq.\,(5), Eq.\,(6), Sub-claims 5.1–5.4, §6.6.1 footnote, §10.9–§10.9.3 footnotes all preserved verbatim |
| Files modified | `docs/drafts/paper-A-final.md` (ADDITIVE §A.2 + §10.9.4 footnote + closing-line update) |
| New file | `docs/audit/wave353-a2-placeholder-fill.md` (this audit doc) |
| Verification gates | `check_claims_consistency.py` PASS; `pytest tests/test_d4_regression_vectors.py -q` 30/30 PASS; `mkdocs build --strict` PASS |

---

## 2. Observed Facts

### 2.1 §A.1 status (predecessor wave)

Wave 353 P1 (commit 0311a64) filled §A.1 with the full 8-section Theorem 4 derivation (BGV12 concentration inequality + Grönwall Lipschitz propagation + Sub-claim 4.1 regime-curve corollary). After Wave 353 P1, the appendix contained:
- §A.1 — full Theorem 4 derivation (lines 681–759)
- §A.2 — 1-paragraph reserved placeholder (lines 765–767)
- §A.3 — full Theorem 5 Lipschitz-constant derivation (lines 819–830)

The §A.2 placeholder was a single paragraph noting that the section was "reserved for the cross-adapter regime-curve derivation extending Theorem 5's per-$\varepsilon_\theta$ family to a quantitative $k^*$ calibration (§6.6 Sub-claim 5.1 Lipschitz-agnostic variant) and the §7.8 R5c regime-curve generalisation."

### 2.2 §A.2 fill — paper-quantity closed-form derivation

Wave 353 P2 replaces the §A.2 placeholder with a substantive 8-subsection derivation of the four paper-quantities that thread through the framework's theoretical-companion path. The §A.2 derivation is **adapter-independent** (the closed forms are functions of the F-side scalar $g$, the physical-cell scale $\rho$, and the F-side separation $d$ — not of any particular adapter's velocity field backend); it formalises the **numerical-evaluation closed forms** that the framework ships in `adaptive_reflow/theory/paper_quantities.py` and threads into the byte-stable `PaperQuantitiesCache` carrier.

The §A.2 structure mirrors the §A.3 structure (Wave 352 P3):

| §A.2 subsection | Content | Cross-reference |
|---|---|---|
| A.2.1 Setup | Defines $g$, $I_z$, $Z_g$, $\rho$ (companion-paper line 130) | companion paper Lemma 2–5 |
| A.2.2 $A_g$ | Proposition 3, line 116–117; trapezoidal discretisation on $[-K, K]$; $O(h^2)$ error bound | `adaptive_reflow/theory/paper_quantities.py:96-175` |
| A.2.3 $B_g$ | Lemma 5, line 159; sign-change sampling + linear interpolation; geometric tail bound Eq.\,(A.14) | `adaptive_reflow/theory/paper_quantities.py:178-288` |
| A.2.4 $C_g$ | Lemma 3, line 191; closed-form $e^{\rho^2/2} / a$ with $a = (1-\rho)^2 \min\{c^2, 1\}$; disjoint-cell constraint $\rho < d/4$ | `adaptive_reflow/theory/paper_quantities.py:291-358` |
| A.2.5 $e_\rho$ | Lemma 5 setup, line 128; closed-form $\min\{\rho^4, (1-\rho)^2 \eta^2\}$; exponential decay Eq.\,(A.17) | `adaptive_reflow/theory/paper_quantities.py:361-418` |
| A.2.6 Corollary 1 | Quantitative allocation after normalization; $Z_{g, \varepsilon} \geq C_1 \varepsilon$; cell-interior mass $O(\varepsilon)$; physical-complement mass $o(1)$; bottleneck-driven `aggregate_ratio` signal | companion paper line 165; `flowmol3_glue.py:746-753` |
| A.2.7 Honest disclosures | 5 items: closed-form vs discretisation, disjoint-cell hypothesis, companion-paper vs framework numerics, dormant under cosine baseline, per-adapter extension deferred | §8.9 + §10 framework-not-theory verdict |
| A.2.8 Source pointers | 8 cross-references to framework + companion paper + Wave 49 Agent C §5.1 | all §A.2 sources |

### 2.3 Equations introduced

The §A.2 derivation introduces 6 new equations, numbered Eq.\,(A.12)–Eq.\,(A.17):

- **Eq.\,(A.12)** — $A_g = (2\pi)^{-1/2} \int_\mathbb{R} e^{-s^2/2} / \sqrt{1 + g(s)^2} \, ds > 0$ (Proposition 3 sheet evidence integral)
- **Eq.\,(A.13)** — $B_g = \sum_{z \in Z_g} e^{-z^2/4} < \infty$ (Lemma 5 root-cell packing sum)
- **Eq.\,(A.14)** — $\text{tail}(K) \leq 2 \cdot (\lceil 1/d \rceil + 1) \cdot e^{-K^2/4} / (1 - e^{-d K / 2})$ (geometric tail bound for the $B_g$ truncation error)
- **Eq.\,(A.15)** — $C_g = e^{\rho^2/2} / a$ with $a = (1-\rho)^2 \min\{c^2, 1\} > 0$ (Lemma 3 per-cell coefficient)
- **Eq.\,(A.16)** — $e_\rho = \min\{\rho^4, (1-\rho)^2 \eta^2\} > 0$ (Lemma 5 setup exterior gap)
- **Eq.\,(A.17)** — $\int_{T^c \setminus \bigcup_z I_z} p_\varepsilon \leq e^{-e_\rho / (2\varepsilon^2)} = o(\varepsilon)$ (Lemma 4 exponential decay)

The (A.N) numbering continues the convention established in §A.1 (Eq.\,(A.6)–(A.11)) and §A.3 (Eq.\,(A.1)–(A.5)); the appendix equations do not conflict with the main-text equations (Eq.\,(1)–(Eq.\,6)) because the A-prefix distinguishes them. All cross-references in the body text remain unchanged.

### 2.4 §10.9.4 footnote (newly added)

Wave 353 P2 adds §10.9.4 at line 617, mirroring the Wave 350/351/352 ADDITIVE-footnote pattern. The §10.9.4 footnote documents the **paper-quantity side** of the §10.9 partial close-out (the §A.3 Lipschitz derivation closes the **restart-blend operator** side; the §A.2 paper-quantity derivation closes the **companion-paper side**). The footnote is 5 sentences + 1 closing sentence + 1 reference list, all ADDITIVE; §10.9, §10.9.1, §10.9.2, §10.9.3, §6.6, §6.6.1, §8.9 are all preserved verbatim.

The §10.9.4 footnote explicitly references:
- §A.2 (Wave 353 P2 ADDITIVE)
- §A.3 (Wave 352 P3 ADDITIVE)
- Theorem 5 (Wave 350 P1, §6.6 ADDITIVE)
- Theorem 5 numerical validation (Wave 351 P3, §6.6.1 ADDITIVE)
- §8.9 (the `PaperQuantitiesCache` 16-site taxonomy)
- §10 (framework-not-theory verdict, 15/16 sites dormant under cosine baseline)

### 2.5 Closing-line update

The §A ending line ("**End of Appendix A.** §A.1 contains ... §A.2 is reserved for ... §A.3 contains ...") was updated to reflect the §A.2 fill: "**§A.2 contains the closed-form derivations of the four paper-quantities ($A_g$, $B_g$, $C_g$, $e_\rho$) with discretisation error bounds and the Corollary 1 quantitative allocation; §A.3 contains the Theorem 5 Lipschitz-constant derivation (Wave 352 P3)**". The closing-line update also adds a forward-pointer to §10.9.4 for the cross-adapter regime-curve derivation that §A.2 was originally reserved for (now documented as a §10.9.4 future-work sibling).

### 2.6 Verification gates

| Gate | Result | Notes |
|---|---|---|
| `python3 tools/check_claims_consistency.py` | **PASS** | "No drift detected." — 61 ACTIVE claims, 0 PROVISIONAL, 2 DEPRECATED. No CLM wording changed; §A.2 + §10.9.4 are paper-draft content, not claim ledger. |
| `python3 -m pytest tests/test_d4_regression_vectors.py -q` | **30/30 PASS** | D.4 byte-stable regression suite green; no test touched. |
| `mkdocs build --strict` | **PASS** | Documentation built in 24.48 seconds; no warnings, no errors. |

---

## 3. Interpretation

### 3.1 What the §A.2 derivation provides

The §A.2 appendix formalises four previously-implicit items:

1. **Closed-form vs discretisation distinction** — $A_g$ and $B_g$ are continuous definitions (Eqs.\,(A.12)–(A.13)) but the framework ships discrete approximations (trapezoidal + sign-change sampling). The discretisation errors are bounded by $O(h^2)$ and $O(h)$ respectively (default $K=8, h=0.01$ places these below proof-working precision). $C_g$ and $e_\rho$ are **closed-form** with no discretisation involved.
2. **Disjoint-cell hypothesis** — Lemma 5's packing estimate + physical-complement statement both require $\rho < d/4$ (companion paper line 135–138). `per_cell_coefficient_C` only validates $\rho \in (0, 1)$, not $\rho < d/4$; the framework's `validate_f_side_hypotheses` is the caller-side guard for the full hypothesis set.
3. **Companion-paper vs framework division of labour** — the companion paper is the authoritative source for the **proof-theoretic role** of each quantity (Lemma 2 sheet evidence, Lemma 3 per-cell coefficient, Lemma 4 exterior complement suppression, Lemma 5 packing + disjoint-cell guarantee, Corollary 1 quantitative allocation); the framework ships the **numerical-evaluation closed forms** in `paper_quantities.py`. The framework does **not** re-derive the companion-paper proofs — it threads the closed-form values through the `PaperQuantitiesCache` 16-site taxonomy.
4. **Dormant-vs-active architecture is by design** — per §8.9 + §10, 15 of 16 enumerated companion application sites are dormant under `CosineAnnealScheduler`. The §A.2 closed forms are part of the framework's **typed-contracts surface** (the 16-site taxonomy) but the headline empirical wins are produced by the typed-contracts loop with site 1 (cosine ramp) + site 6 fallback (`BoundedMergeOperator` no-paper-quantity lift) + site 7 fallback (`ScheduleDerivedPolicyDriver` with no paper-quantity normalisation). The closed-form derivations are exercised only when `profile_residual_fn` is supplied (the optional theoretical-companion opt-in).

### 3.2 Why §A.2 fills the cross-adapter regime-curve reservation partially

The §A.2 placeholder reserved §A.2 for the cross-adapter regime-curve derivation extending Theorem 5's per-$\varepsilon_\theta$ family to a quantitative $k^*$ calibration. Wave 353 P2 fills §A.2 with the **paper-quantity closed-form derivation** instead — a complementary close-out that documents the **companion-paper side** of the framework's theoretical surface. The cross-adapter regime-curve derivation is documented as a future-work sibling in §10.9.4 (newly added ADDITIVE footnote), with the explicit deferral reason: "the per-adapter $L_\text{local}$ + per-adapter paper-quantity diagnostic[s] are engineering follow-ups deferred to a follow-up ultracode wave."

This disposition is consistent with Wave 268 strict-clean ("fewer files touched, fewer lines changed, more additive") — the §A.2 fill is the **paper-quantity side** of the partial close-out that §A.3 (Wave 352 P3) + Theorem 5 (Wave 350 P1) + Theorem 5 numerical validation (Wave 351 P3) constitute on the **restart-blend side**. Both sides are closed; the cross-adapter extension is a separate engineering piece.

### 3.3 Connection to §6.4 paper-quantity mapping

The §6.4 paper-quantity mapping referenced in the §6.6 Theorem 5 Sub-claim 5.4 footnote ("the per-channel $\beta$ from the policy driver is monotone-transformed into $m$ by the canonical blender module") is the **engineering wiring** between the paper quantities and the framework's runtime; the §A.2 derivation provides the **theoretical closed forms** that the engineering wiring consumes. The two are complementary: §A.2 is the theory, §6.4 is the engineering. The §A.2 fill does **not** modify §6.4 — §6.4 is preserved verbatim and the §A.2 derivation cross-references §6.4 only via the §8.9 + §10 main-text references to the four paper-quantity inputs.

### 3.4 What §10.9.4 contributes

The §10.9.4 footnote completes the §10.9 future-work item family:

- **§10.9** (original) — the future-work item that called for a closed-form attenuation bound on the restart-blend operator (Theorem 5).
- **§10.9.1** (Wave 349) — the R5b conditional boundary cross-reference to the Wave 206 P6 4-scheduler × 3-`n_rounds` conditional grid.
- **§10.9.2** (Wave 350) — Theorem 5 partial close-out (the closed-form bound is derived as Eq.\,(6)).
- **§10.9.3** (Wave 352) — Theorem 5 numerical-validation partial close-out (Wave 351 P3 numerical fit matches the empirical grid).
- **§10.9.4** (Wave 353 P2, this wave) — §A.2 paper-quantity closed-form derivation close-out (the companion-paper side of the partial close-out).

The §10.9.4 footnote is **purely additive** — §10.9, §10.9.1, §10.9.2, §10.9.3 are preserved verbatim. The footnote documents the cross-adapter extension (per-adapter $L_\text{local}$ + per-adapter paper-quantity diagnostic) as engineering work deferred to a follow-up ultracode wave, mirroring the §A.3.5(4) Lipschitz-diagnostic disposition.

---

## 4. Honest Disclosures

### 4.1 Closed-form vs discretisation (per §A.2.7(1))

The $A_g$ and $B_g$ numerics are **discrete approximations** (trapezoidal $O(h^2)$ for $A_g$, sign-change + linear-interpolation $O(h)$ for $B_g$). The default $K = 8, h = 0.01$ places the truncation error below $10^{-14}$ for $A_g$ and the discretisation bias below $O(h)$ for $B_g$ — both well below proof-working precision. The $C_g$ and $e_\rho$ numerics are **closed-form** with no discretisation involved. This caveat does not invalidate the closed-form derivations; it bounds the per-quantity numerical-evaluation error as an explicit $O(h)$ or $O(h^2)$ term.

### 4.2 Disjoint-cell hypothesis check (per §A.2.7(2))

`per_cell_coefficient_C` only validates $\rho \in (0, 1)$, not $\rho < d / 4$ (Lemma 5's disjoint-cell guarantee). Callers must combine with `validate_f_side_hypotheses` to assert the full hypothesis set is consistent. This is **not a numerical-validation gap** — it is a hypothesis-set consistency check that the companion paper's Lemma 5 setup guarantees at construction time; the framework's caller-side guard makes the consistency check explicit.

### 4.3 Dormant under cosine baseline (per §A.2.7(4))

The §A.2 closed-form derivations are **dormant under the headline cosine baseline** (per §8.9 + §10 the framework-not-theory verdict: 15 of 16 enumerated companion application sites are dormant under `CosineAnnealScheduler`). The §A.2 derivation formalises the **typed-contracts surface** of the framework (the 16-site taxonomy) and is exercised only when `profile_residual_fn` is supplied (the optional theoretical-companion opt-in). The headline empirical wins are produced by the typed-contracts loop without consuming any paper-quantity input.

### 4.4 Per-adapter extension deferred (per §A.2.7(5))

The §10.9 future-work item family (§10.9.1–§10.9.4) closes the **per-quantity closed-form derivation** side of the framework's theoretical companion. The remaining engineering items — per-adapter Lipschitz diagnostic at construction time + cross-adapter regime curves on R5b CIFAR-10 RF + per-adapter paper-quantity diagnostic — are deferred to a follow-up ultracode wave. The §A.2 derivation is **adapter-independent** (closed forms are functions of the F-side scalar $g$ + scale $\rho$ + separation $d$); the per-adapter wiring is the engineering follow-up.

---

## 5. Verification Evidence

```bash
# Pre-commit verification (all PASS)
$ python3 tools/check_claims_consistency.py
# Claims consistency report
# - Active claims: **61**
# - Provisional claims: **0**
# - Deprecated claims: **2**
# ...
# **No drift detected.**

$ python3 -m pytest tests/test_d4_regression_vectors.py -q
# ... 30 passed, 3 warnings in 6.98s

$ mkdocs build --strict
# INFO    -  Cleaning site directory
# INFO    -  Building documentation to directory: .../site
# INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.
# INFO    -  Documentation built in 24.48 seconds
```

All three verification gates pass. No code change. No claim number change. No main-text number change.

---

## 6. Source Pointers

- **§A.2 implementation:** [`adaptive_reflow/theory/paper_quantities.py`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/adaptive_reflow/theory/paper_quantities.py) — `sheet_evidence_A` (line 96–175), `root_cell_packing_B` (line 178–288), `per_cell_coefficient_C` (line 291–358), `exterior_gap_e_rho` (line 361–418).
- **Rich-result wrappers:** `paper_quantities.py:490-622` — `sheet_evidence_with_result` (A17), `root_cell_packing_with_result` (B13), `per_cell_coefficient_with_result` (B14) — carry literal values + diagnostic bounds.
- **Wave 49 Agent C §5.1 FlowMol3 carrier:** [`adaptive_reflow/adapters/flowmol3_glue.py:295-336`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/adaptive_reflow/adapters/flowmol3_glue.py#L295-L336) — frozen dataclass with the 13 documented fields.
- **Aggregate ratio divisor:** [`adaptive_reflow/adapters/flowmol3_glue.py:746-753`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/adaptive_reflow/adapters/flowmol3_glue.py#L746-L753) — `aggregate_ratio = sheet_A / (sheet_A + cell)` drives `n_cap`.
- **§8.9 main-text cross-reference:** `docs/drafts/paper-A-final.md` line 519 — the four paper-quantity inputs ($A_g$, $B_g$, $C_g$, $e_\rho$).
- **§A.3 predecessor:** [`docs/drafts/paper-A-final.md` line 819](../drafts/paper-A-final.md) — Wave 352 P3 Theorem 5 Lipschitz-constant derivation, the **restart-blend side** of the partial close-out.
- **§A.1 predecessor:** [`docs/drafts/paper-A-final.md` line 681](../drafts/paper-A-final.md) — Wave 353 P1 Theorem 4 derivation.
- **§10.9.4 footnote:** [`docs/drafts/paper-A-final.md` line 617](../drafts/paper-A-final.md) — newly added ADDITIVE footnote documenting the §A.2 paper-quantity closed-form derivation close-out.
- **§10.9 future-work item family:** [`docs/drafts/paper-A-final.md` line 601](../drafts/paper-A-final.md) — original §10.9 + §10.9.1–§10.9.4 footnotes (Wave 349, 350, 352, 353 P2 ADDITIVE).

---

_Last updated: 2026-09-25 (Wave 353 P2 — §A.2 paper-quantity closed-form derivation appendix)._
