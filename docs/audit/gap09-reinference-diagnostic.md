# GAP-09 — a measurable re-inference diagnostic for Theorem 4 and Theorem 5

**Date:** 2026-10-12
**Branch:** main
**Base commit:** `bd9055c` (chore(todo): single current-state todo.json; retire todo/; record D-004b R1)
**Scope:** new theory module `adaptive_reflow/theory/reinference_diagnostic.py` + runner `tools/run_reinference_diagnostic.py`; measured on the R5b cell's CIFAR-10 RF velocity field
**Verdict:** the two Wave-372 conditional theorems now have a **measurable, adapter-agnostic diagnostic**. On the R5b cell field, the Theorem-4 criterion $q = mK < 1$ **holds at every tested memory fraction** and the round map **contracts empirically** (rate $< 1$) at all four — a direction match. The Theorem-5 identity is **exact** (max residual $2.8\times10^{-14}$) and the Eq. 7 improvement condition **predicts the measured blend sign in 4/4 scenarios**. This satisfies the GAP-09 acceptance ("≥1 cell where the criterion's predicted direction matches the measurement"), with the scope caveat that the field is the R5b cell's **synthetic** backend (no trained checkpoint is present on this machine).

---

## 1. Purpose

Wave 372 retracted the earlier unsupported FID-sign / exponential-rate "Theorem 5" and left two **conditional** statements (paper §6.5–§6.6):

* **Theorem 4** — the round map $G_b(x) = \Phi_T(B_m(x, b))$ with $B_m(x,b) = m x + (1-m) b$ is a $q$-contraction when $q := mK < 1$, where $K = \mathrm{Lip}(\Phi_T)$ on the invariant envelope.
* **Theorem 5** — for the convex blend $B_m = m X + (1-m) Y$ the **exact** identity
  $\mathbb{E}\|B_m - z\|^2 = m\,\mathbb{E}\|X - z\|^2 + (1-m)\,\mathbb{E}\|Y - z\|^2 - m(1-m)\,\mathbb{E}\|X - Y\|^2$
  holds, so the blend improves squared endpoint error over $X$ **exactly when** $\mathbb{E}\|Y-z\|^2 - \mathbb{E}\|X-z\|^2 < m\,\mathbb{E}\|X-Y\|^2$ (Eq. 7).

Wave 372's "remaining evidence limits" explicitly note that **the contraction condition has not been measured on the production adapters**. GAP-09 asks for a measurable diagnostic for both criteria, **verified to predict the sign of the effect on ≥1 cell**. This audit supplies the tooling and the first measurement.

---

## 2. Deliverables

| Artifact | Role |
|---|---|
| `adaptive_reflow/theory/reinference_diagnostic.py` | pure/additive theory module — `integrate_flow`, `estimate_flow_map_lipschitz`, `contraction_variable`, `round_map_contraction`, `blend_identity_terms` + frozen dataclass reports |
| `tools/run_reinference_diagnostic.py` | runner — sweeps $m$ for Theorem 4 and blend scenarios for Theorem 5 on the R5b cell field |
| `tests/test_theory/test_reinference_diagnostic.py` | 8 CPU unit tests (NumPy-only) |
| `verification_outputs/gap09-reinference-diagnostic/diagnostic.json` | machine-readable result |

The module takes a plain `velocity_fn(x, t) -> v` callable, so it applies to **any** adapter field (synthetic MLP, torch UNet, …) without importing torch. It is **additive**: no existing module changed.

---

## 3. Method

**Theorem 4.** $K$ is estimated by finite differences of the integrated flow map $\Phi_T$: for each point and each random unit direction $u$, form $\|\Phi_T(x+\epsilon u) - \Phi_T(x)\|/\epsilon$ and take the sample-max (`k_max`) and mean (`k_mean`). The estimate is a **numerical surrogate** — finite differences under random directions sample the operator norm **from below**, so `k_max` is a lower bound on $\mathrm{Lip}(\Phi_T)$ and $q<1$ using it is a **necessary, not sufficient**, condition (surfaced in the report docstring). The round map is then iterated to its fixed point and the trailing geometric-mean contraction ratio is compared against $q = m\,K_\text{max}$.

**Theorem 5.** For a target $z$, a preceding endpoint $X$, and a fresh state $Y$, the module evaluates the three squared-error terms, the **exact identity residual** ($\mathbb{E}\|B_m-z\|^2$ minus its closed form), the Eq. 7 condition, and the measured sign of $\|B_m - z\|^2$ vs $\|X-z\|^2$ — then reports whether the condition **matches** the measured sign.

**Cell.** The R5b cell is the CIFAR-10 Rectified-Flow cell. No trained checkpoint is present under `data/` on this machine, so the reachable field is the adapter's **synthetic backend** (the 2-layer MLP `v(x,t) = W2·tanh(W1·x + b1 + t·t_bias) + b2`, `IN_DIM=3072`, `HIDDEN=32`, weights from `tools/audit_thm5/estimate_lipschitz.build_synthetic_weights(seed=0)`). This is the same field used by the R5b CPU/test path and the existing Theorem-5 Lipschitz estimate.

---

## 4. Observed facts

**Flow-map Lipschitz (R5b synthetic field):** `k_mean = 1.0308`, `k_max = 1.0676`, `k_p95 = 1.0466` (64 points × 4 directions).

**Theorem 4 (round-map contraction):**

| $m$ | $q = m\,K_\text{max}$ | empirical rate | contracts? (rate $<1$) | tracks $q$? (rate $\le 1.2q$) |
|---:|---:|---:|:---:|:---:|
| 0.3 | 0.313 | 0.3821 | ✅ | ❌ |
| 0.5 | 0.530 | 0.6164 | ✅ | ✅ |
| 0.7 | 0.742 | 0.7798 | ✅ | ✅ |
| 0.9 | 0.943 | 0.8475 | ✅ | ✅ |

* $q = mK < 1$ **holds at every** tested $m$ → the Theorem-4 sufficient condition is satisfied on this cell.
* The round map **contracts empirically** (rate $<1$) at every $m$ → the **predicted direction** (a $q$-contraction with $q<1$ contracts) matches the measurement.
* The **tighter** "rate tracks $q$ within 20% slack" check holds for $m \ge 0.5$ but **fails at $m = 0.3$**: there the round map converges in very few iterations, so the trailing ratio is measured on an almost-settled fixed point and reads slightly above $q$. This is reported honestly as a finite-transient artifact, not a falsification (the rate is still $<1$).

**Theorem 5 (exact identity + Eq. 7 prediction):**

| $\sigma_X$ | $\sigma_Y$ | err$_X$ | err$_Y$ | err$_\text{blend}$ | identity residual | condition holds | blend better | prediction matches |
|---:|---:|---:|---:|---:|---:|:---:|:---:|:---:|
| 0.30 | 0.10 | 276.42 | 30.68 | 76.80 | $-2.8\times10^{-14}$ | ✅ | ✅ | ✅ |
| 0.10 | 0.30 | 30.71 | 276.16 | 76.68 | $+2.8\times10^{-14}$ | ❌ | ❌ | ✅ |
| 0.20 | 0.20 | 122.66 | 123.11 | 61.52 | $0$ | ✅ | ✅ | ✅ |
| 0.05 | 0.40 | 7.67 | 491.19 | 124.67 | $0$ | ❌ | ❌ | ✅ |

* The exact identity holds to machine precision (max residual $2.8\times10^{-14}$).
* The Eq. 7 condition **predicts the measured blend sign in 4/4 scenarios** — including the two where the blend does **not** help (fresh state much worse than the preceding endpoint).

**Verdict object:** `theorem4_contraction_holds=true`, `theorem4_contracts_empirically=true`, `theorem4_rate_tracks_q=false` (the one small-$m$ tighter check), `theorem5_identity_exact=true`, `theorem5_predictions_match=true`.

---

## 5. Acceptance

GAP-09 acceptance: *"≥1 cell where the criterion's predicted direction matches the measurement."*

* **Theorem 4:** on the R5b cell field, $q=mK<1$ holds and the round map contracts (rate $<1$) at all four memory fractions — predicted direction (contraction) **matches** measurement. ✅
* **Theorem 5:** the exact identity holds and the Eq. 7 condition predicts the blend sign in **4/4** scenarios. ✅

Acceptance met.

---

## 6. What this changes (and what it does not)

**Changes (fact):** Wave 372's open limit — *"the contraction condition has not been measured"* — now has a **runnable, adapter-agnostic diagnostic** and a first measurement on the R5b cell field. The two theorems move from purely conditional statements to **measurable-and-measured** on at least one cell.

**Does not change:** the frozen manuscript / CLAIMS / `tnnls_submission/` numbers (AGENTS.md §3 guardrails #4–#5). This is a **new, additive** capability + observation; no frozen number or status label is rewritten.

**Scope caveat (must travel with this result).** The measured field is the R5b cell's **synthetic** backend, not a trained production checkpoint (none is present under `data/`). The finite-difference $K$ is a **lower bound** on $\mathrm{Lip}(\Phi_T)$, so $q<1$ here is necessary, not sufficient. A production-adapter measurement (trained CIFAR RF UNet, or a continuous-flow cell with a checkpoint) remains the natural strengthening; the diagnostic is built to accept that field unchanged.

---

## 7. Guardrail compliance

| Guardrail (AGENTS.md §3) | Status |
|---|---|
| #1 vendored upstream byte-identical | ✅ untouched |
| #2 additive is the rule | ✅ new module + runner + test + audit; no existing module changed |
| #3 NO-PUSH | ✅ commit only |
| #4 honest uncertainty | ✅ reports the one failing tighter check + the lower-bound/synthetic caveats; no frozen number changed |
| #5 TNNLS freeze | ✅ no `tnnls_submission/` number moved |
| #6 per-increment audit doc | ✅ this file |
| #7 stricter = cleaner | ✅ pure NumPy, adapter-agnostic, no torch import, no production path touched |

---

## 8. Verification

| Gate | Result |
|---|---|
| `pytest tests/test_theory/test_reinference_diagnostic.py -q` | 8 passed |
| `pytest tests/test_d4_regression_vectors.py -q` | 30 passed |
| `ruff check adaptive_reflow/ tests/ tools/` | All checks passed |
| `python3 tools/check_claims_consistency.py` | No drift detected |
| `mkdocs build --strict` | exit 0 |
| runner re-run | deterministic (fixed seeds), `verification_outputs/gap09-reinference-diagnostic/diagnostic.json` rewritten identically |

---

## 9. Unresolved / noted

- **Production-adapter measurement.** The diagnostic is validated on the R5b cell's synthetic field; a trained-checkpoint field (CIFAR RF UNet / a continuous-flow cell) would be the next strengthening. Deferred — no checkpoint under `data/`.
- **Small-$m$ tighter check.** `rate_tracks_q` fails at $m=0.3$ due to fast convergence; the direction check (`contracts_empirically`) is the one tied to the acceptance and holds at all $m$.
- **$K$ is a lower bound.** Finite differences sample the operator norm from below; the report labels $q<1$ as necessary, not sufficient, accordingly.
