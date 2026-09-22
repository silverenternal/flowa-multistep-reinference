# Kanzi inverse-projection bridge follow-up

## Current evidence (2026-09-13)

Kanzi is available in `.venvs/kanzi_venv`: Torch 2.14.0+cu130, upstream
Kanzi, biotite, esm and pytest import successfully. GPU0 is an RTX PRO
6000 Blackwell; an actual CUDA tensor operation passed. The original
`data/kanzi_ckpt/cleaned_model.pt` and `tools/_kanzi_project_out_inv.pt`
are present. Earlier statements that the Kanzi tests were blocked because
Torch was absent referred to the project venv, not this model sidecar.

The pre-fix N=20 diagnostic at commit `04ddd73` completed with zero skipped
records in 77.5 seconds, mean self-reconstruction RMSD 0.8860 Å and standard
deviation 0.1235 Å. Command, hashes, process handle, exit code and metrics:
`verification_outputs/kanzi_inv_proj_n20_20260913_preflight/`.
This is a generated-coordinate autoencoder roundtrip after a single adapter
rollout, not paired input reconstruction or a multi-round refinement result.
It does not close the original scientific acceptance criteria.

The corrected run at commit `85b5080` also completed all 20 records without
skips: RMSD 0.8862979521 Å (standard deviation 0.1273357750 Å), codebook
utilization 0.537, 190.69 seconds for the sweep. It used seed 42, 50 Euler
adapter steps, 100 pre-loop decoder steps and 100 roundtrip decoder steps.
These decoder counts differ from the legacy diagnostic; the two runs must
not be presented as a controlled before/after comparison. GPU0 was selected
with `CUDA_VISIBLE_DEVICES=0` and CPU threading with `OMP_NUM_THREADS=2`.

Artifacts: `verification_outputs/kanzi_inv_proj_n20_20260913_corrected/`.
Both initial execution and `--resume` exited 0. Resume recovered all 20
records, and the per-record RMSDs, aggregate RMSD and codebook metrics were
exactly equal to the saved initial summary. The rotation-invariance metric
is null (unmeasured); JS explicitly has support of only two records.

## Engineering corrections

Commit `85b5080` removes silent zero-velocity fallback on real Kanzi model
load failures, uses explicit CPU checkpoint mapping and strict state loading,
and rejects missing/non-finite rollout endpoints. Loader/smoke tests: 33 passed,
including original-checkpoint CPU forward; Kanzi regression checks: 8 passed.

Sweep controls now reach the adapter and decoder. Decoder steps are reported
separately from adapter velocity evaluations; unmeasured rotation invariance
is null, and JS sample support explicitly identifies its two-record scope.
The record limit bounds attempts, so failed records cannot be silently replaced
by later successes. Empty/incomplete sweeps raise errors.

Each successful record is atomically checkpointed with RMSD and codebook
indices. Resume validates input/checkpoint/source hashes and execution settings.
It skips completed records and retries failures. Recovery tests inject a failed
record and compare the recovered metrics with an uninterrupted run. Existing
outputs are not overwritten by a fresh run. Legacy result directories without
`checkpoint.json` cannot be resumed with this new mechanism.

Use the inverse-projection driver (it has no `--mode` option):

```bash
.venvs/kanzi_venv/bin/python tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py \
  --input verification_outputs/kanzi_n1000_coords.txt \
  --ckpt data/kanzi_ckpt/cleaned_model.pt --seed 42 --limit 20 \
  --n-steps-decoder 100 --adapter-num-steps 50 --adapter-solver euler \
  --adapter-force-mode torch --output-dir <new-output-directory>
```

To resume, repeat the exact command with `--resume`. Reusing an output directory
without this flag is not recovery and now fails instead of overwriting results.

## Still unmet

The existing Linear(512→4) bridge plus DAE decoding is not the planned new
trained raw-coordinate bridge. Held-out MSE and calibration evidence remain
missing. The current driver uses input coordinates as record enumeration for
its generated arm and does not perform multi-round restart/merge. N=1000,
codebook coverage and comparison to appropriate baseline anchors remain
unverified. A successful diagnostic is not sufficient to mark the plan done.
