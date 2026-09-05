#!/usr/bin/env python3
"""Wave 41 Agent B — LineageFlow upstream real-ckpt numerical forward.

The script was originally authored by Wave 40 Agent A but never executed
end-to-end against the released checkpoint (Wave 40 stalled before the
upstream sidecar venv + clone + run cycle). Wave 41 Agent B re-ran it
on 2026-09-05 to verify the upstream code at commit ``ccef84ad`` loads
the real ckpt, runs the real denoiser, and exercises the real vector-field
+ Euler integration path on CPU.

Loads the released 10.5 GB LineageFlow checkpoint at
``data/lineageflow/lineageflow-rp55.ckpt`` (SHA-256 verified against the
value recorded in ``todo/models/lineageflow.md``) and runs a real
numerical forward through the **upstream** model code cloned from
``github.com/Jinx-byebye/LineageFlow`` (commit ``ccef84ad``), rather than
through the framework's synthetic stub.

Run it with::

    .venvs/lineageflow_venv/bin/python tools/run_lineageflow_real_ckpt.py

It writes the results JSON to
``verification_outputs/lineageflow_real_ckpt_forward_q4_2026.json``.

This script is *only* intended to be executed inside the
``.venvs/lineageflow_venv`` sidecar; the framework's main pytest
environment deliberately does not carry ``transformers`` + the ESM-2-650M
backbone.

Three things are exercised, in increasing depth:

1. **Checkpoint load** — via the upstream ``load_checkpoint_state``,
   which installs the ``core.sampler.SamplerConfig`` unpickling shim that
   Wave 36 Agent C identified and Wave 39 Agent B mirrored into
   ``adaptive_reflow/adapters/lineageflow.py``.
2. **Single denoiser forward** — ``LineageFlowClassifier(x_simplex, t)``
   → ``(B, L, 20)`` amino-acid logits, on real ESM-2-650M + real flow-head
   weights.
3. **Base-flow ODE integration** — a short Euler integration through the
   upstream ``integrate_base_flow`` / ``compute_family_vector_field``
   path, i.e. the actual numerical solver, not just one network call.

The reported decision metric is the Wave 33 **per-position mean entropy**
(``P2-W33-C``), which replaced the saturated ``family_validity`` metric.
The formula is inlined below and is byte-identical to
``tools/run_controlled_audit._per_position_entropy``; it is duplicated
rather than imported because this sidecar venv does not carry the
``adaptive_reflow`` package that module pulls in.

HONEST SCOPE NOTE: the model *weights* are real, and the denoiser and the
ODE solver are the real upstream implementations. The **family prior**
``alpha_h`` is synthetic — upstream ships family priors as separate JSON
assets (``--prior`` / ``--gap``) that are not part of the released
checkpoint and are not in this repo. A synthetic Dirichlet prior is used
so the vector-field path can be exercised end to end; this is recorded in
the output JSON under ``limitations``. No family-validity or foldability
claim is made from this run.
"""
from __future__ import annotations

import hashlib
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_DIR = REPO_ROOT / "data" / "lineageflow_upstream"
CKPT_PATH = REPO_ROOT / "data" / "lineageflow" / "lineageflow-rp55.ckpt"
OUT_PATH = (
    REPO_ROOT / "verification_outputs" / "lineageflow_real_ckpt_forward_q4_2026.json"
)

# Recorded in todo/models/lineageflow.md ("ckpt SHA-256 verified").
EXPECTED_SHA256 = "f0b4b25e626878be5c26da9e65d44c2e1551a076652d416f955b1357cde54a2b"

UPSTREAM_COMMIT = "ccef84adff421fcb6b855285bc1860e1f9a94f59"

# The upstream tree has no setup.py / pyproject.toml, so it cannot be
# ``pip install -e``'d. It is a plain source tree whose modules import each
# other as top-level packages (``from core.vector_field import c_h``,
# ``from models.model import ...``), so it must go on sys.path directly.
sys.path.insert(0, str(UPSTREAM_DIR))

from inference.inference import (  # noqa: E402
    compute_family_vector_field,
    integrate_base_flow,
    load_checkpoint_state,
)
from models.model import FlowTransformerConfig, LineageFlowClassifier  # noqa: E402

# Forward-pass geometry. Kept small: ESM-2-650M on CPU costs ~1-3 s per
# network call, and the Euler integration below makes ``EULER_STEPS`` of
# them.
BATCH = 4
SEQ_LEN = 64
AA_VOCAB = 20
EULER_STEPS = 8
T0 = 1.0
T1 = 4.0  # upstream's default --t-int; --t-max=16.0 is the full horizon
SEED = 42


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def per_position_entropy(endpoints: np.ndarray) -> float:
    """Wave 33 (P2-W33-C) LineageFlow decision metric.

    Per-position mean Shannon entropy of the endpoint distribution,
    treating the last axis as a distribution over the ``K`` amino-acid
    dimension (stable softmax along ``K``), averaged over positions and
    samples. Bounded above by ``log(K)``.

    Byte-identical to ``tools/run_controlled_audit._per_position_entropy``
    -- duplicated because this sidecar venv has no ``adaptive_reflow``.
    """
    if endpoints.size == 0 or endpoints.shape[0] < 2:
        return float("nan")
    z = endpoints - np.max(endpoints, axis=-1, keepdims=True)
    exp_z = np.exp(z)
    p = exp_z / np.sum(exp_z, axis=-1, keepdims=True)
    eps = 1e-12
    per_position = -np.sum(p * np.log(p + eps), axis=-1)
    return float(np.mean(per_position))


def simplex_entropy(x: np.ndarray) -> float:
    """Mean per-position entropy of an array that is *already* a simplex.

    ``per_position_entropy`` softmaxes its input, which is right for
    logits but wrong for the integrator's state ``x`` (already normalised
    along ``K``). This variant consumes the probabilities directly.
    """
    if x.size == 0:
        return float("nan")
    eps = 1e-12
    return float(np.mean(-np.sum(x * np.log(x + eps), axis=-1)))


def main() -> int:
    if not CKPT_PATH.exists():
        print(f"ERROR: checkpoint not found at {CKPT_PATH}", file=sys.stderr)
        return 1
    if not (UPSTREAM_DIR / "models" / "model.py").exists():
        print(f"ERROR: upstream clone missing at {UPSTREAM_DIR}", file=sys.stderr)
        return 1

    print(f"checkpoint: {CKPT_PATH}")
    print(f"  size: {CKPT_PATH.stat().st_size:,} bytes")
    t_sha0 = time.time()
    actual_sha = sha256_of(CKPT_PATH)
    sha_match = actual_sha == EXPECTED_SHA256
    print(f"  sha256: {actual_sha} ({time.time() - t_sha0:.1f}s)")
    print(f"  matches todo/models/lineageflow.md: {sha_match}")

    # --- Build the real upstream model (ESM-2-650M backbone + flow head).
    # The state dict carries no ``family_embed``/``input_proj``/
    # ``prior_weight_proj`` tensors, which pins the default
    # FlowTransformerConfig (family_embed_dim=0,
    # use_esm_token_embedding_expectation=True,
    # use_prior_weight_channel=False, alpha_max=16.0 == upstream --t-max).
    cfg = FlowTransformerConfig()
    t_build0 = time.time()
    model = LineageFlowClassifier(cfg)
    t_build = time.time() - t_build0
    n_params = sum(p.numel() for p in model.parameters())
    print(f"model built: {n_params:,} params ({t_build:.1f}s)")

    t_load0 = time.time()
    state = load_checkpoint_state(CKPT_PATH, map_location="cpu")
    t_load = time.time() - t_load0
    print(f"load_checkpoint_state: {t_load:.1f}s, {len(state)} tensors")

    incompatible = model.load_state_dict(state, strict=False)
    missing = list(incompatible.missing_keys)
    unexpected = list(incompatible.unexpected_keys)
    print(f"load_state_dict: missing={len(missing)} unexpected={len(unexpected)}")
    if missing:
        print(f"  first 5 missing: {missing[:5]}")
    if unexpected:
        print(f"  first 5 unexpected: {unexpected[:5]}")

    # A real load must actually have matched the flow head; if every key
    # were missing we would still be running randomly-initialised weights
    # and the "real ckpt" claim would be false.
    head_loaded = "out_head.weight" not in missing and "norm_out.weight" not in missing
    encoder_keys_matched = len(state) - len(unexpected)

    model.eval()

    # --- Inputs. x_simplex must live on the probability simplex.
    torch.manual_seed(SEED)
    logits_init = torch.randn(BATCH, SEQ_LEN, AA_VOCAB)
    x_simplex = torch.softmax(logits_init, dim=-1)
    pad_mask = torch.ones(BATCH, SEQ_LEN, dtype=torch.bool)
    gap_mask = torch.zeros(BATCH, SEQ_LEN, dtype=torch.bool)
    t_vec = torch.full((BATCH,), T0)

    # --- (2) Single denoiser forward on real weights.
    t_fwd0 = time.time()
    with torch.no_grad():
        aa_logits = model(
            x_simplex=x_simplex,
            t=t_vec,
            pad_mask=pad_mask,
            gap_flag=gap_mask,
            family_id=None,
        )
    t_fwd = time.time() - t_fwd0
    print(f"denoiser forward: {t_fwd:.2f}s -> {tuple(aa_logits.shape)}")

    logits_np = aa_logits.detach().cpu().numpy().astype(np.float64)
    forward_entropy = per_position_entropy(logits_np)
    print(f"  per-position entropy (Wave 33 metric): {forward_entropy:.6f}")
    print(f"  log(K) upper bound: {float(np.log(AA_VOCAB)):.6f}")

    # Determinism: model.eval() disables dropout, so a second identical
    # call must be bit-identical.
    with torch.no_grad():
        aa_logits2 = model(
            x_simplex=x_simplex,
            t=t_vec,
            pad_mask=pad_mask,
            gap_flag=gap_mask,
            family_id=None,
        )
    deterministic = bool(torch.equal(aa_logits, aa_logits2))
    print(f"  deterministic across two calls: {deterministic}")

    # --- (3) Real vector field + Euler ODE integration.
    # SYNTHETIC PRIOR: upstream ships family priors as separate JSON
    # assets that the released checkpoint does not contain. We build a
    # smooth Dirichlet-style prior so the solver path is exercised; no
    # family-specific claim follows from it.
    gen = torch.Generator().manual_seed(SEED)
    alpha_h = torch.rand((SEQ_LEN, AA_VOCAB), generator=gen) * 0.5 + 0.25
    alpha_h = alpha_h * (10.0 / alpha_h.sum(dim=-1, keepdim=True))  # concentration 10

    t_vf0 = time.time()
    with torch.no_grad():
        v = compute_family_vector_field(
            x_simplex,
            t_vec,
            aa_logits,
            alpha_h,
            pad_mask=pad_mask,
            gap_mask=gap_mask,
        )
    t_vf = time.time() - t_vf0
    v_np = v.detach().cpu().numpy().astype(np.float64)
    print(f"vector field: {t_vf:.2f}s -> {tuple(v.shape)}")
    # The field is tangent to the simplex, so each position's components
    # must sum to ~0 (it moves mass around, it does not create it).
    tangency = float(np.abs(v_np.sum(axis=-1)).max())
    print(f"  max |sum_K v| (simplex tangency, want ~0): {tangency:.3e}")

    t_int0 = time.time()
    with torch.no_grad():
        x_end = integrate_base_flow(
            model=model,
            x0=x_simplex,
            alpha_h=alpha_h,
            t0=T0,
            t1=T1,
            pad_mask=pad_mask,
            gap_mask=gap_mask,
            family_id=None,
            steps=EULER_STEPS,
            method="euler",
        )
    t_int = time.time() - t_int0
    x_end_np = x_end.detach().cpu().numpy().astype(np.float64)
    print(f"integrate_base_flow({EULER_STEPS} Euler steps): {t_int:.1f}s")

    start_entropy = simplex_entropy(x_simplex.numpy().astype(np.float64))
    end_entropy = simplex_entropy(x_end_np)
    simplex_sums = x_end_np.sum(axis=-1)
    print(f"  simplex entropy: start={start_entropy:.6f} end={end_entropy:.6f}")
    print(f"  simplex residual: max|sum-1|={float(np.abs(simplex_sums - 1.0).max()):.3e}")

    record = {
        "schema_version": 1,
        "wave": 41,
        "agent": "B",
        "task": "lineageflow_upstream_real_ckpt_numerical_forward",
        "date": "2026-09-05",
        "status": "success",
        "checkpoint": {
            "path": str(CKPT_PATH.relative_to(REPO_ROOT)),
            "size_bytes": CKPT_PATH.stat().st_size,
            "sha256": actual_sha,
            "sha256_expected": EXPECTED_SHA256,
            "sha256_match": sha_match,
            "sha256_source": "todo/models/lineageflow.md",
            "state_dict_tensors": len(state),
        },
        "upstream": {
            "repo": "https://github.com/Jinx-byebye/LineageFlow",
            "commit": UPSTREAM_COMMIT,
            "clone_path": str(UPSTREAM_DIR.relative_to(REPO_ROOT)),
            "pip_installable": False,
            "install_method": "sys.path insert (no setup.py / pyproject.toml upstream)",
            "checkpoint_compat_shim": (
                "inference.inference._install_checkpoint_compat fabricates "
                "core.sampler.SamplerConfig for safe-globals unpickling; this is "
                "the same shim Wave 39 Agent B mirrored into "
                "adaptive_reflow/adapters/lineageflow.py"
            ),
        },
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "torch_version": torch.__version__,
            "numpy_version": np.__version__,
            "cuda_available": torch.cuda.is_available(),
            "device_used": "cpu",
            "venv": ".venvs/lineageflow_venv",
            "requirements": "requirements-lineageflow.txt",
        },
        "model": {
            "class": "models.model.LineageFlowClassifier",
            "config_class": "models.model.FlowTransformerConfig",
            "config": {
                "pretrained_model_name": cfg.pretrained_model_name,
                "aa_vocab": cfg.aa_vocab,
                "use_esm_token_embedding_expectation": cfg.use_esm_token_embedding_expectation,
                "family_embed_dim": cfg.family_embed_dim,
                "use_prior_weight_channel": cfg.use_prior_weight_channel,
                "alpha_min": cfg.alpha_min,
                "alpha_max": cfg.alpha_max,
                "normalize_time": cfg.normalize_time,
            },
            "param_count": int(n_params),
            "build_seconds": round(t_build, 2),
            "ckpt_load_seconds": round(t_load, 2),
            "state_dict_loaded": True,
            "strict": False,
            "missing_keys": len(missing),
            "unexpected_keys": len(unexpected),
            "first_5_missing": missing[:5],
            "first_5_unexpected": unexpected[:5],
            "flow_head_weights_loaded": head_loaded,
            "ckpt_keys_matched": int(encoder_keys_matched),
        },
        "forward_pass": {
            "batch_size": BATCH,
            "sequence_length": SEQ_LEN,
            "aa_vocab": AA_VOCAB,
            "t": T0,
            "input_shape": [BATCH, SEQ_LEN, AA_VOCAB],
            "output_shape": list(aa_logits.shape),
            "elapsed_seconds": round(t_fwd, 3),
            "logits_min": float(logits_np.min()),
            "logits_max": float(logits_np.max()),
            "logits_mean": float(logits_np.mean()),
            "logits_std": float(logits_np.std()),
            "has_nan": bool(np.isnan(logits_np).any()),
            "has_inf": bool(np.isinf(logits_np).any()),
        },
        "wave33_metric": {
            "name": "per_position_mean_entropy",
            "provenance": "P2-W33-C; formula matches tools/run_controlled_audit._per_position_entropy",
            "value": forward_entropy,
            "upper_bound_log_K": float(np.log(AA_VOCAB)),
            "saturated": bool(
                abs(forward_entropy - float(np.log(AA_VOCAB))) < 1e-6
                or forward_entropy < 1e-6
            ),
        },
        "vector_field": {
            "fn": "inference.inference.compute_family_vector_field",
            "elapsed_seconds": round(t_vf, 3),
            "shape": list(v.shape),
            "abs_mean": float(np.abs(v_np).mean()),
            "abs_max": float(np.abs(v_np).max()),
            "simplex_tangency_max_abs_row_sum": tangency,
            "has_nan": bool(np.isnan(v_np).any()),
        },
        "ode_integration": {
            "fn": "inference.inference.integrate_base_flow",
            "method": "euler",
            "steps": EULER_STEPS,
            "t0": T0,
            "t1": T1,
            "elapsed_seconds": round(t_int, 2),
            "network_calls": EULER_STEPS,
            "endpoint_shape": list(x_end.shape),
            "simplex_entropy_start": start_entropy,
            "simplex_entropy_end": end_entropy,
            "simplex_entropy_delta": end_entropy - start_entropy,
            "simplex_residual_max_abs": float(np.abs(simplex_sums - 1.0).max()),
            "endpoint_min": float(x_end_np.min()),
            "endpoint_max": float(x_end_np.max()),
            "has_nan": bool(np.isnan(x_end_np).any()),
            "has_inf": bool(np.isinf(x_end_np).any()),
        },
        "determinism": {
            "seed": SEED,
            "eval_mode": True,
            "identical_across_two_forward_calls": deterministic,
            "method": "torch.equal(aa_logits_call1, aa_logits_call2)",
        },
        "limitations": [
            "The family prior alpha_h is SYNTHETIC. Upstream ships family "
            "priors and gap rates as separate JSON assets (--prior / --gap) "
            "that are not part of the released checkpoint and are not in this "
            "repo. The prior here is a smooth Dirichlet-style array with "
            "concentration 10, used only so the vector-field and ODE paths "
            "can be exercised end to end.",
            "No family_validity / foldability / self-consistency score is "
            "computed. Those need HMMER, OmegaFold, MMseqs2 and ESM-IF, none "
            "of which are installed in this sidecar.",
            "The integration covers t0=1.0 -> t1=4.0 with 8 Euler steps, not "
            "the paper's t_max=16.0 with 200+200 steps. This is a numerical "
            "smoke of the real solver on CPU, not a sampling-quality run.",
            "CPU only. No CUDA kernels were exercised.",
        ],
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(record, indent=2, sort_keys=False) + "\n")
    print(f"wrote: {OUT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
