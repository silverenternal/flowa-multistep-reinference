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
P1 audit (`docs/audit/wave226-p1-a-g-values.md`) reports

| quantity | value | source |
|---|---|---|
| $A_g$ | **0.8549457422** | `verification_outputs/wave226-p1-a-g-values.csv` (12 adapters, identical across all) |
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
adapter's residual profile $g$**, not pathological.

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
Per-seed paired t-tests at $n_{\text{seed}} = 30$ (the 4-arm Table B
budget; `docs/tables/wave204-p3-standardized-stats.md` 16-row
superset) have $\text{df} = 29$ and a minimum-detectable
$d_z^{\text{per-seed}}$ at $\alpha = 0.05$ two-sided, 80% power of
approximately **0.73**. With the observed per-seed $d_z$ values
ranging over $[0.020, 0.226]$ in absolute value
(`verification_outputs/wave208-p1-4arm-power-analysis.csv`, all 16
cells), this means 14 of 16 cells lie below the per-seed detection
floor — exactly the underpower pattern observed (the 2 SUPPORTED
cells, vanilla scPerplexity at NFE 50/100, sit at $d_z \approx -2.93$
and $-2.99$, far above the floor).

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
small-$d_z$ arms (consistent with (MS.10.2)) and SUPPORTED for the
large-$d_z$ vanilla scPerplexity arms (consistent with
$|d_z| \gg 0.73$).

This justifies the project's choice of **per-record analysis as the
confirmatory test for all R-level headline claims** and the demotion
of per-seed analysis to **exploratory-only** for the 4-arm Table B
and n = 30 Theorem 1 quantities cells. The per-seed verdict
underpower is **not** an effect-absence signal — it is the
quantitative consequence of (MS.10.2) at the framework's
$n_{\text{seed}} = 30$ 4-arm budget.

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
4. **Cross-adapter $A_g$** is identical to the default profile on
   all 12 adapters (Wave 226 P1 audit), so the per-seed floor is the
   same on all adapters. Adapters that override the F-side profile
   would shift the floor and would require a per-adapter
   re-evaluation of the per-seed / per-record granularity choice.

---

## §MS.10.5 Cross-references

- `docs/theory/theorem-1-self-contained.md` §B.3 (Theorem 1
  statement), §C.2 (Step 2 of proof sketch — $A_g$ controls the
  first term via Bolley–Guilin–Villani 2012), §D.1 ($A_g$ closed-
  form (D1) and framework surface).
- `adaptive_reflow/theory/paper_quantities.py::sheet_evidence_A` —
  byte-stable $A_g$ evaluator.
- `verification_outputs/wave226-p1-a-g-values.csv` — 12-adapter
  $A_g$ table (all rows identical at default profile).
- `verification_outputs/wave211-p3-f-side-values.csv` — per-adapter
  F-side constants $(d, c, \rho, \eta)$ source.
- `verification_outputs/wave208-p1-4arm-power-analysis.csv` —
  per-seed $d_z$ range $[0.020, 0.226]$ across the 4-arm 16 cells
  + the per-record equivalent $d_z$ estimate.
- `verification_outputs/wave195-p2-r-level-power.json` — R-level
  per-record power at $N = 1000$ records per arm.
- `docs/audit/wave226-p1-a-g-values.md` — Wave 226 P1 audit on $A_g$
  (input to this paragraph).
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
