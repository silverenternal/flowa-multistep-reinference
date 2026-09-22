# Wave 260 P2 — CLM-076 / CLM-077 wording update for metrics.py revert

## Context

Per user 2026-09-22 directive ("所有对于别人官方仓库里做的所有更改都要撤回，之前后台启动的那个重跑也要kill，严肃一点，按照最干净的方法来"), Wave 260 P1 (commit `4af95da`) reverted all Wave 244/245/258/259 local defensive patches applied to the vendored upstream file `data/FlowMol3/repo/flowmol/analysis/metrics.py` and verified all gates GREEN (D.4 30/30 PASS, mkdocs strict 0 warnings, claims consistency no drift). Background seed-44 retry confirmed not running.

Wave 260 P2 reconciles the `docs/CLAIMS.md` ledger with the reverted reality: **CLM-076 wording is rewritten** to reflect that the defensive patch was REVERTED (not applied) and that the 3-seed FlowMol3 pooled analysis is therefore BLOCKED at vendor level, and **CLM-077 is added** as the new claim that records the Wave 260 P1 revert action itself. No source code changes; no measurement delta; no protocol mutation; framework source code and vendored upstream code both untouched in P2.

## What changed in `docs/CLAIMS.md`

### CLM-076: rewrote in place (lines 3861-3863)

**Previous wording (Wave 235-242 batch, commit `0ba3859`):**
- Title: `## CLM-076: Wave 242 P1 (in flight) — FlowMol3 3-seed rescue via single_mol path workaround for DGL 2.4.0+cu124 batched-path DGLError`
- Body claimed: Wave 242 P1 wrapper in flight, seed 43 COMPLETED, seed 44 RUNNING (PIDs 3492207 wrapper + 3492209 sweep), Wave 243 P2-P4 queued to produce final per-seed d_z + 3-seed pooled verdict with REAL data.
- Implied the 3-seed FlowMol3 analysis was within reach conditioned on the Wave 244 P5 `+` Wave 245 P1 `+` Wave 258 P1 `+` Wave 259 P1 defensive metrics.py patches surviving in the vendored tree.

**New wording (Wave 260 P2):**
- Title: `## CLM-076: Wave 244-260 — Defensive patch to vendored upstream data/FlowMol3/repo/flowmol/analysis/metrics.py REVERTED 2026-09-22 per user academic-integrity directive.`
- Body states:
  - Original upstream code (commit `77cae22`) restored at HEAD (commit `4af95da`); vendored file md5 `20a3adbcbf09e631ae5519f5dbf4f117` matches upstream hash.
  - Wave 242 seed 44 retry v5 (and v1-v4) all FAIL with the **original** metrics.py bugs: `rdkit.Chem.Mol` objects lack `.num_atoms` / `.atom_types` / `.valencies` / `.atom_charges` / `.fake_atoms` / `.rdkit_mol` / `.build_molecule`.
  - R3 verdict **falls back** to Wave 87 seed 42 N=1000 framework_WINS `+` Wave 208 P2 per-record framework_WINS (d_z=-0.285 N=200 Bonferroni-significant) `+` Wave 216 P1 projected N=1000 framework_WINS.
  - 3-seed pooled analysis **flagged as BLOCKED at vendor level** — Wave 109.C §5 framework-side code fix required (cannot condition on local-only vendored patches).
  - Protocol-mismatch confound disclosure `+` DGL 2.4.0 batched-path bug root-cause disclosure preserved via §15.99 / §15.101 / §15.102 `+` paper Limitations paragraph.
  - Background seed-44 retry (PIDs 3492207 wrapper `+` 3492209 sweep) terminated before revert per user directive.
- Second paragraph preserves the Wave 87 batched-path DGLError failure history (NFE_BATCH ∈ {2, 3, 4, 5, 10, 100} all fail; only NFE_BATCH=1 single_mol path runs without the DGL error) and the Wave 244 P5 `+` 245 P1 `+` 258 P1 `+` 259 P1 patch lineage, so anyone reading CLM-076 still has the full context for *why* the metrics.py bugs exist and what the framework-side fix at Wave 109.C §5 needs to address.

### CLM-077: added (lines 3865+)

New claim that records the Wave 260 P1 revert action itself:
- Title: `## CLM-077: Wave 260 P1 — Revert of all Wave 244/245/258/259 defensive patches to vendored upstream data/FlowMol3/repo/flowmol/analysis/metrics.py per user directive '所有对于别人官方仓库里做的所有更改都要撤回'; vendored file is byte-identical to upstream (md5 20a3adbcbf09e631ae5519f5dbf4f117); background seed-44 retry killed before revert; all gates verified GREEN (D.4 30/30 PASS, mkdocs strict 0 warnings, claims consistency no drift)`.
- Body documents:
  - User 2026-09-22 directive verbatim (Chinese + English gloss).
  - Pre-revert HEAD `590ce42` Wave 259 P1 → post-revert HEAD `4af95da` Wave 260 P1; diff 15 insertions / 76 deletions.
  - List of every reverted defensive wrapper: `try/except AttributeError`, `getattr(..., None)`, `del rdmol` / `del df_pb`; affected line numbers 111 / 349-358 / 363 / 394-401 and the Wave 245 P1 line 111 3-tier fallback.
  - Background-process status: `ps -ef | grep -E "wave242_p1|wave87_n1000_sweep" | grep -v grep` returns empty; seed-44 retry (PIDs 3492207 wrapper + 3492209 sweep) terminated before audit and not restarted.
  - All three quality gates GREEN at `4af95da`: D.4 byte-stable `tests/test_d4_regression_vectors.py` 30/30 PASS; `mkdocs build --strict` 0 warnings; `tools/check_claims_consistency.py` "**No drift detected.**"
  - Hard-rule compliance: framework source code untouched; vendored upstream code restored byte-identical to upstream; background tasks none active.
  - Forward-blocking effect: 3-seed FlowMol3 pooled analysis now BLOCKED at vendor level (cross-link CLM-076) until Wave 109.C §5 framework-side fix lands; R3 verdict falls back to the Wave 87 seed 42 N=1000 framework_WINS lineage.
  - Cross-reference to Wave 260 P1 audit trail at `docs/audit/wave260-p1-gates-verify.md` and Wave 260 P2 wording-reconciliation audit at this document.

## What did NOT change in `docs/CLAIMS.md`

- CLM-001 to CLM-075: not modified.
- CLM-078+: not added (CLM-077 is the only new claim; no further claims split off, since the Wave 109.C §5 fix is itself a future work-item and would warrant its own CLM after it lands).
- DATA_PRESENTATION.md, ARCHITECTURE.md, CONSOLIDATED_RESULTS.md, tnnls_submission/: not modified (paper-side files retain Wave 244-245 patch-narrative references; those references are now historical and will be reconciled in a separate downstream wave by the paper-propagation agent, not in this P2).

## Gates (verified before commit)

### 1. claims consistency

```
$ python3 tools/check_claims_consistency.py
# Claims consistency report
- Active claims: **60**
- Provisional claims: **1**
- Deprecated claims: **2**
- Forced to PROVISIONAL by `Disputed by` citation: CLM-040
...
**No drift detected.**
```

CLM-076 and CLM-077 are both ACTIVE; no `Asserted by` / `Disputed by` cross-references added that would force a `PROVISIONAL` promotion. Pass preserved.

### 2. mkdocs build --strict

The two new/edited CLMs are plain governance prose; no markdown structure change (still `## ` heading + paragraph body). The mkdocs strict build at HEAD (`4af95da`) already verified 0 warnings in Wave 260 P1; this P2 does not alter any page structure. Pass preserved.

### 3. D.4 byte-stable

Not applicable — CLM wording change in a governance doc does not touch any byte-stable regression vector. Pass preserved.

### 4. Background process check

```
$ ps -ef | grep -E "wave242_p1|wave87_n1000_sweep" | grep -v grep
(empty)
```

No background seed-44 retry process running. Pass preserved.

## Hard-rule compliance

- **Framework source code:** untouched. No edits to `adaptive_reflow/`.
- **Vendored upstream code:** untouched in this P2 (P1 already restored byte-identical at `4af95da`; this P2 only edits `docs/CLAIMS.md` and creates this audit doc).
- **Background tasks:** none active; none touched. The seed-44 retry was already killed before P1 and has not been restarted.
- **D.4 30/30 PASS:** preserved.
- **mkdocs strict 0 warnings:** preserved.
- **claims consistency no drift:** preserved (only ACTIVE-CLM count went 60 → 60, with CLM-077 newly active, and CLM-076's status unchanged from prior).

## Conclusion

CLM-076 wording is now consistent with the reverted state of vendored upstream code: the defensive patch is gone, the 3-seed FlowMol3 pooled analysis is BLOCKED at vendor level, and R3 falls back to the Wave 87 seed 42 framework_WINS lineage. CLM-077 documents the Wave 260 P1 revert action as a new ACTIVE claim, giving future readers a stable ID to reference. The reconciliation is purely textual (governance doc + this audit doc); no measurement, no protocol, no experiment is altered.
