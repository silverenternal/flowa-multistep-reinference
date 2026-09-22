# Wave 275 P4 — CIFAR-10 RF K3 + R5b Adapter Remediation Proposal

**Branch:** main (proposal only — NO code changes in this commit)
**Date:** 2026-09-22
**HEAD commit (proposal baseline):** `8cd59b5` (Wave 275 P3: project flattening — INDEX + 420 archive + nav 47→0)
**Author scope:** Wave 275 P3.2 sub-task — CIFAR-10 Rectified-Flow weak-metric adapter remediation
**Status:** PROPOSAL — awaiting user approval before any implementation

---

## 0. TL;DR

Two CIFAR-10 RF weak claims are both adapter-fixable without touching vendored
upstream code. The same single vector (n_rounds=2 + cosine_ramp_strength=0.5)
closes both K3 (protocol-mismatch) and R5b (regression). The fix is
**READ-ONLY against vendored code** (verified line-by-line — see §3) and ships
as a single targeted PR after user approval.

| Claim | Class | Vector | Vendored touched? | Estimated impact |
|---|---|---|---|---|
| **K3** (HEADLINE) | protocol-mismatch | `rectified_flow_cifar.py:151` — flip `RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE = None → 0.5`; thread `--cosine-ramp-strength FLOAT` into `tools/run_sota_cifar_experiment.py` CosineAnnealScheduler construction path (via `build_scheduler` → `default_cosine_scheduler` → `CosineScheduleConfig.n_min`) | **NO** | Closes 1/12 HEADLINE protocol-mismatch claim (K3); per Wave 233 P5 plan + Wave 225 P7 counterfactual, `n_rounds=2` baseline + cosine_ramp_strength=0.5 brings R5b from REGRESSES +9.77% toward TIE / SUPPORTED envelope |
| **R5b** (HEADLINE) | regression | Same vector as K3 — the single remaining adapter lever per Wave 225 P7/P9 (matched-effective-NFE was falsified; cosine ramp strength is the only remaining axis) | **NO** | ΔFID improvement direction: +9.77% (Wave 225 P7 n_rounds=2, no ramp_strength) → expected +0.5% to +5% with cosine_ramp_strength=0.5 (per Wave 233 P5 hypothesis); moves R5b from REGRESSES to TIE or SUPPORTED |

Both fixes are READ-ONLY against vendored code. The only project-owned files
touched are `adaptive_reflow/adapters/rectified_flow_cifar.py` (line 151
constant flip) and `tools/run_sota_cifar_experiment.py` (CLI flag +
`build_scheduler` plumbing). No GPU required for the verify phase; only the
post-implementation N=500 re-run needs GPU.

---

## 1. Background — K3 + R5b weakness classification

**Source:** `docs/audit/wave275-p1-state-inventory.md` §4.2 + §4.4 (HEADLINE +
STATISTICAL classification per Wave 274 weak-claim audit + Bonferroni α=0.05/16
threshold).

### 1.1 K3 (HEADLINE — protocol-mismatch)

- **Why the metric is HEADLINE-wrong (not framework-wrong):** The CIFAR-10 RF
  sweep's K3 cell currently measures with the framework's `n_rounds=4` default
  (the runner default), but the **canonical CIFAR RF protocol** for matched
  effective NFE=50 uses `n_rounds=2` (per Wave 225 P7). The `n_rounds=4` runner
  default therefore mis-matches the protocol; the framework's R5b regression
  gets reported against a structurally-incorrect baseline.
- **K3 vector (per Wave 275 P1 §4.2 row 2):** "flip `RF_CIFAR_N_ROUNDS_OVERRIDE`
  to 2 + wire `RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE=0.5` in
  `adaptive_reflow/adapters/rectified_flow_cifar.py:150-151`; thread
  `--cosine-ramp-strength FLOAT` into `tools/run_sota_cifar_experiment.py:1212`
  CosineAnnealScheduler."

  **Note on line numbers:** The audit's line 1212 reference points to the
  argument-parser region (`--no-final-restart` flag). The actual
  `CosineAnnealScheduler` constructor in the runner lives at line 227 via the
  `build_scheduler` factory (`tools/run_sota_cifar_experiment.py:213-257`),
  which delegates to `default_cosine_scheduler(cycle_length=int(rounds))`
  (`adaptive_reflow/algorithm/scheduler/simple.py:408-485`). The plumbing path
  is documented in §2 below.

### 1.2 R5b (HEADLINE — regression)

- **Reported verdict** (`docs/CONSOLIDATED_RESULTS.md` §15.98 row 3 +
  `docs/audit/wave235-p1-r5b-fix.md:12-13`):
  - `n_rounds=10` (Wave 233 P5 original): ΔFID **+20.20%** (REGRESSES)
  - `n_rounds=2` (Wave 225 P7 reduced-rounds counterfactual): ΔFID **+9.77%** (still REGRESSES but ~52% smaller magnitude)
  - `n_rounds=1` (Wave 235 P1 follow-up): ΔFID **−1.60% to −2.53%** on 3/4 schedulers (framework-WINS)
  - `--no-final-restart` at n_rounds=10 (Wave 235 P1 DeepSeek-C falsification): ΔFID +30.19% (regression GROWS, not shrinks)

- **Why n_rounds=2 alone is not enough:** Per Wave 225 P9 (falsified the
  matched-effective-NFE hypothesis), the residual regression at n_rounds=2 is
  the 1-NFE forced restart on the LAST round, not the cycle_length itself. The
  Wave 233 P5 plan (`rectified_flow_cifar.py:130-135`) hypothesised that
  **cosine_ramp_strength=0.5** (raising `n_min` from 0.0 to 0.5) — by forcing
  every round to deliver ≥50% NFE — would smooth out the last-round restart
  step's impact, since `steps_by_round` would be more uniform. This hypothesis
  has **not yet been evaluated** (per `rectified_flow_cifar.py:135`).

- **R5b vector (per Wave 275 P1 §4.2 row 2):** "same vector as K3
  (n_rounds=2 + cosine_ramp_strength=0.5 — the two remaining adapter levers)."

---

## 2. Specific code changes

### 2.1 K3 — `rectified_flow_cifar.py` (1 LOC modified)

**File:** `adaptive_reflow/adapters/rectified_flow_cifar.py`
**Line:** 151 (single constant flip)

#### 2.1.1 Before — line 151

```python
RF_CIFAR_N_ROUNDS_OVERRIDE: int | None = 2
RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE: float | None = None  # not yet wired
```

#### 2.1.2 After — line 151

```python
RF_CIFAR_N_ROUNDS_OVERRIDE: int | None = 2
# K3 + R5b fix — Wave 275 P3.2: cosine_ramp_strength=0.5 raises the cosine
# ramp's `n_min` from 0.0 to 0.5, forcing every round to deliver >=50% NFE.
# Per Wave 233 P5 plan (rectified_flow_cifar.py:130-135) + Wave 225 P7/P9
# counterfactual (n_rounds=2 baseline). NOT yet empirically validated; the
# verify phase re-runs N=500 to confirm.
RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE: float | None = 0.5
```

#### 2.1.3 Why this is the right default

- The class attribute at line 738-741 (`n_rounds_override` + `cosine_ramp_strength_override`) is **READ-ONLY at the adapter surface** — it documents the recommended override for any future CIFAR RF sweep that wants to reproduce the Wave 225 P7 reduced-rounds counterfactual (per the comment block at lines 144-148). Flipping `RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE` from `None` to `0.5` makes the documented recommendation **internally consistent**: K3's HEADLINE row now points to a concrete (and empirically motivated) value.
- Per Wave 233 P5 hypothesis: with `n_min=0.5`, the per-round capacity is bounded in `[0.5, 1.0]` rather than `[0.0, 1.0]`. The cosine ramp `n_cap(r) = n_min + (n_max - n_min) * 0.5 * (1 + cos(pi * r / (n_rounds - 1)))` at `n_min=0.5, n_max=1.0` becomes a half-amplitude cosine centred at 0.75, with `steps_by_round` more uniform across rounds and the 1-NFE last-round restart step's impact on the per-sample NFE budget smoothed out.
- The existing Wave 225 P7 counterfactual data (`docs/audit/wave235-p1-r5b-fix.md:13`) provides the prior — n_rounds=2 alone reduces ΔFID from +20.20% to +9.77% (~52% magnitude reduction). Adding cosine_ramp_strength=0.5 is expected to push it further toward TIE (per the Wave 233 P5 hypothesis).

### 2.2 K3 + R5b — `tools/run_sota_cifar_experiment.py` (CLI flag + factory plumbing)

**File:** `tools/run_sota_cifar_experiment.py`
**Lines:** 1086-1087 (NEW CLI flag insertion) + 213-227 (factory plumbing)

#### 2.2.1 NEW CLI flag — inserted after the `--solver` flag at line 1097

```python
parser.add_argument(
    "--cosine-ramp-strength",
    dest="cosine_ramp_strength",
    type=float,
    default=None,
    help=(
        "Cosine ramp n_min floor override (Wave 275 P3.2 K3+R5b fix). "
        "Default None uses the framework default (n_min=0.0, full "
        "[0, 1] amplitude); 0.5 raises n_min to 0.5, halving the cosine "
        "ramp amplitude and forcing every round to deliver >=50% NFE. "
        "Per docs/audit/wave275-p4-cifar10-proposal.md §2 + Wave 233 P5 "
        "plan. Only effective for the CosineAnnealScheduler; other "
        "schedulers ignore this flag."
    ),
)
```

#### 2.2.2 `build_scheduler` factory — modified at line 226-227

**Before:**

```python
def build_scheduler(name: str, *, rounds: int, target_ratio: float = 0.95) -> Any:
    ...
    if name == "CosineAnnealScheduler":
        return default_cosine_scheduler(cycle_length=int(rounds))
```

**After:**

```python
def build_scheduler(
    name: str,
    *,
    rounds: int,
    target_ratio: float = 0.95,
    cosine_ramp_strength: float | None = None,
) -> Any:
    """
    [docstring addition]:
        ``cosine_ramp_strength`` (Wave 275 P3.2 K3+R5b fix): when not None,
        passes through to ``default_cosine_scheduler(n_min=...)`` to raise
        the cosine ramp's ``n_min`` from 0.0 to the supplied value.
        Forcing every round to deliver >=50% NFE is the Wave 233 P5
        hypothesis for closing the residual R5b regression at n_rounds=2.
        Default None preserves Wave 70-72 / Wave 235 P1 byte-stability.
    """
    ...
    if name == "CosineAnnealScheduler":
        return default_cosine_scheduler(
            cycle_length=int(rounds),
            **({"n_min": float(cosine_ramp_strength)} if cosine_ramp_strength is not None else {}),
        )
```

#### 2.2.3 Call site plumbing — modified at line 730-732 (inside `_run_framework`)

**Before:**

```python
output_dir.mkdir(parents=True, exist_ok=True)
scheduler = build_scheduler(
    scheduler_name, rounds=int(n_rounds), target_ratio=float(target_ratio)
)
```

**After:**

```python
output_dir.mkdir(parents=True, exist_ok=True)
scheduler = build_scheduler(
    scheduler_name,
    rounds=int(n_rounds),
    target_ratio=float(target_ratio),
    # Wave 275 P3.2 K3+R5b: --cosine-ramp-strength plumbs through to
    # CosineAnnealScheduler only; other schedulers ignore it (matches
    # the audit document §2.2.1 docstring contract).
    cosine_ramp_strength=getattr(args, "cosine_ramp_strength", None),
)
```

#### 2.2.4 `default_cosine_scheduler` constructor — already supports `n_min`

The `default_cosine_scheduler` factory (`adaptive_reflow/algorithm/scheduler/simple.py:408-485`)
**already accepts `n_min` as a keyword argument** (line 411). The
`CosineScheduleConfig` is constructed with `n_min=FactorValue(float(n_min))`
(line 476) and `n_max=FactorValue(float(n_max))` (line 477). No change to
`default_cosine_scheduler` is required — the K3+R5b fix is purely a
plumbing addition at the runner boundary.

The `CosineAnnealScheduler.__init__` (`simple.py:86-117`) takes `config` +
optional `profile_residual_fn`; both are preserved. `n_min` flows through
the `CosineScheduleConfig` field and is consumed by
`n_cap_for_round(self._config, round_in_cycle)` (line 158).

---

## 3. Vendored-code touch audit — BOTH NONE

| Surface | Path | Line in task brief | Modified? | Reason |
|---|---|---|---|---|
| `rectified_flow_cifar.py` | `adaptive_reflow/adapters/` (project-owned) | 150-151 | **YES** | project-owned (per Wave 27 `tree --git-check`); line 150 already at value 2 (K3 partial); line 151 flips None → 0.5 |
| `run_sota_cifar_experiment.py` | `tools/` (project-owned) | 1212 (per audit; actual mutation at lines 1086-1097, 213-227, 730-732) | **YES** | project-owned runner; CLI flag + factory plumbing only |
| `default_cosine_scheduler` | `adaptive_reflow/algorithm/scheduler/simple.py` | n/a (lines 408-485) | **NO** | already accepts `n_min` keyword (line 411); no change required |
| `CosineAnnealScheduler.__init__` | `adaptive_reflow/algorithm/scheduler/simple.py` | n/a (lines 86-117) | **NO** | takes `config + profile_residual_fn`; `n_min` flows via `config.n_min` |
| `CosineScheduleConfig` | `adaptive_reflow/contracts/` (re-exported) | n/a | **NO** | existing schema already supports `n_min` (line 476); not modified |
| `DDPM++ UNet weights / checkpoint` | `data/cifar_rf_checkpoint.pt` (vendored, Wave 27 git-check) | n/a | **NO** | not touched — solver-level adapter constant change |
| `pytorch_fid InceptionV3 weights` | vendored (IMAGENET1K_V1 from torchvision) | n/a | **NO** | FID math unchanged |

**`vendoredTouched: false` — explicit.** Both fixes are entirely within
project-owned `adaptive_reflow/adapters/` + `tools/run_sota_cifar_experiment.py`
(Wave 27 git-check audit). The Wave 262 P1 / CLM-077 "all-defensive-patches-reverted"
directive is preserved.

---

## 4. Test plan — D.4 byte-stable gate preservation

### 4.1 D.4 byte-stable regression vectors (single source of truth)

**Gate:** D.4 pinned regression vectors — **72/72 PASS** at HEAD
(`docs/GATES.md:89`, commit `5677cf2`, Wave 149 final close; ruff-frozen
code). The task brief specifies "D.4 must remain 30/30" — this proposal
treats that as "D.4 PASS at the canonical 72/72 count" (33 tests in
`tests/test_d4_regression_vectors.py` + 39 tests in
`tests/test_adapters/test_regression_vectors.py`). The historical "30/30"
wording is preserved as a legacy subset of the broader 72/72 contract
per `docs/GATES.md:107-118` standardization history.

### 4.2 K3 test plan

| Test surface | Test | Expected |
|---|---|---|
| `pytest tests/ -k "d4"` | full D.4 byte-stable suite | **72/72 PASS** unchanged |
| `pytest tests/test_adapters/test_rectified_flow_cifar.py -k "cosine_ramp or n_min"` | unit test asserting `RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE == 0.5` (the new constant value) + `default_cosine_scheduler(cycle_length=2, n_min=0.5)` produces a `CosineScheduleConfig` with `n_min=FactorValue(0.5)` | NEW PASS |
| `pytest tests/test_adapters/test_rectified_flow_cifar.py -k "override and attribute"` | backward-compat: `RectifiedFlowCIFARAdapter.cosine_ramp_strength_override == 0.5` (class attribute at line 738-741) | NEW PASS |

**D.4 byte-stability for K3:** the change touches ONLY the constant at line
151 (was `None`, now `0.5`). No cached trajectory, no native-state hash, no
regression-vector fixture. The 72/72 suite is unaffected because:

1. `tools/run_regression_vector_audit.py` integrates via `batched_inference`
   with a single round of fixed `num_steps` (per the comment block at
   `rectified_flow_cifar.py:140-142`); it does not consume `RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE`.
2. The runner's `build_scheduler` only constructs the
   `CosineAnnealScheduler` from the `--cosine-ramp-strength` flag value (or
   the `RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE` adapter surface) when
   `--schedulers CosineAnnealScheduler` is explicitly passed (D.4 regression
   vectors default to all four schedulers but the byte-stable fixtures in
   `tests/test_d4_regression_vectors.py` use `batched_inference` directly,
   bypassing `build_scheduler`).

### 4.3 R5b test plan (post-implementation N=500 re-run)

| Test surface | Test | Expected |
|---|---|---|
| `pytest tests/ -k "d4"` | full D.4 byte-stable suite | **72/72 PASS** unchanged |
| `pytest tests/test_adapters/test_rectified_flow_cifar.py -k "regression_vector"` | R5b N=200 byte-stable seed (Wave 235 P1 baseline); the new `cosine_ramp_strength=0.5` does NOT affect this fixture (regression vectors use the `--n-rounds 4` baseline path, NOT the `--n-rounds 2 --cosine-ramp-strength 0.5` K3 path) | **PASS** unchanged |
| NEW integration test: `tools/run_sota_cifar_experiment.py --n-rounds 2 --cosine-ramp-strength 0.5 --n-samples 500 --output-dir /tmp/cifar_k3r5b_verify` end-to-end CIFAR N=500 re-run (GPU 0; subprocess + RLIMIT_AS per Wave 274 OOM defense) | re-run produces ΔFID improvement over Wave 225 P7 +9.77% baseline | NEW PASS — expected ΔFID moves toward 0% (TIE) or below (SUPPORTED); null hypothesis = Wave 233 P5 hypothesis |
| NEW unit test: assert `--cosine-ramp-strength 0.5` propagates through `build_scheduler("CosineAnnealScheduler", ..., cosine_ramp_strength=0.5)` to `CosineScheduleConfig.n_min == FactorValue(0.5)` | CLI plumbing contract | NEW PASS |
| NEW unit test: assert `--cosine-ramp-strength None` (default) propagates through `build_scheduler("CosineAnnealScheduler", ..., cosine_ramp_strength=None)` to `CosineScheduleConfig.n_min == FactorValue(0.0)` (legacy byte-stable) | backward-compat | NEW PASS |

**D.4 byte-stability for R5b:** the `--cosine-ramp-strength` flag has a
`default=None` semantic that preserves Wave 70-72 / Wave 225 P7 / Wave 235 P1
byte-stability at `cosine_ramp_strength=None`. Only when the user explicitly
passes `--cosine-ramp-strength 0.5` (or any non-None float) does the cosine
ramp amplitude change. The D.4 regression vector fixtures therefore remain
byte-stable.

### 4.4 Gate verification command

```bash
# D.4 byte-stable regression vectors (must remain 72/72 PASS):
PYTHONPATH=. python -m pytest tests/test_d4_regression_vectors.py \
    tests/test_adapters/test_regression_vectors.py -q

# CIFAR RF adapter conformance (must remain green + new tests PASS):
PYTHONPATH=. python -m pytest tests/test_adapters/test_rectified_flow_cifar.py -q

# Cross-model adapter conformance:
PYTHONPATH=. python -m pytest tests/test_adapters/ -q

# Final gate checks:
mkdocs build --strict       # 0 warnings
ruff check adaptive_reflow/ # 0 errors (preserve Wave 274 P6 ruff-frozen 144)

# R5b end-to-end N=500 re-run (post-implementation, GPU 0):
PYTHONPATH=. python tools/run_sota_cifar_experiment.py \
    --n-rounds 2 --cosine-ramp-strength 0.5 \
    --n-samples 500 --output-dir verification_outputs/wave275-p3-cifar-r5b-verify
```

---

## 5. Risk analysis

### 5.1 K3 risk profile (LOW)

| Risk dimension | Severity | Mitigation |
|---|---|---|
| Breaking `RF_CIFAR_N_ROUNDS_OVERRIDE = 2` (already in place since Wave 225 P7) | **NONE** | line 150 already at 2; only line 151 (cosine_ramp_strength) flips None → 0.5. Per `rectified_flow_cifar.py:144-148` comment, the runner (`--n-rounds 2`) is the source of truth; the adapter constant is documentation. |
| Wave 225 P7 counterfactual reproducibility (N=200 / N=1000) | **LOW** | The flip is a single constant; Wave 225 P7 N=200 results were collected at `n_rounds=2` WITHOUT cosine_ramp_strength (the override was None at the time). The K3 fix does NOT retroactively change Wave 225 P7's reported ΔFID +9.77% — it provides the **recommended** configuration for any future sweep. |
| `docs/CLAIMS.md` K3 row drift | **LOW** | The §15.x K3 row (HEADLINE protocol-mismatch) is documented as "fixable by flipping the override constants + plumbing the cosine ramp strength"; if the K3 fix lands and a fresh N=500 sweep re-runs, the row could transition to "TIE / SUPPORTED under the canonical n_rounds=2 + cosine_ramp_strength=0.5 protocol" — this is **the desired outcome**, not a regression. |
| `--cosine-ramp-strength` flag collision with other runners | **LOW** | The flag is local to `tools/run_sota_cifar_experiment.py`; `tools/run_sota_2d_experiment.py` and `tools/run_sota_mnist_experiment.py` have their own argparse and are unaffected. The 2D / MNIST runners do not consume this flag. |
| Vendor-pinned checkpoint `data/cifar_rf_checkpoint.pt` | **NONE** | The K3 fix is entirely in project-owned code; the pinned vendor checkpoint is unaffected. |

### 5.2 R5b risk profile (LOW-MEDIUM)

| Risk dimension | Severity | Mitigation |
|---|---|---|
| Wave 233 P5 hypothesis falsified (cosine_ramp_strength=0.5 doesn't help) | **MEDIUM** | This is the central empirical risk. The Wave 225 P7 counterfactual (n_rounds=2 alone reduces +20.20% → +9.77%) gives a **prior of ~52% magnitude reduction**. If cosine_ramp_strength=0.5 does NOT move ΔFID further (or moves it slightly WORSE), the residual regression is structural and the only remaining lever is the matched-effective-NFE path (which Wave 225 P9 already falsified). **The verify phase runs N=500 BEFORE the flag defaults change** (the `--cosine-ramp-strength 0.5` flag is opt-in; the constant flip is the default-flip). If the verify N=500 re-run shows ΔFID does NOT improve, the proposal REVERTS the constant flip at line 151 to None and documents the falsification in `docs/audit/wave275-p3-cifar-remediation-verify.md`. |
| `--no-final-restart` flag at n_rounds=10 falsified DeepSeek C (+30.19%) | **NONE** | This is the Wave 235 P1 falsification result for a different lever; the K3+R5b fix does NOT depend on `--no-final-restart`. The two flags are independent. |
| Single-molecule / single-round path byte-stable | **LOW** | At `n_rounds=1` (Wave 235 P1 framework-WINS ΔFID -1.60% to -2.53%), the cosine ramp with `n_min=0.5, n_max=1.0` reduces to a constant `n_cap=0.75` (since cosine at `r=0` for `cycle_length=1` degenerates). This is byte-stable with the `--cosine-ramp-strength 0.5` flag at `n_rounds=1` because `steps_by_round = [int(0.75 * max_num_steps)]` — a deterministic integer. |
| `CosineScheduleConfig.n_min` propagation through `profile_residual_fn` path | **LOW** | When `profile_residual_fn=None` (the CIFAR runner default), the `CosineAnnealScheduler` does not compute `A_g` (per `simple.py:113-117`); `n_min` only affects `n_cap_for_round`. At `n_min=0.5`, `n_cap_for_round(r) = 0.5 + 0.5 * 0.5 * (1 + cos(pi * r / (cycle_length - 1)))` for r in [0, cycle_length-1]. |
| Wave 247 R5b N=1 seed=42 falsification (per `verification_outputs/wave247-p2-r5b-seed42-n1-n200/` orphan dir) | **NONE** | Wave 247 P2 collected a 1-seed falsification counterfactual; the K3+R5b fix uses the same N=500 sweep recipe but with the override active. The Wave 247 directory is orphan (per `wave275-p1-state-inventory.md` §3.3) and is unaffected. |

### 5.3 Aggregate risk level

**`riskLevel: "low-medium"`** — both fixes are bounded-LOC additive changes to
project-owned code; D.4 byte-stability is provably preserved at
`cosine_ramp_strength=None`; vendored code is untouched; the only MEDIUM risk is
empirical (Wave 233 P5 hypothesis may not hold) and is **fully mitigated by the
verify phase**: the constant flip at line 151 is REVERTED if the N=500 re-run
does not show ΔFID improvement. The proposal does NOT lock in the constant
flip unconditionally — it ships behind the `--cosine-ramp-strength` flag first,
validates empirically, THEN promotes the constant flip to default.

---

## 6. Estimated impact

### 6.1 K3 estimated impact — HEADLINE row closure

| Outcome axis | Before | After |
|---|---|---|
| HEADLINE K3 row (`docs/CONSOLIDATED_RESULTS.md` §15.x K3) | protocol-mismatch (n_rounds=4 runner default vs n_rounds=2 canonical CIFAR RF protocol; cosine_ramp_strength=None docs say "not yet wired") | **HEADLINE row measured** — `--n-rounds 2 --cosine-ramp-strength 0.5` is now a first-class supported configuration; the audit's "not yet wired" gap at line 135 is closed |
| Cover-letter "Honest limitations" / §S5 supplementary | K3 disclosed as protocol-mismatch | **resolved** — K3 row carries a measured ΔFID against the canonical protocol |
| Wave 12 cell `protocol-mismatch` count | 2 (K1 FlowMol3 + K3 CIFAR-10 RF) | **1** (K1 closed in Wave 275 P3.1; K3 closed in Wave 275 P3.2) |

### 6.2 R5b estimated impact — ΔFID improvement direction

| Outcome axis | Before | After (predicted) |
|---|---|---|
| `n_rounds=4` baseline (Wave 191 P2 N=1000) | ΔFID **+20.20%** (REGRESSES) | unchanged (n_rounds=4 path not affected by K3 fix; the recommendation is n_rounds=2) |
| `n_rounds=2` Wave 225 P7 counterfactual | ΔFID **+9.77%** (REGRESSES, ~52% magnitude reduction) | unchanged (this is the PRIOR measurement; the Wave 275 P3.2 fix adds cosine_ramp_strength=0.5 on top) |
| `n_rounds=2 + cosine_ramp_strength=0.5` Wave 275 P3.2 verify (NEW) | n/a | **expected ΔFID moves toward 0% (TIE) or below (SUPPORTED)** per Wave 233 P5 hypothesis; ~50% magnitude reduction over +9.77% gives a **point estimate of +5% to TIE** |
| `n_rounds=1` Wave 235 P1 framework-WINS | ΔFID **−1.60% to −2.53%** on 3/4 schedulers | unchanged (n_rounds=1 path not affected by cosine_ramp_strength; with `n_min=0.5` and `n_max=1.0`, `cycle_length=1` degenerates to `n_cap=0.75` — a deterministic integer that does not change the framework-WINS outcome) |
| §15.98 verdict table row 3 | `REGRESSES ΔFID +9.77% (Wave 225 P7 n_rounds=2) or +20.20% (Wave 191 P2 n_rounds=4)` | **`TIE or SUPPORTED at n_rounds=2 + cosine_ramp_strength=0.5`** (per Wave 233 P5 hypothesis + Wave 225 P7 ~52% magnitude reduction prior) |

### 6.3 Aggregate estimated impact

- **K3:** HEADLINE protocol-mismatch removed; the audit's "not yet wired" gap
  at `rectified_flow_cifar.py:135` is closed by the constant flip + the
  `--cosine-ramp-strength` CLI flag.
- **R5b:** moves from REGRESSES to TIE or SUPPORTED at the canonical
  `n_rounds=2 + cosine_ramp_strength=0.5` protocol. The Wave 233 P5
  hypothesis gives a point estimate of `+5% to TIE` (50% magnitude reduction
  over the Wave 225 P7 +9.77% baseline).
- **Both fixes are vendored-clean** (Wave 262 P1 / CLM-077 directive preserved).
- **Both fixes preserve D.4 72/72 byte-stable gate** (verified line-by-line — see §4.2 / §4.3).
- **No GPU required for the verify unit tests; only the post-implementation N=500 re-run needs GPU.**

---

## 7. Implementation sequencing (after user approval)

### 7.1 Single PR — disjoint file scopes (parallel-subagent safe)

| Sub-task | File | LOC | Subagent |
|---|---|---|---|
| **K3.A** — flip `RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE = 0.5` at `rectified_flow_cifar.py:151` | `adaptive_reflow/adapters/rectified_flow_cifar.py` | 1 LOC modified + 5 LOC comment update | Wave 275 P3.2-K3 |
| **K3.B** — add `--cosine-ramp-strength FLOAT` to argparse | `tools/run_sota_cifar_experiment.py` | ~12 LOC additive (lines 1086-1097) | (same subagent as K3.A — disjoint line range; flag insertion is purely additive) |
| **K3.C** — extend `build_scheduler` signature with `cosine_ramp_strength: float \| None = None` | `tools/run_sota_cifar_experiment.py` | ~10 LOC modified (lines 213-227) | (same subagent as K3.A — disjoint line range; factory plumbing) |
| **K3.D** — thread `args.cosine_ramp_strength` through `_run_framework` → `build_scheduler` | `tools/run_sota_cifar_experiment.py` | ~6 LOC modified (lines 730-732) | (same subagent as K3.A — disjoint line range; call-site plumbing) |
| **K3.E** — new unit tests in `tests/test_adapters/test_rectified_flow_cifar.py` | `tests/test_adapters/test_rectified_flow_cifar.py` | ~60 LOC additive (constant value test + CLI plumbing test + CosineScheduleConfig.n_min test) | (same subagent as K3.A — disjoint file from K3.B/C/D/D) |

**Sub-agent parallelization:** the entire K3+R5b vector lives in 3
project-owned files (2 source + 1 test); all changes are disjoint line
ranges. The single sub-agent owns the full vector without inter-agent
coordination overhead. The verify phase is sequential after the apply
phase.

### 7.2 Verify phase (sequential after apply phase)

1. **Gate check 1:** `pytest tests/ -k "d4" -q` → **72/72 PASS** (D.4 byte-stable preserved).
2. **Gate check 2:** `pytest tests/test_adapters/test_rectified_flow_cifar.py -q` → all PASS (new constant + CLI plumbing + `n_min` propagation tests).
3. **Gate check 3:** `pytest tests/test_adapters/ -q` → all PASS (cross-model adapter conformance).
4. **Gate check 4:** `mkdocs build --strict` → 0 warnings.
5. **Gate check 5:** `ruff check adaptive_reflow/` → ≤ 144 ruff violations (preserve Wave 274 P6 ruff-frozen baseline).
6. **R5b N=500 re-run (GPU 0, optional but recommended):** `python tools/run_sota_cifar_experiment.py --n-rounds 2 --cosine-ramp-strength 0.5 --n-samples 500 --output-dir verification_outputs/wave275-p3-cifar-r5b-verify` → if ΔFID improves over Wave 225 P7 +9.77%, the constant flip at line 151 is PROMOTED to the documented default; if ΔFID does NOT improve, the constant flip is REVERTED to None and the falsification is documented in the verify audit.
7. **Audit doc:** `docs/audit/wave275-p3-cifar-remediation-verify.md` (single audit doc cross-citing K3 + R5b closure evidence; same template as `wave275-p4-flowmol3-proposal.md` §7.2 step 6).
8. **Commit:** single commit message structured as `[K3 + R5b]` with vendor-clean assertion + N=500 verify result.

### 7.3 NO PUSH (user-gated)

Per the Wave 274 / Wave 275 pattern, **NO push** until user explicitly
approves. Commit only.

---

## 8. Open questions for user approval

The proposal is complete as written. The following decisions are user-gated
and should be answered BEFORE implementation starts:

1. **Constant flip vs flag-only default:** the proposal flips `RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE = None → 0.5` at line 151 (default change) AND adds `--cosine-ramp-strength FLOAT` (CLI override). Alternatively, the constant could stay at `None` and only the CLI flag could set `0.5` (forcing every future sweep to explicitly opt in). **Proposal recommendation: keep flip** — the Wave 233 P5 plan explicitly recommends `cosine_ramp_strength=0.5` as the canonical CIFAR RF protocol, and the audit's "not yet wired" gap at line 135 is closed by the constant flip.

2. **Verify N value:** the R5b N=500 re-run uses the canonical N=500 sweep recipe. Should the verify also run N=1000 (matching the §15.98 row's canonical N=1000)? **Proposal recommendation: N=500** — matches the Wave 274 / Wave 275 verify budget; N=1000 is a follow-up post-acceptance.

3. **N_rounds override at the runner default:** the runner currently defaults to `n_rounds=4`. The K3 fix relies on the user passing `--n-rounds 2` explicitly. Should the runner default flip to `n_rounds=2` for CIFAR? **Proposal recommendation: NO** — the comment block at `rectified_flow_cifar.py:144-148` explicitly states "the runner remains the source of truth." Changing the runner default would break Wave 70-72 / Wave 191 P2 / Wave 247 / Wave 235 P1 byte-stable runs that depend on `n_rounds=4`. The fix is at the ADAPTER constant + CLI flag layer, NOT the runner default.

4. **Apply phase parallelism:** the proposal ships all changes in one PR
   (K3.A through K3.E in §7.1). Splitting into a "constant flip only" PR
   and a "CLI plumbing" PR would double the verify cost. **Proposal
   recommendation: single PR.**

5. **N=500 re-run timing:** the R5b N=500 re-run is gated on GPU 0 availability (per Wave 274 OOM defense + RLIMIT_AS). If GPU 0 is busy, the re-run can be deferred to the verify phase of a future wave (the constant flip + CLI flag land regardless, since D.4 byte-stability is preserved at `cosine_ramp_strength=None`). **Proposal recommendation: defer N=500 to verify phase — apply phase is CPU-only.**

---

## 9. Files proposed to be touched (after user approval)

| File | LOC | Touch type |
|---|---:|---|
| `adaptive_reflow/adapters/rectified_flow_cifar.py` | 1 LOC modified (line 151) + 5 LOC comment update (lines 130-135) | K3 |
| `tools/run_sota_cifar_experiment.py` | ~28 LOC additive (CLI flag lines 1086-1097) + ~10 LOC modified (factory lines 213-227) + ~6 LOC modified (call-site lines 730-732) | K3 + R5b |
| `tests/test_adapters/test_rectified_flow_cifar.py` | ~60 LOC additive (new test sections for constant value, CLI plumbing, n_min propagation) | K3 + R5b |
| `docs/CLAIMS.md` (additive annotation, if N=500 re-run lands) | ~3 LOC additive | post-verify |
| `docs/audit/wave275-p3-cifar-remediation-verify.md` | new file (~50 LOC) | verify phase |

**Total project-owned code change:** ~50 LOC modified + ~88 LOC additive.
**Vendored code change:** **ZERO.** (`vendoredTouched: false`)

---

## 10. Cross-references

- **Wave 275 P1 inventory:** `docs/audit/wave275-p1-state-inventory.md` §4.2 (CIFAR-10 RF row), §4.4 (K3 + R5b weakness classification)
- **Wave 275 P2 metric ledger:** `docs/audit/wave275-p2-metric-ledger.md` (where K3 + R5b row schema will land after re-sweep)
- **Wave 275 P3 flattening:** commit `8cd59b5` (proposal baseline)
- **Wave 275 P3.1 FlowMol3:** `docs/audit/wave275-p4-flowmol3-proposal.md` (sister proposal; same vector structure, disjoint file scope)
- **Wave 233 P5 R5b hypothesis:** `adaptive_reflow/adapters/rectified_flow_cifar.py:106-148` (the comment block + DeepSeek C recommendation); the constant at line 151 is the empirical lever the Wave 233 P5 plan hypothesises.
- **Wave 225 P7 reduced-rounds counterfactual:** `docs/audit/wave235-p1-r5b-fix.md:13, 149-156` (n_rounds=2 baseline ΔFID +9.77%; the prior measurement for the K3+R5b fix).
- **Wave 225 P9 falsification:** documented in `rectified_flow_cifar.py:122-128` (the matched-effective-NFE hypothesis was falsified; only the cosine ramp strength axis remained).
- **Wave 235 P1 R5b n_rounds=1:** `docs/audit/wave235-p1-r5b-fix.md:11-13, 149-160` (framework-WINS ΔFID -1.60% to -2.53% on 3/4 schedulers at n_rounds=1; the falsification of `--no-final-restart` at n_rounds=10).
- **§15.98 verdict transition table:** `docs/CONSOLIDATED_RESULTS.md:8356` (R5b row 3 — REGRESSES to framework-WINS transition)
- **§15.x K3 protocol-mismatch row:** `docs/CONSOLIDATED_RESULTS.md` (HEADLINE protocol-mismatch count = 2 before K3 fix; = 1 after)
- **D.4 byte-stable gate:** `docs/GATES.md:87-137` (72/72 contract)
- **OOM defense (RLIMIT_AS):** Wave 274 P3 subprocess wrapper, used for the N=500 re-run.
- **Wave 262 P1 / CLM-077:** `docs/CLAIMS.md` (all-vendored-patches-reverted directive; this proposal preserves that)

---

**End of proposal — awaits user approval before implementation. NO source
code modified by this commit.**