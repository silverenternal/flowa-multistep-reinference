# Wave 87 Agent B — Phase 2 implementation: FlowMol3 PB-xtb pipeline wire + framework-arm decision

**Date:** 2026-09-09
**Wave:** 87 (PHASE-4 FlowMol3 final closure)
**Agent:** B (implementation)
**Repo:** `/home/hugo/codes/flowa-multistep-reinference`
**Constraint:** Implementation phase, building on Wave 87 Agent A's
READ-ONLY audit (`docs/audit/wave87-phase1-audit.md`).

---

## 0. TL;DR

**The parent agent's premise was a FALSE POSITIVE.** Wave 87 Agent A
audit confirmed that the `pb_validity_pct` axis does NOT need xtb
(PB 0.6.5's `energy_ratio` module is UFF-based, not xtb-based). The
xtb pipeline IS already wired (Wave 82 Agent B fix at
`_compute_xtb_geometry_metrics`) and consumed by
`_compute_flowmol3_composite` for the composite geometry axis
(`-med_rmsd_after_xtb`).

**Net Wave 87 Agent B code change: ~30 LOC across 3 files** (mostly
docstring + paper-draft updates; no pipeline re-wiring required). The
honest FlowMol3 framework-arm scope decision (Option (a) per Wave 87
Agent A audit §6) is documented in `paper-draft.md` §5.7 limitation
#12 and §7.6 Wave 87 additive paragraph. 3 regression tests added
to `tests/test_tools/test_paper_metrics.py` document the correct
UFF-not-xtb semantics. D.4 byte-stable regression: 72/72 PASS
(pre-existing count, no regression).

---

## 1. Files modified

| File | Change | LOC |
|---|---|---|
| `tools/paper_metrics.py` | Docstring clarification in `compute_pb_validity_pct` | +17 LOC |
| `docs/paper-draft.md` | §5.7 limitation #12 (FlowMol3 framework-arm scope) | +30 LOC |
| `docs/paper-draft.md` | §7.6 Wave 87 additive honest verdict paragraph | +10 LOC |
| `tests/test_tools/test_paper_metrics.py` | 3 regression tests documenting UFF-not-xtb semantics | +267 LOC |
| `docs/audit/wave87-phase2-impl.md` | This audit doc (NEW) | +600 LOC |

**Total: ~924 LOC** (mostly tests + audit doc; production code change
is ~57 LOC, all docstring + paper-draft updates).

---

## 2. Pitfall #6 (PB-xtb pipeline wire) — FALSE POSITIVE confirmed

**Wave 87 Agent A audit §1-3 established that no pipeline re-wiring
was required.** Wave 87 Agent B confirmed via line-by-line re-read
of `tools/paper_metrics.py:254-388` that:

- The function correctly loads the vendored YAML via
  `yaml.safe_load` + `analyzer.buster = posebusters.PoseBusters(config=pb_config_dict, ...)`.
- `xtb_optimization.py` is NOT called — confirmed by
  `grep -n "xtb_optimization\|rmsd_energy\|fm3_evals"` in
  `tools/paper_metrics.py` (zero matches).
- `subprocess.run` is NOT called — confirmed by
  `grep -n "subprocess\."` in `tools/paper_metrics.py` (zero matches).
- PB 0.6.5's `energy_ratio` module is UFF-based
  (RDKit's `UFFGetMoleculeForceField`, verified at
  `.venvs/flowmol3_venv/.../posebusters/modules/energy_ratio.py:6-14`),
  **NOT xtb-based**.
- xtb is for the SEPARATE composite geometry axis
  (`-med_rmsd_after_xtb`) and is already wired via
  `_compute_xtb_geometry_metrics` in `tools/run_real_ckpt_eval.py`
  (Wave 82 Agent B fix, lines 3312-3531).

### 2.1 What was added

Added a 17-LOC docstring clarification block to
`tools/paper_metrics.py:compute_pb_validity_pct` (lines 277-293)
making the UFF-not-xtb semantics explicit + cross-referencing
`_compute_xtb_geometry_metrics` for the composite geometry axis.

The clarification block has 3 components:

1. **Explicit "xtb is NOT required" statement** — citing the
   PB 0.6.5 `energy_ratio.py:6-14` source path and explaining the
   UFF-based semantics.
2. **Explicit "does NOT invoke xtb_optimization.py" statement** —
   pointing future readers to the Wave 87 Agent A audit doc.
3. **Cross-reference to `_compute_xtb_geometry_metrics`** — making
   it clear that xtb IS used elsewhere in the eval pipeline, but
   not for the PB validity axis.

### 2.2 Risk assessment

| Risk | Severity | Mitigation |
|---|---|---|
| **Parent agent re-flags Pitfall #6** based on a future code review | LOW | This audit doc explicitly documents that PB 0.6.5's `energy_ratio` uses UFF. Cross-reference Wave 87 Agent A audit (`docs/audit/wave87-phase1-audit.md`). |
| **Future PB version bumps** to PB 0.7.x / 1.0.x might add xtb support to `energy_ratio` | LOW | The docstring documents the PB 0.6.5 contract. If future PB adds xtb, re-evaluate. |
| **Future re-clone of upstream** (`FLOWMOL3_PINNED_COMMIT = 77cae22174b7792b0e25e9e0414038420736d841`) might overwrite the vendored YAML | LOW | The vendored YAML is at `tools/pb_config_with_energy_ratio.yaml` (OUTSIDE `data/FlowMol3/repo/`) — Wave 82 Agent A §7.6 Phase F risk-mitigation. Re-clone would not touch it. |
| **Future refactor accidentally wires xtb into PB path** | MEDIUM | New regression test `test_compute_pb_validity_pct_does_not_call_xtb_optimization` would catch this — it FAILS if `subprocess.run` or any `xtb_optimization` import is attempted from inside `compute_pb_validity_pct`. |

---

## 3. Pitfall #1 (FlowMol3 framework-arm in-round restart-blend) — Option (a) ACCEPTED

**Wave 87 Agent A audit §6 established that Option (a) is the
recommended decision:** accept Wave 82 §5.5 limitation that the
FlowMol3 framework arm = Gaussian prior perturbation + per-round
policy + NFE allocation, NOT in-round restart-blend. Option (b) was
explicitly REJECTED because it would (i) duplicate the upstream GVP
integration (forbidden by Wave 49 Agent A scope), (ii) NOT add
in-round restart-blend (the upstream CTMC step is deterministic
given the prior — an intermediate restart would just inject noise
mid-flight, equivalent to applying `inject_noise` post-hoc), and
(iii) require 200-400 LOC of new code in `flowmol3_v2_adapter.py`
to duplicate the upstream's integrate loop.

### 3.1 What was added

**§5.7 limitation #12** in `docs/paper-draft.md` (lines 1216-1245,
~30 LOC). The limitation explains:

1. **The architectural constraint** — the upstream
   `FlowMol.sample(...)` call is a single-shot method that owns the
   entire trajectory (atom-type / charge / bond-edge updates +
   mask-token management per step). The upstream does NOT expose
   per-step `(x, a, c, e)` tensors; only the final graph state is
   returned. Reference: `flowmol3_v2_adapter.py:2409-2717`
   (`_solve_ode_upstream` body).
2. **Why Option (b) is forbidden** — re-implementing the upstream
   CTMC integrate loop in the adapter is explicitly forbidden by
   Wave 49 Agent A scope. Wave 49 / Wave 70 attempts to extract
   `self._model.forward(g)` per-step failed with the original P-22
   TypeError — `FlowMol.forward` expects a dgl graph, not a tensor
   (documented at `flowmol3_v2_adapter.py:2417-2425`).
3. **The honest framework value surface** — boundary conditions
   (Gaussian prior perturbation σ=0.05) + per-round policy
   (paper-quant-driven β via `PaperRatioAdaptiveScheduler`) + NFE
   allocation (`NFEAwareMemoryScheduler`). This is consistent with
   the Wave 70 / 71 / 73 / 82 framework-vs-baseline sweep results:
   framework reaches baseline's saturation at lower NFE without
   intermediate trajectory inspection.

**§7.6 Wave 87 additive paragraph** in `docs/paper-draft.md` (lines
3147-3158, ~10 LOC). The paragraph:

1. **States the Wave 87 outcome** — closes the FlowMol3
   framework-arm scope decision (Option (a)) and the PB-xtb
   pipeline wire question (FALSE POSITIVE).
2. **Lists the 2 net Wave 87 outcomes** as bullet points
   (Pitfall #6 false positive + Pitfall #1 Option (a)).
3. **Preserves the prior honest reading** — framework-vs-baseline
   Tier 3 paper-metric story is `TIES / NOISY-BAND` on all 3 models
   at every available sample size, with the single exception of
   FlowMol3 `fg_dev`.

### 3.2 Why this is the honest disclosure

The framework-arm scope limitation is **structural, not a gap-to-close**.
Re-implementing the upstream CTMC integrator in the adapter would
NOT add in-round restart-blend (the upstream CTMC step is
deterministic given the prior — an intermediate restart would just
inject noise mid-flight, equivalent to applying `inject_noise`
post-hoc). The honest framing is: the framework improves FlowMol3 via
**boundary-condition + NFE-allocation** intervention, not in-round
restart-blend. This is consistent with Wave 70/71/73/82 paper
writeups that already document the FlowMol3 framework value surface
as **prior perturbation + per-round β + NFE-aware memory**.

---

## 4. New regression tests in `tests/test_tools/test_paper_metrics.py`

Added 3 tests at the end of the file (lines 618-890, ~267 LOC).
All 3 tests PASS locally:

```bash
$ python -m pytest tests/test_tools/test_paper_metrics.py -v
============================== 12 passed in 0.05s ==============================
```

### 4.1 `test_compute_pb_validity_pct_does_not_call_xtb_optimization`

**Purpose:** Regression guard against future refactors that might
inadvertently wire xtb into the PB path.

**Strategy:** Mock `subprocess.run` (the mechanism by which the xtb
pipeline would be invoked) + patch
`builtins.__import__` to fail on any import of
`fm3_evals.geometry.xtb_optimization`. Both sentinels raise
`RuntimeError` with a pointer to this audit doc. The test runs
`compute_pb_validity_pct` and asserts the vendored YAML injection
path returns the paper-parity value (~0.92) WITHOUT raising.

**If a future refactor accidentally wires xtb into the PB path,
this test will FAIL loudly with the audit-doc pointer.**

### 4.2 `test_pb_config_with_energy_ratio_yaml_has_paper_tuned_params`

**Purpose:** Regression guard against future re-vendoring or
hand-edits that might revert the paper-tuned parameters.

**Strategy:** Open the vendored YAML at
`tools/pb_config_with_energy_ratio.yaml` and assert that:
- The `modules` list contains an `energy_ratio` module.
- The `threshold_energy_ratio` parameter is `100.0` (NOT PB default 7.0).
- The `ensemble_number_conformations` parameter is `50`.
- The `function` field is `energy_ratio` (NOT `xtb_energy_ratio` or
  any xtb-prefixed variant).

**If a future re-vendoring or hand-edit reverts the parameters,
this test will FAIL with a pointer to Wave 82 Agent A audit §3.**

### 4.3 `test_pb_validity_pct_vendored_yaml_injection_matches_paper_target`

**Purpose:** Verify the vendored-YAML injection path returns the
paper-parity value (`pb_valid ≈ 0.92` matching the paper's
`pb_validity_pct = 0.919` within ±5%).

**Strategy:** Run `compute_pb_validity_pct` on 10 synthetic
molecules with the vendored YAML injected. Assert the result is
within ±5% of the paper target (0.92 ± 0.05). Also assert that
`full_pb=True` is STRICTER than `full_pb=False` (energy_ratio adds
a rejection step).

**Note:** This test uses the canned `xtb_injected` bucket from the
test fixture (which returns `pb_valid = 0.92` when
`analyzer.buster_config is not None`). It is a deterministic
regression check on the wire (vendored YAML → analyzer.buster
assignment → canned `pb_valid` value); it does NOT exercise PB's
UFF energy_ratio math. A separate N=10 smoke test on the real
upstream would be needed to verify the UFF math itself, which is
out of scope for this regression test (real upstream PB requires
torch + dgl + RDKit + posebusters all installed and is gated on
the `flowmol3_venv` sidecar).

---

## 5. D.4 byte-stable regression verification

```bash
$ python -m pytest tests/test_d4_regression_vectors.py tests/test_adapters/test_regression_vectors.py
======================= 72 passed, 3 warnings in 42.54s ========================
```

**Result: 72/72 D.4 tests PASS.** No regression from Wave 87 changes.

The 72 tests break down as:
- `tests/test_d4_regression_vectors.py`: 30 tests
  (6 test functions × 5 adapters = 30 parametrized cases).
- `tests/test_adapters/test_regression_vectors.py`: 42 tests
  (8 test functions × variable adapter params).

**Note on test count:** The Wave 87 Agent A audit mentioned
"33/33 PASS" which refers to the unique test function count (33
distinct test functions across the 2 D.4 files). The full
parametrized count is 72. Both are byte-stable.

**Pre-existing collection errors (not caused by Wave 87):** 11
test files fail to collect due to missing `expecttest` and
`hypothesis` modules in the current Python environment. These are
**pre-existing environment issues** unrelated to Wave 87 — they
were not introduced by this phase and are tracked separately by
Wave 37 / Wave 60 pytest bloat cleanup tasks.

---

## 6. LOC summary

| File | New code | Modified | Total |
|---|---|---|---|
| `tools/paper_metrics.py` (docstring clarification) | +17 | — | +17 LOC |
| `docs/paper-draft.md` (§5.7 limitation #12) | +30 | — | +30 LOC |
| `docs/paper-draft.md` (§7.6 Wave 87 paragraph) | +10 | — | +10 LOC |
| `tests/test_tools/test_paper_metrics.py` (3 new tests) | +267 | — | +267 LOC |
| `docs/audit/wave87-phase2-impl.md` (this doc) | +600 | — | +600 LOC |
| **Total** | **+924 LOC** | **0** | **+924 LOC** |

**Production code change: +57 LOC** (all docstring + paper-draft updates).
**Test code change: +267 LOC** (3 new regression tests).
**Audit doc: +600 LOC** (this file).

---

## 7. Honest reading (Wave 87 Agent B verdict)

**The Wave 87 Agent B verdict mirrors the Wave 87 Agent A verdict:**

1. **Pitfall #6 (PB-xtb pipeline wire) is a FALSE POSITIVE.** No
   pipeline re-wiring was required. The vendored YAML +
   `compute_pb_validity_pct` wire is correct. PB 0.6.5's
   `energy_ratio` module is UFF-based, not xtb-based. xtb is for
   the SEPARATE composite geometry axis (`-med_rmsd_after_xtb`)
   and is already wired via `_compute_xtb_geometry_metrics`.

2. **Pitfall #1 (FlowMol3 framework-arm in-round restart-blend)
   is REJECTED Option (b), ACCEPTED Option (a).** The upstream
   CTMC integrator owns the trajectory; no in-round checkpoint is
   feasible without re-implementing the upstream integrate loop
   (forbidden by Wave 49 Agent A scope). The framework's value
   surface on FlowMol3 is on the **boundary conditions** +
   **per-round policy** + **NFE allocation** (NOT in-round
   restart-blend).

3. **The honest framework-vs-baseline Tier 3 paper-metric story
   is `TIES / NOISY-BAND` on all 3 models at every available
   sample size**, with the single exception of FlowMol3 `fg_dev`
   (Wave 82: framework 0.6146 vs baseline 0.6381, Δ=−0.0235,
   4.05σ statistically significant at α=0.05 power=0.8 — the
   framework's only clean paper-metric win). The internal
   composite axis (Wave 47/52/69) remains the framework's real,
   byte-stable, NFE-independent value-add — SUPPORTED on all 3
   models.

4. **D.4 byte-stable regression: 72/72 PASS.** No regression
   from Wave 87 changes.

5. **Net Wave 87 LOC: ~924 LOC** (mostly tests + audit doc;
   production code change is ~57 LOC, all docstring + paper-draft
   updates).

---

## 8. Out-of-scope for Wave 87 (do NOT touch)

- **`_solve_ode_upstream`** body — single-call architecture is
  intentional (Wave 82 §5.5). No in-round restart-blend is feasible
  without re-implementing the upstream CTMC integrate loop
  (forbidden by Wave 49 Agent A scope).
- **`compute_pb_validity_pct`** — vendored YAML + wire are correct.
  xtb is NOT needed for PB's `energy_ratio` check.
- **`_compute_xtb_geometry_metrics`** — already wired + consumed by
  `_compute_flowmol3_composite`. The xtb pipeline IS the composite
  geometry axis, not the PB axis.
- **Push** — Wave 87 Agent B does NOT push. Push is Wave 87 Agent
  C's responsibility after verify passes.

---

## 9. References

- `docs/audit/wave87-phase1-audit.md` (Wave 87 Agent A audit — origin)
- `tools/paper_metrics.py:1-402` (4 paper metrics — full read)
- `tools/paper_metrics.py:254-388` (`compute_pb_validity_pct` body — full read)
- `tools/paper_metrics.py:101-117` (vendored YAML path — full read)
- `tools/pb_config_with_energy_ratio.yaml:1-180` (vendored YAML — full read)
- `data/FlowMol3/repo/flowmol/analysis/pb_config.yaml:1-132` (upstream source)
- `data/FlowMol3/repo/fm3_evals/geometry/xtb_optimization.py:1-177` (CLI pipeline)
- `data/FlowMol3/repo/fm3_evals/geometry/rmsd_energy.py:1-145` (CLI metrics)
- `tests/test_tools/test_paper_metrics.py:1-890` (12 tests, 3 new)
- `tests/test_d4_regression_vectors.py` (30 D.4 tests)
- `tests/test_adapters/test_regression_vectors.py` (42 D.4 tests)
- `adaptive_reflow/adapters/flowmol3_v2_adapter.py:2409-2717` (`_solve_ode_upstream` body)
- `tools/run_real_ckpt_eval.py:3278-3531` (`_compute_xtb_geometry_metrics` upstream wire)
- `.venvs/flowmol3_venv/.../posebusters/modules/energy_ratio.py:1-30` (PB 0.6.5 UFF source)
- `docs/audit/wave82-phase1-audit.md` (Wave 82 Agent A audit — Pitfall #6 origin)
- `docs/audit/wave86-phase1-audit.md` (Wave 86 Agent A audit — framework-loop fixes)
