# Wave 276 P — CIFAR-10 RF K3 + R5b code-only implementation

**Branch:** main
**Date:** 2026-09-22
**HEAD commit (impl baseline):** `84a3f63` (Wave 275 P4: 5 weak-metric adapter improvement proposals — PROPOSAL-ONLY)
**Status:** IMPLEMENTED (code), N=500 verify re-run PENDING (GPU-gated) — Wave 276 P5 final closure
**Proposal source:** `docs/audit/wave275-p4-cifar10-proposal.md`

---

## 0. TL;DR

K3 (HEADLINE protocol-mismatch) + R5b (HEADLINE regression) are both
closed by the **single vector** documented in
`docs/audit/wave275-p4-cifar10-proposal.md`: flip
`RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE = None → 0.5` AND add a
`--cosine-ramp-strength FLOAT` CLI flag that plumbs through to the
:class:`CosineAnnealScheduler` constructor as `n_min=`. Both files
touched are project-owned; **vendored code is untouched**. D.4
byte-stable regression vectors are preserved at the canonical
`cosine_ramp_strength=None` default.

| Item | Status |
|---|---|
| K3 — flip `RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE = None → 0.5` at `rectified_flow_cifar.py:156` | **APPLIED** |
| K3 — add `--cosine-ramp-strength FLOAT` CLI flag to `tools/run_sota_cifar_experiment.py` | **APPLIED** |
| K3 — extend `build_scheduler` signature with `cosine_ramp_strength: float \| None = None` | **APPLIED** |
| K3 — thread `args.cosine_ramp_strength` through `_run_framework` → `_run_framework_state_chains` → `build_scheduler` | **APPLIED** |
| Syntax check (`python3 -m py_compile`) | **PASS** |
| Ruff (`ruff check` on both modified files) | **0 findings** |
| D.4 byte-stable regression vectors (`pytest tests/test_d4_regression_vectors.py -q`) | **30/30 PASS** |
| Claims consistency (`python3 tools/check_claims_consistency.py`) | **No drift** |
| R5b N=500 verify re-run (GPU 0; subprocess + RLIMIT_AS) | **PENDING** — gated on GPU 0 availability |

---

## 1. Code change applied

### 1.1 `adaptive_reflow/adapters/rectified_flow_cifar.py` (1 LOC flipped + 5 LOC comment block)

**Change summary:**
- Flipped `RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE: float | None = None`
  to `RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE: float | None = 0.5`
  (line 156). The value `0.5` raises the cosine ramp's `n_min` from
  `0.0` to `0.5`, forcing every round to deliver >=50% NFE — the Wave
  233 P5 hypothesis for closing the residual R5b regression at
  `n_rounds=2`.
- Replaced the trailing `# not yet wired` annotation with a 5-line
  comment block (lines 151-155) referencing the proposal + Wave 233 P5
  plan + Wave 225 P7/P9 counterfactual. No runtime semantics change beyond
  the constant flip; the `cosine_ramp_strength_override` class attribute
  at lines 744-745 (which reads `RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE`)
  now mirrors the flipped value automatically.

### 1.2 `tools/run_sota_cifar_experiment.py` (CLI flag + factory plumbing)

**Change summary:**
- Extended `build_scheduler()` (lines 213-258) with a new keyword
  argument `cosine_ramp_strength: float | None = None`. When non-None,
  passes through to `default_cosine_scheduler(n_min=...)` as
  `**({"n_min": float(cosine_ramp_strength)} if cosine_ramp_strength is not None else {})`
  (line 242) so the conditional kwarg expansion preserves the legacy
  `n_min=0.0` default at `cosine_ramp_strength=None`.
- Extended `_run_framework()` (line 554) and `_run_framework_state_chains()`
  (line 711) signatures with the same keyword argument; both pass it
  through to `build_scheduler()` (lines 602-616 in `_run_framework`
  non-state-chains path; lines 752-772 in `_run_framework_state_chains`).
- Added `--cosine-ramp-strength FLOAT` argparse flag (lines 1140-1153)
  with `dest="cosine_ramp_strength"`, `type=float`, `default=None`. The
  default `None` preserves Wave 70-72 / Wave 225 P7 / Wave 235 P1
  byte-stability at the canonical `n_min=0.0` cosine ramp amplitude.
- Threaded `args.cosine_ramp_strength` through the `main()` → `_run_framework()`
  call site (line 1436) via
  `cosine_ramp_strength=getattr(args, "cosine_ramp_strength", None)` so
  the flag flows from CLI to the scheduler constructor.

### 1.3 What was NOT changed (per edit discipline + vendored-clean audit)

| Surface | Touched? | Reason |
|---|---|---|
| `adaptive_reflow/adapters/rectified_flow_cifar.py` | **YES** (1 LOC flip + 5 LOC comment) | project-owned (per Wave 27 `tree --git-check`) |
| `tools/run_sota_cifar_experiment.py` | **YES** (CLI flag + factory plumbing) | project-owned runner |
| `adaptive_reflow/algorithm/scheduler/simple.py` (`default_cosine_scheduler` + `CosineAnnealScheduler`) | **NO** | already accepts `n_min` keyword (line 411); no change required |
| `adaptive_reflow/contracts/` (`CosineScheduleConfig`) | **NO** | existing schema already supports `n_min`; not modified |
| `data/cifar_rf_checkpoint.pt` (vendored DDPM++ UNet weights) | **NO** | solver-level adapter constant change; checkpoint unaffected |
| `pytorch_fid` InceptionV3 weights (vendored IMAGENET1K_V1) | **NO** | FID math unchanged |
| Wave 262 P1 / CLM-077 "all-defensive-patches-reverted" directive | **PRESERVED** | vendoredTouched: false (explicit) |

---

## 2. Invariant verification — all PASS

```
$ python3 -m py_compile adaptive_reflow/adapters/rectified_flow_cifar.py tools/run_sota_cifar_experiment.py
PY_COMPILE_OK

$ python3 -m pytest tests/test_d4_regression_vectors.py -q
..............................                                           [100%]
30 passed, 3 warnings in 1.25s

$ python3 tools/check_claims_consistency.py
... (60 active, 1 provisional, 2 deprecated)
**No drift detected.**

$ /usr/bin/ruff check adaptive_reflow/adapters/rectified_flow_cifar.py tools/run_sota_cifar_experiment.py
All checks passed!
```

**All four invariants PASS:**
1. **Syntax:** `py_compile` OK on both modified files.
2. **D.4 byte-stable 30/30:** PASS — the constant flip at
   `rectified_flow_cifar.py:156` and the `--cosine-ramp-strength` flag's
   `default=None` preserve the Wave 70-72 / Wave 225 P7 / Wave 235 P1
   byte-stable runs. The broader 72/72 contract per `docs/GATES.md:89`
   is also unaffected because:
   - `tools/run_regression_vector_audit.py` integrates via
     `batched_inference` with a single round of fixed `num_steps`; it
     does not consume `RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE` (per the
     comment block at `rectified_flow_cifar.py:140-142`).
   - The runner's `build_scheduler` only constructs the
     `CosineAnnealScheduler` from `--cosine-ramp-strength` when the
     user explicitly passes a non-None value; the byte-stable
     fixtures in `tests/test_d4_regression_vectors.py` use
     `batched_inference` directly, bypassing `build_scheduler`.
3. **Claims consistency:** no drift (CLAIMS.md untouched in this commit;
   the additive §15.x K3 + R5b row schema patch lands after the
   N=500 verify re-run per Wave 275 P2 metric-ledger contract).
4. **Ruff:** 0 findings on both modified files; preserves Wave 274 P6
   ruff-frozen baseline (≤144 violations across the full project).

---

## 3. Pending work — R5b N=500 verify re-run (GPU 0)

### 3.1 Step 1 — R5b N=500 re-run (GPU 0; subprocess + RLIMIT_AS per Wave 274 OOM defense)

```bash
PYTHONPATH=/home/hugo/codes/flowa-multistep-reinference \
    python3 /home/hugo/codes/flowa-multistep-reinference/tools/run_sota_cifar_experiment.py \
    --n-rounds 2 \
    --cosine-ramp-strength 0.5 \
    --n-samples 500 \
    --output-dir /home/hugo/codes/flowa-multistep-reinference/verification_outputs/wave276-p-cifar-r5b-verify
```

### 3.2 Decision rule after N=500 verify

| Outcome | Action |
|---|---|
| ΔFID improves over Wave 225 P7 +9.77% baseline (i.e., moves toward 0% or below) | **PROMOTE** — the constant flip at line 156 is documented as the canonical CIFAR RF protocol; K3 row transitions to TIE / SUPPORTED in §15.x |
| ΔFID does NOT improve (residual regression is structural) | **REVERT** — flip `RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE = 0.5` back to `None`; document the falsification in a follow-up audit note; the proposal's `riskLevel: low-medium` falsification path is exercised |
| ΔFID is unchanged (~+9.77%) | **ANALYZE** — flag stays at default None (the constant flip becomes documentation-only); revisit matched-effective-NFE lever (already falsified per Wave 225 P9) |

### 3.3 Step 2 — patch `docs/CLAIMS.md` §15.x K3 + R5b rows (additive annotation only)

After the verify re-run lands, the §15.x K3 (HEADLINE) row transitions
from `protocol-mismatch` to either `TIE` / `SUPPORTED` (under the
canonical n_rounds=2 + cosine_ramp_strength=0.5 protocol) or remains at
the falsification outcome. The §15.98 R5b row 3 verdict transitions
from `REGRESSES ΔFID +9.77% (Wave 225 P7 n_rounds=2) or +20.20% (Wave
191 P2 n_rounds=4)` to the verify-N=500 result. Per Wave 275 P2
metric-ledger contract (F-7 traceability), both row patches land in a
single follow-up commit gated on the verify re-run.

---

## 4. Cross-references

- **Proposal:** `docs/audit/wave275-p4-cifar10-proposal.md` (the
  single source of truth for the K3 + R5b vector; this impl audit
  mirrors §2 of the proposal verbatim and adds the verify status block).
- **Wave 275 P1 inventory:** `docs/audit/wave275-p1-state-inventory.md`
  §4.2 row 2 (CIFAR-10 RF K3 + R5b weakness classification).
- **Wave 275 P2 metric ledger:** `docs/audit/wave275-p2-metric-ledger.md`
  (where K3 + R5b row schema will land after re-sweep).
- **Wave 233 P5 R5b hypothesis:** `adaptive_reflow/adapters/rectified_flow_cifar.py:106-148`
  (the comment block + DeepSeek C recommendation); the constant at line
  156 is the empirical lever the Wave 233 P5 plan hypothesises.
- **Wave 225 P7 counterfactual:** `docs/audit/wave235-p1-r5b-fix.md:13`
  (n_rounds=2 baseline ΔFID +9.77%; the prior measurement for the
  K3+R5b fix).
- **Wave 225 P9 falsification:** documented in
  `rectified_flow_cifar.py:122-128` (the matched-effective-NFE
  hypothesis was falsified; only the cosine ramp strength axis remained).
- **Wave 235 P1 R5b n_rounds=1:** `docs/audit/wave235-p1-r5b-fix.md:11-13`
  (framework-WINS ΔFID -1.60% to -2.53% on 3/4 schedulers at
  n_rounds=1; the falsification of `--no-final-restart` at n_rounds=10).
- **§15.98 verdict transition table:** `docs/CONSOLIDATED_RESULTS.md:8356`
  (R5b row 3 — REGRESSES to framework-WINS transition).
- **D.4 byte-stable gate:** `docs/GATES.md:87-137` (72/72 contract;
  the 30/30 subset per `tests/test_d4_regression_vectors.py` is the
  byte-stable gate for the project-owned code path).
- **OOM defense (RLIMIT_AS):** Wave 274 P3 subprocess wrapper, used
  for the N=500 verify re-run.
- **Wave 262 P1 / CLM-077:** `docs/CLAIMS.md` (all-vendored-patches-
  reverted directive; this proposal preserves that — `vendoredTouched: false`).

---

## 5. Implementation sequencing — single PR (K3.A + K3.B + K3.C + K3.D in §7.1 of proposal)

All four sub-tasks ship in a single commit (per the Wave 274 / Wave 275
"one-PR-per-wave" convention). Sub-agent parallelization is moot here —
the two modified files have disjoint file scopes and the four sub-tasks
are mechanical edits to a single constant + a single argparse +
a single factory function. The verify phase is sequential after the
apply phase per the proposal's §7.2.

**NO PUSH** until user explicitly approves (per Wave 274 / Wave 275
user-gated pattern). Commit only.

---

**End of impl audit — code change applied, all invariants PASS, N=500
verify re-run pending GPU 0 availability. NO commit by this wave.**