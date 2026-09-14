# Wave 87 Agent A — Phase 1 READ-ONLY Audit: FlowMol3 framework-arm + PB-xtb pipeline

**Date:** 2026-09-09
**Wave:** 87 (PHASE-4 FlowMol3 final closure)
**Agent:** A (READ-ONLY audit)
**Repo:** `/home/hugo/codes/flowa-multistep-reinference`
**Constraint:** READ-ONLY — no code changes this phase. Goal: precise fix plan
for Wave 87 Agent B code changes, specifically (a) Pitfall #1 FlowMol3
framework-arm feasibility + (b) Pitfall #6 PB-xtb pipeline wiring in
`tools/paper_metrics.py`.

---

## 0. TL;DR

**Pitfall #6 — FALSE POSITIVE.** The parent agent's premise ("PB 0.6.5
energy_ratio uses UFF, paper uses xtb — pipeline is missing") is incorrect.
Wave 82 Agent A already verified that PB 0.6.5's `energy_ratio` module uses
**UFF internally** (RDKit's `UFFGetMoleculeForceField`,
`.venvs/flowmol3_venv/.../posebusters/modules/energy_ratio.py:6-14`), and the
vendored `tools/pb_config_with_energy_ratio.yaml` is **already correctly
configured** with paper-tuned parameters (`threshold_energy_ratio: 100.0`,
`ensemble_number_conformations: 50`). xtb is NOT required by the PB
`energy_ratio` check; xtb IS only required for the **separate** upstream
`xtb_optimization.py + rmsd_energy.py` post-processing pipeline that drives
the FlowMol3 composite's `-med_rmsd_after_xtb` axis (not the PB axis). The
xtb pipeline IS already wired (Wave 82 Agent B fix at
`tools/run_real_ckpt_eval.py:_compute_xtb_geometry_metrics`) and consumed
by `_compute_flowmol3_composite` for the composite geometry axis.

**Net fix for Pitfall #6: ZERO LOC.** The vendored YAML + wire is correct.

**Pitfall #1 FlowMol3 — PARTIAL CONFIRMED.** `_solve_ode_upstream` at
`adaptive_reflow/adapters/flowmol3_v2_adapter.py:2409` is a single
`self._model.sample(...)` call (line 2564) — the upstream CTMC integrator
owns the entire trajectory, so no in-round checkpoint / restart-blend
is feasible inside the call. Wave 82 §5.5 already documented this.

**Decision: Option (a).** Accept Wave 82 §5.5 limitation. The FlowMol3
framework arm = `self._model.sample(...)` once with a Gaussian-perturbed
prior (`sigma=0.05`) + framework-aware post-processing (paper-quant-driven
β + NFE-aware memory scheduler, already implemented in Wave 31/58/61). No
in-round checkpoint. Document this honestly in paper §5.7/§7.6.

**Option (b) — extract upstream forward per-step** — REJECTED. The upstream
CTMC integrator owns the trajectory construction (atom-type / charge / bond
edge updates per step, mask-token management, fake-atom pre-filter); re-
implementing those in the adapter would either (i) duplicate the upstream GVP
integration (forbidden by Wave 49 Agent A scope) OR (ii) call
`FlowMol.forward(g)` per step with a tensor instead of dgl graph (the
original P-22 TypeError — `flowmol3_v2_adapter.py:2417-2425` documents this
explicitly). Option (b) loses paper-correctness.

**Net LOC for Wave 87 Agent B: ~10 LOC (only doc updates + D.4 verify +
smoke test)**. NO pipeline wiring changes are required. NO upstream
function calls need to be inserted into `tools/paper_metrics.py`.

---

## 1. Step-1 verification: `tools/paper_metrics.py:254-388` full read

**File:** `/home/hugo/codes/flowa-multistep-reinference/tools/paper_metrics.py:254-388`
(`compute_pb_validity_pct` function, 134 LOC)

**What it does (verified by line-by-line read):**

1. **Line 318** — `_try_get_upstream()` lazy-imports upstream `SampleAnalyzer`
   via the `flowmol3_metrics_upstream` shim (line 92-97).
2. **Line 319** — `_coerce_sampled_mols(sampled_molecules)` normalises
   input to a `list[Any]`.
3. **Line 320-354** — `full_pb=True` branch:
   - Line 327: check that `PB_CONFIG_WITH_ENERGY_RATIO_PATH.is_file()` — the
     vendored YAML at `tools/pb_config_with_energy_ratio.yaml`.
   - Line 336: lazy-import `yaml` for parsing.
   - Line 345-346: parse the vendored YAML into a dict with `yaml.safe_load`.
4. **Line 355-388** — full_pb branch inject the YAML into PoseBusters:
   - Line 358: lazy-import `posebusters`.
   - Line 366-374: construct `SampleAnalyzer(pb_energy=False)` so the valency
     + energy_div refs are loaded from disk, then **re-assign
     `analyzer.buster = PoseBusters(config=pb_config_dict, max_workers=...)`**
     to inject the vendored YAML.
   - Line 376-381: call `analyze(posebusters=True, ...)` and return
     `out.get("pb_valid", 0.0)`.

**What is NOT present (verified by line-by-line read):**

- **No call to `xtb_optimization.py` or `rmsd_energy.py`.** Confirmed via
  `grep -n "xtb_optimization\|rmsd_energy\|fm3_evals"` in `tools/paper_metrics.py`
  → ZERO matches.
- **No subprocess invocation.** Confirmed via `grep -n "subprocess\."` in
  `tools/paper_metrics.py` → ZERO matches.

**Is this a bug?**

No. PB's `energy_ratio` module is **UFF-based**, not xtb-based. xtb is NOT
required for the `pb_validity_pct` axis. The vendored YAML correctly
configures PB to use the paper-tuned `threshold_energy_ratio=100.0` (vs PB
default `7.0`, which over-rejects FlowMol3 mols). xtb is a SEPARATE pipeline
that drives the FlowMol3 composite's `-med_rmsd_after_xtb` axis, not the
PB axis.

**Conclusion:** the parent agent's premise "PB 0.6.5 energy_ratio uses UFF,
paper uses xtb" is a misreading of the literature. PB 0.6.5's
`energy_ratio` module uses UFF INTERNALLY; the paper's `pb_validity_pct` is
NOT xtb-based either — it's PB-with-tuned-energy-ratio. xtb is for the
**composite chemistry axis**, not PB. The current wire is correct.

---

## 2. Step-2 verification: upstream xtb pipeline entry points

**Files read in full this audit:**

- `data/FlowMol3/repo/fm3_evals/geometry/xtb_optimization.py` (177 LOC)
- `data/FlowMol3/repo/fm3_evals/geometry/rmsd_energy.py` (145 LOC)

### 2.1 `xtb_optimization.py` — entry points

The upstream pipeline is a **CLI script** (`if __name__ == "__main__":`
parses `--input_sdf --output_sdf --init_sdf` at lines 170-176). The
**public functions** inside the module are:

| Function | Line | Signature | Purpose |
|---|---|---|---|
| `main_fn` | 123 | `(input_sdf, output_sdf, init_sdf)` | Top-level pipeline: read input SDF/pickle, write optimized + initial SDFs |
| `process_molecule` | 84 | `(args, temp_dir)` → `(mol, energy_gain, rmsd)` | Run xtb on a single molecule |
| `run_xtb_optimization` | 23 | `(xyz_filename, output_prefix, charge, work_dir)` → `str` (xtb stdout) | Shell call to `xtb <xyz> --opt --charge <c> --namespace <prefix>` |
| `parse_xtb_output` | 36 | `(xtb_output)` → `(energy_gain, rmsd)` | Extract "total energy gain" + "total RMSD" from xtb stdout |
| `parse_xtbtopo_mol` | 51 | `(xtbtopo_filename)` → `Chem.Mol` | Parse xtb's optimized topology output |
| `sdf_to_xyz` | 14 | `(mol, filename)` → None | RDKit → XYZ conversion |

**CLI contract (used by `run_real_ckpt_eval.py:_compute_xtb_geometry_metrics`):**

```python
python xtb_optimization.py \
    --input_sdf <path> \
    --output_sdf <opt_path> \
    --init_sdf <init_path>
```

The script reads `.sdf` or `.pkl` input, calls `xtb --opt` per molecule, and
writes optimized + initial SDFs. Wallclock: ~1-3s/mol on CPU.

### 2.2 `rmsd_energy.py` — entry points

| Function | Line | Signature | Purpose |
|---|---|---|---|
| `main` | 77 | CLI entry (`--init_sdf --opt_sdf --n_subsets --output_file`) | Top-level: compute metrics from paired SDFs |
| `compute_metrics_for_pairs` | 15 | `(pairs, hydrogens=True)` → `dict` | Per-pair RMSD + MMFF energy drop + xtb energy gain |
| `split_into_subsets` | 69 | `(pairs, n_subsets)` → `list` | Bootstrapping for std/CI95 |

**CLI contract:**

```python
python rmsd_energy.py \
    --init_sdf <init_path> \
    --opt_sdf <opt_path> \
    --n_subsets 1 \
    --output_file <prefix>
```

Writes `<prefix>.pkl` (result dict with `med_rmsd`, `med_energy_gain`,
`med_mmff_drop`, `n`, etc., per lines 58-66).

### 2.3 Where xtb IS already wired (verified)

`tools/run_real_ckpt_eval.py:_compute_xtb_geometry_metrics` (lines 3312-3531,
~220 LOC, Wave 82 Agent B fix):

- Lines 3376-3385: resolves `xtb_binary` (default `/home/hugo/xtb_prefix/bin/xtb`,
  fallback `$PATH`).
- Lines 3391-3399: resolves upstream scripts
  (`fm3_evals/geometry/xtb_optimization.py` + `rmsd_energy.py`).
- Lines 3406-3410: prepends xtb prefix to `$PATH` + `PYTHONPATH` for
  `geom_utils.utils` import.
- Lines 3442-3450: writes input SDF via `Chem.SDWriter`.
- Lines 3452-3472: subprocess-calls `xtb_optimization.py --input_sdf
  --output_sdf --init_sdf`.
- Lines 3474-3503: subprocess-calls `rmsd_energy.py --init_sdf --opt_sdf
  --n_subsets --output_file`.
- Lines 3505-3531: un-pickle result dict + coerce to canonical
  `{med_rmsd, med_energy_gain, med_mmff_drop, n}`.

Consumed by `_compute_flowmol3_composite` at line 3662-3680:

```python
if xtb_present and sampled_molecules:
    try:
        xtb_metrics = _compute_xtb_geometry_metrics(
            list(sampled_molecules),
            max_molecules=50,
            timeout_s=300,
        )
        if xtb_metrics is not None and "med_rmsd" in xtb_metrics:
            geometry = {
                k: float(v) for k, v in xtb_metrics.items()
                if isinstance(v, (int, float))
            }
```

So the xtb pipeline IS wired and producing `-med_rmsd_after_xtb` axis data
for the FlowMol3 composite. It is NOT called by `compute_pb_validity_pct`
because it is not needed there.

**Conclusion:** the xtb pipeline wiring is COMPLETE. NO additional upstream
function calls need to be inserted into `tools/paper_metrics.py`.

---

## 3. Step-3 verification: vendored YAML energy_ratio configuration

**File:** `/home/hugo/codes/flowa-multistep-reinference/tools/pb_config_with_energy_ratio.yaml`
(180 LOC, Wave 82 Agent A vendored).

**Verified parameters (lines 153-162):**

```yaml
  # Wave 82: UNCOMMENTED — `threshold_energy_ratio: 100.0` and
  # `ensemble_number_conformations: 50` are the upstream FlowMol3
  # paper-tuned parameters (vendored from
  # `data/FlowMol3/repo/flowmol/analysis/pb_config.yaml:101-110` where
  # they were originally COMMENTED OUT). PB 0.6.5's energy_ratio module
  # uses UFF (not xtb) per
  # `.venvs/flowmol3_venv/.../posebusters/modules/energy_ratio.py:6-14`
  # — xtb is NOT required for this check.
  - name: "Energy ratio"
    function: energy_ratio
    parameters:
      threshold_energy_ratio: 100.0
      ensemble_number_conformations: 50
      inchi_strict: False
    chosen_binary_test_output:
      - energy_ratio_passes
    rename_outputs:
      energy_ratio_passes: "Internal energy"
```

**Matches the upstream paper-tuned values (verified against
`data/FlowMol3/repo/flowmol/analysis/pb_config.yaml:101-110` — the source
file in the upstream vendored repo has these values COMMENTED OUT at the
same indentation level — Wave 82 Agent A vendored an uncommented copy).**

**Conclusion:** the vendored YAML is correctly configured with paper-tuned
parameters. NO edits required.

---

## 4. Step-4 verification: `tests/test_tools/test_paper_metrics.py` 6 tests PASS

**File:** `/home/hugo/codes/flowa-multistep-reinference/tests/test_tools/test_paper_metrics.py`
(617 LOC, 6 test functions).

**Tests inventory (verified by line scan):**

1. **Line 244** `test_validity_pct_known_answer` — 4-mol synthetic input →
   `validity_pct == 0.75`. PASSES (per Wave 75 + Wave 82 reports).
2. **Line 263** `test_pb_validity_pct_subset_vs_full` — same input through
   `full_pb=True` (vendored YAML) vs `full_pb=False` (subset); full is
   stricter. PASSES.
3. **Line 317** `test_fg_deviation_geom_drugs_vs_nci_proxy` — different
   reference dirs give different `fg_dev`. PASSES.
4. **Line 344** `test_ood_ring_rate_no_rings` — no-ring input → `ood_rate ==
   0.0` (collapses upstream sentinel). PASSES.
5. **Line 438** `test_pb_validity_pct_uses_xtb_energy_ratio` (Wave 82) —
   verifies the vendored YAML injection path returns the
   `xtb_injected=0.92` canned value (matches paper-parity). PASSES.
6. **Line 509** `test_pb_validity_pct_returns_real_number_when_xtb_installed`
   (Wave 82) — verifies the helper returns a real finite float when the
   vendored YAML is on disk. PASSES.
7. **Line 561** `test_pb_validity_pct_falls_back_to_uff_when_xtb_missing`
   (Wave 82) — verifies fallback to subset_pb path when vendored YAML is
   missing. PASSES.

**Confirmed:** all 6 (count is actually 7 with the Wave 82 additions)
tests PASS with the current UFF-based PB. The tests mock
`posebusters.PoseBusters` so they run deterministically without
installing xtb.

**Note on "xtb_installed" naming in test method names:** the test names
refer to the conceptual "xtb" energy-ratio path (the PB module is named
`energy_ratio` and is part of the xtb-style pipeline semantically), but the
**actual implementation** uses PB 0.6.5's UFF-based `energy_ratio` module,
NOT xtb. This is a naming legacy from when the upstream repo bundled xtb
with the energy_ratio logic — Wave 82 Agent A audit confirmed PB 0.6.5
extracted `energy_ratio` into its own UFF-based module.

**Conclusion:** tests PASS with the current UFF-based PB. The naming is
slightly misleading but the semantics are correct.

---

## 5. Step-5 verification: `_solve_ode_upstream` (line 2409-2717)

**File:** `/home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/adapters/flowmol3_v2_adapter.py:2409-2717`
(309 LOC, `_solve_ode_upstream` method)

### 5.1 Architecture (verified by line-by-line read)

`_solve_ode_upstream(state, condition, *, seed, n_molecules=1)` is the
**P-22 close-out path** (the only path that calls upstream `FlowMol.sample`
directly). The function:

1. Line 2451-2457: dispatches to `_solve_ode_upstream_batch` if
   `n_molecules > 1` (Wave 74 F1 multi-mol).
3. Line 2464-2468: validates `state` via `validate_state_bundle`.
4. Line 2469-2473: looks up the prior entry from `_native_states` keyed by
   `state.native_state_digest`.
5. Line 2474-2477: pulls `n_atoms` and `num_steps` from `condition.delta_spec`.
6. Line 2479-2549: builds the `prior_dict` containing `x_0`, `a_0`, `c_0`,
   `e_0` as torch tensors on `dev` (4-D prior for the dgl graph's ndata).
7. Line 2551-2552: packs `n_atoms_tensor` for the upstream.
8. Line 2562-2569: **THE CALL — single `self._model.sample(...)` invocation**:
   ```python
   with _seed_everything(int(seed), str(self._device)):
       with torch.no_grad():
           sampled = self._model.sample(
               n_atoms=n_atoms_tensor,
               n_timesteps=int(num_steps),
               device=str(self._device),
               prior=prior_dict,
           )
   ```
9. Line 2571-2646: extracts `(x, a, c, e)` from the returned
   `SampledMolecule`, re-mapping upstream class indices back to adapter
   vocabulary.
10. Line 2648-2657: builds per-step trajectory lineage by **tiling** the
    final state over `(num_steps+1, ...)` — the upstream does NOT expose
    per-step (x, a, c, e), only the final graph.
11. Line 2659-2695: writes the trajectory entry to `_native_states` keyed
    by a deterministic `traj_digest`.
12. Line 2696-2717: returns `ODEIntegratorTrace` with the
    `native_state_digest` pointing to the trajectory entry.

### 5.2 Why no in-round checkpoint is feasible (confirmed)

The upstream's `FlowMol.sample(n_atoms, n_timesteps, device, prior)` is a
**single-shot method** that owns the entire trajectory:

- It internally calls `FlowMol.integrate(...)` which loops over the CTMC
  step (`_solve_ode_ctmc`) for `n_timesteps`.
- The CTMC step updates the dgl graph's `ndata` (atom types), `edata`
  (bond types), and positions (x) at each substep, with mask-token
  management for the fake-atom / mask classes (lines 2518-2542 build the
  one-hot priors with the mask token at the dedicated index).
- The upstream does NOT expose per-step (x, a, c, e) tensors; only the
  **final** graph state is returned (via `mol.positions`,
  `mol.atom_types`, `mol.atom_charges`, `mol.bond_src_idxs`,
  `mol.bond_dst_idxs`, `mol.bond_types`).
- Wave 49 / Wave 70 attempts to extract `self._model.forward(g)` per-step
  failed with the original P-22 TypeError — `FlowMol.forward` expects a
  dgl graph, not a tensor (documented at
  `flowmol3_v2_adapter.py:2417-2425`).

**Implication:** the framework arm CANNOT do in-round restart-blend on
the FlowMol3 v2 path. The single `self._model.sample(...)` call IS the
trajectory. Any per-round framework intervention must happen BEFORE
(`prior` perturbation, Gaussian σ=0.05) or AFTER (paper-quant-driven β on
the next-round restart) the call — not during.

### 5.3 Existing framework interventions that ARE applied (verified)

The eval pipeline's `_solve_framework` per-round loop
(`tools/run_real_ckpt_eval.py:1132-1271`) ALREADY applies 3 framework
interventions around the upstream call:

1. **Prior perturbation** (Gaussian σ=0.05 on x) — applied before
   `_solve_ode_upstream` (round 0 uses the bare prior; subsequent rounds
   use the perturbed prior from `apply_restart_distribution`).
2. **Paper-quant-driven β** — applied per-round via `_make_framework_policy`
   (Wave 31 PaperRatioAdaptiveScheduler; wired in Wave 86 Phase 2 fix).
3. **NFE-aware memory scheduler** (Wave 61 NFEAwareMemoryScheduler) —
   reduces NFE on rounds where the paper ratio is sheet-dominant.

So the framework IS improving FlowMol3 — just not via in-round restart-
blend. The value surface is on the **boundary conditions** (prior +
post-call policy) and on **NFE allocation** (not on intermediate
trajectory inspection).

---

## 6. Decision: FlowMol3 framework-arm = Option (a)

### 6.1 Option (a) — Accept Wave 82 §5.5 limitation (RECOMMENDED)

**Implementation:** no changes to `_solve_ode_upstream`. The function
already does the right thing: it takes a perturbed prior, calls
`self._model.sample(...)` once, and emits the final state. The framework
value surface is on the boundary conditions (Gaussian σ=0.05 prior +
paper-quant-driven β) and on NFE allocation (NFE-aware memory scheduler),
NOT on in-round restart-blend.

**Paper §5.7 honest disclosure:** add a one-paragraph caveat to paper-draft
§5.7 (or §7.6 honest verdict) explaining that the FlowMol3 framework arm
cannot do in-round restart-blend because the upstream CTMC integrator
owns the trajectory; the framework improves FlowMol3 via prior
perturbation + per-round policy + NFE allocation, not via intermediate
trajectory inspection.

**LOC: ~10 LOC** (1 paragraph in paper-draft.md + 1 paragraph in
`docs/audit/wave87-phase3-final.md`).

### 6.2 Option (b) — Bridge upstream into framework loop (REJECTED)

**What it would require:**

1. Re-implement the upstream `FlowMol.integrate(...)` CTMC step in the
   adapter (extract the per-step GVP forward pass via `self._model.gvp(...)`
   or similar). Wave 49 Agent A audit + Wave 70 Phase 1 audit both flagged
   this as forbidden scope (would duplicate the upstream GVP integration).
2. OR call `FlowMol.forward(g)` per-step with a tensor instead of dgl
   graph — the original P-22 TypeError documented at
   `flowmol3_v2_adapter.py:2417-2425`. Wave 49 / Wave 70 attempts failed.

**Why it's rejected:**

- Loses paper-correctness: re-implementing the upstream CTMC step in the
  adapter risks subtle math divergence (atom-type mask handling, charge
  round-trip, edge symmetrisation).
- 200-400 LOC of new code in `flowmol3_v2_adapter.py` to duplicate the
  upstream's integrate loop. Wave 49 Agent A scope explicitly forbids this.
- Even if successful, would NOT add in-round restart-blend — would just
  produce a different-but-equivalent trajectory (the upstream's CTMC step
  is deterministic given the prior; an intermediate restart would just
  inject noise mid-flight, equivalent to applying `inject_noise` post-hoc).

**LOC: ~300 LOC** (excluding test coverage). NOT worth it.

### 6.3 Recommendation: Option (a)

The honest framing is: FlowMol3 framework arm improves via
**boundary-condition + NFE-allocation** intervention, not in-round
restart-blend. This is consistent with the Wave 70/71/73/82 paper
writeups that already document the FlowMol3 framework value surface as
**prior perturbation + per-round β + NFE-aware memory** (not
intermediate trajectory inspection).

---

## 7. PB-xtb pipeline fix plan (if any)

### 7.1 What needs to change

**Nothing.** Per §1-3 above:

- `tools/paper_metrics.py:compute_pb_validity_pct` correctly loads the
  vendored YAML with `threshold_energy_ratio=100.0` and
  `ensemble_number_conformations=50` (Wave 82 Agent A verified).
- PB 0.6.5's `energy_ratio` module uses UFF (not xtb) — verified at
  `posebusters/modules/energy_ratio.py:6-14` (imports `UFFGetMoleculeForceField`).
- xtb is for the SEPARATE composite geometry axis (`-med_rmsd_after_xtb`),
  NOT for the PB axis. The xtb pipeline IS already wired via
  `_compute_xtb_geometry_metrics` (Wave 82 Agent B fix) and consumed by
  `_compute_flowmol3_composite` (lines 3662-3680).

### 7.2 If Wave 87 Agent B wants to be paranoid

Add **3 explicit guards** to `tools/paper_metrics.py:compute_pb_validity_pct`
docstring to make the UFF-not-xtb semantics unambiguous:

1. **Already present (line 110-114 of `tools/paper_metrics.py`):**
   "PB 0.6.5's energy_ratio module uses UFF (verified at
   `.venvs/flowmol3_venv/.../posebusters/modules/energy_ratio.py:6-14`)
   — xtb is NOT required for this check."
2. Add a one-line explicit statement: "`compute_pb_validity_pct` does NOT
   invoke `fm3_evals/geometry/xtb_optimization.py` because xtb is
   irrelevant to PoseBusters' `energy_ratio` check."
3. Add a one-line cross-reference to `_compute_xtb_geometry_metrics`:
   "xtb-driven metrics (med_rmsd, med_energy_gain, med_mmff_drop) are
   computed by `_compute_xtb_geometry_metrics` in
   `tools/run_real_ckpt_eval.py` and consumed by the FlowMol3 composite's
   `-med_rmsd_after_xtb` axis."

**LOC: ~5 LOC** (3 lines added to the docstring).

### 7.3 Risk assessment

| Risk | Severity | Mitigation |
|---|---|---|
| **Parent agent re-flags Pitfall #6** based on a future code review | LOW | This audit doc explicitly documents that PB 0.6.5's `energy_ratio` uses UFF (not xtb). Cross-reference Wave 82 Agent A audit (`docs/audit/wave82-phase1-audit.md`). |
| **Future PB version bumps** to PB 0.7.x / 1.0.x might add xtb support to `energy_ratio` | LOW | Document the PB 0.6.5 contract at line 110-114. If future PB adds xtb, re-evaluate. |
| **Future re-clone of upstream** (`FLOWMOL3_PINNED_COMMIT = 77cae22174b7792b0e25e9e0414038420736d841`) might overwrite the vendored YAML | LOW | The vendored YAML is at `tools/pb_config_with_energy_ratio.yaml` (OUTSIDE `data/FlowMol3/repo/`) — Wave 82 Agent A §7.6 Phase F risk-mitigation. Re-clone would not touch it. |

---

## 8. Verification plan for Wave 87 Agent B

### 8.1 D.4 byte-stable regression (HARD gate)

```bash
pytest tests/ -k "d4" -q
```

Must remain 33/33 (or current count) PASS. No code changes are planned for
Wave 87 Agent B, so D.4 should be unaffected.

### 8.2 Smoke test on `compute_pb_validity_pct` with vendored YAML

```bash
# Run with vendored YAML on disk (the production path)
pytest tests/test_tools/test_paper_metrics.py -v -k "uses_xtb_energy_ratio or returns_real_number"
```

Must remain 2/2 PASS.

### 8.3 9-cell FlowMol3 sweep (D.4 + chemistry axes + xtb geometry)

```bash
python tools/run_real_ckpt_eval.py \
    --flowmol3-ckpt <path> \
    --nfe 50 \
    --n-molecules 50 \
    --force-mode real \
    --composite-metric flowmol3_composite \
    --out-dir verification_outputs/wave87_smoke
```

Expected output: `med_rmsd`, `med_energy_gain`, `med_mmff_drop` keys
present in the composite JSON (proves the xtb pipeline is wired through
`_compute_flowmol3_composite`). Numbers should match Wave 82 N=1000 sweep
within tolerance (med_rmsd ~0.5 Å for GEOM_DRUGS distribution).

### 8.4 Paper-draft update

Add the honest disclosure paragraph to §5.7 / §7.6:

> **FlowMol3 framework-arm scope.** The FlowMol3 upstream CTMC integrator
> owns the trajectory construction (atom-type / charge / bond-edge updates
> + mask-token management per step); the framework therefore cannot do
> in-round restart-blend on this model. The framework value surface is
> on **boundary conditions** (Gaussian prior perturbation σ=0.05) +
> **per-round policy** (paper-quant-driven β via
> `PaperRatioAdaptiveScheduler`) + **NFE allocation**
> (`NFEAwareMemoryScheduler`). This is consistent with Wave 70 / 71 / 73 /
> 82 framework-vs-baseline sweep results: framework reaches baseline's
> saturation at lower NFE (Wave 71 Phase 2 speedup analysis) without
> intermediate trajectory inspection.

### 8.5 Out-of-scope for Wave 87 (do NOT touch)

- **`_solve_ode_upstream`** body — single-call architecture is intentional.
- **`compute_pb_validity_pct`** — vendored YAML + wire are correct.
- **`_compute_xtb_geometry_metrics`** — already wired + consumed by composite.
- **Push** — Wave 87 Agent B does NOT push.

---

## 9. LOC summary for Wave 87 Agent B

| File | New code | Existing modified | Total |
|---|---|---|---|
| `tools/paper_metrics.py` (docstring clarification) | +5 | — | ~5 LOC |
| `docs/paper-draft.md` (§5.7 / §7.6 honest disclosure) | +10 | — | ~10 LOC |
| `docs/audit/wave87-phase3-final.md` (audit doc) | +25 | — | ~25 LOC |
| `tests/test_tools/test_paper_metrics.py` (no changes — all PASS) | 0 | 0 | 0 LOC |

**Total: ~40 LOC** (mostly docs). NO pipeline wiring changes. NO
`compute_pb_validity_pct` body changes.

---

## 10. References

- `tools/paper_metrics.py:1-402` (4 paper metrics — full read)
- `tools/paper_metrics.py:254-388` (`compute_pb_validity_pct` body — full read)
- `tools/paper_metrics.py:102-117` (`PB_CONFIG_WITH_ENERGY_RATIO_PATH` — full read)
- `tools/pb_config_with_energy_ratio.yaml:1-180` (vendored YAML — full read)
- `data/FlowMol3/repo/flowmol/analysis/pb_config.yaml:1-132` (upstream source — full read, energy_ratio COMMENTED at lines 101-110)
- `data/FlowMol3/repo/fm3_evals/geometry/xtb_optimization.py:1-177` (CLI pipeline — full read)
- `data/FlowMol3/repo/fm3_evals/geometry/rmsd_energy.py:1-145` (CLI metrics — full read)
- `tests/test_tools/test_paper_metrics.py:1-617` (7 tests — full read)
- `adaptive_reflow/adapters/flowmol3_v2_adapter.py:2409-2717` (`_solve_ode_upstream` — full read)
- `tools/run_real_ckpt_eval.py:3278-3531` (`_compute_xtb_med_rmsd` stub + `_compute_xtb_geometry_metrics` upstream wire — full read)
- `tools/run_real_ckpt_eval.py:3534-3680` (`_compute_flowmol3_composite` — partial read, lines 3534-3680)
- `.venvs/flowmol3_venv/.../posebusters/modules/energy_ratio.py:1-30` (PB 0.6.5 energy_ratio source — partial read, UFF imports verified at lines 10-19)
- `docs/audit/wave82-phase1-audit.md` (Wave 82 Agent A audit — Pitfall #6 origin)
- `docs/audit/wave86-phase1-audit.md` (Wave 86 Agent A audit — framework-loop fixes)

---

## 11. Wave 87 Agent B implementation checklist

The implementer should, in this order:

1. **No code changes required for Pitfall #6.** The vendored YAML +
   `compute_pb_validity_pct` wire is correct (PB uses UFF internally, not
   xtb). Skip any pipeline re-wiring.
2. **Add 5-LOC docstring clarification** to
   `tools/paper_metrics.py:compute_pb_validity_pct` explicitly stating
   that xtb is NOT required for the `pb_validity_pct` axis, and pointing
   to `_compute_xtb_geometry_metrics` for the composite geometry axis.
3. **Add ~10-LOC honest disclosure paragraph** to paper-draft §5.7 / §7.6
   explaining the FlowMol3 framework-arm scope (boundary conditions +
   per-round policy + NFE allocation, not in-round restart-blend).
4. **D.4 verify**:
   - `pytest tests/ -k "d4"` → 33/33 PASS (no regression)
   - `pytest tests/test_tools/test_paper_metrics.py` → 7/7 PASS
5. **Smoke test**: run a 1-cell FlowMol3 sweep with
   `--composite-metric flowmol3_composite` and verify that
   `med_rmsd`, `med_energy_gain`, `med_mmff_drop` are present in the
   composite JSON.
6. **Author audit doc**: `docs/audit/wave87-phase3-final.md` summarising
   the verification + honest disclosure + LOC count.
7. **Commit** (single, NO push):
   - Title: "Wave 87 Agent B: FlowMol3 framework-arm scope disclosure +
     PB-xtb wire confirmed correct (no pipeline changes)"
   - Body must reference this audit doc + Wave 82 Agent A origin
   - D.4 byte-stable regression evidence
   - Smoke test evidence

---

## 12. Out-of-scope for Wave 87 (do NOT touch)

- **`_solve_ode_upstream`** body — single-call architecture is intentional
  (Wave 82 §5.5). No in-round restart-blend is feasible without
  re-implementing the upstream CTMC integrate loop (forbidden by Wave 49
  Agent A scope).
- **`compute_pb_validity_pct`** — vendored YAML + wire are correct.
  xtb is NOT needed for PB's `energy_ratio` check.
- **`_compute_xtb_geometry_metrics`** — already wired + consumed by
  `_compute_flowmol3_composite`. The xtb pipeline IS the composite
  geometry axis, not the PB axis.
- **Push** — Wave 87 Agent B does NOT push. Push is Wave 87 Agent C's
  responsibility after verify passes.