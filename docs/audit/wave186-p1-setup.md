# Wave 186 P1 — sensitivity analysis setup

**Date:** 2026-09-18
**Branch:** main
**Scope:** Wave 186 P1 — verify the lineageflow generator accepts the
sensitivity analysis parameter set before the P2 sweep runs.

---

## 1. Goal

Confirm `tools/gen_lineageflow_n1000_fastas.py` can drive a sensitivity
analysis. The four parameters that the Wave 186 sweep plans to vary:

| Parameter        | Meaning                                                |
|------------------|--------------------------------------------------------|
| `--beta-base`    | Family-balance exponent on restart distribution blend |
| `--restart-min-nfe` | Min NFE budget under which restart-blend is disabled |
| `--nfe-ref`      | Reference NFE for normalized BL convergence plot        |
| `--seed`         | Per-arm RNG seed (already supported)                   |

The first three are needed by the Wave 186 §11 theory-tightness
analysis; `--seed` is needed for the multi-seed protocol inherited
from Wave 179 P1.

---

## 2. CLI inventory (`gen_lineageflow_n1000_fastas.py --help`)

```
usage: gen_lineageflow_n1000_fastas.py [-h] [--outdir OUTDIR] [--n N]
                                       [--seed SEED] [--min-len MIN-LEN]
                                       [--max-len MAX-LEN] [--nfe NFE]
                                       [--n-rounds N-ROUNDS]
                                       [--temperature TEMPERATURE]
```

The argparse surface has 8 flags. The four required sensitivity
parameters resolve as follows:

| Parameter        | Supported today?     | Evidence                                                |
|------------------|----------------------|---------------------------------------------------------|
| `--beta-base`    | **NO**               | Not in argparse surface; not in module globals           |
| `--restart-min-nfe` | **NO**            | Not in argparse surface; not in module globals           |
| `--nfe-ref`      | **NO**               | Not in argparse surface; not in module globals           |
| `--seed`         | **YES**              | `argparse` line 332: `p.add_argument("--seed", type=int, default=42)` |

Module-level constants in `tools/gen_lineageflow_n1000_fastas.py`
exposed for `--nfe` and `--n-rounds` rewiring are:

```python
NFE_PER_RECORD: int = 10  # overridden by --nfe in main()
N_ROUNDS:      int = 3   # overridden by --n-rounds in main()
```

There is **no** `BETA_BASE`, `RESTART_MIN_NFE`, or `NFE_REF` constant
in `tools/gen_lineageflow_n1000_fastas.py`, in
`flowa/`, or in `data/lineageflow_upstream/` (verified via grep).
The references in `tools/compute_nfe_aware_projection.py` (lines
110-111, 145, 223) and `tools/w185_p4_plot.py` (lines 57, 60) are
*post-hoc* projection / plotting inputs, not generator CLI args.

---

## 3. Smoke test

Two N=2 invocations to confirm the CLI is live and the manifest
captures parameter perturbations. Venv:
`.venvs/lineageflow_venv/bin/python` (per Wave 178 P6 / Wave 179
P1 dispatch).

### 3.1 Default (Wave 81 / Wave 86 manifest bytes)

```bash
.venvs/lineageflow_venv/bin/python tools/gen_lineageflow_n1000_fastas.py \
  --outdir /tmp/w186p1_smoke/default --n 2 \
  --seed 42 --nfe 10 --n-rounds 3 --temperature 1.0
```

Output: `baseline.fasta`, `framework.fasta`, `manifest.json`.
Manifest fields: `seed=42`, `nfe_per_record=10`, `n_rounds=3`,
`temperature=1.0`, `framework_fallback_per_family_count={}` (no
defensive fallbacks — Wave 86 Agent B invariant holds).

### 3.2 Perturbed

```bash
.venvs/lineageflow_venv/bin/python tools/gen_lineageflow_n1000_fastas.py \
  --outdir /tmp/w186p1_smoke/perturbed --n 2 \
  --seed 99 --nfe 50 --n-rounds 5 --temperature 0.7
```

Output identical shape; manifest fields:
`seed=99`, `nfe_per_record=50`, `n_rounds=5`,
`temperature=0.7`. Baseline bytes differ from default (seed-driven,
as expected).

---

## 4. Decision

**Generator currently supports `--seed` only** of the four
sensitivity-analysis parameters the Wave 186 sweep needs.
`--beta-base`, `--restart-min-nfe`, and `--nfe-ref` are **not**
wired in. Wave 186 P2 must either:

1. Extend `gen_lineageflow_n1000_fastas.py` with the three flags
   (`p.add_argument` + `manifest` capture + framework-arm wire-through
   for `--beta-base` / `--restart-min-nfe`; `--nfe-ref` is a
   post-process projection knob that can be passed to a downstream
   script such as `compute_nfe_aware_projection.py`), **or**
2. Pass the three values through a new wrapper around the generator
   that mutates module-level globals before invoking the framework
   arm (mirrors the Wave 168 P1 `--nfe` rewire pattern).

Path 1 (CLI flags) is preferred — it preserves the Wave 81/86
manifest-bytes invariant for default invocations and is byte-stable
under backward-compatible defaults. Wave 186 P2 is responsible for
choosing the path; this P1 audit establishes the gap.

---

## 5. Output JSON

```json
{
  "beta_base_supported": false,
  "restart_min_nfe_supported": false,
  "nfe_ref_supported": false,
  "cli_pattern": ".venvs/lineageflow_venv/bin/python tools/gen_lineageflow_n1000_fastas.py --outdir <DIR> --n <N> --seed <SEED> --nfe <NFE> --n-rounds <ROUNDS> --temperature <T>",
  "commit_sha": "<set at end of P2>"
```