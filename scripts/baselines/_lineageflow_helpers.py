"""Shared helpers for Wave 52 LineageFlow baseline scripts.

The helpers below are *only* intended to be imported by the
``scripts/baselines/run_lineageflow_*.py`` scripts. They reproduce the
three composite phi components that the framework's
``LineageFlowGlue.compute_composite`` consumes (per
``adaptive_reflow/adapters/lineageflow_glue.py``), so each baseline's
endpoint can be turned into a comparable (composite, phi1, phi2, phi3)
triple and dropped into the Wave 52 audit doc.

Why duplicate rather than import: the sidecar venv
(``.venvs/lineageflow_venv``) deliberately does NOT carry the
``adaptive_reflow`` package. The Wave 47 framework composite code lives
inside that package. Duplicating the formula (≈ 25 LOC) here is
substantially cheaper than dragging in the full framework surface just
to call a single helper.

All math is byte-identical to
``adaptive_reflow/adapters/lineageflow_glue.py:LineageFlowGlue.compute_composite``.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[2]
UPSTREAM_DIR = REPO_ROOT / "data" / "lineageflow_upstream"
CKPT_PATH = REPO_ROOT / "data" / "lineageflow" / "lineageflow-rp55.ckpt"

# Wave 47 (Glue) constants — must stay byte-identical with
# adaptive_reflow/adapters/lineageflow_glue.py.
LINEAGEFLOW_VOCAB_SIZE: int = 33
DEFAULT_COMPOSITE_WEIGHTS: tuple[float, float, float] = (0.40, 0.35, 0.25)


def _add_upstream_to_path() -> None:
    """Insert ``data/lineageflow_upstream`` at the front of ``sys.path``.

    The upstream tree has no ``setup.py`` / ``pyproject.toml``, so it
    cannot be ``pip install -e``'d — modules import each other as
    top-level packages (``from core.vector_field import c_h``).
    """
    p = str(UPSTREAM_DIR)
    if p not in sys.path:
        sys.path.insert(0, p)


def load_lineageflow_model(device: str = "cpu"):
    """Build the LineageFlowClassifier and load the real ckpt.

    Returns ``(model, n_params, build_seconds, load_seconds, ckpt_keys_matched)``.
    """
    _add_upstream_to_path()
    from inference.inference import load_checkpoint_state  # noqa: E402
    from models.model import FlowTransformerConfig, LineageFlowClassifier  # noqa: E402

    t_build0 = time.time()
    cfg = FlowTransformerConfig()
    model = LineageFlowClassifier(cfg)
    t_build = time.time() - t_build0

    t_load0 = time.time()
    state = load_checkpoint_state(CKPT_PATH, map_location=device)
    t_load = time.time() - t_load0

    incompatible = model.load_state_dict(state, strict=False)
    n_unexpected = len(incompatible.unexpected_keys)
    _n_missing = len(incompatible.missing_keys)

    model.eval()
    n_params = sum(p.numel() for p in model.parameters())
    return model, n_params, t_build, t_load, len(state) - n_unexpected


def make_inputs(
    *,
    batch_size: int,
    seq_len: int,
    aa_vocab: int,
    seed: int,
    device: str = "cpu",
):
    """Build the standard inputs for a LineageFlow forward pass.

    Returns ``(x_simplex, pad_mask, gap_mask, alpha_h, t_vec)``.
    ``alpha_h`` is a synthetic Dirichlet-style prior with concentration
    10 per position — see ``tools/run_lineageflow_real_ckpt.py`` for
    why this is necessary (upstream priors ship as JSON assets not in
    this repo).
    """
    torch.manual_seed(seed)
    logits_init = torch.randn(batch_size, seq_len, aa_vocab)
    x_simplex = torch.softmax(logits_init, dim=-1)
    pad_mask = torch.ones(batch_size, seq_len, dtype=torch.bool)
    gap_mask = torch.zeros(batch_size, seq_len, dtype=torch.bool)

    gen = torch.Generator().manual_seed(seed)
    alpha_h = torch.rand((seq_len, aa_vocab), generator=gen) * 0.5 + 0.25
    alpha_h = alpha_h * (10.0 / alpha_h.sum(dim=-1, keepdim=True))

    t_vec = torch.full((batch_size,), 1.0)
    return x_simplex, pad_mask, gap_mask, alpha_h, t_vec


def per_position_entropy(x: np.ndarray, *, eps: float = 1e-12) -> float:
    """Per-position mean Shannon entropy of an already-simplex tensor.

    Mirrors ``tools/run_lineageflow_real_ckpt.py:simplex_entropy``.
    Bounded above by ``log(K)`` where ``K = x.shape[-1]``.
    """
    if x.size == 0:
        return float("nan")
    return float(np.mean(-np.sum(x * np.log(x + eps), axis=-1)))


def phi1_entropy_reduction_normalised(
    theta_b: np.ndarray, theta_f: np.ndarray, K: int
) -> float:
    """Wave 47 phi1: normalised per-position entropy reduction.

    ``phi1 = mean(entropy(theta_b) - entropy(theta_f)) / log K``

    Bounded in ``[-1, +1]``: positive means framework concentrates the
    simplex (lower entropy than baseline).
    """
    eps = 1e-12
    def _ent(t):
        return -np.sum(t * np.log(t + eps), axis=-1)
    b = _ent(theta_b)
    f = _ent(theta_f)
    return float(np.mean(b - f) / np.log(K))


def phi2_max_prob_delta(theta_b: np.ndarray, theta_f: np.ndarray) -> float:
    """Wave 47 phi2: mean shift in per-position max probability.

    ``phi2 = mean(max(theta_f) - max(theta_b))``

    Bounded in ``[-1, +1]``: positive means framework sharpens the
    per-position argmax.
    """
    return float(np.mean(np.max(theta_f, axis=-1) - np.max(theta_b, axis=-1)))


def phi3_argmax_turnover_signed(theta_b: np.ndarray, theta_f: np.ndarray) -> float:
    """Wave 47 phi3: signed argmax turnover per position.

    ``phi3 = 2 * mean(argmax(theta_f) != argmax(theta_b)) - 1``

    Bounded in ``[-1, +1]``: +1 means every position changed argmax;
    -1 means no position changed.
    """
    a_b = np.argmax(theta_b, axis=-1)
    a_f = np.argmax(theta_f, axis=-1)
    diff_rate = float(np.mean(a_b != a_f))
    return 2.0 * diff_rate - 1.0


def compute_composite(
    theta_b: np.ndarray,
    theta_f: np.ndarray,
    *,
    weights: tuple[float, float, float] = DEFAULT_COMPOSITE_WEIGHTS,
    K: int = LINEAGEFLOW_VOCAB_SIZE,
) -> dict[str, float]:
    """Compute the Wave 47 LineageFlow composite for an endpoint pair.

    Mirrors ``LineageFlowGlue.compute_composite`` but uses bare
    numpy arrays (no adapter / trace / native-state-cache plumbing)
    because the sidecar venv does not have access to
    ``adaptive_reflow``. Returns the same dict shape:
    ``{composite, phi1_..., phi2_..., phi3_..., weights, K}``.
    """
    phi1 = phi1_entropy_reduction_normalised(theta_b, theta_f, K)
    phi2 = phi2_max_prob_delta(theta_b, theta_f)
    phi3 = phi3_argmax_turnover_signed(theta_b, theta_f)
    w1, w2, w3 = weights
    composite = w1 * phi1 + w2 * phi2 + w3 * phi3
    return {
        "composite": composite,
        "phi1_entropy_reduction_normalised": phi1,
        "phi2_max_prob_delta": phi2,
        "phi3_argmax_turnover_signed": phi3,
        "weights": list(weights),
        "K": K,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write ``payload`` as pretty JSON, creating parent dirs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")


# Shared default sweep geometry for all 3 baselines.
DEFAULT_BATCH_SIZE: int = 2
DEFAULT_SEQ_LEN: int = 32
DEFAULT_AA_VOCAB: int = 20
DEFAULT_SEED: int = 42
DEFAULT_NFE_LIST: tuple[int, ...] = (10, 50)
DEFAULT_T0: float = 1.0
DEFAULT_T1: float = 4.0
