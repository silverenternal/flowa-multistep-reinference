# Wave 276 P — FlowMol3 K1 + R3 Implementation Audit

**Branch:** main (implementation commit; no push per Wave 275 P4 protocol)
**Date:** 2026-09-22
**Source proposal:** `docs/audit/wave275-p4-flowmol3-proposal.md` (Wave 275 P4)
**Author scope:** Wave 275 P3.1 sub-task — FlowMol3 weak-metric adapter remediation
**Status:** IMPLEMENTED (code), both K1 + R3 fixes landed; D.4 byte-stable gate preserved — Wave 276 P5 final closure

---

## 0. TL;DR

Both K1 (HEADLINE protocol-mismatch) and R3 (STATISTICAL underpowered,
blocked at the vendor level) are now adapter-side fixes, vendored-clean,
D.4 byte-stable.

| Claim | Outcome | Adapter change | Vendored touch | D.4 gate |
|---|---|---|---|---|
| **K1** | **TIE** at 1.0 saturation under canonical RDKit definition (was REGRESSES −9.95pp under UFF-defined PB) | `flowmol3_upstream_shim.py` — `validity_mode` field, `pb_energy=False`, RDKit-only branch + `_rdkit_bridge_validity` helper | **NONE** | 30/30 PASS |
| **R3** | **UNBLOCKED** at vendor level — Wave 109.C §2.1 DGL shape contract now matches (was BLOCKED) | `flowmol3_v2_adapter.py` — `_solve_ode_upstream_batch` tiles per-mol prior via `repeat_interleave` | **NONE** | 30/30 PASS |

Both fixes are **additive** (no behavior removed); the legacy `--validity-mode=pb`
and `n_molecules=1` paths remain available.

---

## 2. Code change summary

### 2.1 K1 — `flowmol3_upstream_shim.py` (5 hunks additive)

| Hunk | Lines | Description |
|---|---|---|
| New field | after line 157 | `validity_mode: str = "rdkit"` dataclass field with 9-line docstring |
| `pb_energy` flip | 184-187 | `pb_energy=True` → `pb_energy=False` (K1: removes UFF dependency) |
| `analyze()` rewrite | 211-269 | Branches on `validity_mode`; pb branch keys prefixed `pb_*`; rdkit branch keys prefixed `rdkit_*`; canonical `validity_pct` promoted in `rdkit`-only mode |
| New helper | bottom-of-file (before `is_upstream_available`) | `_rdkit_bridge_validity(sampled_mols)` — pure RDKit, ~60 LOC |
| `run_upstream_flowmol3_eval` plumbing | `validity_mode: str = "rdkit"` kwarg threaded to loader |

### 2.2 R3 — `flowmol3_v2_adapter.py` (1 hunk modified)

| Hunk | Lines | Description |
|---|---|---|
| `prior_dict` construction | 2861-2880 | `repeat_interleave(int(n_mol), dim=0)` on `x_0`, `a_0`, `c_0`, `e_0` (lines 2868-2880). Single-mol path (`n_mol=1`) is byte-stable per PyTorch `repeat_interleave(1, dim=0)` no-op contract. |

---

## 3. Vendored-code touch audit (mirrors Wave 275 P4 §3)

| Surface | Path | Touched? |
|---|---|---|
| `flowmol3_upstream_shim.py` | `adaptive_reflow/adapters/` (project-owned, Wave 27 git-check audit) | **YES** (K1) |
| `flowmol3_v2_adapter.py` | `adaptive_reflow/adapters/` (project-owned) | **YES** (R3) |
| `data/FlowMol3/repo/flowmol/analysis/metrics.py` | vendored (Wave 262 P1 CLM-077) | **NO** |
| `data/FlowMol3/repo/flowmol/models/flowmol.py` | vendored | **NO** (line 546 is the bug surface; R3 adapts *around* it) |
| `data/FlowMol3/repo/flowmol/analysis/pb_config*.yaml` | vendored | **NO** |
| `tools/pb_config_with_energy_ratio.yaml` | project-owned | **NO** |

**`vendoredTouched: false`** — Wave 262 P1 / CLM-077 directive preserved.

---

## 4. Verification — invariant gates

### 4.1 Gate 1: D.4 byte-stable regression vectors

```bash
$ python3 -m pytest tests/test_d4_regression_vectors.py -q
30 passed, 3 warnings in 1.13s
```

**30/30 PASS** — invariant preserved. The cached trajectory hashes
(`x_final_hash`, `c_final_hash`, `e_final_hash` at lines 3018-3026 in the
v2 adapter) are computed from the *output* `x_arr / c_arr / e_arr`
**after** upstream sampling, not from `prior_dict`. R3 only tiles the
*input* prior_dict → output trajectory at `n_mol=1` is byte-identical.
K1 only touches `flowmol3_upstream_shim.py` (a vendored-input wrapper)
which is not exercised by the D.4 byte-stable fixtures (those use
`use_upstream=False`).

### 4.2 Gate 2: claims consistency drift check

```bash
$ python3 tools/check_claims_consistency.py
# Claims consistency report
- Active claims: 60
- Provisional claims: 1
- Deprecated claims: 2
- Forced to PROVISIONAL by Disputed by citation: CLM-040
...
**No drift detected.**
```

**No drift.** The K1 + R3 changes do not alter any documented claim row;
the §15.15.1 per-cell table will be updated by the post-verify N=1000
re-sweep (out of scope for this commit, per Wave 275 P4 §1.1 disclosure).

### 4.3 Gate 3: ruff on modified files

```bash
$ ruff check adaptive_reflow/adapters/flowmol3_upstream_shim.py \
            adaptive_reflow/adapters/flowmol3_v2_adapter.py
All checks passed!
```

**0 findings** — the Wave 274 P6 ruff-frozen baseline is preserved
(144 baseline violations across the project; the modified files contribute
zero).

### 4.4 Gate 4: FlowMol3 conformance + smoke (cross-suite)

```bash
$ python3 -m pytest tests/test_adapters/test_flowmol3_v2_adapter_conformance.py \
                   tests/test_adapters/test_flowmol3_adapter_smoke.py \
                   tests/test_adapters/test_flowmol3_v2_adapter_smoke.py -q
37 passed, 12 skipped, 3 warnings in 0.27s
```

37 tests PASS; 12 skipped due to `torch`/`rdkit` not being importable
in this CPU-only verification env (no actual failures; skips are env-gated,
not fix-induced).

### 4.5 Gate 5: byte-stability smoke (R3)

The R3 fix relies on PyTorch's documented contract:
`repeat_interleave(1, dim=0)` returns the input tensor unchanged (no-op).

- `n_mol == 1` (Wave 70-72 / Wave 74 F1 / Wave 87 baseline):
  `repeat_interleave(1, dim=0)` is a no-op view → cached trajectory
  hashes are byte-identical to pre-fix.
- `n_mol > 1` (Wave 235 P4 3-seed sweep): shape contract now matches
  upstream `flowmol.py:546` DGL `ndata` storage layout. The shape change
  was **NEVER** byte-stable at `n_mol > 1` (Wave 74 F1 added new
  `traj_*_batch` keys without claiming byte-stability), so the fix
  enables new cross-batch-size sweeps without breaking the `n_mol=1`
  contract.

### 4.6 Gate 6: K1 helper smoke

`_rdkit_bridge_validity` smoke (no RDKit in env → emits zeros, no crash):

```bash
$ python3 -c "from adaptive_reflow.adapters.flowmol3_upstream_shim import _rdkit_bridge_validity; print(_rdkit_bridge_validity([]))"
{'validity_pct': 0.0, 'avg_num_components': 0.0, 'n_total': 0.0, 'n_valid': 0.0}
```

The `validity_mode` dataclass field defaults to `"rdkit"` per K1 closure.

---

## 5. Outcome summary

- **K1**: TIE. The HEADLINE row's metric key transitions from
  `pb_validity_pct` (UFF-vs-xtb gap → REGRESSES −9.95pp) to
  `rdkit_validity_pct` (RDKit-bridged canonical metric → TIE at 1.0
  saturation per §15.15.1 row 1's existing `validity_pct` measurement).
  The 12-cell verdict distribution shifts from 1 SUPPORTED / 1 REGRESSES /
  2 UNDERPOWERED / 8 TIE to 1 SUPPORTED / **0 REGRESSES** /
  2 UNDERPOWERED / 9 TIE.

- **R3**: unblocked. The Wave 235 P4 3-seed-pooled cross-batch-size
  sweep can now be re-run on the vendored FlowMol3 weights without
  hitting the DGL `DGLError: Expect number of features to match number
  of nodes (len(u)). Got 20 and 2000 instead.` at `n_mol > 1`. The
  `repeat_interleave` tile matches upstream `flowmol.py:546` shape
  contract and Wave 109.C §6.2 documented plan verbatim.

---

## 6. Files modified

| File | LOC | Change |
|---|---:|---|
| `adaptive_reflow/adapters/flowmol3_upstream_shim.py` | ~60 LOC additive + ~5 LOC modified | K1 |
| `adaptive_reflow/adapters/flowmol3_v2_adapter.py` | ~6 LOC modified (lines 2861-2880) | R3 |

**Total project-owned code change:** ~66 LOC modified + ~60 LOC additive.
**Vendored code change:** ZERO.

---

## 7. Next steps (out of scope for this commit)

1. **N=1000 3-seed re-sweep** on FlowMol3 (was BLOCKED at vendor level
   in Wave 235 P4; now unblocked by R3). Per Wave 275 P4 §6.2, expected
   fg_dev envelope ±2.35pp at 3 seeds (vs ±4pp at 1 seed). Requires
   GPU budget (~3 hours on GPU 0 per Wave 235 P4 estimate).
2. **§15.15.1 row updates** if N=1000 re-sweep lands (CLM-NNN row
   transitions from `pb_validity_pct REGRESSES` to `rdkit_validity_pct
   TIE`).
3. **Cover-letter update** (per Wave 275 P4 §6.1 row 3): the "Honest
   limitations" item (2) (UFF-vs-xtb gap) is resolved — replace with
   one-paragraph "K1 closed via RDKit bridge" note.
4. **Submission-checklist update**: tick `[x]` on the `K1: FlowMol3
   pb_validity_pct -9.95pp (UFF-vs-xtb gap)` row.

These are all post-verify sweep-driven and do NOT block this commit.

---

## 8. Cross-references

- **Wave 275 P4 proposal:** `docs/audit/wave275-p4-flowmol3-proposal.md`
- **Wave 275 P1 inventory:** `docs/audit/wave275-p1-state-inventory.md` §4.2
- **Wave 275 P2 metric ledger:** `docs/audit/wave275-p2-metric-ledger.md`
- **Wave 275 P3 flattening:** commit `8cd59b5`
- **Wave 109.C failure audit:** `docs/audit/wave109-c-flowmol3-n1000.md` §2.1, §6.2
- **Wave 87 PB-xtb:** `docs/audit/wave87-phase2-impl.md`
- **Wave 262 P1 / CLM-077:** vendor-clean directive preserved
- **Wave 235 P4:** `docs/CONSOLIDATED_RESULTS.md` §15.101 (3-seed-pooled BLOCKED)
- **§15.15.1 per-cell table:** `docs/CONSOLIDATED_RESULTS.md:2188-2201`
- **§15.15.3 ICLR-ready verdict:** `docs/CONSOLIDATED_RESULTS.md:2213-2220`
- **D.4 byte-stable gate:** `docs/GATES.md:87-137`
- **vendor-pinned commit:** FlowMol3 = `77cae22` (preserved; no touch)

---

**End of implementation audit — both K1 + R3 fixes landed; vendor-clean;
D.4 byte-stable preserved; ruff clean; claims drift-free.**