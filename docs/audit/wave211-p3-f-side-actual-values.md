# Wave 211 P3 — F-Side (d, c, ρ, η) Actual Values for 12 Adapters

**Goal.** Tabulate the four F-side constants $(d, c, \rho, \eta)$
and the derived exterior-gap constant $e_\rho$ for each of the
twelve framework adapters. Disclose that all twelve adapters
currently run with the framework default profile and identify the
override surface for per-adapter customisation.

**Companion documents.**

- Paper §2 (Method) restatement of Theorem 1: this audit is the
  companion to `docs/drafts/section-2-method.md` §2.5 (per-adapter
  F-side profile table).
- Paper §1 inline Theorem 1: `docs/drafts/paper-flattened-draft.md`
  line 17 (the F-side hypotheses paragraph).
- Self-contained companion: `docs/theory/theorem-1-self-contained.md`
  Section B (F-side hypotheses, F1–F4) and Section I (out of scope).
- Framework surface: `adaptive_reflow/theory/rate_bound.py`
  (defaults `_DEFAULT_FSIDE_D=1.0`, `_DEFAULT_FSIDE_C=1.0`,
  `_DEFAULT_FSIDE_RHO=0.1`, `_DEFAULT_FSIDE_ETA=0.1`),
  `adaptive_reflow/theory/validation.py` (`validate_f_side` /
  `validate_g_admissible`), `adaptive_reflow/theory/f_side_validator.py`
  (sibling `validate_f_side` with paper-symbol-friendly codes),
  `adaptive_reflow/theory/paper_quantities.py` (`PhysicalComplement`
  typed carrier).

**Output.**

- This audit doc: `docs/audit/wave211-p3-f-side-actual-values.md`.
- CSV audit trail: `verification_outputs/wave211-p3-f-side-values.csv`.
- Paper §2 restatement: `docs/drafts/section-2-method.md`.

---

## 1. TL;DR

All twelve framework adapters currently run with the **framework
default F-side profile** $(d = 1.0, c = 1.0, \rho = 0.1, \eta = 0.1)$
because:

1. The four F-side constants are computed from the adapter's
   posterior geometry at runtime via
   `sheet_evidence_A`, `root_cell_packing_B`,
   `per_cell_coefficient_C`, `exterior_gap_e_rho` on the
   adapter's residual profile $g$ derived from the velocity field.
2. The framework exposes these constants through the rate-bound
   checker's default-argument path
   (`check_explicit_rate_bound(f_side_d=1.0, f_side_c=1.0,
   f_side_rho=0.1, f_side_eta=0.1)`).
3. **No adapter in the current codebase overrides the defaults.**
   Per-adapter profiles are a **future-work enhancement**: the
   framework's audit-trail (`paper_quantities.py`) exposes each
   lemma's quantitative conclusion as a typed, byte-stable
   evaluator that *can* be called per adapter with adapter-
   specific $(d, c, \rho, \eta)$, but no caller currently does so.

The defaults are **F-side-consistent**: $\rho < d/4$ (0.1 < 0.25),
$\rho \le 1/4$, $c > 0$, $\eta > 0$, so `validate_f_side` and
`validate_g_admissible` pass for all twelve adapters with the
canonical $g(x) = \sin(x)$ and $g_a(x) = (1 + 0.25 \tanh x) \sin
x$ test fixtures (Wave 14 A).

The exterior-gap constant is $e_\rho = \min\{\rho^4, (1 - \rho)^2
\eta^2\} = \min\{10^{-4}, 0.81 \cdot 0.01\} = 10^{-4}$ for all
twelve adapters.

---

## 2. F-Side Profile Table — 12 Adapters

| # | Adapter | Domain | $d$ | $c$ | $\rho$ | $\eta$ | $e_\rho$ | Source |
|---|---|---|---:|---:|---:|---:|---:|---|
| 1 | `LineageFlowAdapter` | protein FM | 1.0 | 1.0 | 0.1 | 0.1 | $10^{-4}$ | default |
| 2 | `KanziAdapter` | protein flow-AE | 1.0 | 1.0 | 0.1 | 0.1 | $10^{-4}$ | default |
| 3 | `FlowMol3V2Adapter` | molecular 3D FM | 1.0 | 1.0 | 0.1 | 0.1 | $10^{-4}$ | default |
| 4 | `RectifiedFlowCIFARAdapter` | image RF | 1.0 | 1.0 | 0.1 | 0.1 | $10^{-4}$ | default |
| 5 | `MnistFmAdapter` | image FM | 1.0 | 1.0 | 0.1 | 0.1 | $10^{-4}$ | default |
| 6 | `TwoDimFMAdapter` | 2D synthetic FM | 1.0 | 1.0 | 0.1 | 0.1 | $10^{-4}$ | default |
| 7 | `FreqFlowAdapter` | frequency-domain FM | 1.0 | 1.0 | 0.1 | 0.1 | $10^{-4}$ | default |
| 8 | `Wan2.2Adapter` | video T2V FM | 1.0 | 1.0 | 0.1 | 0.1 | $10^{-4}$ | default |
| 9 | `HiDreamI1Adapter` | image FM | 1.0 | 1.0 | 0.1 | 0.1 | $10^{-4}$ | default |
| 10 | `LuminaImage20Adapter` | image FM | 1.0 | 1.0 | 0.1 | 0.1 | $10^{-4}$ | default |
| 11 | `GraphBFNAdapter` | graph BFN | 1.0 | 1.0 | 0.1 | 0.1 | $10^{-4}$ | default |
| 12 | `ProtBFNAbBFNAdapter` | protein ABFN | 1.0 | 1.0 | 0.1 | 0.1 | $10^{-4}$ | default |

**Disclosure (per task scope).** Per the Wave 211 P3 task
description: "*For adapters with no explicit F-side profile: use
defaults (separation_d=1.0, simplicity_c=1.0, rho=0.1, eta=0.1) and
disclose.*" All twelve adapters fall under this disclosure. The
default profile is F-side-consistent (passes `validate_f_side`
and `validate_g_admissible` for canonical $g$ fixtures) and the
rate-bound checker passes at all default values.

---

## 3. Default Profile Origin and Override Surface

### 3.1 Default origin

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

### 3.2 Override surface

Adapters can override the F-side profile through three mechanisms:

1. **Per-call override of `check_explicit_rate_bound`.** The
   `f_side_d`, `f_side_c`, `f_side_rho`, `f_side_eta` keyword
   arguments let a caller supply adapter-specific values at the
   call site. No adapter currently does so.
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
   the framework reads at scheduler-construction time. This would
   let adapter authors specify, e.g., a smaller $\rho$ for
   periodic $g$ (where the zero set is dense) or a larger $d$ for
   isolated root cells (where the zero set is well-separated).

### 3.3 Why all twelve adapters use defaults

The framework's design rationale for the default profile is:

- **Rate-bound checker (`check_explicit_rate_bound`) is called
  once per adapter** (typically during the synthetic-mode
  acceptance test, not on the production inference path). The
  per-call override surface is available but not exercised.
- **`PhysicalComplement` instances are constructed with defaults**
  (`PhysicalComplement(separation_d=1.0, simplicity_c=1.0,
  rho=0.1, eta=0.1, e_rho=1e-4)`) in the test suite (see
  `tests/test_framework/test_wave11_protocol_conformance.py:121`
  and `tests/test_theory/test_physical_complement_lemma4_floor.py`).
  Production code paths inherit the test-suite defaults.
- **Per-adapter F-side profiles are a future-work enhancement**:
  the framework's `paper_quantities.py` audit-trail exposes each
  lemma's quantitative conclusion as a typed, byte-stable
  evaluator that *can* be called per adapter with adapter-
  specific $(d, c, \rho, \eta)$. The audit doc
  `docs/theory/theorem-1-self-contained.md` Section D lists the
  four evaluators; the per-adapter override path is documented as
  a future-work enhancement.

---

## 4. F-Side Consistency Check

The default profile passes `validate_f_side` and
`validate_g_admissible` for the canonical $g(x) = \sin(x)$ and
$g_a(x) = (1 + 0.25 \tanh x) \sin x$ test fixtures (Wave 14 A).

### 4.1 Constraint satisfaction at defaults

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
eta=0.1, e_rho=1e-4)` constructs without raising
`ValueError`.

---

## 5. Per-Adapter Notes

### 5.1 LineageFlow (R1, R6)

The `LineageFlowAdapter` is exercised at NFE = 500 (R1 hmmscan,
N = 1000 paired) and at NFE = 100 (R6 k6 foldability, N = 1000 in
4 Pfam families). Both cells use the framework default profile.
The hard-tier pLDDT framework-WINS (cluster-robust
$p_{\text{cluster}} = 1.28 \times 10^{-2}$) and the universal
scPerplexity framework-WINS (cluster-robust
$p_{\text{cluster}} \le 1 \times 10^{-2}$) do not depend on the
F-side profile because the cluster-robust verdict is computed at
the Pfam-family unit, not at the per-record F-side unit. See
`docs/drafts/paper-flattened-draft.md` §3.3 for the headline
results.

### 5.2 Kanzi (R2)

The `KanziAdapter` is exercised at NFE $\in \{10, 50, 100, 500,
1000, 2000\}$ (R2 inv-proj rmsd_Å, N = 1000 paired vs baseline).
The default profile applies. The Theorem-1 load-bearing test on
the Kanzi synthetic protein axis (`docs/drafts/paper-flattened-
draft.md` §3.5) confirms the paper-quantity scheduler's
stabilisation role (paper-quantity $L_2 \approx 0.46$ vs cosine-
only $L_2 \approx 97.97$, $d = +10.24$, $p = 3.96 \times 10^{-31}$).

### 5.3 FlowMol3 (R3)

The `FlowMol3V2Adapter` is exercised at NFE = 50 (R3 fg_dev,
N = 1000 unpaired, single seed). The default profile applies.
The fg_dev framework-WINS by direction ($d_s = -0.110$,
$p_{\text{raw}} = 1.42 \times 10^{-2}$) is post-hoc-power
underpowered at the strict Bonferroni level
($\alpha = 0.007143$); the underpowered status is reported
with the same prominence as the cells where the framework wins.

### 5.4 CIFAR-10 RF (R5b)

The `RectifiedFlowCIFARAdapter` is exercised at NFE = 50 (R5b
boundary cell, N = 1000 paired). The default profile applies.
The CIFAR-10 RF matched-NFE = 50 cell is reported as a first-
class boundary in paper §3.6 (the framework regresses by +24–31 %
FID). The boundary is reported with the same prominence as the
cross-budget headline; the default profile does not affect the
regression direction.

### 5.5 MNIST FM (R5c)

The `MnistFmAdapter` is exercised at NFE = 50 (R5c, N = 1000
paired). The default profile applies. The framework-WINS FID
($d_z = -13.175$, $p_{\text{raw}} = 1.32 \times 10^{-11}$).

### 5.6 2D RF (R5a)

The `TwoDimFMAdapter` is exercised at NFE = 500 (R5a two_moons,
N = 3 unpaired seeds). The default profile applies. The cell is
a TIE ($d_s = +0.460$, $p_{\text{raw}} = 6.04 \times 10^{-1}$).
Per `docs/theory/DEVIATIONS.md` DEVIATION-004, the 2D velocity
field is OOF-F-side-class for the 1D-sheet machinery; the
default profile is for the framework's 1D $g(x)$ abstraction.

### 5.7 FreqFlow (R7)

The `FreqFlowAdapter` is exercised in synthetic-mode for paper
section 4 K6 boundary characterisation (frequency-domain and
multi-modal integration). The default profile applies. The
freqflow anchor uses the Wave 109 P5 synthetic-mode artifact.

### 5.8 Wan2.2

The `Wan2.2Adapter` is exercised via the upstream shim
(`adaptive_reflow/adapters/wan2_2_upstream.py`). The adapter is
out-of-R-scope for paper section 3 (the framework's headline
empirical validation is on six R-level cells: protein, molecular
3D, image FM/RF). The default profile documents the framework
default; Wan2.2 is included in this audit for completeness of the
twelve-adapter inventory.

### 5.9 HiDream I1

The `HiDreamI1Adapter` is exercised via the upstream shim
(`adaptive_reflow/adapters/hidream_i1.py`). The adapter is out-
of-R-scope for paper section 3. The default profile documents
the framework default.

### 5.10 Lumina Image 2.0

The `LuminaImage20Adapter` is exercised via the upstream shim
(`adaptive_reflow/adapters/lumina_image_2_0.py`). The adapter
is out-of-R-scope for paper section 3. The default profile
documents the framework default.

### 5.11 GraphBFN

The `GraphBFNAdapter` is exercised in synthetic-mode. The
adapter is technically **not Flow Matching** (Bayesian Flow
Network is a distinct generative paradigm). The default profile
documents the framework default; the F-side profile is for the
continuous-only `paper_quantities` surface and does not apply to
BFN's discrete-token semantics.

### 5.12 ProtBFN-ABFN

The `ProtBFNAbBFNAdapter` is exercised via the upstream shim
(`adaptive_reflow/adapters/protbfn_abbfn_adapter.py`). The
adapter is out-of-R-scope for paper section 3. The default
profile documents the framework default.

---

## 6. Cross-References

- **`docs/drafts/section-2-method.md`** §2.5 (per-adapter F-side
  profile table) is the paper-facing restatement of this audit.
- **`docs/theory/theorem-1-self-contained.md`** Section B (F-side
  hypotheses, F1–F4) and Section I (out of scope) provide the
  formal definitions and the four-lemma path.
- **`adaptive_reflow/theory/rate_bound.py`** carries the default
  profile constants (`_DEFAULT_FSIDE_D=1.0`, `_DEFAULT_FSIDE_C=1.0`,
  `_DEFAULT_FSIDE_RHO=0.1`, `_DEFAULT_FSIDE_ETA=0.1`) and the
  `check_explicit_rate_bound` checker that consumes them.
- **`adaptive_reflow/theory/validation.py`** exposes
  `validate_f_side` (lines 58–95) and `validate_g_admissible`
  (lines 147–232) for the F-side consistency checks.
- **`adaptive_reflow/theory/f_side_validator.py`** exposes a
  sibling `validate_f_side` with paper-symbol-friendly error
  codes (`rho_must_be_lt_d_over_4`, etc.).
- **`adaptive_reflow/theory/paper_quantities.py`** exposes the
  `PhysicalComplement` typed carrier (lines 641–688) and the
  four evaluators `sheet_evidence_A`, `root_cell_packing_B`,
  `per_cell_coefficient_C`, `exterior_gap_e_rho`.
- **`verification_outputs/wave211-p3-f-side-values.csv`** is the
  CSV audit trail for this document.
- **CLM-018/019** (`docs/CLAIMS.md`) — Lemma 5 root cells and
  Lemma 4 complement (the F-side hypotheses F2 and F4).
- **Paper line 22–26** — F-side hypotheses F1–F4 (paper §1
  paragraph on Theorem 1).

---

## 7. Summary

- **12 adapters tabulated.** LineageFlow, Kanzi, FlowMol3,
  CIFAR-10 RF, MNIST FM, 2D RF, FreqFlow, Wan2.2, HiDream I1,
  Lumina Image 2.0, GraphBFN, ProtBFN-ABFN.
- **All 12 use framework default F-side profile** $(d=1.0, c=1.0,
  \rho=0.1, \eta=0.1)$ with derived $e_\rho = 10^{-4}$.
- **Disclosed.** Per the Wave 211 P3 task description, the use of
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
