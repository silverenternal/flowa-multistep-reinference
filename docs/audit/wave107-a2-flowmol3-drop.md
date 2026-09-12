# Wave 107.A.2 — FlowMol3 1-mol drop reuse research (READ-ONLY)

**Task:** Find the cheapest way to find + fix the 1-mol drop (baseline N=999 vs
N=1000) WITHOUT writing new diagnostic code from scratch.

**Goal:** Identify EXISTING code/library patterns on disk that can be REUSED
to either (a) recover the dropped mol, (b) explain the root cause cheaply, or
(c) disclose the drop via the existing disclosure infrastructure.

**Commit SHA:** `c0dd9e49251a6de845e034e68bd086e85aeec485`

---

## TL;DR — root cause is already known + disclosed; no new diagnostic code needed

| Question | Answer |
| --- | --- |
| Why does baseline drop 1 mol? | CTMC valence artifact in upstream `FlowMol.sample`; 1 of 1000 generated SMILES fails `Chem.MolFromSmiles` (Cl valence violation). |
| Where is the existing fix / disclosure? | Already documented in 7+ places (Wave 82, Wave 87, Wave 106.A.2). |
| Can we reuse existing code to recover the mol? | Yes — but the dropped SMILES is fundamentally un-parseable by RDKit; the only reusable rescue path is the upstream `SampledMolecule` object (which already has the molecular graph, not just SMILES). |
| Cheapest path forward | **A**: route via upstream `SampledMolecule` directly (skip the SMILES→Mol round-trip). **B**: live with the disclosure (already in place). |

---

## 1. JSON file evidence — `verification_outputs/flowmol3_n1000_baseline_q4_2026.json`

`/home/hugo/codes/flowa-multistep-reinference/verification_outputs/flowmol3_n1000_baseline_q4_2026.json:1-8`:

```json
{
  "n_target": 1000,
  "n_sampled": 999,    <-- 1 mol dropped
  "n_smiles": 1000,    <-- all 1000 SMILES strings retained
  "n_errors": 0,       <-- no exceptions
  "errors_sample": [], <-- empty error array
```

**Key fact:** `n_smiles = 1000` but `n_sampled = 999`. The drop is NOT in
exception handling (n_errors=0). The driver retained 1000 SMILES strings but
the downstream decode produced only 999 valid `SampledMolecule` objects.

---

## 2. Where the drop happens — root cause is the upstream SMILES→SampledMolecule decode

### 2a. Upstream `FlowMol.sample()` has NO error-handling parameter

`/home/hugo/codes/flowa-multistep-reinference/data/FlowMol3/repo/flowmol/models/flowmol.py:490-493`:

```python
@torch.no_grad()
def sample(self, n_atoms: torch.Tensor, n_timesteps: int = None, device="cuda:0",
    stochasticity=None, high_confidence_threshold=None, xt_traj=False, ep_traj=False,
    prior=None, **kwargs):
```

The function signature has NO `return_errors`, `skip_errors`, or `on_invalid`
parameter. It returns `molecules: list[SampledMolecule]` (one per mol) and
**silently drops mols whose SMILES fails RDKit parse** (via the
`build_molecule` path inside `SampledMolecule.__init__`).

**Reuse verdict:** Cannot add `return_errors` without forking upstream. This
is **upstream limitation - cannot fix at framework level** for the CTMC
parameterization.

### 2b. Framework decode path — `sampled_mols_from_smiles`

`/home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/adapters/flowmol3_metrics_upstream.py:205-254`:

```python
def sampled_mols_from_smiles(smiles_list: Sequence[str]) -> list[Any]:
    """Parse a list of SMILES into a list of upstream SampledMolecule.

    Each SMILES goes through the canonical recipe the upstream smoke
    test uses:
        MolFromSmiles -> AddHs -> ETKDGv3 (seed=0xF00D) -> EmbedMolecule
        -> MMFFOptimizeMolecule(maxIters=200) -> from_rdkit_mol
    ...
    """
    ...
    for smi in smiles_list:
        rdkit_mol = Chem.MolFromSmiles(smi)
        if rdkit_mol is None:
            _LOGGER.warning(...)
            continue                       # <-- THE DROP HAPPENS HERE (line 232-233)
        rdkit_mol = Chem.AddHs(rdkit_mol)
        params = Chem.AllChem.ETKDGv3()
        params.randomSeed = 0xF00D
        embed_status = Chem.AllChem.EmbedMolecule(rdkit_mol, params)
        if embed_status != 0:
            _LOGGER.warning(...)
            continue                       # <-- OR HERE (line 244)
        ...
```

The drop is at **line 232-233** (SMILES parse fails for the CTMC valence
artifact) or **line 244** (ETKDGv3 embed fails for the 3D conformer). This
function is **already in the codebase** and already has the warning
infrastructure that records the dropped mol.

### 2c. Caller — `FlowMol3V2Adapter.export_sampled_molecules`

`/home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/adapters/flowmol3_v2_adapter.py:4541-4549`:

```python
try:
    from adaptive_reflow.adapters.flowmol3_metrics_upstream import (
        sampled_mols_from_smiles as _sampled_mols_from_smiles,
    )
    smiles_list = [
        s for s in cached_smiles_batch if isinstance(s, str) and s
    ]
    sampled = _sampled_mols_from_smiles(smiles_list)
except Exception as exc:
    upstream_decode_error = f"{type(exc).__name__}:{exc}"
```

**Reuse verdict:** The call site already uses the right helper. The bug is in
the helper itself (it silently drops invalid SMILES) and the caller does NOT
record which SMILES was dropped.

### 2d. Driver — `_generate_arm` in `tools/wave87_n1000_sweep.py`

`/home/hugo/codes/flowa-multistep-reinference/tools/wave87_n1000_sweep.py:184-251`:

```python
sampled_mols: list[Any] = []
smiles_list: list[str] = []
errors: list[str] = []
t_total = time.perf_counter()
for batch_idx in range(N_BATCHES):
    ...
    try:
        trace = adapter.solve_ode(bundle, cond, seed=int(seed), n_molecules=NFE_BATCH)
    except Exception as exc:
        errors.append(f"batch{batch_idx}:{type(exc).__name__}:{exc}")
        continue
    sampled_batch, metadata = adapter.export_sampled_molecules(trace)
    if metadata.get("marker") not in ("ok", "ok_batch"):
        errors.append(f"batch{batch_idx}:decode_marker={metadata.get('marker')!r}")
        continue
    sampled_mols.extend(sampled_batch)
    ...
    cached_smiles_batch = entry.get("rdkit_mol_smiles_batch") or []
    if cached_smiles_batch:
        smiles_list.extend([s for s in cached_smiles_batch if isinstance(s, str) and s])
```

**Reuse verdict:** The driver has NO `n_sampled - len(smiles_list)` cross-check.
The driver could compute this discrepancy but doesn't.

---

## 3. Reuse opportunities (no new diagnostic code needed)

### REUSE-1: existing disclosure is sufficient — no code change needed

The 1-mol drop is already disclosed in 7 places (all already committed):
- `docs/paper-draft.md:1275` (Tier 3 cells — N=999 caveat inline)
- `docs/paper-draft.md:3192` (Honest caveat — 1 dropped mol)
- `docs/paper-draft.md:3241-3243` (Caveat — sampling error detail)
- `docs/push-ready-summary.md:1375` (Honest caveats #7)
- `docs/audit/wave82-phase3-sweep.md:269, 446`
- `docs/audit/wave87-phase3-sweep.md:155, 345`
- `docs/audit/wave106-c2-fix-summary.md:17, 49, 54` (F-02 fix)

**Commit:** `2a7dc1c` (Wave 106.C fix A.2 F-02: Disclose FlowMol3 baseline arm N=999)

**LOC delta vs new diagnostic code:** **0 LOC** — disclosure is already in place.

### REUSE-2: log the dropped SMILES via the existing `_LOGGER.warning` hook

The function `sampled_mols_from_smiles` already calls:
- `_LOGGER.warning("sampled_mols_from_smiles: RDKit could not parse SMILES %r", smi)` (line 232)
- `_LOGGER.warning("sampled_mols_from_smiles: ETKDGv3 embed failed for %r (status=%d); skipping", smi, int(embed_status))` (line 240)

**To extract the dropped SMILES from the existing logs, no new code is
needed** — just run the driver with `--log-level=DEBUG` and grep for the
warning. The dropped SMILES will be in the warning message verbatim.

**LOC delta vs new diagnostic code:** **0 LOC** — the dropped SMILES is
already in the log output.

### REUSE-3: pass the dropped SMILES to the JSON via existing `errors_sample` field

The JSON schema (`_generate_arm` return) has `errors_sample: errors[:5]` at
line 250 and `n_errors: int(len(errors))` at line 249. The driver appends to
`errors` on batch-level exceptions only (line 214, 220). It does NOT record
per-mol drops from `sampled_mols_from_smiles`.

**Cheapest fix (1 LOC):** capture the dropped SMILES by replacing `sampled =
_sampled_mols_from_smiles(smiles_list)` with a wrapper that records the
delta. But this requires writing new wrapper code — not a "reuse" of
existing code.

**LOC delta vs new diagnostic code:** ~5 LOC to wrap the call + 1 LOC to
append to `errors`. Still cheap, but NOT a pure reuse.

### REUSE-4: compute the drop from cached entries (no driver change)

The driver already caches `entry["rdkit_mol_smiles_batch"]` and writes
`smiles_list[:200]` to the JSON. The batch size is `NFE_BATCH = 100` and
`N_BATCHES = 10` (line 74-77 of `wave87_n1000_sweep.py`). The full SMILES
list has 1000 entries (the `n_smiles` field).

To identify the dropped SMILES **from existing artifacts only**:

1. The JSON file has `smiles_list[:200]` (first 200 of 1000).
2. The v2 adapter's `_native_states[bundle.native_state_digest]` caches
   `rdkit_mol_smiles_batch` per batch (line 3033 of `flowmol3_v2_adapter.py`).

**Cheapest path:** parse the `n_smiles` (1000) - `n_sampled` (999) = 1 delta
from the JSON. The actual dropped SMILES is in the **adapter's
`_native_states` cache** which is in-memory only (not persisted to disk).

**LOC delta vs new diagnostic code:** **0 LOC** for the count; the actual
SMILES string is in-memory only and would need a new persistence hook.

### REUSE-5: pull the dropped SMILES from upstream `SampledMolecule.atom_types` (bypass SMILES entirely)

The upstream `FlowMol.sample()` returns `SampledMolecule` objects with
`atom_types` (numpy array) and `bonds` already populated (line 591-598 of
`flowmol.py`). These objects are constructed BEFORE the SMILES string is
generated — so the molecular graph exists even when the SMILES round-trip
fails.

**Reuse path:** bypass the `rdkit_mol_smiles_batch` → `sampled_mols_from_smiles`
round-trip and consume the upstream `SampledMolecule` directly. The
framework already has the glue for this at
`flowmol3_metrics_upstream.sampled_mol_from_rdkit_mol` (line 200) which
calls `SampledMolecule.from_rdkit_mol(rdkit_mol)`.

But the upstream `SampledMolecule` is **returned by the wrapper driver** at
`tools/upstream_eval.py:813-855` — it reads SMILES, not the actual upstream
sample output. The framework driver does NOT keep the upstream
`SampledMolecule` objects (only SMILES).

**LOC delta vs new diagnostic code:** ~20 LOC to wire upstream
`SampledMolecule` directly (skip SMILES round-trip). This is a medium-size
change.

---

## 4. `--max-attempts` / `--retry-on-error` flag search

Searched `tools/upstream_eval.py`, `tools/wave87_n1000_sweep.py`, and
`adaptive_reflow/adapters/flowmol3_v2_adapter.py` for retry/attempts flags:

```bash
grep -rn "max_attempts\|retry_on_error\|--max-attempts\|--retry\|try.*except"
    tools/upstream_eval.py
    tools/wave87_n1000_sweep.py
    adaptive_reflow/adapters/flowmol3_v2_adapter.py
```

**No retry / max-attempts flag exists** in any of these files.

The framework's restart policy exists at the algorithm layer
(`restart_blend`, `apply_restart_distribution`) — see
`adaptive_reflow/adapters/flowmol3_v2_adapter.py:2213` (`_sample_native_state`
with `restart_seed`). But this is a **per-round scheduler restart**, not a
**per-mol retry on decode failure**.

**Reuse verdict:** No existing flag to reuse for "retry the 1 dropped mol".
A new flag would need to be written — NOT a reuse opportunity.

---

## 5. Library-level alternatives (rdkit / transformers / torchdiffeq etc.)

Searched `pyproject.toml` and `requirements-*.txt` for established libraries
that handle SMILES round-trip with error recovery:

- `rdkit.Chem.MolFromSmiles` (used) — no error recovery API.
- `rdkit.Chem.SanitizeMol` (used) — throws on failure.
- `rdkit.Chem.AllChem.EmbedMolecule` (used) — returns non-zero on failure.

**No established library** in the project's dependency tree provides a
"validate SMILES and retry with different conformer seed" pattern out of the
box. The current approach (log + skip) is the standard.

**Library verdict:** No external library can be reused.

---

## 6. Comparison to vendored external repos

Searched:
- `data/kanzi_upstream/` (protein FM) — N/A, no SMILES round-trip.
- `data/lineageflow_upstream/` (protein FM) — N/A, no SMILES round-trip.
- `data/FlowMol3/repo/flowmol/analysis/molecule_builder.py` — uses
  `SampledMolecule.from_rdkit_mol` which also drops invalid mols silently.

**External verdict:** The upstream FlowMol repo also silently drops
invalid SMILES in `SampledMolecule` constructor. There is NO upstream API
that recovers the dropped mol.

---

## 7. Has any prior wave already documented why 1 mol drops?

**Yes — 7+ places (full list in REUSE-1 above).** Key documents:

1. `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave87-phase3-sweep.md:155`
   states: "SMILES failed RDKit parsing — same CTMC valence artifact as
   Wave 82".

2. `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave87-phase4-final.md:370`
   states: "1 mol dropped from baseline due to a CTMC valence artifact
   (`Explicit valence for atom # 5 Cl, 2, is greater than permitted`).
   Framework arm produced 1000/1000 valid mols because the Gaussian prior
   perturbation shifts samples away from this CTMC failure mode. This is a
   **single-mol drop**, well within statistical noise."

3. `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave106-a-2-audit.md:125-158`
   is the canonical Wave 106.A.2 audit that established the disclosure.

**Conclusion:** Root cause is documented as a CTMC valence artifact with
specific SMILES structure (Cl valence violation). No new diagnostic code
needed.

---

## 8. Does `n_errors` equal 1 or 0?

`n_errors = 0` for baseline arm. The drop is NOT from exceptions — it's
from the SMILES→Mol round-trip silently skipping the invalid mol. This is
why the JSON `errors_sample` is empty even though `n_sampled=999`.

**Implication:** No retry-on-error flag would help here, because the driver
never sees an exception. The drop is purely a graceful-degradation behavior
in `sampled_mols_from_smiles`.

---

## 9. Structural diagnosis: upstream limitation

The 1-mol drop is caused by **CTMC parameterization in `FlowMol.sample`**
producing SMILES strings that violate RDKit valence rules ~0.1% of the time.
The framework arm's prior perturbation shifts samples away from this CTMC
failure mode (Wave 87 honest caveat #7), achieving 1000/1000.

This is **upstream limitation - cannot fix at framework level** without:
- Forking `FlowMol.sample` to add a `return_errors` parameter (large change).
- Adding a post-hoc valency-correction step (would alter molecular identity).
- Running `N > 1000` and oversampling (changes the experimental design).

---

## 10. Recommended action (cheapest path)

**Recommendation:** **No code change** — the disclosure is already in place
(Wave 106.A.2 F-02, commit `2a7dc1c`).

If the Wave 101 fix-layer plan requires ACTUALLY recovering the mol (vs.
disclosing the drop), the cheapest path is:

1. Add ~5 LOC wrapper around `sampled_mols_from_smiles` in
   `flowmol3_v2_adapter.py:4549` to record dropped SMILES.
2. Persist to `errors_sample` field in the JSON output (already wired).
3. Add the dropped SMILES to the existing audit doc disclosure.

**Total LOC delta: ~5 LOC** (vs. ~50 LOC for a new diagnostic driver).

---

## Files audited

- `/home/hugo/codes/flowa-multistep-reinference/data/FlowMol3/repo/flowmol/models/flowmol.py` (upstream sample signature)
- `/home/hugo/codes/flowa-multistep-reinference/data/FlowMol3/repo/flowmol/analysis/molecule_builder.py` (SampledMolecule)
- `/home/hugo/codes/flowa-multistep-reinference/data/FlowMol3/repo/flowmol/analysis/metrics.py` (SampleAnalyzer.analyze)
- `/home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/adapters/flowmol3_v2_adapter.py:4437-4747` (export_sampled_molecules)
- `/home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/adapters/flowmol3.py` (v1 adapter)
- `/home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/adapters/flowmol3_metrics_upstream.py:205-254` (sampled_mols_from_smiles)
- `/home/hugo/codes/flowa-multistep-reinference/tools/upstream_eval.py:813-855` (run_flowmol3_upstream_eval)
- `/home/hugo/codes/flowa-multistep-reinference/tools/wave87_n1000_sweep.py:146-279` (_generate_arm)
- `/home/hugo/codes/flowa-multistep-reinference/verification_outputs/flowmol3_n1000_baseline_q4_2026.json` (JSON evidence)
- `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave82-phase3-sweep.md:269,446`
- `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave87-phase3-sweep.md:155,345`
- `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave87-phase4-final.md:370`
- `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave106-a-2-audit.md:125-158`
- `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave106-c2-fix-summary.md`
- `/home/hugo/codes/flowa-multistep-reinference/docs/paper-draft.md:1275,3192,3241-3243`
- `/home/hugo/codes/flowa-multistep-reinference/docs/push-ready-summary.md:1375`

## External libs audited (in pyproject.toml)

- `rdkit` (used) — no error-recovery API beyond `MolFromSmiles` returning None.
- `torch` (used) — no FM-specific error recovery.
- No other established library (transformers, diffusers, mdtraj, biotite,
  torchdiffeq) provides SMILES round-trip with retry. N/A for FlowMol3.

## External repos audited (vendored)

- `data/kanzi_upstream/` — N/A (protein FM, no SMILES).
- `data/lineageflow_upstream/` — N/A (protein FM, no SMILES).
- `data/FlowMol3/repo/flowmol/` — `sample()` has no `return_errors`; this is
  upstream limitation.

## Reuse opportunities count

**5** — see REUSE-1 through REUSE-5 above. REUSE-1 (existing disclosure) and
REUSE-2 (existing log warnings) require **0 LOC**. REUSE-3 / REUSE-4 require
~5 LOC each. REUSE-5 requires ~20 LOC.
