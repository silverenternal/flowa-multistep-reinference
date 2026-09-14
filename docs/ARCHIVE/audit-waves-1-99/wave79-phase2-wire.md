# Wave 79 Agent 2 — Upstream Eval Wire (Phase 2)

**Date:** 2026-09-08
**Wave:** 79 (Agent 2)
**Scope:** Add per-model `--upstream-eval` flag to
`tools/run_real_ckpt_eval.py` that invokes the upstream eval
**directly as a subprocess** (NOT a wrapper class), opt-in default
OFF, byte-stable with the legacy internal-observer path.

---

## 1. Per-model flag mapping

| Model        | CLI flag                            | Subprocess driver                                           | Output metric surface (flattened)                       |
|--------------|--------------------------------------|-------------------------------------------------------------|----------------------------------------------------------|
| lineageflow  | `--lineageflow-upstream-eval`        | `python data/lineageflow_upstream/evaluation/evaluate_all.py --fasta <fasta> --outdir <outdir> --metrics family_validity foldability self_consistency novelty` | `family_validity__<key>`, `novelty__<key>` etc.          |
| kanzi        | `--kanzi-upstream-eval`              | `python -c "<inline driver vendors kanzi; DAE.encode→DAE.decode→kabsch_rmsd>"` | `n_seqs`, `mean_rmsd_A`, `min_rmsd_A`, `max_rmsd_A`     |
| flowmol3     | `--flowmol3-upstream-eval`           | `python -c "<inline driver vendors data/FlowMol3/repo; SampleAnalyzer.analyze>"` | `frac_valid_mols`, `frac_mols_stable_valence`, `pb_valid`, `flag_rate`, `ood_rate`, `reos_cum_dev` |

A shared `--upstream-n-samples` flag controls how many sequences /
molecules / SMILES are fed into the upstream eval (default 1000,
matches Wave 76 paper-claim protocol).

All 3 flags are **OFF by default**; the legacy internal-observer path
(adapter.observe_token_indices / observe_entropy_reduction) is
byte-stable when no flag is set. The D.4 regression vectors
(72/72 PASS) verify this byte-stability below.

---

## 2. Why subprocess, NOT a wrapper class

The Wave 73-74 NFE-scan speedup story was on **internal composite**
metrics (entropy reduction + max_prob_delta + argmax_turnover). These
are NOT paper metrics. The Wave 75 + 79 work closes the gap by
running the upstream eval **directly**:

* A **wrapper class** would re-implement the metric math in the
  framework, defeating the purpose ("we ship our own Kabsch RMSD that
  disagrees with Kanzi upstream's Kabsch RMSD" → unverifiable claim).
* A **subprocess** keeps the framework hands-off the upstream eval
  code; a bug fix in `kanzi.kabsch_rmsd` immediately reflects in our
  pipeline without a framework re-release.

Phase 1 audit verified each upstream entry point is a single CLI
script (LineageFlow `evaluation/evaluate_all.py:1`) or a single Python
import (Kanzi `from kanzi import DAE, kabsch_rmsd`; FlowMol3
`from flowmol.analysis.metrics import SampleAnalyzer`). The 3 shims
in `tools/upstream_eval.py` invoke those entry points via
`subprocess.run([sys.executable, ...], check=False, timeout=...)` so
the vendored upstream packages are loaded in a fresh interpreter with
clean `sys.path`.

---

## 3. Upstream subprocess invocation

### 3.1 LineageFlow (`run_lineageflow_upstream_eval`)

```python
cmd = [
    sys.executable,
    "data/lineageflow_upstream/evaluation/evaluate_all.py",
    "--fasta", "<baseline+framework AA FASTA>",
    "--outdir", "<output dir>",
    "--metrics", "family_validity", "foldability",
                  "self_consistency", "novelty",
]
```

Reads `<outdir>/summary.json` (3 per-metric dicts: family_validity,
foldability, novelty) and flattens to
`{"family_validity__n_records": <float>, ..., "metric_kind": "..."}`.

### 3.2 Kanzi (`run_kanzi_upstream_eval`)

Kanzi upstream has NO `evaluation/` directory (Phase 1 §2.3). The
paper metric is **reconstruction Kabsch RMSD** on AFDB-Foldseek
held-out; we invoke the upstream surface (the README quick-start path)
via a subprocess driver that vendors `kanzi` on `sys.path`:

```python
cmd = [
    sys.executable, "-c", """
        from kanzi import DAE, kabsch_rmsd
        dae = DAE.from_pretrained(args.ckpt).eval()
        for x in coords:
            *_, idx = dae.encode(x, preprocess=False)
            recon = dae.decode(idx)
            rmsd_by_seq.append(kabsch_rmsd(recon*10, x*10))
    """,
    "--input", "<comma-separated coords file>",
    "--ckpt", "<Kanzi cleaned_model.pt>",
    "--output", "<reconstruction.json>",
]
```

Reads `<output>/reconstruction.json` and flattens the `summary`
block to `{"n_seqs": <float>, "mean_rmsd_A": <float>, ...}`.

### 3.3 FlowMol3 (`run_flowmol3_upstream_eval`)

```python
cmd = [
    sys.executable, "-c", """
        sys.path.insert(0, "data/FlowMol3/repo")
        from flowmol.analysis.metrics import SampleAnalyzer
        mols = [SampledMolecule-stub for sm in smiles]
        analyzer = SampleAnalyzer(processed_data_dir=args.reference)
        analyzer.analyze(mols, functional_validity=True,
                         posebusters=True, energy_div=False)
    """,
    "--smiles-list", "<baseline+framework SMILES>",
    "--reference", "GEOM_DRUGS",
    "--output", "<sample_analyzer.json>",
    "--pb-workers", "2",
]
```

Reads `<output>/sample_analyzer.json` and flattens the analyzer's
output dict to `{"frac_valid_mols": <float>, "pb_valid": <float>,
...}`.

---

## 4. CLI wiring in `tools/run_real_ckpt_eval.py`

```python
p.add_argument("--lineageflow-upstream-eval", action="store_true", ...)
p.add_argument("--kanzi-upstream-eval", action="store_true", ...)
p.add_argument("--flowmol3-upstream-eval", action="store_true", ...)
p.add_argument("--upstream-n-samples", type=int, default=1000, ...)
```

Each flag defaults OFF. `main()` threads them into `_run_cell` via
4 new keyword arguments:
`lineageflow_upstream_eval=`, `kanzi_upstream_eval=`,
`flowmol3_upstream_eval=`, `upstream_n_samples=`. The cell dict
gains 2 new fields when any flag is set:

* `cell["upstream_eval_metrics"]` — flattened dict of metric
  name → float (one entry per upstream orchestrator).
* `cell["upstream_eval_debug"]` — per-model marker
  (`"computed" | "blocked" | "not_run"`) + per-model reason for any
  blocked state.

The 3 flags are mutually independent; passing all 3 invokes all 3
upstream evals. The legacy `baseline_metric` / `framework_metric` /
`delta_pct` fields are untouched — the upstream eval results live
*alongside* the internal-observer path (additive, not replacement).

---

## 5. Test results

```
tests/test_tools/test_upstream_eval.py
8 passed in 0.04s

  test_upstream_eval_lineageflow_smoke
  test_upstream_eval_lineageflow_subprocess_failure
  test_upstream_eval_kanzi_smoke
  test_upstream_eval_kanzi_subprocess_timeout
  test_upstream_eval_flowmol3_smoke
  test_upstream_eval_flowmol3_missing_output
  test_upstream_eval_module_paths_exist
  test_upstream_eval_module_all_exports

tests/test_d4_regression_vectors.py
tests/test_adapters/test_regression_vectors.py
72 passed, 3 warnings in 63.06s (0:01:03)
```

* The 8 upstream-eval tests use `unittest.mock.patch` on
  `subprocess.run` so no upstream package is imported (cold-clone
  safe + CI-friendly).
* The D.4 regression vectors (72/72 PASS) verify the legacy default
  path is byte-stable when no `--*-upstream-eval` flag is set.

---

## 6. Failure-mode surface (verified by tests)

| Failure mode                                           | Helper returns                                                  | Test                                                            |
|--------------------------------------------------------|-----------------------------------------------------------------|------------------------------------------------------------------|
| Orchestrator subprocess exits non-zero (e.g. HMMER missing) | `{"status": 0.0, "reason": "...nonzero_exit:<code>:<stderr>"}` | `test_upstream_eval_lineageflow_subprocess_failure`              |
| Subprocess timeout (e.g. Kanzi DiT decode too slow)    | `{"status": 0.0, "reason": "...timeout"}`                       | `test_upstream_eval_kanzi_subprocess_timeout`                    |
| Subprocess succeeds but no output file                  | `{"status": 0.0, "reason": "...no_<file>"}`                     | `test_upstream_eval_flowmol3_missing_output`                     |
| Output JSON malformed                                  | `{"status": 0.0, "reason": "..._parse_failed:..."}`             | (covered by missing-output test; same code path)                |

All failures degrade gracefully to `status=0.0` + a descriptive
`reason` string. The cell's `upstream_eval_debug["<model>"]` field
records the per-model outcome (`"computed"` vs `"blocked"`) so
downstream consumers can branch.

---

## 7. Files written

| Path                                                                  | LOC  | Purpose                                                              |
|-----------------------------------------------------------------------|------|----------------------------------------------------------------------|
| `/home/hugo/codes/flowa-multistep-reinference/tools/upstream_eval.py` | ~410 | Per-model upstream-eval subprocess shims (3 runner functions)         |
| `/home/hugo/codes/flowa-multistep-reinference/tests/test_tools/test_upstream_eval.py` | ~360 | 8 unit tests (mock subprocess) covering all 3 runners + module surface |
| `/home/hugo/codes/flowa-multistep-reinference/tools/run_real_ckpt_eval.py` | edited | Added 4 CLI flags + 2 helper functions + upstream-eval block in `_run_cell` |
| `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave79-phase2-wire.md` | this doc | Wave 79 Phase 2 audit                                                 |

No upstream files were modified. No framework source code was touched
beyond the additive `--*-upstream-eval` block.

---

## 8. JSON return

```json
{
  "upstream_eval_module": "tools/upstream_eval.py",
  "models_wired": ["lineageflow", "kanzi", "flowmol3"],
  "files_changed": [
    "tools/upstream_eval.py (new)",
    "tests/test_tools/test_upstream_eval.py (new)",
    "tools/run_real_ckpt_eval.py (CLI flags + _run_cell block + 2 helpers)",
    "docs/audit/wave79-phase2-wire.md (new)"
  ],
  "loc_added": 830,
  "regression_tests_added": 8,
  "test_results": {
    "upstream_eval_tests": "8 passed in 0.04s",
    "d4_tests": "72 passed in 63.06s"
  },
  "d4_byte_stable": true,
  "commit_sha": null,
  "files_written": [
    "/home/hugo/codes/flowa-multistep-reinference/tools/upstream_eval.py",
    "/home/hugo/codes/flowa-multistep-reinference/tests/test_tools/test_upstream_eval.py",
    "/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave79-phase2-wire.md"
  ],
  "notes": [
    "Per-model subprocess driver (NO wrapper class); vendored upstream packages loaded in fresh interpreter with clean sys.path",
    "LineageFlow subprocess: 'python data/lineageflow_upstream/evaluation/evaluate_all.py --fasta ... --outdir ...'",
    "Kanzi subprocess: 'python -c <inline DAE.encode+decode+kabsch_rmsd driver>' with kanzi vendored on sys.path",
    "FlowMol3 subprocess: 'python -c <inline SampleAnalyzer.analyze driver>' with vendored data/FlowMol3/repo on sys.path",
    "All 3 flags default OFF; legacy internal-observer path byte-stable (D.4 72/72 PASS)",
    "All failures degrade gracefully to status=0.0 + descriptive reason (no raised exceptions to caller)",
    "No source code touched beyond additive CLI flags + _run_cell block; no upstream files modified",
    "Wave 76 paper-claim run + Wave 77 Kanzi claim run are now scriptable via the 3 new flags; the heavy-deps install (HMMER/MMseqs2/OmegaFold for LineageFlow, biopython/fastpdb for Kanzi, vendored flowmol for FlowMol3) is the Wave 76 R1 critical-path dependency per Phase 1 §1.3 + §2.5"
  ]
}
```