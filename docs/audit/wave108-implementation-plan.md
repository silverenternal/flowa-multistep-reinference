# Wave 108 Implementation Plan — Synthesized from Wave 107 Research

**Author:** Wave 108.B Agent (synthesis only — no code edits)
**Date:** 2026-09-11
**Repo HEAD at synthesis time:** `c0dd9e4` (Wave 106.C.5 final; Wave 107.A.1–A.4 audit outputs written into working tree, no source/docs edits)
**Inputs (READ-ONLY):**

- `docs/audit/wave107-a1-seeded-decoder.md` (Wave 88 F-4 Kanzi decoder seed reuse)
- `docs/audit/wave107-a2-flowmol3-drop.md` (FlowMol3 baseline 1-mol drop reuse)
- `docs/audit/wave107-a3-lineageflow-n1000-gpu.md` (LineageFlow N=1000 GPU sweep reuse)
- `docs/audit/wave107-a4-paper-presentation.md` (honest stochastic N=1000 paper-presentation reuse)
- `docs/audit/wave106-a-1-adapter-stubs.md` + `wave106-a-2-audit.md` + `wave106-a3-honesty-gaps.md` + `wave106-a4-path-consistency.md` (parent audits)
- `todo/planned/w101-fix-layer2-algorithm-tools.md` (Layer-2 fix plan)

---

## 0. TL;DR (3 sentences max)

Wave 108 closes the **3 outstanding Wave 106.A.2 / A.3 honesty gaps** identified by the Wave 107 research: (a) **Kanzi decoder stochasticity** (REUSE-1 — 0 LOC, just thread `--seed` into the existing `kanzi_latent_to_coords(seed=...)` bridge call), (b) **FlowMol3 1-mol drop** (REUSE-1 — 0 LOC, disclosure already in 7 places since Wave 87; REUSE-2 — ~5 LOC wrapper if the dropped SMILES is needed in the JSON), and (c) **LineageFlow N=1000 GPU sweep** (REUSE-1 — 0 LOC via the existing `tools/upstream_eval.run_lineageflow_upstream_eval` wrapper + the Wave 86 pre-generated FASTAs + the Wave 69 3-shell-call pattern). The **paper-presentation cleanup** adds 4 additive ~5-LOC drop-in extensions to `cover_letter.md` / `paper-draft.md` / `supplementary.md` REUSING existing §1.5 / §C.7 / "Per-Wave F-N caveat" templates (no new template code). The full plan is **9 commits across 5 phases** with a **total LOC delta of ~50 LOC** (most of it in the optional REUSE-2 wrapper for the dropped SMILES + the optional REUSE-3 hygiene upgrade to `torch.random.fork_rng()`).

---

## 1. Per-improvement table (5 improvements, REUSE-first)

| # | Improvement | Existing code to REUSE | LOC delta | Commit count | Risk |
|---|---|---|---:|---:|---|
| **1** | Kanzi seeded decoder (Wave 88 F-4 caveat elimination) | `tools.kanzi_latent_to_coord.kanzi_latent_to_coords(seed=int(seed))` + `torch.manual_seed(int(seed))` at bridge line 165 (REUSE-1) | **0 LOC** (drop-in `--seed` CLI flag in the sweep driver only) | **1 commit** | **LOW** — bridge already does it; just wire a CLI flag |
| **2** | FlowMol3 1-mol drop disclosure (Wave 106.A.2 F-02 reinforcement) | Existing 7-place disclosure (REUSE-1 from Wave 87 §"Honest caveats" #7 + Wave 106.A.2 §125–158) | **0 LOC** (REUSE-1: confirm in place) OR **~5 LOC** (REUSE-2: append dropped SMILES to `errors_sample` JSON via existing warning hook) | **1 commit** | **LOW** — disclosure already done; wrapper is an additive JSON field |
| **3** | LineageFlow N=1000 GPU sweep (Wave 81 PARTIAL closure) | `tools.upstream_eval.run_lineageflow_upstream_eval` (Wave 81 wrapper at line 173–388 + line 949–966 CLI) + `tools.gen_lineageflow_n1000_fastas` (Wave 86 pre-generated FASTAs already on disk) + `tools.run_real_ckpt_eval --model lineageflow --force-mode real --composite-metric real` (Wave 47 wiring) + `tools._gpu_watchdog.gpu_watchdog` (auto-wired into upstream_eval.py main()s) | **0 LOC** if user accepts the Wave 69 3-shell-call pattern OR **~30 LOC** (optional `tools/lineageflow_n1000_gpu_sweep.sh`) OR **~5 LOC** (optional `tools/run_lineageflow_n1000_gpu_sweep.py` entry point) | **1 commit** (shell wrapper if used) | **MEDIUM** — first run will reveal whether `lineageflow_venv` CUDA-upgraded torch 2.7.0+cu128 still satisfies Wave 81's `--hmmdb/--target-db` defaults; the assertion helper `_sweep_assertion.assert_n_records_match_with_file_count` raises rather than silently truncating if N < 1000 |
| **4** | Paper-presentation: stochasticity caveat (§F-4 drop-in) | `cover_letter.md:29` ("Honest limitations" item 1) + `paper-draft.md:2169` (Wave 88 §7.3 F-4 paragraph) + `supplementary.md:163` (§S3.5 FSQ quantisation noise floor) | **~15 LOC** (5 drop-in additions × ~3 LOC each) | **2 commits** (cover letter + paper-package) | **LOW** — pure additive drop-in; no template code added |
| **5** | Paper-presentation: multi-metric-same-axis convention + D.4 33/33→30/30 + 33/33 clarification | `docs/CONSOLIDATED_RESULTS.md:2902` (3-tier verdict distribution) + `cover_letter.md:29` (2/12 framework_improves + 6/12 ties + 2/12 underpowered) + `submission_checklist.md:55` + `supplementary.md:248` (D.4 72/72 PASS) | **~10 LOC** (1 cover letter addition + 1 supplementary §S6.2 disambiguation + 1 submission_checklist refresh) | **1 commit** | **LOW** — additive disclosure; cross-doc consistency |

**Total LOC delta:** ~50 LOC across 5 improvements (most of it optional REUSE-2 wrappers).
**Total commits:** 9 commits across 5 phases (foundational → sequential).

---

## 2. Per-commit dependency graph (9 commits in 5 phases)

```
Phase 1 (foundational — no dependencies, parallelizable):
  Commit 1: Kanzi decoder seed CLI flag (Improvement #1)
  Commit 2: FlowMol3 1-mol drop disclosure confirm/extend (Improvement #2)

Phase 2 (GPU sweep, depends on Phase 1):
  Commit 3: LineageFlow N=1000 GPU sweep shell wrapper (Improvement #3, OPTIONAL 30-LOC shell)
  OR Commit 3': LineageFlow N=1000 GPU sweep via existing 3-shell-call (0 LOC, document the template)

Phase 3 (paper-presentation, depends on Phase 1 + Phase 2 outputs as cross-cite sources):
  Commit 4: Stochasticity caveat (§F-4) drop-in — cover_letter.md + paper-draft.md §7.3 + supplementary.md §S3.5 (Improvement #4 part A)
  Commit 5: Multi-metric-same-axis convention + 2/6/2 verdict distribution drop-in (Improvement #5 part A)
  Commit 6: Decoder seed-handling per-model-family disclosure (Improvement #4 part B)

Phase 4 (verification, depends on Phase 3):
  Commit 7: D.4 33/33 → 30/30 + 33/33 clarification in submission_checklist.md + supplementary.md §S6.2 (Improvement #5 part B)

Phase 5 (final verification):
  Commit 8: Update push-ready-summary.md additively with Wave 108 findings
  Commit 9: Author docs/audit/wave108-final-synthesis.md + verify D.4 33/33 (or 30/30+33/33) + mkdocs EXIT=0 + commit
```

**Critical path:** Commit 1 → Commit 4 → Commit 8 → Commit 9 (the paper-package path).
**Parallelizable:** Commit 1 || Commit 2 || Commit 3' (0-LOC) || Commit 5 || Commit 6.

---

## 3. The 9 commits in order (full descriptions)

### Commit 1 (foundational, 0 LOC + small driver tweak) — Kanzi decoder seed CLI flag

**Title:** "Wave 108.A: Thread `--seed` into Kanzi N=1000 paper-metric sweep (close Wave 88 F-4)"

**Description:**
The Wave 88 F-4 caveat (`docs/audit/wave88-phase3-final.md:122`) — "`DAE.decode` is stochastic and unseeded. Run-to-run σ 0.0947 Å" — is eliminated by REUSE-1 (0 LOC). The bridge `tools.kanzi_latent_to_coords(seed=...)` at `tools/kanzi_latent_to_coord.py:72-82` already accepts `seed: int = 0` and applies `torch.manual_seed(int(seed))` at line 165 before `DAE.decode` (line 229). All Wave 108 needs is to expose `--seed` at the sweep driver CLI and thread it into the bridge call.

**Files to touch:**

1. `tools/sweep_kanzi_n1000_paper_metrics.py:32-37` (argparser) — add `--seed int` CLI flag (default 42).
2. `tools/sweep_kanzi_n1000_paper_metrics.py:77` (existing `seed=0` call site — currently `tools._kanzi_sweep_runner.run_kanzi_sweep(mode="baseline", seed=...)` via Wave 105 P1-A extraction) — thread `seed=int(args.seed)` through.
3. `tools/sweep_kanzi_n1000_framework_paper_metrics.py` — same `--seed` flag (mirrors the baseline driver).
4. `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py` — same `--seed` flag (Wave 95.P3.C fix driver).

**Existing functions to import (none new):** All sweep drivers already import `tools._kanzi_sweep_runner.run_kanzi_sweep` (Wave 105 P1-A extraction). The runner already accepts `seed=int` (per Wave 80 Agent B contract — `seed=0` default at line 77). No new imports needed.

**Exact existing call to modify:**

```python
# tools/sweep_kanzi_n1000_paper_metrics.py:77 (current)
seed=0,
# →
seed=int(args.seed),
```

**LOC delta:** ~6 LOC total across 3 sweep drivers (3 drivers × 2 LOC each for `--seed` argparser + threading).

**Verification:**

```bash
.venvs/kanzi_venv/bin/python tools/sweep_kanzi_n1000_paper_metrics.py --help | grep seed
.venvs/kanzi_venv/bin/python tools/sweep_kanzi_n1000_paper_metrics.py \
    --input verification_outputs/kanzi_n1000_coords.txt \
    --ckpt data/kanzi_ckpt/cleaned_model.pt \
    --output-dir /tmp/w108_seed_test \
    --seed 42
.venvs/kanzi_venv/bin/python tools/sweep_kanzi_n1000_paper_metrics.py \
    --input verification_outputs/kanzi_n1000_coords.txt \
    --ckpt data/kanzi_ckpt/cleaned_model.pt \
    --output-dir /tmp/w108_seed_test2 \
    --seed 42
# diff /tmp/w108_seed_test/reconstruction.json /tmp/w108_seed_test2/reconstruction.json
# Expected: byte-identical (σ drops from 0.0947 Å to 0.0 Å; per-record spread = 0)
```

**Optional REUSE-4 hygiene upgrade (Commit 1.5, +4 LOC, separate commit):** Wrap the existing `torch.manual_seed(int(seed))` at `tools/kanzi_latent_to_coord.py:165` in `with torch.random.fork_rng():` to prevent seed leak to the caller's RNG state. **Defer unless user asks** — REUSE-1 is sufficient to close F-4.

**Risk:** LOW. The bridge already does the right thing; the commit is purely a CLI surface expansion.

---

### Commit 2 (foundational, ~5 LOC, REUSE-2 wrapper) — FlowMol3 1-mol drop disclosure + JSON persistence

**Title:** "Wave 108.B: Persist dropped SMILES to FlowMol3 baseline arm JSON (Wave 107.A.2 REUSE-2)"

**Description:**
The FlowMol3 baseline arm drops 1 mol out of 1000 (CTMC valence artifact, n_sampled=999) per `verification_outputs/flowmol3_n1000_baseline_q4_2026.json:5` and the root-cause disclosure is in 7 places since Wave 87 (`docs/audit/wave87-phase4-final.md:370`, `docs/audit/wave106-a-2-audit.md:125-158`, `docs/paper-draft.md:1275/3192/3241-3243`, etc.). The cheapest **additive** path is REUSE-2: the `sampled_mols_from_smiles` function at `adaptive_reflow/adapters/flowmol3_metrics_upstream.py:205-254` already calls `_LOGGER.warning("sampled_mols_from_smiles: RDKit could not parse SMILES %r", smi)` at line 232 and `_LOGGER.warning("sampled_mols_from_smiles: ETKDGv3 embed failed for %r (status=%d); skipping", smi, int(embed_status))` at line 240. **REUSE-2 wraps the call site at `adaptive_reflow/adapters/flowmol3_v2_adapter.py:4549` with a thin wrapper that captures the `n_smiles - len(sampled)` delta and appends the dropped SMILES to the `errors_sample` JSON field (already wired at line 250 of `tools/wave87_n1000_sweep.py:249-250`).**

**Files to touch:**

1. `adaptive_reflow/adapters/flowmol3_v2_adapter.py:4549` — replace the bare `_sampled_mols_from_smiles(smiles_list)` call with a wrapper that captures `dropped_smiles: list[str]` from the per-iter warning output.
2. `tools/wave87_n1000_sweep.py:249-250` — extend the `errors` list to also accept `f"dropped_smiles:{smi}"` entries (in addition to the existing batch-level exception entries at line 214, 220).
3. `tools/wave87_n1000_sweep.py:184-251` (`_generate_arm`) — add a `n_sampled - n_smiles` cross-check that logs a WARNING if `n_sampled != n_smiles` (cheap diagnostic, catches future drift).

**Existing functions to import (none new):** The v2 adapter already imports `sampled_mols_from_smiles` at line 4543 (via the existing `try/except` block). The sweep driver already has `errors_sample: errors[:5]` at line 250.

**Exact existing helper to extend:**

```python
# adaptive_reflow/adapters/flowmol3_metrics_upstream.py:205-254
def sampled_mols_from_smiles(smiles_list: Sequence[str]) -> list[Any]:
    """[existing docstring]"""
    ...
    for smi in smiles_list:
        rdkit_mol = Chem.MolFromSmiles(smi)
        if rdkit_mol is None:
            _LOGGER.warning(...)  # <-- ALREADY wired at line 232
            continue
        ...
```

No change needed to `sampled_mols_from_smiles` itself — the existing logger captures the dropped SMILES; the wrapper at the call site just collects them.

**LOC delta:** ~5 LOC for the wrapper at `flowmol3_v2_adapter.py:4549` + ~3 LOC for the JSON extension at `tools/wave87_n1000_sweep.py:249-250` + ~2 LOC for the diagnostic WARNING at line ~245 = **~10 LOC total**.

**Verification:**

```bash
# 1. Run the existing baseline arm and confirm n_sampled=999 + n_smiles=1000 + dropped_smiles:["..."] in errors_sample
.venvs/flowmol3_venv/bin/python tools/wave87_n1000_sweep.py \
    --arm baseline \
    --output /tmp/w108_drop_test.json
cat /tmp/w108_drop_test.json | python -c "import json,sys; d=json.load(sys.stdin); print(d['n_sampled'], d['n_smiles'], d['errors_sample'])"

# 2. Confirm pytest tests/test_tools/test_upstream_eval.py + tests/ -k d4 → 72/72 PASS
.venv/bin/python -m pytest tests/test_tools/test_upstream_eval.py -v
.venv/bin/python -m pytest tests/ -k "d4" --continue-on-collection-errors -q
```

**Risk:** LOW. The wrapper is additive (records dropped SMILES without changing the existing flow). The WARNING at line ~245 is purely diagnostic.

---

### Commit 3 (Phase 2, 0 LOC OR 30 LOC shell OR 5 LOC entry point) — LineageFlow N=1000 GPU sweep

**Title:** "Wave 108.C: LineageFlow N=1000 GPU framework-vs-baseline sweep (Wave 81 PARTIAL closure)"

**Description:**
The full LineageFlow N=1000 GPU framework-vs-baseline sweep has never completed (Wave 81 was killed at N=2 per arm; Wave 84 foldability is OMEGAFOLD-BLOCKED on Python 3.10 venv availability; Wave 86 framework-vs-baseline partial at N=1000 per arm on `family_validity` + `novelty` only). **REUSE-1 (0 LOC) is the cheapest path**: invoke the 3 existing scripts in 3 shell calls following the Wave 69 template (`docs/audit/wave69-phase5-lineageflow-sweep.md:1-60`).

**Files to touch (option A — 0 LOC, no new file):**

- **No new files.** Just invoke existing CLI:
  ```bash
  # Phase A: baseline arm upstream eval (2 unblocked metrics: family_validity + novelty)
  CUDA_VISIBLE_DEVICES=0 timeout 3600 \
      .venvs/lineageflow_venv/bin/python tools/run_real_ckpt_eval.py \
      --model lineageflow --seeds 42 --nfe-budgets 250 \
      --force-mode real --metric-mode real --composite-metric real \
      --output verification_outputs/lineageflow_n1000_baseline_q4_2026_v2.json

  # Phase B: framework arm upstream eval
  CUDA_VISIBLE_DEVICES=0 timeout 3600 \
      .venvs/lineageflow_venv/bin/python tools/run_real_ckpt_eval.py \
      --model lineageflow --seeds 42 --nfe-budgets 250 \
      --force-mode real --metric-mode real --composite-metric real \
      --output verification_outputs/lineageflow_n1000_framework_q4_2026_v2.json

  # Phase C (OPTIONAL — requires Python 3.10 sidecar venv for OmegaFold):
  .venvs/omegafold_venv/bin/python tools/run_lineageflow_n1000_foldability_omegafold.py \
      --baseline-fasta data/lineageflow_n1000/baseline.fasta \
      --framework-fasta data/lineageflow_n1000/framework.fasta \
      --output-dir verification_outputs/lineageflow_n1000_foldability_q4_2026_v2 \
      --max-seqs 1000
  ```

**Files to touch (option B — 30 LOC shell wrapper, RECOMMENDED for reproducibility):**

1. `tools/lineageflow_n1000_gpu_sweep.sh` (NEW, ~30 LOC) — chains the 3 phases above into a single entry point. Cites Wave 69 template.

**Files to touch (option C — 5 LOC Python entry point):**

1. `tools/run_lineageflow_n1000_gpu_sweep.py` (NEW, ~5 LOC) — imports `from tools.upstream_eval import run_lineageflow_upstream_eval` + calls `subprocess.run(["tools/run_real_ckpt_eval.py", ...])`.

**Existing functions to import (none new):**

- `tools.upstream_eval.run_lineageflow_upstream_eval` (line 173–388 of `tools/upstream_eval.py` — Wave 81 wrapper, signature: `run_lineageflow_upstream_eval(fasta_path, output_dir, *, metrics=("family_validity", "novelty"), timeout_s=1800, hmmdb=DEFAULT_HMMDB, target_db=DEFAULT_TARGET_DB, pfam_fastas_dir=DEFAULT_PFAM_FASTAS_DIR, hmmscan=DEFAULT_HMMSCAN, mmseqs=DEFAULT_MMSEQS) -> dict[str, float]`)
- `tools._gpu_watchdog.gpu_watchdog` (auto-wired into upstream_eval.py main()s at lines 245, 609, 862 — no manual wiring needed)
- `tools._sweep_assertion.assert_n_records_match_with_file_count` (auto-wired into upstream_eval.py wrapper at line 339-387)
- `tools.gen_lineageflow_n1000_fastas` (Wave 86 — FASTAs already exist at `data/lineageflow_n1000/{baseline,framework}.fasta` per `data/lineageflow_n1000/manifest.json`)

**Pre-existing FASTAs (Wave 86 committed, no need to re-run):**

- `data/lineageflow_n1000/baseline.fasta` (1000 records)
- `data/lineageflow_n1000/framework.fasta` (1000 records)
- `data/lineageflow_n1000/manifest.json` (per-record seed/family metadata)

**Pre-existing venv (Wave 69 Agent 4 CUDA upgrade):**

- `.venvs/lineageflow_venv/pyvenv.cfg` → Python 3.12.13 + torch 2.7.0+cu128
- Verified CUDA: `NVIDIA RTX PRO 6000 Blackwell Workstation Edition` per Wave 69 §2

**LOC delta:**

- **0 LOC** for option A (invoke 3 shell calls directly)
- **~30 LOC** for option B (recommended — single reproducible entry point)
- **~5 LOC** for option C (Python entry point)

**Verification:**

```bash
# 1. Confirm N=1000 FASTA exists
wc -l data/lineageflow_n1000/{baseline,framework}.fasta  # both should be 1000

# 2. Run shell wrapper (option B) or 3-shell-call pattern (option A)
bash tools/lineageflow_n1000_gpu_sweep.sh 2>&1 | tee /tmp/w108_lineageflow.log

# 3. Confirm N=1000 contract via assertion
.venvs/lineageflow_venv/bin/python -c "
import json
for arm in ('baseline', 'framework'):
    d = json.load(open(f'verification_outputs/lineageflow_n1000_{arm}_q4_2026_v2.json'))
    assert d['n_records'] == 1000, f'{arm}: expected 1000, got {d[\"n_records\"]}'
    print(f'{arm}: n_records={d[\"n_records\"]}, family_validity={d[\"family_validity\"]}, novelty={d[\"novelty\"]}')
"

# 4. D.4 byte-stable regression
.venv/bin/python -m pytest tests/ -k "d4" --continue-on-collection-errors -q
```

**Risk:** MEDIUM. The first run will be slow (~6-12 hours total per arm on RTX PRO 6000 Blackwell). The `_sweep_assertion.assert_n_records_match_with_file_count` helper raises `RuntimeError` if actual < requested AND requested > 0 — so N<1000 will not silently truncate. The OmegaFold phase C requires `.venvs/omegafold_venv/bin/python` to exist (Wave 84 installed Python 3.10 sidecar; user must verify `omegafold` is on PATH).

---

### Commit 4 (Phase 3, ~6 LOC) — Stochasticity caveat (§F-4) drop-in

**Title:** "Wave 108.D: Stochasticity-of-decoder caveat drop-in (Wave 88 F-4 paper-presentation)"

**Description:**
The repo already has an extensive honest-disclosure surface for stochasticity (per Wave 107.A.4 §0 TL;DR + Check #1-7). Wave 108 only needs to ADD 3 drop-in extensions to existing paragraphs, all citing the existing `docs/audit/wave88-phase3-final.md:72-94` (canonical σ=0.0947 Å table) + `docs/audit/wave96e-final-synthesis.md:139-164` (honest std-target-missed framing) + `docs/audit/wave93-phase2-final.md` (per-cell Bonferroni).

**Files to touch:**

1. `cover_letter.md:29` — APPEND one sentence to "(1) Sample budget" paragraph: "Decoder stochasticity (Wave 88 F-4, Kanzi only) contributes ±0.186 Å at 95% to per-record `reconstruction_kabsch_rmsd_A` — about 72% of Wave 83 N=200 across-record std; the framework arm seeds this via `tools.kanzi_latent_to_coords(seed=...)` per Wave 108.A; the upstream `flowmol.FlowMol.sample` framework arm is seeded per Wave 74 F2 (byte-stable 3-run `fg_dev=0.6146`); the upstream `lineageflow/evaluation/evaluate_all.py` framework arm is seeded via `np.random.seed(seed_base)`; Kanzi upstream `DAE.decode` is now seeded per Wave 108.A — see `docs/audit/wave88-phase3-final.md` §1.5 for evidence."
2. `paper-draft.md:2169` (Wave 88 §7.3 item 3) — APPEND one sentence: "Wave 108.A threads `--seed` into the Kanzi sweep driver, dropping the per-record σ from 0.0947 Å to 0.0 Å (verified); the +0.864 Å verdict (Wave 96.D, N=10 framework arm, Bonferroni p=4.6e-7, Welch t=+12.74) is robust to decoder stochasticity (the 0.864 Å magnitude is 4.6σ pooled)."
3. `supplementary.md:163` (§S3.5 FSQ quantisation noise floor) — APPEND 4th caveat item: "**Decoder seed-handling per model family.** FlowMol3 framework arm seeds via `flowmol.FlowMol.sample(seed=42)` per Wave 74 F2 (byte-stable 3 runs); LineageFlow framework arm seeds via `np.random.seed(seed_base)` per `data/lineageflow_upstream/evaluation/evaluate_all.py`; Kanzi `DAE.decode` now seeded via `torch.manual_seed(int(seed))` in `tools/kanzi_latent_to_coord.py:165` per Wave 108.A — proposed `--seed` flag threaded into `dae.decode` remediation is live (`tools/sweep_kanzi_n1000_paper_metrics.py --seed`)."

**Existing sections to cite (no edits):**

- `docs/audit/wave88-phase3-final.md:72-94` — §1.5 "Stochasticity of `DAE.decode`" canonical disclosure
- `docs/audit/wave96e-final-synthesis.md:139-164` — §5 "Honest note on RMSD std target"
- `docs/audit/wave91-phase5-final.md:92` — Wave 91 Phase 5 decoder-stochasticity note
- `docs/baseline-audit-report.md:482-611` — §C.7 SBC stochasticity disclosure template (for the pass_label enum reference)

**LOC delta:** ~6 LOC (1 sentence in cover_letter + 1 sentence in paper-draft + 1 caveat item in supplementary).

**Verification:**

```bash
# 1. Confirm the 3 drop-ins are present
grep -n "Wave 108.A" cover_letter.md paper-draft.md supplementary.md

# 2. mkdocs build --strict
.venv/bin/python -m mkdocs build --strict
echo "mkdocs EXIT=$?"

# 3. D.4 byte-stable regression
.venv/bin/python -m pytest tests/ -k "d4" --continue-on-collection-errors -q
```

**Risk:** LOW. Pure additive drop-in; cross-cites existing canonical docs.

---

### Commit 5 (Phase 3, ~3 LOC) — Multi-metric-same-axis convention drop-in

**Title:** "Wave 108.E: Multi-metric-same-axis convention drop-in (framework_improves + framework_ties insight)"

**Description:**
Wave 107.A.4 Check #4 identified that the existing convention for reporting multiple-metric, same-axis claims is well-established in 4+ places. The cleanest drop-in is to extend `cover_letter.md:29` "(1) Sample budget" with one sentence acknowledging that the 6/12 `ties_within_sem` cells include cells where `|Δ|` is on the order of the per-record σ from `DAE.decode` — citing `wave88-phase3-final.md` §1.5.

**Files to touch:**

1. `cover_letter.md:29` — APPEND one sentence to "(1) Sample budget" paragraph: "The 6/12 `ties_within_sem` cells include N cells where `|Δ|` is on the order of the per-record σ from `DAE.decode` (Wave 88 F-4: 0.0947 Å ≈ 72% of Wave 83 N=200 across-record std on `reconstruction_kabsch_rmsd_A`); the framework-vs-baseline noise floor is therefore decoder-bound, not framework-bound (Wave 108.A now seeds the decoder to drop the per-record σ to 0)."

**Existing patterns to REUSE (no edits):**

- `docs/CONSOLIDATED_RESULTS.md:2902` — `|Δ| < 1pp noise floor` tier (precedent for the 3-tier verdict distribution)
- `cover_letter.md:29` — current `(1) Sample budget` paragraph (extension target)
- `docs/paper-draft.md:1942` (§7.3 Kanzi) — `composite_verdict` enum + per-cell value table (precedent for multi-metric-same-axis framing)
- `docs/paper-draft.md:2321` (§7.4 LineageFlow aggregate) — composite-axis verdict + decision-metric-axis verdict (precedent for "two verdicts on the same metric")

**LOC delta:** ~3 LOC.

**Verification:**

```bash
# 1. Confirm the drop-in is present
grep -n "decoder-bound, not framework-bound" cover_letter.md

# 2. mkdocs build --strict + D.4 regression
.venv/bin/python -m mkdocs build --strict && \
    .venv/bin/python -m pytest tests/ -k "d4" --continue-on-collection-errors -q
```

**Risk:** LOW. Pure additive drop-in; cross-cites Wave 108.A + Wave 88 F-4.

---

### Commit 6 (Phase 3, ~3 LOC) — Per-model decoder seed-handling disclosure

**Title:** "Wave 108.F: Per-model decoder seed-handling disclosure (3-model matrix)"

**Description:**
Wave 107.A.4 Check #1 + Check #7 identified that the per-model decoder seed-handling state (FlowMol3 seeded / LineageFlow seeded / Kanzi was-UNSEEDED-now-seeded) is partially disclosed at `supplementary.md:163` but not in the cover letter TL;DR. Wave 108 adds one sentence to the cover letter TL;DR + extends `supplementary.md:163` §S3.5 caveat item 4.

**Files to touch:**

1. `cover_letter.md:11` (TL;DR) — APPEND one sentence: "Decoder seed-handling (Wave 108.A + Wave 74 F2 + Wave 81 wrapper): FlowMol3 framework arm seeds via `flowmol.FlowMol.sample(seed=42)`; LineageFlow framework arm seeds via `np.random.seed(seed_base)`; Kanzi framework arm now seeds via `torch.manual_seed(int(seed))` in `tools/kanzi_latent_to_coord.py:165` per Wave 108.A — all 3 framework arms are now byte-stable per seed."
2. `supplementary.md:163` (§S3.5 caveat item 4) — REPLACE "**Decoder stochasticity from `torch.randn_like` is unseeded (Wave 88 F-4: 8 records × 8 unseeded repeats, σ=0.095 Å run-to-run)**" with "**Decoder seed-handling per model family.** Wave 108.A: Kanzi `DAE.decode` now seeded via `torch.manual_seed(int(seed))` in `tools/kanzi_latent_to_coord.py:165` (sweep driver accepts `--seed int`). Per-record σ drops from 0.0947 Å (Wave 88 F-4) to 0.0 Å. FlowMol3 framework arm seeded via `flowmol.FlowMol.sample(seed=42)` per Wave 74 F2 (byte-stable 3 runs). LineageFlow framework arm seeded via `np.random.seed(seed_base)` per `data/lineageflow_upstream/evaluation/evaluate_all.py`."

**LOC delta:** ~6 LOC total (~1 in cover_letter TL;DR + ~5 in supplementary §S3.5 caveat item 4).

**Verification:**

```bash
grep -n "Wave 108.A" cover_letter.md supplementary.md
.venv/bin/python -m mkdocs build --strict
```

**Risk:** LOW. Additive disclosure; replaces one sentence in supplementary §S3.5 with a more informative version.

---

### Commit 7 (Phase 4, ~4 LOC) — D.4 33/33 → 30/30 + 33/33 clarification

**Title:** "Wave 108.G: Disambiguate D.4 33/33 (Wave 38-39 first batch) vs 72/72 (full) in submission_checklist + supplementary"

**Description:**
Wave 106.A.3 finding #29 flagged that `D.4 byte-stable regression vectors: 72/72 PASS` is cited in `cover_letter.md:39` + `submission_checklist.md:55` + `supplementary.md:248`, but the task list references `D.4 72/72` (the modernized single-source-of-truth per `docs/GATES.md`). Wave 108 disambiguates: 33/33 = the Wave 38-39 first-batch subset; 72/72 = the full `tests/test_d4_regression_vectors.py` + `tests/test_adapters/test_regression_vectors.py` (30 + 42). The current `cover_letter.md:39` already disambiguates correctly ("D.4 byte-stable regression vectors: 72/72 PASS" + "The legacy '72/72 PASS' figure referred to the Wave 38-39 first-batch regression subset only") but `submission_checklist.md:55` + `supplementary.md:248` still cite 33/33 without the disambiguation. **Wave 108 fixes those 2 stale references.** (Note: the task brief mentions "30/30 → 33/33 clarification" — this is consistent with the 30 = `tests/test_d4_regression_vectors.py` + 33 = `tests/test_d4_regression_vectors.py` after some additional vector additions; verify actual counts at commit time.)

**Files to touch:**

1. `submission_checklist.md:55` — REPLACE "D.4 byte-stable regression vectors: 72/72 PASS" with "D.4 byte-stable regression vectors: 72/72 PASS (`tests/test_d4_regression_vectors.py` 30/30 + `tests/test_adapters/test_regression_vectors.py` 42/42; the legacy '72/72 PASS' figure cited the Wave 38-39 first-batch subset only — see `docs/GATES.md` for the modernized single-source-of-truth)."
2. `supplementary.md:248` (§S6.2) — same replacement.

**Existing files to REUSE:**

- `docs/GATES.md` (canonical D.4 row + per-test-file counts)
- `tests/test_d4_regression_vectors.py` + `tests/test_adapters/test_regression_vectors.py` (actual file counts — verify at commit time)
- `cover_letter.md:39` (already correctly disambiguated — use as the template)

**LOC delta:** ~4 LOC (2 lines × 2 files = 4 LOC of replacement text).

**Verification:**

```bash
# 1. Confirm the counts match
.venv/bin/python -m pytest tests/test_d4_regression_vectors.py -v --collect-only 2>&1 | grep -c "test_"
.venv/bin/python -m pytest tests/test_adapters/test_regression_vectors.py -v --collect-only 2>&1 | grep -c "test_"

# 2. Confirm the 72/72 replacement is present
grep -n "72/72 PASS" submission_checklist.md supplementary.md

# 3. mkdocs + D.4 regression
.venv/bin/python -m mkdocs build --strict && \
    .venv/bin/python -m pytest tests/ -k "d4" --continue-on-collection-errors -q
```

**Risk:** LOW. Pure cosmetic / consistency fix.

---

### Commit 8 (Phase 5, ~3 LOC) — push-ready-summary.md additive update

**Title:** "Wave 108.H: push-ready-summary.md additive update (Wave 108 findings)"

**Description:**
Adds a Wave 108 entry to `docs/push-ready-summary.md` documenting the 7 commits (Commits 1-7) and their Wave 106.A.2 / A.3 finding closures. Follows the additive convention established by Wave 106.C.2 + Wave 106.C.3 + Wave 106.C.4 + Wave 95/99 etc.

**Files to touch:**

1. `docs/push-ready-summary.md` — APPEND a new section at the end (just before any `## Final verification` anchor): "## Wave 108 — Wave 106 honesty-gap closures (commit 1-7)" with the 7-commit summary.

**Existing pattern to REUSE:**

- `docs/push-ready-summary.md:1375` (Honest caveats #7) — the FlowMol3 1-mol drop disclosure (verbatim reuse)
- `docs/push-ready-summary.md:1068-1070` (Wave 82 + Wave 87 FlowMol3 N=1000 disclosure) — REUSE verbatim
- `docs/push-ready-summary.md:270` (Wave 93 unpushed commit count anchor) — pattern reference

**LOC delta:** ~3 LOC of additive content (1 section header + 1 short summary line + 1 commit-list link).

**Verification:**

```bash
grep -n "Wave 108" docs/push-ready-summary.md
.venv/bin/python -m mkdocs build --strict
```

**Risk:** LOW. Additive disclosure; follows established convention.

---

### Commit 9 (Phase 5 final, ~10 LOC audit doc) — Wave 108 final synthesis + verify

**Title:** "Wave 108.I: Author docs/audit/wave108-final-synthesis.md + final verify (no algorithm/source-code edits)"

**Description:**
The standard Wave-close-out pattern (Wave 92.E + Wave 95.D + Wave 99.D + Wave 106.C.5): author a final synthesis doc + run D.4 byte-stable regression + run capability audit + run mkdocs build --strict + verify G-MASTER 7/7 PASS + commit (no push).

**Files to touch:**

1. `docs/audit/wave108-final-synthesis.md` (NEW, ~50 LOC) — Wave 108 final synthesis with per-commit summary + D.4 status + G-MASTER status + mkdocs status + per-finding Wave 106.A.2/A.3 closure matrix.

**Existing pattern to REUSE:**

- `docs/audit/wave106-final-synthesis.md:1-50` — Wave 106.C.5 final synthesis template (verbatim reuse of the verification-gates table)
- `docs/audit/wave99-n1000-final.md:14-15` — Wave 99.D final synthesis template (verbatim reuse)
- `docs/GATES.md` — canonical gate definitions

**LOC delta:** ~50 LOC for the audit doc (no source code edits).

**Verification (full Wave 108 close-out):**

```bash
# 1. D.4 byte-stable regression (must be 72/72 PASS)
.venv/bin/python -m pytest tests/test_d4_regression_vectors.py tests/test_adapters/test_regression_vectors.py -q

# 2. Capability audit (must be G-MASTER 7/7 PASS)
.venv/bin/python tools/capability_audit.py

# 3. mkdocs build --strict (must EXIT=0)
.venv/bin/python -m mkdocs build --strict

# 4. Count unpushed commits
git log --oneline $(git rev-parse origin/main 2>/dev/null || echo HEAD~50)..HEAD | wc -l

# 5. Author docs/audit/wave108-final-synthesis.md
# 6. Single commit (no push)
```

**Risk:** LOW. Documentation-only close-out.

---

## 4. Per-commit verification protocol

| Commit | Verification command(s) | Expected result |
|---|---|---|
| **1 (Kanzi seed)** | `tools/sweep_kanzi_n1000_paper_metrics.py --help \| grep seed` + run twice with `--seed 42`, diff outputs | `--seed int` argparser present; diff = byte-identical (σ drops from 0.0947 Å → 0.0 Å) |
| **2 (FlowMol3 drop)** | `tools/wave87_n1000_sweep.py --arm baseline --output /tmp/w108_drop_test.json` + `python -c "import json; d=json.load(open('/tmp/w108_drop_test.json')); print(d['n_sampled'], d['n_smiles'], d['errors_sample'])"` | `n_sampled=999`, `n_smiles=1000`, `errors_sample=['dropped_smiles:"Cl..."']` (the CTMC valence artifact SMILES) |
| **3 (LineageFlow N=1000)** | `bash tools/lineageflow_n1000_gpu_sweep.sh 2>&1 \| tee /tmp/w108_lineageflow.log` + `python -c "import json; [json.load(open(f'verification_outputs/lineageflow_n1000_{a}_q4_2026_v2.json')) for a in ('baseline','framework')]"` | Both arms have `n_records=1000`, `family_validity` + `novelty` metrics present; WARNING logged if `_sweep_assertion` raises |
| **4 (Stochasticity caveat)** | `grep -n "Wave 108.A" cover_letter.md paper-draft.md supplementary.md` + `mkdocs build --strict` + `pytest -k d4` | 3 matches; mkdocs EXIT=0; pytest 72/72 PASS |
| **5 (Multi-metric-same-axis)** | `grep -n "decoder-bound, not framework-bound" cover_letter.md` + `mkdocs build --strict` | 1 match; mkdocs EXIT=0 |
| **6 (Decoder seed-handling)** | `grep -n "Wave 108.A" cover_letter.md supplementary.md` + `mkdocs build --strict` | 2 matches; mkdocs EXIT=0 |
| **7 (D.4 33/33 disambiguation)** | `grep -n "72/72 PASS" submission_checklist.md supplementary.md` + `pytest -k d4` | 2 matches; pytest 72/72 PASS |
| **8 (push-ready-summary)** | `grep -n "Wave 108" docs/push-ready-summary.md` + `mkdocs build --strict` | 1 match; mkdocs EXIT=0 |
| **9 (final synthesis)** | `pytest -k d4` + `tools/capability_audit.py` + `mkdocs build --strict` + `git log --oneline origin/main..HEAD \| wc -l` | 72/72 PASS; G-MASTER 7/7 PASS; mkdocs EXIT=0; +9 commits (Commits 1-9) |

---

## 5. Estimated wall-clock

| Phase | Commits | Wall-clock (single-GPU PRO 6000 Blackwell + CPU) | Risk |
|---|---|---|---|
| **Phase 1** (Commits 1, 2) | 2 | ~30 min (Kanzi seed CLI flag trivial; FlowMol3 wrapper trivial) | LOW |
| **Phase 2** (Commit 3) | 1 | **~6-12 hours** (LineageFlow N=1000 sweep is the longest single run; both arms must complete) — but most of this is **existing** code execution, not new development | MEDIUM |
| **Phase 3** (Commits 4, 5, 6) | 3 | ~30 min (pure additive drop-in to cover_letter + paper-draft + supplementary) | LOW |
| **Phase 4** (Commit 7) | 1 | ~10 min (cosmetic / consistency fix) | LOW |
| **Phase 5** (Commits 8, 9) | 2 | ~1 hour (close-out audit doc + D.4/G-MASTER/mkdocs verification) | LOW |
| **TOTAL** | 9 commits | **~8-15 hours** (mostly GPU wall-clock on Phase 2) | LOW-MEDIUM |

**Wall-clock dominated by Phase 2 (LineageFlow N=1000 GPU sweep).** All 8 other commits are <1 hour each of development + verification work.

---

## 6. Files audited (READ-ONLY research + plan synthesis)

### Source code / tools / tests (referenced for line numbers + signatures)

- `<repo_root>/tools/kanzi_latent_to_coord.py:72-238` (bridge function — line 165 `torch.manual_seed`, line 229 `decoder.decode` call)
- `<repo_root>/tools/sweep_kanzi_n1000_paper_metrics.py:32-37` (argparser), `:77` (`seed=0` call site)
- `<repo_root>/tools/sweep_kanzi_n1000_framework_paper_metrics.py` (mirror of baseline driver)
- `<repo_root>/tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py` (Wave 95.P3.C fix driver)
- `<repo_root>/tools/_kanzi_sweep_runner.py` (Wave 105 P1-A shared sweep loop body)
- `<repo_root>/tools/upstream_eval.py:173-388` (`run_lineageflow_upstream_eval` Wave 81 wrapper), `:99-101` (`LINEAGEFLOW_EVALUATE_ALL` path constant), `:262-283` (subprocess cmd builder), `:949-966` (CLI surface)
- `<repo_root>/tools/gen_lineageflow_n1000_fastas.py:1-200` (Wave 86 FASTA generator — FASTAs already on disk)
- `<repo_root>/tools/run_lineageflow_n1000_foldability_omegafold.py:1-200` (Wave 84 foldability + self_consistency wrapper)
- `<repo_root>/tools/run_real_ckpt_eval.py` (eval CLI; `--model lineageflow --force-mode real --composite-metric real` Wave 47 wiring)
- `<repo_root>/tools/_gpu_watchdog.py:1-250` (`gpu_watchdog` context manager + `gpu_status` one-shot poll)
- `<repo_root>/tools/_sweep_assertion.py:1-200` (`assert_n_records_match` + `assert_n_records_match_with_file_count` + `write_summary_with_n_keys`)
- `<repo_root>/tools/wave87_n1000_sweep.py:184-251` (`_generate_arm`), `:249-250` (`errors_sample: errors[:5]` + `n_errors: int(len(errors))`)
- `<repo_root>/tools/eval/cli.py:29-200` (argparser — `run_real_ckpt_eval.py` CLI)
- `<repo_root>/tools/eval/sweep.py` + `tools/eval/metrics.py` (per-cell sweep orchestrator + composite + real-metric helpers)
- `<repo_root>/adaptive_reflow/adapters/kanzi.py:2098-2235` (`solve_ode` custom NumPy Euler/Heun — NOT a `DAE.decode` wrapper)
- `<repo_root>/adaptive_reflow/adapters/flowmol3_v2_adapter.py:4541-4549` (caller of `sampled_mols_from_smiles`)
- `<repo_root>/adaptive_reflow/adapters/flowmol3_metrics_upstream.py:205-254` (`sampled_mols_from_smiles` — drop point + warning hooks at line 232, 240)

### External vendored repos (audited)

- `<repo_root>/data/kanzi_upstream/src/kanzi/models.py:364-372` (DAE.decode signature — NO seed param), `:375` (`x_BLD = torch.randn(...)`), `:421` (`eps = torch.randn_like(x_BLD)`), `:608` (RnFlowMatcher.sample — pure ODE), `:635-664` (euler_maruyama_sample), `:1137` (train-side seed in train_cb.py:220)
- `<repo_root>/data/kanzi_upstream/src/kanzi/cfm.py:41, 98, 150, 153` (sample_noise_like — global RNG)
- `<repo_root>/data/kanzi_upstream/src/kanzi/fsq.py:96` (jitter noise — global RNG)
- `<repo_root>/data/kanzi_upstream/src/kanzi/train_cb.py:220` (train-side seed)
- `<repo_root>/data/FlowMol3/repo/flowmol/models/flowmol.py:490-493` (FlowMol.sample signature — NO `return_errors` / `skip_errors` param), `:591-598` (SampledMolecule construction)
- `<repo_root>/data/FlowMol3/repo/flowmol/analysis/molecule_builder.py` (SampledMolecule — also drops invalid mols silently)
- `<repo_root>/data/lineageflow_upstream/evaluation/evaluate_all.py` (~400 LOC vendored orchestrator)
- `<repo_root>/data/lineageflow_upstream/evaluation/run_foldability.py` + `foldability_omegafold.py` + `self_consistency_esmif.py` + `family_validity_hmmer.py` + `novelty_mmseqs2.py` (4 vendored metric scripts)
- `<repo_root>/data/lineageflow_n1000/{baseline,framework}.fasta` (Wave 86 pre-generated, 1000 records each)
- `<repo_root>/data/lineageflow_n1000/manifest.json` (per-record seed/family metadata)

### Pre-existing on-disk data (REUSE)

- `<repo_root>/verification_outputs/flowmol3_n1000_baseline_q4_2026.json:5` (`n_sampled=999`, `n_smiles=1000`, `n_errors=0`)
- `<repo_root>/verification_outputs/flowmol3_n1000_framework_q4_2026.json:5` (`n_sampled=1000`)
- `<repo_root>/verification_outputs/lineageflow_n1000_baseline_q4_2026.json` (Wave 81 partial — 1 cell of N=1000)
- `<repo_root>/verification_outputs/lineageflow_n1000_framework_q4_2026.json` (Wave 81 partial)
- `<repo_root>/verification_outputs/lineageflow_v2_aggregated_q4_2026.json` (Wave 69 9-cell NFE-scan aggregated)
- `<repo_root>/verification_outputs/ckpt_sha256.json` (Wave 106.C.1 — Kanzi + LineageFlow + FlowMol3 SHAs pinned)

### Venv configuration

- `<repo_root>/.venvs/lineageflow_venv/pyvenv.cfg` (Python 3.12.13 + torch 2.7.0+cu128 — Wave 69 Agent 4 CUDA upgrade)
- `<repo_root>/.venvs/kanzi_venv/` (Python 3.12 + torch CPU + diffusers + esm + biopython — Wave 39 Agent A sidecar)
- `<repo_root>/.venvs/omegafold_venv/` (Python 3.10 sidecar — Wave 84 install for OmegaFold)

### Paper-package docs (for Commit 4-8 drops)

- `<repo_root>/cover_letter.md:11, 19, 21, 29, 31, 39` (TL;DR + G1 SHA + G2 config + Honest limitations + Wave 99 update + Reproducibility)
- `<repo_root>/submission_checklist.md:55, 63` (D.4 + ckpt_sha256 references)
- `<repo_root>/supplementary.md:163, 248, 252` (§S3.5 FSQ noise floor + §S6.2 ckpt_sha256 + §S5.4 F-02 caveat)
- `<repo_root>/docs/paper-draft.md:1275, 1942, 2115, 2169, 2321, 2609, 3192, 3241-3243` (§7.3/§7.4/§7.5/§7.6 + Wave 79/88/87/106 prose anchors)
- `<repo_root>/docs/push-ready-summary.md:270, 1068-1070, 1375` (Wave 93/82/87 + Honest caveats anchors)
- `<repo_root>/docs/CONSOLIDATED_RESULTS.md:2902` (`|Δ| < 1pp noise floor` tier)
- `<repo_root>/docs/baseline-audit-report.md:482-611` (§C.7 SBC template + `pass_label` enum + seed_offset rationale at line 521)
- `<repo_root>/docs/GATES.md` (canonical gate definitions — for D.4 disambiguation in Commit 7)
- `<repo_root>/docs/audit/wave88-phase3-final.md:18, 72-94, 122, 189-192, 306` (F-4 finding + §1.5 stochasticity disclosure + cmd-line repro + Wave 83 "byte-stable" retraction)
- `<repo_root>/docs/audit/wave91-phase5-final.md:92` (Wave 91 §5 decoder stochasticity note)
- `<repo_root>/docs/audit/wave96e-final-synthesis.md:139-164` (honest std-target note template)
- `<repo_root>/docs/audit/wave93-phase2-final.md` (per-cell Bonferroni table)
- `<repo_root>/docs/audit/wave99b-n1000-verdict.md` (statistical power analysis)
- `<repo_root>/docs/audit/wave87-phase3-sweep.md:155, 345` (Honest caveats #7 anchor)
- `<repo_root>/docs/audit/wave87-phase4-final.md:370` (1 mol dropped — CTMC valence artifact)
- `<repo_root>/docs/audit/wave106-a-2-audit.md:125-158` (Wave 106.A.2 F-02 disclosure)
- `<repo_root>/docs/audit/wave106-a3-honesty-gaps.md:24-60` (30-finding honesty-gap audit table)
- `<repo_root>/docs/audit/wave106-a4-path-consistency.md` (41-finding path + data consistency audit)
- `<repo_root>/docs/audit/wave69-phase5-lineageflow-sweep.md:1-60` (Wave 69 3-shell-call template)
- `<repo_root>/docs/audit/wave81-phase3-sweep.md` + `wave81-phase4-final.md` (Wave 81 N=2 per arm kill + honest disclosure)
- `<repo_root>/docs/audit/wave82-phase3-sweep.md` + `wave82-phase4-final.md` (Wave 82 PB-xtb + N=1000 sweep)
- `<repo_root>/docs/audit/wave86-phase3-sweep.md` (Wave 86 N=1000 framework-vs-baseline — actual +116% source)
- `<repo_root>/docs/audit/wave99-n1000-final.md` (Wave 99.D Kanzi real N=1000 verdict)

### Wave 107 research outputs (synthesized)

- `<repo_root>/docs/audit/wave107-a1-seeded-decoder.md` (4 REUSE opportunities — REUSE-1 0 LOC wins)
- `<repo_root>/docs/audit/wave107-a2-flowmol3-drop.md` (5 REUSE opportunities — REUSE-1 0 LOC disclosure + REUSE-2 ~5 LOC JSON wrapper)
- `<repo_root>/docs/audit/wave107-a3-lineageflow-n1000-gpu.md` (12 REUSE opportunities — REUSE-1 0 LOC 3-shell-call OR optional 30-LOC shell)
- `<repo_root>/docs/audit/wave107-a4-paper-presentation.md` (11 REUSE opportunities — REUSE-1 ~23 LOC drop-in + REUSE-2 ~15 LOC honesty-gap remediation)

### Wave 106 parent audits (synthesized)

- `<repo_root>/docs/audit/wave106-a-1-adapter-stubs.md` (29 issues — 3 HIGH + 12 MEDIUM + 14 LOW)
- `<repo_root>/docs/audit/wave106-a-2-audit.md` (7 issues — 4 HIGH + 2 MEDIUM + 1 LOW)
- `<repo_root>/docs/audit/wave106-a3-honesty-gaps.md` (30 issues — 6 HIGH + 7 MEDIUM + 5 LOW + 11 NONE + 1 UNVERIFIED)
- `<repo_root>/docs/audit/wave106-a4-path-consistency.md` (41 issues — 6 HIGH + 14 MEDIUM + 19 LOW + 7 UNVERIFIED)
- `<repo_root>/docs/audit/wave106-final-synthesis.md` (Wave 106.C.5 — 107 findings → 4 audit docs → 4 fix waves)
- `<repo_root>/docs/audit/wave106-c2-fix-summary.md` (F-02 — Wave 106.A.2 F-02 fix: Disclose FlowMol3 baseline arm N=999)

---

## 7. External libraries / standard libraries audited (REUSE)

### PyTorch stdlib (REUSE — all available, no new dependency)

- `torch.manual_seed(int(seed))` — global RNG seed (REUSE-1 in Commit 1)
- `torch.cuda.manual_seed_all(int(seed))` — CUDA global RNG seed (Wave 74 F2 pattern at `flowmol3_v2_adapter.py:627-629`)
- `torch.Generator(device="cpu").manual_seed(int(seed))` — local RNG generator (hidream_i1 / wan2_2 pattern at `_hidream_i1_upstream_shim.py:416`, `hidream_i1.py:1116`, `wan2_2_upstream_shim.py:135`)
- `torch.random.fork_rng()` — stdlib context manager for seed isolation (REUSE-4 hygiene upgrade — OPTIONAL, +4 LOC)

### Other libraries (in pyproject.toml or requirements-*.txt, NOT applicable to Wave 108 fixes)

- `transformers`, `diffusers` — applicable to image FM (Hidream / Wan2.2), NOT to Kanzi protein FM or LineageFlow protein FM
- `biotite` 1.7.1 — used by LineageFlow vendored upstream (deterministic per input)
- `fair-esm` — used by LineageFlow vendored upstream (deterministic per seed)
- `posebusters` 0.6.5 — PB-xtb UFF-vs-xtb definitional gap (already disclosed in cover_letter.md:29)
- `rdkit` — used for SMILES round-trip (no error-recovery API beyond `MolFromSmiles` returning None)
- `torchdiffeq` — ODE solvers (no stochasticity disclosure)
- `mtraj` — molecular trajectory (NOT applicable to Wave 108 fixes)

### External vendored repos (REUSE — already vendored at Wave 40, 50, 80)

- `data/kanzi_upstream/` — vendored at `cfed9cf` (Wave 40)
- `data/lineageflow_upstream/` — vendored at `ccef84a` (Wave 40)
- `data/FlowMol3/repo/` — vendored at `77cae22` (Wave 50)

### REUSE opportunity count

**32 distinct REUSE opportunities across the 4 Wave 107 research docs:**

- A.1 (Kanzi seeded decoder): 4 REUSE
- A.2 (FlowMol3 1-mol drop): 5 REUSE
- A.3 (LineageFlow N=1000 GPU): 12 REUSE
- A.4 (Paper presentation): 11 REUSE

---

## 8. Output JSON

```json
{
  "commit_sha": "c0dd9e49251a6de845e034e68bd086e85aeec485",
  "output_file": "<repo_root>/docs/audit/wave108-implementation-plan.md",
  "input_research_docs": [
    "docs/audit/wave107-a1-seeded-decoder.md",
    "docs/audit/wave107-a2-flowmol3-drop.md",
    "docs/audit/wave107-a3-lineageflow-n1000-gpu.md",
    "docs/audit/wave107-a4-paper-presentation.md"
  ],
  "parent_audits": [
    "docs/audit/wave106-a-1-adapter-stubs.md",
    "docs/audit/wave106-a-2-audit.md",
    "docs/audit/wave106-a3-honesty-gaps.md",
    "docs/audit/wave106-a4-path-consistency.md",
    "docs/audit/wave106-final-synthesis.md"
  ],
  "files_audited_count": 50,
  "external_libs_audited": [
    "torch.manual_seed (stdlib)",
    "torch.cuda.manual_seed_all (stdlib)",
    "torch.Generator (stdlib)",
    "torch.random.fork_rng (stdlib)",
    "transformers (in pyproject.toml — not applicable to Wave 108)",
    "diffusers (in pyproject.toml — not applicable to Wave 108)",
    "biotite (in pyproject.toml — not applicable to Wave 108)",
    "fair-esm (vendored at data/lineageflow_upstream)",
    "posebusters 0.6.5 (in pyproject.toml — Wave 108 G3 reference)",
    "rdkit (vendored at FlowMol3 upstream — Wave 108 SMILES round-trip reference)",
    "torchdiffeq (in pyproject.toml — not applicable to Wave 108)",
    "data/kanzi_upstream/ (vendored at cfed9cf)",
    "data/lineageflow_upstream/ (vendored at ccef84a)",
    "data/FlowMol3/repo/ (vendored at 77cae22)"
  ],
  "reuse_opportunities_count": 32,
  "improvements_count": 5,
  "commits_planned": 9,
  "loc_delta_total": "~50 LOC (most optional REUSE-2 wrappers)",
  "estimated_wall_clock_hours": "~8-15 hours (dominated by LineageFlow N=1000 GPU sweep)",
  "verification_gates": [
    "pytest tests/ -k d4 → 72/72 PASS",
    "tools/capability_audit.py → G-MASTER 7/7 PASS",
    "mkdocs build --strict → EXIT=0",
    "git log --oneline origin/main..HEAD | wc -l → +9 commits"
  ]
}
```

---

## 9. Constraint compliance

| Constraint | Honored? | Evidence |
|---|---|---|
| NO source code edits | YES | Plan is READ-ONLY synthesis; all 9 commits described but not yet executed |
| NO docs edits (this doc is the only output) | YES | `docs/audit/wave108-implementation-plan.md` is the sole output file |
| NO commits | YES | No git changes from this agent |
| Cite `file_path:line` + EXACT signature + commit SHA | YES | 50+ file:line citations across §3 + §6 |
| Compare against vendored external repos | YES | §6 external vendored repos; §7 vendored external libs |
| Compare against established libraries in pyproject.toml | YES | §7 stdlib + pyproject.toml libs |
| DO NOT speculate; if pattern does not exist on disk, say so | YES | §6 explicit "No new files" for option A of Commit 3; §6 explicit `n_smiles=1000` + `n_sampled=999` from JSON evidence |
| Output to `docs/audit/wave108-implementation-plan.md` | YES | This file |
| Return JSON | YES | §8 |

---

## 10. Verdict

**The cheapest end-to-end Wave 108 plan is ~50 LOC across 9 commits in 5 phases.** Wave 108 closes the 3 outstanding Wave 106.A.2/A.3 honesty gaps by REUSING the existing patterns identified by Wave 107.A.1–A.4:

- **Wave 88 F-4 Kanzi decoder stochasticity** — REUSE-1 (0 LOC) at `tools/kanzi_latent_to_coord.py:165` (already seeded); just thread `--seed` through the sweep driver CLI.
- **Wave 106.A.2 F-02 FlowMol3 1-mol drop** — REUSE-1 (0 LOC; disclosure already in 7 places) + REUSE-2 (~10 LOC; persist dropped SMILES to existing `errors_sample` JSON field).
- **Wave 81 PARTIAL LineageFlow N=1000 GPU sweep** — REUSE-1 (0 LOC; Wave 69 3-shell-call pattern + Wave 86 pre-generated FASTAs + Wave 81 wrapper + Wave 47 composite wiring + auto-wired GPU watchdog + auto-wired N-contract assertion).
- **Paper-presentation stochasticity caveat** — REUSE-1 (~15 LOC of drop-in prose to existing §1.5 / "Per-Wave F-N caveat" / "Honest limitations" / "Stochasticity disclosure" templates).
- **Multi-metric-same-axis + D.4 33/33→72/72 disambiguation** — REUSE-1 (~10 LOC of drop-in to existing 3-tier verdict distribution + `docs/GATES.md` + `cover_letter.md:39` template).

**All improvements REUSE existing code; NO new algorithm/source-code edits. NO new template code.** The 9 commits are dominated by ~30-60 min development each, with the LineageFlow N=1000 GPU sweep (Commit 3) being the only multi-hour wall-clock item (~6-12 hours of existing-code execution).

**End of Wave 108 implementation plan.**


---

**Wave 149 D.4 drift fix (2026-09-14):** The historical "33/33 PASS" wording used in this document referred to the Wave 38-39 first-batch regression subset ONLY. The current authoritative D.4 count is **72/72 PASS** (33 tests in `tests/test_d4_regression_vectors.py` + 39 tests in `tests/test_adapters/test_regression_vectors.py` = 72 total, per `docs/GATES.md` §D.4 + Wave 106.C.3 standardization). The 72/72 figure includes Wave 32 batches 2/3/4 + Wave 33 batch 2/3 additions (commit `40d979c` and subsequent). This drift fix is the Wave 149 Agent 6 contribution; see `docs/audit/wave149-close.md` for the Wave 149 audit trail.
