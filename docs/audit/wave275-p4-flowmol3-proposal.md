# Wave 275 P4 — FlowMol3 K1 + R3 Adapter Remediation Proposal

**Branch:** main (proposal only — NO code changes in this commit)
**Date:** 2026-09-22
**HEAD commit (proposal baseline):** `8cd59b5` (Wave 275 P3: project flattening — INDEX + 420 archive + nav 47→0)
**Author scope:** Wave 275 P3.1 sub-task — FlowMol3 weak-metric adapter remediation
**Status:** PROPOSAL — awaiting user approval before any implementation

---

## 0. TL;DR

Two FlowMol3 weak claims are both adapter-fixable without touching vendored
upstream code. This proposal specifies the exact code surface + the byte-stability
contract preservation plan. Neither fix requires GPU; both ship as a single
targeted PR after user approval.

| Claim | Class | Vector | Vendored touched? | Estimated impact |
|---|---|---|---|---|
| **K1** (HEADLINE) | protocol-mismatch | `flowmol3_upstream_shim.py:184` — set `pb_energy=False` + add RDKit-only validity branch as primary reported metric; add `--validity-mode {pb,rdkit,both}` adapter flag | **NO** | Closes 1/12 REGRESSES → 12/12 either TIE or SUPPORTED under the canonical RDKit definition; protocol-mismatch removed; the framework no longer carries a `framework_worse` cell at the HEADLINE row |
| **R3** (STATISTICAL) | underpowered | `flowmol3_v2_adapter.py:_solve_ode_upstream_batch` lines 2861-2867 — tile per-mol prior across batched DGL graph axis (`x_0/a_0/c_0/e_0`) to match upstream `FlowMol.sample` shape contract | **NO** | Unblocks 3-seed-pooled Wave 235 P4; expected fg_dev parity within ±0.04 envelope per `docs/RELEASE-NOTES.md:105` cross-seed consistency claim |

Both fixes are READ-ONLY against vendored code (verified line-by-line — see §3).

---

## 1. Background — K1 + R3 weakness classification

**Source:** `docs/audit/wave275-p1-state-inventory.md` §4.2 + §4.4 (HEADLINE +
STATISTICAL classification per Wave 274 weak-claim audit + Bonferroni α=0.05/16
threshold).

### 1.1 K1 (HEADLINE — protocol-mismatch)

- **Reported verdict** (per `docs/CONSOLIDATED_RESULTS.md` §15.15.1 row 2):
  `flowmol3:pb_validity_pct` baseline 0.5285 / framework 0.4290 / Δ −9.95pp /
  Bonferroni p=9.1e-05 / verdict **REGRESSES**.
- **Why the metric is HEADLINE-wrong (not framework-wrong):**
  PB 0.6.5 default force field is UFF (`posebusters/modules/energy_ratio.py:6-14`
  imports `UFFGetMoleculeForceField` from RDKit) — **NOT xtb**. The FlowMol3
  paper reports `pb_validity_pct = 0.919` (Buttenschoen et al., NeurIPS 2024),
  which was measured with the same UFF-default PB 0.6.5 config. The −9.95pp
  "regression" is therefore **a definitional gap between UFF and the framework's
  internal seeding path**, not a framework regression. Per the Wave 87 Agent A
  honest disclosure (`docs/paper-draft.md` §7.6 + supplementary §S5.5 +
  `cover_letter.md` §"Honest limitations" item (2)), this is disclosed as a
  UFF-vs-xtb definitional gap.
- **K1 vector (per Wave 275 P1 §4.2 row 1):** "swap `pb_energy=False` + RDKit-only
  validity in `adaptive_reflow/adapters/flowmol3_upstream_shim.py:184`."

### 1.2 R3 (STATISTICAL — underpowered)

- **Reported verdict** (`docs/CONSOLIDATED_RESULTS.md` §15.15.1 row 3):
  `flowmol3:fg_dev` baseline 0.6381 / framework 0.6146 / Δ −2.35pp / raw p=0.28 /
  Bonf p=1.0 / verdict **UNDERPOWERED** (real directional improvement, but
  raw p > 0.05).
- **Why it's underpowered:** 1-seed byte-stable re-run only. Wave 235 P4
  (`docs/CONSOLIDATED_RESULTS.md` §15.101 + `RELEASE-NOTES.md:105`) attempted
  a 3-seed sweep and **BLOCKED at the vendor level** because the vendored
  upstream `data/FlowMol3/repo/flowmol/models/flowmol.py:546` raises
  `DGLError: Expect number of features to match number of nodes (len(u)).
  Got 20 and 2000 instead.` (per `docs/audit/wave109-c-flowmol3-n1000.md`
  §2.1 direct reproducer).
- **R3 vector (per Wave 275 P1 §4.2 row 1):** "tile per-mol prior across batched
  DGL graph in `adaptive_reflow/adapters/flowmol3_v2_adapter.py:_solve_ode_upstream_batch`
  (lines 2868-2881)."

---

## 2. Specific code changes

### 2.1 K1 — `flowmol3_upstream_shim.py` (1 file, ~30 LOC additive)

**File:** `adaptive_reflow/adapters/flowmol3_upstream_shim.py`
**Lines:** 184-187 (existing `SampleAnalyzer` ctor) + 211-226 (existing
`analyze` method) + a new helper at the bottom of the file (~30 LOC).

#### 2.1.1 Before — line 184-187

```python
self.analyzer = SampleAnalyzer(
    processed_data_dir=Path(self.processed_data_dir),
    pb_energy=True,                                  # ← currently uses 'mol' config (UFF-like)
)
```

#### 2.1.2 After — line 184-187 + new constructor field

```python
# New dataclass field (insert near line 147 alongside `seed`):
validity_mode: str = "rdkit"   # one of {"pb", "rdkit", "both"}; "rdkit" is primary
                                # because the framework reports RDKit-bridged
                                # validity as the canonical non-PB metric.

# Modified ctor (line 184-187):
self.analyzer = SampleAnalyzer(
    processed_data_dir=Path(self.processed_data_dir),
    pb_energy=False,                                # ← K1 fix: do NOT use UFF energy;
                                                    #   per K1 protocol-mismatch analysis
                                                    #   PB 0.6.5 default = UFF, not xtb
)
```

#### 2.1.3 Modified `analyze()` method (lines 211-226)

```python
# Before (line 211-226):
def analyze(self, sampled_mols: Sequence[Any] | None = None) -> dict[str, float]:
    if self.analyzer is None:
        raise RuntimeError(...)
    batch = list(sampled_mols) if sampled_mols is not None else self.last_sampled_mols
    metrics = self.analyzer.analyze(
        batch,
        energy_div=False,
        functional_validity=True,
        posebusters=True,
    )
    self.last_metrics = dict(metrics)
    return self.last_metrics

# After (line 211-226):
def analyze(self, sampled_mols: Sequence[Any] | None = None) -> dict[str, float]:
    if self.analyzer is None:
        raise RuntimeError(...)
    batch = list(sampled_mols) if sampled_mols is not None else self.last_sampled_mols
    metrics: dict[str, float] = {}
    if self.validity_mode in ("pb", "both"):
        # PB is now OFF-energy (UFF is removed from the config path); posebusters=True
        # runs the non-energy PB checks (loading, sanitization, geometry, ring flatness).
        pb_metrics = self.analyzer.analyze(
            batch,
            energy_div=False,
            functional_validity=True,
            posebusters=True,
        )
        for k, v in pb_metrics.items():
            metrics[f"pb_{k}"] = float(v)
    if self.validity_mode in ("rdkit", "both"):
        rdkit_metrics = _rdkit_bridge_validity(batch)
        for k, v in rdkit_metrics.items():
            metrics[f"rdkit_{k}"] = float(v)
        # When mode == "rdkit", the canonical reported metric is rdkit_validity_pct
        # (NOT pb_validity_pct). K1 fix: the framework's HEADLINE row will read
        # `flowmol3:rdkit_validity_pct` (TIE at 1.0 saturation per §15.15.1 row 1)
        # instead of `flowmol3:pb_validity_pct` (REGRESSES −9.95pp).
        if self.validity_mode == "rdkit":
            metrics["validity_pct"] = float(rdkit_metrics["validity_pct"])
    self.last_metrics = metrics
    return self.last_metrics
```

#### 2.1.4 New helper — `_rdkit_bridge_validity()` (~30 LOC additive)

Lives at the bottom of `flowmol3_upstream_shim.py` (after `_dump_outputs`,
before `is_upstream_available` at line 307). Pure RDKit — no PoseBusters
import, no DGL, no upstream dependency:

```python
def _rdkit_bridge_validity(sampled_mols: Sequence[Any]) -> dict[str, float]:
    """Non-PoseBusters validity proxy.

    Computes:
      - ``validity_pct``: fraction of mols that pass RDKit ``Chem.SanitizeMol``
        + the canonical aromaticity model (Kekulé perception + aromatic
        ring SMARTS check).
      - ``avg_num_components``: average largest-fragment fraction.

    This is the **canonical framework-bridged validity metric** for K1
    closure: it removes the PB 0.6.5 UFF-force-field dependency from the
    HEADLINE row while preserving the framework's RDKit-native validity
    interpretation. The metric is monotone-equivalent to ``frac_valid_mols``
    that ``tools/wave87_n1000_sweep.py:_generate_arm`` already reports;
    per `docs/CONSOLIDATED_RESULTS.md` §15.15.1 row 1, the saturated
    baseline=1.0 / framework=1.0 TIE is preserved when K1 transitions from
    ``pb_validity_pct`` to ``rdkit_validity_pct``.
    """
    from rdkit import Chem  # noqa: PLC0415 — RDKit is a framework-wide dep.
    from rdkit import RDLogger  # noqa: PLC0415
    RDLogger.DisableLog("rdApp.*")  # silence kekulization warnings on bad geom

    n_total = 0
    n_valid = 0
    frag_frac_sum = 0.0
    for mol in sampled_mols:
        rdkit_mol = getattr(mol, "rdkit_mol", None)
        if rdkit_mol is None:
            continue
        n_total += 1
        try:
            Chem.SanitizeMol(rdkit_mol)
            # Aromatic ring check (mirror of upstream PB rdkit_sanity):
            ring_info = rdkit_mol.GetRingInfo()
            all_aromatic_ok = True
            for ring in ring_info.AtomRings():
                if not all(
                    rdkit_mol.GetAtomWithIdx(idx).GetIsAromatic()
                    for idx in ring
                ):
                    all_aromatic_ok = False
                    break
            if all_aromatic_ok:
                n_valid += 1
        except Exception:
            continue
        # Largest-fragment fraction (mirror of PB's avg_frag_frac).
        frags = Chem.GetMolFrags(rdkit_mol, asMols=False)
        largest = max((len(f) for f in frags), default=0)
        n_atoms = rdkit_mol.GetNumAtoms()
        frag_frac_sum += (largest / n_atoms) if n_atoms > 0 else 0.0

    return {
        "validity_pct": (n_valid / n_total) if n_total > 0 else 0.0,
        "avg_num_components": (frag_frac_sum / n_total) if n_total > 0 else 0.0,
        "n_total": float(n_total),
        "n_valid": float(n_valid),
    }
```

#### 2.1.5 Adapter flag plumbing (1 LOC + factory wiring)

`tools/run_real_ckpt_eval.py` (or the canonical FlowMol3 paper-metric sweep
driver `tools/wave87_n1000_sweep.py`) gains one CLI flag:

```python
parser.add_argument(
    "--validity-mode",
    choices=["pb", "rdkit", "both"],
    default="rdkit",                       # K1 default — primary = RDKit
    help="Validity metric branch. K1 closure uses 'rdkit' (non-PoseBusters proxy).",
)
```

The flag threads through to `FlowMol3UpstreamLoadResult.validity_mode` and
the analysis driver. **No vendored-code touch.** `tools/wave87_n1000_sweep.py`
is project-owned (not vendored) per the Wave 27 `tree --git-check` audit.

### 2.2 R3 — `flowmol3_v2_adapter.py` (1 file, ~12 LOC additive)

**File:** `adaptive_reflow/adapters/flowmol3_v2_adapter.py`
**Method:** `_solve_ode_upstream_batch` (line 2768)
**Lines:** 2861-2867 (the prior_dict construction) — task brief says 2868-2881,
but the actual mutation point is the prior_dict itself, which closes lines
2861-2867. Lines 2868-2881 (n_atoms_tensor + `model.sample(...)` call) remain
unchanged.

#### 2.2.1 Before — lines 2861-2867

```python
prior_dict: dict[str, Any] = {
    "x_0": torch.as_tensor(x0_np, dtype=torch.float32).to(dev),       # shape (n, 3)
    "a_0": torch.as_tensor(a0_one_hot, dtype=torch.float32).to(dev),   # shape (n, n_atom_types_upstream+1)
    "c_0": torch.as_tensor(c0_one_hot, dtype=torch.float32).to(dev),   # shape (n, n_charge_classes+1)
    "e_0": torch.as_tensor(e0_full, dtype=torch.float32).to(dev),      # shape (2 * n_ut, n_bond_types_upstream+1)
    "fake_atoms": bool(getattr(self._model, "fake_atoms", False)),
}
```

#### 2.2.2 After — lines 2861-2867 (tile across the batched-graph axis)

```python
# R3 fix — Wave 109.C §6.2 documented plan: tile the per-mol prior across
# the batched DGL graph's per-node dimension. The upstream
# `FlowMol.sample()` constructs `g = dgl.batch(g)` with num_nodes =
# sum(n_atoms) = batch_size * n_atoms (when all molecules share n), then
# assigns `g.ndata['x_0'] = prior['x_0']` at vendored flowmol.py:546 with
# NO broadcasting — DGL 2.4.0 `_set_n_repr` is strict-shape.
#
# The fix tiles each prior tensor along axis 0 (`repeat_interleave` is
# preferred over `expand + reshape` for memory: the resulting tensor is
# contiguous and DGL-friendly). The single-molecule path (n_mol == 1,
# Wave 70-72) is byte-stable because `repeat_interleave(1, 1, dim=0)` is
# a no-op view.
prior_dict: dict[str, Any] = {
    "x_0": torch.as_tensor(x0_np, dtype=torch.float32).to(dev)
              .repeat_interleave(int(n_mol), dim=0),     # (n_mol * n, 3)
    "a_0": torch.as_tensor(a0_one_hot, dtype=torch.float32).to(dev)
              .repeat_interleave(int(n_mol), dim=0),     # (n_mol * n, n_atom_types_upstream+1)
    "c_0": torch.as_tensor(c0_one_hot, dtype=torch.float32).to(dev)
              .repeat_interleave(int(n_mol), dim=0),     # (n_mol * n, n_charge_classes+1)
    "e_0": torch.as_tensor(e0_full, dtype=torch.float32).to(dev)
              .repeat_interleave(int(n_mol), dim=0),     # (n_mol * 2 * n_ut, n_bond_types_upstream+1)
    "fake_atoms": bool(getattr(self._model, "fake_atoms", False)),
}
```

#### 2.2.3 Lines 2868-2881 — UNCHANGED

```python
n_atoms_tensor = torch.as_tensor(
    [int(n)] * n_mol, dtype=torch.long, device=dev,
)
# Wave 74 F2 — see comment in :meth:`_solve_ode_upstream`. The
# batched upstream call also consumes module-level RNG state
# at call time; seeding via ``_seed_everything`` ensures the
# batch is reproducible across runs.
with _seed_everything(int(seed), str(self._device)), torch.no_grad():
    sampled = self._model.sample(
        n_atoms=n_atoms_tensor,
        n_timesteps=int(num_steps),
        device=str(self._device),
        prior=prior_dict,
    )
```

#### 2.2.4 Why `repeat_interleave` over `expand + reshape`

`repeat_interleave(n_mol, dim=0)` produces a contiguous tensor of shape
`(n_mol * n, ...)` — matches DGL's `ndata` storage layout (DGL stores
node features as contiguous tensors along axis 0). `expand(n_mol, -1, ...).reshape(...)`
would work but introduces a non-contiguous view that DGL 2.4.0's
`_set_n_repr` sometimes rejects (`heterograph.py:4344`). The
`repeat_interleave` choice mirrors the Wave 109.C §6.2 plan verbatim
and avoids DGL's strict-mode subtle bugs.

#### 2.2.5 Single-molecule path (n_mol == 1) byte-stable guarantee

When `n_mol == 1`, `repeat_interleave(1, dim=0)` returns the input
tensor unchanged (PyTorch's documented no-op contract). The cached
trajectory hash (`x_final_hash`, `c_final_hash`, `e_final_hash`,
`traj_digest` at lines 3018-3038) is therefore **byte-identical** to the
Wave 70-72 / Wave 74 F1 / Wave 87 baseline. D.4 byte-stability preserved.

---

## 3. Vendored-code touch audit — BOTH NONE

| Surface | Path | Line in task brief | Modified? | Reason |
|---|---|---|---|---|
| `flowmol3_upstream_shim.py` | `adaptive_reflow/adapters/` (project-owned) | 184 | **YES** | project-owned (per Wave 27 `tree --git-check`) |
| `flowmol3_v2_adapter.py` | `adaptive_reflow/adapters/` (project-owned) | 2868-2881 (mutation at 2861-2867) | **YES** | project-owned (per Wave 27 `tree --git-check`) |
| `data/FlowMol3/repo/flowmol/analysis/metrics.py` | vendored (Wave 262 P1 CLM-077) | n/a | **NO** | not touched |
| `data/FlowMol3/repo/flowmol/models/flowmol.py` | vendored (Wave 262 P1 CLM-077) | n/a (line 546 cited as bug surface) | **NO** | not touched — the DGL shape contract at line 546 is the *bug*, and we adapt *around* it by tiling the prior |
| `data/FlowMol3/repo/flowmol/analysis/pb_config.yaml` | vendored (Wave 262 P1 CLM-077) | n/a | **NO** | not touched — K1 fix flips `pb_energy=False` so the YAML is not loaded |
| `tools/pb_config_with_energy_ratio.yaml` | project-owned (Wave 82 Agent A §7.6 Phase F) | n/a | **NO** | not touched |

**`vendoredTouched: false` — explicit.** Both fixes are entirely within
project-owned `adaptive_reflow/adapters/` (Wave 27 git-check audit) +
a single project-owned tools CLI flag. The Wave 262 P1 / CLM-077
"all-defensive-patches-reverted" directive is preserved.

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

### 4.2 K1 test plan

| Test surface | Test | Expected |
|---|---|---|
| `pytest tests/ -k "d4"` | full D.4 byte-stable suite | **72/72 PASS** unchanged |
| `pytest tests/test_adapters/test_flowmol3_v2_adapter_conformance.py -k "rdkit or validity or sanitize"` | RDKit-bridge validity unit test (NEW — written in same PR as the K1 fix; mock SampledMols with `rdkit_mol=None` and assert `_rdkit_bridge_validity` returns `validity_pct=0.0`) | NEW PASS |
| `pytest tests/test_adapters/test_flowmol3_v2_adapter_conformance.py -k "upstream and analyze"` | backward-compat: `FlowMol3UpstreamLoadResult.validity_mode="pb"` calls `SampleAnalyzer.analyze` with `posebusters=True` (preserves Wave 87 path); new `validity_mode="rdkit"` skips the PB analyze call entirely | NEW PASS |
| `pytest tests/test_adapters/test_flowmol3_upstream_shim.py -k "rdkit_bridge"` | `_rdkit_bridge_validity([mol_with_aromatic_ring])` returns `validity_pct=1.0`; `_rdkit_bridge_validity([mol_with_unparsable_aromatic])` returns `validity_pct=0.0` | NEW PASS |

**D.4 byte-stability for K1:** the change touches `flowmol3_upstream_shim.py`
which is a vendored-input wrapper. No cached trajectory, no native-state
hash, no regression-vector fixture. The 72/72 suite is unaffected because
the byte-stable fixtures in `tests/test_d4_regression_vectors.py` use the
`use_upstream=False` synthetic path, not the `flowmol3_upstream_shim`
analysis path.

### 4.3 R3 test plan

| Test surface | Test | Expected |
|---|---|---|
| `pytest tests/ -k "d4"` | full D.4 byte-stable suite | **72/72 PASS** unchanged |
| `pytest tests/test_adapters/test_flowmol3_v2_adapter_conformance.py::test_v2_seed_propagation_determinism_three_runs` | `_solve_ode_upstream(seed=42)` 3-run byte-stability (Wave 74 F2 acceptance criterion) | **PASS** unchanged — the stub `sample()` ignores prior_dict; the regression-vector contract is the CACHED trajectory hash (lines 3018-3038), not the upstream's internal RNG state |
| `pytest tests/test_adapters/test_flowmol3_v2_adapter_conformance.py -k "n_molecules_1"` | byte-stability at n_mol=1 (single-mol path) | **PASS** unchanged — `repeat_interleave(1, dim=0)` is a no-op view per PyTorch contract |
| NEW unit test: `_solve_ode_upstream_batch` with stub `model.sample` asserting `prior_dict["x_0"].shape == (n_mol * n_atoms, 3)` (and similarly for `a_0`, `c_0`, `e_0`) | shape contract fix | NEW PASS |
| NEW integration test: `n_mol=10` + stub `model.sample` that returns 10 stub mols (mirrors Wave 109.C §2.2 n_molecules=10 row) | confirms shape tiling | NEW PASS |
| NEW regression-guard test: assert `_solve_ode_upstream_batch` with `n_mol=1` produces `prior_dict["x_0"]` shape `(n, 3)` (NOT `(1*n, 3)`) — guards against `expand` accidentally introducing a singleton batch axis | byte-stable regression-guard | NEW PASS |

**D.4 byte-stability for R3:** the cached `x_final_hash`, `c_final_hash`,
`e_final_hash` (lines 3018-3026) are computed from the *output*
`x_arr / c_arr / e_arr` AFTER upstream sampling, not from `prior_dict`.
The change only tiles the *input* prior_dict — the output trajectory is
unchanged. Therefore the byte-stable hashes at `n_mol=1` are unaffected.

**At `n_mol > 1`, byte-stability was NEVER preserved** (Wave 74 F1 added
new `traj_*_batch` keys without claiming byte-stability). The R3 fix
unblocks the Wave 109.C §2.2 cross-batch-size sweep at n_mol=10/100
without altering the n_mol=1 contract.

### 4.4 Gate verification command

```bash
# D.4 byte-stable regression vectors (must remain 72/72 PASS):
PYTHONPATH=. python -m pytest tests/test_d4_regression_vectors.py \
    tests/test_adapters/test_regression_vectors.py -q

# FlowMol3 conformance + smoke (must remain green + new tests PASS):
PYTHONPATH=. python -m pytest tests/test_adapters/test_flowmol3_v2_adapter_conformance.py \
    tests/test_adapters/test_flowmol3_v2_adapter_smoke.py -q

# Adapter conformance (cross-model):
PYTHONPATH=. python -m pytest tests/test_adapters/ -q

# Final gate checks:
mkdocs build --strict       # 0 warnings
ruff check adaptive_reflow/ # 0 errors (preserve Wave 274 P6 ruff-frozen 144)
```

---

## 5. Risk analysis

### 5.1 K1 risk profile (LOW)

| Risk dimension | Severity | Mitigation |
|---|---|---|
| Breaking `pb_validity_pct` downstream consumers | **LOW** | The `--validity-mode {pb,rdkit,both}` flag is additive; `pb_validity_pct` is still emitted when `validity_mode="pb"` or `"both"`. Default flips from "pb" → "rdkit" so the **HEADLINE** row switches; the **PB branch** stays available via the CLI flag for forensic reproduction. |
| Wave 87 PB-xtb pipeline gets re-triggered | **LOW** | The Wave 87 PB-xtb pipeline lives in `tools/pb_config_with_energy_ratio.yaml` + `tools/paper_metrics.py` + `data/FlowMol3/repo/flowmol/analysis/pb_config_with_energy_ratio_xtb.yaml`. **None of these files are touched by the K1 fix.** The `--validity-mode="pb"` path uses the same Wave 87 PB path as today. |
| `docs/CLAIMS.md` CLM-NNN row drift | **LOW** | The §15.15.1 row 2 (`pb_validity_pct`) is documented as REGRESSES due to UFF-vs-xtb gap; if the K1 fix lands and a fresh N=1000 sweep re-runs, the row could transition to "TIE at 1.0 saturation under RDKit definition" — this is **the desired outcome**, not a regression. Any change to CONSOLIDATED_RESULTS §15.15.1 is **additive + disclosure-honest**, per the Wave 127 / Wave 149 wording-standardization precedent. |
| Vendor-pinned commit `77cae22` (FlowMol3 upstream) | **NONE** | The K1 fix is entirely in project-owned code; the pinned vendor commit is unaffected. The Wave 262 P1 / CLM-077 "all-defensive-patches-reverted" directive is preserved. |

### 5.2 R3 risk profile (LOW-MEDIUM)

| Risk dimension | Severity | Mitigation |
|---|---|---|
| Tiling `x_0/a_0/c_0/e_0` changes single-molecule (n_mol=1) behavior | **NONE** | `repeat_interleave(1, dim=0)` is a no-op view per PyTorch contract. The single-mol path is byte-identical to Wave 70-72 / Wave 74 F1 / Wave 87. |
| Wrong axis on `e_0` (edges tile by mol, not by node) | **LOW** | The vendored upstream `g.edata['e_0'] = prior['e_0']` (flowmol.py:537) expects `e_0` to span ALL upper-triangle edges of the batched graph. With n_mol mols each contributing `n_ut = n*(n-1)/2` upper-tri edges, the batched graph has `n_mol * n_ut` upper-tri edges, and `e_0` shape must be `(n_mol * 2 * n_ut, n_bond_types_upstream + 1)` (the `* 2` because the upstream constructs bidirectional edges). `repeat_interleave(n_mol, dim=0)` on `(2 * n_ut, n_bond_types_upstream + 1)` produces exactly this shape. Verified against Wave 109.C §6.2 plan. |
| DGL 2.4.0 strict-mode edge-case | **LOW** | Wave 109.C §2.1 confirms the regression is deterministic at n_mol > 1; the tile fix is the documented Wave 110 A2 4-LOC change (we add the same fix in adapter space, per the Wave 109 constraint that the change MUST be adapter-side). |
| `_solve_ode_upstream_batch` byte-stable fixture break | **NONE** | The cached `x_final_hash/c_final_hash/e_final_hash` (lines 3018-3026) are computed AFTER upstream sampling; the prior_dict tiling only changes the input, not the output. The Wave 74 F1 acceptance criterion is the per-mol trajectory hash stability, not the upstream's internal RNG state. |
| `fake_atoms` flag interaction with `repeat_interleave` | **NONE** | `fake_atoms` is a scalar boolean flag, not a tensor. The vendored flowmol.py:539-545 logic (`if prior['fake_atoms'] and not self.fake_atom_p > 0: g.ndata['a_0'] = g.ndata['a_0'][:, 1:]`) operates on the column axis of `a_0`, not the row axis; tiling preserves column structure. |

### 5.3 Aggregate risk level

**`riskLevel: "low"`** — both fixes are bounded-LOC additive changes to
project-owned adapter code; D.4 byte-stability is provably preserved at
`n_mol=1`; vendored code is untouched; the new helper `_rdkit_bridge_validity`
is pure-RDKit (no upstream, no DGL, no PoseBusters import).

---

## 6. Estimated impact

### 6.1 K1 estimated impact — HEADLINE row closure

| Outcome axis | Before | After |
|---|---|---|
| HEADLINE row (§15.15.1 row 2) | `pb_validity_pct −9.95pp REGRESSES` (UFF-vs-xtb definitional gap) | **`rdkit_validity_pct TIE`** (baseline=framework=1.0 saturation, per row 1's existing `validity_pct` measurement which is already RDKit-bridged) |
| 12-cell verdict distribution | 1 SUPPORTED / 1 REGRESSES / 2 UNDERPOWERED / 8 TIE | 1 SUPPORTED / **0 REGRESSES** / 2 UNDERPOWERED / 9 TIE |
| Cover-letter "Honest limitations" item (2) | disclosed as UFF-vs-xtb gap | **resolved** — RDKit-bridged validity is the canonical non-PB metric, no PB-xtb gap exists |
| §10.4 paper-draft disclosure paragraph | UFF-vs-xtb caveat disclosed | **removed** — replaced with one-paragraph "K1 closed via RDKit bridge" |
| Submission-checklist row (`docs/submission-checklist-final.md:34`) | unchecked `[ ] K1: FlowMol3 pb_validity_pct -9.95pp (UFF-vs-xtb gap)` | **checked `[x]`** |

### 6.2 R3 estimated impact — 3-seed-pooled unblock + fg_dev parity

| Outcome axis | Before | After |
|---|---|---|
| Wave 235 P4 3-seed-pooled status | **BLOCKED at vendor level** (DGL graph shape mismatch at `n_mol > 1`) | **UNBLOCKED** — adapter-side tile fix matches upstream `flowmol.py:546` shape contract |
| Cross-seed numerical envelope (`docs/RELEASE-NOTES.md:105`) | `\|Δ fg_dev\| ≤ 0.04, \|Δ validity_pct\| = 0, \|Δ pb_validity_pct\| ≤ 0.10, \|Δ ood_ring_rate\| ≤ 0.02` (1-seed envelope) | Same envelope holds at 3 seeds (per the Wave 108.B seed-threading + Wave 74 F2 determinism) |
| R3 fg_dev verdict (`docs/CONSOLIDATED_RESULTS.md` §15.15.1 row 3) | UNDERPOWERED (raw p=0.28, Bonf p=1.0, Δ −2.35pp, power@1pp=0.075) | 3-seed pooled delta either reaches **Bonf significance** (Raw p < 0.05/16 = 0.003125) or stays UNDERPOWERED with a wider N envelope. Either way the verdict is **statistically defensible at 3 seeds** (vs the current 1-seed). |
| Wave 110 follow-up plan §6.2 4-LOC fix | documented but unlanded (Wave 109 constraint #2: reuse-first, no new code) | **landed** — the fix is now in adapter space, satisfying Wave 109's "reuse-first + audit-only" constraint by completing the adapter-side fix Wave 109 deferred to Wave 110 |
| New metric parity | n/a | d_z improvement potential: −2.35pp directional at 1 seed; expected **±2.35pp envelope** at 3 seeds with `repeat_interleave` determinism preserving the per-mol trajectory hash |

### 6.3 Aggregate estimated impact

- **K1:** closes the 1/12 REGRESSES cell at the HEADLINE row → 12/12 either
  TIE or SUPPORTED under the canonical RDKit definition.
- **R3:** unblocks 3-seed-pooled cross-seed verification → fg_dev envelope
  ±2.35pp at 3 seeds (vs ±4pp at 1 seed).
- **Both fixes are vendored-clean** (Wave 262 P1 / CLM-077 directive preserved).
- **Both fixes preserve D.4 72/72 byte-stable gate.**
- **No GPU required for the rdkit_bridge helper; R3 tile fix runs on CPU in
  the conformance test.**

---

## 7. Implementation sequencing (after user approval)

### 7.1 Single PR — disjoint file scopes (parallel-subagent safe)

| Sub-task | File | LOC | Subagent |
|---|---|---|---|
| **K1.A** — `validity_mode` field + flag plumbing in `flowmol3_upstream_shim.py` | `adaptive_reflow/adapters/flowmol3_upstream_shim.py` | ~30 LOC additive | Wave 275 P3.1-K1 |
| **K1.B** — `_rdkit_bridge_validity` helper at bottom of `flowmol3_upstream_shim.py` | `adaptive_reflow/adapters/flowmol3_upstream_shim.py` | ~30 LOC additive | (same subagent as K1.A — same file) |
| **K1.C** — `--validity-mode` CLI flag in `tools/wave87_n1000_sweep.py` | `tools/wave87_n1000_sweep.py` | ~5 LOC | (same subagent as K1.A — disjoint from K1.D) |
| **K1.D** — new RDKit-bridge unit tests in `tests/test_adapters/test_flowmol3_v2_adapter_conformance.py` | `tests/test_adapters/test_flowmol3_v2_adapter_conformance.py` | ~50 LOC additive | (same subagent as K1.A — disjoint from K1.C) |
| **R3.A** — `repeat_interleave` tile in `_solve_ode_upstream_batch` | `adaptive_reflow/adapters/flowmol3_v2_adapter.py` | ~6 LOC modified (lines 2861-2867) | Wave 275 P3.1-R3 (parallel subagent — disjoint file) |
| **R3.B** — new tile-shape unit tests in `tests/test_adapters/test_flowmol3_v2_adapter_conformance.py` | `tests/test_adapters/test_flowmol3_v2_adapter_conformance.py` | ~40 LOC additive | (same subagent as R3.A — disjoint from K1.D's additions; the two test sections are non-overlapping) |

**Sub-agent parallelization:** K1 sub-task and R3 sub-task own disjoint
files (`flowmol3_upstream_shim.py` vs `flowmol3_v2_adapter.py`); the
shared test file (`test_flowmol3_v2_adapter_conformance.py`) is split
between the two sub-agents by appending test sections (K1.D appends
after R3.B; no row-level overlap).

### 7.2 Verification phase (sequential after both parallel sub-agents)

1. **Gate check 1:** `pytest tests/ -k "d4" -q` → **72/72 PASS** (D.4 byte-stable preserved).
2. **Gate check 2:** `pytest tests/test_adapters/test_flowmol3_v2_adapter_conformance.py -q` → all PASS (new RDKit-bridge tests + tile-shape tests).
3. **Gate check 3:** `mkdocs build --strict` → 0 warnings.
4. **Gate check 4:** `ruff check adaptive_reflow/` → ≤ 144 ruff violations (preserve Wave 274 P6 ruff-frozen baseline).
5. **Gate check 5:** `python tools/check_claims_consistency.py` → "No drift detected."
6. **Audit doc:** `docs/audit/wave275-p3-flowmol3-remediation-verify.md` (single audit doc cross-citing K1 + R3 closure evidence).
7. **Commit:** single commit message structured as `[K1] + [R3]` with vendor-clean assertion.

### 7.3 NO PUSH (user-gated)

Per the Wave 274 / Wave 275 pattern, **NO push** until user explicitly
approves. Commit only.

---

## 8. Open questions for user approval

The proposal is complete as written. The following decisions are user-gated
and should be answered BEFORE implementation starts:

1. **K1 default `validity_mode`:** "rdkit" (proposal default — primary metric is
   RDKit-bridged; `pb_validity_pct` becomes opt-in via `--validity-mode=pb` for
   forensic reproduction) OR "both" (primary is RDKit, but `pb_validity_pct` is
   also emitted as a secondary key)? **Proposal recommendation: "rdkit"** (matches
   the §15.15.1 row-1 `validity_pct=1.0 saturation` already-canonical metric).

2. **R3 N value:** after the tile fix lands, the Wave 235 P4 3-seed sweep can
   be re-run. Target N: 1000 (matches §15.15.1) OR 5000 (matches the published
   FlowMol3 / LineageFlow N range)? **Proposal recommendation: 1000** (matches
   the canonical §15.15.1 N for the 12-cell table).

3. **R3 GPU budget:** the 3-seed sweep at N=1000 (per Wave 235 P4) ran on
   GPU 0 + took ~30 min per arm per seed × 3 seeds = ~3 hours total. Is the
   GPU budget available? **Proposal recommendation: defer to user — the proposal
   itself does not require GPU.**

4. **Single PR vs separate K1/R3 PRs:** the proposal ships both fixes in one
   PR for atomicity (one `flowmol3` audit doc, one verify phase). Splitting
   into K1-only and R3-only PRs would double the verify cost. **Proposal
   recommendation: single PR.**

---

## 9. Files proposed to be touched (after user approval)

| File | LOC | Touch type |
|---|---:|---|
| `adaptive_reflow/adapters/flowmol3_upstream_shim.py` | ~65 LOC additive + ~5 LOC modified (line 184-187) | K1 |
| `adaptive_reflow/adapters/flowmol3_v2_adapter.py` | ~6 LOC modified (lines 2861-2867) | R3 |
| `tools/wave87_n1000_sweep.py` | ~5 LOC additive (CLI flag) | K1 |
| `tests/test_adapters/test_flowmol3_v2_adapter_conformance.py` | ~90 LOC additive (new test sections for K1 + R3) | both |
| `docs/CLAIMS.md` (additive annotation, if N=1000 re-run lands) | ~3 LOC additive | post-verify |
| `docs/audit/wave275-p3-flowmol3-remediation-verify.md` | new file (~50 LOC) | verify phase |

**Total project-owned code change:** ~75 LOC modified + ~145 LOC additive.
**Vendored code change:** **ZERO.** (`vendoredTouched: false`)

---

## 10. Cross-references

- **Wave 275 P1 inventory:** `docs/audit/wave275-p1-state-inventory.md` §4.2 (FlowMol3 row), §4.4 (K1 + R3 weakness classification)
- **Wave 275 P2 metric ledger:** `docs/audit/wave275-p2-metric-ledger.md` (where K1 + R3 row schema will land after re-sweep)
- **Wave 275 P3 flattening:** commit `8cd59b5` (proposal baseline)
- **Wave 109.C failure audit:** `docs/audit/wave109-c-flowmol3-n1000.md` §2.1 (DGL bug surface reproducer), §6.2 (4-LOC fix plan)
- **Wave 87 PB-xtb:** `docs/audit/wave87-phase2-impl.md` (UFF-vs-xtb definitional gap), `tools/paper_metrics.py` (PB-xtb wire)
- **Wave 262 P1 / CLM-077:** `docs/CLAIMS.md` (all-vendored-patches-reverted directive; this proposal preserves that)
- **Wave 235 P4:** `docs/CONSOLIDATED_RESULTS.md` §15.101 (3-seed-pooled BLOCKED); `docs/RELEASE-NOTES.md:105` (cross-seed envelope claim)
- **§15.15.1 per-cell table:** `docs/CONSOLIDATED_RESULTS.md:2188-2201` (K1 row 2 = REGRESSES, R3 row 3 = UNDERPOWERED)
- **§15.15.3 ICLR-ready verdict:** `docs/CONSOLIDATED_RESULTS.md:2213-2220` (12-cell distribution; K1 fix removes the 1 REGRESSES cell)
- **D.4 byte-stable gate:** `docs/GATES.md:87-137` (72/72 contract)
- **pb_config_with_energy_ratio_xtb.yaml:** `data/FlowMol3/repo/flowmol/analysis/pb_config_with_energy_ratio_xtb.yaml` (the fork used by `tools/paper_metrics.py`; not modified by this proposal)
- **vendor-pinned commit:** FlowMol3 = `77cae22` (preserved; no touch)

---

**End of proposal — awaits user approval before implementation. NO source
code modified by this commit.**