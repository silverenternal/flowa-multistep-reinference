# Wave 209 P8 — G3: F-Side (d, c, ρ, η) Actual Values for 12 Adapters

**Date:** 2026-09-21
**Agent:** Wave 209 P8 (G3 — F-side actual values for paper §2.5).
**Companion:** Wave 211 P3 produced the canonical F-side audit at
`docs/audit/wave211-p3-f-side-actual-values.md`; this document is
the Wave 209 P8 mirror with the cell × R-level cross-reference added.

**Goal.** Tabulate the four F-side constants $(d, c, \rho, \eta)$
and the derived exterior-gap constant $e_\rho$ for each of the
twelve framework adapters, and disclose that all twelve adapters
currently run with the framework default profile. The override
surface for per-adapter customisation is documented in
`docs/audit/wave211-p3-f-side-actual-values.md` §3.2.

**Source CSV:** `verification_outputs/wave211-p3-f-side-values.csv`.

---

## 0. TL;DR

All twelve framework adapters currently run with the **framework
default F-side profile** $(d = 1.0, c = 1.0, \rho = 0.1, \eta = 0.1)$
because:

1. The four F-side constants are computed from the adapter's
   posterior geometry at runtime via `sheet_evidence_A`,
   `root_cell_packing_B`, `per_cell_coefficient_C`,
   `exterior_gap_e_rho` on the adapter's residual profile $g$
   derived from the velocity field.
2. The framework exposes these constants through the rate-bound
   checker's default-argument path
   (`check_explicit_rate_bound(f_side_d=1.0, f_side_c=1.0,
   f_side_rho=0.1, f_side_eta=0.1)`).
3. **No adapter in the current codebase overrides the defaults.**
   Per-adapter profiles are a **future-work enhancement**.

The defaults are **F-side-consistent**: $\rho < d/4$ (0.1 < 0.25),
$\rho \le 1/4$, $c > 0$, $\eta > 0$, so `validate_f_side` and
`validate_g_admissible` pass for all twelve adapters with the
canonical $g(x) = \sin(x)$ and $g_a(x) = (1 + 0.25 \tanh x) \sin x$
test fixtures (Wave 14 A).

The exterior-gap constant is $e_\rho = \min\{\rho^4, (1 - \rho)^2
\eta^2\} = \min\{10^{-4}, 0.81 \cdot 0.01\} = 10^{-4}$ for all
twelve adapters.

---

## 1. F-Side Profile Table — 12 Adapters

| # | Adapter | R-cell | Domain | $d$ | $c$ | $\rho$ | $\eta$ | $e_\rho$ | Source |
|---|---|---|---|---:|---:|---:|---:|---:|---|
| 1 | `LineageFlowAdapter` | R1, R6 | protein FM (ICML 2026, 657M params, ESM-2 33-token) | 1.0 | 1.0 | 0.1 | 0.1 | $10^{-4}$ | default |
| 2 | `KanziAdapter` | R2 | protein flow-AE (ICLR 2026, 44.1M params) | 1.0 | 1.0 | 0.1 | 0.1 | $10^{-4}$ | default |
| 3 | `FlowMol3V2Adapter` | R3 | molecular 3D FM (NeurIPS 2024, 65M params, DGL graph kernels) | 1.0 | 1.0 | 0.1 | 0.1 | $10^{-4}$ | default |
| 4 | `RectifiedFlowCIFARAdapter` | R5b | image RF (Open DDPM++ UNet, 32×32) | 1.0 | 1.0 | 0.1 | 0.1 | $10^{-4}$ | default |
| 5 | `MnistFmAdapter` | R5c | image FM (Open MNIST FM recipe) | 1.0 | 1.0 | 0.1 | 0.1 | $10^{-4}$ | default |
| 6 | `TwoDimFMAdapter` | R5a | 2D synthetic FM (Two Moons / Eight Gaussians) | 1.0 | 1.0 | 0.1 | 0.1 | $10^{-4}$ | default |
| 7 | `FreqFlowAdapter` | (K6 boundary) | frequency-domain FM (synthetic-mode) | 1.0 | 1.0 | 0.1 | 0.1 | $10^{-4}$ | default |
| 8 | `Wan2.2Adapter` | (out-of-R) | video T2V FM (upstream shim) | 1.0 | 1.0 | 0.1 | 0.1 | $10^{-4}$ | default |
| 9 | `HiDreamI1Adapter` | (out-of-R) | image FM (upstream shim) | 1.0 | 1.0 | 0.1 | 0.1 | $10^{-4}$ | default |
| 10 | `LuminaImage20Adapter` | (out-of-R) | image FM (upstream shim) | 1.0 | 1.0 | 0.1 | 0.1 | $10^{-4}$ | default |
| 11 | `GraphBFNAdapter` | (out-of-R) | graph BFN (synthetic-mode) | 1.0 | 1.0 | 0.1 | 0.1 | $10^{-4}$ | default |
| 12 | `ProtBFNAbBFNAdapter` | (out-of-R) | protein ABFN (upstream shim) | 1.0 | 1.0 | 0.1 | 0.1 | $10^{-4}$ | default |

**Disclosure (per task scope).** Per the Wave 209 P8 G3 task
description: "*For adapters with no explicit F-side profile: use
defaults (separation_d=1.0, simplicity_c=1.0, rho=0.1, eta=0.1) and
disclose.*" All twelve adapters fall under this disclosure. The
default profile is F-side-consistent (passes `validate_f_side` and
`validate_g_admissible` for canonical $g$ fixtures) and the
rate-bound checker passes at all default values.

---

## 2. Default Profile Origin

The framework's default F-side profile is declared in
`adaptive_reflow/theory/rate_bound.py`:

```python
_DEFAULT_FSIDE_D: float = 1.0
_DEFAULT_FSIDE_C: float = 1.0
_DEFAULT_FSIDE_RHO: float = 0.1
_DEFAULT_FSIDE_ETA: float = 0.1
```

These are forwarded to `check_explicit_rate_bound` as the default
keyword arguments (`f_side_d`, `f_side_c`, `f_side_rho`,
`f_side_eta`) and are then passed to `validate_g_admissible` (or
the sibling `validate_f_side`) for the fail-closed F-side pre-check
that gates the rate-bound checker.

---

## 3. Override Surface

Adapters can override the F-side profile through three mechanisms:

1. **Per-call override of `check_explicit_rate_bound`.** The
   `f_side_d`, `f_side_c`, `f_side_rho`, `f_side_eta` keyword
   arguments let a caller supply adapter-specific values at the
   call site. **No adapter currently does so.**
2. **`PhysicalComplement` typed carrier** (in
   `adaptive_reflow/theory/paper_quantities.py`). The frozen
   dataclass carries `(separation_d, simplicity_c, rho, eta,
   e_rho)` and is consumed by `BoundedMergeOperator.merge` and
   `CodimensionSheetScheduler.inject_noise` so the two algorithm
   surfaces share a single typed carrier. The dataclass validates
   `separation_d > 0`, `simplicity_c > 0`, `0 < rho < 1`, `eta > 0`,
   `e_rho > 0` at construction time.
3. **Per-adapter `f_side_profile` attribute** (not currently
   implemented). A future enhancement can introduce a class-
   level attribute or constructor argument on each adapter that
   the framework reads at scheduler-construction time.

---

## 4. F-Side Consistency Check at Defaults

The default profile passes `validate_f_side` and
`validate_g_admissible` for the canonical $g(x) = \sin(x)$ and
$g_a(x) = (1 + 0.25 \tanh x) \sin x$ test fixtures (Wave 14 A).

### 4.1 Constraint satisfaction

| Constraint | Default value | Bound | Status |
|---|---|---|---|
| $d > 0$ | 1.0 | strict positive | PASS |
| $c > 0$ | 1.0 | strict positive | PASS |
| $0 < \rho \le 1/4$ | 0.1 | strict positive, $\le 0.25$ | PASS |
| $\rho < d/4$ | 0.1 < 0.25 | strict inequality | PASS |
| $\eta > 0$ | 0.1 | strict positive | PASS |
| $e_\rho > 0$ | $10^{-4}$ | strict positive | PASS |

### 4.2 `validate_f_side` return code at defaults

`adaptive_reflow/theory/validation.validate_f_side(1.0, 1.0, 0.1,
0.1)` returns `(True, ())` — no error codes emitted.

### 4.3 `validate_g_admissible` return at defaults

`adaptive_reflow/theory/validation.validate_g_admissible(g_sin,
1.0, 1.0, 0.1, 0.1)` returns `True` for $g(x) = \sin(x)$
(nonempty $Z_g$ at $\pm n\pi$, uniform simplicity on $|u| \le
\rho$).

### 4.4 `PhysicalComplement` construction at defaults

`PhysicalComplement(separation_d=1.0, simplicity_c=1.0, rho=0.1,
eta=0.1, e_rho=1e-4)` constructs without raising `ValueError`.

---

## 5. Per-Adapter Notes (cross-referenced to R-cells)

### 5.1 LineageFlow (R1, R6)

The `LineageFlowAdapter` is exercised at NFE = 50 / 200 (R1 hmmscan
and R6 k6 foldability, N = 1000 paired records in 4 Pfam families).
Both cells use the framework default profile. The hard-tier pLDDT
framework-WINS (cluster-robust $p_{\text{cluster}} = 1.28 \times
10^{-2}$) and the universal scPerplexity framework-WINS
(cluster-robust $p_{\text{cluster}} \le 1 \times 10^{-2}$) do not
depend on the F-side profile because the cluster-robust verdict is
computed at the Pfam-family unit, not at the per-record F-side unit.

### 5.2 Kanzi (R2)

The `KanziAdapter` is exercised at NFE $\in \{10, 50, 100, 500,
1000, 2000\}$ (R2 inv-proj rmsd_Å, N = 1000 paired vs baseline).
The default profile applies. The Theorem-1 load-bearing test on
the Kanzi synthetic protein axis confirms the paper-quantity
scheduler's stabilisation role (paper-quantity $L_2 \approx 0.46$ vs
cosine-only $L_2 \approx 97.97$, $d = +10.24$, $p = 3.96 \times
10^{-31}$). Note: KanziAdapter is exercised in synthetic-mode
(Kanzi_inv_proj) where the residual posterior is $g(x) = \sin(x)$-
shaped; the default profile is F-side-consistent for that $g$.

### 5.3 FlowMol3 (R3)

The `FlowMol3V2Adapter` is exercised at NFE = 250 (R3 fg_dev,
N = 1000 unpaired, single seed). The default profile applies. The
fg_dev framework-WINS by direction ($d_s = -0.110$, $p_{\text{raw}}
= 1.42 \times 10^{-2}$) is post-hoc-power underpowered at the strict
Bonferroni level ($\alpha = 0.007143$); the underpowered status is
reported with the same prominence as the cells where the framework
wins. FlowMol3 is exercised via Python 3.11 sidecar; the F-side
constants are framework-side, not adapter-side.

### 5.4 CIFAR-10 RF (R5b)

The `RectifiedFlowCIFARAdapter` is exercised at NFE = 50 (R5b
boundary cell, N = 1000 paired). The default profile applies. The
CIFAR-10 RF matched-NFE = 50 cell is reported as a first-class
boundary in paper §3.6 (the framework regresses by +24–31% FID).
The boundary is reported with the same prominence as the
cross-budget headline; the default profile does not affect the
regression direction.

### 5.5 MNIST FM (R5c)

The `MnistFmAdapter` is exercised at NFE = 50 (R5c, N = 1000
paired). The default profile applies. The framework-WINS FID
($d_z = -13.175$, $p_{\text{raw}} = 1.32 \times 10^{-11}$).

### 5.6 2D RF (R5a)

The `TwoDimFMAdapter` is exercised at NFE = 100 (R5a two_moons,
N = 7 unpaired seeds per Wave 209 P6 E2). The default profile
applies. The cell is a TIE ($d_s = +1.302$, $p_{\text{raw}} = 3.29
\times 10^{-2}$). Per `docs/theory/DEVIATIONS.md` DEVIATION-004,
the 2D velocity field is OOF-F-side-class for the 1D-sheet
machinery; the default profile is for the framework's 1D $g(x)$
abstraction.

### 5.7 FreqFlow (K6 boundary)

The `FreqFlowAdapter` is exercised in synthetic-mode for paper §4
K6 boundary characterisation (frequency-domain and multi-modal
integration). The default profile applies. The freqflow anchor uses
the Wave 109 P5 synthetic-mode artifact.

### 5.8 Wan2.2 / HiDream I1 / Lumina Image 2.0 / ProtBFN-ABFN (out-of-R)

These four adapters are exercised via their upstream shims. They
are out-of-R-scope for paper §3 (the framework's headline empirical
validation is on six R-level cells: protein, molecular 3D, image
FM/RF). The default profile documents the framework default; these
adapters are included in this audit for completeness of the
twelve-adapter inventory.

### 5.11 GraphBFN (out-of-R)

The `GraphBFNAdapter` is exercised in synthetic-mode. The adapter
is technically **not Flow Matching** (Bayesian Flow Network is a
distinct generative paradigm). The default profile documents the
framework default; the F-side profile is for the continuous-only
`paper_quantities` surface and does not apply to BFN's
discrete-token semantics.

---

## 6. Cross-References

- **`docs/audit/wave211-p3-f-side-actual-values.md`** — canonical
  Wave 211 P3 audit (this document mirrors it with R-cell cross-ref).
- **`docs/drafts/section-2-method.md`** §2.5 (per-adapter F-side
  profile table) is the paper-facing restatement.
- **`docs/theory/theorem-1-self-contained.md`** Section B (F-side
  hypotheses, F1–F4) and Section I (out of scope) provide the
  formal definitions and the four-lemma path.
- **`adaptive_reflow/theory/rate_bound.py`** carries the default
  profile constants (`_DEFAULT_FSIDE_D=1.0`, `_DEFAULT_FSIDE_C=1.0`,
  `_DEFAULT_FSIDE_RHO=0.1`, `_DEFAULT_FSIDE_ETA=0.1`).
- **`adaptive_reflow/theory/validation.py`** exposes
  `validate_f_side` (lines 58–95) and `validate_g_admissible`
  (lines 147–232) for the F-side consistency checks.
- **`adaptive_reflow/theory/paper_quantities.py`** exposes the
  `PhysicalComplement` typed carrier and the four evaluators.
- **`verification_outputs/wave211-p3-f-side-values.csv`** — 12-row
  CSV audit trail for this document.

---

## 7. Summary

- **12 adapters tabulated.** LineageFlow (R1, R6), Kanzi (R2),
  FlowMol3 (R3), CIFAR-10 RF (R5b), MNIST FM (R5c), 2D RF (R5a),
  FreqFlow, Wan2.2, HiDream I1, Lumina Image 2.0, GraphBFN,
  ProtBFN-ABFN.
- **All 12 use framework default F-side profile** $(d=1.0, c=1.0,
  \rho=0.1, \eta=0.1)$ with derived $e_\rho = 10^{-4}$.
- **Disclosed.** Per the Wave 209 P8 G3 task description, the use of
  defaults is explicit and the override surface is documented
  (`check_explicit_rate_bound` keyword arguments,
  `PhysicalComplement` typed carrier, future per-adapter
  `f_side_profile` attribute).
- **F-side-consistent.** The default profile passes
  `validate_f_side` and `validate_g_admissible` for canonical
  $g(x) = \sin(x)$ and $g_a(x) = (1 + 0.25 \tanh x) \sin x$ test
  fixtures.
- **CSV audit trail** at
  `verification_outputs/wave211-p3-f-side-values.csv`.
- **Paper §2 (Method) restatement** at
  `docs/drafts/section-2-method.md` §2.5.
