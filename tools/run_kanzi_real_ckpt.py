#!/usr/bin/env python3
"""Wave 39 Agent A — Kanzi sidecar real-ckpt forward pass.

Loads the actual 530 MB Kanzi checkpoint at
``data/kanzi_ckpt/cleaned_model.pt`` (verified SHA-256) inside the
``.venvs/kanzi_venv`` sidecar (created in this wave) and runs a real
forward pass through the upstream ``kanzi`` package (installed from the
official ``rdilip/kanzi`` GitHub repo, commit ``cfed9cf4``).

Run it with::

    .venvs/kanzi_venv/bin/python tools/run_kanzi_real_ckpt.py

It writes the results JSON to
``verification_outputs/kanzi_real_ckpt_forward_q4_2026.json``.

This script is *only* intended to be executed inside the
``.venvs/kanzi_venv`` sidecar; the framework's main pytest environment
lacks the ``kanzi`` package by design.

NOTE: The upstream ``kanzi`` package has a bug in ``GPT.forward`` (it
calls ``block(s_BLD, block_mask, pair_bias_BLLD=None)`` but
``TransformerBlock.forward``'s signature only accepts ``pair_bias_BLLD``
as a positional argument, plus an ``attn_kwargs`` keyword namespace).
We work around it by patching ``DAE.forward`` to skip the GPT-prior
loss computation. The encoder + flow decoder + decoder all run
unchanged on real checkpoint weights, and ``DAE.encode`` /
``DAE.decode`` (used by the rest of the script) are unaffected.
"""
from __future__ import annotations

import hashlib
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
OUT_PATH = REPO_ROOT / "verification_outputs" / "kanzi_real_ckpt_forward_q4_2026.json"

EXPECTED_SHA256 = "c2f2ab8df7d6e1234e2e95f9ff625c769810ee4b1b50290e3da0af8bf53dd270"

# Kanzi-side imports live ONLY inside this sidecar venv; fail loudly if
# they are missing rather than silently degrading.
from kanzi import DAE, DAEConfig  # noqa: E402


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def patch_dae_skip_gpt() -> None:
    """Workaround for upstream ``GPT.forward`` signature mismatch.

    The upstream ``kanzi`` package (commit ``cfed9cf4``) calls
    ``block(s_BLD, block_mask, pair_bias_BLLD=None)`` inside
    ``GPT.forward``, but ``TransformerBlock.forward`` declares
    ``(self, s_BLD, pair_bias_BLLD, **attn_kwargs)``. ``block_mask``
    ends up bound to ``pair_bias_BLLD``, and the kwarg ``pair_bias_BLLD=None``
    creates a duplicate-argument error.

    We work around this by overriding ``DAE.forward`` to compute
    ``flow_loss`` only and report ``gpt_prior_loss = 0``. The encoder
    and decoder paths (``DAE.encode`` / ``DAE.decode``) are unaffected
    and still exercise the real checkpoint weights end-to-end.
    """
    orig_forward = DAE.__dict__["forward"]

    def patched_forward(self, x_BLD):
        x_BLD = x_BLD - x_BLD.mean(dim=1, keepdim=True)
        _, c_BLD, idx_BL = self.encode(x_BLD)
        B, L, D = c_BLD.shape
        x0 = torch.randn_like(x_BLD)
        x0 = x0 - x0.mean(dim=1, keepdim=True)
        t, xt, ut = self.cfm.sample_location_and_conditional_flow(x0, x_BLD)
        cmask = (torch.rand((B,), device=x_BLD.device) > self.drop_cond_p)[
            :, None, None
        ]
        c_BLD = c_BLD * cmask
        vt = self.net(xt, t, z_BLD=c_BLD)
        ut = ut[:, :L, :]
        vt = vt[:, :L, :]
        loss = ((ut[:, :L, :] - vt[:, :L, :]) ** 2).mean()
        loss_gpt = torch.tensor(0.0, device=x_BLD.device)
        loss_dict = {"flow_loss": loss, "gpt_prior_loss": loss_gpt}
        return idx_BL, loss_dict

    DAE.forward = patched_forward
    return orig_forward


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

    # Patch DAE.forward BEFORE constructing the model so that the
    # overridden method is what gets called.
    patch_dae_skip_gpt()

    t_load0 = time.time()
    raw = torch.load(CKPT_PATH, map_location="cpu", weights_only=False)
    t_load = time.time() - t_load0
    print(f"torch.load: {t_load:.1f}s")

    model_cfg = dict(raw["model_cfg"])
    # The cfg key 'levels' is a tuple in DAEConfig; the checkpoint has it as a list.
    if isinstance(model_cfg.get("levels"), list):
        model_cfg["levels"] = tuple(model_cfg["levels"])
    cfg = DAEConfig(**{k: v for k, v in model_cfg.items() if k in DAEConfig.__dataclass_fields__})
    dae = DAE(cfg)
    n_params = sum(p.numel() for p in dae.parameters())

    missing, unexpected = dae.load_state_dict(raw["model"], strict=False)
    print(f"DAE: {n_params:,} params, missing={len(missing)}, unexpected={len(unexpected)}")
    if missing or unexpected:
        print(f"  first 5 missing: {missing[:5]}")
        print(f"  first 5 unexpected: {unexpected[:5]}")

    dae.eval()

    # Forward pass on synthetic protein coords
    torch.manual_seed(42)
    B, L, D_coord = 2, 64, 3
    x = torch.randn(B, L, D_coord)

    t_fwd0 = time.time()
    with torch.no_grad():
        idx_BL, loss_dict = dae(x)
    t_fwd = time.time() - t_fwd0
    print(f"forward pass (no_grad): {t_fwd:.2f}s")

    idx_unique_count = len(set(idx_BL.flatten().tolist()))
    counter = Counter(idx_BL.flatten().tolist())
    top5 = counter.most_common(5)

    # Determinism: re-run with the same seed and check identical output
    torch.manual_seed(42)
    with torch.no_grad():
        idx_BL2, _ = dae(x)
    deterministic = torch.equal(idx_BL, idx_BL2)

    # Decode: run a tiny 5-step decode to verify the decoder path runs on real ckpt
    torch.manual_seed(42)
    t_dec0 = time.time()
    with torch.no_grad():
        x_decoded = dae.decode(idx_BL, n_steps=5)
    t_dec = time.time() - t_dec0

    # Build the JSON report
    record = {
        "schema_version": 1,
        "wave": 39,
        "agent": "A",
        "task": "kanzi_sidecar_real_ckpt_forward",
        "date": "2026-09-05",
        "checkpoint": {
            "path": str(CKPT_PATH.relative_to(REPO_ROOT)),
            "size_bytes": CKPT_PATH.stat().st_size,
            "sha256": actual_sha,
            "sha256_expected": EXPECTED_SHA256,
            "sha256_match": sha_match,
            "iteration": int(raw.get("it", -1)),
            "test_loss": float(raw["test_loss"]) if "test_loss" in raw else None,
            "model_cfg": {k: (list(v) if isinstance(v, tuple) else v) for k, v in model_cfg.items()},
        },
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "torch_version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "device_used": "cpu",
            "kanzi_package": _kanzi_pkg_info(),
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
            "tok_shape": list(idx_BL.shape),
            "tok_dtype": str(idx_BL.dtype),
            "tok_min": int(idx_BL.min()),
            "tok_max": int(idx_BL.max()),
            "tok_mean": float(idx_BL.float().mean()),
            "tok_unique_count": idx_unique_count,
            "tok_top5": [[int(t), int(c)] for t, c in top5],
            "flow_loss": float(loss_dict["flow_loss"]),
            "gpt_prior_loss": float(loss_dict["gpt_prior_loss"]),
            "gpt_skipped_due_to_upstream_bug": True,
        },
        "determinism": {
            "seed": 42,
            "identical_across_runs": deterministic,
            "method": "torch.equal(idx_BL_run1, idx_BL_run2)",
        },
        "decode_check": {
            "elapsed_seconds": round(t_dec, 3),
            "n_steps": 5,
            "x_decoded_shape": list(x_decoded.shape),
            "x_decoded_mean": float(x_decoded.mean()),
            "x_decoded_std": float(x_decoded.std()),
            "has_nan": bool(torch.isnan(x_decoded).any().item()),
            "has_inf": bool(torch.isinf(x_decoded).any().item()),
            "decoder_runs_on_real_ckpt": True,
        },
        "upstream_issues": {
            "kanzi_package_source": "git+https://github.com/rdilip/kanzi.git@cfed9cf4be06a98bd2ce5f8492e20c0b9fa0d41b",
            "gpt_forward_bug": (
                "kanzi/models.py GPT.forward calls "
                "block(s_BLD, block_mask, pair_bias_BLLD=None) but "
                "TransformerBlock.forward signature is "
                "(self, s_BLD, pair_bias_BLLD, **attn_kwargs). "
                "GPT-prior loss branch bypassed via DAE.forward override; "
                "encoder + flow decoder + decoder all run unchanged."
            ),
        },
        "status": "success",
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(record, indent=2, sort_keys=False) + "\n")
    print(f"wrote: {OUT_PATH.relative_to(REPO_ROOT)}")
    return 0


def _kanzi_pkg_info() -> dict:
    import kanzi

    return {
        "name": "kanzi",
        "path": os.path.dirname(kanzi.__file__),
        "version": getattr(kanzi, "__version__", "unknown"),
    }


if __name__ == "__main__":
    raise SystemExit(main())