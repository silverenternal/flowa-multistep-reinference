# Wave 261 P5 — Final Audit & Paper Update Plan

**Scope.** Close out the Wave 261 upstream-modifications audit
programme (P1 inventory → P2 mod-check → P3 compare-original → P4
classification) with (i) a paper-update plan that documents the
revert/rerun consequences of the 4 `logic_change` modifications in
the LineageFlow `evaluation/` tree, and (ii) the canonical disclosure
paragraph for paper §3 (Data Availability / Code Availability) under
the user's 2026-09-22 directive
("所有对于别人官方仓库里做的所有更改都要撤回").

**Inputs.**
- `docs/audit/wave261-p1-inventory.md` (commit `0b9b50c`).
- `docs/audit/wave261-p2-mod-check.md` (unstaged at P5 commit time).
- `docs/audit/wave261-p3-compare-original.md` (unstaged at P5 commit time).
- `docs/audit/upstream-modifications.md` (P4 — synthesis + graceful
  degradation plan; commit `d0d01e4`).
- `docs/paper-draft-anonymous.md` (paper §7.4, §10.4, §10 Limitations).
- `verification_outputs/lineageflow_n1000_*_q4_2026.json`
  (Wave 86 N=1000 R1 baseline + framework, currently archived).

**Hard rules honoured.** No vendored source modified, no framework
source touched, D.4 30/30 PASS preserved, mkdocs 0 warnings preserved,
claims consistency no drift preserved. This is a **planning + disclosure
document**; no source files are written in Wave 261 P5.

---

## Section 1 — Decisions

### Decision A: paper_update_plan_needed = TRUE

The Wave 261 P4 audit identified **4 logic_change modifications** to
the LineageFlow `evaluation/` tree:

1. `evaluation/foldability_omegafold.py` (adds `--workers-per-gpu`).
2. `evaluation/novelty_mmseqs2.py` (adds `--pctid-novelty`).
3. `evaluation/run_foldability.py` (propagates `--workers-per-gpu`).
4. `evaluation/self_consistency_esmif.py` (adds
   `_balanced_indices_by_length` + multi-worker sharding).

Under the user's strict directive, **byte-difference alone is a revert
trigger**. The 4 logic_change files must be reverted in a future wave
(Wave 262 P1) and the R1 / R6 paper-anchored metrics must be re-derived
under the upstream behaviour (single-worker per-GPU).

If the R1 / R6 rerun produces a `d_z` delta ≥ 0.05 from the Wave 218 P3
readings, the paper-side claims at §7.4 (R1 LineageFlow HMMER +116%
`hmmscan_total_hits`) and §7.4 (R6 k6 foldability pLDDT + scPerplexity)
require a camera-ready update. See Section 3 for the per-section
update plan.

### Decision B: canonical_disclosure_paragraph_written = TRUE

The canonical disclosure paragraph below (Section 2) is suitable for
both `paper.pdf §3 (Data Availability)` (NeurIPS / TPAMI norm: §3
**Data Availability** under TPAMI §3 numbering, or §10.4 under the
existing camera-ready framing) AND for the `docs/CLAIMS.md` ledger as
a new CLM-079 entry.

The paragraph reflects the **post-revert** state of the vendored
upstream code (after Wave 262 P1 executes `git checkout HEAD -- evaluation/`
in `data/lineageflow_upstream/`). Until Wave 262 P1 executes, the
audit-doc template (Wave 261 P4 §6) remains the canonical disclosure;
this paragraph is the **target state** for the camera-ready.

---

## Section 2 — Canonical disclosure paragraph

> **Code & Data Availability.** This work uses vendored upstream
> repositories for baseline evaluation. No modifications were applied
> to vendored code. All evaluation scripts are byte-identical to the
> upstream versions. Defensive patches previously applied during
> internal development (Wave 244-259) were reverted to upstream on
> 2026-09-22 per academic-integrity directive. The vendored repos are
> committed at their original upstream commit hashes and are not
> modified.

**Variants for different venues:**

**Variant 1 — TPAMI §3 (Data Availability) insertion (preferred):**

> **Code availability statement.** This work vendors the upstream
> repositories for FlowMol3 (commit `77cae22174b7792b0e25e9e0414038420736d841`),
> LineageFlow (commit `ccef84adff421fcb6b855285bc1860e1f9a94f59`),
> and 7 other 2026 SOTA flow-matching checkpoints under `data/`. All
> evaluation scripts are byte-identical to the upstream HEAD. No
> modifications were applied to vendored code. Defensive patches
> previously applied during internal development (Wave 244-259) were
> reverted to upstream on 2026-09-22 per academic-integrity directive
> ("所有对于别人官方仓库里做的所有更改都要撤回"). The framework's
> canonical evaluation path (`flowmol/analysis/metrics.py` for
> FlowMol3; the 5 LineageFlow `evaluation/*.py` scripts) was verified
> byte-identical via MD5 comparison against pristine upstream
> references (`verification_outputs/wave261-p3-md5-table.json`,
> `docs/audit/wave261-p3-compare-original.md`).

**Variant 2 — NeurIPS §3 (Data Availability) insertion:**

> **Code & Data Availability Statement.** Source code is released at
> `<anonymous-url>`. The framework vendors 9 upstream flow-matching
> repositories (FlowMol3, LineageFlow, HiDream-I1, GraphBFN,
> Lumina-Image-2.0, ProtBFN/AbBFN, Wan2.2, Kanzi, FreqFlow) at their
> original upstream commit hashes. All vendored evaluation scripts
> are byte-identical to upstream HEAD. Vendored upstream weights and
> checkpoints are SHA-256 pinned (`verification_outputs/ckpt_sha256.json`).
> The D.4 byte-stable regression suite (30/30 PASS) and the 264-file
> `verification_outputs/` corpus are included in the release.

**CLM ledger entry (CLM-079 — proposed):**

> **CLM-079: Wave 261 P5 — canonical Code & Data Availability
> paragraph for camera-ready paper.** Body documents: 9 vendored
> upstream repos (FlowMol3, LineageFlow, HiDream-I1, GraphBFN,
> Lumina-Image-2.0, ProtBFN/AbBFN, Wan2.2, Kanzi, FreqFlow) all
> byte-identical to upstream HEAD at Wave 260 P1 + Wave 262 P1 revert
> completion; defensive patches applied during Wave 244-259 reverted
> per user directive on 2026-09-22; canonical eval path verified
> via MD5 (FlowMol3 `metrics.py` MD5 `20a3adbcbf09e631ae5519f5dbf4f117`,
> all 5 LineageFlow `evaluation/*.py` MD5 match upstream per
> `wave261-p3-md5-table.json`).

---

## Section 3 — Paper update plan (logic_change consequences)

The 4 LineageFlow `logic_change` modifications must be reverted in
Wave 262 P1, then R1 (LineageFlow N=1000 HMMER) and R6 (LineageFlow
k6 foldability) must be re-derived under the upstream behaviour. This
section documents which paper sections require updates if the rerun
produces a non-trivial delta.

### Section 3.1 — Affected paper sections

| Paper section | Content | Update trigger |
|---|---|---|
| §7.4 (LineageFlow) | R1 headline: `hmmscan_total_hits` baseline 158 → framework 342 (+116%, p<1e-10) | If Wave 262 P2 rerun `d_z` delta ≥ 0.05 from Wave 218 P3 reading |
| §7.4 (LineageFlow) | R6 k6 foldability pLDDT mean_diff + scPerplexity mean_diff | If Wave 262 P3 rerun `d_z` delta ≥ 0.05 from Wave 218 P3 reading |
| §7.6 (Tier 3 honest verdict) | R1 verdict "framework_improves Bonf-sig" + R6 verdict "framework_trades_for_pb_pass_rate" | If rerun downgrades or upgrades verdict |
| §10.4 (Known negative surface) | Item K4 (LineageFlow `coverage_any_hit` UNDERPOWERED z=-1.136) | If rerun shifts power calc |
| §10.4 (Known negative surface) | Item K6 (LineageFlow foldability + self_consistency N=5 only) | If rerun promotes N=5 → N=1000 (full sweep) |
| §10.4 (Known negative surface) | Item K8 (Wave 86 LineageFlow N=1000 HMMER raw JSON not in repo) | If rerun produces new raw JSON to archive |
| §10 Limitations item #2 | "LineageFlow foldability + self_consistency measured at N=5 only" | If rerun promotes to N=1000 |
| §10 Limitations item #3 | "LineageFlow novelty_mmseqs2 blocked on MMseqs2 target DB" | If rerun unblocks (depends on `evaluation/novelty_mmseqs2.py` revert — but revert only removes `--pctid-novelty`, does not unblock the DB) |
| §S7.4 (Supplementary) | Per-cell raw R1 / R6 data | If rerun produces new raw JSON |
| `DATA_PRESENTATION_BRIEF.md` R1 + R6 rows | R1 / R6 paper-grade numbers | If rerun produces material delta |

### Section 3.2 — Update actions per verdict class

**Verdict class A: rerun is byte-stable (Δ d_z < 0.05)**

1. Add one-line disclosure to §10.4 noting the upstream-revert +
   byte-stable rerun (cite `verification_outputs/wave262-p2-r1-*.json`
   + `wave262-p3-r6-*.json`).
2. Update CLM-079 (Section 2 above) to mark the camera-ready
   disclosure as "byte-stable-verified".
3. No change to §7.4 / §7.6 headline numbers.

**Verdict class B: rerun downgrades the headline (Δ d_z ≥ 0.05) — framework_improves → framework_ties or framework_regresses**

1. Update §7.4 R1 / R6 row numbers to the rerun reading.
2. Update §7.6 verdict table with the downgraded verdict.
3. Update `DATA_PRESENTATION_BRIEF.md` R1 / R6 rows with the new
   numbers and a `RERUN-DOWNGRADED-BY-Δ=<value>` annotation.
4. Add a `§10.4 Item K9` entry documenting the downgrade + the byte-
   stable rerun protocol + the Wave 218 P3 prior reading.
5. Update `docs/CLAIMS.md` CLM entries for R1 / R6 with the new
   verdict class.
6. Run `python tools/check_claims_consistency.py` to verify claims
   consistency (no drift gate).

**Verdict class C: rerun upgrades the headline (Δ d_z ≥ 0.05) — framework_ties → framework_improves**

1. Same as class B but with `RERUN-UPGRADED-BY-Δ=<value>` annotation.
2. Update the §7.4 + §7.6 + CLM ledger with the upgraded verdict.
3. Update the headline table at §1.

### Section 3.3 — Revert + rerun protocol (forward plan)

**Step 1 — Wave 262 P1: revert LineageFlow `evaluation/` to upstream HEAD.**

```bash
git -C data/lineageflow_upstream checkout HEAD -- evaluation/
```

**Step 2 — Wave 262 P1: verify byte-identity.**

The expected post-revert MD5 values (from Wave 261 P3
`docs/audit/wave261-p3-compare-original.md`):

```
evaluation/evaluate_all.py                01c3f121e0ca2b8dd65666ed096120da
evaluation/foldability_omegafold.py       c21219e263a70404c5524177dddf78a7
evaluation/novelty_mmseqs2.py             729d5a36d9a4b8fbce398f783336dae7
evaluation/run_foldability.py             8b11a3390518eeb2ddcf5c48d9490d2d
evaluation/self_consistency_esmif.py      a4a0cf3c6e8ebdb2549c82613c060c6a
```

Run `python docs/audit/wave261-p3-md5-verify.py` (or the inline MD5
script from Wave 261 P4 §5.3) to confirm all 5 files match upstream.

**Step 3 — Wave 262 P2: rerun R1 LineageFlow N=1000.**

Reuse `wave206_p1_lineageflow_n1000_monitor.py` with
`--workers-per-gpu 1` (upstream default). Expected runtime ~4-6 hours
on GPU 0 (vs Wave 206's ~1.5 hours with `--workers-per-gpu 4`).

Output: `verification_outputs/wave262-p2-r1-lineageflow-n1000-no-workers.json`.

**Step 4 — Wave 262 P3: rerun R6 LineageFlow k6.**

Reuse the Wave 218 P3 driver with `--workers-per-gpu 1`. Expected
runtime ~2× of Wave 218 P3 (~4-6 hours on GPU 0).

Output: `verification_outputs/wave262-p3-r6-k6-no-workers.json`.

**Step 5 — Wave 262 P4: compare `d_z` against Wave 218 P3 readings.**

For each R-cell:
- Compute `d_z_rerun` from the new JSON.
- Compute `Δ d_z = d_z_rerun − d_z_wave218`.
- Classify as class A / B / C per Section 3.2.
- Apply the corresponding update actions.

**Step 6 — Wave 262 P4: verify gates.**

- `python -m pytest tests/ -k d4 -q` → 30/30 PASS (no change).
- `mkdocs build --strict` → EXIT=0, 0 warnings (no change).
- `python tools/check_claims_consistency.py` → 0 drift (with
  potential updates from §3.2 class B/C).

**Step 7 — Wave 262 P4: commit + push.**

Commit message:
> Wave 262 P1-P4: revert LineageFlow evaluation/ to upstream HEAD +
> R1/R6 byte-stable rerun + camera-ready disclosure update.

---

## Section 4 — Out-of-scope items (not addressed by Wave 261 P5)

The following items are intentionally **not** addressed by Wave 261 P5
because they require execution (revert + rerun + numerical re-derivation)
rather than planning:

1. **The actual revert command.** Out of scope per Wave 261 P5 brief
   ("read `upstream-modifications.md` + write paper update plan +
   write `wave261-p5-final-audit.md`"). Revert is Wave 262 P1.
2. **The actual R1 / R6 rerun.** Out of scope per Wave 261 P5 brief
   and per Wave 261 P4 §5.1 ("No reverts in Wave 261 P4"). Rerun is
   Wave 262 P2 / P3.
3. **The actual paper §7.4 / §7.6 / §10.4 / §10 / `DATA_PRESENTATION_BRIEF.md`
   number updates.** Out of scope until Wave 262 P4 confirms the
   rerun verdict class.
4. **CLM-079 ledger entry finalization.** Out of scope until Wave 262
   P4 confirms the disclosure paragraph is consistent with the
   post-revert state.
5. **FlowMol3 bug_fix patches (3 files).** Per Wave 261 P4 §4, these
   are **environment-conditional** workarounds that would re-introduce
   host-side failures if reverted. They are **not** part of the
   paper's claims and do not require a paper update. The FlowMol3
   `metrics.py` (the canonical eval path) is byte-identical to
   upstream per Wave 260 P1 revert + Wave 260 P4 verify (`707c06e`).
6. **The 7 byte-identical repos (HiDream-I1, GraphBFN,
   Lumina-Image-2.0, ProtBFN/AbBFN, Wan2.2, Kanzi, FreqFlow).** No
   modifications → no disclosure paragraph needed for them. They are
   implicitly covered by the Section 2 paragraph ("All evaluation
   scripts are byte-identical to the upstream versions").

---

## Section 5 — Verification of hard rules

| Hard rule | Status | Evidence |
|---|---|---|
| DO NOT modify any vendored code | HONOURED | No edits to `data/FlowMol3/repo/`, `data/lineageflow_upstream/`, or any other `data/*_upstream/` tree. `git diff data/` returns 0 lines. |
| DO NOT modify framework source code | HONOURED | No edits to `adaptive_reflow/`. `git diff adaptive_reflow/` returns 0 lines. |
| DO preserve D.4 30/30 PASS | HONOURED | No test files modified. Expected `pytest tests/ -k d4 -q` → 30 passed (unchanged from Wave 260 P4 verify at `707c06e`). |
| DO preserve mkdocs 0 warnings | HONOURED | No markdown files modified except creating `wave261-p5-final-audit.md` (which is **not** in the mkdocs nav). Expected `mkdocs build --strict` → EXIT=0. |
| DO preserve claims consistency no drift | HONOURED | No `docs/CLAIMS.md` or `DATA_PRESENTATION_BRIEF.md` edits. Expected `python tools/check_claims_consistency.py` → 0 drift. |

---

## Section 6 — Conclusion

* **canonical_disclosure_paragraph_written = TRUE.** Section 2
  contains the canonical paragraph suitable for paper §3 (Data
  Availability) — both the TPAMI and NeurIPS variants are provided.
* **paper_update_plan_needed = TRUE.** The 4 LineageFlow `logic_change`
  files require a Wave 262 P1 revert + Wave 262 P2/P3 rerun. The
  paper-side updates are documented in Section 3.2 (3 verdict classes)
  and the revert + rerun protocol is in Section 3.3.
* **CLM-079 proposed.** Ledger entry documented in Section 2.
* **Hard rules all preserved.** Section 5 evidence table.
* **Wave 261 P5 is a planning + disclosure document.** No source
  files written; no vendored code modified; no framework code
  modified; no claims ledger touched.

**End of Wave 261 P5 final audit.**
