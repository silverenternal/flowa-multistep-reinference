# Wave 262 P3: R1 + R6 flag-dependency audit (rerun decision)

## Scope

Verify whether the headline numbers reported by **R1 LineageFlow HMMER
N=1000** (`158 → 342`) and **R6 k6 LineageFlow foldability per-tier
d_z** (hard / medium / easy) depend on the flags added to vendored
LineageFlow files that were reverted in Wave 262 P1 (`8f0255d`).

The five flags / modifications in scope:

| # | File | Reverted change | Default behaviour (reverted = upstream) |
|---|------|------------------|--------------------------------------------|
| 1 | `evaluation/foldability_omegafold.py` | `--workers-per-gpu` | `--gpus 0` only (1 process per GPU, no multi-worker sharding) |
| 2 | `evaluation/novelty_mmseqs2.py` | `--pctid-novelty` | flag absent (additive metric) |
| 3 | `evaluation/run_foldability.py` | propagates `--workers-per-gpu` | propagates only `--fold-gpus` / `--sc-gpus` |
| 4 | `evaluation/self_consistency_esmif.py` | multi-worker per-GPU sharding | one process per GPU, round-robin indices |
| 5 | `evaluation/evaluate_all.py` | `--temperature` (default 1.0) | flag absent (upstream equivalent) |

## R1 — LineageFlow HMMER N=1000 (`158 → 342`)

### Pipeline that produced the numbers

The R1 +116% headline numbers come from
`docs/audit/wave158-hmmer-rederivation.md` (Wave 158 P2) and the
source-of-truth `verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/`.

Pipeline (3 stages):

1. **Generate FASTAs** —
   `tools/gen_lineageflow_n1000_fastas.py` (Wave 86 Agent B, fixed in
   Wave 158 P2 to inject `_REPO_ROOT` into `sys.path`).
   1000 baseline + 1000 framework records.
2. **HMMER `hmmscan`** — system binary
   (`/home/hugo/hmmer_build/bin/hmmscan`), called directly with
   `--cpu 4 --noali` against the Pfam-A reference HMM database.
   Wall-clock ~5 min.
3. **Count hits** — count lines in the `.tbl` files (158 baseline +
   342 framework = `Δ = +184, +116.46%`).

### Flag-dependency analysis

| Stage | Tool | Touches vendored LineageFlow code? |
|-------|------|--------------------------------------|
| 1 | `tools/gen_lineageflow_n1000_fastas.py` (not vendored) | NO |
| 2 | system `hmmscan` binary | NO |
| 3 | line count on `.tbl` files | NO |

`tools/gen_lineageflow_n1000_fastas.py` accepts `--temperature` (default
1.0, argmax path — same as Wave 158 / Wave 161 K6 / Wave 167 P5 manifest
bytes per Wave 171 P1 docs), but `--temperature` is forwarded to
**the framework's internal LineageFlowAdapter decoder**, NOT to the
vendored `evaluate_all.py`. The vendored `evaluate_all.py` was never
called by the R1 pipeline.

The `--workers-per-gpu`, `--pctid-novelty`, and `--temperature` flags
are NOT on the R1 pipeline's code path. **R1 HMMER numbers are
byte-stable after Wave 262 P1 revert.**

`grep -E "workers-per-gpu|pctid-novelty|--temperature"
verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/
verification_outputs/lineageflow_real_fastas_w158_q3_2026/`
→ no matches.

## R6 — LineageFlow k6 foldability per-tier d_z

### Pipeline that produced the numbers

The R6 per-tier d_z readings come from
`verification_outputs/wave225-p4-k6-tier-aware.json` (Wave 225 P4),
which is a counterfactual JSON that re-stratifies the per-record paired
foldability data from
`verification_outputs/k6_foldability_n1000_w161_q3_2026/{baseline,framework}/foldability/`.

Source data:

* Baseline foldability (N=1000) from `k6_foldability_n1000_w161_q3_2026/baseline/foldability/foldability.jsonl`
* Framework foldability (N=1000) from `k6_foldability_n1000_w161_q3_2026/framework/foldability/foldability.jsonl`
* Self-consistency files for the same arms

Per-tier d_z readings:

| Tier | n | d_z | p-value |
|------|----|-----|---------|
| hard | 330 | 1.189 | 4.82e-65 |
| medium | 340 | 0.218 | 7.12e-05 |
| easy | 330 | -0.499 | 1.13e-17 |

Overall (Wave 225 P4, before counterfactual uplift): d_z = 0.071
(uplift to 0.223 via reduced-intensity counterfactual).

### Flag-dependency analysis — actual command

`grep -E "run_foldability|foldability_omegafold|self_consistency_esmif|workers-per-gpu"
verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/foldability.log`
returns the exact command used to produce the R6 source data:

```bash
$ python /home/hugo/codes/flowa-multistep-reinference/data/lineageflow_upstream/evaluation/run_foldability.py \
    --fasta /tmp/w158/lineageflow_real_fastas/baseline.fasta \
    --outdir /tmp/w160/foldability_n1000/baseline/foldability \
    --omegafold-bin /home/hugo/.conda/envs/omegafold_py310/bin/omegafold \
    --fold-gpus 0 --sc-gpus 0 \
    --min-len 10 --max-len 1024 --chain A --log-every 30 --no-plots
```

Subprocess invocations (Stage A + Stage B):

```
[run] fold stage: python evaluation/foldability_omegafold.py ... --gpus 0 ...
[run] self-consistency stage: python evaluation/self_consistency_esmif.py ... --gpus 0 ...
```

**Note:** `--workers-per-gpu` is **NOT** in the actual command. The
foldability run was single-GPU, single-worker per GPU (the upstream
behaviour). The added `--workers-per-gpu` flag was never used in the
production R6 sweep.

`grep -E "workers-per-gpu|pctid-novelty|--temperature"
verification_outputs/k6_foldability_n1000_w161_q3_2026/{baseline,framework}/foldability.log`
→ no matches.

The `--pctid-novelty` flag is in `novelty_mmseqs2.py`, but R6 is a
**foldability** sweep — novelty was never computed for R6. The
`--temperature` flag was on `evaluate_all.py` (which orchestrates all
metrics), but R6 was run via the lower-level `run_foldability.py`,
not `evaluate_all.py`.

**R6 per-tier d_z numbers are byte-stable after Wave 262 P1 revert.**

## Rerun decision

| Headline | Flag-dependent? | Rerun required? |
|----------|------------------|------------------|
| R1 HMMER +116% (158 → 342) | NO — pipeline is `tools/gen_*` + system `hmmscan` | NO |
| R6 k6 foldability per-tier d_z | NO — command was `--fold-gpus 0 --sc-gpus 0 --no-plots`, no `--workers-per-gpu` | NO |

**Rerun decision: NOT NEEDED.**

Both headline numbers were produced via code paths that did not use
any of the reverted flags. The reverted code is byte-identical to the
behaviour used to produce these numbers, so the headline numbers are
byte-stable after Wave 262 P1.

The `--workers-per-gpu` flag, if it had been used, would have changed
the per-record sharding order (LPT-balanced within a GPU vs round-robin
across processes), but that flag was never invoked in the R6 production
sweep. The `--pctid-novelty` flag is on `novelty_mmseqs2.py`, which R6
does not call. The `--temperature` flag on `evaluate_all.py` was never
invoked by R6 or R1 (R1 bypasses vendored eval scripts entirely; R6 uses
`run_foldability.py` directly).

## Honest disclosure (paper §10)

None of the 5 reverted flags were on the R1 / R6 production code path.
The headline numbers (R1 +116%, R6 per-tier d_z) are independent of the
revert. The tool-side `tools/run_lineageflow_n1000_foldability_omegafold.py`
still contains its own `--workers-per-gpu` argument (added in Wave 201
P5/P6), but that argument is on the framework wrapper (a `tools/` file,
not vendored). If a future rerun explicitly passes `--workers-per-gpu`
to the tool, the tool will pass it to `run_foldability.py`, which will
**fail with `unrecognized argument --workers-per-gpu`** because the
vendored script no longer accepts that flag — this is a known
incompatibility surfaced in Wave 262 P1's revert and documented in
`docs/audit/wave262-p1-revert-all.md`. The current headline numbers
were not produced under that failure mode.

## Gate verification

| Gate | Command | Result | Delta from P1 |
|------|---------|---------|---------------|
| D.4 byte-stable | `.venvs/lineageflow_venv/bin/python -m pytest tests/test_d4_regression_vectors.py -q --no-header` | `30 passed, 3 warnings in 2.40s` | unchanged (still 30/30 PASS) |
| claims consistency | `python3 tools/check_claims_consistency.py` | `60 active + 1 provisional + 2 deprecated. No drift detected.` | unchanged |
| vendored bytewise match | `git -C data/lineageflow_upstream diff HEAD -- <5 files>` | empty | unchanged (Wave 262 P2 verify) |
| mkdocs | `mkdocs build --strict` | 1 pre-existing warning (Wave 261 P4 `d0d01e4`) | unchanged (Wave 262 P2 verify) |

No source-code change; only this audit doc was added.

## Hard-rule compliance

| Rule | Status |
|------|--------|
| DO NOT modify any vendored code | HONOURED — only `docs/audit/wave262-p3-rerun.md` written |
| DO preserve D.4 30/30 PASS | HONOURED — 30/30 PASS (unchanged) |
| DO preserve mkdocs 0 warnings | HONOURED — net delta from P1 is 0; pre-existing warning from `d0d01e4` |
| DO preserve claims consistency no drift | HONOURED — 0 drift (unchanged) |

## Output JSON

```json
{
  "flags_dependent_on_reverted_files": false,
  "r1_hits_match_after_revert": true,
  "r6_per_tier_d_z_match_after_revert": true,
  "rerun_decision": "not_needed",
  "audit_doc_path": "docs/audit/wave262-p3-rerun.md",
  "commit_sha": "<see commit>"
}
```
