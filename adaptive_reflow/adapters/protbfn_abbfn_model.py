"""Pure-PyTorch implementation of the InstaDeep ProtBFN / AbBFN BFN encoder.

The model architecture mirrors ``data/protbfn_abbfn/repo/model.py``
(:func:`get_transformer_fn`):

* Input: per-position categorical ``theta`` of shape ``(L, K)`` where
  ``K == 32`` (the full tokenizer vocabulary: 6 control tokens +
  26 amino-acid-like tokens). The BFN sender operates on this
  ``K``-way categorical.
* :func:`apply_entropy_encoding` concatenates a 32-dim
  Fourier-of-entropy feature (16 sin + 16 cos), giving an
  ``(L, 64)`` encoder input.
* :class:`Transformer` = a 33-layer BERT-style encoder:
  ``embed_dim=1280``, ``ffn_embed_dim=5120``, ``num_heads=20``,
  ``qkv_size=64``. Rotary embeddings inside the multi-head attention.
* :class:`RobertaHead` is the per-position classifier: LayerNorm ->
  Linear(1280 -> 1280) -> GELU -> LayerNorm -> Linear(1280 -> K).
* Total: 650M parameters, vocab_size ``K = 32``.

The encoder forward returns logits of shape ``(L, K)``. The BFN
sampling loop in :mod:`adaptive_reflow.adapters.protbfn_abbfn_adapter`
interprets those logits as the per-step "phi" posterior (passed through
softmax) and refines the per-position categorical accordingly.

The module is built as a single :class:`torch.nn.Module` for
convenience and loaded directly from a :class:`ProtBFNParamTree` via
:meth:`ProtBFNTransformer.load_from_pytree`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import torch
from torch import nn

# ---------------------------------------------------------------------------
# Constants - mirror data/protbfn_abbfn/repo/model.py
# ---------------------------------------------------------------------------

#: Tokenizer vocabulary size (5 control tokens + 26 amino-acid tokens + 1 bos
#: token; matches ``id_to_token`` in repo/utils.py). NOTE: this is the K
#: dimension used by the published ProtBFN/AbBFN encoder and is different
#: from the engine-level 22-entry amino-acid channel.
PROTBFN_VOCAB_SIZE: int = 32

#: Per-position categorical dimension before Fourier-entropy encoding.
#: ``vocab_size = 32`` always.
ENTROPY_INPUT_DIM: int = PROTBFN_VOCAB_SIZE  # 32

#: Fourier-feature dimension. ``fourier_dim // 2`` frequencies are
#: sin-encoded and another ``fourier_dim // 2`` are cos-encoded,
#: then concatenated with the input theta.
FOURIER_DIM: int = 32

#: Encoder input dimension after entropy encoding.
#: ``theta`` (32) + sin features (16) + cos features (16) = 64.
ENCODER_INPUT_DIM: int = ENTROPY_INPUT_DIM + FOURIER_DIM  # 64

#: Embedding dimension inside the transformer.
EMBED_DIM: int = 1280

#: FFN hidden dimension inside each self-attention block.
FFN_EMBED_DIM: int = 5120

#: Number of self-attention layers (33, paper Table 1).
NUM_LAYERS: int = 33

#: Number of attention heads (20).
NUM_HEADS: int = 20

#: Per-head key/query size (``embed_dim // num_heads``).
QKV_SIZE: int = EMBED_DIM // NUM_HEADS  # 64

#: Rotary-embedding upper frequency (10000, RoFormer paper default).
UPPER_FREQ: float = 10_000.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def gelu_exact(x: torch.Tensor) -> torch.Tensor:
    """Exact GELU activation (matches ``jax.nn.gelu(approximate=False)``)."""
    # 0.5 * x * (1 + erf(x / sqrt(2)))
    return torch.nn.functional.gelu(x, approximate="none")


def apply_entropy_encoding(theta: torch.Tensor) -> torch.Tensor:
    """Per-variable Fourier-of-entropy encoding.

    Mirrors ``data/protbfn_abbfn/repo/model.py:364``. ``theta`` has
    shape ``(L, K)``; the result has shape ``(L, K + 32)``.
    """
    L, K = theta.shape
    # Per-position entropy H(theta_i) = -sum theta_i * log(theta_i + eps)
    log_theta = torch.log(theta + 1e-12)
    entropy = -(theta * log_theta).sum(dim=-1)  # (L,)
    max_entropy = -math.log(K)  # scalar (log of vocab size)
    # Express entropy as a fraction of maximum possible entropy, then
    # sqrt-compress to [-1, 1].
    entropy_param = torch.sqrt(
        torch.clamp(1.0 - entropy / max_entropy, min=0.0, max=1.0)
    )  # (L,)
    # 16 frequencies: 2^(-1) .. 2^(14)
    fourier_n_freqs = FOURIER_DIM // 2  # 16
    fourier_base = (
        math.pi
        * (2.0 ** torch.arange(-1, fourier_n_freqs - 1, dtype=theta.dtype, device=theta.device))
    )  # (16,)
    fourier_base = fourier_base.broadcast_to((L, fourier_n_freqs))
    sin_emb = torch.sin(entropy_param.unsqueeze(-1) * fourier_base)
    cos_emb = torch.cos(entropy_param.unsqueeze(-1) * fourier_base)
    fourier_embedding = torch.cat([sin_emb, cos_emb], dim=-1)  # (L, 32)
    return torch.cat([theta, fourier_embedding], dim=-1)  # (L, 64)


def _inv_freq(qkv_size: int) -> torch.Tensor:
    """RoFormer inverse-frequency schedule for rotary embeddings."""
    return 1.0 / (
        UPPER_FREQ ** (torch.arange(0, qkv_size, 2, dtype=torch.float32) / qkv_size)
    )


def _rotary_embedding(heads: torch.Tensor, inv_freq: torch.Tensor) -> torch.Tensor:
    """Apply RoFormer rotary embeddings to ``heads``.

    ``heads`` has shape ``(L, num_heads, qkv_size)``. Returns the same
    shape with rotary position embeddings applied to the last axis.
    """
    L = heads.shape[0]
    t = torch.arange(L, dtype=inv_freq.dtype, device=heads.device)
    freqs = torch.einsum("i,j->ij", t, inv_freq)  # (L, qkv_size//2)
    emb = torch.cat([freqs, freqs], dim=-1)  # (L, qkv_size)
    sin_emb = torch.sin(emb)[:, None, :]  # (L, 1, qkv_size)
    cos_emb = torch.cos(emb)[:, None, :]
    half = heads.shape[-1] // 2
    x1 = heads[..., :half]
    x2 = heads[..., half:]
    heads_rotated = torch.cat([-x2, x1], dim=-1)
    return heads * cos_emb + heads_rotated * sin_emb


# ---------------------------------------------------------------------------
# Modules
# ---------------------------------------------------------------------------


class MultiHeadAttention(nn.Module):
    """Multi-head attention with rotary embeddings.

    Mirrors ``data/protbfn_abbfn/repo/model.py:41``. Returns the
    attention output of shape ``(L, embed_dim)``.
    """

    def __init__(self, num_heads: int, qkv_size: int) -> None:
        super().__init__()
        self.num_heads = num_heads
        self.qkv_size = qkv_size
        self.embed_dim = num_heads * qkv_size
        # He-uniform init: bound = sqrt(6 / fan_in) where fan_in = embed_dim
        # (matches ``initializers.VarianceScaling(2.0, 'fan_in', 'uniform')``).
        self.register_buffer("inv_freq", _inv_freq(qkv_size))
        # Per-head projection: in -> num_heads * qkv_size
        self.query = nn.Linear(self.embed_dim, num_heads * qkv_size)
        self.key = nn.Linear(self.embed_dim, num_heads * qkv_size)
        self.value = nn.Linear(self.embed_dim, num_heads * qkv_size)
        # Output projection: num_heads * qkv_size -> embed_dim
        self.mha_output = nn.Linear(num_heads * qkv_size, num_heads * qkv_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass. ``x`` shape ``(L, embed_dim)`` -> same."""
        L = x.shape[0]
        # Project to (L, num_heads, qkv_size)
        q = self.query(x).reshape(L, self.num_heads, self.qkv_size)
        k = self.key(x).reshape(L, self.num_heads, self.qkv_size)
        v = self.value(x).reshape(L, self.num_heads, self.qkv_size)
        # Apply rotary embeddings to q and k only
        q = _rotary_embedding(q, self.inv_freq)
        k = _rotary_embedding(k, self.inv_freq)
        # Attention logits: (num_heads, L, L)
        attn_logits = torch.einsum("thd,Thd->htT", q, k) / math.sqrt(self.qkv_size)
        attn = torch.softmax(attn_logits, dim=-1)
        # Combine with values: (L, num_heads, qkv_size)
        out = torch.einsum("htT,Thd->thd", attn, v)
        # Concatenate heads: (L, num_heads * qkv_size)
        out = out.reshape(L, self.num_heads * self.qkv_size)
        return self.mha_output(out)


class SelfAttentionBlock(nn.Module):
    """Single BERT-style block: LayerNorm -> MHA -> residual, then LN -> FFN -> residual.

    Mirrors ``data/protbfn_abbfn/repo/model.py:196``.
    """

    def __init__(
        self, num_heads: int, embed_dim: int, ffn_embed_dim: int
    ) -> None:
        super().__init__()
        self.num_heads = num_heads
        self.embed_dim = embed_dim
        self.ffn_embed_dim = ffn_embed_dim
        self.qkv_size = embed_dim // num_heads
        self.layer_norm_self_attention = nn.LayerNorm(embed_dim)
        self.sa_layer = MultiHeadAttention(num_heads, self.qkv_size)
        self.fc1 = nn.Linear(embed_dim, ffn_embed_dim)
        self.fc2 = nn.Linear(ffn_embed_dim, embed_dim)
        self.layer_norm_mlp = nn.LayerNorm(embed_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        res = x
        # Self-attention block
        x = self.layer_norm_self_attention(x)
        x = self.sa_layer(x)
        x = res + x
        # FFN block
        res = x
        x = self.layer_norm_mlp(x)
        x = gelu_exact(self.fc1(x))
        x = self.fc2(x)
        x = res + x
        return x


class RobertaHead(nn.Module):
    """Roberta-style LM head.

    Mirrors ``data/protbfn_abbfn/repo/model.py:11``. Returns per-position
    logits of shape ``(L, num_outputs)``.
    """

    def __init__(self, embed_dim: int, num_outputs: int) -> None:
        super().__init__()
        self.first_layer_norm = nn.LayerNorm(embed_dim)
        self.fc1 = nn.Linear(embed_dim, embed_dim)
        self.second_layer_norm = nn.LayerNorm(embed_dim)
        self.final_fc = nn.Linear(embed_dim, num_outputs)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.first_layer_norm(x)
        x = self.fc1(x)
        x = gelu_exact(x)
        x = self.second_layer_norm(x)
        return self.final_fc(x)


# ---------------------------------------------------------------------------
# Top-level transformer
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProtBFNModelConfig:
    """Immutable configuration for the :class:`ProtBFNTransformer`."""

    embed_dim: int = EMBED_DIM
    ffn_embed_dim: int = FFN_EMBED_DIM
    num_layers: int = NUM_LAYERS
    num_heads: int = NUM_HEADS
    vocab_size: int = PROTBFN_VOCAB_SIZE


class ProtBFNTransformer(nn.Module):
    """Pure-PyTorch implementation of the ProtBFN/AbBFN encoder.

    Forward signature mirrors :func:`get_transformer_fn` from the
    reference implementation. Input ``theta`` of shape ``(L, K)`` is
    passed through :func:`apply_entropy_encoding`, embedded to
    ``(L, embed_dim)``, refined through ``num_layers`` self-attention
    blocks, then projected to per-position logits ``(L, K)``.
    """

    def __init__(self, config: ProtBFNModelConfig | None = None) -> None:
        super().__init__()
        cfg = config or ProtBFNModelConfig()
        self.config = cfg
        self.embed_dim = cfg.embed_dim
        self.ffn_embed_dim = cfg.ffn_embed_dim
        self.num_layers = cfg.num_layers
        self.num_heads = cfg.num_heads
        self.vocab_size = cfg.vocab_size
        self.embed_layer = nn.Linear(ENCODER_INPUT_DIM, self.embed_dim)
        self.emb_layer_norm_before = nn.LayerNorm(self.embed_dim)
        self.layers = nn.ModuleList(
            [
                SelfAttentionBlock(
                    num_heads=self.num_heads,
                    embed_dim=self.embed_dim,
                    ffn_embed_dim=self.ffn_embed_dim,
                )
                for _ in range(self.num_layers)
            ]
        )
        self.lm_head = RobertaHead(self.embed_dim, self.vocab_size)

    def forward(self, theta: torch.Tensor) -> torch.Tensor:
        """Apply the BFN encoder to per-position categorical ``theta``.

        ``theta`` has shape ``(L, K)`` where ``K == self.vocab_size``.
        Returns logits of shape ``(L, K)``.
        """
        x = apply_entropy_encoding(theta)
        x = self.embed_layer(x)
        x = self.emb_layer_norm_before(x)
        for layer in self.layers:
            x = layer(x)
        return self.lm_head(x)

    @classmethod
    def load_from_pytree(
        cls,
        pytree: "ProtBFNParamTree",  # type: ignore[name-defined]
        *,
        config: ProtBFNModelConfig | None = None,
        device: str | torch.device = "cpu",
        dtype: torch.dtype = torch.float32,
    ) -> "ProtBFNTransformer":
        """Construct a :class:`ProtBFNTransformer` and bind it from a :class:`ProtBFNParamTree`.

        The binding is name-driven: every entry in ``pytree`` is
        matched against the canonical Haiku module path
        (``transformer/<sub>/<param>`` -> ``<sub>.<param>``). LayerNorm
        parameters are mapped from the Haiku ``scale/offset`` naming to
        the PyTorch ``weight/bias`` naming.
        """
        from adaptive_reflow.adapters.protbfn_abbfn_jax_loader import (
            ProtBFNParamTree,
        )

        if not isinstance(pytree, ProtBFNParamTree):
            raise TypeError("expected_ProtBFNParamTree")
        cfg = config or ProtBFNModelConfig()
        model = cls(cfg).to(device=device, dtype=dtype)
        # Build a name -> tensor mapping from the pytree. Strip the
        # leading ``transformer`` prefix; the ``/~`` separator is
        # kept as a path component (Haiku's transparent-module marker).
        name_to_arr: dict[str, np.ndarray] = {}
        for path, arr in pytree.items():
            # paths are like "transformer/~/linear/w" or
            # "transformer/attention_layer_0/~/fc1/w".
            parts = path.split("/")
            if parts[0] != "transformer":
                raise ValueError(f"unexpected_root:{path}")
            # Re-join without the leading "transformer".
            attr_path = "/".join(parts[1:])
            name_to_arr[attr_path] = arr
        # Now bind into model. Walk module hierarchy via state_dict
        # naming.
        sd: dict[str, torch.Tensor] = {}
        # Map Haiku param name -> PyTorch state-dict key.
        for haiku_name, arr in name_to_arr.items():
            torch_key = _haiku_to_torch_key(haiku_name)
            sd[torch_key] = torch.as_tensor(arr, dtype=dtype, device=device)
        # Also include the inv_freq buffers (registered via
        # register_buffer, not stored in the pytree).
        for name, module in model.named_modules():
            if isinstance(module, MultiHeadAttention):
                sd[f"{name}.inv_freq"] = module.inv_freq.to(device=device)
        missing, unexpected = model.load_state_dict(sd, strict=False)
        if unexpected:
            raise ValueError(f"unexpected_state_dict_keys:{unexpected}")
        if missing:
            raise ValueError(f"missing_state_dict_keys:{missing}")
        model.eval()
        return model


def _haiku_to_torch_key(haiku_name: str) -> str:
    """Convert a canonical Haiku parameter name to a PyTorch state-dict key.

    Examples::

        "~/linear/w" -> "embed_layer.weight"
        "~/linear/b" -> "embed_layer.bias"
        "~/emb_layer_norm_before/offset" -> "emb_layer_norm_before.bias"
        "~/emb_layer_norm_before/scale" -> "emb_layer_norm_before.weight"
        "attention_layer_0/~/fc1/w" -> "layers.0.fc1.weight"
        "attention_layer_0/~/fc1/b" -> "layers.0.fc1.bias"
        "attention_layer_0/~/self_attention/key/w" -> "layers.0.sa_layer.key.weight"
        "attention_layer_0/~/self_attention/mha_output/w" -> "layers.0.sa_layer.mha_output.weight"
        "attention_layer_0/~/self_attention/query/b" -> "layers.0.sa_layer.query.bias"
        "attention_layer_0/~/final_layer_norm/offset" -> "layers.0.layer_norm_mlp.bias"
        "attention_layer_0/~/self_attention_layer_norm/scale" -> "layers.0.layer_norm_self_attention.weight"
        "roberta_lm_head/~/emb_layer_norm_after/offset" -> "lm_head.first_layer_norm.bias"
        "roberta_lm_head/~/emb_layer_norm_after/scale" -> "lm_head.first_layer_norm.weight"
        "roberta_lm_head/~/lm_head_fc_1/w" -> "lm_head.fc1.weight"
        "roberta_lm_head/~/lm_head_fc_1/b" -> "lm_head.fc1.bias"
        "roberta_lm_head/~/lm_head_layer_norm/offset" -> "lm_head.second_layer_norm.bias"
        "roberta_lm_head/~/lm_final_fc/w" -> "lm_head.final_fc.weight"
    """
    # Handle attention layer first because of the "/~" separator.
    if haiku_name.startswith("attention_layer_"):
        # "attention_layer_0/~/fc1/w" -> "layers.0.fc1.w"
        parts = haiku_name.split("/~/")
        layer_part, sub = parts[0], parts[1] if len(parts) > 1 else ""
        layer_idx = int(layer_part.split("_")[-1])
        # sub is like "fc1/w" or "self_attention/key/w" or
        # "self_attention_layer_norm/offset" or "final_layer_norm/offset"
        return f"layers.{layer_idx}.{_submodule_key(sub)}"
    # Top-level transformer submodules are prefixed with "~/" (the
    # Haiku transparent-module marker). Strip it.
    if haiku_name.startswith("~/"):
        sub = haiku_name[2:]
        if sub == "linear/w":
            return "embed_layer.weight"
        if sub == "linear/b":
            return "embed_layer.bias"
        if sub.startswith("emb_layer_norm_before/"):
            tail = sub[len("emb_layer_norm_before/") :]
            return f"emb_layer_norm_before.{_layernorm_key(tail)}"
        if sub.startswith("roberta_lm_head/~/"):
            inner = sub[len("roberta_lm_head/~/") :]
            return f"lm_head.{_submodule_key(inner)}"
        raise ValueError(f"unrecognized_top_level:{sub}")
    raise ValueError(f"unrecognized_haiku_param:{haiku_name}")


def _submodule_key(sub: str) -> str:
    """Map a Haiku sub-module path to a PyTorch module path."""
    parts = sub.split("/")
    head = parts[0]
    tail = parts[1] if len(parts) > 1 else ""
    if head in ("fc1", "fc2"):
        if tail == "w":
            return f"{head}.weight"
        if tail == "b":
            return f"{head}.bias"
    if head == "self_attention":
        sa = parts[1]  # query, key, value, mha_output
        t = parts[2]
        if t == "w":
            return f"sa_layer.{sa}.weight"
        if t == "b":
            return f"sa_layer.{sa}.bias"
    if head == "self_attention_layer_norm":
        return f"layer_norm_self_attention.{_layernorm_key(tail)}"
    if head == "final_layer_norm":
        return f"layer_norm_mlp.{_layernorm_key(tail)}"
    if head in ("emb_layer_norm_after", "lm_head_layer_norm"):
        # These map into lm_head sub-modules; the caller decides which.
        # For lm_head/emb_layer_norm_after -> lm_head.first_layer_norm
        # For lm_head/lm_head_layer_norm -> lm_head.second_layer_norm
        # The caller already prefixed "lm_head." so we use the
        # canonical PyTorch sub-name.
        if head == "emb_layer_norm_after":
            return f"first_layer_norm.{_layernorm_key(tail)}"
        if head == "lm_head_layer_norm":
            return f"second_layer_norm.{_layernorm_key(tail)}"
    # Map Haiku "lm_head_fc_1" to PyTorch "fc1", "lm_final_fc" to
    # PyTorch "final_fc". The caller has already prefixed "lm_head."
    # so we just return the PyTorch sub-name.
    if head == "lm_head_fc_1":
        if tail == "w":
            return "fc1.weight"
        if tail == "b":
            return "fc1.bias"
    if head == "lm_final_fc":
        if tail == "w":
            return "final_fc.weight"
        if tail == "b":
            return "final_fc.bias"
    raise ValueError(f"unrecognized_submodule:{sub}")


def _layernorm_key(tail: str) -> str:
    """Map a Haiku LayerNorm param name to a PyTorch LayerNorm param name."""
    if tail == "offset":
        return "bias"
    if tail == "scale":
        return "weight"
    raise ValueError(f"unrecognized_layernorm_param:{tail}")


__all__ = [
    "EMBED_DIM",
    "ENCODER_INPUT_DIM",
    "ENTROPY_INPUT_DIM",
    "FFN_EMBED_DIM",
    "FOURIER_DIM",
    "NUM_HEADS",
    "NUM_LAYERS",
    "PROTBFN_VOCAB_SIZE",
    "QKV_SIZE",
    "ProtBFNModelConfig",
    "ProtBFNTransformer",
]
