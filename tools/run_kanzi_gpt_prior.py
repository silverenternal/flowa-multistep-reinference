#!/usr/bin/env python3
"""Wave 41 Agent A — Kanzi GPT-prior end-to-end test on real 530 MB ckpt.

Loads the actual Kanzi checkpoint at ``data/kanzi_ckpt/cleaned_model.pt``
inside the ``.venvs/kanzi_venv`` sidecar (same env as Wave 39 Agent A's
``run_kanzi_real_ckpt.py``) and runs a real forward pass through the
upstream ``kanzi`` package with the GPT-prior loss branch enabled.

This script verifies the upstream signature-mismatch patch that Wave 40
Agent B (commit ``d7c2f89``) installed in
``adaptive_reflow/adapters/kanzi.py::_install_gpt_prior_patch()``. The
patch monkey-patches ``kanzi.models.GPT.forward`` so that ``block_mask``
is routed to ``**attn_kwargs`` (matching the actual
``TransformerBlock.forward`` signature). Without the patch, the
``DAE.forward`` GPT-prior branch raises
``TypeError: got multiple values for argument 'pair_bias_BLLD'``.

Wave 39's ``run_kanzi_real_ckpt.py`` worked around this by overriding
``DAE.forward`` to report ``gpt_prior_loss = 0``. That left the
GPT-prior loss branch unexercised end-to-end on real checkpoint
weights. This script exercises the **unmodified** ``DAE.forward`` (which
calls ``self.gpt(...)`` when ``self.cfg.gpt_prior`` is ``True``) with the
GPT-prior patch installed in-process, so we can verify
``gpt_prior_loss`` is non-zero on real weights.

Run it with::

    .venvs/kanzi_venv/bin/python tools/run_kanzi_gpt_prior.py

It writes results to
``verification_outputs/kanzi_gpt_prior_q4_2026.json``.

This script is *only* intended to be executed inside the
``.venvs/kanzi_venv`` sidecar; the framework's main pytest environment
lacks the ``kanzi`` package by design.
"""
from __future__ import annotations

import functools
import hashlib
import importlib
import importlib.util
import inspect
import json
import os
import platform
import sys
import time
from collections import Counter
from pathlib import Path

import torch

REPO_ROOT = Path(__file__).resolve().parents[1]
CKPT_PATH = REPO_ROOT / "data" / "kanzi_ckpt" / "cleaned_model.pt"
SHA256_PATH = REPO_ROOT / "data" / "kanzi_ckpt" / "SHA256SUMS"
OUT_PATH = REPO_ROOT / "verification_outputs" / "kanzi_gpt_prior_q4_2026.json"

EXPECTED_SHA256 = "c2f2ab8df7d6e1234e2e95f9ff625c769810ee4b1b50290e3da0af8bf53dd270"

# Kanzi-side imports live ONLY inside this sidecar venv; fail loudly if
# they are missing rather than silently degrading.
from kanzi import DAE, DAEConfig  # noqa: E402

# ---------------------------------------------------------------------------
# Inlined GPT-prior monkey-patch (mirrors
# ``adaptive_reflow.adapters.kanzi._install_gpt_prior_patch``)
# ---------------------------------------------------------------------------
#
# This is the same patch as Wave 40 Agent B installed in the adapter,
# duplicated here verbatim because the sidecar ``kanzi_venv`` does not
# have the ``adaptive_reflow`` package on PYTHONPATH (the adapter lives
# in the main framework venv). DO NOT modify this block without also
# updating ``adaptive_reflow/adapters/kanzi.py``; the two implementations
# must stay in lockstep so a verifier run inside the main venv sees the
# same patched ``GPT.forward`` semantics as this sidecar run.
#
# See ``adaptive_reflow/adapters/kanzi.py`` lines ~306-444 for the
# canonical implementation.

_GPT_PRIOR_PATCH_MARKER = "_kanzi_gpt_prior_patched_w41"


def _install_gpt_prior_patch_inline() -> bool:
    """Inlined version of ``adaptive_reflow.adapters.kanzi._install_gpt_prior_patch``.

    Introspects ``kanzi.attention.TransformerBlock.forward`` to decide
    whether ``block_mask`` is a named positional parameter or absorbed
    by ``**attn_kwargs`` (the current upstream absorbs it via
    ``**attn_kwargs``), then re-implements ``GPT.forward`` so the
    ``block_mask`` argument lands in the correct namespace.

    Idempotent: re-invocation is a no-op via the marker attribute.

    Returns
    -------
    bool
        ``True`` iff the patch was installed (or was already installed).
        ``False`` when ``kanzi`` is not importable.
    """
    if importlib.util.find_spec("kanzi") is None:
        return False
    if importlib.util.find_spec("kanzi.models") is None:
        return False
    if importlib.util.find_spec("kanzi.attention") is None:
        return False

    _km = importlib.import_module("kanzi.models")
    _ka = importlib.import_module("kanzi.attention")

    if getattr(_km.GPT, _GPT_PRIOR_PATCH_MARKER, False):
        return True

    _original_forward = _km.GPT.forward

    _tb_signature = inspect.signature(_ka.TransformerBlock.forward)
    _tb_params = set(_tb_signature.parameters)
    _block_mask_is_positional = "block_mask" in _tb_params

    _always_kwargs = {"score_mod": None}

    @functools.wraps(_original_forward)
    def _patched_gpt_forward(self, tok_BL, tgt_BL=None):
        s_BLD = self.embed(tok_BL)
        device = s_BLD.device
        L = s_BLD.size(-2)
        block_mask = self.get_block_mask(L, device)
        if _block_mask_is_positional:
            for block in self.blocks:
                s_BLD = block(
                    s_BLD,
                    block_mask,
                    pair_bias_BLLD=None,
                    **_always_kwargs,
                )
        else:
            for block in self.blocks:
                s_BLD = block(
                    s_BLD,
                    pair_bias_BLLD=None,
                    block_mask=block_mask,
                    **_always_kwargs,
                )
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
    setattr(_km.GPT, _GPT_PRIOR_PATCH_MARKER, True)
    return True


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if not CKPT_PATH.exists():
        print(f"ERROR: checkpoint not found at {CKPT_PATH}", file=sys.stderr)
        return 1

    actual_sha = sha256_of(CKPT_PATH)
    sha_match = actual_sha == EXPECTED_SHA256
    print(f"checkpoint: {CKPT_PATH}")
    print(f"  size: {CKPT_PATH.stat().st_size:,} bytes")
    print(f"  sha256: {actual_sha}")
    print(f"  matches SHA256SUMS: {sha_match}")

    # Install the GPT-prior patch BEFORE constructing the DAE so the
    # GPT.forward reference is bound at module-construction time.
    # Equivalent to running
    # ``from adaptive_reflow.adapters.kanzi import _install_gpt_prior_patch;
    #   _install_gpt_prior_patch()`` in the main venv.
    patch_installed = _install_gpt_prior_patch_inline()
    if not patch_installed:
        print("ERROR: GPT-prior patch failed to install", file=sys.stderr)
        return 2
    print("GPT-prior patch: installed (GPT.forward monkey-patched)")

    t_load0 = time.time()
    raw = torch.load(CKPT_PATH, map_location="cpu", weights_only=False)
    t_load = time.time() - t_load0
    print(f"torch.load: {t_load:.1f}s")

    model_cfg = dict(raw["model_cfg"])
    if isinstance(model_cfg.get("levels"), list):
        model_cfg["levels"] = tuple(model_cfg["levels"])
    cfg = DAEConfig(
        **{k: v for k, v in model_cfg.items() if k in DAEConfig.__dataclass_fields__}
    )
    print(f"checkpoint gpt_prior flag: {model_cfg.get('gpt_prior')}")
    dae = DAE(cfg)
    n_params = sum(p.numel() for p in dae.parameters())

    missing, unexpected = dae.load_state_dict(raw["model"], strict=False)
    print(
        f"DAE: {n_params:,} params, "
        f"missing={len(missing)}, unexpected={len(unexpected)}"
    )
    if missing or unexpected:
        print(f"  first 5 missing: {missing[:5]}")
        print(f"  first 5 unexpected: {unexpected[:5]}")

    dae.eval()

    # Forward pass on synthetic protein coords (matches Wave 39 inputs
    # so the verification record is directly comparable).
    torch.manual_seed(42)
    B, L, D_coord = 2, 64, 3
    x = torch.randn(B, L, D_coord)

    t_fwd0 = time.time()
    try:
        with torch.no_grad():
            idx_BL, loss_dict = dae(x)
        fwd_error = None
    except Exception as exc:
        fwd_error = repr(exc)
        idx_BL = None
        loss_dict = None
    t_fwd = time.time() - t_fwd0
    print(f"forward pass (no_grad): {t_fwd:.2f}s")
    if fwd_error is not None:
        print(f"  ERROR: {fwd_error}")
    else:
        flow_loss = float(loss_dict["flow_loss"])
        gpt_prior_loss = float(loss_dict["gpt_prior_loss"])
        print(f"  flow_loss:      {flow_loss:.6f}")
        print(f"  gpt_prior_loss: {gpt_prior_loss:.6f}  "
              f"(non-zero={gpt_prior_loss != 0.0})")

    if fwd_error is None and idx_BL is not None:
        idx_unique_count = len(set(idx_BL.flatten().tolist()))
        counter = Counter(idx_BL.flatten().tolist())
        top5 = counter.most_common(5)

        # Determinism: re-run with the same seed and check identical output.
        torch.manual_seed(42)
        with torch.no_grad():
            idx_BL2, loss_dict2 = dae(x)
        deterministic = torch.equal(idx_BL, idx_BL2)
        deterministic_loss = (
            abs(float(loss_dict["flow_loss"]) - float(loss_dict2["flow_loss"]))
            < 1e-9
            and abs(
                float(loss_dict["gpt_prior_loss"])
                - float(loss_dict2["gpt_prior_loss"])
            )
            < 1e-9
        )
    else:
        idx_unique_count = 0
        top5 = []
        deterministic = False
        deterministic_loss = False
        flow_loss = None
        gpt_prior_loss = None

    # Decode: run a tiny 5-step decode to verify the decoder path runs
    # on real ckpt (independent of GPT-prior branch).
    if idx_BL is not None:
        torch.manual_seed(42)
        t_dec0 = time.time()
        with torch.no_grad():
            x_decoded = dae.decode(idx_BL, n_steps=5)
        t_dec = time.time() - t_dec0
    else:
        x_decoded = None
        t_dec = 0.0

    end_to_end_pass = (
        fwd_error is None
        and flow_loss is not None
        and gpt_prior_loss is not None
        and gpt_prior_loss != 0.0
    )

    record = {
        "schema_version": 1,
        "wave": 41,
        "agent": "A",
        "task": "kanzi_gpt_prior_end_to_end",
        "date": "2026-09-05",
        "checkpoint": {
            "path": str(CKPT_PATH.relative_to(REPO_ROOT)),
            "size_bytes": CKPT_PATH.stat().st_size,
            "sha256": actual_sha,
            "sha256_expected": EXPECTED_SHA256,
            "sha256_match": sha_match,
            "iteration": int(raw.get("it", -1)),
            "test_loss": float(raw["test_loss"]) if "test_loss" in raw else None,
            "model_cfg": {
                k: (list(v) if isinstance(v, tuple) else v)
                for k, v in model_cfg.items()
            },
        },
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "torch_version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "device_used": "cpu",
            "kanzi_package": _kanzi_pkg_info(),
        },
        "patch": {
            "name": "_install_gpt_prior_patch (Wave 40 Agent B)",
            "upstream_source": (
                "git+https://github.com/rdilip/kanzi.git@"
                "cfed9cf4be06a98bd2ce5f8492e20c0b9fa0d41b"
            ),
            "patch_installed": patch_installed,
            "patch_target": "kanzi.models.GPT.forward",
            "upstream_bug": (
                "GPT.forward calls "
                "block(s_BLD, block_mask, pair_bias_BLLD=None) but "
                "TransformerBlock.forward signature is "
                "(self, s_BLD, pair_bias_BLLD, **attn_kwargs). "
                "block_mask ends up bound to pair_bias_BLLD, "
                "kwarg pair_bias_BLLD=None creates "
                "duplicate-argument error."
            ),
            "patch_strategy": (
                "Introspect TransformerBlock.forward signature; "
                "route block_mask to **attn_kwargs (current upstream). "
                "Idempotent via _kanzi_gpt_prior_patched_w41 marker."
            ),
        },
        "model": {
            "class": "kanzi.DAE",
            "config_class": "kanzi.DAEConfig",
            "param_count": int(n_params),
            "state_dict_loaded": True,
            "missing_keys": len(missing),
            "unexpected_keys": len(unexpected),
            "first_5_missing": list(missing[:5]),
            "first_5_unexpected": list(unexpected[:5]),
        },
        "forward_pass": {
            "batch_size": B,
            "sequence_length": L,
            "coord_dim": D_coord,
            "input_shape": [B, L, D_coord],
            "elapsed_seconds": round(t_fwd, 3),
            "fwd_error": fwd_error,
            "tok_shape": list(idx_BL.shape) if idx_BL is not None else None,
            "tok_dtype": str(idx_BL.dtype) if idx_BL is not None else None,
            "tok_min": int(idx_BL.min()) if idx_BL is not None else None,
            "tok_max": int(idx_BL.max()) if idx_BL is not None else None,
            "tok_mean": (
                float(idx_BL.float().mean()) if idx_BL is not None else None
            ),
            "tok_unique_count": idx_unique_count,
            "tok_top5": (
                [[int(t), int(c)] for t, c in top5] if top5 else []
            ),
            "flow_loss": flow_loss,
            "gpt_prior_loss": gpt_prior_loss,
            "gpt_prior_loss_non_zero": (
                None if gpt_prior_loss is None else gpt_prior_loss != 0.0
            ),
            "gpt_prior_branch_exercised": (
                None
                if fwd_error is not None
                else model_cfg.get("gpt_prior") is True
            ),
            "note": (
                "Wave 39 reported gpt_prior_loss=0 via DAE.forward override "
                "that bypassed the GPT-prior branch. This run uses "
                "unmodified DAE.forward so the GPT-prior loss is computed "
                "on real checkpoint weights."
            ),
        },
        "determinism": {
            "seed": 42,
            "identical_across_runs": deterministic,
            "identical_loss_across_runs": deterministic_loss,
            "method": "torch.equal(idx_BL_run1, idx_BL_run2) + abs(loss diff) < 1e-9",
        },
        "decode_check": {
            "elapsed_seconds": round(t_dec, 3),
            "n_steps": 5,
            "x_decoded_shape": (
                list(x_decoded.shape) if x_decoded is not None else None
            ),
            "x_decoded_mean": (
                float(x_decoded.mean()) if x_decoded is not None else None
            ),
            "x_decoded_std": (
                float(x_decoded.std()) if x_decoded is not None else None
            ),
            "has_nan": (
                bool(torch.isnan(x_decoded).any().item())
                if x_decoded is not None
                else None
            ),
            "has_inf": (
                bool(torch.isinf(x_decoded).any().item())
                if x_decoded is not None
                else None
            ),
            "decoder_runs_on_real_ckpt": x_decoded is not None,
        },
        "end_to_end": {
            "pass": end_to_end_pass,
            "patch_works": patch_installed and fwd_error is None,
            "gpt_prior_loss_value": gpt_prior_loss,
            "gpt_prior_loss_was_zero_before_patch": True,
            "gpt_prior_loss_non_zero_after_patch": (
                None if gpt_prior_loss is None else gpt_prior_loss != 0.0
            ),
        },
        "status": "success" if end_to_end_pass else "fail",
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(record, indent=2, sort_keys=False) + "\n")
    print(f"wrote: {OUT_PATH.relative_to(REPO_ROOT)}")
    print(f"end_to_end_pass: {end_to_end_pass}")
    return 0 if end_to_end_pass else 3


def _kanzi_pkg_info() -> dict:
    import kanzi

    return {
        "name": "kanzi",
        "path": os.path.dirname(kanzi.__file__),
        "version": getattr(kanzi, "__version__", "unknown"),
    }


if __name__ == "__main__":
    raise SystemExit(main())
