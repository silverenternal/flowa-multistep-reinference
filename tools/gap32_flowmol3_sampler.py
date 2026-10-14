"""GAP-32 — FlowMol3 R3 x-channel head-to-head sampler.

The R3 cell (``docs/audit/gap02-r3-n1000-resolved.md``) samples real
molecules with the published FlowMol3 CTMC checkpoint. The canonical
sampler is a **monolithic** vendored loop:

* ``FlowMol.sample`` → ``CTMCVectorField.integrate`` → ``CTMCVectorField.step``
  (``data/FlowMol3/repo/flowmol/models/{flowmol,ctmc_vector_field}.py``).

``CTMCVectorField.step`` advances **two** things per macro-step:

1. the **coordinate** channel ``x`` with a first-order Euler step
   ``x_s = x_t + dt * alpha_t'/(1-alpha_t) * (x1_pred - x_t)`` where
   ``x1_pred`` is the GVP's endpoint prediction; and
2. the **categorical** channels ``a`` / ``c`` / ``e`` with the model's
   native CTMC rule (``campbell_step``).

The R6 external solvers (Fast-DLLM / AB-Cache / LeDiFlow) are
**continuous-ODE step rules**: they only make sense on the continuous
coordinate channel. GAP-32 therefore drives the vendored
``CTMCVectorField.step`` **verbatim** (so the GVP forward + the native
CTMC categorical update are byte-identical across arms), then overwrites
``g.ndata['x_t']`` with the arm's own coordinate rule. Nothing under
``data/FlowMol3/`` is modified — this module only *calls* the vendored
objects.

Arms
----

* ``vanilla``  — stock Euler coordinate step (the reference).
* ``fastdllm`` — confidence-aware Euler + midpoint verifier
  (Wu et al. 2025, ``arXiv:2505.22618``). Per-**molecule** confidence
  (the batch axis is the molecule, mirroring the R6 per-record rule).
* ``abcache``  — 2-step Adams-Bashforth velocity-cache reuse
  (Yu et al. 2024, ``arXiv:2504.10540``).
* ``lediflow`` — learned-prior-shifted Euler (Zwick et al. 2025,
  ``arXiv:2505.20723``); the shift is a per-atom Gaussian direction
  seeded once per arm (a *global* 3-vector would be annihilated by the
  upstream's ``remove_com=True``, so the direction is per-atom).
* ``flowa``    — the framework multi-round restart-blend loop on the
  coordinate channel (4 rounds / cosine ramp / β=0.5 / restart from
  round 1 — the same recipe as the MNIST GAP-32 cell). Each round
  rebuilds the graph (fresh categorical prior) and starts the
  coordinate channel from ``(1-β)·prev_endpoint + β·fresh_x0``.

The three external solver rules mirror :mod:`tools.gap32_external_solvers`
verbatim (same macro grid, same confidence rule, same AB-Cache schedule,
same prior-shift formula); the only difference is that the state carries
no leading batch axis — the batch axis is the *molecule*, recovered from
``node_batch_idx``.

Provenance: GAP-32-SOTA-HEADTOHEAD; audit ``docs/audit/gap32-headtohead.md``.
"""
from __future__ import annotations

import hashlib
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Canonical arm order for tables / CSVs (mirrors the MNIST GAP-32 driver).
ARM_ORDER: tuple[str, ...] = ("vanilla", "fastdllm", "abcache", "lediflow", "flowa")
#: The three published external accelerators.
EXTERNAL_ARMS: tuple[str, ...] = ("fastdllm", "abcache", "lediflow")

#: Defaults mirroring :mod:`tools.gap32_external_solvers` verbatim.
DEFAULT_FASTDLLM_CONFIDENCE_THRESHOLD: float = 0.5
DEFAULT_ABCACHE_WARMUP_STEPS: int = 2
DEFAULT_ABCACHE_RECOMPUTE_INTERVAL: int = 6
DEFAULT_ABCACHE_QUEUE_LENGTH: int = 2
DEFAULT_LEDIFLOW_PRIOR_ALPHA: float = 0.5
DEFAULT_LEDIFLOW_PRIOR_SEED: int = 0x4C44
DEFAULT_LEDIFLOW_PRIOR_SCALE: float = 0.4
#: Framework restart-blend recipe (same as the MNIST GAP-32 cell).
DEFAULT_FLOWA_N_ROUNDS: int = 4
DEFAULT_FLOWA_BETA: float = 0.5
DEFAULT_FLOWA_RESTART_FROM_ROUND: int = 1
#: Canonical FlowMol3 R3 integration budget.
DEFAULT_NFE: int = 250


@dataclass(frozen=True)
class SolverConfig:
    """Solver hyper-parameters (defaults mirror the R6 roster verbatim)."""

    nfe: int = DEFAULT_NFE
    fastdllm_threshold: float = DEFAULT_FASTDLLM_CONFIDENCE_THRESHOLD
    abcache_warmup: int = DEFAULT_ABCACHE_WARMUP_STEPS
    abcache_interval: int = DEFAULT_ABCACHE_RECOMPUTE_INTERVAL
    abcache_qlen: int = DEFAULT_ABCACHE_QUEUE_LENGTH
    lediflow_alpha: float = DEFAULT_LEDIFLOW_PRIOR_ALPHA
    lediflow_seed: int = DEFAULT_LEDIFLOW_PRIOR_SEED
    lediflow_scale: float = DEFAULT_LEDIFLOW_PRIOR_SCALE
    flowa_n_rounds: int = DEFAULT_FLOWA_N_ROUNDS
    flowa_beta: float = DEFAULT_FLOWA_BETA
    flowa_restart_from_round: int = DEFAULT_FLOWA_RESTART_FROM_ROUND


# ---------------------------------------------------------------------------
# Vendored imports (lazy; only available inside the flowmol3 venv)
# ---------------------------------------------------------------------------


def _import_upstream() -> dict[str, Any]:
    """Import the vendored FlowMol3 helpers (repo must be on ``sys.path``)."""
    import dgl  # noqa: PLC0415
    from flowmol.analysis.molecule_builder import SampledMolecule  # noqa: PLC0415
    from flowmol.data_processing.utils import (  # noqa: PLC0415
        build_edge_idxs,
        get_batch_idxs,
        get_upper_edge_mask,
    )

    return {
        "dgl": dgl,
        "SampledMolecule": SampledMolecule,
        "build_edge_idxs": build_edge_idxs,
        "get_batch_idxs": get_batch_idxs,
        "get_upper_edge_mask": get_upper_edge_mask,
    }


def _per_molecule_relative_l2(
    a: Any, b: Any, node_batch_idx: Any, n_mol: int
) -> Any:
    """Per-molecule ``||a-b||_2 / (||a||_2 + eps)`` (the R6 per-record rule)."""
    import torch  # noqa: PLC0415

    diff_sq = (a - b).pow(2).sum(dim=-1)
    a_sq = a.pow(2).sum(dim=-1)
    num = torch.zeros(int(n_mol), device=a.device).index_add_(0, node_batch_idx, diff_sq)
    den = torch.zeros(int(n_mol), device=a.device).index_add_(0, node_batch_idx, a_sq)
    return torch.sqrt(num) / (torch.sqrt(den) + 1e-12)


# ---------------------------------------------------------------------------
# The sampler
# ---------------------------------------------------------------------------


class FlowMol3XChannelSampler:
    """Drive the vendored FlowMol3 CTMC sampler with an arm-specific x-rule.

    ``model`` is the loaded upstream ``FlowMol`` (LightningModule) whose
    ``.vector_field`` is a :class:`CTMCVectorField`. Every call runs inside
    ``torch.no_grad()`` and seeds the module RNGs so the upstream CTMC
    categorical draws are reproducible for a fixed ``seed``.
    """

    def __init__(self, model: Any, *, device: str = "cuda:0") -> None:
        self._model = model
        self._device = str(device)
        self._up = _import_upstream()

    # -- graph + prior --------------------------------------------------

    def _build_graph(self, n_atoms_list: list[int]) -> tuple[Any, Any, Any, Any]:
        import torch  # noqa: PLC0415

        dgl = self._up["dgl"]
        build_edge_idxs = self._up["build_edge_idxs"]
        get_batch_idxs = self._up["get_batch_idxs"]
        get_upper_edge_mask = self._up["get_upper_edge_mask"]

        edge_idxs_dict = {
            int(n): build_edge_idxs(int(n)) for n in sorted(set(int(x) for x in n_atoms_list))
        }
        graphs = []
        for n_i in n_atoms_list:
            ei = edge_idxs_dict[int(n_i)]
            graphs.append(
                dgl.graph((ei[0], ei[1]), num_nodes=int(n_i), device=self._device)
            )
        g = dgl.batch(graphs)
        upper_edge_mask = get_upper_edge_mask(g)
        node_batch_idx, edge_batch_idx = get_batch_idxs(g)
        # Native upstream prior (``prior=None`` path of ``FlowMol.sample``):
        # the checkpoint's own trained prior config, sampled per node so
        # every molecule gets an independent draw.
        g = self._model.sample_prior(g, node_batch_idx, upper_edge_mask)
        del torch
        return g, node_batch_idx, edge_batch_idx, upper_edge_mask

    # -- model forward --------------------------------------------------

    def _velocity(
        self,
        g: Any,
        node_batch_idx: Any,
        upper_edge_mask: Any,
        x: Any,
        t_val: float,
    ) -> tuple[Any, Any]:
        """Return ``(v_x, dst_dict)`` for the coordinate channel at ``(x, t)``.

        ``v_x = alpha_t'/(1-alpha_t) * (x1_pred - x)`` is the vendored
        ``EndpointVectorField.vector_field``; ``dst_dict`` is the raw GVP
        endpoint prediction (needed by the native CTMC categorical step).
        """
        import torch  # noqa: PLC0415

        vf = self._model.vector_field
        g.ndata["x_t"] = x
        dst_dict = vf(
            g,
            t=torch.full((g.batch_size,), float(t_val), device=g.device),
            node_batch_idx=node_batch_idx,
            upper_edge_mask=upper_edge_mask,
            apply_softmax=True,
            remove_com=True,
            prev_dst_dict=None,
        )
        t_tensor = torch.tensor([float(t_val)], device=g.device)
        alpha_t = vf.interpolant_scheduler.alpha_t(t_tensor)[0]
        alpha_t_prime = vf.interpolant_scheduler.alpha_t_prime(t_tensor)[0]
        v_x = vf.vector_field(x, dst_dict["x"], alpha_t[0], alpha_t_prime[0])
        return v_x, dst_dict

    # -- one integration (single pass) ----------------------------------

    def _integrate(
        self,
        g: Any,
        node_batch_idx: Any,
        edge_batch_idx: Any,
        upper_edge_mask: Any,
        *,
        arm: str,
        nfe: int,
        cfg: SolverConfig,
        x_start: Any = None,
        reinit_channels: bool = True,
        t_grid: Any = None,
        restart_steps: dict[int, float] | None = None,
    ) -> tuple[Any, dict[str, Any]]:
        import torch  # noqa: PLC0415

        vf = self._model.vector_field
        n_mol = int(g.batch_size)

        t = (
            torch.linspace(0.0, 1.0, int(nfe), device=g.device)
            if t_grid is None
            else t_grid
        )
        alpha_t = vf.interpolant_scheduler.alpha_t(t)
        alpha_t_prime = vf.interpolant_scheduler.alpha_t_prime(t)

        if reinit_channels:
            for feat in vf.canonical_feat_order:
                src = g.edata if feat == "e" else g.ndata
                src[f"{feat}_t"] = src[f"{feat}_0"]
        if x_start is not None:
            g.ndata["x_t"] = x_start

        # --- arm state ---
        cache: deque = deque(maxlen=int(cfg.abcache_qlen))
        skip_next = torch.zeros(n_mol, dtype=torch.bool, device=g.device)
        n_verifier = 0
        n_skip = 0
        n_recompute = 0
        n_cache_reuse = 0
        n_restarts = 0
        dst_dict = None

        for s_idx in range(1, int(t.shape[0])):
            # Coordinate-channel restart (the framework arm): re-blend the
            # coordinate state with the prior at the round boundary, leaving
            # the native CTMC categorical trajectory untouched.
            if restart_steps and s_idx in restart_steps:
                beta = float(restart_steps[s_idx])
                g.ndata["x_t"] = (1.0 - beta) * g.ndata["x_t"] + beta * g.ndata["x_0"]
                n_restarts += 1
            s_i = t[s_idx]
            t_i = t[s_idx - 1]
            alpha_t_i = alpha_t[s_idx - 1]
            alpha_s_i = alpha_t[s_idx]
            alpha_t_prime_i = alpha_t_prime[s_idx - 1]
            last_step = s_idx == int(t.shape[0]) - 1
            dt = float(s_i - t_i)
            x_prev = g.ndata["x_t"].clone()

            # Vendored step: GVP forward at (x_prev, t_i) + native CTMC
            # categorical update. The coordinate Euler result it computes is
            # discarded and replaced by the arm rule below. ``cat_temp_func``
            # / ``forward_weight_func`` are resolved here exactly as the
            # vendored ``CTMCVectorField.integrate`` does (the vendored
            # ``step`` does NOT fall back to ``self`` defaults).
            g, dst_dict = vf.step(
                g,
                s_i,
                t_i,
                alpha_t_i,
                alpha_s_i,
                alpha_t_prime_i,
                node_batch_idx,
                edge_batch_idx,
                upper_edge_mask,
                cat_temp_func=vf.cat_temp_func,
                forward_weight_func=vf.forward_weight_func,
                prev_dst_dict=dst_dict,
                dfm_type="campbell",
                stochasticity=None,
                high_confidence_threshold=None,
                last_step=bool(last_step),
            )

            x_1 = dst_dict["x"]
            v_x = vf.vector_field(x_prev, x_1, alpha_t_i[0], alpha_t_prime_i[0])

            if arm == "fastdllm":
                x_s, n_verifier, n_skip, skip_next = self._fastdllm_step(
                    g, node_batch_idx, upper_edge_mask, x_prev, v_x, dt, float(t_i),
                    skip_next, n_verifier, n_skip, cfg,
                )
            elif arm == "abcache":
                x_s, n_recompute, n_cache_reuse = self._abcache_step(
                    x_prev, v_x, dt, int(s_idx), cache, n_recompute, n_cache_reuse, cfg,
                )
            else:  # vanilla / lediflow / flowa
                x_s = x_prev + dt * v_x

            g.ndata["x_t"] = x_s

        for feat in vf.canonical_feat_order:
            src = g.edata if feat == "e" else g.ndata
            src[f"{feat}_1"] = src[f"{feat}_t"]

        stats: dict[str, Any] = {
            "n_macro_steps": int(nfe) - 1,
            "effective_nfe": int(nfe) - 1,
            "arm": arm,
        }
        if restart_steps:
            stats["n_coordinate_restarts"] = int(n_restarts)
        if arm == "fastdllm":
            stats.update(
                {
                    "n_verifier_steps": int(n_verifier),
                    "n_skip_steps": int(n_skip),
                    "threshold": float(cfg.fastdllm_threshold),
                }
            )
        elif arm == "abcache":
            stats.update(
                {
                    "n_recompute_steps": int(n_recompute),
                    "n_cache_reuse_steps": int(n_cache_reuse),
                    "effective_nfe": int(n_recompute),
                }
            )
        return g, stats

    # -- arm step rules -------------------------------------------------

    def _fastdllm_step(
        self,
        g: Any,
        node_batch_idx: Any,
        upper_edge_mask: Any,
        x_prev: Any,
        v_x: Any,
        dt: float,
        t_i: float,
        skip_next: Any,
        n_verifier: int,
        n_skip: int,
        cfg: SolverConfig,
    ) -> tuple[Any, int, int, Any]:
        import torch  # noqa: PLC0415

        x_pred = x_prev + dt * v_x
        do_verifier = ~skip_next
        x_mid = x_prev + 0.5 * dt * v_x
        v_half, _ = self._velocity(
            g, node_batch_idx, upper_edge_mask, x_mid, t_i + 0.5 * dt
        )
        x_verify = x_mid + 0.5 * dt * v_half
        rel = _per_molecule_relative_l2(x_pred, x_verify, node_batch_idx, int(g.batch_size))
        confidence = torch.clamp(1.0 - rel, min=0.0)
        mask = do_verifier[node_batch_idx].unsqueeze(-1)
        x_s = torch.where(mask, x_verify, x_pred)
        n_verifier += int(do_verifier.sum())
        n_skip += int((do_verifier & (confidence > float(cfg.fastdllm_threshold))).sum())
        skip_next = do_verifier & (confidence > float(cfg.fastdllm_threshold))
        return x_s, n_verifier, n_skip, skip_next

    def _abcache_step(
        self,
        x_prev: Any,
        v_x: Any,
        dt: float,
        step_index: int,
        cache: deque,
        n_recompute: int,
        n_cache_reuse: int,
        cfg: SolverConfig,
    ) -> tuple[Any, int, int]:
        warmup = int(cfg.abcache_warmup)
        interval = int(cfg.abcache_interval)
        is_warmup = step_index <= warmup
        is_periodic = (not is_warmup) and ((step_index - warmup - 1) % interval == 0)
        if is_warmup or is_periodic:
            cache.appendleft(v_x.detach().clone())
            return x_prev + dt * v_x, n_recompute + 1, n_cache_reuse
        assert len(cache) >= 2, f"abcache_needs_2_entries:got {len(cache)}"
        ab_velocity = 2.0 * cache[0] - cache[1]
        return x_prev + dt * ab_velocity, n_recompute, n_cache_reuse + 1

    def _apply_lediflow_shift(self, g: Any, cfg: SolverConfig) -> None:
        """Per-atom deterministic prior shift (the LeDiFlow rule)."""
        import torch  # noqa: PLC0415

        x0 = g.ndata["x_0"]
        n_nodes = int(x0.shape[0])
        gen = torch.Generator(device="cpu").manual_seed(int(cfg.lediflow_seed))
        direction = torch.randn(
            (n_nodes, 3), generator=gen, dtype=torch.float32
        ).to(x0.device)
        direction = direction / direction.norm().clamp_min(1e-30) * float(cfg.lediflow_scale)
        x0_shifted = x0 + direction
        g.ndata["x_0"] = (1.0 - float(cfg.lediflow_alpha)) * x0 + float(
            cfg.lediflow_alpha
        ) * x0_shifted

    # -- public API -----------------------------------------------------

    def sample_arm(
        self,
        *,
        arm: str,
        n_atoms_list: list[int],
        seed: int,
        cfg: SolverConfig,
    ) -> dict[str, Any]:
        """Sample one arm's molecules; returns ``{"molecules", "stats", ...}``."""
        import torch  # noqa: PLC0415

        if arm not in ARM_ORDER:
            raise ValueError(f"unknown_arm:{arm}")
        self._seed_rng(int(seed))
        with torch.no_grad():
            if arm == "flowa":
                g, upper_edge_mask, stats = self._run_flowa(n_atoms_list, cfg)
            else:
                g, nbi, ebi, uem = self._build_graph(n_atoms_list)
                if arm == "lediflow":
                    self._apply_lediflow_shift(g, cfg)
                    x_start = g.ndata["x_0"].detach().clone()
                else:
                    x_start = None
                g, stats = self._integrate(
                    g, nbi, ebi, uem, arm=arm, nfe=int(cfg.nfe), cfg=cfg, x_start=x_start,
                )
                upper_edge_mask = uem
        molecules = self._decode(g, upper_edge_mask)
        return {"molecules": molecules, "stats": stats}

    def _run_flowa(
        self, n_atoms_list: list[int], cfg: SolverConfig
    ) -> tuple[Any, Any, dict[str, Any]]:
        """Framework arm — coordinate-channel restart on a shared CTMC path.

        A single vendored integration runs the full ``--nfe`` budget (so the
        native CTMC categorical channels unmask continuously across the whole
        trajectory — a per-round re-mask would leave ``Se`` mask tokens when a
        round is short). At each of the ``n_rounds - 1`` interior round
        boundaries the **coordinate** channel is re-blended with the prior,
        ``x_t <- (1-beta) * x_t + beta * x_0`` — the framework restart, applied
        to the only continuous channel. Total coordinate NFE is therefore
        exactly matched to the single-pass arms.
        """
        import torch  # noqa: PLC0415

        g, nbi, ebi, uem = self._build_graph(n_atoms_list)
        n_rounds = int(cfg.flowa_n_rounds)
        total_steps = max(1, int(cfg.nfe) - 1)
        restart_steps: dict[int, float] = {}
        for r in range(int(cfg.flowa_restart_from_round), n_rounds):
            idx = int(round(float(r) * float(total_steps) / float(n_rounds)))
            if 1 <= idx <= total_steps:
                restart_steps[idx] = float(cfg.flowa_beta)
        t_grid = torch.linspace(0.0, 1.0, int(cfg.nfe), device=g.device)
        g, base_stats = self._integrate(
            g,
            nbi,
            ebi,
            uem,
            arm="vanilla",
            nfe=int(cfg.nfe),
            cfg=cfg,
            t_grid=t_grid,
            restart_steps=restart_steps,
        )
        stats = {
            "arm": "flowa",
            "n_rounds": n_rounds,
            "restart_from_round": int(cfg.flowa_restart_from_round),
            "beta": float(cfg.flowa_beta),
            "restart_step_indices": sorted(int(k) for k in restart_steps),
            "total_nfe_per_sample": int(cfg.nfe) - 1,
            "n_coordinate_restarts": int(base_stats.get("n_coordinate_restarts", 0)),
        }
        return g, uem, stats

    # -- decode + seeding ----------------------------------------------

    def _decode(self, g: Any, upper_edge_mask: Any) -> list[Any]:
        dgl = self._up["dgl"]
        SampledMolecule = self._up["SampledMolecule"]
        model = self._model
        g.edata["ue_mask"] = upper_edge_mask
        g_cpu = g.to("cpu")
        molecules: list[Any] = []
        for g_i in dgl.unbatch(g_cpu):
            molecules.append(
                SampledMolecule(
                    g_i,
                    model.atom_type_map,
                    ctmc_mol=True,
                    fake_atoms=bool(getattr(model, "fake_atoms", False)),
                    build_xt_traj=False,
                    build_ep_traj=False,
                    exclude_charges=bool(getattr(model, "exclude_charges", False)),
                    explicit_aromaticity=bool(
                        getattr(model, "explicit_aromaticity", False)
                    ),
                )
            )
        return molecules

    def _seed_rng(self, seed: int) -> None:
        import random  # noqa: PLC0415

        import torch  # noqa: PLC0415

        random.seed(int(seed))
        np.random.seed(int(seed) % (2**32 - 1))
        torch.manual_seed(int(seed))
        if str(self._device).startswith("cuda"):
            torch.cuda.manual_seed_all(int(seed))


def config_fingerprint(cfg: SolverConfig) -> str:
    """Stable hash of the solver config (for METADATA provenance)."""
    blob = repr(
        (
            "gap32_flowmol3_solver",
            int(cfg.nfe),
            float(cfg.fastdllm_threshold),
            int(cfg.abcache_warmup),
            int(cfg.abcache_interval),
            int(cfg.abcache_qlen),
            float(cfg.lediflow_alpha),
            int(cfg.lediflow_seed),
            float(cfg.lediflow_scale),
            int(cfg.flowa_n_rounds),
            float(cfg.flowa_beta),
            int(cfg.flowa_restart_from_round),
        )
    ).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


__all__: list[str] = [
    "ARM_ORDER",
    "DEFAULT_ABCACHE_QUEUE_LENGTH",
    "DEFAULT_ABCACHE_RECOMPUTE_INTERVAL",
    "DEFAULT_ABCACHE_WARMUP_STEPS",
    "DEFAULT_FASTDLLM_CONFIDENCE_THRESHOLD",
    "DEFAULT_FLOWA_BETA",
    "DEFAULT_FLOWA_N_ROUNDS",
    "DEFAULT_FLOWA_RESTART_FROM_ROUND",
    "DEFAULT_LEDIFLOW_PRIOR_ALPHA",
    "DEFAULT_LEDIFLOW_PRIOR_SCALE",
    "DEFAULT_LEDIFLOW_PRIOR_SEED",
    "DEFAULT_NFE",
    "EXTERNAL_ARMS",
    "FlowMol3XChannelSampler",
    "SolverConfig",
    "config_fingerprint",
]
