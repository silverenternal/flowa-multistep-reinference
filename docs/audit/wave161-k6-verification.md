# Wave 161 — K6 N=1000 Sweep Verification

**Status**: VERIFIED — N=1000/1000 both arms; sha256 cross-checked; gates preserved; K6 RESOLVED-ready
**Author**: Wave 161 Agent 1
**Date**: 2026-09-15
**Scope**: Add-only verification of the Wave 160 P1 K6 foldability + self-consistency N=1000 sweep outputs on disk at `/tmp/w160/foldability_n1000/{baseline,framework}/`.

## 1. Process check

`ps aux | grep -E "evaluate_all|omegafold"` returns **no live processes**. The Wave 160 P1 sweep (assumed still running at Wave 161 P1 launch; verified complete) finished successfully and both arms are idle on disk.

## 2. Record counts (N=1000/1000 verified)

| arm | foldability.jsonl | self_consistency.jsonl | pdb/ dir |
|------|-------------------:|-----------------------:|---------:|
| baseline | **1000** | **1000** | **1000** |
| framework | **1000** | **1000** | **1000** |

No records skipped in either arm. `n_with_plddt = n_with_sc = n_with_both = 1000` per `metrics_summary.json` for both arms. `n_errors = 0` for both arms per `self_consistency_summary.json`. `missing_pdb = 0` per tail of foldability.log for both arms.

## 3. Top-level `summary.json` contents (per arm)

### baseline
```json
{
  "foldability": {
    "n_total": 1000,
    "n_with_plddt": 1000,
    "n_with_sc": 1000,
    "n_with_both": 1000,
    "plddt_mean_mean": 42.07247315651403,
    "plddt_mean_median": 40.3635508070016,
    "sc_perplexity_mean": 17.87505990487994,
    "sc_perplexity_median": 17.572139235178476,
    "corr_plddt_vs_sc": 0.17089715054709714
  }
}
```

### framework
```json
{
  "foldability": {
    "n_total": 1000,
    "n_with_plddt": 1000,
    "n_with_sc": 1000,
    "n_with_both": 1000,
    "plddt_mean_mean": 43.19560865856248,
    "plddt_mean_median": 41.29622661564626,
    "sc_perplexity_mean": 13.95841014634339,
    "sc_perplexity_median": 13.765437361818046,
    "corr_plddt_vs_sc": -0.13174947808570772
  }
}
```

## 4. Delta computation

| metric | baseline | framework | delta | delta % | direction |
|--------|---------:|----------:|------:|--------:|-----------|
| plddt_mean_mean ↑ | 42.07247315651403 | 43.19560865856248 | +1.123136 | +2.6695% | framework wins |
| sc_perplexity_mean ↓ | 17.87505990487994 | 13.95841014634339 | −3.916650 | −21.9113% | framework wins |
| corr_plddt_vs_sc | +0.1709 | −0.1317 | sign-flip | n/a | framework aligns axes |

These deltas match the Wave 160 P2 §11 headline (`+2.67% pLDDT`, `−21.91% scPerplexity`) and the Wave 86 byte-for-byte baseline derivation path.

## 5. sha256 — source files (Wave 160 outputs)

```
7dc407880063760bd36806518dfbf9f81f7057729fd1ce0a69dafbf906bd0e3d  /tmp/w160/foldability_n1000/baseline/summary.json
bf896fe6a61ac6863c2568bdd05698a8ccd66aecaba772a060e202aab13f2a51  /tmp/w160/foldability_n1000/baseline/run_manifest.json
164825057a413af6f4d27a53b3ca519484f5c36019dafaa6c14e33dc823e4261  /tmp/w160/foldability_n1000/baseline/foldability/foldability.jsonl
fd21d98829eb5d5df9d87d3295637bd4a9c5524cff6663ed6f384d43db45ea92  /tmp/w160/foldability_n1000/baseline/foldability/self_consistency.jsonl
f50f3fc6fb353645e89e5cec7da86981fe08ba4ecd735f2f758e263aa6670a60  /tmp/w160/foldability_n1000/baseline/foldability/metrics_summary.json
5d483e3f4619dd9ebb26f3644e68b3e9522579ceed4240b447880a19ace23e20  /tmp/w160/foldability_n1000/baseline/foldability/summary.json
62be16f2114926350f9c37728bf65ca09bb212276e716353603e404e8f5f63cf  /tmp/w160/foldability_n1000/baseline/foldability/self_consistency_summary.json

0aa63c652c6a6ba1bcd5dddfd89c5183efbd76d00dae3557ff1db838a1350269  /tmp/w160/foldability_n1000/framework/summary.json
23db172be2b17a8d232324fa008afceebf1d3770628e6c2054d676acf5773d63  /tmp/w160/foldability_n1000/framework/run_manifest.json
b608edfb0f13a39bde5a06c3d16ccc94aa98f90db5434411cefe2f647574fc85  /tmp/w160/foldability_n1000/framework/foldability/foldability.jsonl
bbd7ca13b46eb81a4d72fa5a7da25c095f0751b81eead315de5d2cdcb0a1d34b  /tmp/w160/foldability_n1000/framework/foldability/self_consistency.jsonl
2b36d588485d40dd65add5af3b4f5775a0536df5a21a2033157f3afe31839e3e  /tmp/w160/foldability_n1000/framework/foldability/metrics_summary.json
e96b1e2592a36d25a29658df9258fd408be454aa1ac2bd09f13e1d44f35c3aad  /tmp/w160/foldability_n1000/framework/foldability/summary.json
21bfab127b1dde26719051954c92c88f7193b09326bac97cdd29771db2930000  /tmp/w160/foldability_n1000/framework/foldability/self_consistency_summary.json
```

## 6. sha256 — verification_outputs copies (cross-verify)

After copy to `verification_outputs/k6_foldability_n1000_w161_q3_2026/`, three load-bearing files re-hashed:

```
7dc407880063760bd36806518dfbf9f81f7057729fd1ce0a69dafbf906bd0e3d  verification_outputs/.../baseline/summary.json
164825057a413af6f4d27a53b3ca519484f5c36019dafaa6c14e33dc823e4261  verification_outputs/.../baseline/foldability/foldability.jsonl
fd21d98829eb5d5df9d87d3295637bd4a9c5524cff6663ed6f384d43db45ea92  verification_outputs/.../baseline/foldability/self_consistency.jsonl

0aa63c652c6a6ba1bcd5dddfd89c5183efbd76d00dae3557ff1db838a1350269  verification_outputs/.../framework/summary.json
b608edfb0f13a39bde5a06c3d16ccc94aa98f90db5434411cefe2f647574fc85  verification_outputs/.../framework/foldability/foldability.jsonl
bbd7ca13b46eb81a4d72fa5a7da25c095f0751b81eead315de5d2cdcb0a1d34b  verification_outputs/.../framework/foldability/self_consistency.jsonl
```

All six hashes match the source /tmp/w160 sha256 list above — copies are byte-identical. Each arm ships a 12-file verification bundle:

```
verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/
├── summary.json
├── run_manifest.json
├── foldability.log
├── sweep.log
├── sha256.txt
└── foldability/
    ├── foldability.jsonl
    ├── self_consistency.jsonl
    ├── metrics_summary.json
    ├── summary.json
    ├── self_consistency_summary.json
    ├── inputs.json
    └── queries.fasta
```

(Mirrored for `framework/`.) PDB tree is intentionally not copied — manifest + metadata + log prove the sweep completed; PDB reproduction would require re-running.

## 7. Gate verification

| gate | command | result |
|------|---------|--------|
| **ruff** | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | `All checks passed!` |
| **claims** | `python tools/check_claims_consistency.py` | `No drift detected.` (39 active claims, 0 provisional) |
| **pytest -k d4** | `pytest tests/ -k "d4" -q` | `33 passed, 31 skipped, 5020 deselected` (D4 spec-literal regression suite) |

All three gates pass with zero failures. The 31 skipped tests are environment-related (missing torch / hypothesis / pandas in this venv); they are not introduced by Wave 161 (additive only, no source-code changes).

## 8. K6 status

| milestone | status |
|-----------|--------|
| Wave 80 §10 deferred | N=1000 foldability + ssc deferred to camera-ready (~25h/arm time budget) |
| Wave 159 P3 | K6 **ENV_BLOCKED → UNBLOCKED-WITH-NOTE** (OmegaFold Python 3.10 sidecar venv provisioned) |
| Wave 160 P1 | K6 **UNBLOCKED-WITH-NOTE → UNBLOCKED-SWEEP-LAUNCHED** (sanity N=5 PASS, N=1000 launched in background) |
| Wave 160 P2 §11 | K6 **UNBLOCKED-SWEEP-LAUNCHED → RESOLVED** (Wave 160 P2 audit doc §11 already declares RESOLVED based on Wave 160 P1 outputs) |
| Wave 161 P1 (this doc) | K6 **RESOLVED-ready** — N=1000/1000 verified, sha256 cross-checked, copies in `verification_outputs/`, gates preserved |

## 9. Honesty disclosures

- **stub disclosure** (carried from Wave 160): The sweep used a small native-torch stub for `torch_scatter` because upstream PyG wheels do not yet cover torch 2.14 / CUDA 13.0. The stub implements only the small subset actually called by ESM-IF GVP (1 `scatter_add` call site, signature `scatter_add(src, index, dim_size)`). Equivalent to canonical PyG for that signature; verified with a 4-element unit test.
- **first-record inference time**: First PDB of each arm takes ~5-10 min (OmegaFold weight load + compile) then amortizes to <2 s/record. End-to-end per-record wallclock is ~3-4 s on RTX 5090 and ~2 s on RTX PRO 6000 Blackwell.
- **ESM-IF model weights**: Downloaded once into sidecar venv `/home/hugo/.cache/torch/hub/checkpoints/esm_if1_*`; reused for full N=1000 sweep.
- **Wave 160 P1 sweep**: assumed still-running at Wave 161 P1 launch; verified complete on disk at `/tmp/w160/foldability_n1000/{baseline,framework}/`. Wave 160 P2 audit doc already declares K6 RESOLVED based on these outputs.

## 10. Wave 161 P1 outputs

- `docs/audit/wave161-k6-verification.md` (this doc)
- `verification_outputs/k6_foldability_n1000_w161_q3_2026/{baseline,framework}/` — 12 files per arm × 2 arms = 24 files total
  - `baseline/{summary.json, run_manifest.json, foldability.log, sweep.log, sha256.txt, foldability/*}`
  - `framework/{summary.json, run_manifest.json, foldability.log, sweep.log, sha256.txt, foldability/*}`

Wave 161 is ADDITIVE only. No files in `adaptive_reflow/` / `tests/` / `scripts/` / `tools/` were modified.
