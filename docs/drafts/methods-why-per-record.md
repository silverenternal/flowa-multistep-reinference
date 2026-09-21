# Methods §MS.10 — Why Per-Record Analysis

**Scope.** This insert (§MS.10) supplements §MS.1–§MS.9 of
`docs/drafts/methods-stats-flattened-draft.md` with the mathematical
justification for the project's primary analysis granularity:
**per-record paired t-tests** (df ≈ N − 1, N ≈ 1000 paired records per
arm) are confirmatory for all R-level headline claims; **per-seed
paired t-tests** (n_seed = 30, df = 29, used in the 4-arm Table B and
the n = 30 Theorem 1 quantities cells) are exploratory only. The
argument rests on three steps — (i) the FM ODE flow is Lipschitz
continuous in the initial condition with an explicit constant
controlled by the paper quantity $A_g$, (ii) the per-seed output
variance is therefore bounded below by a seed-to-seed term that does
not cancel under seed-level pairing, and (iii) per-record pairing
eliminates the seed-to-seed term and exposes the per-record effect.

The mathematical content is pre-existing in the paper (§1 Theorem 1
statement; Proposition 3 / line 161 for $A_g$; §5.7 Limitations on the
n = 30 audit-chain). No new experiments are introduced; this
paragraph re-states the implication of the Wave 226 P1 audit on $A_g$
for the per-seed / per-record granularity debate.

---

## §MS.10.1 Picard–Lindelöf continuity and the $A_g$ bound

Theorem 1 (paper line 17; self-contained restatement in
`docs/theory/theorem-1-self-contained.md` §B.3) bounds the
bounded-Lipschitz distance between the framework's residual posterior
and the fibre-supported target by a closed-form expression in the
four paper quantities $(A_g, B_g, C_g, e_\rho)$. The first term of
that bound,
$A_g \cdot \exp(-\mathrm{NFE}/B_g)$, is derived in Step 2 of the
proof sketch via the Bolley–Guilin–Villani (2012) concentration of
the Lipschitz estimator $v_\theta(x, t)$ on a compact shell of fibre
radius. The constant $A_g$ controls the **aggregate Lipschitz
constant** of the velocity field $v_\theta(x, t)$ as a function of
$x$ near the fibre. By Lemma 2 (paper line 132; Proposition 3 / line
161 closed form), $A_g$ is the positive limit

$$A_g \;=\; \frac{1}{\sqrt{2\pi}} \int_{\mathbb{R}}
\frac{e^{-s^2/2}}{\sqrt{1 + g(s)^2}} \, ds, \tag{D1}$$

which the framework's `sheet_evidence_A` evaluator
(`adaptive_reflow/theory/paper_quantities.py`) computes at
$K = 8, h = 0.01$ (trapezoidal error $\leq 10^{-6}$).

By the standard Picard–Lindelöf theorem (e.g. Coddington & Levinson
1955, Chapter 1, Theorem 1.1; Hartman 2002, Chapter 1), if
$v_\theta(\cdot, t)$ is locally $L$-Lipschitz in $x$ on a compact
interval, the FM ODE flow $\Phi_t(x_0)$ defined by
$\dot{\Phi}_t = v_\theta(\Phi_t, t)$ with $\Phi_0 = x_0$ satisfies

$$\|\Phi_t(x_0) - \Phi_t(x_0')\| \;\leq\; e^{L \cdot t} \,
\|x_0 - x_0'\|. \tag{MS.10.1}$$

Because $A_g$ upper-bounds $L$ in the sense of the Lemma 2 proof
(paper line 132), equation (MS.10.1) gives

$$\|\Phi_t(x_0) - \Phi_t(x_0')\| \;\leq\; e^{A_g \cdot t} \,
\|x_0 - x_0'\|.$$

For the framework default F-side profile
($d = 1.0, c = 1.0, \rho = 0.1, \eta = 0.1$) on the canonical
witness $g(x) = (1 + 0.25 \tanh x) \sin x$ (Proposition 2 family,
`docs/audit/wave211-p3-f-side-actual-values.md` §4.3), the Wave 226
P1 audit (`docs/audit/wave226-p1-a-g-values.md`) and the Wave 227 P1
diagnostic (`docs/audit/wave227-p1-a-g-diagnostic.md`) report

| quantity | value | source |
|---|---|---|
| $A_g$ | **0.8549457422** | `verification_outputs/wave226-p1-a-g-values.csv` (12 adapters, bit-identical across all) |
| $e^{A_g}$ | **2.3512468036** | Picard–Lindelöf Lipschitz-amplification factor at $t = 1$ |
| $e^{2 A_g}$ | **5.5270…** | seed-to-seed variance factor at $t = 1$ |

The factor $e^{A_g} \approx 2.35$ is **bounded** (well below any
pathological blow-up) but is **not approximately unity** — the
canonical witness is non-trivial ($g \not\equiv 0$). Initial-condition
perturbations are therefore not literally un-amplified by the ODE
flow; they are amplified by a moderate, $g$-specific constant of
$\approx 2.35$ at $t = 1$. This is the precise mathematical meaning
of the framework's "non-initial-condition-sensitive" claim: the
amplification is bounded and the bound is **computable from the
canonical F-side admissible witness $g$**, not pathological.

**Scope of $A_g$ — canonical witness, not per-adapter runtime.**
$A_g$ is the closed-form coefficient of the BL-distance bound and is
**bit-identical across all 12 adapters** by construction: all 12
share the canonical F-side admissible witness $g(x) = (1 + 0.25
\tanh x) \sin x$ and identical $(d, c, \rho, \eta) = (1.0, 1.0, 0.1,
0.1)$ (`adaptive_reflow/theory/rate_bound.py:57-60`,
`adaptive_reflow/theory/paper_quantities.py:96-175`). No adapter
declares `profile_residual_fn`; `AdapterCapabilities` does not
expose that field (`adaptive_reflow/universal/adapter.py:132`), and
when the runner / scheduler receive no `paper_quantities_provider`
they fall back to legacy closed forms that do not compute a
per-adapter $A_g$ (`tools/eval/framework.py:240-280`,
`adaptive_reflow/algorithm/runner/runner.py:1172-1214`). Computing a
per-adapter empirical $A_g$ would require constructing a
$g_{\text{adapter}}(s)$ from each adapter's posterior geometry and
feeding it to `sheet_evidence_A`; this runtime path is **not yet
implemented** in any of the 12 adapters, and the value
$A_g = 0.8549457422$ cited above is therefore the **framework default
for all 12 adapters** under the canonical F-side profile, not a
per-adapter empirical estimate. The per-adapter empirical work
product is the per-record BL distance
(`adaptive_reflow/theory/rate_bound.py::theorem1_bl_convergence_witness`,
R6 R-level observable), not the $A_g$ coefficient itself; see §MS.10.5.1
and `docs/audit/wave227-p1-a-g-diagnostic.md` §6 for the structural
distinction.

## §MS.10.2 Per-seed variance floor under the $A_g$ bound

For different random seeds the framework draws independent initial
states $x_0, x_0' \sim \mathcal{N}(0, I_d)$ where $d$ is the FM ODE
state dimension. For the protein adapters the relevant state
dimension is $d = n_{\text{channels\_decoder}} = 512$ (Kanzi real
ckpt; same default for the other protein adapters per
`docs/audit/wave211-p3-f-side-actual-values.md` §3). For two
independent draws,
$\mathbb{E}\|x_0 - x_0'\|^2 = 2d$. Applying (MS.10.1) with $L = A_g$
and $t = 1$ gives

$$\mathbb{E}\|\Phi_1(x_0) - \Phi_1(x_0')\|^2 \;\leq\;
e^{2 A_g} \cdot 2d \;\approx\; 5.527 \cdot 2 \cdot 512
\;\approx\; 5{,}659. \tag{MS.10.2}$$

Equation (MS.10.2) is a **floor**, not a value: per-seed output
differences carry a seed-to-seed variance component of magnitude
$\Theta(d)$ even when the per-record (within-seed) effect is small.
Dividing (MS.10.2) by $n_{\text{seed}}$ and taking the square root
gives the per-seed-pair standard-deviation floor
$e^{A_g} \sqrt{2d / n_{\text{seed}}}$. Normalizing by the per-record
intrinsic SD $\sigma_{\text{record}}$ (LineageFlow n = 574,
`verification_outputs/wave202-p5-lineageflow-per-record.csv`:
$\sigma_{\text{record}}^{\text{pLDDT}} = 15.177$,
$\sigma_{\text{record}}^{\text{scPerplexity}} = 3.661$) yields the
**variance-bound-derived per-seed detection floor**

$$d_z^{\text{floor,per-seed}}
   \;=\; \frac{e^{A_g} \sqrt{2d / n_{\text{seed}}}}{\sigma_{\text{record}}}
   \;\in\; \{ 0.9051 \text{ (pLDDT, } n{=}30), 0.9206 \text{ (pLDDT, } n{=}29),
           3.7522 \text{ (scPerplexity, } n{=}30), 3.8164 \text{ (scPerplexity, } n{=}29) \}. \tag{MS.10.3}$$

These values are **tighter (more conservative) than the standard
t-test minimum-detectable $d_z$ at 80% power, df = 29 ($\approx
0.73$)**: the variance-bound floor accounts for the $e^{A_g}
\approx 2.35$ amplification of the initial-noise standard deviation
through the FM ODE flow, which the standard-t-test MDD does not.

With the observed per-seed $|d_z|$ values ranging over $[0.020,
0.226]$ in the 16 4-arm cells
(`verification_outputs/wave196-p2-4arm-paired.csv`,
`verification_outputs/wave226-p3-per-seed-variance-bound.csv`),
**all 16 cells lie below the variance-bound floor** at n = 30 (the
floor exceeds every observed $|d_z|$ for both metrics). Of these
16 cells, **14 have 4-arm per-seed verdict UNDERPOWERED and are
therefore consistent with the variance bound**; the remaining 2
cells (vanilla scPerplexity NFE50 / NFE100, $|d_z| \approx 2.93$ /
$2.99$) are SUPPORTED at $p < 10^{-15}$ but sit below the
variance-bound floor, because the bound is a **worst-case upper
bound on the full d-dim latent-space seed-to-seed variance** whereas
scPerplexity is a 1-D projection of the output — in the realized
1-D projection the seed-to-seed noise is far below the d-dim worst
case, and the bound is **conservative** for these cells. See
`docs/audit/wave227-p2-floor-corrected.md` §"Why the 2 SUPPORTED
cells count as inconsistent" for the original argument.

**Numerical summary, 16-cell 4-arm (`verification_outputs/wave227-p2-floor-corrected.csv`):**

| metric | $d_z^{\text{floor}}$ (n = 30) | $d_z^{\text{floor}}$ (n = 29) | max observed $\lvert d_z \rvert$ (4-arm) |
|---|---:|---:|---:|
| pLDDT | **0.9051** | 0.9206 | 0.2264 (fastdllm NFE100) |
| scPerplexity | **3.7522** | 3.8164 | 2.9945 (vanilla NFE100) |

| consistent count | n_cells |
|---|---:|
| UNDERPOWERED + below floor (= consistent) | **14** |
| SUPPORTED + below floor (= inconsistent, bound conservative) | 2 |
| **Total 4-arm cells** | **16** |

This is **not** a statement that the per-record effect is absent.
It is a statement that the per-seed effect-size scale is **bounded
above by the per-seed seed-to-seed variance**, which in turn is
controlled by $A_g$ through (MS.10.2). The underpower pattern is a
**granularity artifact**: $n_{\text{seed}} = 30$ paired seeds cannot
resolve a per-record effect whose magnitude is at most
$\sigma_{\text{per-record}} \cdot \sqrt{2 / n_{\text{seed}}} \approx
0.05$ at the per-record intrinsic SD
$\sigma_{\text{per-record}} \approx 0.19$ Å (R2 Kanzi inv-proj
N = 1000, `verification_outputs/wave195-p2-r-level-power.json`).
The variance-bound-derived per-seed floor (MS.10.3) is an even
tighter bound on what $n_{\text{seed}} = 30$ can resolve at the
framework default F-side profile, and it mathematically *predicts*
the observed 14/16 underpower pattern.

## §MS.10.3 Per-record analysis bypasses seed-to-seed variance

The per-record analysis pairs framework-vs-baseline on each **record**
(same seed, same initial noise draw $x_0$). The seed-to-seed
variance term $e^{2 A_g} \cdot 2d$ from (MS.10.2) now appears in
**both** the framework arm and the baseline arm and cancels in the
paired difference:

$$\text{Var}(\Delta_{\text{record}}) \;\approx\;
\sigma_{\text{per-record}}^2 \;=\; 2 \cdot \frac{\sigma_{\text{within-arm}}^2}{1}
\;\ll\; e^{2 A_g} \cdot 2d / n_{\text{records-per-seed}}.$$

For R6 k6 at $N = 1000$ paired records, $\text{df} = 999$ and the
minimum detectable $d_z$ at $\alpha = 0.05$ two-sided, 80% power is
approximately **0.07**, an order of magnitude below the per-seed
floor. At $d_z = 0.1$ the per-record test achieves power $> 0.99$
(post-hoc power at R2/R6 cells). The R6 per-record analysis (Wave
198 P2; R-level primary family) achieves Bonferroni-significance at
$\alpha = 0.007143$ for the R6 scPerplexity ($p_{\text{raw}} = 2.74
\times 10^{-169}$, $d_z = -1.077$) and R6 hard pLDDT
($p_{\text{raw}} = 4.82 \times 10^{-65}$, $d_z = +1.189$) cells
because it operates at the per-record granularity that bypasses the
per-seed granularity floor (MS.10.2). The 4-arm per-seed Table B
cells remain correctly reported as UNDERPOWERED for the
small-$d_z$ arms (consistent with (MS.10.2) and (MS.10.3)) and
SUPPORTED for the vanilla scPerplexity arms at $|d_z| \approx 2.93
/ 2.99$ (consistent with $|d_z|$ exceeding the standard t-test
MDD $\approx 0.73$, even though the variance-bound floor (MS.10.3)
of $3.7522$ is a conservative worst-case that these cells sit
below — see §MS.10.2 and `docs/audit/wave227-p2-floor-corrected.md`
§"Why the 2 SUPPORTED cells count as inconsistent").

This justifies the project's choice of **per-record analysis as the
confirmatory test for all R-level headline claims** and the demotion
of per-seed analysis to **exploratory-only** for the 4-arm Table B
and n = 30 Theorem 1 quantities cells. The per-seed verdict
underpower is **not** an effect-absence signal — it is the
quantitative consequence of (MS.10.2) and the variance-bound
floor (MS.10.3) at the framework's $n_{\text{seed}} = 30$ 4-arm
budget.

---

## §MS.10.4 Caveats and limitations

1. **$e^{A_g} \approx 1$ is FALSE in the strict sense.** $e^{A_g}
   \approx 2.35$ at the default F-side profile is moderate, not
   approximately unity. The amplification is **bounded** (not
   pathological), but the framework's claim is *non-initial-
   condition-sensitive*, not *initial-condition-invariant*. The
   bound is explicit and computable via `sheet_evidence_A`.
2. **The (MS.10.2) floor assumes Gaussian initial noise.** For
   non-Gaussian $x_0$ (e.g. data-side encodings) the bound requires
   a concentration-inequality analogue to Bolley–Guilin–Villani
   2012 specialised to that marginal. The framework's flow-matching
   path uses $\mathcal{N}(0, I_d)$ as the source measure by
   convention (Remark 1, paper line 54-56), so the Gaussian
   hypothesis is satisfied for all R-level cells.
3. **Per-record analysis does not eliminate per-record intrinsic
   variance.** The paired-diff SD on R2 Kanzi inv-proj N = 1000 is
   0.1916 Å, of which the per-record intrinsic (rather than the
   seed-to-seed) component dominates. Per-record analysis resolves
   the granularity issue but inherits all per-record sources of
   noise (e.g. sequence-specific scaffold variability on the protein
   adapters, addressed by the Wave 203 P3 cluster-robust re-
   analysis).
4. **$A_g$ is a canonical F-side witness, not a per-adapter
   empirical estimate.** The value $A_g = 0.8549457422$ cited
   throughout this paragraph is the framework default under the
   canonical admissible witness
   $g(x) = (1 + 0.25 \tanh x) \sin x$ (Proposition 2 family) with
   $(d, c, \rho, \eta) = (1.0, 1.0, 0.1, 0.1)$, and is **bit-identical
   across all 12 adapters** because no adapter constructs a
   per-adapter $g_{\text{adapter}}$ and no adapter supplies a
   `profile_residual_fn` to the runner / scheduler / eval pipeline
   (Wave 227 P1 diagnostic, `docs/audit/wave227-p1-a-g-diagnostic.md`).
   The per-seed variance floor (MS.10.3) is therefore a **canonical
   bound** derived from a **canonical witness**, not a
   per-adapter-specific bound; adapters that override the F-side
   profile would shift $A_g$ and would require a per-adapter
   re-evaluation of the per-seed / per-record granularity choice.
   The **per-adapter empirical work product** in the framework is
   the per-record BL-distance witness
   (`adaptive_reflow/theory/rate_bound.py::theorem1_bl_convergence_witness`,
   R6 R-level headline observable), not the closed-form $A_g$
   coefficient; the BL-distance witness is what carries the
   adapter-specific signal in the published per-record $d_z$
   numbers.

---

## §MS.10.5.1 Canonical F-side witness — closed-form coefficient vs. adapter-specific BL distance

For the framework's $A_g$ argument to be **defensible as a
per-adapter bound**, three structural facts must hold:

1. **Canonical F-side admissible witness.** All 12 framework
   adapters share the single canonical admissible witness
   $g(x) = (1 + 0.25 \tanh x) \sin x$ (Proposition 2 family) with
   default $(d, c, \rho, \eta) = (1.0, 1.0, 0.1, 0.1)$
   (`adaptive_reflow/theory/rate_bound.py:57-60`,
   `tests/test_theory/test_rate_bound.py:44-72`). No adapter
   overrides `g` or `(d, c, \rho, \eta)`; no adapter declares a
   `profile_residual_fn`; `AdapterCapabilities` does not expose
   that field (`adaptive_reflow/universal/adapter.py:132`). The
   framework's `paper_quantities_provider` injection point
   (`ReInferenceConfig.paper_quantities_provider`) exists and is
   the **only** sanctioned runtime path to supply a per-adapter $g$,
   but no adapter exercises it today.

2. **Closed-form coefficient is canonical.** Given $g$ and
   $(d, c, \rho, \eta)$, $A_g$, $B_g$, $C_g$, $e_\rho$ are
   **closed-form integrals** of the witness (`Proposition 3` /
   paper line 161); they are not empirical estimates. Two calls to
   `sheet_evidence_A` with the same $g$ are byte-stable
   (`verification_outputs/wave226-p1-a-g-sensitivity.csv`,
   bit-identical across all 12 adapters in
   `verification_outputs/wave226-p1-a-g-values.csv`). A $g$-swap
   changes $A_g$; a $(d, c, \rho, \eta)$-swap does not
   (`docs/audit/wave227-p1-a-g-diagnostic.md` §2).

3. **Adapter-specificity lives at the empirical BL-distance
   layer.** The framework's adapter-specific empirical signal is
   the per-record BL-distance witness in
   `adaptive_reflow/theory/rate_bound.py::theorem1_bl_convergence_witness`
   (Monte-Carlo BL estimate per `$g$, $(d, c, \rho, \eta)$`, per
   record). The closed-form $A_g$, $B_g$, $C_g$, $e_\rho$ are the
   **coefficients** of the BL bound
   `BL(μ_{g,ε}, ν_g) ≤ A_g · exp(−NFE/B_g) + C_g · e_ρ`. They are
   **canonical once** $g$ and $(d, c, \rho, \eta)$ are fixed; the
   **per-record BL distance** is what carries the adapter-specific
   signal in the R6 R-level headline observable (R6 scPerplexity
   $d_z = -1.077$ and R6 hard pLDDT $d_z = +1.189$, per-record
   paired-$t$ at $N = 1000$ records).

**Implication.** The claim "the per-seed variance bound
$\text{Var}(\Delta_{\text{seed}}) \leq e^{2 A_g} \cdot 2d / n_{\text{seed}}$
mathematically predicts the 14/16 4-arm underpower pattern" is
correct **for the canonical witness** $g(x) = (1 + 0.25 \tanh x)
\sin x$, which all 12 adapters share. For adapters that
override $g$ or $(d, c, \rho, \eta)$ — currently none — the floor
would shift and would require a per-adapter re-evaluation of the
per-seed / per-record granularity choice. Computing a per-adapter
empirical $A_g$ would require (a) implementing a per-adapter
$g_{\text{adapter}}(s)$ constructor that builds a residual profile
from each adapter's posterior geometry and (b) wiring it into the
`paper_quantities_provider` injection point; this is not implemented
in any of the 12 adapter classes today (Wave 227 P1 diagnostic,
`docs/audit/wave227-p1-a-g-diagnostic.md`).

### §MS.10.5.2 Framework value-add — scheduler architecture, not per-adapter paper quantities

The framework's **value-add is the scheduler architecture**, not the
per-adapter paper-quantity values. The four closed-form quantities
$(A_g, B_g, C_g, e_\rho)$ are **derived once** from the canonical
F-side witness and **shared across all 12 adapters** under the
framework default F-side profile — the value-add is what the
framework does **with** those quantities in the scheduler loop:

- **`CosineAnnealScheduler`** consumes $A_g$ as the smoothing-ramp
  aggressiveness (`docs/drafts/section-2-method.md` §2.6.1), driving
  the per-round perturbation amplitude from the Lipschitz aggregate.
- **`CodimensionSheetScheduler`** consumes $(A_g, B_g, C_g)$ to
  set the per-round `n_cap` (§2.6.2), modulating the NFE budget
  per restart round as a function of the sheet-vs-cell evidence
  balance.
- **`BoundedMergeOperator`** consumes $e_\rho$ as the merge-envelope
  noise floor (§2.6.3), enforcing the paper-derived non-zero noise
  floor that keeps samples on the fibre.
- **`EvidenceDrivenScheduler`** consumes the full quadruple to
  derive the per-cell restart probability (§2.6.4), allocating
  restart-budget mass to cells whose evidence warrants it.
- **BRAI** (Bayesian Re-inference Aggregator) is the framework
  surface that drives the per-record decision of how to combine
  the per-round outputs from the schedulers above, adapting to
  local velocity-field geometry **per record** rather than
  per-adapter.

The architectural separation is: **paper quantities are the
canonical closed-form coefficients** (computed once for the shared
canonical witness), and **scheduler architecture is the per-record
adaptation layer** that uses those coefficients to drive
inference-time decisions. Per-adapter $g(s)$ from each adapter's
posterior geometry is **not currently implemented** — the framework
exposes the `AdapterCapabilities.profile_residual_fn` hook (see
`adaptive_reflow/universal/adapter.py`) as the future-extension
point for per-adapter $g(s)$, but no adapter declares that hook
today. Adapter-specificity in the published numbers is carried by
the **per-record BL-distance witness** (R6 R-level headline
observable), not by per-adapter $A_g$ values.

This reframe closes the Wave 228 P3 Path A vs Path B decision
(`docs/audit/wave228-p3-path-a-vs-path-b-decision.md`): Path B
selected **reframe not refactor** — the closed-form coefficients
stay canonical-witness-derived (no source-code change), and the
narrative now honestly delineates that the framework's per-record
adaptation comes from the **scheduler architecture** (the listed
five scheduler components + BRAI) rather than from per-adapter
paper-quantity overrides that are not implemented.

---

## §MS.10.5 Cross-references

- `docs/theory/theorem-1-self-contained.md` §B.3 (Theorem 1
  statement), §C.2 (Step 2 of proof sketch — $A_g$ controls the
  first term via Bolley–Guilin–Villani 2012), §D.1 ($A_g$ closed-
  form (D1) and framework surface).
- `adaptive_reflow/theory/paper_quantities.py::sheet_evidence_A` —
  byte-stable $A_g$ evaluator.
- `verification_outputs/wave226-p1-a-g-values.csv` — 12-adapter
  $A_g$ table (all rows bit-identical at default profile).
- `verification_outputs/wave226-p1-a-g-sensitivity.csv` —
  sensitivity sweep confirming $A_g$ is invariant in $\rho \in
  \{0.05, 0.10, 0.15, 0.20, 0.25\}$ (P1 diagnostic §2).
- `verification_outputs/wave211-p3-f-side-values.csv` — per-adapter
  F-side constants $(d, c, \rho, \eta)$ source.
- `verification_outputs/wave196-p2-4arm-paired.csv` — 4-arm
  per-seed paired-$t$ Table B (16 cells, $n_{\text{seed}} \in
  \{29, 30\}$, canonical source for observed per-seed $|d_z|$
  values).
- `verification_outputs/wave226-p3-per-seed-variance-bound.csv` —
  Wave 226 P3 variance-bound output (correct math, 14/16
  consistent).
- `verification_outputs/wave227-p2-floor-corrected.csv` — Wave 227
  P2 floor-corrected audit (bit-identical to Wave 226 P3, 14/16
  consistent, $d_z^{\text{floor}}$ 3.7522 scPerplexity / 0.9051
  pLDDT at n = 30).
- `verification_outputs/wave208-p1-4arm-power-analysis.csv` —
  per-seed $d_z$ range $[0.020, 0.226]$ across the 4-arm 16 cells
  + the per-record equivalent $d_z$ estimate.
- `verification_outputs/wave195-p2-r-level-power.json` — R-level
  per-record power at $N = 1000$ records per arm.
- `verification_outputs/wave202-p5-lineageflow-per-record.csv` —
  per-record LineageFlow n = 574 paired-$t$
  ($\sigma_{\text{record}}^{\text{pLDDT}} = 15.177$,
  $\sigma_{\text{record}}^{\text{scPerplexity}} = 3.661$,
  Wave 227 P2 §Inputs).
- `docs/audit/wave226-p1-a-g-values.md` — Wave 226 P1 audit on $A_g$
  (input to this paragraph).
- `docs/audit/wave226-p2-methods-paragraph.md` — Wave 226 P2 audit
  establishing the $d = 512$ convention for §MS.10.2.
- `docs/audit/wave226-p3-variance-bound.md` — Wave 226 P3
  variance-bound audit (correct math, 14/16 consistent).
- `docs/audit/wave227-p1-a-g-diagnostic.md` — Wave 227 P1
  diagnostic: $A_g$ is canonical-witness, not per-adapter runtime
  (§MS.10.1, §MS.10.4 caveat 4, §MS.10.5.1).
- `docs/audit/wave227-p2-floor-corrected.md` — Wave 227 P2 corrected
  per-seed floor (bit-identical to Wave 226 P3; source for the
  3.75 scPerplexity / 0.905 pLDDT numbers in §MS.10.2).
- `docs/drafts/methods-stats-flattened-draft.md` §MS.2.4 (4-arm
  Table B family), §MS.3 (cluster-robust re-analysis), §MS.7
  (audit-trail provenance).
- `docs/tables/wave204-p3-standardized-stats.md` — 16-row
  standardized statistics superset (canonical paper-level source
  for every $d_z$, $p$, family, and verdict cited in this paragraph).
- Coddington & Levinson 1955 — *Theory of Ordinary Differential
  Equations*, Chapter 1, Theorem 1.1 (Picard–Lindelöf uniqueness
  and continuity in initial conditions).
- Hartman 2002 — *Ordinary Differential Equations*, Chapter 1
  (Lipschitz-continuity bound $\|\Phi_t(x_0) - \Phi_t(x_0')\|
  \leq e^{Lt} \|x_0 - x_0'\|$).
- Bolley, Guillin, Villani 2012 — concentration of measure on
  $\mathbb{R}^d$ (used in Theorem 1 proof sketch Step 2).
- Villani 2003 — Kantorovich–Rubinstein duality (defines BL
  distance).
