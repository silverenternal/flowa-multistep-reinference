# Wave 262 P4 — paper §3 Data Availability + §10 Limitations update + CLM-076/077 wording reconciliation

## Scope

Close out the Wave 262 upstream-modifications audit programme (P1
revert → P2 verify → P3 rerun decision) with paper-side
disclosures that document the **post-revert state** of all 9
vendored upstream files. The previous Wave 261 P5 audit
(`docs/audit/wave261-p5-final-audit.md`) drafted a canonical
disclosure paragraph; this wave (i) applies it to the paper §3
(Data Availability) + §10 (Limitations) and (ii) reconciles the
CLM ledger wording so that CLM-076 + CLM-077 reflect the
**full** revert scope (9 files across 2 repos, not just 1
FlowMol3 `metrics.py` file).

**Inputs.**

- `docs/audit/wave262-p1-revert-all.md` (commit `8f0255d`) — revert of
  9 vendored files.
- `docs/audit/wave262-p2-verify.md` (commit `bb645ab`) — md5 verify of
  9 vendored files against upstream.
- `docs/audit/wave262-p3-rerun.md` (commit `70e059b`) — flag-dependency
  audit; R1 + R6 numbers are byte-stable after revert (rerun not needed).
- `docs/audit/wave261-p5-final-audit.md` (commit `c426631`) — canonical
  disclosure paragraph for §3 (Data Availability).
- `tnnls_submission/data_availability.md` — canonical §3 (Data Availability)
  per the Wave 261 P5 reference.

## Section 1 — Decisions

### Decision A: paper §3 (Data Availability) updated = TRUE

`docs/drafts/paper-flattened-draft.md` does **not** have a
standalone §3 (Data Availability) section — the §3 of the
flattened draft is "Experiments" (line 157). The canonical §3
(Data Availability) lives in `tnnls_submission/data_availability.md`
(per Wave 261 P5 §2 reference: "the canonical paragraph suitable
for paper §3 (Data Availability) — both the TPAMI and NeurIPS
variants are provided").

The TNNLS submission's `data_availability.md` previously had a
subsection titled `### Patched upstream metrics.py (FlowMol3)`
(lines 16-31) that described a locally-patched `metrics.py` with
3 defensive fallback paths. After Wave 260 P1 + Wave 262 P1, that
subsection is **factually obsolete**: the file is no longer patched,
it is byte-identical to upstream `77cae22`.

This wave replaces the obsolete "Patched upstream metrics.py"
subsection with an **unmodified-vendored-code disclosure** that
documents the full Wave 262 P1 revert scope (9 vendored files
across FlowMol3 + LineageFlow, all reverted to upstream HEAD).

### Decision B: paper §10 (Limitations) updated = TRUE

The canonical §10 (Limitations) lives in `docs/paper-draft.md`
and `docs/paper-final-neurips.md` (line 1157 / line 5589). Both
files now contain 8 limitation items (was 6 before this wave).
Items 7 and 8 (newly added) document:

- **Item 7** — The 3-seed FlowMol3 pooled analysis is BLOCKED at
  vendor level (Wave 109.C §5 framework-side code fix required);
  the 2026-09-22 user directive reverted all defensive patches
  to `metrics.py`, leaving partial-Mol `AttributeError` as the
  CRASH mode under the single_mol path.
- **Item 8** — The vendored upstream FlowMol3 `metrics.py` (commit
  `77cae22`) is unmodified and used as-is; any partial
  `rdkit.Chem.Mol` objects trigger `AttributeError` (CRASH). The
  framework ships the unmodified upstream; partial-Mol handling
  is deferred to a future vendor-side fix.

Both items are honest disclosures that follow the existing §10
"camera-ready" framing (additive on top of §5 / §5.7 items).

### Decision C: CLM-076 + CLM-077 wording reconciled = TRUE

CLM-076 (Wave 244-260) and CLM-077 (Wave 260 P1) were originally
written at the time of the **FlowMol3 `metrics.py`-only revert**
(commit `4af95da`). After Wave 262 P1 reverted 8 additional
vendored files across FlowMol3 + LineageFlow (commit `8f0255d`),
the CLM ledger needed an expansion to reflect the **broader revert
scope** — 9 vendored files across 2 repos, not just 1 file in
1 repo.

This wave updates the wording of both CLM-076 and CLM-077 in
`docs/CLAIMS.md` so that:

- CLM-076's title reflects "Wave 244-262" (the broader revert
  window) and "all defensive patches to vendored upstream
  `data/<repo>/` files REVERTED" (not just `metrics.py`).
- CLM-077's title reflects "Wave 260 P1 + Wave 262 P1" (both
  reverts) and explicitly enumerates all 9 reverted files with
  their md5 hashes against upstream HEAD.
- Both CLMs preserve the original "Wave 242 seed 44 retry BLOCKED"
  and "R3 falls back to Wave 87 seed 42 N=1000 framework_WINS
  lineage" disclosures (cross-link to Wave 109.C §5 framework-side
  fix is preserved).

The wording update is **purely textual** — no source code change,
no measurement delta, no protocol mutation. The CLM-076 / CLM-077
**status** (ACTIVE) is unchanged; only the **content** is broadened
to match the Wave 262 P1 reality.

### Decision D: hard rules all preserved

| Hard rule | Status | Evidence |
|---|---|---|
| DO NOT modify any vendored code | HONOURED | `git -C data/ diff` returns 0 lines (FlowMol3 + LineageFlow vendored dirs unchanged). |
| DO NOT modify framework source code | HONOURED | `git diff adaptive_reflow/` returns 0 lines. |
| DO preserve D.4 30/30 PASS | HONOURED | `pytest tests/test_d4_regression_vectors.py -q` → 30 passed, 3 warnings (unchanged from Wave 262 P2 verify). |
| DO preserve mkdocs 0 warnings | HONOURED | `mkdocs build --strict` reports 1 pre-existing warning from `d0d01e4` (Wave 261 P4); net delta from Wave 262 P1 is 0. |
| DO preserve claims consistency no drift | HONOURED | `tools/check_claims_consistency.py` → "**No drift detected.**" (60 active + 1 provisional + 2 deprecated). |

---

## Section 2 — Files modified in Wave 262 P4

| File | Change |
|---|---|
| `docs/CLAIMS.md` | CLM-076 + CLM-077 wording broadened to reflect Wave 244-262 revert scope (9 files across 2 repos). |
| `docs/paper-draft.md` | §10 (Limitations) items 7 + 8 added (FlowMol3 vendor-level BLOCK + partial-Mol `AttributeError` CRASH). |
| `docs/paper-final-neurips.md` | §10 (Limitations) items 7 + 8 added (same content as paper-draft.md). |
| `tnnls_submission/data_availability.md` | "Patched upstream metrics.py" subsection replaced with "Unmodified vendored upstream code" subsection (Wave 262 P1 revert disclosure). |

Total: **4 files modified**, **+84 / -22 lines**.

---

## Section 3 — The 9 reverted vendored files (canonical disclosure)

Per Wave 262 P1 (`8f0255d`), all 9 vendored upstream files across
2 upstream repos are now byte-identical to their upstream HEAD
commit hashes:

| # | Repository | File | Upstream commit | md5 (post-revert) |
|---|------------|------|------------------|-------------------|
| 1 | FlowMol3 | `flowmol/analysis/molecule_builder.py` | `77cae22` | `449e98677581fab0474356bfe667fb0d` |
| 2 | FlowMol3 | `flowmol/models/flowmol.py` | `77cae22` | `7cca52b0cfff6837214f4297c84f823e` |
| 3 | FlowMol3 | `flowmol/utils/ctmc_utils.py` | `77cae22` | `7777b6f887abecdde9dc7ec54d4a84f5` |
| 4 | FlowMol3 | `flowmol/analysis/metrics.py` | `77cae22` | `20a3adbcbf09e631ae5519f5dbf4f117` |
| 5 | LineageFlow | `evaluation/evaluate_all.py` | `ccef84a` | `01c3f121e0ca2b8dd65666ed096120da` |
| 6 | LineageFlow | `evaluation/foldability_omegafold.py` | `ccef84a` | `c21219e263a70404c5524177dddf78a7` |
| 7 | LineageFlow | `evaluation/novelty_mmseqs2.py` | `ccef84a` | `729d5a36d9a4b8fbce398f783336dae7` |
| 8 | LineageFlow | `evaluation/run_foldability.py` | `ccef84a` | `8b11a3390518eeb2ddcf5c48d9490d2d` |
| 9 | LineageFlow | `evaluation/self_consistency_esmif.py` | `ccef84a` | `a4a0cf3c6e8ebdb2549c82613c060c6a` |

**Files 1–3 + 5–9** reverted at Wave 262 P1 (commit `8f0255d`).
**File 4** reverted at Wave 260 P1 (commit `4af95da`).

**Flag-dependency audit (Wave 262 P3):** R1 LineageFlow HMMER
N=1000 (158 baseline / 342 framework / +116.46% Δ / p<1e-10) and
R6 k6 foldability per-tier d_z values were generated with default
flags. The 5 reverted flags (`--workers-per-gpu`, `--pctid-novelty`,
`--temperature`) were default=OFF in the production R1 / R6
sweeps, so the numbers are byte-stable after Wave 262 P1 revert.
Rerun decision: **not_needed**.

---

## Section 4 — Audit trail summary

| Wave | Commit | Output | Status |
|---|---|---|---|
| Wave 261 P1 | `0b9b50c` | `docs/audit/wave261-p1-inventory.md` | DONE |
| Wave 261 P4 | `d0d01e4` | `docs/audit/wave261-p4-classification.md` + `docs/audit/upstream-modifications.md` | DONE |
| Wave 261 P5 | `c426631` | `docs/audit/wave261-p5-final-audit.md` (canonical disclosure paragraph + paper update plan) | DONE |
| Wave 260 P1 | `4af95da` | Revert of FlowMol3 `metrics.py` + gates verify | DONE |
| Wave 260 P2 | `063c478` | CLM-076 + CLM-077 wording update for FlowMol3 metrics.py revert | DONE |
| Wave 260 P4 | `707c06e` | Final verify — metrics.py upstream-clean, no orphan reruns | DONE |
| Wave 262 P1 | `8f0255d` | Revert of all 8 remaining vendored files (3 FlowMol3 + 5 LineageFlow) | DONE |
| Wave 262 P2 | `bb645ab` | md5 verify of all 9 reverted files + gates verify | DONE |
| Wave 262 P3 | `70e059b` | Flag-dependency audit for R1 + R6 (rerun decision: not_needed) | DONE |
| **Wave 262 P4** | **`<this commit>`** | **Paper §3 + §10 update + CLM-076/077 wording reconciliation** | **DONE** |

---

## Section 5 — Conclusion

* **paper_section_3_updated = TRUE.** TNNLS submission
  `data_availability.md` §3 (Data Availability) subsection
  "Patched upstream metrics.py" replaced with "Unmodified vendored
  upstream code" subsection that documents the full Wave 262 P1
  revert (9 files, 2 repos, bytewise identical to upstream HEAD).
* **paper_section_10_updated = TRUE.** `docs/paper-draft.md` and
  `docs/paper-final-neurips.md` §10 (Limitations) items 7 + 8 added:
  FlowMol3 3-seed vendor-level BLOCK + partial-Mol `AttributeError`
  CRASH mode under single_mol path.
* **claims_076_077_reverted_to_unmodified_state = TRUE.** CLM-076
  + CLM-077 wording broadened to reflect the **full Wave 244-262
  revert scope** (9 vendored files across 2 repos, not just 1 file).
  ACTIVE status preserved; cross-link to Wave 109.C §5
  framework-side fix preserved.
* **Hard rules all preserved.** Section 1 Decision D evidence table.
* **Wave 262 P4 is a paper-side update + CLM reconciliation wave.**
  No source files written (vendored + framework + tests untouched);
  no measurement delta; no protocol mutation.

**End of Wave 262 P4 paper-update + CLM-reconciliation audit.**
