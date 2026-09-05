# Wave 39 Agent A — Kanzi sidecar real-ckpt forward pass

**Date:** 2026-09-05
**Agent:** Wave 39 Agent A
**Goal:** Build a sidecar venv capable of running the actual 530 MB
Kanzi checkpoint at `data/kanzi_ckpt/cleaned_model.pt` end-to-end on
CPU, document the procedure, and verify the result.

## Status: SUCCESS

A real-ckpt forward pass executes in the new sidecar
`.venvs/kanzi_venv/` on synthetic protein coords; outputs are sensible
quantized token indices (vocab_size = 1000) and a non-trivial flow
loss. The encoder + flow-decoder + decoder all run on real checkpoint
weights with no NaN / Inf in the output.

Full results JSON:
[`verification_outputs/kanzi_real_ckpt_forward_q4_2026.json`](../../verification_outputs/kanzi_real_ckpt_forward_q4_2026.json).

## What was built

| Path | Purpose |
| --- | --- |
| `.venvs/kanzi_venv/` | New sidecar venv, Python 3.12.13 (uv-created). CPU-only torch + diffusers + esm + biopython + the official `kanzi` package. **Disjoint scope** — does not touch any other venv in `.venvs/`. |
| `requirements-kanzi.txt` | Sidecar-only dependency list. Already authored in a prior wave; verified accurate. |
| `tools/run_kanzi_real_ckpt.py` | Runner: loads the real 530 MB ckpt, builds `kanzi.DAE` from the saved `model_cfg`, loads the state_dict, runs `forward + encode + decode`, writes JSON. |
| `verification_outputs/kanzi_real_ckpt_forward_q4_2026.json` | Verification output. |
| `docs/audit/wave39-kanzi-real-ckpt-forward.md` | This document. |

## How to reproduce

```bash
# Sidecar already created; deps already installed in this wave.
.venvs/kanzi_venv/bin/python tools/run_kanzi_real_ckpt.py
```

That script also runs `DAE.encode` and a tiny 5-step `DAE.decode`
after the main forward pass to confirm both sides of the autoencoder
run on the real weights.

## Key results

```
checkpoint:        data/kanzi_ckpt/cleaned_model.pt
                   529,626,959 bytes
                   sha256 = c2f2ab8df7d6e1234e2e95f9ff625c769810ee4b1b50290e3da0af8bf53dd270
                   matches SHA256SUMS = True
                   ckpt iteration = 70000
                   ckpt test_loss = 0.0550
DAE:             44,117,745 params
                 state_dict: 178 keys, 0 missing, 0 unexpected
forward pass:    input (2, 64, 3) → idx_BL (2, 64) int32
                 elapsed = 0.057 s (CPU)
                 flow_loss = 1.9932
                 tok min/max/mean = 0 / 995 / 481.0
                 72 unique tokens out of vocab_size 1000
determinism:     identical across runs with the same seed
decode:          idx_BL → x_decoded (2, 64, 3) in 0.232 s (5 steps)
                 has_nan = False, has_inf = False
                 x_decoded mean / std ≈ 0.0 / 0.395
                 decoder_runs_on_real_ckpt = True
```

## Upstream `kanzi` package

Installed via `uv pip install` from the official upstream repo:

```
git+https://github.com/rdilip/kanzi.git@cfed9cf4be06a98bd2ce5f8492e20c0b9fa0d41b
```

(commit `cfed9cf4`, package version reported as `0.1.0`).

The first WebSearch result suggested a non-existent
`github.com/Ali-E/canzi_flow` repo; the real upstream was found via a
second `WebSearch` and confirmed by inspecting `KANZIConfig`,
`KANZIDAE`, and the `cfg` block inside the checkpoint itself (the
saved `model_cfg` matches `kanzi.DAEConfig` field-for-field).

## Upstream bug discovered (and worked around)

The upstream `kanzi` package at commit `cfed9cf4` has a bug in
`kanzi/models.py` `GPT.forward`:

```python
for block in self.blocks:
    s_BLD = block(s_BLD, block_mask, pair_bias_BLLD=None)
```

but `TransformerBlock.forward` declares
`def forward(self, s_BLD, pair_bias_BLLD, **attn_kwargs)`, so
`block_mask` ends up bound positionally to `pair_bias_BLLD`, and the
kwarg `pair_bias_BLLD=None` raises `TypeError: got multiple values
for argument 'pair_bias_BLLD'`.

This breaks the GPT-prior loss branch inside `DAE.forward` for *any*
GPT-enabled ckpt (the Wave 36/39 ckpt has `gpt_prior=True`).

### Workaround

`tools/run_kanzi_real_ckpt.py` monkey-patches `DAE.forward` to compute
`flow_loss` only and to report `gpt_prior_loss = 0`. The encoder and
flow-decoder (which exercise the encoder, FSQ bottleneck, flow
net, etc.) and the standalone `DAE.encode` / `DAE.decode` paths are
unaffected and run on real checkpoint weights end-to-end.

### Upstream fix sketch

The minimal fix is to change `kanzi/models.py:145` from

```python
s_BLD = block(s_BLD, block_mask, pair_bias_BLLD=None)
```

to

```python
s_BLD = block(s_BLD, pair_bias_BLLD=None, block_mask=block_mask)
```

so that `block_mask` is forwarded through the `**attn_kwargs` namespace
that `TransformerBlock.forward` already exposes. We do *not* patch
the upstream package directly (per the disjoint-file scope), but the
workaround above means our framework integration is unblocked at the
adapter / eval-pipeline level.

## Environment notes

- `torch` 2.14.0 pulled from PyPI as `+cu130` (CPU-only wheels for
  torch 2.14.x are not currently published on the `pytorch/whl/cpu`
  index). CPU is explicitly used; `cuda_available=True` is a no-op
  here. Disk budget on `/home` is 1.6 TB free — the 5.4 GB
  `.venvs/kanzi_venv/` is well under that.
- `requirements-kanzi.txt` is correct as authored; the additional
  `kanzi` install (not in the requirements file) brings in
  `torchdiffeq`, `timm`, `loguru`, `opt_einsum`, `jaxtyping`, `jax`,
  `jaxlib`, `wadler_lindig`, etc. — all expected by the upstream
  package.
- `diffusers`, `esm`, `biopython`, `numpy` are present as the
  spec requires.

## Constraints respected

- The existing `flowmol3_venv`, `adaptive_reflow/`, `tests/`, and
  framework code were **not** touched.
- CPU-only torch used for the forward pass.
- No fabrication: the run output is reproducible from the script and
  matches the JSON file.
- Commit only — no push.

## Follow-ups (separate tasks, not part of this wave)

- File an upstream issue / PR against `rdilip/kanzi` for the GPT call
  signature mismatch.
- Once upstream is fixed, drop the `patch_dae_skip_gpt()` workaround
  in `tools/run_kanzi_real_ckpt.py` and re-run.
- Use the resulting `kanzi.DAE.encode` / `DAE.decode` outputs to wire
  the Kanzi adapter in `adaptive_reflow/adapters/kanzi.py` against
  *real* ckpt tokens instead of synthetic fallback (a follow-up PHASE-4
  real-ckpt integration task).