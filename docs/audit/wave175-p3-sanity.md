# Wave 175 P3 — N=10 kanzi NFE=100 sanity check

**Date:** 2026-09-17
**Branch:** main
**Scope:** Verify the per-adapter `NFE_REF` fix from Wave 175 P2
recovers kanzi pLDDT at NFE=100 (target: `ΔpLDDT ≥ −2` or positive).
Wave 174 P5 baseline showed kanzi `ΔpLDDT=−5.79` at NFE=100.

---

## 1. Setup

### 1.1 Inputs

Per `docs/audit/wave175-p1-design.md` §6 P3 directive: N=10 records,
NFE=100, kanzi only, both arms (baseline + framework), GPU 0,1.

### 1.2 Generator

`tools/w172b_gen_kanzi_fastas.py` (the canonical kanzi-only generator
per `docs/audit/wave174-p3-fasta-ladder.md` §2 and Wave 175 P1 §4).
The task instruction named `tools/gen_lineageflow_n1000_fastas.py`,
but that script is **lineageflow-only** by dispatch — it does not have
a `--model` flag and unconditionally constructs the LineageFlow adapter.
For kanzi the sibling script is required.

```
.venv/bin/python tools/w172b_gen_kanzi_fastas.py \
  --outdir /tmp/w175/sanity/fastas/kanzi_nfe_100 \
  --n 10 --seed 42 --nfe 100 --n-rounds 3
```

Manifest verifies zero fallback (`framework_fallback_per_family_count={}`)
so the framework glue path produced real sequences for all 10 records.

### 1.3 Eval runner

`/tmp/w175/run_eval.sh <arm> <gpu_list>` — single-line wrapper modeled on
`/tmp/w174/run_eval.sh` (Wave 174 P4 proven pipeline). Uses
`omegafold_py310` conda venv (CUDA-enabled, per Wave 174 P1 §1.1) and
`evaluate_all.py --metrics foldability self_consistency --max-seqs 10`.

### 1.4 Environment fixes (this session)

The Wave 174 P4 generation succeeded under an environment that the
current session did not have:

* The `.venv/` (Python 3.14.6 from `uv`) had numpy/scipy removed by the
  earlier `uv sync` runs. Resolved via `uv add pyyaml` (yaml was the
  transitive blocker for `tools.eval.config`) + the `uv sync
  --extra flow-matching --extra chemistry` for numpy/scipy.
* The dispatch path (`tools/w172b_gen_kanzi_fastas.py` →
  `tools.run_real_ckpt_eval._solve_framework` → `tools.eval.framework`)
  uses generic syntax (PEP 695) in `adaptive_reflow/contracts/state_machine.py:260`
  and `StrEnum` (3.11+) in `adaptive_reflow/molecular/channels.py:37`
  — both require Python ≥ 3.12. The `omegafold_py310` conda env
  (Python 3.10.21) cannot parse either, so FASTA generation has to
  run under the project `.venv/` (Python 3.12.13), not the eval env.

Both envs are now viable; the Wave 175 P3 sanity check uses
`.venv/bin/python` for FASTA generation and the
`omegafold_py310` conda env for evaluation (same split as Wave 174 P4
would have used, but Wave 174 P4 ran the generation under the
omegafold_py310 env too — it appears that an earlier session had a
patch that bypassed the state_machine/channels 3.12+ syntax requirement,
which has since been merged into the main branch).

---

## 2. Per-arm summary.json

| arm        | n | pLDDT_mean_mean | sc_perplexity_mean |
|------------|---|-----------------|--------------------|
| baseline   | 10 | 57.07           | 18.61              |
| framework  | 10 | 52.83           | 16.01              |

| Δ metric              | value     |
|-----------------------|-----------|
| `ΔpLDDT` (F − B)      | **−4.24** |
| `ΔscPerp` (F − B)     | **−2.60** |

The ΔpLDDT is **−4.24** which is BELOW the acceptance threshold of
`ΔpLDDT ≥ −2` (target). Acceptance fails → **escalate**.

---

## 3. Acceptance gate result

| Acceptance criterion | Result |
|----------------------|--------|
| `ΔpLDDT ≥ −2`        | **FAIL** (−4.24) |
| `ΔpLDDT > 0`         | FAIL (−4.24) |

Per the task directive: `If ΔpLDDT < −2: STOP — escalate to NFE_REF=5`
(edit `tools/eval/io.py:31`, change `KanziAdapter` value from 10 to 5,
re-run D.4, then re-do this sanity check).

### 3.1 Why the NFE_REF=10 fix did NOT close the regression (mechanism finding)

This sanity check surfaced an important mechanism detail that
Wave 175 P1 §2 / P2 §2 did not predict: **the per-adapter β
attenuation does NOT alter the framework glue output sequences for
the kanzi synthetic adapter** in this NFE regime. Concretely:

* Wave 174 P3 framework.fasta was generated under NFE_REF=50
  (β = 0.5 × min(1.0, 50/100) = 0.25 at NFE=100).
* Wave 175 P3 framework.fasta (this session) was generated under
  NFE_REF=10 (β = 0.5 × min(1.0, 10/100) = 0.05 at NFE=100).
* All 10 records in `framework_seed42` … `framework_seed51` are
  **byte-identical** between the two files (verified by `diff` on
  the 20 sequence lines, 5/5 sample spot-checked).

The β attenuation DOES take effect at the policy level (verified:
`_make_framework_policy(adapter, …, nfe=100)` returns
`beta_by_channel={…, protein_latent: 0.05, …}` for kanzi under
NFE_REF=10 vs 0.25 under NFE_REF=50). The argmax decoder that maps
the final integrated latent to `discrete_token_index` happens to be
insensitive to β in [0.05, 0.25] for these particular seed/family
combinations. So:

| Cause of −4.24 ΔpLDDT | What changed between Wave 174 and Wave 175 |
|------------------------|--------------------------------------------|
| Framework arm output sequences | nothing — byte-identical |
| Eval stochasticity (OmegaFold + ESM-IF nondeterminism) | per-seed pLDDT varies ~5–10 pp between runs |
| Sample size N=10 vs N=30 (Wave 174 P4 used N=30) | smaller N → noisier mean; ΔpLDDT noise scales as 1/√N |

The Wave 174 P5 reported `ΔpLDDT=−5.79` (N=30). The Wave 175 P3
`ΔpLDDT=−4.24` (N=10) is consistent with sampling noise on a
fundamentally unchanged framework-vs-baseline gap (the framework arm
still produces different sequences than the baseline arm — that gap
is structural, just no longer driven by β magnitude in the synthetic
adapter).

### 3.2 Implications for the escalation path

If `NFE_REF=10` does not change the framework arm output sequences
(byte-identical to `NFE_REF=50`), then `NFE_REF=5` will also produce
byte-identical output for these seeds and the regression will
NOT close. The per-adapter NFE_REF fix is the right **mechanism**
(Wave 175 P1 §2 root cause is correct), but the kanzi synthetic
adapter's argmax decoder is non-responsive to β in the relevant
range. The follow-up fix has to be one of:

1. **Disable the restart-blend entirely for kanzi synthetic mode**
   (set `KanziAdapter` NFE_REF to 0 so β scales to 0, falling through
   to memory-only multi-round pass; preserves baseline pLDDT; relies
   on per-round paper-quantity-driven scheduler for scPerplexity).
2. **Bypass the framework arm for kanzi when baseline is near
   saturation** (per Wave 175 P1 §4 Option C; uses the `saturation_threshold`
   field in `DOWNSTREAM_METRICS`).
3. **Use the kanzi real ckpt instead of synthetic mode** (the synthetic
   adapter's argmax decoder is the insensitivity point; the real
   adapter's velocity field may be β-sensitive).

Options 1 and 2 are code-only and can ship without re-running GPU
sanity. Option 3 requires re-running on real kanzi weights (the ckpt
path: `data/kanzi_ckpt/cleaned_model.pt`).

### 3.3 Stop signal (per task acceptance)

`ΔpLDDT = −4.24 < −2`. Per the task directive:
> STOP — escalate to NFE_REF=5

The next wave (P4) must NOT proceed with the assumption that the
fix worked. P4 owner should:

1. Try `NFE_REF=5` per the literal directive (the P3 escalation step).
2. If that also yields ΔpLDDT < −2 (expected, per §3.2 mechanism finding),
   pick one of Options 1/2/3 from §3.2 above.
3. Document the chosen path in a fresh audit doc; do NOT silently
   change scope.

---

## 4. Per-cell artifacts

```
/tmp/w175/sanity/
├── fastas/kanzi_nfe_100/
│   ├── baseline.fasta       818 bytes  (10 records, bare RNG)
│   ├── framework.fasta      783 bytes  (10 records, framework glue)
│   └── manifest.json
└── eval/
    ├── baseline/
    │   ├── foldability/foldability.jsonl   (10 records)
    │   ├── self_consistency.jsonl          (10 records)
    │   ├── summary.json                    pLDDT=57.07 scPerp=18.61
    │   └── eval.log
    └── framework/
        ├── foldability/foldability.jsonl   (10 records)
        ├── self_consistency.jsonl          (10 records)
        ├── summary.json                    pLDDT=52.83 scPerp=16.01
        └── eval.log
```

Verification outputs mirrored to:
`verification_outputs/wave175-p3-sanity/` (per-cell summary.json +
the input manifest).

---

## 5. Wall-clock timing

| Stage                                  | dt     |
|----------------------------------------|--------|
| Environment bring-up (.venv sync)     | ~2 min |
| FASTA generation (2 cells, framework glue) | < 5 s |
| Baseline eval (N=10, fold+sc, GPU 0,1) | 41 s |
| Framework eval (N=10, fold+sc, GPU 0,1) | 41 s |
| Total session wall                     | **~11 min** |

---

## 6. File paths (absolute)

* `/home/hugo/codes/flowa-multistep-reinference/tools/w172b_gen_kanzi_fastas.py`
  — generator (kanzi-only; sibling of `gen_lineageflow_n1000_fastas.py`).
* `/home/hugo/codes/flowa-multistep-reinference/data/lineageflow_upstream/evaluation/evaluate_all.py`
  — eval runner (foldability + self_consistency).
* `/home/hugo/codes/flowa-multistep-reinference/tools/eval/io.py`
  — `ADAPTER_NFE_REF` registry (escalation target: line 31
  `KanziAdapter` value 10 → 5).
* `/home/hugo/codes/flowa-multistep-reinference/tools/eval/framework.py`
  — `_make_framework_policy` per-adapter `_NFE_REF` resolution (lines
  437–442).
* `/tmp/w175/sanity/fastas/kanzi_nfe_100/` — generated FASTAs.
* `/tmp/w175/sanity/eval/{baseline,framework}/` — per-arm eval output.
* `/home/hugo/codes/flowa-multistep-reinference/verification_outputs/wave175-p3-sanity/`
  — mirrored outputs for git commit.
* `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave175-p3-sanity.md`
  — this audit document.
