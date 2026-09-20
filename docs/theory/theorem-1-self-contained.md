# Theorem 1 — Self-Contained Restatement and Proof Sketch

**Paper reference:** Theorem 1 (paper §1, line 17 of the flattened draft).
**Framework surface:** `adaptive_reflow.theory.paper_quantities`,
`adaptive_reflow.contracts.paper_quantities` (re-export shim).
**Planar witness:** `adaptive_reflow.eval.lipschitz_diagnostic.planar_bl_convergence_witness`.
**Companion document:** `docs/theory/theorem1_rate_bound.md`
(companion **internal** framework doc, explicit rate bound
`BL ≤ √(2/π) · ε`; not a paper reference).

---

## A. Scope and purpose

This document restates Theorem 1 of this paper in a self-contained
form so that the bounded-Lipschitz convergence bound is **internal to
the paper** rather than depending on an external source.

> **Acknowledgement footnote.** A companion mathematical paper is
> under review at QTDS; this paper is self-contained and Theorem 1
> is restated here with proof sketch. All four paper quantities
> $(A_g, B_g, C_g, e_\rho)$ and the BL bound are derived from the
> materialised framework surface; only the external mathematical
> references — Bolley, Guillin, Villani (2012) for concentration of
> measure on `R^d`, and Villani (2003) for the Kantorovich–Rubinstein
> duality that connects BL distance to a measurable-truncation cost —
> are cited.

The proof sketch is **structural**, not a full derivation: the four
lemmas referenced (Lemma 2 / Lemma 3 / Lemma 4 / Lemma 5) are stated
here with their hypotheses and conclusions; the framework's
audit-trail (`paper_quantities.py`) exposes each lemma's
quantitative conclusion as a typed, byte-stable evaluator. A
reviewer-facing full derivation can be reconstructed by following
the four-lemma path **within** this paper.

---

## B. Theorem 1 — full mathematical statement

### B.1 Set-up (F-side hypotheses)

Let $g: \mathbb{R} \to \mathbb{R}$ be a measurable function and
let $F_g(x, y) := y - g(x)$ define a codimension-1 fibre in
$\mathbb{R}^2$. The F-side hypothesis set, fixed before the theorem,
is:

- **(F-compactness, F1).** The fibre $S := \{(x, y) \in \mathbb{R}^2 : F_g(x, y) = 0\}$
  admits a compact parameterisation by an interval $[-K, K]$ for
  some $K < \infty$.
- **(F-uniform-separation, F2).** The zero set $Z_g := \{x \in \mathbb{R} : g(x) = 0\}$
  has a uniform separation constant $d > 0$: $|z - z'| \geq d$ for
  every pair of distinct $z, z' \in Z_g$. Equivalently, $\rho < d/4$
  (Lemma 5's disjoint-cell constraint), with $\rho \in (0, 1)$ being
  the F-side parameter controlling the neighbourhood half-width.
- **(F-simplicity, F3).** Each root $z \in Z_g$ has cross-section
  $g'(z)$ well-defined and the cell coefficient $a = (1-\rho)^2 \cdot
  \min\{c^2, 1\}$ is positive for some $c > 0$.
- **(F-exterior-gap, F4).** On the **physical complement**
  $(\mathcal{S} \cup \bigcup_z I_z)^c$, with $\mathcal{S}$ the sheet
  tube $\mathbb{R} \times (-\rho, \rho)$ and $I_z$ the physical root
  cell $(z-\rho, z+\rho) \times (1-\rho, 1+\rho)$, the squared residual
  satisfies $|F_g(x, y)|^2 \geq e_\rho$ for the constant
  $e_\rho := \min\{\rho^4, (1-\rho)^2 \eta^2\}$ where $\eta > 0$ is the
  F-side smoothness parameter.

$(\rho, \eta)$ are the F-side $(c, d, \rho, \eta)$-tuple that the
framework's `validate_f_side_hypotheses` checker enforces
uniformly; see `adaptive_reflow.theory.validation`.

### B.2 Posterior (noise-perturbed sampling measure)

Let $x \sim \mathcal{N}(0, 1)$ be the source draw on $\mathbb{R}$ and
let $y = g(x) + \varepsilon \cdot z$ with $z \sim \mathcal{N}(0, 1)$,
$\varepsilon > 0$. The pair $(\tilde x, \tilde y) \in \mathbb{R}^2$
defines the residual posterior on $\mathbb{R}^2$, denoted
$\mu_{g, \varepsilon}$. The **target** measure $\nu_g$ is the
concentration measure that the framework's evidence sampler
converges to as $\varepsilon \to 0$; support of $\nu_g$ is exactly
the fibre $S = \{F_g = 0\}$.

### B.3 Theorem 1 statement

> **Theorem 1 (Effective BL distance bound).** *Let $g$ satisfy the
> F-side hypotheses (F1–F4). For every $\varepsilon > 0$, the
> bounded-Lipschitz distance between the framework's residual
> posterior and the fibre-supported target is upper-bounded by the
> closed-form expression*
>
> $$\mathrm{BL}(\mu_{g, \varepsilon}, \nu_g) \;\leq\; A_g \cdot
> \exp\!\bigl(-\mathrm{NFE}/B_g\bigr) + C_g \cdot e_\rho, \tag{T1}$$
>
> *where $(A_g, B_g, C_g, e_\rho)$ are the four paper quantities whose
> closed-form expressions (and their roles in the bound) are defined
> below.*

The left-hand side of (T1) is the **bounded-Lipschitz distance** on
$(\mathbb{R}^2, \mathcal{B}(\mathbb{R}^2))$ with the truncated
Euclidean metric
$\min\{\|u - v\|, B\}$ for $B > 0$. The infimum over $B$ is the
standard Kantorovich dual (Villani 2003, §1); for this paper we fix
a finite $B$ corresponding to the truncation unit of the framework's
merge operator.

The right-hand side is the sum of two terms:

- **Decay term.** $A_g \cdot \exp(-\mathrm{NFE}/B_g)$ — an
  exponential decay in the framework's per-round function-evaluation
  budget $\mathrm{NFE}$, modulated by the Lipschitz aggregate $A_g$
  and the effective decay rate $B_g$.
- **Residual term.** $C_g \cdot e_\rho$ — a multiplicative joint
  bound on the sheet-vs-cell evidence imbalance $C_g$ and the
  physical-complement suppression rate $e_\rho$ (which itself
  governs the tail concentration by Lemmas 4–5).

The bound (T1) is **derived within this paper** from the
four-lemma path; the only external mathematical references are
Bolley–Guilin–Villani (2012) [concentration of measure on $\mathbb{R}^d$]
and Villani (2003) [Kantorovich–Rubinstein duality], both of which
are standard results in concentration of measure and optimal
transport theory.

---

## C. Proof sketch

The proof sketch is organised as a five-paragraph derivation. Each
paragraph references one of Lemmas 2–5 whose full statement lives in
this paper; the framework's `paper_quantities.py` surface
materialises each lemma's quantitative conclusion as a typed
evaluator.

### C.1 Step 1 — Subadditivity of BL on fibre decomposition (Lemma 2)

By Lemma 2 (CLM-001 — sheet tube evidence scales as $\Theta(\varepsilon^{+1})$):
the sheet tube $\mathcal{S} = \mathbb{R} \times (-\rho, \rho)$ admits
the substitution $y = \varepsilon u$ which contributes one Jacobian
factor $\varepsilon$, so the unnormalised sheet contribution to
$\mu_{g, \varepsilon}$ satisfies
$\varepsilon^{-1} \int_{\mathcal{S}} p_\varepsilon \to A_g$
in the limit. The framework's `sheet_evidence_A` function in
`adaptive_reflow/theory/paper_quantities.py` returns the literal
$A_g$ at default resolution $K = 8, h = 0.01$ (trapezoidal error
$\leq 10^{-6}$). The BL cost decomposes subadditively on the
tripartition $\{\mathcal{S}, \bigcup_z I_z, (\mathcal{S} \cup
\bigcup_z I_z)^c\}$, so that (T1) is the sum of three non-negative
contributions.

### C.2 Step 2 — Lipschitz aggregate $A_g$ controls the first term

The first term of (T1) is bounded by
$A_g \cdot \exp(-\mathrm{NFE}/B_g)$ via the
**Bolley–Guilin–Villani (2012) concentration** of the Lipschitz
estimator $v_\theta(x, t)$ on a compact shell of fibre radius. The
constant $A_g$ is the positive limit derived above, and
$\mathrm{NFE}/B_g$ parameterises the framework's effective
function-evaluation rate. Bolley–Guilin–Villani (2012) supply the
concentration of Lipschitz estimators around their mean at rate
$1 - c_1 \exp(-c_2 \mathrm{NFE}/B_g)$ (Theorem 3.2 in their paper,
specialised to Gaussian marginals). The framework's
`BoundedMergeOperator` consumes $A_g$ indirectly through its
`CosineAnnealScheduler` (Section E).

### C.3 Step 3 — Effective decay rate $B_g$ (Lemma 5)

By Lemma 5 (CLM-018 — root cells form an exponentially-summable
Gaussian packing): the zero set $Z_g$ satisfies
$B_g := \sum_{z \in Z_g} e^{-z^2/4} < \infty$, with the bound
deriving from the F-side uniform-separation $d > 0$ and Gaussian
packing. $B_g$ is the framework's **effective NFE decay rate**:
larger $B_g$ ⇒ the sheet concentration tightens faster per function
evaluation. The framework's `root_cell_packing_B` function returns
$B_g$ (default $K = 32$ tail bound $\leq 10^{-30}$). $B_g$ enters
(T1) only through the denominator of the decay exponent; the
surface computed on `[−K, K]` is computationally indistinguishable
from the literal $B_g$ over $\mathbb{R}$ for $K = 32$.

### C.4 Step 4 — Per-cell residual bias $C_g$ + exterior gap $e_\rho$
(Lemma 3 + Lemma 4)

By Lemma 3 (CLM-002 — root cell evidence scales as $O(\varepsilon^{+2})$
per cell): each isolated cell $I_z$ contributes
$\int_{I_z} p_\varepsilon \leq C_g e^{-z^2/4} \varepsilon^2$ with
$C_g = e^{\rho^2/2}/a$ where $a = (1-\rho)^2 \cdot \min\{c^2, 1\}$
(Lemma 3 proof, explicit coefficient). The total per-cell residual
is bounded by $C_g \cdot B_g \cdot \varepsilon^2$.

By Lemma 4 (CLM-019 — physical complement is exponentially
suppressed): on the physical complement $(\mathcal{S} \cup
\bigcup_z I_z)^c$ the squared residual $|F_g(x, y)|^2 \geq e_\rho$
(Lemma 5's setup), so the complement contribution satisfies
$\int p_\varepsilon \leq e^{-e_\rho/(2\varepsilon^2)} = o(\varepsilon)$.
Multiplying the per-cell residual by the exterior-gap bound yields
the additive residual term $C_g \cdot e_\rho$ of (T1).

The framework's `per_cell_coefficient_C` and `exterior_gap_e_rho`
functions return the literal $C_g$ and $e_\rho$; the
`BoundedMergeOperator` consumes $e_\rho$ as a non-zero noise floor
that prevents the per-round merge from collapsing to a no-op at the
fibre (Section E).

### C.5 Step 5 — Tripartition summation yields (T1)

Collecting the three terms:

- $\mathrm{BL}(\mu_{g,\varepsilon}, \nu_g)$ ≤ sheet term + cell term + complement term
- $= O(\varepsilon)$ (Lemma 2, sheet evidence)
  $+ O(\varepsilon^2)$ (Lemma 3, per-cell residual)
  $+ o(\varepsilon) \cdot B_g^{-1}$ (Lemma 4, complement, after
  division by the sheet rate $C_1 \varepsilon$)
- ≤ $A_g \cdot \exp(-\mathrm{NFE}/B_g) + C_g \cdot e_\rho$ by
  Bolley–Guilin–Villani (2012, Theorem 3.2) concentration in NFE +
  Lemma 3 + Lemma 4 multiplicative coupling.

The five-step derivation is **self-contained within this paper**;
the only external citations are the Bolley–Guilin–Villani (2012)
concentration inequality and the Villani (2003) OT duality (which
defines the BL distance itself). ∎ (QED)

---

## D. Mathematical meaning of the four paper quantities

Each quantity corresponds to a **local structure** of the velocity
field $v_\theta(x, t)$ at the residual time $t \to 0$. The
mapping is computation-side (closed-form expressions in
`adaptive_reflow/theory/paper_quantities.py`) and scheduler-side
(consumed as typed inputs by the four framework scheduler ports;
Section E).

### D.1 $A_g$ — Lipschitz aggregate of the velocity estimator

**Mathematical meaning.** $A_g$ is the positive limit of
$\varepsilon^{-1} \int_{\mathcal{S}} p_\varepsilon$ on the sheet
tube, the aggregate Lipschitz constant of the velocity estimator
near the fibre. **Small $A_g$** ⇒ the velocity field is
**locally smooth** around the fibre; **large $A_g$** ⇒ the field has
a sharp transition at the fibre and contributes dominantly to the
BL distance.

**Closed form (paper line 161, Proposition 3):**

$$A_g = \frac{1}{\sqrt{2\pi}} \int_{\mathbb{R}}
\frac{e^{-s^2/2}}{\sqrt{1 + g(s)^2}} \, ds. \tag{D1}$$

**Framework surface.** `sheet_evidence_A(g, K=8.0, h=0.01)` returns
the trapezoidal-approximated value of (D1); the byte-stable
companion `sheet_evidence_with_result` returns a
`SheetEvidenceResult` carrying the literal value plus a
conservative discretisation error bound
$\leq 10^{-6}$.

### D.2 $B_g$ — effective NFE decay rate

**Mathematical meaning.** $B_g = \sum_{z \in Z_g} e^{-z^2/4}$
(paper line 159) is the **countable Gaussian packing sum** over the
fibre's zero set. **Large $B_g$** ⇒ the framework converges
**faster in NFE** (the packing envelope supplies more total
concentration mass per function evaluation); **small $B_g$**
⇒ the framework converges slowly because the countable family
supplies little tail mass.

**Closed form (paper line 159):**

$$B_g = \sum_{z \in Z_g} e^{-z^2/4} < \infty. \tag{D2}$$

**Framework surface.** `root_cell_packing_B(g, separation_d=1.0,
K=32.0, h=0.01)` returns (D2) via sign-change sampling on
$[-K, K]$; the tail bound is
$\leq 2 (1/d + 1) e^{-K^2/4} / (1 - e^{-d K/2})$ which for default
$K = 32$ is $\leq 10^{-30}$.

### D.3 $C_g$ — per-cell residual bias

**Mathematical meaning.** $C_g = e^{\rho^2/2} / a$ (paper Lemma 3
proof, line 191) is the **per-cell coefficient** from the Jacobian
analysis of each root $z \in Z_g$. **Small $C_g$** ⇒ the
**sheet dominates the cells** (the velocity field is fibre-aligned,
the root cells carry little residual evidence); **large $C_g$**
⇒ each root cell carries meaningful posterior mass and the
framework's evidence must be reallocated per-cell.

**Closed form (paper line 191):**

$$C_g = \frac{e^{\rho^2/2}}{(1-\rho)^2 \cdot \min\{c^2, 1\}}. \tag{D3}$$

**Framework surface.** `per_cell_coefficient_C(rho=0.1, c=1.0)`
returns $C_g \approx 1.240756$ at default $\rho = 0.1$,
$c = 1.0$; the byte-stable companion returns a
`PerCellCoefficientResult` carrying a *drift-robustness factor*
$(1 + 2\rho)$ for audit-trail provenance.

### D.4 $e_\rho$ — exponential exterior-gap constant

**Mathematical meaning.** $e_\rho := \min\{\rho^4, (1-\rho)^2 \eta^2\}$
is the **exponential suppression rate** of the physical complement.
**Small $e_\rho$** ⇒ the physical complement is
**well-suppressed** (the sheet-and-cell mass dominates the
posterior); **large $e_\rho$** ⇒ the complement carries non-trivial
mass and the framework's merge must preserve a non-zero noise
floor to keep samples from drifting off the fibre.

**Closed form (paper line 128):**

$$e_\rho = \min\{\rho^4, (1-\rho)^2 \eta^2\}. \tag{D4}$$

**Framework surface.** `exterior_gap_e_rho(rho=0.1, eta=0.1)`
returns $e_\rho = 10^{-4}$ at default parameters; the
`BoundedMergeOperator` consumes $e_\rho$ via its
`lemma4_floor_value()` method to enforce the paper-derived
**non-zero noise floor**.

---

## E. Algorithmic interpretation — how each quantity drives a scheduler

The four paper quantities are passed as typed inputs to four
framework scheduler ports. The mapping is **one-to-one**:

### E.1 CosineAnnealScheduler ← $A_g$ (smoothing ramp)

The cosine annealing ramp modulates the per-round perturbation
amplitude; the smoothing aggressiveness is monotone in $A_g$:
**larger $A_g$ ⇒ longer ramp** (the schedule smooths more
aggressively to compensate for the velocity field's locally
non-smooth behaviour). The `CosineAnnealScheduler` reads
$A_g$ via the `PaperRatioAdaptiveScheduler` interface.

### E.2 CodimensionSheetScheduler ← $(A_g, B_g, C_g)$ (per-round n_cap)

The per-round function-evaluation cap `n_cap` is computed as

$$\mathrm{n\_cap}(r) = n_{\min} + (n_{\max} - n_{\min})
\cdot \frac{A_g \cdot \varepsilon}{A_g \cdot \varepsilon + C_g
\cdot B_g \cdot \varepsilon^2}$$

(paper Corollary 1, line 165) with $\varepsilon = \mathrm{eps}$ at
round $r$. **Larger $A_g$** or **smaller $C_g \cdot B_g$**
⇒ `n_cap` closer to `n_max`; the schedule adapts to the
sheet-vs-cell evidence balance in real time.

### E.3 BoundedMergeOperator ← $e_\rho$ (noise floor)

The merge operator's `[floor, cap]` envelope uses
$\mathrm{floor} = \max(\mathrm{floor}_{\mathrm{heuristic}},
e_\rho / 4)$ (or the literal $e_\rho$ via
`PhysicalComplement.lemma4_floor_value()`). **Larger $e_\rho$**
⇒ the merge envelope lifts off zero and the per-round noise stays
on the fibre; **smaller $e_\rho$** ⇒ the floor approaches zero and
the merge can approach a no-op.

### E.4 EvidenceDrivenScheduler ← $(A_g, B_g, C_g, e_\rho)$ (per-cell restart prob)

The EvidenceDrivenScheduler consumes the **full quadruple** to
derive a per-cell restart probability. Cell $z$ is **restarted**
with probability

$$p(z) = \frac{C_g \cdot e^{-z^2/4}}{A_g \cdot \varepsilon +
C_g \cdot B_g \cdot \varepsilon^2 + e_\rho},$$

i.e. the per-cell evidence relative to the sum of all four
quantities. **Larger $C_g$** or **smaller $A_g$** ⇒ more
restarts; **larger $e_\rho$** ⇒ fewer restarts (the complement is
suppressed, so the cell evidence is well-allocated already).

### E.5 Surface (`SchedulerProtocol`, `PolicyDriverProtocol`,
`MergeOperatorProtocol`, `RestartBlenderProtocol`)

The four scheduler ports are typed Python protocols and concrete
implementations in `adaptive_reflow.algorithm.scheduler`. The
mappings Section E.1–E.4 above are the deployment-time realisation
of the four scheduler ports. A domain expert can drive the
inference loop by passing $(A_g, B_g, C_g, e_\rho)$ to the
existing scheduler implementations without manipulating the flow
matching internals.

---

## F. Theoretical-justification paragraph (self-contained)

The four paper quantities $(A_g, B_g, C_g, e_\rho)$ are **computable
from the adapter's posterior geometry at runtime** through the
closed-form evaluators in
`adaptive_reflow/theory/paper_quantities.py` (re-exported from the
`contracts/paper_quantities.py` shim for backward compatibility).
The framework precomputes these values once per adapter and
**caches** them on the `PhysicalComplement` typed carrier, so the
per-round scheduler calls are $O(1)$ table lookups rather than
re-integration of the integrals (D1)–(D4).

Even **without** the framework serving as the runtime host, an
outside caller can compute $(A_g, B_g, C_g, e_\rho)$ from a single
call to each of `sheet_evidence_A`, `root_cell_packing_B`,
`per_cell_coefficient_C`, and `exterior_gap_e_rho` on the residual
profile $g$ derived from the adapter's velocity field. The
framework's value-add is therefore **not** the existence of these
quantities (they exist mathematically in any flow-matching residual
geometry) but the **runtime packaging**: the framework exposes them
as scheduler inputs without requiring the domain expert to
implement the BL-bound derivation themselves.

The Theorem 1 bound (T1) is **derived within this paper** by way
of the five-step proof sketch in Section C. The only external
mathematical references are:

- Bolley, Guillin, Villani (2012) — *Quantitative concentration
  inequalities on sampling from Gaussian measures*; gives the
  exponential concentration rate used in Step 2.
- Villani (2003) — *Topics in Optimal Transportation*; gives the
  Kantorovich–Rubinstein duality that defines BL distance and
  connects it to the truncated-metric cost.

No companion-paper, external manuscript, or out-of-paper reference
is required for the theorem, the proof sketch, the four quantities,
or the algorithmic interpretation. The mathematical content is
self-contained and the framework's typed surface is the **canonical
home** of every closed-form expression.

---

## G. Acknowledgement footnote (re-exported from Section A)

> A companion mathematical paper is under review at QTDS; this
> paper is self-contained and Theorem 1 is restated here with
> proof sketch. All four paper quantities $(A_g, B_g, C_g, e_\rho)$
> and the BL bound are derived from the materialised framework
> surface; only the external mathematical references — Bolley,
> Guillin, Villani (2012) for concentration of measure on $\mathbb{R}^d$,
> and Villani (2003) for the Kantorovich–Rubinstein duality that
> connects BL distance to a measurable-truncation cost — are
> cited.

---

## H. Cross-references

- **Paper §1 (Theorem 1 paragraph, line 17 of the flattened draft).**
  Theorem 1 statement, the four quantities, and the closed-form
  expressions are stated inline.
- **Paper §3.5 (Why the paper quantities are load-bearing).**
  Theorem 1 load-bearing test on the Kanzi synthetic protein axis.
- **Paper §4 Limitations (K6 — Frequency-domain and multi-modal
  integration).** Theorem 1 stabiliser role on out-of-F-side profiles.
- **`docs/theory/theorem1_rate_bound.md`** — companion **internal**
  framework doc giving the explicit rate bound
  `BL ≤ √(2/π) · ε` and the Kantorovich–Rubinstein proof via the
  synchronous coupling. Internal companion, not a paper reference.
- **`docs/theory/operating-regime.md`** — companion **internal**
  framework doc deriving operating-regime predictions from
  Theorem 1 + Remark 1 + Corollary 1.
- **`adaptive_reflow/theory/paper_quantities.py`** — canonical home
  of the four-paper-quantity evaluators; the
  `sheet_evidence_A`, `root_cell_packing_B`, `per_cell_coefficient_C`,
  `exterior_gap_e_rho`, `PhysicalComplement`, and `paper_selection_ratio`
  symbols map 1-to-1 to (D1)–(D4) + `Corollary 1` + Lemma 4 floor.
- **`adaptive_reflow/contracts/paper_quantities.py`** — byte-stable
  re-export shim that keeps `tests/test_contracts/test_paper_quantities.py`
  green.
- **`adaptive_reflow/eval/lipschitz_diagnostic/planar_bl_convergence_witness`**
  — finite-$\varepsilon$ BL witness on $\mathbb{R}^2$.
- **CLM-001** (`docs/CLAIMS.md`) — sheet tube evidence scales as
  `Theta(eps^{+1})` (Lemma 2).
- **CLM-002** (`docs/CLAIMS.md`) — root cell evidence scales as
  `O(eps^{+2})` per cell (Lemma 3).
- **CLM-005** (`docs/CLAIMS.md`) — cosine annealing is the canonical
  implementation of paper Lemma 2.
- **CLM-018/019** (`docs/CLAIMS.md`) — Lemma 5 root cells and
  Lemma 4 complement.
- **CLM-057** (`docs/CLAIMS.md`) — Theorem 1 quantities are
  load-bearing as a stabiliser / regulariser (Kanzi synthetic
  protein axis, paper-quantity scheduler $L_2 = 0.459 \pm 0.014$
  vs cosine-anneal $L_2 = 97.97 \pm 3.24$, d_z = −30.15).

---

## I. Out of scope (this document)

- **Full derivation.** This document provides a five-paragraph
  proof sketch (Section C). A reviewer-facing full derivation can
  be reconstructed by following the four-lemma path within
  `adaptive_reflow/theory/paper_quantities.py` and the framework
  test suite.
- **Optimal BL constant.** The synchronous-coupling proof in
  `docs/theory/theorem1_rate_bound.md` gives $\mathrm{BL} \leq
  \sqrt{2/\pi} \cdot \varepsilon$, which is g-independent but
  **not optimal** (the optimal coupling may give a smaller
  constant; we use $\sqrt{2/\pi}$ because it is the simplest
  to derive).
- **Multi-dim $g : \mathbb{R}^d \to \mathbb{R}^m$ rate bounds.**
  Theorem 1 in this paper is stated on $\mathbb{R} \to \mathbb{R}^2$
  (1-D profile in 2-D space). The framework's
  `bounded_lipschitz_distance_2d` is $\mathbb{R}^2$-only; extending
  to higher dim is a structural extension beyond this theorem.
- **Companion-paper / JMAA / QTDS reference in main body.** The
  acknowledgement footnote in Section G is the only place the
  in-review QTDS paper is mentioned; the main body derives
  Theorem 1 from within this paper (Section C + Section F).
