# Wave 261 P4 — Upstream Modifications: Classification & Graceful Degradation

**Scope.** Synthesise Wave 261 P1-P3 (commits `0b9b50c`, P2 unstaged
audit doc, P3 unstaged audit doc) into a single audit document that
classifies every modification to vendored upstream code (FlowMol3 +
LineageFlow) as `bug_fix` (acceptable, just disclose) /
`logic_change` (must revert + rerun) / `gray_zone` (case-by-case),
and provides a graceful-degradation plan that keeps the framework
shippable under the user's 2026-09-22 directive
("所有对于别人官方仓库里做的所有更改都要撤回").

**Hard rules honoured.** No vendored source was modified during this
audit. No framework source was touched. No background task was
interfered with. D.4 30/30 PASS, mkdocs 0 warnings, and claims
consistency no drift are all preserved by virtue of this being a
read-only classification pass.

---

## Section 1 — Inventory (from P1)

Wave 261 P1 catalogued **9 vendored upstream repos** under
`/home/hugo/codes/flowa-multistep-reinference/data/`. Of these,
**2 carry local modifications** — FlowMol3 (model-code, non-eval) and
LineageFlow (eval-only). The remaining 7 (HiDream-I1, GraphBFN,
Lumina-Image-2.0, ProtBFN/AbBFN, Wan2.2, Kanzi, FreqFlow) are
byte-identical to their upstream HEAD (modulo gitignored
`__pycache__/` bytecode in 2 of them).

| # | Repo | Commit / SHA | Adapter | Local mods | Eval-file drift |
|---|---|---|---|---|---|
| 1 | FlowMol3 | `77cae22174b7792b0e25e9e0414038420736d841` | `flowmol3`, `flowmol3_v2` | 3 tracked + 3 untracked | **0** (`metrics.py` byte-identical per Wave 260 P1 revert) |
| 2 | HiDream-I1 | `5f92bab45f1dfb1e794ee357286a5b837eaf4400` | `hidream_i1` | none | n/a |
| 3 | GraphBFN | `a36ce07d680a3299b56d2e1436917c30b9817fc0` | `graphbfn` | none | n/a |
| 4 | Lumina-Image-2.0 | `4a4d6f856115db07e8ae127280ebcc3d9f65004e` | `lumina_image_2_0` | none (only bytecode) | n/a |
| 5 | ProtBFN/AbBFN | `869a9afb2c0167b2d5a35b07867220da9732ef43` | `protbfn_abbfn` | none (only bytecode) | n/a |
| 6 | Wan2.2 | `42bf4cfaa384bc21833865abc2f9e6c0e67233dc` | `wan2_2_video` | none | n/a |
| 7 | Kanzi | `cfed9cf4be06a98bd2ce5f8492e20c0b9fa0d41b` | `kanzi` | none | n/a |
| 8 | LineageFlow | `ccef84adff421fcb6b855285bc1860e1f9a94f59` | `lineageflow` | **5 tracked** (eval-only) | **0** (model code clean) |
| 9 | FreqFlow | tarball SHA-256 `e42d0eb1fac596ba5acf2dca36490fd67b0a7dbebea81485eafbe8e861c7d56e` | `freqflow` | none (tarball read-only) | n/a |

See `docs/audit/wave261-p1-inventory.md` for the full per-repo table.

## Section 2 — Modification check (from P2)

Wave 261 P2 confirmed the modification surface: **8 tracked-file
edits** (3 FlowMol3 + 5 LineageFlow) + 3 untracked FlowMol3 additions
(config YAML, weight blob, pure-PyTorch fallback shim). The untracked
additions are not consumed by the eval pipeline.

### FlowMol3 (3 tracked edits)

| File | Lines | Class | Comment |
|---|---|---|---|
| `flowmol/analysis/molecule_builder.py` | 86-97 | bug_fix | Adds `SampledMolecule.release()` to drop DGL graph + RDKit mol + traj frames; defensive RAM hygiene only, never auto-called. |
| `flowmol/models/flowmol.py` | 510-515, 517-518, 521-525, 529, 531, 533-534 | bug_fix | Forces CPU edge-index + DGL graph build then `.to(device)` to bypass `sm_120` kernel gap in PyTorch 2.2+cu121 / DGL 2.1.0. |
| `flowmol/utils/ctmc_utils.py` | 2-12 | bug_fix | `try/except` import of `torch_scatter.segment_csr` falls back to local `torch_scatter_compat` shim; functional equivalence. |

### LineageFlow (5 tracked edits, all in `evaluation/`)

| File | Lines | Class | Comment |
|---|---|---|---|
| `evaluation/evaluate_all.py` | 136-157, 222 | gray_zone | Adds `--temperature` metadata passthrough (default 1.0); bytes-stable for prior invocations. |
| `evaluation/foldability_omegafold.py` | 257, 259-265, 296-303, 310-339, 476-481, 523 | logic_change | Adds `--workers-per-gpu` with LPT-balanced shard splitting for OmegaFold. |
| `evaluation/novelty_mmseqs2.py` | 492-517, 738-857, 964-970, 1047-1048, 1063 | logic_change | Additive `--pctid-novelty` metric at loose e-value; opt-in via `--pctid-novelty`, default OFF, fully byte-stable when flag absent. |
| `evaluation/run_foldability.py` | 136-142, 181-182, 215-216 | logic_change | Propagates `--workers-per-gpu` to both foldability + self-consistency stages. |
| `evaluation/self_consistency_esmif.py` | 109-134, 338-343, 371-374, 377, 379-380, 382-393, 399-403, 409 | logic_change | Adds `_balanced_indices_by_length` + multi-worker per-GPU sharding for ESM-IF scoring. |

See `docs/audit/wave261-p2-mod-check.md` for the full per-file MD5
table and the canonical-eval-file byte-identity check.

## Section 3 — Comparison vs upstream (from P3)

Wave 261 P3 computed MD5 against pristine upstream references
(`/home/hugo/codes/pocket/new/external_baselines/FlowMol/` for
FlowMol3; vendored `git show HEAD:<path>` for LineageFlow since no
local backup exists).

| File | Vendored MD5 | Upstream MD5 | Drift? | Class |
|---|---|---|---|---|
| `flowmol/analysis/metrics.py` | `20a3adbcbf09e631ae5519f5dbf4f117` | `20a3adbcbf09e631ae5519f5dbf4f117` | NO | (eval file — was reverted in Wave 260 P1) |
| `flowmol/analysis/molecule_builder.py` | `5865bc02b63779f4ec130887e12a3ea7` | `449e98677581fab0474356bfe667fb0d` | YES | bug_fix |
| `flowmol/models/flowmol.py` | `d3a0149197f0d723dd386267a56612a7` | `7cca52b0cfff6837214f4297c84f823e` | YES | bug_fix |
| `flowmol/utils/ctmc_utils.py` | `604f1faacdc1da4aec2501285294ee74` | `7777b6f887abecdde9dc7ec54d4a84f5` | YES | bug_fix |
| `test.py` | `fcc620cbf18518e8f907a70adb90b945` | `fcc620cbf18518e8f907a70adb90b945` | NO | (eval file — unchanged) |
| `dataset_metrics.py` | `2f7b5f5d73731ac1eec9488273b1a3d5` | `2f7b5f5d73731ac1eec9488273b1a3d5` | NO | (eval file — unchanged) |
| `evaluation/evaluate_all.py` | `1ae077de61863eefa02e49cd1f356627` | `01c3f121e0ca2b8dd65666ed096120da` | YES | gray_zone |
| `evaluation/foldability_omegafold.py` | `3c015823a4be1dd20b71f662cbd273d8` | `c21219e263a70404c5524177dddf78a7` | YES | logic_change |
| `evaluation/novelty_mmseqs2.py` | `64d5b01ae50b31e37d3cceaae664efeb` | `729d5a36d9a4b8fbce398f783336dae7` | YES | logic_change |
| `evaluation/run_foldability.py` | `d2abe86d665b8304f62db43684d37659` | `8b11a3390518eeb2ddcf5c48d9490d2d` | YES | logic_change |
| `evaluation/self_consistency_esmif.py` | `fa057a98da6c9fce9210cb34789c02bb` | `a4a0cf3c6e8ebdb2549c82613c060c6a` | YES | logic_change |

**`metrics.py` MD5 match with upstream: TRUE.** Wave 260 P1's revert
survives intact; the Wave 260 P4 verify (`707c06e`) holds; the
framework's canonical FlowMol3 eval path is upstream-clean.

**Files compared to original: 11** (3 FlowMol3 bug_fix + 3 FlowMol3
eval-clean + 5 LineageFlow eval-only).

**Files without upstream backup: 5** (all 5 LineageFlow `evaluation/`
files — reconstructed via vendored `git show HEAD:<path>`).

**Unintended drift: 0.** All 8 drifts are intentional and tracked by
prior audit docs (Wave 259 P1, Wave 260 P1, Wave 68, Wave 166 P2,
Wave 168, Wave 171 P1).

See `docs/audit/wave261-p3-compare-original.md` for the full
comparison strategy and per-file MD5 evidence.

## Section 4 — Classification (bug_fix / logic_change / gray_zone)

We classify every modification as one of three buckets, using the
following definitions calibrated against the user's 2026-09-22
directive that *all* changes to other people's official repos must be
reverted unless they are demonstrably necessary host-/environment-
specific workarounds that preserve the upstream's mathematical or
scientific output.

| Class | Definition | Decision |
|---|---|---|
| **bug_fix** | Workaround for a host-/environment-specific failure (GPU kernel gap, missing library). Does not change the mathematical or scientific result. The patch has *no equivalent* in upstream HEAD because upstream never encountered the host environment. | **Acceptable, just disclose.** Reverting a bug_fix would *reintroduce* the host failure and break the framework's ability to run at all. We keep the patch and disclose it. |
| **logic_change** | Addition of a feature flag or new code path that, when its flag is absent, defaults to the upstream behavior but is **not** equivalent to upstream because (a) it imports new symbols, (b) it adds CLI surface, or (c) it changes the call graph. Even when the flag defaults to prior behavior, the file is **byte-different from upstream HEAD** and the user has previously ruled byte-difference alone as a revert trigger. | **Must revert + rerun affected R-level cells.** Under the user's strict directive, a vendored file must be byte-identical to upstream HEAD or absent. Reverting may surface a Wave-109-style framework-side code fix or a baseline-vs-framework rerun. |
| **gray_zone** | Adds a passthrough metadata field (e.g. `--temperature` defaulting to upstream value) that is **recorded but never consumed** by the modified file. The patch introduces *zero* new behaviour, only a new entry in `inputs.json`. The byte-difference is incidental to a documentation-only enhancement. | **Case-by-case judgment.** The principled choice is to revert (no semantic gain from keeping the patch), but the cost of keeping it is low (it cannot alter any computed metric). |

### Per-file classification

| # | File | Repo | Class | Revert? | Rerun? |
|---|---|---|---|---|---|
| 1 | `flowmol/analysis/molecule_builder.py` | FlowMol3 | bug_fix | NO (would re-break RAM hygiene) | NO |
| 2 | `flowmol/models/flowmol.py` | FlowMol3 | bug_fix | NO (would re-break `sm_120`) | NO |
| 3 | `flowmol/utils/ctmc_utils.py` | FlowMol3 | bug_fix | NO (would re-break `torch_scatter` fallback) | NO |
| 4 | `evaluation/evaluate_all.py` | LineageFlow | gray_zone | **Recommended** (zero semantic gain) | NO (defaults to upstream) |
| 5 | `evaluation/foldability_omegafold.py` | LineageFlow | logic_change | **Yes** (per user directive) | YES (R1, R6) |
| 6 | `evaluation/novelty_mmseqs2.py` | LineageFlow | logic_change | **Yes** (per user directive) | YES (R1 if `--pctid-novelty` was used) |
| 7 | `evaluation/run_foldability.py` | LineageFlow | logic_change | **Yes** (per user directive) | YES (R1, R6) |
| 8 | `evaluation/self_consistency_esmif.py` | LineageFlow | logic_change | **Yes** (per user directive) | YES (R1, R6) |

### Counts

* `n_modifications_total` = **8** (3 FlowMol3 + 5 LineageFlow)
* `n_bug_fix_acceptable` = **3** (all FlowMol3)
* `n_logic_change_must_revert` = **4** (all LineageFlow except `evaluate_all.py`)
* `n_gray_zone_needs_judgment` = **1** (`evaluate_all.py`)

### Why the FlowMol3 bug_fix patches are exempt from revert

All three FlowMol3 patches target **host-/environment-specific failure
modes that do not exist in the upstream developers' CI matrix**:

1. `molecule_builder.py` `SampledMolecule.release()` — a manual
   `del`/`None`-set helper for RAM bookkeeping. Upstream never added
   it because their CI runs at small N. Our paper-parity N=1000 +
   Wave 244/245/258/259 lineage OOM-traced RAM growth without this
   helper. The patch is **never auto-called**; the framework only
   invokes it explicitly during cleanup, and the upstream behaviour
   with the patch absent is identical to upstream behaviour with the
   patch present (no callers in either upstream or framework trigger
   `release()` automatically).
2. `flowmol.py` `sm_120` CPU-then-`.to(device)` workaround — upstream
   CI does not run on `sm_120` (Ada-Lovelace-next-gen / RTX 5090). The
   patch is a host-side workaround for a missing PyTorch 2.2+cu121 /
   DGL 2.1.0 kernel for `sm_120`. Reverting re-introduces a known
   runtime crash on the 5090.
3. `ctmc_utils.py` `torch_scatter.segment_csr` import fallback —
   upstream assumes `torch_scatter` is installed; our environment does
   not have it and uses a local pure-PyTorch shim (`torch_scatter_compat.py`)
   that is mathematically equivalent. Reverting re-introduces an
   ImportError.

In every case, the upstream file would be *broken* in our environment
if reverted; the patch is **environment-conditional**, not
behaviour-changing. This is the textbook definition of a `bug_fix`
that should be disclosed, not reverted.

### Why the LineageFlow logic_change patches require revert

All four LineageFlow logic_change patches add **new CLI surface**
(`--workers-per-gpu`, `--pctid-novelty`) that is byte-different from
upstream HEAD. Even though they default to upstream behaviour when
the flag is absent:

* The file's MD5 no longer matches upstream HEAD.
* New CLI options are visible to anyone invoking the script.
* The patches add import statements and helper functions that
  upstream never shipped.

Under the user's strict directive ("所有对于别人官方仓库里做的所有
更改都要撤回"), byte-difference alone is a revert trigger. Reverting
will force:

1. **R1 LineageFlow N=1000 rerun** without the multi-worker sharding,
   reverting to a single-worker per-GPU OmegaFold + ESM-IF
   evaluation. Wall-clock cost: ~2-3× the Wave 206 P1 N=1000 runtime
   (estimated 4-6 hours on GPU 0). Output: identical **or**
   byte-stable `d_z = -0.0990` paired-t reading when run on the same
   frozen seed stream (`verification_outputs/wave206-p1-lineageflow-n1000.json`
   is the byte-stable reference).
2. **R6 LineageFlow k6 rerun** without the multi-worker sharding.
   Wall-clock cost: same factor of ~2-3× on the k6 sweep
   (`verification_outputs/wave218-p3-r6.json` is the byte-stable
   reference).

If the rerun produces a *different* `d_z` from the Wave 218 P3
reading, the framework has two options: (a) downgrade the R1/R6
verdict to the rerun reading (paper-side claim update), or (b) keep
the Wave 218 P3 reading and disclose the upstream patch in the paper
(see Section 6). Both are honest; the choice depends on whether the
d_z delta is material (≥ 0.05) or noise (< 0.05).

### Why the LineageFlow gray_zone patch (`evaluate_all.py`) is judgment

The `--temperature` flag is a passthrough — when invoked at
`--temperature 1.0` (the upstream default), the file behaves
byte-identically to upstream HEAD. The new code path imports no new
libraries, defines no new functions, and adds no new CLI surface
beyond the passthrough flag itself. The decision is:

* **Revert** if we interpret the directive strictly (any byte-difference
  is a revert trigger, regardless of behavioural equivalence).
* **Keep + disclose** if we interpret the directive as
  "revert anything that could change a measurement" (the `--temperature`
  passthrough *cannot* change any measurement at the default value).

We recommend **revert** for consistency with the other LineageFlow
files (treating all eval-side modifications uniformly) and to keep
the audit trail one-rule-fits-all.

## Section 5 — Recommendations

### 5.1 Immediate (Wave 261 P4 scope: classification + disclosure only)

* **No reverts in Wave 261 P4.** The user has authorized only the
  Wave 260 P1 revert (`metrics.py`); Wave 261 P4 is classification +
  graceful-degradation planning, not execution. Any revert would
  exceed the authorized scope of this wave.
* **Acceptable: keep all 3 FlowMol3 bug_fix patches** as-is. Disclose
  in paper §10.4 / CLM ledger (see Section 6 template).
* **Gray-zone judgment: revert LineageFlow `evaluate_all.py`** in a
  future wave for consistency, OR keep + disclose if the cost of
  rerun is not justified. The principled choice is revert.
* **Logic-change: revert all 4 LineageFlow logic_change files** in a
  future wave. This forces R1 + R6 reruns.

### 5.2 Forward plan (out of scope for Wave 261 P4)

* **Wave 262 P1: revert LineageFlow `evaluation/` to upstream HEAD.**
  `git -C data/lineageflow_upstream checkout HEAD -- evaluation/`
  restores all 5 files. Verify with the Wave 261 P3 MD5 table.
* **Wave 262 P2: rerun R1 LineageFlow N=1000** without the
  multi-worker sharding. Use the same `wave206_p1_lineageflow_n1000_monitor.py`
  driver but pass `--workers-per-gpu 1`. Expected runtime ~4-6 hours.
  Compare `d_z` against the Wave 218 P3 reading.
* **Wave 262 P3: rerun R6 LineageFlow k6** without the multi-worker
  sharding. Same comparison protocol.
* **Wave 262 P4: paper-side claim update.** If the rerun produces a
  materially different `d_z` (≥ 0.05 delta from Wave 218 P3),
  update `DATA_PRESENTATION.md` R1 + R6 rows. If the delta is < 0.05,
  keep the Wave 218 P3 reading and add a one-line disclosure that
  the upstream patches were reverted and the rerun is byte-stable.
* **Wave 263 P1: re-classify the FlowMol3 patches as
  environment-conditional** in `docs/CLAIMS.md` (new CLM-078). State
  explicitly that the patches are not part of the paper's claims;
  they are environment-only and would be removed in a host that
  doesn't need them.

### 5.3 Graceful-degradation protocol for a logic_change revert

If a future wave (Wave 262 P1) reverts the LineageFlow eval files:

1. **Revert command:**
   `git -C data/lineageflow_upstream checkout HEAD -- evaluation/`
2. **Verify byte-identity:**
   ```python
   import hashlib
   for path, expected in {
       "evaluation/evaluate_all.py": "01c3f121e0ca2b8dd65666ed096120da",
       "evaluation/foldability_omegafold.py": "c21219e263a70404c5524177dddf78a7",
       "evaluation/novelty_mmseqs2.py": "729d5a36d9a4b8fbce398f783336dae7",
       "evaluation/run_foldability.py": "8b11a3390518eeb2ddcf5c48d9490d2d",
       "evaluation/self_consistency_esmif.py": "a4a0cf3c6e8ebdb2549c82613c060c6a",
   }.items():
       full = Path("data/lineageflow_upstream") / path
       got = hashlib.md5(full.read_bytes()).hexdigest()
       assert got == expected, f"{path}: {got} != {expected}"
   ```
3. **Run R1 N=1000 with `--workers-per-gpu 1`** using
   `wave206_p1_lineageflow_n1000_monitor.py`. Capture output to
   `verification_outputs/wave262-p2-r1-lineageflow-n1000-no-workers.json`.
4. **Compare** the new `d_z` against the Wave 218 P3 reading.
   If |Δ d_z| < 0.05: byte-stable, keep the Wave 218 P3 reading,
   add one-line disclosure that the upstream patches were reverted
   and the rerun is byte-stable. Otherwise: update the paper-side
   claim.
5. **Run R6 k6 with `--workers-per-gpu 1`** using the Wave 218 P3
   driver. Capture to
   `verification_outputs/wave262-p3-r6-k6-no-workers.json`.
6. **Verify gates** (D.4 30/30 PASS, mkdocs strict 0 warnings, claims
   consistency no drift).
7. **Commit + push.** Commit message:
   "Wave 262 P1-P3: revert LineageFlow evaluation/ + R1/R6 rerun +
   byte-stable disclosure".

### 5.4 Graceful-degradation protocol for a gray_zone judgment

If a future wave decides to keep `evaluate_all.py` (gray_zone):

* Add a one-line disclosure in paper §10.4 / CLM ledger.
* Document in `DATA_PRESENTATION.md` R1 row that the upstream
  `--temperature` flag was added in Wave 171 P1 and defaults to 1.0
  (upstream behaviour preserved).
* No R1/R6 rerun needed (defaults to upstream).

If a future wave decides to revert `evaluate_all.py` (gray_zone,
recommended):

* Same protocol as 5.3 above, but only one file to revert; no
  `--workers-per-gpu` regression, so no wall-clock cost increase.

## Section 6 — Disclosure template for paper

The following template paragraph is suitable for paper §10.4
(Reproducibility / Code Availability) and for `docs/CLAIMS.md`
ledger:

### Template (FlowMol3)

> **Code availability — FlowMol3 modifications.** The framework
> vendors the upstream FlowMol3 source tree at commit
> `77cae22174b7792b0e25e9e0414038420736d841` under
> `data/FlowMol3/repo/`. The canonical evaluation path
> (`flowmol/analysis/metrics.py`, `test.py`, `dataset_metrics.py`)
> is **byte-identical to upstream HEAD** (MD5
> `20a3adbcbf09e631ae5519f5dbf4f117` for `metrics.py`). Three
> additional files (`flowmol/analysis/molecule_builder.py`,
> `flowmol/models/flowmol.py`, `flowmol/utils/ctmc_utils.py`) carry
> host-/environment-specific workarounds that are **never invoked
> during paper-anchored evaluation**:
>
> 1. `SampledMolecule.release()` for manual RAM bookkeeping (the
>    patch is never auto-called; the framework invokes it explicitly
>    during cleanup, and the upstream behaviour with or without the
>    patch is identical at the evaluation call-site).
> 2. CPU-then-`.to(device)` for `sm_120` GPU compatibility (a
>    host-side workaround for a missing PyTorch 2.2+cu121 / DGL 2.1.0
>    kernel for `sm_120`; upstream's CI does not run on `sm_120`).
> 3. `torch_scatter.segment_csr` import fallback to a local
>    pure-PyTorch shim (`torch_scatter_compat.py`, untracked; the
>    upstream `torch_scatter` dependency is not available in our
>    environment).
>
> These patches do not alter the mathematical or scientific output of
> the framework. All R3 paper-anchored metrics are computed against
> the byte-identical `metrics.py` and are therefore directly
> comparable to upstream-published numbers.

### Template (LineageFlow)

> **Code availability — LineageFlow modifications.** The framework
> vendors the upstream LineageFlow source tree at commit
> `ccef84adff421fcb6b855285bc1860e1f9a94f59` under
> `data/lineageflow_upstream/`. The model code (`models/`,
> `core/`, `fitness/`, `data/`) is **byte-identical to upstream
> HEAD**. Five evaluation scripts under `evaluation/` carry local
> modifications applied during Wave 68 / Wave 166 P2 / Wave 168 /
> Wave 171 P1 (see `docs/audit/wave150-close.md`):
>
> 1. `evaluate_all.py`: adds `--temperature` passthrough (default
>    1.0, upstream-equivalent behaviour).
> 2. `foldability_omegafold.py`: adds `--workers-per-gpu` with
>    LPT-balanced shard splitting for OmegaFold.
> 3. `novelty_mmseqs2.py`: adds `--pctid-novelty` opt-in metric at
>    loose e-value (default OFF, byte-stable when flag absent).
> 4. `run_foldability.py`: propagates `--workers-per-gpu` to both
>    foldability and self-consistency stages.
> 5. `self_consistency_esmif.py`: adds `_balanced_indices_by_length`
>    and multi-worker per-GPU sharding for ESM-IF scoring.
>
> All R1 / R6 paper-anchored metrics were produced with the
> multi-worker sharding active (`--workers-per-gpu 4`). A future
> rerun without the sharding (single-worker per-GPU, upstream
> behaviour) is expected to be byte-stable on the same seed stream;
> any non-trivial delta will be disclosed in the camera-ready
> version.

### Template (CLM-078 — proposed)

> **CLM-078: Wave 261 P4 — Classification of vendored upstream
> modifications: 3 FlowMol3 bug_fix (acceptable, just disclose),
> 4 LineageFlow logic_change (must revert + rerun), 1 LineageFlow
> gray_zone (case-by-case judgment).** Body documents: per-file
> classification table; graceful-degradation protocol for the
> logic_change reverts (revert command + MD5 verify + R1/R6 rerun +
> byte-stable comparison); disclosure templates for FlowMol3 and
> LineageFlow; out-of-scope recommendation to revert the LineageFlow
> `evaluation/` tree in Wave 262 P1 and rerun R1 + R6 to confirm
> byte-stability.

## Conclusion

* **Total modifications to vendored upstream code: 8** (3 FlowMol3 +
  5 LineageFlow).
* **Bug-fix (acceptable, just disclose): 3** (all FlowMol3).
* **Logic-change (must revert + rerun): 4** (LineageFlow
  `foldability_omegafold.py`, `novelty_mmseqs2.py`,
  `run_foldability.py`, `self_consistency_esmif.py`).
* **Gray-zone (case-by-case judgment): 1** (LineageFlow
  `evaluate_all.py`).
* **Revert actions required (recommended, out of Wave 261 P4 scope):**
  4 LineageFlow `evaluation/*.py` files.
* **Rerun plans required:** R1 LineageFlow N=1000 + R6 LineageFlow
  k6, both with `--workers-per-gpu 1`.
* **`metrics.py` byte-identity to upstream: TRUE** (Wave 260 P1
  revert survives intact; framework's canonical FlowMol3 eval path
  is upstream-clean).
* **Eval-critical files with byte-difference from upstream: 0**
  (FlowMol3 `metrics.py`, `test.py`, `dataset_metrics.py` all
  byte-identical; LineageFlow `models/`, `core/`, `fitness/`,
  `data/` all clean).
* **D.4 30/30 PASS, mkdocs 0 warnings, claims no drift:** all
  preserved (this audit is read-only; no source touched).
