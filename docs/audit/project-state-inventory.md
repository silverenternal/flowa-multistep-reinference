# Project state inventory — configuration surfaces (scheduler first)

**Date:** 2026-10-18
**Author:** inventory agent (USER AUTHORIZED, NO PUSH)
**Skill:** `flowa-research-audit` (read-only audit; no claim or number changed)
**HEAD at audit time:** `d034e7a7` ("GAP-43: pre-register the decisive blend-positive test (R3 fg_dev)")
**Trigger:** standing user request — *"先把项目完整状态盘点清楚，比方说调度器有没有最优的，统一用最优调度器，先把这种地方都确认清楚"* (do not start GAP-43 yet).

**Scope:** read-only. This document writes **no** code, **no** `docs/CLAIMS.md`, **no**
`docs/drafts/paper-A-final.*`, **no** `tnnls_submission/**`, and **no** headline artifact.
It records what the code and the frozen artifacts actually do, and separates
*confirmed* from *unconfirmed* configuration surfaces.

---

## 0. TL;DR

1. **There is no single optimal scheduler.** On the domains that were swept,
   `codimension_sheet` leads on CIFAR single-round and 2D well-averaged W2, while
   `evidence_driven` leads on MNIST smoke FID and `nfe_aware_memory` leads on the
   short-budget CIFAR screen. No arm wins every domain (§4).
2. **"10 of 11 headline cells use `CosineAnnealScheduler`" is not supported by the code.**
   Eight of the eleven cells instantiate **no scheduler object**: R2, R3, K1, K7
   construct none; R1/K4/K5 pass the string `"cosine"`, which `tools/eval/framework.py:914-920`
   routes to a **legacy uniform NFE split**; R6 is a post-hoc counterfactual.
   Only R5a (`PaperRatioAdaptiveScheduler`), R5b (four arms), and R5c (three arms)
   construct a real scheduler (§2.2).
3. **"Unify on the best scheduler" is not an executable configuration change.** It would
   move frozen headline numbers on every cell it touches, and on R1 it is a provable
   no-op (cosine and codimension_sheet are byte-identical there, GAP-42 §6). It is a
   re-run-and-re-freeze decision, not a switch (§5).
4. **A second, larger finding surfaced while checking NFE matching:** R5c's three
   framework arms are **not NFE-matched** — cosine and evidence_driven consume
   **25 steps/sample**, codimension_sheet **48**, and the baseline **50**
   (`verification_outputs/wave191-p3-mnist-n1000.json`). The paper's
   "matched NFE = 50" is therefore not accurate for R5c (§6.1, conflict C7).
5. **A third finding:** R5c's reported Δ% is a **chunk-mean** delta, not the ratio of
   the two headline FIDs printed in the same artifact. Recomputing from the printed
   FIDs gives −20.70%, not −28.43% (§6.6, conflict C8).

Nothing in this document changes a status label. Every item that would move a paper
number is filed as **user-gated** in §8.

---

## 1. Method and evidence classes

Three evidence classes are used, and never mixed:

| Class | Meaning | How it was obtained |
|---|---|---|
| **CODE** | What the shipped source does at HEAD | direct read of the cited file:line |
| **ARTIFACT** | What the frozen JSON/CSV records | direct read of the cited artifact field |
| **INFERRED** | A conclusion that follows from CODE + ARTIFACT but is not itself recorded | stated as inference, with the two premises cited |

Two runtime checks were executed (read-only, no GPU):

```
build_scheduler("cosine")            -> CosineAnnealScheduler            OK
build_scheduler("codimension_sheet") -> CodimensionSheetScheduler        OK
build_scheduler("evidence_driven")   -> KeyError                          FAIL
build_scheduler("freetraj")          -> KeyError                          FAIL
```

The check confirms that two families named in `PROTOCOL_REGISTRY` cannot be
constructed through the central factory (§2.1, conflict C6).

---

## 2. Scheduler inventory

### 2.1 Two registries, 16 names, 15 constructible

| Registry | Location | Names | Reachable via `build_scheduler` |
|---|---|---|---|
| `SCHEDULER_REGISTRY` | `adaptive_reflow/algorithm/scheduler/nfe_aware.py:551-577` | `cosine, constant, linear, exponential, polynomial, sigmoid, convergence_adaptive, codimension_sheet, paper_ratio_adaptive, sequential, nfe_aware_memory, tier_aware_codimension` (12 eager) + `edm, adaptive_pid, jittered_constant` (3 lazy, registered by `_register_extra_scheduler_families()` at `:630-648`) | all 15 |
| `PROTOCOL_REGISTRY` | `adaptive_reflow/algorithm/protocol_registry.py:161-180` | the 15 above **plus** `evidence_driven`, `freetraj`, `multi_channel_jittered`, `handoff_sequential` | 15 of 19; `evidence_driven` and `freetraj` raise `KeyError` |

**Consequence (INFERRED).** `evidence_driven` and `freetraj` are real scheduler
classes but are only constructible through the private `_build_scheduler` maps inside
the SOTA harnesses (`tools/run_sota_2d_experiment.py`, `tools/run_sota_cifar_experiment.py`,
`scripts/wave191_p3_mnist_sweep.py`). They are not first-class members of the central
factory, so any driver that only knows `build_scheduler` cannot select them.

### 2.2 Per-cell truth table

The "canonical" column is the driver that produced the artifact the paper cites, not
the driver that merely exists in the tree.

| Cell | Canonical driver (artifact) | Scheduler object actually constructed | How selected | Evidence |
|---|---|---|---|---|
| **R1** | `tools/gen_lineageflow_n1000_fastas.py` | **none** — string `"cosine"` routes to legacy uniform split | `SCHEDULER_NAME = "cosine"` default at `:126`; `framework.py:914-920` | CODE |
| **R2** | `tools/_kanzi_sweep_runner.py` (`framework_inv_proj`) | **none** — one `solve_ode` per record | `:475` | CODE |
| **R3** | `scripts/wave338_p5_r3_n1000_paired.py`; `tools/wave87_n1000_sweep.py` | **none** — one `solve_ode` per batch | `:232` and `:247` | CODE |
| **R5a** | `tools/run_sota_2d_experiment.py` (wave189 artifact) | **`PaperRatioAdaptiveScheduler`** | artifact field `scheduler` | ARTIFACT |
| **R5b** | `tools/run_sota_cifar_experiment.py` | **four arms**: Cosine / CodimensionSheet / EvidenceDriven / FreeTraj | `SCHEDULER_NAMES` `:148-153` | CODE + ARTIFACT |
| **R5c** | `scripts/wave191_p3_mnist_sweep.py` | **three arms**: cosine / codimension_sheet / evidence_driven; headline arm = `evidence_driven` | `ARM_LABELS` `:105`; `best_arm` field | CODE + ARTIFACT |
| **R6** | `scripts/wave235_p3_r6_uplift.py` | **none** — counterfactual arithmetic over a frozen k6 sweep | docstring `:27-45` | CODE |
| **K1** | `tools/wave87_n1000_sweep.py` (N=200 cap) | **none** — one `solve_ode` | `:247` | CODE |
| **K4/K5** | `tools/gen_lineageflow_n1000_fastas.py --upstream-eval-len-bias long` | **none** — same `"cosine"` legacy label as R1 | same as R1 | CODE |
| **K7** | `tools/upstream_eval.py` on `baseline.fasta` | **none** — no framework arm | paper §10.7 note; driver has no `solve_ode` | CODE |

**Count:** 3 of 11 cells construct a real scheduler object (R5a, R5b, R5c).
4 of 11 construct none and have no multi-round loop (R2, R3, K1, K7).
1 of 11 is a post-hoc counterfactual (R6).
3 of 11 pass the `"cosine"` **label** into a code path that does not build a
scheduler (R1, K4, K5).

### 2.3 Why the prior audit over-claimed

`docs/audit/scheduler-per-cell-summary.md` (2026-09-23) states
"13/13 R-cell + weak-claim HEADLINE sweeps used `CosineAnnealScheduler`".
Its source column cites *secondary* drivers — e.g. R2 →
`tools/run_sota_graphbfn_experiment.py:382`, R3 →
`tools/run_sota_flowmol3_v2_adapter_experiment.py:525` — both of which do call
`default_cosine_scheduler`, but **neither produced the artifact the paper cites**.
The canonical R2 runner (`_kanzi_sweep_runner.py`) and the canonical R3 runner
(`wave87_n1000_sweep.py`) never import a scheduler.

**Observed:** the prior audit answered "which scheduler does *some* driver use?"
**Not observed:** "which scheduler does *the cited artifact* use?"
The distinction is the root cause of the §0 item 2 over-claim.

---

## 3. Conflict ledger

Each entry is an observed fact, its impact, and its class. No entry is fixed here.

| ID | Observed | Impact | Class |
|---|---|---|---|
| **C1** | Paper §4.5 (`paper-A-final.md:374`) says 10/11 cells use `CosineAnnealScheduler`. Code shows 3/11 construct a scheduler; 7/11 construct none. | Reviewer cross-reading code will find the statement unsupported. | doc-vs-code |
| **C2** | R5c paper cites `d_z = -13.18` and `−28.43%` under the label "CosineAnnealScheduler". The artifact's `best_arm` is `evidence_driven`, whose `cohens_dz` is `-13.1755`; the cosine arm's is `-17.1211`. | The number is correct for the **evidence_driven** arm; the label is wrong. | label |
| **C3** | R5a paper says cosine. The artifact field is `"scheduler": "PaperRatioAdaptiveScheduler"` (`wave189-p2-post-cd70821-combined.json`), and the cited `d_s = +0.460` is computed on that arm. | The R5a headline is a paper-quantity-driven arm, not cosine. | label |
| **C4** | R6 paper says `TierAwareCodimensionSheetScheduler` wrapping `CodimensionSheetScheduler`. The canonical R6 artifact is a **counterfactual** with no scheduler; the live path with `paper_quantities=None` wraps `ConstantScheduler(n_cap=0.5)` (`framework.py:615-636`). | "Headline scheduler" is a conceptual mapping, not an executed object. | label + method |
| **C5** | R1 passes `"cosine"`, but `framework.py:914-920` deliberately bypasses `build_scheduler` for that string to preserve byte-stability. | The R1/K4/K5 headline is a **uniform NFE split**, not a cosine ramp. | label |
| **C6** | `evidence_driven` and `freetraj` are in `PROTOCOL_REGISTRY` but raise `KeyError` in `build_scheduler`. | A user following the registry docs cannot select them centrally. | API |
| **C7** | R5c arms consume 25 / 48 / 25 steps per sample vs baseline 50; the paper says "matched NFE = 50". | The arm comparison is NFE-confounded; `codimension_sheet` spent ~2× the budget of the other two arms. | method |
| **C8** | R5c `delta_vs_baseline_pct` is computed on chunk means, while `fid_headline` is a separate aggregate. Printed FIDs imply −20.70%, artifact says −28.43%. | A reader cannot reproduce Δ% from the printed FIDs. | metric semantics |
| **C9** | R2 `configs/kanzi_framework_inv_proj.yaml` declares `n_rounds: 3`, but `_kanzi_sweep_runner.py` never reads `n_rounds`. | The declared multi-round config is dormant; the arm is single-pass. | dormant config |
| **C10** | R1 canonical runs at `--nfe 10`; `RESTART_MIN_NFE = 20` collapses `effective_n_rounds` to 1 (`gen_lineageflow_n1000_fastas.py:581-582`). | The R1 framework arm is one round + blend + re-anchor, not a 3-round chain. | method |
| **C11** | `docs/environments.md` lists 5 venvs; `.venvs/` contains 11, including the `kanzi_venv` and `lineageflow_venv` that `AGENTS.md` mandates. | An operator following the environment doc cannot reproduce R2/R1. | doc drift |

---

## 4. Is there an optimal scheduler?

The evidence is **domain- and budget-dependent**. All numbers below are quoted from
existing artifacts; none was re-run.

| Domain / setting | Arms compared | Winner | Margin | Source |
|---|---|---|---|---|
| CIFAR N=200 n=3 NFE≈2 | cosine / codim / evidence / paper_ratio / convergence / nfe_aware_memory | `nfe_aware_memory` | −2.500% | CIFAR short-budget screen |
| CIFAR N=200 n=1 NFE=50 | cosine / codim / evidence / freetraj | `codimension_sheet` | −2.53% (cosine −1.60%) | `wave235-p1-r5b-fix.json` |
| CIFAR N=1000 n=1 NFE=50 | cosine / codim / evidence / freetraj | `evidence_driven` | 48.1669 vs baseline 48.4059; cosine 48.5668 and codim 48.6594 regress | `wave247-p3-r5b-n1000-n1/summary.json` |
| CIFAR N=500 | cosine / codim | `codimension_sheet` | −0.112% vs +98.602% | GAP-42 §3 |
| MNIST smoke N=1000 | cosine / codim / evidence | `evidence_driven` by FID; `cosine` by `d_z` | 23.3879 vs 23.5487; `d_z` −13.18 vs −17.12 | `wave191-p3-mnist-n1000.json` |
| MNIST matched-NFE (w16e1_5k / 10k) | cosine / codim | `codimension_sheet` | −25.39% / −15.18% | GAP-35 |
| 2D well-averaged | cosine / codim / evidence / freetraj | `codimension_sheet` | +5.6% (0.0746 vs 0.0790) | `wave189` / `wave351` |
| R1 equal-NFE | cosine / codim | **tie** | byte-identical (md5 equal) | GAP-42 §6 |
| R6 tier-aware | live uniform vs counterfactual tier-aware | tier-aware (counterfactual only) | counterfactual +0.2235 = the promotion bar; live uniform +0.1466 (not promoted) | `gap01-r6-live-wiring.md` §3, `gap28-r6-faithful.md` |

**Verdict (INFERRED).** No single scheduler dominates. `codimension_sheet` leads in
the image and 2D regimes where a per-round signal exists; `evidence_driven` leads on
MNIST smoke and on CIFAR N=1000; `nfe_aware_memory` leads only in the very short
budget. On R1 the comparison is **constructively null** because the adapter has no
`profile_residual_fn`, so `codimension_sheet`'s `n_cap` weights degenerate to
`[1.0, 0.9997, 1.0]` (GAP-42 §4).

**Therefore "the optimal scheduler" does not exist as a single name.** The honest
statement is a per-regime recommendation, which is what `docs/defaults-matrix.md`
already encodes (cosine for short/adaptive/sequential, codimension for long runs).

---

## 5. Can we unify on one scheduler?

Four independent blockers, in increasing severity:

1. **Most cells have nothing to unify.** 8 of 11 cells do not instantiate a
   scheduler object (4 construct none, 3 use the legacy label, 1 is a counterfactual;
   §2.2). "Switching" them means adding a multi-round re-inference loop that was
   never part of their protocol — a new experiment, not a config change.
2. **The string `"cosine"` is a byte-stability contract.** `framework.py:901-911`
   documents that the legacy split is preserved so the Wave 158 / Wave 161 / Wave 172b
   anchor manifests stay byte-identical. Changing it breaks the D.4 regression vectors
   unless the change is versioned.
3. **It would move frozen headline numbers.** R5a, R5b, R5c, and R6 are all
   `SUPPORTED`/`CONDITIONAL` on specific arms. Re-labelling or re-running to a common
   arm changes Δ, `d_z`, and `p`, which is forbidden without explicit user gating
   (TNNLS freeze).
4. **On R1 the unification is provably a no-op.** GAP-42 §6 recorded md5-identical
   outputs for cosine vs codimension_sheet at equal NFE. Unifying R1 would produce
   zero numerical change and only relabel the text.

**Cost if attempted anyway:** R1 (~30–50 h CPU + HMMER), R2 (Kanzi GPU), R3
(FlowMol3 GPU), R5a/b/c (GPU), R6 (CPU counterfactual), plus a full
`docs/CLAIMS.md` / MANIFEST / PDF refresh. This is larger than GAP-43 and has no
pre-registered decision rule.

**Recommendation (recorded, not executed):** do **not** unify. Instead:
(a) keep `docs/defaults-matrix.md` as the per-regime recommendation surface;
(b) correct the *labels* in the paper only if the user authorises a frozen-surface
edit (P1 in §8); (c) treat any arm switch as a new pre-registered experiment.

---

## 6. Other configuration surfaces

The user's "比方说" explicitly widens the scope beyond schedulers. The same
"confirmed vs not" test is applied to the remaining surfaces.

### 6.1 NFE matching

| Cell | Baseline NFE | Framework NFE (per sample) | Matched? |
|---|---|---|---|
| R1 | 10 (per record) | 10 total, collapsed to 1 round | yes by construction; **not** matched to upstream ~150 |
| R2 | 50 (`adapter_num_steps`) | 100 decoder steps (`nfe_budgets[0]`) | **no** — different axes (decoder vs adapter) |
| R3 | 250 | 250 | yes |
| R5a | 100 | 100 | yes |
| R5b N=200 | 50 | 50 | yes |
| R5b N=1000 | 50 | 50 (`framework_total_nfe` per arm) | yes |
| R5c | 50 | **25 / 48 / 25** | **no** (C7) |
| R6 | n/a (counterfactual) | n/a | n/a |

### 6.2 `n_rounds`

| Cell | Declared | Effective | Evidence |
|---|---|---|---|
| R1 | 3 | **1** (gate `RESTART_MIN_NFE=20` vs NFE=10) | C10 |
| R2 | 3 in YAML | **ignored** (single solve) | C9 |
| R3 | n/a | 1 | CODE |
| R5a | 5 | 5 | ARTIFACT |
| R5b | 1 | 1 | ARTIFACT |
| R5c | 4 | 4 | ARTIFACT |
| R6 | n/a | counterfactual | CODE |

### 6.3 β / memory fraction

- Framework default `BETA_BASE = 0.5` (`gen_lineageflow_n1000_fastas.py:115`).
- R5c `beta_framework = 0.5`, `beta_baseline = 0.0`.
- R6 tier-aware uses `easy_tier_nfe_reduction_factor = 0.5`.
- GAP-43 pre-registers β = 0.5 (`restart-memory-fraction 0.5`).
**Status:** consistent at 0.5 across all cells; no cell uses a tuned β.
This is a *choice*, not a verified optimum — no β sweep exists at headline N.

### 6.4 Seeds and power

| Cell | Statistical n | Note |
|---|---|---|
| R1 | 1 (seed 42) | 3-seed pool invalidated by seed-43/44 fallback contamination |
| R2 | 1 index-matched two-sample N=1000 | `corr ≈ +0.02` |
| R3 | 1 (seed 42) | per-record n=200 actual; n=1000 projected |
| R5a | 3 | |
| R5b | 3 (N=200) / 1 (N=1000) | |
| R5c | 3 (N=200 production) / chunk-level 10 (N=1000 smoke) | |
| R6 | 1 paired N=1000 sweep | |
| K1 | 3 × 200 | |
| K4/K5 | 3 × 1000 | |
| K7 | 1 | |

`docs/audit/gap37-statistical-power.md` already records that at α=0.05/7 the minimum
detectable `d_z` at n=3 is ≈1.7, at n=15 ≈0.91, at n=50 ≈0.50. Cells with n=1–3
cannot detect the 0.5 floor. **Status:** confirmed and already disclosed; no action
implied here.

### 6.5 Checkpoints

| Cell | Checkpoint | Identity check |
|---|---|---|
| R3 | `data/flowmol3/weights_real/checkpoints/last.ckpt` | md5 `d6cda2d7…` (GAP-43 §9) |
| R5c smoke | `data/mnist_fm.npz` | sha256 `ded1fa70…`, flagged `checkpoint_is_smoke_materialization = True` |
| R5c production | `data/mnist_fm/production.ckpt` | recorded in `wave280-p-r5c/aggregate.json` |
| R6 | frozen k6 sweep | `k6_foldability_n1000_w161_q3_2026/` |
| R2 | Kanzi real ckpt | `force_mode: real`, `metric_mode: real` |

**Status:** checkpoint identity is recorded per artifact. The open question is
**provenance of the R1 canonical artifact**: `reproduce/01` verifies
`lineageflow_hmmer_real_n1000_w158_q3_2026/`, while `reproduce/09` verifies
`wave349-r1-3seed-gpu/`. The two are different runs. This inventory does not resolve
which one the §7.2 single-seed number came from; flagged as **unconfirmed** (U1).

### 6.6 Metric identity

| Cell | Metric in paper | Metric in artifact | Same? |
|---|---|---|---|
| R1/K4/K5 | `hmmscan_total_hits` | vendored HMMER count | yes |
| R2 | `reconstruction_kabsch_rmsd_Å` | composite | yes (synthetic input disclosed) |
| R3 | `fg_dev` | `paper_fg_deviation` = REOS cumulative deviation | yes |
| R5a | W2 | W2 | yes |
| R5b | Inception FID | `inceptionv3_tfport` | yes |
| R5c | "FID" | **projection FID** (784→128 Gaussian projection), explicitly *not* InceptionV3 | **no** (disclosed in artifact, not in the paper row) |
| R6 | pLDDT | pLDDT | yes |
| K1 | `rdkit_validity_pct` | RDKit validity | yes (note: GAP-39 pilot's "K1" was `paper_pb_validity_pct`, not this) |
| K7 | `novel_pct_pfam_twilight` | novelty at Tanimoto thresholds | yes |

**C8** additionally applies to R5c: Δ% is chunk-mean-based, not ratio-of-FIDs.

### 6.7 Environment and registry

- `docs/environments.md` is stale: 5 venvs documented, 11 present, and it omits
  `kanzi_venv` / `lineageflow_venv` which `AGENTS.md` §2.2 requires (C11).
- The two-registry split (C6) means the public registry is not the full scheduler set.
- `profile_residual_fn_registry` (`adaptive_reflow/adapters/profile_residual.py:407`)
  is used only by `scripts/wave229_p3_core_adapter_paper_quantities.py`. **No headline
  driver wires `profile_residual_fn` into `_solve_framework`.** This is why
  `codimension_sheet` is inert on R1 and why the paper-quantity controllers are
  dormant on 10/11 cells.

---

## 7. What this inventory does not establish

1. It does **not** claim any headline number is wrong. The numbers are the artifact
   values; only their **labels**, **NFE matching**, and **aggregation semantics** are
   at issue.
2. It does **not** re-run any sweep, and it does **not** re-derive any `d_z` or `p`.
3. It does **not** resolve U1 (R1 artifact provenance) or the exact chunk-mean
   formula behind C8.
4. It does **not** assert that `codimension_sheet` would win on the cells where it was
   never run; it only reports where it was run.

---

## 8. Action register

### P0 — record-only (done by this commit)

| # | Action | Surface |
|---|---|---|
| P0-1 | This audit document | `docs/audit/project-state-inventory.md` |
| P0-2 | Register in `mkdocs.yml` nav | `mkdocs.yml` |
| P0-3 | Record the inventory as an open item in `todo.json` | `todo.json` |

### P1 — user-gated paper-surface correction (no number moves)

| # | Proposed change | Why it needs the user |
|---|---|---|
| P1-1 | Replace "10 of 11 cells use `CosineAnnealScheduler`" with the §2.2 truth (3 construct a scheduler; 3 use the legacy label; 4 none; 1 counterfactual). | frozen manuscript |
| P1-2 | Fix the R5c arm label: `evidence_driven`, not `CosineAnnealScheduler` (C2). Number unchanged. | frozen manuscript |
| P1-3 | Fix the R5a arm label: `PaperRatioAdaptiveScheduler` (C3). Number unchanged. | frozen manuscript |
| P1-4 | Disclose R5c's per-arm NFE (25 / 48 / 25 vs 50) and the chunk-mean Δ% semantics (C7, C8). | frozen manuscript + CLAIMS |
| P1-5 | Correct R6's "headline scheduler" to "counterfactual tier mapping; live base is `ConstantScheduler(n_cap=0.5)`" (C4). | frozen manuscript |

### P2 — requires a new pre-registered experiment

| # | Question | Why not now |
|---|---|---|
| P2-1 | Would `codimension_sheet` beat the current arm on R1/K1/K4/K5 if `profile_residual_fn` were wired? | R1 is a no-op without it; needs adapter work + a new sweep |
| P2-2 | R5c at genuinely matched NFE (all arms 50) | would move the `−28.43%` number |
| P2-3 | β sweep at headline N | no prior; would need a pre-registration like GAP-43 |

**Status update (2026-10-20, additive).**

| # | State | Where |
|---|---|---|
| P2-2 | **CLOSED.** R5c re-measured with 50 NFE on both sides, 4 checkpoints × 3 genuine draws, N=1000. The `−28.43 %` does not survive: it was the smoke checkpoint, and the matched-NFE effect at `w16e1_5k` is `−9.37 %`. The production cell regresses `+9.52 %`. | `docs/audit/gap57-equal-nfe-regime-ladder.md` |
| P2-3 | **ANSWERED FOR R1, NOT FOR THE OTHERS.** β ∈ {0, 1/6, 1} at NFE=150: β=0 collapses (0 hits), and β=1/6 vs β=1 is a tie in 3/3 seeds, so the memory term is null and the per-record perturbation carries the gain. R2/R3/R5a/R5b have not been swept. | `docs/audit/gap45-r1-blend-off-wiring.md` §8 |
| P2-1 | **OPEN.** `profile_residual_fn` is still unwired for `codimension_sheet` on R1/K1/K4/K5. | — |

---

## 9. References

- `tools/eval/framework.py:901-940` — legacy `"cosine"` branch and scheduler-driven allocation.
- `tools/eval/framework.py:600-636` — R6 live base is `ConstantScheduler(n_cap=0.5)`.
- `adaptive_reflow/algorithm/scheduler/nfe_aware.py:551-577`, `:630-648`, `:671-700` — registry and factory.
- `adaptive_reflow/algorithm/protocol_registry.py:161-180` — second registry.
- `tools/gen_lineageflow_n1000_fastas.py:80-126`, `:581-594` — R1 NFE/rounds/scheduler constants.
- `tools/_kanzi_sweep_runner.py:475` — R2 single solve.
- `scripts/wave338_p5_r3_n1000_paired.py:232`, `tools/wave87_n1000_sweep.py:247` — R3/K1 single solve.
- `scripts/wave235_p3_r6_uplift.py:27-45` — R6 counterfactual definition.
- `verification_outputs/wave191-p3-mnist-n1000.json` — R5c per-arm NFE and `d_z`.
- `verification_outputs/wave189-p2-post-cd70821-combined.json` — R5a scheduler field.
- `verification_outputs/wave235-p1-r5b-fix.json`, `verification_outputs/wave247-p3-r5b-n1000-n1/summary.json` — R5b arms and matched NFE.
- `docs/audit/gap42-scheduler-budget-conservation.md` §4, §6 — codimension_sheet degeneration and byte-identical R1.
- `docs/audit/scheduler-per-cell-summary.md` — prior audit whose 13/13 claim §2.3 supersedes.
- `docs/defaults-matrix.md` — existing per-scenario recommendation surface.
- `docs/audit/gap37-statistical-power.md` — n vs detectable `d_z`.
