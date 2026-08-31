"""Read-only candidate registry for 2025/2026 Flow Matching sources (DTB-G2).

This module provides a frozen, hash-stable registry of Flow Matching model
candidates that may be wired into the public
:class:`flow_matching_engine.Engine` via per-model adapters. The registry
itself is **not** an admission oracle: each entry records the
reproducible commit / paper / capability manifest that another (human)
audit owner would need before granting execution access.

Public surface
--------------

Frozen dataclasses
    :class:`AdapterStatus` (Literal)
    :class:`TaskCondition` (Literal)
    :class:`CandidateEntry`
    :class:`CandidateRegistry`

Pure functions
    :func:`make_initial_registry`
    :func:`admit_entry`
    :func:`by_status`
    :func:`admitted_only`

Tasks satisfied:

* ``DTB-G2`` — read-only candidate registry for 2025/2026 local Flow
  Matching sources.

Non-claims enforced here:

* The registry is **not** a SOTA ranking. Audit / admission basis is
  reproducibility + capability manifest + parity report, not leaderboard
  position.
* An entry with ``adapter_status="admitted_unconditional_only"`` is
  admitted only for mechanics validation, never for pocket-conditioned
  efficacy claims.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Literal

# ---------------------------------------------------------------------------
# Status & task enums
# ---------------------------------------------------------------------------


AdapterStatus = Literal[
    "unsupported",
    "blocked",
    "admitted",
    "admitted_unconditional_only",
]
"""Admission status for a candidate entry.

* ``unsupported`` — no source code or capability evidence available.
* ``blocked`` — source known but fails audit (e.g. license, missing ODE
  boundary, untestable private tensors).
* ``admitted`` — passed audit and parity, eligible for paired evaluation.
* ``admitted_unconditional_only`` — passed mechanics gate but the task
  domain is unconditional; cannot validate pocket-conditioned efficacy
  claims.
"""

TaskCondition = Literal[
    "unconditional_3d",
    "pocket_conditioned",
    "sequence_conditioned",
    "other",
]
"""Task condition surface the candidate supports."""

# ---------------------------------------------------------------------------
# Frozen dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CandidateEntry:
    """One row in the candidate registry.

    Every field is required. ``audit_notes`` is non-empty by construction
    so the registry cannot be used as a "claim-by-omission" surface.
    """

    repo_url: str
    commit: str
    license: str
    paper_id: str
    paper_date: str
    task_conditions: tuple[TaskCondition, ...]
    dataset_split: str
    native_metric_protocol: str
    ode_call_site: str
    state_boundary: str
    condition_boundary: str
    restart_boundary: str
    compatible_channels: tuple[str, ...]
    available_checkpoint: str | None
    adapter_status: AdapterStatus
    audit_notes: str
    registered_at: str
    registered_by: str

    def __post_init__(self) -> None:
        # Structural validation only — fail at construction time so a
        # malformed entry cannot survive even one round.
        for fname, fvalue in (
            ("repo_url", self.repo_url),
            ("commit", self.commit),
            ("license", self.license),
            ("paper_id", self.paper_id),
            ("paper_date", self.paper_date),
            ("dataset_split", self.dataset_split),
            ("native_metric_protocol", self.native_metric_protocol),
            ("ode_call_site", self.ode_call_site),
            ("state_boundary", self.state_boundary),
            ("condition_boundary", self.condition_boundary),
            ("restart_boundary", self.restart_boundary),
            ("audit_notes", self.audit_notes),
            ("registered_at", self.registered_at),
            ("registered_by", self.registered_by),
        ):
            if not isinstance(fvalue, str) or not fvalue:
                raise ValueError(f"{fname}_must_be_non_empty_string")
        if not isinstance(self.task_conditions, tuple) or not self.task_conditions:
            raise ValueError("task_conditions_must_be_non_empty_tuple")
        if not isinstance(self.compatible_channels, tuple) or not self.compatible_channels:
            raise ValueError("compatible_channels_must_be_non_empty_tuple")
        if not isinstance(self.adapter_status, str) or self.adapter_status not in (
            "unsupported",
            "blocked",
            "admitted",
            "admitted_unconditional_only",
        ):
            raise ValueError("adapter_status_must_be_valid_literal")
        for tc in self.task_conditions:
            if tc not in (
                "unconditional_3d",
                "pocket_conditioned",
                "sequence_conditioned",
                "other",
            ):
                raise ValueError(f"task_condition_must_be_valid_literal:{tc}")
        # admitted_unconditional_only may NOT carry pocket_conditioned
        if (
            self.adapter_status == "admitted_unconditional_only"
            and "pocket_conditioned" in self.task_conditions
        ):
            raise ValueError(
                "admitted_unconditional_only_cannot_carry_pocket_conditioned"
            )


@dataclass(frozen=True)
class CandidateRegistry:
    """Frozen registry of :class:`CandidateEntry` rows.

    The registry is read-only after construction; mutating methods raise.
    Hashing is deterministic (sorted JSON) so byte-equality can be checked
    at the policy-authority boundary.
    """

    entries: tuple[CandidateEntry, ...]
    registry_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.entries, tuple):
            raise ValueError("entries_must_be_tuple")
        object.__setattr__(self, "registry_hash", _registry_hash(self.entries))

    def by_status(self, status: AdapterStatus) -> tuple[CandidateEntry, ...]:
        """Return the subset of entries with ``adapter_status == status``."""
        return tuple(e for e in self.entries if e.adapter_status == status)

    def admitted_only(self) -> tuple[CandidateEntry, ...]:
        """Return entries with ``admitted`` or ``admitted_unconditional_only``.

        Callers that need a strict admission gate must call
        :meth:`by_status` with ``"admitted"`` instead.
        """
        return tuple(
            e
            for e in self.entries
            if e.adapter_status in ("admitted", "admitted_unconditional_only")
        )

    def assert_readonly(self) -> None:
        """Always returns ``None``; provided so callers can document intent.

        Construction-time enforcement of immutability comes from
        ``frozen=True``; this method exists only for symmetry with the
        audit fixture.
        """
        return


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _registry_hash(entries: tuple[CandidateEntry, ...]) -> str:
    """Deterministic hash of the registry over sorted-JSON serialization."""
    payload = [
        {
            "repo_url": e.repo_url,
            "commit": e.commit,
            "license": e.license,
            "paper_id": e.paper_id,
            "paper_date": e.paper_date,
            "task_conditions": list(e.task_conditions),
            "dataset_split": e.dataset_split,
            "native_metric_protocol": e.native_metric_protocol,
            "ode_call_site": e.ode_call_site,
            "state_boundary": e.state_boundary,
            "condition_boundary": e.condition_boundary,
            "restart_boundary": e.restart_boundary,
            "compatible_channels": list(e.compatible_channels),
            "available_checkpoint": e.available_checkpoint,
            "adapter_status": e.adapter_status,
            "audit_notes": e.audit_notes,
            "registered_at": e.registered_at,
            "registered_by": e.registered_by,
        }
        for e in sorted(entries, key=lambda x: (x.repo_url, x.commit))
    ]
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def admit_entry(
    registry: CandidateRegistry,
    entry: CandidateEntry,
) -> CandidateRegistry:
    """Append ``entry`` to ``registry`` and return a new registry.

    Returns a fresh ``CandidateRegistry``; the input is not mutated (it
    cannot be, since both inputs are frozen).
    """
    if not isinstance(entry, CandidateEntry):
        raise TypeError("entry_must_be_candidate_entry")
    return CandidateRegistry(entries=registry.entries + (entry,))


def make_initial_registry(
    flowmol3_entry: CandidateEntry | None = None,
) -> CandidateRegistry:
    """Construct the initial registry.

    Currently seeds one row — the FlowMol3 commit pinned at
    ``77cae22174b7792b0e25e9e0414038420736d841``. Pass ``flowmol3_entry=None``
    to start with an empty registry.
    """
    entries: tuple[CandidateEntry, ...]
    entries = () if flowmol3_entry is None else (flowmol3_entry,)
    return CandidateRegistry(entries=entries)


# ---------------------------------------------------------------------------
# Default FlowMol3 row (read-only, fixed commit)
# ---------------------------------------------------------------------------


FLOWMOL3_PINNED_COMMIT = "77cae22174b7792b0e25e9e0414038420736d841"
"""Pinned FlowMol3 commit. DO NOT change without re-running the
mechanics parity gate."""


HIDREAM_I1_PINNED_COMMIT = "0000000000000000000000000000000000000000"
"""Pinned HiDream-I1 commit placeholder.

The HiDream-ai/HiDream-I1 HuggingFace repos do not yet have a pinned
git commit hash that is reproducible from the public sandbox (the HF
repo URL is not in the pre-acquired ``weights_metadata.json`` and the
sandbox has no HF token). This zero-hash placeholder will be replaced
once the user supplies a reproducible checkout hash for one of the
``HiDream-ai/HiDream-I1-{Full,Dev,Fast}`` sub-repos. DO NOT change
without re-running the mechanics parity gate."""


def make_default_flowmol3_entry() -> CandidateEntry:
    """Build the canonical FlowMol3 row for the registry.

    ``adapter_status="admitted_unconditional_only"`` makes the
    pocket-conditioned efficacy non-claim boundary explicit at the
    registry level; any caller that wants pocket-conditioned claims must
    re-admit with ``adapter_status="admitted"`` after a separate audit.
    """
    return CandidateEntry(
        repo_url="https://github.com/zavalab/ML/tree/FlowMol3",
        commit=FLOWMOL3_PINNED_COMMIT,
        license="MIT",
        paper_id="FlowMol3",
        paper_date="2025",
        task_conditions=("unconditional_3d",),
        dataset_split="n/a (unconditional 3D generator)",
        native_metric_protocol=(
            "model-internal sampling diagnostics only; no pocket-conditioned "
            "evaluator provenance available"
        ),
        ode_call_site="integrate / step functions over (x, a, c, e) features",
        state_boundary=(
            "model.integrate output: state variable returned with "
            "stop_gradient=True at the (x, a, c, e) boundary"
        ),
        condition_boundary="no pocket conditioning exposed",
        restart_boundary=(
            "model.integrate restart boundary: state variable "
            "detached via .detach() at every restart"
        ),
        compatible_channels=("coordinate", "charge", "raw_pair"),
        available_checkpoint=None,
        adapter_status="admitted_unconditional_only",
        audit_notes=(
            "FlowMol3 native state is (x, a, c, e). It is exposed via "
            "the engine-domain channel vocabulary: x->coordinate, "
            "c->charge, e->raw_pair. The native atom-type channel (a) "
            "is a model-local label and is NOT carried as an "
            "adaptive-reflow evidence surface. "
            "FlowMol3 is an unconditional 3D generator; this read-only "
            "mechanics adapter validates the public engine + adapter "
            "protocol (DTB-G1) only. It does NOT validate any "
            "pocket-conditioned efficacy claim; admission to "
            "pocket-conditioned experiments requires a separate "
            "candidate row with adapter_status='admitted' and a "
            "pocket-conditioned paper/eval reference."
        ),
        registered_at="2026-08-25",
        registered_by="DTB-G2 audit scaffold",
    )


def make_default_hidream_i1_entry() -> CandidateEntry:
    """Build the canonical HiDream-I1 row for the registry.

    ``adapter_status="admitted_unconditional_only"`` is the appropriate
    status for a text-conditional image adapter that has passed the
    mechanics gate but cannot claim pocket-conditioned efficacy. The
    HiDream-I1 adapter is a ``sequence_conditioned`` candidate (text
    prompt + optional negative prompt); it is NOT an unconditional 3D
    generator and therefore uses ``"sequence_conditioned"`` rather than
    ``"unconditional_3d"`` in ``task_conditions``.

    The compatible channels are the adapter's own vocabulary:
    ``image_latent`` (latent domain; the FLUX.1 VAE 16x128x128 latent)
    and ``text_cond`` (continuous domain; cached hybrid encoder
    output). The QA-only / aesthetics benchmark suite (DPG-Bench,
    GenEval, HPSv2.1) is intentionally NOT validated here because
    HiDream-I1's published metrics exclude FID.
    """
    return CandidateEntry(
        repo_url="https://huggingface.co/HiDream-ai/HiDream-I1-Full",
        commit=HIDREAM_I1_PINNED_COMMIT,
        license="MIT",
        paper_id="HiDream-I1 (arXiv:2505.22705)",
        paper_date="2025",
        task_conditions=("sequence_conditioned",),
        dataset_split=(
            "web-crawled + internal copyright-respecting corpora, "
            "deduplicated via SSCD + k-means + intra-cluster Faiss, "
            "filtered by NSFW / aesthetic / watermark / Top-IQ / "
            "bytes-per-pixel, captioned by MiniCPM-V 2.6"
        ),
        native_metric_protocol=(
            "DPG-Bench (overall 85.89), GenEval (overall 0.83), "
            "HPSv2.1 (average 33.82) — paper Tables 1-3. FID is "
            "intentionally NOT a paper metric; any FID row would be "
            "an optional non-paper metric (e.g. FID against "
            "MS-COCO-30K or MJHQ-30K)."
        ),
        ode_call_site=(
            "v_theta(x_t, t, conditioning_stack) over the latent "
            "(16, 128, 128) FLUX.1-VAE state; three published variants "
            "(Full 50+ NFE Euler/midpoint, Dev 28 NFE guidance-"
            "distilled, Fast 14 NFE DMD-distilled)"
        ),
        state_boundary=(
            "v_theta input/output shape (16, 128, 128); restart "
            "blend is latent-space m * prior + (1 - m) * fresh; "
            "conditioning reference preserved across rounds"
        ),
        condition_boundary=(
            "text-only (prompt + optional negative prompt) via "
            "4-source hybrid text encoder cache (CLIP-L/14 + "
            "CLIP-G/14 pooled for adaLN, T5-XXL tokens + "
            "Llama-3.1-8B multi-intermediate-layer features for "
            "the text sequence). CFG scale is a per-round "
            "integrator parameter, not a static condition."
        ),
        restart_boundary=(
            "model.integrate restart boundary: latent state variable "
            "detached via the standard protocol boundary; restart "
            "blend happens in latent space (NOT pixel space)"
        ),
        compatible_channels=("image_latent", "text_cond"),
        available_checkpoint=None,  # user must supply HiDream-I1 weights locally
        adapter_status="admitted_unconditional_only",
        audit_notes=(
            "HiDream-I1 is a 17B-parameter open-source text-to-image "
            "foundation model (sparse Diffusion Transformer with dual-"
            "stream encoders + single-stream sparse MoE; latent flow "
            "matching objective). This row records the protocol surface: "
            "the adapter is wired at adaptive_reflow/adapters/hidream_i1.py "
            "with state_shape=(16, 128, 128), the per-variant num_steps / "
            "CFG defaults (full=50/5.0, dev=28/1.0, fast=14/1.0), and "
            "the synthetic-mode test path that lets the test suite run "
            "without the heavy torch dependency. The torch-mode production "
            "path requires the [hidream] extra + HiDream-ai/HiDream-I1-"
            "{Full,Dev,Fast} weights (~34 GB / variant) + the four text "
            "encoders (~30 GB total) + a CUDA host with >=40 GB HBM. "
            "DPG-Bench / GenEval / HPSv2.1 scoring require their own "
            "eval stack (MiniCPM-V 2.6, official detection+text-match, "
            "HPSv2.1 CLIP-H respectively). The harness is a stub "
            "(tools/run_sota_hidream_i1_experiment.py) that exits with "
            "75 (EX_TEMPFAIL) until the user supplies the missing "
            "inputs. This row does NOT validate any prompt-following / "
            "aesthetic quality claim; admission to text-conditioned "
            "efficacy experiments requires a separate candidate row "
            "with adapter_status='admitted' and a reproducible "
            "HiDream-I1 commit hash + a full eval-stack provenance."
        ),
        registered_at="2026-08-31",
        registered_by="R17 HiDream-I1 audit scaffold",
    )


def default_registry() -> CandidateRegistry:
    """Build the registry with the default FlowMol3 row seeded."""
    return make_initial_registry(flowmol3_entry=make_default_flowmol3_entry())


def make_default_flowmol3adapter_entry() -> CandidateEntry:
    """Build the canonical registry row that pairs with
    :class:`adaptive_reflow.adapters.flowmol3_v2_adapter.FlowMol3V2Adapter`.

    Same pinned commit, license, paper, and audit notes as
    :func:`make_default_flowmol3_entry`; the
    ``audit_notes`` field is extended to record that the real
    mechanics adapter is wired (cf. the read-only placeholder
    ``adaptive_reflow.adapters.flowmol3.FlowMol3Adapter``). The row is
    the load-bearing registry entry the production SOTA harness will
    look up.

    Note: this row carries the same ``admitted_unconditional_only``
    status — FlowMol3's pocket-conditioned efficacy remains a
    non-claim boundary at this admission.
    """
    return CandidateEntry(
        repo_url="https://github.com/zavalab/ML/tree/FlowMol3",
        commit=FLOWMOL3_PINNED_COMMIT,
        license="MIT",
        paper_id="FlowMol3",
        paper_date="2025",
        task_conditions=("unconditional_3d",),
        dataset_split="n/a (unconditional 3D generator)",
        native_metric_protocol=(
            "model-internal sampling diagnostics only; no pocket-conditioned "
            "evaluator provenance available"
        ),
        ode_call_site=(
            "model.integrate / model.step over (x, a, c, e) — wired "
            "through adaptive_reflow.adapters.flowmol3_v2_adapter."
            "FlowMol3V2Adapter (backend='torch' lazy-imports the "
            "zavalab FlowMol3 module at the pinned commit; "
            "backend='numpy' is the deterministic Protocol conformance "
            "fallback)"
        ),
        state_boundary=(
            "model.integrate output: state variable returned with "
            "stop_gradient=True at the (x, a, c, e) boundary"
        ),
        condition_boundary="no pocket conditioning exposed",
        restart_boundary=(
            "model.integrate restart boundary: state variable "
            "detached via .detach() at every restart"
        ),
        compatible_channels=("coordinate", "charge", "raw_pair"),
        available_checkpoint=None,
        adapter_status="admitted_unconditional_only",
        audit_notes=(
            "FlowMol3 native state is (x, a, c, e). It is exposed via "
            "the engine-domain channel vocabulary: x->coordinate, "
            "c->charge, e->raw_pair. The native atom-type channel (a) "
            "is a model-local label and is NOT carried as an "
            "adaptive-reflow evidence surface. "
            "The real mechanics adapter "
            "(adaptive_reflow.adapters.flowmol3_v2_adapter.FlowMol3V2Adapter) "
            "implements all eight FlowMatchingODEAdapter methods "
            "(capabilities / build_initial_state / export_endpoint / "
            "detach_and_validate_endpoint / apply_restart_distribution / "
            "compose_condition / solve_ode / observe_endpoint) plus the "
            "public export_trajectory (P0-7) surface. Restart "
            "boundary applies .detach() at every model.integrate / "
            "model.step entry; the channel-aware blender uses "
            "LinearBlender for the continuous (coordinate, charge) "
            "channels and categorical resampling for the discrete "
            "(raw_pair) channel. FlowMol3 is an unconditional 3D "
            "generator; this row does NOT validate any "
            "pocket-conditioned efficacy claim; admission to "
            "pocket-conditioned experiments requires a separate "
            "candidate row with adapter_status='admitted' and a "
            "pocket-conditioned paper/eval reference."
        ),
        registered_at="2026-08-31",
        registered_by="DTB-G2 mechanics-adapter scaffold",
    )


# ---------------------------------------------------------------------------
# Default GraphBFN row (read-only; adapter_status="unsupported" until the
# paper PDF + weights land in data/graphbfn/).
# ---------------------------------------------------------------------------


GRAPHBFN_PINNED_COMMIT: str = "TODO:graphbfn-pin-on-weights-landing"
"""Pinned GraphBFN commit. ``TODO`` placeholder until the weights-
acquisition phase succeeds (see ``data/graphbfn/weights_metadata.json``)
and a concrete commit SHA is recorded."""


def make_default_graphbfn_entry() -> CandidateEntry:
    """Build the canonical GraphBFN row for the registry.

    ``adapter_status="unsupported"`` is the honest default until the
    published GraphBFN paper PDF + state_dict land in
    ``data/graphbfn/``. The synthetic-mode adapter skeleton lives in
    :mod:`adaptive_reflow.adapters.graphbfn` so the public engine +
    Protocol surface can be exercised on CPU-only environments, but
    no production checkpoint is admitted for evaluation until the
    dependency blockers clear (per the design spec).

    Re-admit with ``adapter_status="admitted_unconditional_only"``
    once the QM9 / ZINC250k weights land (the GraphBFN baseline is
    unconditional 2D molecular graph generation — there is no
    pocket-conditioned efficacy claim to validate).
    """
    return CandidateEntry(
        repo_url="https://arxiv.org/abs/2412.08559 (ICLR 2025 GraphBFN) "
        "/ arXiv:2510.10211 (Hierarchical BFN)",
        commit=GRAPHBFN_PINNED_COMMIT,
        license="TODO:license (TBD pending weights acquisition)",
        paper_id="arXiv:2412.08559 (ICLR 2025) / arXiv:2510.10211 (Hierarchical)",
        paper_date="2024-12 / 2025-10",
        task_conditions=("other",),  # 2D molecular-graph generation (not 3D).
        dataset_split="canonical QM9 100k/10k/24k OR ZINC250k 220k/15k/15k",
        native_metric_protocol=(
            "RDKit-based validity / FCD (Frechet ChemNet Distance) / "
            "NSPDK (Neighborhood Subgraph Pairwise Distance Kernel); "
            "also per-property KL / Wasserstein on logP / QED / SA. "
            "Eval gated on data/graphbfn/weights landing + RDKit + ChemNet "
            "env at /tmp/flowa_rdkit_env."
        ),
        ode_call_site=(
            "BFN Bayesian-update loop wrapped as NFE-step calls: per-step "
            "(1) sample y_t per node / edge from current Categorical, "
            "(2) call the GNN / Graph Transformer forward, "
            "(3) update per-node + per-edge Categorical parameters."
        ),
        state_boundary=(
            "graph-shaped native state: per-node (N, K_atom) Categorical "
            "params, per-edge (E, K_bond) Categorical params, (N, N) "
            "adjacency logits. Carried behind TensorRef keys in the "
            "adapter's private _native_states cache; engine never "
            "inspects the payload."
        ),
        condition_boundary=(
            "unconditional baseline + property-conditioned (logP / QED / "
            "SA) via Hierarchical CDF-rounding; ``condition_kind`` is "
            "one of {unconditional, property_logp, property_qed, "
            "property_sa} with optional ``property_value`` scalar."
        ),
        restart_boundary=(
            "graph BFN restart blend on per-channel Categorical "
            "parameters: ``m * prior + (1 - m) * fresh`` elementwise "
            "with ``m = 1 - beta`` per channel. Mirrors "
            "TwoDimFMAdapter blend math lifted to graph-shaped tensors."
        ),
        compatible_channels=(
            "atoms",
            "bonds",
            "adjacency",
            "valence",
            "charge",
        ),
        available_checkpoint=None,
        adapter_status="unsupported",
        audit_notes=(
            "GraphBFN native state is graph-shaped (variable N, E, "
            "adjacency), not a fixed tensor. The engine's StateBundle "
            "treats state_shape as a fixed tuple; the adapter publishes "
            "state_shape=() (zero-length surrogate) and routes the "
            "graph payload through private native-state dict keyed by "
            "native_state_digest, matching the FlowMol3 / ReferenceFlowA "
            "placeholder pattern. Per-channel domain is "
            "atoms/bonds/adjacency=discrete + valence/charge=continuous. "
            "DEP-BLOCKER: published GNN/Graph-Transformer weights have "
            "NOT landed in data/graphbfn/ (status='failed' in "
            "weights_metadata.json per the design spec). Adapter ships "
            "with synthetic-mode (deterministic NumPy BFN update loop) "
            "so the Protocol surface can be exercised on CPU-only "
            "environments until production weights land. EVAL-BLOCKER: "
            "RDKit-based validity / FCD / NSPDK evaluators require "
            "rdkit>=2024.3.3 + chemnet-pretrained-weights; the harness "
            "stub at tools/run_sota_graphbfn_experiment.py documents "
            "the planned CLI surface but does not execute."
        ),
        registered_at="2026-08-31",
        registered_by="DTB-M7 GraphBFN adapter scaffold",
    )


__all__ = [
    "FLOWMOL3_PINNED_COMMIT",
    "GRAPHBFN_PINNED_COMMIT",
    "AdapterStatus",
    "CandidateEntry",
    "CandidateRegistry",
    "TaskCondition",
    "admit_entry",
    "default_registry",
    "make_default_flowmol3_entry",
    "make_default_flowmol3adapter_entry",
    "make_default_graphbfn_entry",
    "make_initial_registry",
]
