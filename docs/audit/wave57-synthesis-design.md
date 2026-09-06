# Wave 57 Agent D — Synthesis & design doc: closing the FlowMol3 restart gap

**Date:** 2026-09-07
**Wave:** 57, Agent D (synthesis)
**Inputs:**
* `docs/audit/wave57-nfe-adaptive-research.md` (Agent A — 2026 literature)
* `docs/audit/wave57-pattern-investigation.md` (Agent B — 3/9 vs 6/9 statistics)
* `docs/audit/wave57-flowmol3-restart-interaction.md` (Agent C — CTMC ↔ restart-blend math)

**Scope of this doc:** READ-ONLY synthesis. No code changed. It names one
primary fix, ranked backups, an honest paper framing for §7.5, and a
5-step implementation plan for Wave 58.

---

## 1. Executive summary

### 1.1 What the three agents actually established

| Claim | Evidence | Verdict |
|---|---|---|
| All 3 NFE=10 cells regress (mean −15.94%) | Agent B §1, §3.1 | **TRUE** |
| *All* regressions are at NFE=10 | Agent B §2.2 | **FALSE** — 3/6 regressions are at NFE 50/200 |
| Mean delta is monotone in NFE (−15.9% → −8.5% → +1.1%) | Agent B §3.1 | **TRUE**, strongest signal in the data |
| The NFE=10 effect is statistically significant | Agent B §4 (sign p=0.125; Wilcoxon W+=10, p≈0.10) | **NOT ESTABLISHED** (n=3 per stratum) |
| Seed 44 regresses at *every* NFE (3/3, lowest variance) | Agent B §3.2 | **TRUE** — NFE-independent failure |
| The adapter's restart prior omits CTMC mask tokens | Agent C §2.2, `flowmol3_v2_adapter.py:457-495` vs `ctmc_vector_field.py:121-134` | **TRUE — a correctness bug** |
| The literature endorses disabling refinement below an NFE threshold | Agent A §3.1 (A-FloPS, ASFM, Instance-Aware, Adaptive Sparse Sampling) | **NO paper endorses it**; the 2026 consensus is *smarter allocation*, not abandonment |

### 1.2 The decisive tension

Agents A and C both land on the same immediate recommendation — an
NFE-adaptive gate that skips restart-blend below ~NFE 20. This synthesis
**declines that as the primary fix**, for three reasons drawn from the
agents' own evidence:

1. **It cannot explain the data.** Half the regressions (seed 42 @ NFE 50,
   seed 44 @ NFE 50, seed 44 @ NFE 200) sit *above* any plausible
   threshold. A gate at NFE<20 leaves 3/6 regressions untouched and
   the seed-44 failure entirely unexplained.
2. **It is fitted to n=3 per stratum.** Agent B could not reject H0 at
   α=0.05. Hard-coding a threshold calibrated on an under-powered
   stratum is exactly the overfitting that Agent A's §3.1 survey warns
   against — no 2025/2026 paper does this, and three of them win *at*
   the low-NFE regime that our gate would abandon.
3. **It suppresses a symptom of a bug Agent C already localised.** Agent
   C §2.2 found that the framework's "fresh prior" starts every
   categorical token *unmasked*, which is the opposite of what
   Campbell-style CTMC expects at t=0 (`will_unmask` filters on
   `xt == mask_index`, `ctmc_vector_field.py:446`). That is not a
   regime limitation; it is a wrong prior, and it is wrong at NFE=200
   too — which is precisely the shape of the seed-44 finding.

### 1.3 Recommended primary fix

> **P0 — Mask-token-correct restart prior.** Make the adapter's fresh
> prior draw (`_sample_a0`, `_sample_e0`, and the `_sample_native_state`
> assembly) emit the CTMC **mask token** for the categorical channels
> `(a, c, e)` at t=0, matching upstream `ctmc_vector_field.py:121-134`,
> and make `_channel_aware_blend` mask-aware so a blend never converts a
> mask token into a spurious concrete label.

This is a correctness fix, not a tuning knob. It is NFE-independent, it
addresses the mechanism Agent C traced end-to-end, and — unlike a gate —
it can plausibly improve *all* nine cells rather than flattening three of
them to "framework ≡ baseline". It also keeps the JMAA Theorem-1
re-inference mechanism live at low NFE, which is where Agent A's survey
says the field is heading.

The NFE gate is retained as **backup B1**, to be shipped only if P0 fails
to flip the NFE=10 stratum, and then framed as an *operating-regime
declaration* rather than a fix.

### 1.4 What we will and will not claim

We will not claim "framework improves FlowMol3". The n=9 sweep does not
support it in either direction (Agent B §4). We will claim a *localised
implementation defect in the FlowMol3 adapter's restart prior*, verified
against upstream source, plus a monotone NFE trend reported as
directional-but-underpowered. See §4.

---

## 2. Recommended fix, in detail

### 2.1 Root cause restated

Upstream FlowMol3 initialises the categorical channels at t=0 entirely at
the mask token (α_t(0)=0 ⇒ mask probability 1). The CTMC step then
*unmasks* tokens progressively:

```text
# ctmc_vector_field.py:414-461 (Campbell step, paraphrased)
will_unmask = (xt == mask_index) & (rand < unmask_p)
xt[will_unmask] = x1[will_unmask]
if not last_step: xt[will_mask] = mask_index      # self-correction
```

Our adapter's prior (`flowmol3_v2_adapter.py:457-495`) instead draws
`a0 ~ Uniform{0..10}` and `e0 ≈ no-bond with 5% sprinkle` — every token
already concrete, none at `mask_index`. Consequences:

* On a fresh prior, `will_unmask` is empty → the CTMC contributes nothing
  and the chain silently degrades to the linear-interpolant fallback.
* Campbell self-correction (the re-mask branch) has nothing to re-anchor
  on, so early mistakes are never repaired.
* At a restart boundary, `_channel_aware_blend` (lines 1057-1232) replaces
  ~50% of round-r's converged labels with *independent uniform* labels
  (`m_* = 0.5` by default). At NFE=10 round-r was already high-variance
  (η=8.0, dt=0.1 ⇒ mask_prob≈0.8, Agent C §1.4), so the blend destroys
  more signal than it explores.

### 2.2 Code sketch

```python
# adaptive_reflow/adapters/flowmol3_v2_adapter.py

# --- new module constants (near FLOWMOL3ADAPTER_N_ATOM_TYPES) -----------
#: Mask-token index per categorical channel. Upstream appends the mask
#: token as the LAST index of each vocabulary (ctmc_vector_field.py:121-134).
#: The adapter's existing widths are FLOWMOL3ADAPTER_N_ATOM_TYPES = 10
#: (:141) and FLOWMOL3ADAPTER_N_BOND_TYPES = 5 (:137) — note these do NOT
#: match Agent C's reading of upstream (11 atom types, 4 bond types + mask),
#: so Step 1 MUST pin these indices against the loaded ckpt's logit widths
#: rather than against a literal. See risk R1.
FLOWMOL3ADAPTER_A_MASK_INDEX: int = ...  # pin from ckpt logit width
FLOWMOL3ADAPTER_E_MASK_INDEX: int = ...  # pin from ckpt logit width
# No charge mask constant: the adapter treats `c` as continuous (:469).
# Resolve against Agent C §1.1 before touching it — see risk R2.


def _sample_a0(seed: int, n_atoms: int, *, masked: bool = True) -> ArrayF64:
    """Atom-type prior at t=0.

    ``masked=True`` (CTMC-correct, the new default) returns the mask
    token everywhere, matching upstream ``alpha_t(0) == 0``. The
    ``masked=False`` branch preserves the historical uniform-Categorical
    draw for the ``ctmc_enabled=False`` ablation path and for the pinned
    D.4 regression vectors.
    """
    if masked:
        return np.full(int(n_atoms), FLOWMOL3ADAPTER_A_MASK_INDEX, dtype=np.int64)
    rng = np.random.default_rng(int(seed) + 2)
    return rng.integers(
        0, int(FLOWMOL3ADAPTER_N_ATOM_TYPES), size=int(n_atoms), dtype=np.int64
    )


def _sample_e0(seed: int, n_atoms: int, *, masked: bool = True) -> ArrayF64:
    """Bond-type prior at t=0; mask token everywhere when ``masked``."""
    if masked:
        return np.full(
            (int(n_atoms), int(n_atoms)),
            FLOWMOL3ADAPTER_E_MASK_INDEX,
            dtype=np.int64,
        )
    ...  # existing 5%-sprinkle body unchanged


# --- blend: never fabricate a label out of a mask ----------------------
def _channel_aware_blend(prior, fresh, memory_fraction, *, rng):
    ...
    # Discrete channels: a categorical "keep" draw as before, BUT if the
    # fresh draw is masked, keeping the mask is the correct outcome —
    # the CTMC will unmask it with the right rate. Never overwrite a
    # CONCRETE prior label with a mask when the prior is more converged
    # than the fresh draw; that is what destroyed round-r signal.
    keep_a = rng.random(prior_a.shape) < memory_fraction[ChannelName("atom_type")]
    out_a = np.where(keep_a | _is_mask(fresh_a, A_MASK), prior_a, fresh_a)
```

### 2.3 Why this is expected to help each stratum

| stratum | current mean | mechanism P0 removes | expected direction |
|---|---|---|---|
| NFE=10 | −15.94% | 50% of labels replaced by uniform noise on an already high-variance endpoint | largest gain; target ≥ 0% (framework ≥ baseline) |
| NFE=50 | −8.53% | same, weaker; plus dead CTMC on fresh prior | moderate gain |
| NFE=200 | +1.13% | dead CTMC on fresh prior (seed-44 failure mode) | small gain, mainly on seed 44 |

**Falsifiable prediction to record before running:** if P0 is the right
fix, seed 44 stops being uniformly-regression. If seed 44 still regresses
3/3 after P0, the cause is elsewhere (see B4) and we must say so.

---

## 3. Implementation plan (Wave 58)

Five steps. Steps 1-2 are the fix; 3-5 are verification and honesty.

**Step 1 — Mask tokens in the prior.**
* `adaptive_reflow/adapters/flowmol3_v2_adapter.py:457` (`_sample_a0`),
  `:475` (`_sample_e0`), `:469` (`_sample_c0` — charge channel is
  continuous upstream, so *verify* before touching it; Agent C §1.1 lists
  `c` as categorical in the CTMC set but the adapter treats it as
  continuous. Resolve this discrepancy first and record the answer.)
* `:498` `_sample_native_state` — thread a `masked: bool = True` kwarg
  through; add the three mask-index constants near the existing vocab
  constants.
* Keep the unmasked path reachable (`masked=False`) so the
  `ctmc_enabled=False` ablation and the pinned D.4 regression vectors
  still reproduce byte-for-byte.

**Step 2 — Mask-aware blend.**
* `:1057-1232` `_channel_aware_blend` — add `_is_mask` guards per
  categorical channel per the §2.2 sketch.
* `:2008-2148` `apply_restart_distribution` — no signature change; assert
  post-blend that no channel contains an *out-of-vocabulary* index, and
  emit audit code `flowmol3adapter_restart_masked_prior_v1` in the
  returned bundle's provenance so downstream evals can tell the two
  regimes apart.

**Step 3 — Tests.**
* `tests/test_adapters/test_flowmol3_v2_adapter.py` (existing file):
  * `test_sample_a0_masked_default` / `test_sample_e0_masked_default` —
    every entry equals the mask index.
  * `test_sample_native_state_unmasked_path_is_byte_stable` — the
    `masked=False` branch reproduces the pre-Wave-58 arrays exactly.
  * `test_channel_aware_blend_never_overwrites_concrete_with_mask`.
  * `test_apply_restart_distribution_emits_masked_prior_audit_code`.
* `tests/test_adapters/test_flowmol3_glue.py` — one end-to-end restart
  round asserting the CTMC actually unmasks (i.e. the post-round state
  contains no mask tokens at t=1).
* Confirm the D.4 pinned vectors for flowmol3_v2 either still pass or are
  re-pinned with an explicit changelog line — never silently refreshed.

**Step 4 — Re-run the sweep with more power.**
* Re-run the 9-cell grid → `verification_outputs/flowmol3_real_metric_v4_q4_2026.json`.
* **Extend to 6 seeds (42-47) × 3 NFE = 18 cells.** Agent B §6.3 is
  explicit that n=3 per stratum cannot reach α=0.05; 6 seeds brings the
  NFE=10 stratum to a binomial test that *can* (7/10 ≈ 0.05). Do not
  re-report a 9-cell result as evidence either way.
* Report per-stratum mean, the sign test, and the Wilcoxon W+, as Agent B
  did — same tests, so v3 and v4 are directly comparable.

**Step 5 — Docs, paper, commit.**
* `docs/theory/DEVIATIONS.md` — additive entry: the pre-Wave-58 prior was
  a deviation from upstream; state it plainly with the upstream line refs.
* `docs/CONSOLIDATED_RESULTS.md` §15/§16 — append v4 rows; keep v3 rows.
* `paper-draft.md` §7.5 — rewrite per §4 below.
* Commit; do not push until Step 4's numbers are in the doc.

---

## 4. Paper framing for §7.5 (honest version)

The temptation is to write "we identified an NFE threshold below which
re-inference does not help". That would be three claims we cannot
support: a threshold estimated from n=3, a monotonicity we cannot
distinguish from noise at α=0.05, and an implicit suggestion that the
regression was a property of the *method* rather than of *our adapter*.

Recommended framing, in this order:

1. **Lead with the defect, not the trend.** "Our FlowMol3 adapter's
   restart prior initialised the categorical channels to concrete labels,
   whereas upstream FlowMol3 initialises them to the CTMC mask token
   (`ctmc_vector_field.py:121-134`). The framework's restart boundary
   therefore fed the CTMC a prior it is not designed to consume." This is
   verifiable from source and needs no statistics.

2. **Report the sweep as directional and underpowered.** "Across 3 seeds
   × 3 NFE budgets, the signed delta was monotone in NFE
   (−15.9% / −8.5% / +1.1%), with all three NFE=10 cells regressing.
   Neither a sign test (p = 0.25 overall, p = 0.125 within NFE=10) nor a
   Wilcoxon signed-rank test (W+ = 10, n = 9) rejects the null at
   α = 0.05. We therefore report the direction, not a significant effect."

3. **Report the seed-44 anomaly rather than averaging it away.** One of
   three seeds regressed at every budget, with the *lowest* variance of
   any seed. Averaging over seeds hides this; say it out loud, and say
   whether the Wave-58 fix removed it.

4. **State explicitly what we did not do.** We did not adopt an NFE gate.
   Cite Agent A's survey: A-FloPS, ASFM, Instance-Aware Discretization and
   Adaptive Sparse Sampling all *target and win in* the low-NFE regime, so
   "disable refinement below NFE 20" would have been a claim against the
   2026 consensus, made on n=3. If we later ship the gate (B1), frame it
   as a declared **operating regime**, cross-referenced to
   `docs/theory/operating-regime.md`, never as evidence that re-inference
   is impossible at low NFE.

5. **Sizing language.** Prefer "3 of 9 cells improved" over "framework
   improves"; prefer "consistent with" over "shows"; give n beside every
   percentage.

A one-line abstract-safe version: *"We trace a FlowMol3-specific
regression to a mask-token mismatch between our restart prior and the
upstream CTMC initialisation, fix it, and report an NFE-monotone but
statistically underpowered trend (n=3 per budget) rather than a
significance claim."*

---

## 5. Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Mask indices are not the last vocab slot upstream, and the adapter's own widths (`N_ATOM_TYPES = 10` at `:141`, `N_BOND_TYPES = 5` at `:137`) disagree with Agent C's reading of upstream (11 atom types; 4 bond types + 1 mask) | **High** | Wrong labels everywhere, silent | Step 1 must read the upstream vocab construction and pin each index against the loaded ckpt's logit width, asserted in a test — never against a literal |
| R2 | `c` (charge) channel classification is contradictory between Agent C §1.1 (categorical/CTMC) and the adapter (continuous) | Medium | Fix applied to the wrong channel | Resolve before Step 1; record the answer in DEVIATIONS.md |
| R3 | Pinned D.4 regression vectors for flowmol3_v2 break | High (by design) | Test-suite red; looks like a regression | Keep `masked=False` path byte-stable; re-pin with an explicit changelog entry, never a silent refresh |
| R4 | P0 lands but NFE=10 still regresses | Medium | Primary fix invalidated | Falsifiable prediction recorded in §2.3; fall through to B1/B2 and *report the failed prediction* |
| R5 | v4 sweep at 18 cells is still not significant | Medium-high | Cannot claim anything | Framing in §4 already survives a null result; §7.5 does not depend on significance |
| R6 | Masked prior interacts badly with the partial-fidelity head (which is not a real FlowMol3, Agent C §3 Option 3 cons) | Medium | Fix helps only on the real-ckpt path | Run Step 4 with `--force-mode real`; report partial-fidelity separately |
| R7 | Scope creep into soft-restart (B3) during Wave 58 | Medium | Wave 58 doesn't land | B3 is explicitly Wave 59+; Wave 58 ships Steps 1-5 only |

---

## 6. Alternative paths, ranked

Take these in order only if the one above it fails its recorded prediction.

**B1 — NFE-adaptive restart gate** (Agent A §4, Agent C Option 1).
Guard in `apply_restart_distribution`: if effective NFE < threshold,
return `state` unchanged and emit
`flowmol3adapter_restart_skipped_low_nfe`. ~15 LOC + 1 test.
*Ship only if P0 leaves the NFE=10 stratum negative.* Make the threshold a
per-adapter constructor kwarg with a CLI override, never a global
constant, and calibrate it on the 18-cell v4 grid rather than on n=3.
Cost: it flattens 3 cells to "≡ baseline" and abandons the low-NFE regime
the 2026 literature is actively winning.

**B2 — Per-channel low-alpha restart policy** (Agent C Option 2).
`FlowMol3LowAlphaRestartPolicy` with `beta_by_channel ≈ 0.9`
(⇒ `m_* ≈ 0.1`), so restarts perturb rather than half-replace. ~30 LOC +
an alpha sweep. Strictly more expressive than B1 (B1 is the `m=0` corner)
and keeps re-inference alive at low NFE. Prefer **B2 over B1** if both
are on the table; B1's only advantage is that it is easier to explain.
Consider making β a function of NFE — which is the honest version of
"NFE-adaptive": *scale* the restart, don't switch it off.

**B3 — Soft restart from the model's own belief** (Agent C Option 3).
Replace the independent fresh draw with a short back-then-forward walk
from the round-r endpoint, so the restart state lies near the data
manifold. ~80 LOC + a `soft_restart()` Protocol method. This is the
principled long-term answer and generalises to every discrete-channel
adapter (FlowMol3, Kanzi, LineageFlow). **Wave 59+, not Wave 58.**
Caveat from Agent C: on the partial-fidelity head the "model's belief" is
a readout of the same head, so pilot it on the real ckpt only.

**B4 — Seed-conditioned investigation.** If seed 44 still regresses 3/3
after P0, the cause is not the prior. Next probes, in order: (a) is the
first noise state deterministic given the seed, and does 44 land on an
unusual `n_atoms` draw from `DEFAULT_N_ATOMS_PRIOR` (`:440`)? (b) is the
entropy-reduction metric axis degenerate for that molecule size? (c) does
the restart_seed derivation `SHA256(policy_hash || next_round)[:8]`
collide unfavourably for that trajectory?

**B5 — Power before mechanism.** If P0..B2 all produce ambiguous v4
numbers, stop optimising and spend the compute on seeds instead: 10 seeds
× 3 NFE. A clean null at n=30 is a publishable, honest §7.5; three
mechanism fixes evaluated at n=3 each are not.

**B6 — Adaptive substepping** (Agent A §3.3). The 2026 frontier (ASFM,
Adaptive Sparse Sampling). Out of scope for this gap, recorded as a
future direction so §7.5 can name it as the principled alternative to a
gate.

---

## 7. Cross-references

* `adaptive_reflow/adapters/flowmol3_v2_adapter.py` — `:440` n_atoms prior,
  `:447` `_sample_x0`, `:457` `_sample_a0`, `:469` `_sample_c0`,
  `:475` `_sample_e0`, `:498` `_sample_native_state`,
  `:1057-1232` `_channel_aware_blend`, `:2008-2148`
  `apply_restart_distribution`, `:2184+` `solve_ode`
* `data/FlowMol3/repo/flowmol/models/ctmc_vector_field.py` — `:121-134`
  masked init, `:414-461` `campbell_step`, `:446` `will_unmask` filter
* `verification_outputs/flowmol3_real_metric_v3_q4_2026.json` — the 9 cells
* `docs/theory/operating-regime.md`, `docs/theory/DEVIATIONS.md`
* `todo/algo-improvement-FlowMol3V2-restart-fix.md` — existing plan doc to
  update with the Wave 58 steps
* `paper-draft.md` §7.5, §7.6

---

## 8. Files changed

`docs/audit/wave57-synthesis-design.md` (this file, NEW). No code changed.
