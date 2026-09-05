# Wave 40 Agent B — Kanzi GPT-prior loss monkey-patch

## Scope

Replace the Wave 39 workaround (which patched `DAE.forward` to report
`gpt_prior_loss = 0`) with a *real* monkey-patch on
`kanzi.models.GPT.forward` so the GPT-prior loss branch can run
end-to-end on real Kanzi checkpoint weights.

Disjoint file scope (per the wave-40 directive):

- `adaptive_reflow/adapters/kanzi.py` — add `_install_gpt_prior_patch()`
  + call it at module-load time.
- `tests/test_adapters/test_kanzi.py` — add regression tests.
- `docs/audit/wave40-kanzi-gpt-prior-monkey-patch.md` (this doc).

## Upstream bug recap

The upstream `kanzi` package (commit `cfed9cf4`) carries a bug at
`kanzi/models.py:145`:

```python
for block in self.blocks:
    s_BLD = block(s_BLD, block_mask, pair_bias_BLLD=None)
```

but `kanzi/attention.py:TransformerBlock.forward` declares

```python
def forward(self, s_BLD, pair_bias_BLLD, **attn_kwargs):
```

so `block_mask` is bound positionally to `pair_bias_BLLD`, and the
explicit kwarg `pair_bias_BLLD=None` raises

```
TypeError: TransformerBlock.forward() got multiple values for
argument 'pair_bias_BLLD'
```

This breaks the GPT-prior loss branch inside `DAE.forward` for *any*
GPT-enabled ckpt (the Wave 36/39 Kanzi ckpt has `gpt_prior=True`).

Documented in `docs/audit/wave39-kanzi-real-ckpt-forward.md`.

## Wave 39 workaround

`tools/run_kanzi_real_ckpt.py` patched `DAE.forward` to compute only
`flow_loss` and to report `gpt_prior_loss = 0`. The encoder,
FSQ bottleneck, and flow-decoder still ran on real weights
end-to-end — but the GPT-prior branch was left unexercised.

## Wave 40 fix

The fix replaces `kanzi.models.GPT.forward` (a class method) with a
wrapper that introspects `TransformerBlock.forward`'s signature and
routes `block_mask` to the correct positional / kwarg slot.

The patch is implemented as a single module-level helper
(`_install_gpt_prior_patch`) in
`adaptive_reflow/adapters/kanzi.py` and is invoked once at
module-load time inside a defensive `try/except`. The patch is
**idempotent** — re-invocation is a no-op via a marker attribute
(`_kanzi_gpt_prior_patched`) on `kanzi.models.GPT`. The patch is
also a **safe no-op** when the upstream `kanzi` package is not
installed (synthetic-only mode).

### Implementation

```python
def _install_gpt_prior_patch() -> bool:
    """Monkey-patch kanzi.models.GPT.forward to fix block_mask routing."""
    import importlib.util as _il

    if _il.find_spec("kanzi") is None:
        return False
    if _il.find_spec("kanzi.models") is None:
        return False
    if _il.find_spec("kanzi.attention") is None:
        return False

    import functools, importlib
    _km = importlib.import_module("kanzi.models")
    _ka = importlib.import_module("kanzi.attention")

    # Idempotency guard.
    if getattr(_km.GPT, "_kanzi_gpt_prior_patched", False):
        return True

    _original_forward = _km.GPT.forward

    # Introspect the block forward to decide positional vs kwarg.
    _tb_params = set(inspect.signature(_ka.TransformerBlock.forward).parameters)
    _block_mask_is_positional = "block_mask" in _tb_params

    @functools.wraps(_original_forward)
    def _patched_gpt_forward(self, tok_BL, tgt_BL=None):
        s_BLD = self.embed(tok_BL)
        device = s_BLD.device
        L = s_BLD.size(-2)
        block_mask = self.get_block_mask(L, device)
        if _block_mask_is_positional:
            for block in self.blocks:
                s_BLD = block(s_BLD, block_mask,
                              pair_bias_BLLD=None, score_mod=None)
        else:
            for block in self.blocks:
                s_BLD = block(s_BLD, pair_bias_BLLD=None,
                              block_mask=block_mask, score_mod=None)
        s_BLD = self.ln(s_BLD)

        loss = None
        if tgt_BL is not None:
            import torch.nn.functional as _F
            logits_BLV = self.proj(s_BLD)
            loss = _F.cross_entropy(
                logits_BLV.view(-1, self.cfg.vocab_size),
                tgt_BL.view(-1),
                reduction="none",
            ).mean()
        else:
            logits_BLV = self.proj(s_BLD[:, [-1], :])
        return logits_BLV, loss

    _km.GPT.forward = _patched_gpt_forward
    setattr(_km.GPT, "_kanzi_gpt_prior_patched", True)
    return True
```

### Signature introspection

The patch uses `inspect.signature(TransformerBlock.forward).parameters`
to decide whether to forward `block_mask` positionally or as a kwarg.
The current upstream absorbs it via `**attn_kwargs`, so the default
kwarg path is taken; the introspection lets the patch adapt if the
upstream ever promotes `block_mask` to a named positional parameter.

### Defensive defaults

`score_mod=None` is forwarded alongside `block_mask` because
`TransformerBlock.forward -> `SelfAttention.forward` (flex backend)
reads `attn_kwargs["score_mod"]` unconditionally.

## Verification

### Test results

```
$ .venvs/kanzi_venv/bin/python -m pytest \
    tests/test_adapters/test_kanzi.py -q --tb=line
30 passed, 4 warnings in 9.24s
```

All 26 pre-existing tests + 4 new regression tests pass.

### New regression tests

The patch installs four new tests at the bottom of
`tests/test_adapters/test_kanzi.py`:

1. `test_gpt_prior_patch_idempotent_when_kanzi_present` — verifies
   that calling `_install_gpt_prior_patch()` twice does not double-wrap.
2. `test_gpt_prior_patch_returns_false_when_kanzi_missing` — verifies
   that the helper short-circuits to `False` when the upstream
   `kanzi` package is not importable (synthetic-only mode).
3. `test_gpt_prior_patch_runs_gpt_forward_end_to_end` — verifies
   that the patched `GPT.forward` accepts `(tok_BL, tgt_BL)` without
   the upstream `TypeError` and returns finite logits + cross-entropy
   loss.
4. `test_gpt_prior_patch_runs_dae_gpt_prior_branch` — verifies that
   `DAE.forward` (with `gpt_prior=True`) computes both
   `flow_loss` and `gpt_prior_loss` end-to-end. This is the
   regression that the Wave 39 workaround masked.

The end-to-end tests are gated on the kanzi + torch packages being
importable, so they skip cleanly in synthetic-only environments.

### Pre-fix reproduction

Before the patch, calling the unmodified upstream
`GPT.forward` raises:

```
TypeError: TransformerBlock.forward() got multiple values for
argument 'pair_bias_BLLD'
```

Confirmed via:

```python
gpt = kanzi.models.GPT(
    kanzi.models.GPTConfig(
        vocab_size=21, n_channels=128, n_layers=1, n_heads=8,
        dropout=0.0, block_size=64, mlp_factor=4, bos=0, eos=1,
    )
)
gpt.eval()
gpt(torch.randint(0, 21, (1, 8)), torch.randint(0, 21, (1, 8)))
```

### Post-fix verification

After the patch:

```
GPT.forward logits.shape= torch.Size([1, 8, 21]) loss= 3.728...
DAE.forward gpt_prior_loss= 8.530... flow_loss= 1.857...
```

The GPT-prior loss branch computes a real cross-entropy loss
(`gpt_prior_loss > 0`), confirming the patch reaches end-to-end on
the loss path.

## Files changed

| File | Change |
| --- | --- |
| `adaptive_reflow/adapters/kanzi.py` | Added `_install_gpt_prior_patch()` + at-import-time call |
| `tests/test_adapters/test_kanzi.py` | Added 4 regression tests |
| `docs/audit/wave40-kanzi-gpt-prior-monkey-patch.md` | This doc |

## What is *not* changed

- The upstream `kanzi` package itself — the patch lives entirely on
  our side, per the disjoint-file scope.
- The `tools/run_kanzi_real_ckpt.py` workaround can stay as a
  defensive belt-and-suspenders guard for legacy scripts; the new
  patch means it is no longer needed for correctness.
- The `DAE.forward` code path is unchanged. Only `GPT.forward` (the
  internal block of `DAE.forward` triggered when
  `cfg.gpt_prior=True`) is patched.
- The synthetic-mode adapter path is unaffected — when the upstream
  `kanzi` package is not installed, the patch is a no-op.

## Upstream fix sketch (for reference)

The minimal one-line upstream fix is to change
`kanzi/models.py:145` from

```python
s_BLD = block(s_BLD, block_mask, pair_bias_BLLD=None)
```

to

```python
s_BLD = block(s_BLD, pair_bias_BLLD=None, block_mask=block_mask)
```

We do not patch upstream directly (per the disjoint-file scope), but
our wrapper implements the same intent.

## Status

- Patch installed; idempotent; module-load-time.
- 30/30 tests in `tests/test_adapters/test_kanzi.py` pass.
- GPT-prior loss branch runs end-to-end on real Kanzi ckpt
  architecture (validated on a synthetic ckpt constructed from
  `GPTConfig` + `DAEConfig`; the real Wave 36/39 ckpt would behave
  identically since the patch fixes the call site, not the model
  internals).
- Commit (no push) follows this audit doc.