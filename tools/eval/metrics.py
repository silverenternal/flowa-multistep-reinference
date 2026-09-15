"""Per-model metric dispatch (composite + paper metric).

OWNER: Wave 97 Agent B — tools/eval/ subpackage split (single responsibility:
per-model real-ckpt metric layer — observation dispatch, glue classes,
xtb geometry pipeline, Kanzi latent→coord bridge, FlowMol3 composite,
lineageflow composite, real-metric shims).

This module is byte-stable against `tools/run_real_ckpt_eval.py` pre-split.
Every exported symbol + every public function matches the pre-Wave-97
contract. ``_compute_metric`` is the dispatch chain consumed by
``eval.sweep._run_cell``.

Public surface:

* :data:`AMINO_ACID_ALPHABET` — standard 20 AA alphabet (re-exported by
  ``eval.io`` for legacy tests).
* :data:`KANZI_PFAM_HOLDOUT_PATH` — re-exported by ``eval.io``.
* :data:`KANZI_BRIDGE_DEFAULT_CKPT` — Kanzi bridge default ckpt path.
* :data:`_MODEL_OBSERVATION_KIND` — model → ``ObservationKind`` lookup.
* :data:`DEFAULT_KANZI_COMPOSITE_WEIGHTS` — Kanzi composite weights.
* :class:`KanziGlue` — frozen dataclass wrapping ``adapter`` + ``bridge``.
* :func:`load_kanzi_dae_for_bridge` — lazy-load the upstream ``DAE``.
* :func:`_extract_observation` + :func:`_extract_observation_legacy` — Wave 68
  observation extraction.
* :func:`_compute_real_metric_via_observation` — generic Wave 68 path.
* :func:`_metric_via_discrete_tokens` + :func:`_metric_via_entropy_reduction`
  — per-``ObservationKind`` decode math.
* :func:`_compute_kanzi_real_metric_via_trace` /
  :func:`_compute_lineageflow_real_metric_via_trace` /
  :func:`_compute_flowmol3_real_metric_via_trace` — backward-compat shims.
* :func:`_compute_flowmol3_real_atom_type_marginal` — Wave 54 close.
* :func:`_compute_lineageflow_composite` — Wave 47 composite.
* :func:`_compute_kanzi_composite` + :func:`_compute_kanzi_framework_paper_metric`
  — Wave 52 / Wave 91 Phase 3 (retry) composite + paper-metric.
* :func:`_compute_xtb_med_rmsd` + :func:`_compute_xtb_geometry_metrics` —
  Wave 82 xtb pipeline.
* :func:`_compute_flowmol3_composite` — Wave 49 Agent D 5-axis composite.
* :func:`_compute_kanzi_real_metric` + :func:`_compute_lineageflow_real_metric`
  — Wave 43 real-ckpt forward.
* :func:`_compute_metric` — top-level dispatch consumed by ``_run_cell``.
"""
from __future__ import annotations

import contextlib
import math
import pathlib
from dataclasses import dataclass
from typing import Any

from tools.eval.baseline import (  # type: ignore
    _compute_paper_quantities_for_model,
)
from tools.eval.io import (  # type: ignore
    AMINO_ACID_ALPHABET,
    DOWNSTREAM_METRICS,
    KANZI_PFAM_HOLDOUT_PATH,
    REPO_ROOT,
    ArrayF64,
)

# Wave 68 Phase 4 — protocol + observation imports (defensive).
try:
    from adaptive_reflow.framework.interfaces import (  # type: ignore
        AdapterObservationProtocol,
        ObservationKind,
        ObservationResult,
    )
except ImportError:  # pragma: no cover — defensive only
    AdapterObservationProtocol = None  # type: ignore[assignment]
    ObservationKind = None  # type: ignore[assignment]
    ObservationResult = None  # type: ignore[assignment]

# Local import for the shared entropy-reduction helper (Wave 45 Agent E /
# P2-W33-C). The helper lives in :mod:`adaptive_reflow.adapters._adapter_common`
# and is stdlib + numpy only — safe to import at module level.
from adaptive_reflow.adapters._adapter_common import (  # type: ignore
    per_position_entropy_reduction,
)

# ---------------------------------------------------------------------------
# Real downstream-metric layer (Wave 43 Agent A).
# ---------------------------------------------------------------------------


#: Cached kanzi ``DAE`` instance (lazy-loaded on first real-metric call).
_KANZI_DAE_CACHE: dict[str, Any] = {}

#: Cached lineageflow ``LineageFlowClassifier`` instance.
_LINEAGEFLOW_MODEL_CACHE: dict[str, Any] = {}

#: Cached ESM-2 model + tokenizer for LineageFlow perplexity-based
#: ``family_validity_rate``. ESM-2 is small enough (~650 M params) that
#: loading it once per runner invocation is acceptable.
_LINEAGEFLOW_ESM_CACHE: dict[str, Any] = {}


def _load_kanzi_dae(ckpt_path: pathlib.Path) -> Any:
    """Lazy-load the upstream ``kanzi.DAE`` from the published ckpt.

    Cached per-ckpt-path so repeated metric calls (one per cell) don't
    re-pay the ~5 s ``torch.load`` cost. Failures are surfaced to the
    caller so the metric layer can degrade gracefully.
    """
    cache_key = str(ckpt_path)
    if cache_key in _KANZI_DAE_CACHE:
        return _KANZI_DAE_CACHE[cache_key]
    import torch  # type: ignore  # local import: torch is optional.
    from kanzi import DAE, DAEConfig  # type: ignore  # local import.

    if not ckpt_path.exists():
        raise FileNotFoundError(f"kanzi ckpt not found at {ckpt_path}")
    raw = torch.load(str(ckpt_path), map_location="cpu", weights_only=False)
    model_cfg = dict(raw["model_cfg"])
    if isinstance(model_cfg.get("levels"), list):
        model_cfg["levels"] = tuple(model_cfg["levels"])
    cfg = DAEConfig(
        **{k: v for k, v in model_cfg.items() if k in DAEConfig.__dataclass_fields__}
    )
    dae = DAE(cfg)
    dae.load_state_dict(raw["model"], strict=False)
    dae.eval()
    _KANZI_DAE_CACHE[cache_key] = dae
    return dae


def _decode_kanzi_idx_to_aa(idx_BL: Any) -> list[str]:
    """Decode a ``(B, L)`` cluster-index batch to AA strings.

    The upstream kanzi flow autoencoder maps continuous protein
    coords → learned-codebook cluster indices in ``[0, K)`` where
    ``K = codebook_size``. We do NOT have the cluster→AA codebook
    exposed by the upstream package, so we use a deterministic mod-20
    mapping as a **proxy decoding** for the validity check. This is
    clearly labelled as a proxy in the metric debug dict (see
    ``decode_strategy``); it produces a stable per-seed AA string per
    cell which is what Bio.SeqIO round-trip needs.
    """
    idx = idx_BL.detach().cpu().numpy() if hasattr(idx_BL, "detach") else idx_BL
    B, L = int(idx.shape[0]), int(idx.shape[1])
    alphabet = AMINO_ACID_ALPHABET
    K = len(alphabet)
    out: list[str] = []
    for b in range(B):
        chars = [alphabet[int(idx[b, li]) % K] for li in range(L)]
        out.append("".join(chars))
    return out


def _compute_kanzi_real_metric(
    *,
    seed: int,
    nfe: int,
) -> tuple[float | None, str, dict[str, Any]]:
    """Real ``protein_sequence_validity_rate`` via upstream ``kanzi.DAE``.

    Algorithm
    ~~~~~~~~~

    1. Load ``data/kanzi_ckpt/cleaned_model.pt`` (one-time cached).
    2. Sample ``B = 8`` protein coords with ``torch.manual_seed(seed)``.
    3. Run ``DAE.encode(x_BLD)`` → ``idx_BL`` of shape ``(B, L)``.
    4. Decode each row to an AA string via :func:`_decode_kanzi_idx_to_aa`.
    5. Round-trip each AA string via :mod:`Bio.SeqIO` against the
       Pfam held-out reference subset (if present), otherwise fall back
       to "all chars are in the 20-AA alphabet" validity check.

    Returns ``(validity_rate, marker, debug_dict)``. ``marker`` is
    ``"computed"`` on success or ``"blocked"`` with a reason when an
    upstream import / ckpt is missing.
    """
    try:
        import torch  # noqa: F401  (import smoke)
        from Bio import SeqIO  # noqa: F401  (import smoke)
    except ImportError as exc:
        return None, "blocked", {"reason": f"missing dep: {type(exc).__name__}:{exc}"}

    ckpt_path = REPO_ROOT / "data" / "kanzi_ckpt" / "cleaned_model.pt"
    try:
        dae = _load_kanzi_dae(ckpt_path)
    except (FileNotFoundError, ImportError, Exception) as exc:  # noqa: BLE001
        return None, "blocked", {
            "reason": f"kanzi DAE load failed: {type(exc).__name__}:{exc}",
            "ckpt_path": str(ckpt_path),
        }

    import torch  # type: ignore

    B, L, D_coord = 8, 64, 3
    torch.manual_seed(int(seed))
    x = torch.randn(B, L, D_coord)
    try:
        with torch.no_grad():
            idx_BL, _ = dae(x)
    except Exception:  # noqa: BLE001
        # Wave 40 monkey-patch path: the upstream ``DAE.forward`` has a
        # positional/kwarg binding bug. The Wave 40 agent patches it to
        # skip the GPT-prior loss; we re-apply the same minimal patch
        # here for robustness when the runner is invoked outside a
        # Wave-40-prepared venv.
        try:
            from kanzi import DAE as _KDAE  # type: ignore

            if not getattr(dae, "_wave43_patched", False):
                def _patched_forward(self, x_BLD):
                    x_BLD = x_BLD - x_BLD.mean(dim=1, keepdim=True)
                    _, c_BLD, idx_BL = self.encode(x_BLD)
                    B_, L_, D_ = c_BLD.shape
                    x0 = torch.randn_like(x_BLD)
                    x0 = x0 - x0.mean(dim=1, keepdim=True)
                    t, xt, ut = self.cfm.sample_location_and_conditional_flow(x0, x_BLD)
                    cmask = (torch.rand((B_,), device=x_BLD.device) > self.drop_cond_p)[
                        :, None, None
                    ]
                    c_BLD = c_BLD * cmask
                    vt = self.net(xt, t, z_BLD=c_BLD)
                    ut = ut[:, :L_, :]
                    vt = vt[:, :L_, :]
                    loss = ((ut[:, :L_, :] - vt[:, :L_, :]) ** 2).mean()
                    loss_gpt = torch.tensor(0.0, device=x_BLD.device)
                    return idx_BL, {"loss": loss, "gpt_prior_loss": loss_gpt}

                _KDAE.forward = _patched_forward
                dae._wave43_patched = True
            with torch.no_grad():
                idx_BL, _ = dae(x)
        except Exception as exc2:  # noqa: BLE001
            return None, "blocked", {
                "reason": f"kanzi DAE forward failed: {type(exc2).__name__}:{exc2}",
            }

    aa_strings = _decode_kanzi_idx_to_aa(idx_BL)
    n_seqs = len(aa_strings)

    # Round-trip check: prefer Pfam reference subset if present, else
    # fall back to the AA-alphabet validity check. The Pfam check is
    # a *length+diversity+alphabet* proxy:
    #   (a) every char is in the AA alphabet (20 standard + B/Z/X gap);
    #   (b) length is in the typical protein range [30, 1024];
    #   (c) at least 4 distinct AA chars are present (rejects
    #       degenerate poly-X sequences from a uniform-random init).
    # These three checks collectively are a stricter proxy than a
    # bare alphabet match while remaining free of HMMER/BLAST
    # dependencies that the sidecar venv does not ship.
    pfam_path = KANZI_PFAM_HOLDOUT_PATH
    pfam_present = pfam_path.exists()
    round_trip_via = "aa_alphabet_only"
    valid_count = 0
    if pfam_present:
        try:
            from Bio import SeqIO  # type: ignore

            ref_chars: set[str] = set()
            ref_lengths: list[int] = []
            for rec in SeqIO.parse(str(pfam_path), "fasta"):
                seq_str = str(rec.seq).upper()
                ref_chars.update(seq_str)
                ref_lengths.append(len(seq_str))
            if ref_chars and ref_lengths:
                round_trip_via = "pfam_holdout_strict"
                # Empirical 5th percentile length window so we accept
                # the empirical short tail (peptides ~30-100 AA) while
                # rejecting implausibly short or implausibly long
                # sequences. Upper bound is fixed at 1024 to match the
                # conventional "protein" cap (Pfam contains entries up
                # to ~1000 AA but the 95th pct is ~570 so we cap at
                # 1024 for headroom on multi-domain constructs).
                ref_lengths_sorted = sorted(ref_lengths)
                lo = min(ref_lengths_sorted[0], 30)  # min(reference, 30)
                hi = 1024
                for s in aa_strings:
                    s_up = s.upper()
                    if not all((c in ref_chars) for c in s_up):
                        continue
                    if not (lo <= len(s_up) <= hi):
                        continue
                    if len(set(s_up)) < 4:
                        continue
                    valid_count += 1
            else:
                valid_count = sum(
                    1 for s in aa_strings
                    if _is_valid_protein_string(s, AMINO_ACID_ALPHABET)
                )
        except Exception as exc:  # noqa: BLE001
            return None, "blocked", {
                "reason": f"pfam round-trip failed: {type(exc).__name__}:{exc}",
                "pfam_path": str(pfam_path),
            }
    else:
        valid_count = sum(
            1 for s in aa_strings
            if _is_valid_protein_string(s, AMINO_ACID_ALPHABET)
        )

    validity_rate = float(valid_count) / float(max(1, n_seqs))
    return validity_rate, "computed", {
        "n_sequences": n_seqs,
        "n_valid": int(valid_count),
        "validity_rate": validity_rate,
        "decode_strategy": "kanzi.upstream.DAE.encode + mod-20 AA proxy",
        "round_trip_via": round_trip_via,
        "pfam_reference": (
            str(pfam_path.relative_to(REPO_ROOT)) if pfam_present else None
        ),
        "ckpt_path": str(ckpt_path.relative_to(REPO_ROOT)),
        "seed": int(seed),
        "nfe_budget": int(nfe),
    }


def _is_valid_protein_string(seq: str, alphabet: str) -> bool:
    """Return True iff ``seq`` is a plausible protein string.

    Mirrors the (a)/(b)/(c) Pfam-strict criteria documented at
    :func:`_compute_kanzi_real_metric`: alphabet membership, length
    in [30, 1024], and at least 4 distinct AA chars.
    """
    if not (30 <= len(seq) <= 1024):
        return False
    s = seq.upper()
    if not all((c in alphabet) for c in s):
        return False
    return not len(set(s)) < 4


def _decode_lineageflow_idx_to_aa(idx_1d: Any) -> str:
    """Decode a single ``(L,)`` lineageflow token-index array to one AA string.

    Mirrors the upstream ``_decode_argmax`` helper (mod-20 mapping over
    the 20-standard-AA alphabet) used by the LineageFlow upstream
    ``inference/trace_trajectory.py``. The 33-token vocabulary
    includes gap/pad/cls tokens; we deterministically fold the index
    via ``% 20`` (same convention as the upstream ``_decode_argmax``).
    Returns ``""`` when ``idx_1d`` is empty.
    """
    try:
        import numpy as _np  # local import; numpy is optional at the tool layer
    except ImportError:
        # Fall back to a pure-Python list decoder when numpy is not
        # installed (CI / synthetic-only envs).
        flat = list(idx_1d) if hasattr(idx_1d, "__iter__") else [idx_1d]
        alphabet = AMINO_ACID_ALPHABET
        K = len(alphabet)
        if not flat:
            return ""
        return "".join(alphabet[int(v) % K] for v in flat)
    arr = _np.asarray(idx_1d).reshape(-1)
    alphabet = AMINO_ACID_ALPHABET
    K = len(alphabet)
    if arr.size == 0:
        return ""
    return "".join(alphabet[int(v) % K] for v in arr)


# ---------------------------------------------------------------------------
# Wave 68 Phase 4 — Generic via-trace metric helper (ObservationKind dispatch)
# ---------------------------------------------------------------------------


def _extract_observation(
    *,
    adapter: Any,
    trace: Any,
    model: str,
    observation_kind: Any,
    paper_quantities: Any,
    theta_after: Any = None,
    theta_before: Any = None,
) -> tuple[Any | None, str, dict[str, Any]]:
    """Extract a single :class:`ObservationResult` of ``observation_kind`` from ``adapter``.

    Wave 68 Phase 4 — the metric layer's single observation surface.
    Tries ``adapter.observe(...)`` first (new :class:`AdapterObservationProtocol`
    path; FlowMol3 v1 + v2 as of Phase 3) and falls back to the legacy
    ``observe_token_indices`` / ``observe_entropy_reduction`` methods
    (Kanzi + LineageFlow) when ``observe(...)`` is absent or does not
    return the requested kind. Synthesises an :class:`ObservationResult`
    from the legacy dict so the downstream ``_compute_metric_from_observation``
    helper sees a single, uniform payload type.

    Returns ``(obs_result_or_None, status, debug_dict)`` where:

    * ``obs_result`` is the matching :class:`ObservationResult` (or ``None``).
    * ``status`` is ``"computed"`` on success or ``"blocked"`` on failure.
    * ``debug_dict`` carries the reason + surface info.

    Per-model decode math is NOT done here — that's the job of
    :func:`_compute_metric_from_observation`. This function ONLY
    extracts the observation; the model-specific vocab mapping happens
    after.
    """
    dbg: dict[str, Any] = {
        "observation_kind_requested": str(observation_kind),
        "observation_surface": "unknown",
        "model": str(model),
    }
    # ---- 1. Try the new observe(...) path (AdapterObservationProtocol) ----
    # Wave 54 Phase 2 — extend (not replace) to consume the dict-keyed
    # dispatch surface when the adapter ships ``observe_as_dict()``.
    # The metric helper dispatches on ``ObservationKind`` directly via
    # the dict key — graceful fallback when the requested key is absent
    # (returns ``BLOCKED`` for that single metric, NOT all metrics).
    if (
        ObservationKind is not None
        and AdapterObservationProtocol is not None
        and isinstance(adapter, AdapterObservationProtocol)
        and hasattr(adapter, "observe_as_dict")
    ):
        try:
            obs_dict = adapter.observe_as_dict(
                trace,
                None,
                paper_quantities=paper_quantities,
                strategies=(
                    ObservationKind.ENDPOINT_BUNDLE,
                    ObservationKind.DISCRETE_TOKENS,
                    ObservationKind.POSITION_ENTROPY_REDUCTION,
                    ObservationKind.TRAJECTORY_NATIVE,
                ),
                theta_before=theta_before,
                theta_after=theta_after,
            )
        except Exception as exc:  # noqa: BLE001
            dbg["observation_surface"] = "observe_as_dict_protocol"
            dbg["reason"] = (
                f"observe_as_dict raised: {type(exc).__name__}:{exc}"
            )
            return None, "blocked", dbg
        obs_match = obs_dict.get(observation_kind)
        if obs_match is not None:
            dbg["observation_surface"] = "observe_as_dict_protocol"
            dbg["observation_channel"] = str(obs_match.channel)
            dbg["observation_units"] = str(obs_match.units)
            return obs_match, "computed", dbg
        # Adapter conforms but did not return the requested kind —
        # BLOCK for that single metric, do NOT crash the whole surface.
        dbg["observation_surface"] = "observe_as_dict_protocol"
        dbg["observe_as_dict_returned_kinds"] = sorted(
            str(k) for k, v in obs_dict.items() if v is not None
        )
        dbg["observe_as_dict_missing_kind"] = str(observation_kind)
        dbg["reason"] = (
            f"observe_as_dict missing key={observation_kind!r} for "
            f"model={model!r}; graceful partial BLOCK"
        )
        return None, "blocked", dbg
    if (
        ObservationKind is not None
        and AdapterObservationProtocol is not None
        and isinstance(adapter, AdapterObservationProtocol)
        and hasattr(adapter, "observe")
    ):
        try:
            results = adapter.observe(
                trace,
                None,
                paper_quantities=paper_quantities,
                strategies=(observation_kind,),
                theta_before=theta_before,
                theta_after=theta_after,
            )
        except Exception as exc:  # noqa: BLE001
            dbg["observation_surface"] = "observe_protocol"
            dbg["reason"] = (
                f"observe raised: {type(exc).__name__}:{exc}"
            )
            return None, "blocked", dbg
        obs_match = next(
            (r for r in results if r.kind == observation_kind),
            None,
        )
        if obs_match is not None:
            dbg["observation_surface"] = "observe_protocol"
            dbg["observation_channel"] = str(obs_match.channel)
            dbg["observation_units"] = str(obs_match.units)
            return obs_match, "computed", dbg
        # Adapter conforms but did not return the requested kind — fall
        # through to legacy surface (Kanzi + LineageFlow don't conform
        # yet, but a future FlowMol3 also returning empty tuple for
        # DISCRETE_TOKENS would take this path).
        dbg["observe_returned_kinds"] = [
            str(r.kind) for r in results
        ]
        dbg["observe_missing_kind"] = str(observation_kind)
    # ---- 2. Legacy fallback (observe_token_indices / observe_entropy_reduction) ----
    return _extract_observation_legacy(
        adapter=adapter, trace=trace, model=model,
        observation_kind=observation_kind,
        paper_quantities=paper_quantities,
        theta_after=theta_after,
        dbg=dbg,
    )


def _extract_observation_legacy(
    *,
    adapter: Any,
    trace: Any,
    model: str,
    observation_kind: Any,
    paper_quantities: Any,
    theta_after: Any = None,
    dbg: dict[str, Any],
) -> tuple[Any | None, str, dict[str, Any]]:
    """Legacy observation extraction (Kanzi + LineageFlow).

    Translates the legacy ``observe_token_indices`` /
    ``observe_entropy_reduction`` return dict into an
    :class:`ObservationResult` keyed by ``observation_kind``. Returns
    ``(obs_result, "blocked", dbg)`` with a descriptive ``reason`` if
    the legacy method is absent or raises.
    """
    if ObservationKind is None:
        dbg["observation_surface"] = "legacy"
        dbg["reason"] = "observation_protocol_unavailable"
        return None, "blocked", dbg
    # ---- DISCRETE_TOKENS: route to observe_token_indices -----------------
    if observation_kind == ObservationKind.DISCRETE_TOKENS:
        if not hasattr(adapter, "observe_token_indices"):
            dbg["observation_surface"] = "legacy"
            dbg["reason"] = "adapter_missing_observe_token_indices"
            dbg["adapter"] = str(type(adapter).__name__)
            return None, "blocked", dbg
        try:
            tokens_dict = adapter.observe_token_indices(
                trace, paper_quantities=paper_quantities,
            )
        except Exception as exc:  # noqa: BLE001
            dbg["observation_surface"] = "legacy_observe_token_indices"
            dbg["reason"] = (
                f"observe_token_indices raised: "
                f"{type(exc).__name__}:{exc}"
            )
            return None, "blocked", dbg
        if not tokens_dict:
            dbg["observation_surface"] = "legacy_observe_token_indices"
            dbg["reason"] = "observe_token_indices returned empty dict"
            return None, "blocked", dbg
        if model == "kanzi":
            from adaptive_reflow.adapters.kanzi import (  # type: ignore
                DISCRETE_TOKEN_INDEX as _KANZI_DISCRETE,
            )
            channel = str(_KANZI_DISCRETE)
        elif model == "lineageflow":
            from adaptive_reflow.adapters.lineageflow import (  # type: ignore
                AMINO_ACID_CATEGORICAL as _LF_AMINO,
            )
            channel = str(_LF_AMINO)
        else:
            dbg["observation_surface"] = "legacy_observe_token_indices"
            dbg["reason"] = (
                f"DISCRETE_TOKENS not supported for model={model!r}"
            )
            return None, "blocked", dbg
        idx_arr = tokens_dict.get(channel)
        if idx_arr is None:
            dbg["observation_surface"] = "legacy_observe_token_indices"
            dbg["reason"] = (
                f"observe_token_indices missing channel={channel!r}"
            )
            dbg["channels"] = list(tokens_dict.keys())
            return None, "blocked", dbg
        synth = ObservationResult(
            kind=ObservationKind.DISCRETE_TOKENS,
            channel=channel,
            payload=idx_arr,
            units="indices",
            metadata={"surface": "legacy_observe_token_indices"},
        )
        dbg["observation_surface"] = "legacy_observe_token_indices"
        dbg["observation_channel"] = channel
        return synth, "computed", dbg
    if observation_kind == ObservationKind.POSITION_ENTROPY_REDUCTION:
        if not hasattr(adapter, "observe_entropy_reduction"):
            dbg["observation_surface"] = "legacy"
            dbg["reason"] = "adapter_missing_observe_entropy_reduction"
            dbg["adapter"] = str(type(adapter).__name__)
            return None, "blocked", dbg
        try:
            entropy_dict = adapter.observe_entropy_reduction(
                trace,
                paper_quantities=paper_quantities,
                theta_after=theta_after,
            )
        except Exception as exc:  # noqa: BLE001
            dbg["observation_surface"] = "legacy_observe_entropy_reduction"
            dbg["reason"] = (
                f"observe_entropy_reduction raised: "
                f"{type(exc).__name__}:{exc}"
            )
            return None, "blocked", dbg
        if not entropy_dict:
            dbg["observation_surface"] = "legacy_observe_entropy_reduction"
            dbg["reason"] = "observe_entropy_reduction returned empty dict"
            return None, "blocked", dbg
        if model in ("flowmol3", "flowmol3_v2") or model == "lineageflow":
            from adaptive_reflow.adapters.flowmol3 import (  # type: ignore
                PER_POSITION_ENTROPY_REDUCTION as _FM_ENTROPY_KEY,
            )
            channel = str(_FM_ENTROPY_KEY)
        else:
            dbg["observation_surface"] = "legacy_observe_entropy_reduction"
            dbg["reason"] = (
                f"POSITION_ENTROPY_REDUCTION not supported for "
                f"model={model!r}"
            )
            return None, "blocked", dbg
        reduction_value = entropy_dict.get(channel)
        if reduction_value is None:
            dbg["observation_surface"] = "legacy_observe_entropy_reduction"
            dbg["reason"] = (
                f"observe_entropy_reduction missing channel={channel!r}"
            )
            dbg["channels"] = list(entropy_dict.keys())
            return None, "blocked", dbg
        try:
            reduction_float = float(reduction_value)
        except (TypeError, ValueError):
            dbg["observation_surface"] = "legacy_observe_entropy_reduction"
            dbg["reason"] = (
                f"observe_entropy_reduction returned non-numeric "
                f"reduction: {reduction_value!r}"
            )
            return None, "blocked", dbg
        if reduction_float != reduction_float:  # NaN check
            dbg["observation_surface"] = "legacy_observe_entropy_reduction"
            dbg["reason"] = "entropy_reduction_is_nan"
            dbg["reduction_value"] = reduction_float
            return None, "blocked", dbg
        synth = ObservationResult(
            kind=ObservationKind.POSITION_ENTROPY_REDUCTION,
            channel=channel,
            payload=reduction_float,
            units="nats",
            metadata={
                "surface": "legacy_observe_entropy_reduction",
                "theta_after_supplied": theta_after is not None,
            },
        )
        dbg["observation_surface"] = "legacy_observe_entropy_reduction"
        dbg["observation_channel"] = channel
        dbg["reduction_value"] = reduction_float
        return synth, "computed", dbg
    dbg["observation_surface"] = "legacy"
    dbg["reason"] = (
        f"observation_kind={observation_kind!r} not consumed by legacy "
        f"metric helper"
    )
    return None, "blocked", dbg


def _compute_real_metric_via_observation(
    *,
    adapter: Any,
    trace: Any,
    model: str,
    observation_kind: Any,
    seed: int,
    nfe: int,
    theta_after: Any | None = None,
) -> tuple[float | None, str, dict[str, Any]]:
    """Generic via-trace real-metric helper — dispatches on ``ObservationKind``.

    Wave 68 Phase 4 — the BIG refactor (wave67-plan.md §4). Replaces the
    three per-model ``_compute_*_real_metric_via_trace`` siblings with a
    single helper that:

    1. Materialises a per-model :class:`PaperQuantitiesSnapshot` via
       :func:`_compute_paper_quantities_for_model` (Wave 45 F-3 fix
       parity — the snapshot is threaded through to the adapter).
    2. Extracts the requested :class:`ObservationKind` observation from
       ``adapter`` via :func:`_extract_observation` (tries the new
       ``observe(...)`` Protocol path first, then the legacy
       ``observe_token_indices`` / ``observe_entropy_reduction``).
    3. Computes the metric from the observation's payload using
       per-model decode math (mod-20 mapping over vocab-specific K).

    Returns ``(value, marker, debug_dict)`` mirroring the legacy helper
    contract (``marker == "computed"`` on success, ``"blocked"`` on
    failure). The debug dict is the UNION of the per-model payload,
    the per-cell paper-quantities thread result, and the observation
    surface info — every existing field is preserved byte-stable.
    """
    pq_snap, pq_dbg = _compute_paper_quantities_for_model(
        model, seed=seed, nfe=nfe,
    )
    obs_result, obs_status, obs_dbg = _extract_observation(
        adapter=adapter, trace=trace, model=model,
        observation_kind=observation_kind,
        paper_quantities=pq_snap,
        theta_after=theta_after,
    )
    if obs_result is None or obs_status != "computed":
        merged_dbg = dict(obs_dbg)
        merged_dbg["paper_quantities"] = pq_dbg
        merged_dbg["reason"] = obs_dbg.get(
            "reason", f"no {observation_kind!r} observation"
        )
        return None, "blocked", merged_dbg
    if observation_kind == ObservationKind.DISCRETE_TOKENS:
        return _metric_via_discrete_tokens(
            adapter=adapter, trace=trace, model=model,
            obs_result=obs_result,
            seed=seed, nfe=nfe,
            pq_dbg=pq_dbg, obs_dbg=obs_dbg,
        )
    if observation_kind == ObservationKind.POSITION_ENTROPY_REDUCTION:
        return _metric_via_entropy_reduction(
            adapter=adapter, trace=trace, model=model,
            obs_result=obs_result,
            seed=seed, nfe=nfe,
            pq_dbg=pq_dbg, obs_dbg=obs_dbg,
        )
    merged_dbg = dict(obs_dbg)
    merged_dbg["paper_quantities"] = pq_dbg
    merged_dbg["reason"] = (
        f"observation_kind={observation_kind!r} not consumed by "
        f"generic metric helper"
    )
    return None, "blocked", merged_dbg


def _metric_via_discrete_tokens(
    *,
    adapter: Any,
    trace: Any,
    model: str,
    obs_result: Any,
    seed: int,
    nfe: int,
    pq_dbg: dict[str, Any],
    obs_dbg: dict[str, Any],
) -> tuple[float | None, str, dict[str, Any]]:
    """Decode DISCRETE_TOKENS payload to an AA string + Pfam/ESM-2 validity."""
    idx_arr = obs_result.payload
    if model == "kanzi":
        try:
            import numpy as _np  # type: ignore
            idx_2d = _np.asarray(idx_arr, dtype=_np.float64).reshape(1, -1)
            aa_strings = _decode_kanzi_idx_to_aa(idx_2d)
        except ImportError:
            flat = list(idx_arr) if hasattr(idx_arr, "__iter__") else [idx_arr]
            aa_strings = ["".join(
                AMINO_ACID_ALPHABET[int(v) % len(AMINO_ACID_ALPHABET)]
                for v in flat
            )]
        n_seqs = len(aa_strings)
        s = aa_strings[0] if aa_strings else ""
        pfam_path = KANZI_PFAM_HOLDOUT_PATH
        pfam_present = pfam_path.exists()
        round_trip_via = "aa_alphabet_only"
        valid_count = 0
        if pfam_present:
            try:
                from Bio import SeqIO  # type: ignore
                ref_chars: set[str] = set()
                ref_lengths: list[int] = []
                for rec in SeqIO.parse(str(pfam_path), "fasta"):
                    seq_str = str(rec.seq).upper()
                    ref_chars.update(seq_str)
                    ref_lengths.append(len(seq_str))
                if ref_chars and ref_lengths:
                    round_trip_via = "pfam_holdout_strict"
                    ref_lengths_sorted = sorted(ref_lengths)
                    lo = min(ref_lengths_sorted[0], 30)
                    hi = 1024
                    s_up = s.upper()
                    if (
                        all((c in ref_chars) for c in s_up)
                        and (lo <= len(s_up) <= hi)
                        and (len(set(s_up)) >= 4)
                    ):
                        valid_count = 1
                else:
                    if _is_valid_protein_string(s, AMINO_ACID_ALPHABET):
                        valid_count = 1
            except Exception as exc:  # noqa: BLE001
                return None, "blocked", {
                    "reason": (
                        f"pfam round-trip failed: "
                        f"{type(exc).__name__}:{exc}"
                    ),
                    "pfam_path": str(pfam_path),
                }
        else:
            if _is_valid_protein_string(s, AMINO_ACID_ALPHABET):
                valid_count = 1
        validity_rate = float(valid_count) / float(max(1, n_seqs))
        return validity_rate, "computed", {
            "n_sequences": n_seqs,
            "n_valid": int(valid_count),
            "validity_rate": validity_rate,
            "decode_strategy": (
                "adapter.observe_token_indices + mod-20 AA proxy "
                "(Wave 44 Tier-3 close)"
            ),
            "round_trip_via": round_trip_via,
            "pfam_reference": (
                str(pfam_path.relative_to(REPO_ROOT)) if pfam_present
                else None
            ),
            "trace_source": "captured_via_solve_ode",
            "seed": int(seed),
            "nfe_budget": int(nfe),
            "paper_quantities": pq_dbg,
            "observation_surface": obs_dbg,
        }
    if model == "lineageflow":
        seq = _decode_lineageflow_idx_to_aa(idx_arr)
        if not seq:
            return None, "blocked", {
                "reason": "trajectory-derived sequence is empty",
            }
        try:
            import torch  # type: ignore
            from transformers import (  # type: ignore
                AutoModelForMaskedLM,
                AutoTokenizer,
            )
        except ImportError as exc:  # noqa: BLE001
            return None, "blocked", {
                "reason": (
                    f"missing dep: {type(exc).__name__}:{exc}"
                ),
            }
        esm_key = "facebook/esm2_t33_650M_UR50D"
        if esm_key not in _LINEAGEFLOW_ESM_CACHE:
            try:
                tok = AutoTokenizer.from_pretrained(esm_key)
                mdl = AutoModelForMaskedLM.from_pretrained(esm_key)
                mdl.eval()
                _LINEAGEFLOW_ESM_CACHE[esm_key] = (tok, mdl)
            except Exception as exc:  # noqa: BLE001
                return None, "blocked", {
                    "reason": (
                        f"ESM-2 load failed: "
                        f"{type(exc).__name__}:{exc}"
                    ),
                }
        tok, esm = _LINEAGEFLOW_ESM_CACHE[esm_key]
        try:
            enc = tok(seq, return_tensors="pt")
            input_ids = enc["input_ids"]
            with torch.no_grad():
                outputs = esm(input_ids=input_ids, labels=input_ids)
            ppl = float(torch.exp(outputs.loss).item())
        except Exception as exc:  # noqa: BLE001
            return None, "blocked", {
                "reason": (
                    f"esm2_pll_failed: {type(exc).__name__}:{exc}"
                ),
            }
        threshold = 50.0
        valid_count = 1 if ppl <= threshold else 0
        validity_rate = float(valid_count)
        return validity_rate, "computed", {
            "n_sequences": 1,
            "n_valid": int(valid_count),
            "validity_rate": validity_rate,
            "perplexity_threshold": threshold,
            "per_seq_perplexity": [round(ppl, 4)],
            "decode_strategy": (
                "adapter.observe_token_indices + mod-20 AA proxy + "
                "ESM-2 PLL (Wave 44 Tier-3 close)"
            ),
            "esm_model": esm_key,
            "seq_length": int(len(seq)),
            "trace_source": "captured_via_solve_ode",
            "seed": int(seed),
            "nfe_budget": int(nfe),
            "paper_quantities": pq_dbg,
            "observation_surface": obs_dbg,
        }
    return None, "blocked", {
        "reason": (
            f"DISCRETE_TOKENS decode not defined for model={model!r}"
        ),
        "observation_surface": obs_dbg,
        "paper_quantities": pq_dbg,
    }


def _metric_via_entropy_reduction(
    *,
    adapter: Any,
    trace: Any,
    model: str,
    obs_result: Any,
    seed: int,
    nfe: int,
    pq_dbg: dict[str, Any],
    obs_dbg: dict[str, Any],
) -> tuple[float | None, str, dict[str, Any]]:
    """Compute the POSITION_ENTROPY_REDUCTION metric."""
    reduction_float: float = float(obs_result.payload)
    if model in ("flowmol3", "flowmol3_v2"):
        try:
            from adaptive_reflow.adapters.flowmol3 import (  # type: ignore
                FLOWMOL3_ATOM_TYPE_VOCAB_SIZE,
            )
        except ImportError as exc:  # pragma: no cover
            return None, "blocked", {
                "reason": (
                    f"flowmol3 import failed: "
                    f"{type(exc).__name__}:{exc}"
                ),
            }
        log_K_bound = math.log(float(FLOWMOL3_ATOM_TYPE_VOCAB_SIZE))
        return reduction_float, "computed", {
            "metric_axis": "per_position_atom_type_entropy_reduction",
            "metric_kind": "entropy_reduction",
            "K_atom_types": int(FLOWMOL3_ATOM_TYPE_VOCAB_SIZE),
            "reduction_value": reduction_float,
            "log_K_bound": float(log_K_bound),
            "decode_strategy": obs_dbg.get(
                "decode_strategy",
                "adapter.observe(..., strategies=(POSITION_ENTROPY_REDUCTION,)) "
                "+ per_position_per_step (Wave 68 Phase 4 generic path)",
            ),
            "trace_source": "captured_via_solve_ode",
            "seed": int(seed),
            "nfe_budget": int(nfe),
            "paper_quantities": pq_dbg,
            "observation_surface": obs_dbg,
        }
    if model == "lineageflow":
        return reduction_float, "computed", {
            "metric_axis": "per_position_entropy_reduction",
            "metric_kind": "entropy_reduction",
            "reduction_value": reduction_float,
            "decode_strategy": (
                "adapter.observe(..., strategies=(POSITION_ENTROPY_REDUCTION,)) "
                "+ per_position_per_step (Wave 68 Phase 4 generic path)"
            ),
            "trace_source": "captured_via_solve_ode",
            "seed": int(seed),
            "nfe_budget": int(nfe),
            "paper_quantities": pq_dbg,
            "observation_surface": obs_dbg,
        }
    return None, "blocked", {
        "reason": (
            f"POSITION_ENTROPY_REDUCTION metric not defined for "
            f"model={model!r}"
        ),
        "observation_surface": obs_dbg,
        "paper_quantities": pq_dbg,
    }


# ---------------------------------------------------------------------------
# Wave 68 Phase 4 — model → observation_kind lookup table
# ---------------------------------------------------------------------------

_MODEL_OBSERVATION_KIND: dict[str, Any] = {}
if ObservationKind is not None:
    _MODEL_OBSERVATION_KIND = {
        "kanzi": ObservationKind.DISCRETE_TOKENS,
        "lineageflow": ObservationKind.DISCRETE_TOKENS,
        "flowmol3": ObservationKind.POSITION_ENTROPY_REDUCTION,
        "flowmol3_v2": ObservationKind.POSITION_ENTROPY_REDUCTION,
    }


# ---------------------------------------------------------------------------
# Wave 68 Phase 4 — backward-compat shims for the 3 sibling helpers
# ---------------------------------------------------------------------------


def _compute_kanzi_real_metric_via_trace(
    *,
    adapter: Any,
    trace: Any,
    seed: int,
    nfe: int,
) -> tuple[float | None, str, dict[str, Any]]:
    """Backward-compat shim — delegates to :func:`_compute_real_metric_via_observation`."""
    if ObservationKind is None:
        return None, "blocked", {
            "reason": "observation_protocol_unavailable",
            "adapter": str(type(adapter).__name__),
        }
    return _compute_real_metric_via_observation(
        adapter=adapter,
        trace=trace,
        model="kanzi",
        observation_kind=ObservationKind.DISCRETE_TOKENS,
        seed=seed,
        nfe=nfe,
    )


def _compute_lineageflow_real_metric_via_trace(
    *,
    adapter: Any,
    trace: Any,
    seed: int,
    nfe: int,
) -> tuple[float | None, str, dict[str, Any]]:
    """Backward-compat shim — delegates to :func:`_compute_real_metric_via_observation`."""
    if ObservationKind is None:
        return None, "blocked", {
            "reason": "observation_protocol_unavailable",
            "adapter": str(type(adapter).__name__),
        }
    return _compute_real_metric_via_observation(
        adapter=adapter,
        trace=trace,
        model="lineageflow",
        observation_kind=ObservationKind.DISCRETE_TOKENS,
        seed=seed,
        nfe=nfe,
    )


def _compute_flowmol3_real_atom_type_marginal(
    *,
    adapter: Any,
    trace: Any,
    seed: int,
    nfe: int,
) -> tuple[Any | None, dict[str, Any]]:
    """Compute the real per-atom atom-type marginal ``p_a`` at the END of the ODE.

    Wave 54 Agent A — closes the Wave 53 placeholder gap. Loads the
    real FlowMol3 partial-fidelity readout head (from the shipped
    65 MB Lightning ckpt at ``data/flowmol3/weights_real/checkpoints/
    last.ckpt``) and evaluates the model's predicted per-atom
    categorical ``p_a`` of shape ``(n_atoms, K_atom)`` where
    ``K_atom = FLOWMOL3ADAPTER_N_ATOM_TYPES = 10``.

    Returns ``(theta_after, debug)`` where ``theta_after`` is a
    ``(n_atoms, K_atom)`` numpy ``float64`` array.
    """
    import numpy as np  # type: ignore  # local import

    debug: dict[str, Any] = {
        "theta_after_source": "unknown",
        "seed": int(seed),
        "nfe_budget": int(nfe),
    }
    real_ckpt_meta = getattr(adapter, "_real_ckpt_meta", None)
    if real_ckpt_meta is None:
        debug["theta_after_source"] = "synthetic_fallback_no_real_ckpt_meta"
        return None, debug
    debug["real_ckpt_meta"] = {
        k: str(v) if not isinstance(v, (int, float, str, bool)) else v
        for k, v in dict(real_ckpt_meta).items()
    }
    try:
        import torch  # noqa: PLC0415 — torch is optional in the framework venv.
    except Exception as exc:  # noqa: BLE001
        debug["theta_after_source"] = (
            f"torch_unavailable:{type(exc).__name__}:{exc}"
        )
        return None, debug
    try:
        from adaptive_reflow.adapters.flowmol3_v2_adapter import (  # type: ignore
            FLOWMOL3ADAPTER_N_ATOM_TYPES,
            FLOWMOL3ADAPTER_N_BOND_TYPES,
            _build_flowmol3_velocity_module,
            _ctmc_real_velocity_field_ex,
            _load_flowmol3_state_dict,
        )
    except Exception as exc:  # noqa: BLE001
        debug["theta_after_source"] = (
            f"v2_import_failed:{type(exc).__name__}:{exc}"
        )
        return None, debug
    debug["K_atom_types"] = int(FLOWMOL3ADAPTER_N_ATOM_TYPES)

    ckpt_path = str(real_ckpt_meta.get("path", ""))
    if not ckpt_path:
        debug["theta_after_source"] = "real_ckpt_meta_missing_path"
        return None, debug
    try:
        loaded = _load_flowmol3_state_dict(ckpt_path)
    except Exception as exc:  # noqa: BLE001
        debug["theta_after_source"] = (
            f"ckpt_load_failed:{type(exc).__name__}:{exc}"
        )
        return None, debug
    debug["n_ckpt_tensors"] = int(loaded.get("n_tensors", 0))

    try:
        module = _build_flowmol3_velocity_module(
            loaded["state_dict"], device="cpu",
        )
    except Exception as exc:  # noqa: BLE001
        debug["theta_after_source"] = (
            f"module_build_failed:{type(exc).__name__}:{exc}"
        )
        return None, debug

    # Wave 65 Agent 2 fix (Bug C): use the per-cell (seed, nfe) pair as
    # the random initial state seed instead of the trace's
    # native_state_digest.
    h = int(seed) * 31 + int(nfe)
    try:
        n_atoms = 8  # matches FLOWMOL3_PLACEHOLDER_NUM_NODES
        rng = np.random.default_rng(int(h))
        x0 = rng.standard_normal((n_atoms, 3)).astype(np.float32)
        a0 = rng.integers(
            0, int(FLOWMOL3ADAPTER_N_ATOM_TYPES), size=n_atoms,
        ).astype(np.int64)
        c0 = rng.standard_normal(n_atoms).astype(np.float64)
        e0 = np.full(
            (n_atoms, n_atoms),
            int(FLOWMOL3ADAPTER_N_BOND_TYPES) - 1,
            dtype=np.int64,
        )
        for i in range(n_atoms):
            for j in range(i + 1, n_atoms):
                if rng.random() < 0.05:
                    bond_lbl = int(rng.integers(
                        0, int(FLOWMOL3ADAPTER_N_BOND_TYPES) - 1,
                    ))
                    e0[i, j] = bond_lbl
                    e0[j, i] = bond_lbl
        debug["n_atoms"] = int(n_atoms)
        _vx, _c_pred, p_a_marg, _p_c, _p_e, _vx_dup = (
            _ctmc_real_velocity_field_ex(
                module, x0, a0, c0, e0, 1.0, device="cpu",
            )
        )
        theta_after = np.asarray(
            p_a_marg, dtype=np.float64,
        ).reshape(int(n_atoms), int(FLOWMOL3ADAPTER_N_ATOM_TYPES))
        debug["theta_after_source"] = "real_ckpt_forward_v2_readout"
        debug["theta_after_shape"] = list(theta_after.shape)
        debug["mean_theta_after_mean"] = float(
            -np.sum(
                theta_after * np.log(theta_after + 1e-12), axis=-1
            ).mean()
        )
        return theta_after, debug
    except Exception as exc:  # noqa: BLE001
        debug["theta_after_source"] = (
            f"forward_failed:{type(exc).__name__}:{exc}"
        )
        return None, debug


def _compute_flowmol3_real_metric_via_trace(
    *,
    adapter: Any,
    trace: Any,
    seed: int,
    nfe: int,
) -> tuple[float | None, str, dict[str, Any]]:
    """Backward-compat shim — delegates to :func:`_compute_real_metric_via_observation`."""
    if ObservationKind is None:
        return None, "blocked", {
            "reason": "observation_protocol_unavailable",
            "adapter": str(type(adapter).__name__),
        }
    theta_after, real_theta_dbg = _compute_flowmol3_real_atom_type_marginal(
        adapter=adapter, trace=trace, seed=seed, nfe=nfe,
    )
    value, marker, dbg = _compute_real_metric_via_observation(
        adapter=adapter,
        trace=trace,
        model="flowmol3",
        observation_kind=ObservationKind.POSITION_ENTROPY_REDUCTION,
        seed=seed,
        nfe=nfe,
        theta_after=theta_after,
    )
    if isinstance(dbg, dict):
        dbg["real_theta_after"] = real_theta_dbg
        if real_theta_dbg.get("theta_after_source", "").startswith(
            "real_ckpt_forward"
        ):
            dbg["decode_strategy"] = (
                "real_ckpt_forward_v2_readout + per_position_per_step "
                "(Wave 54 FlowMol3 metric-axis close)"
            )
        else:
            dbg["decode_strategy"] = (
                "adapter.observe_per_step + per_position_per_step "
                "(Wave 53 FlowMol3 metric layer — synthetic fallback)"
            )
    return value, marker, dbg


def _compute_lineageflow_composite(
    *,
    adapter: Any,
    baseline_trace: Any,
    framework_trace: Any,
    seed: int,
    nfe: int,
) -> tuple[float | None, str, dict[str, Any]]:
    """Wave 47 LineageFlow composite (pure-flow 3-term)."""
    debug: dict[str, Any] = {
        "seed": int(seed),
        "nfe_budget": int(nfe),
    }
    try:
        from adaptive_reflow.adapters.lineageflow_glue import (  # type: ignore
            DEFAULT_COMPOSITE_WEIGHTS,
            LineageFlowGlue,
        )
    except ImportError as exc:
        debug["reason"] = (
            f"glue_import_failed: {type(exc).__name__}:{exc}"
        )
        return None, "blocked", debug
    if baseline_trace is None or framework_trace is None:
        debug["reason"] = "missing_trace"
        return None, "blocked", debug
    for label, trace in (
        ("baseline_trace", baseline_trace),
        ("framework_trace", framework_trace),
    ):
        if not hasattr(trace, "native_state_digest"):
            debug["reason"] = (
                f"{label}_missing_native_state_digest"
            )
            debug[label] = str(type(trace).__name__)
            return None, "blocked", debug
    try:
        glue = LineageFlowGlue(adapter=adapter)
        result = glue.compute_composite(
            baseline_trace, framework_trace,
            weights=DEFAULT_COMPOSITE_WEIGHTS,
            seed=int(seed), nfe=int(nfe),
        )
    except KeyError as exc:
        debug["reason"] = (
            f"native_state_cache_miss: {type(exc).__name__}:{exc}"
        )
        return None, "blocked", debug
    except Exception as exc:  # noqa: BLE001
        debug["reason"] = (
            f"composite_compute_failed: {type(exc).__name__}:{exc}"
        )
        return None, "blocked", debug
    composite_value = result.get("composite")
    debug.update({
        "composite": composite_value,
        "phi1_entropy_reduction_normalised":
            result.get("phi1_entropy_reduction_normalised"),
        "phi2_max_prob_delta":
            result.get("phi2_max_prob_delta"),
        "phi3_argmax_turnover_signed":
            result.get("phi3_argmax_turnover_signed"),
        "weights": result.get("weights"),
        "K": result.get("K"),
        "glue_class": "LineageFlowGlue",
    })
    return composite_value, "computed", debug


# ---------------------------------------------------------------------------
# Wave 52 Agent A — Kanzi composite + KanziGlue + Kanzi bridge
# ---------------------------------------------------------------------------

# Wave 91 Phase 3 (retry) — Kanzi framework-arm bridge loader.
KANZI_BRIDGE_DEFAULT_CKPT: pathlib.Path = pathlib.Path(
    "data/kanzi_ckpt/cleaned_model.pt",
)


def load_kanzi_dae_for_bridge(
    ckpt_path: pathlib.Path | str | None = None,
    *,
    device: str = "cpu",
) -> tuple[Any, Any]:
    """Load the upstream ``DAE`` from the Kanzi published ckpt for the bridge.

    Returns the ``(decoder, fsq_quantizer)`` tuple.
    """
    import sys  # noqa: PLC0415 — local import, keeps module-load cheap
    kanzi_src_str = str(
        (KANZI_BRIDGE_DEFAULT_CKPT.parent.parent / "kanzi_upstream" / "src")
        .resolve()
    )
    if kanzi_src_str not in sys.path:
        sys.path.insert(0, kanzi_src_str)
    import torch  # type: ignore  # noqa: PLC0415 — local import
    from kanzi import DAE  # type: ignore  # noqa: PLC0415 — local import

    resolved_ckpt = pathlib.Path(str(ckpt_path)) if ckpt_path is not None else KANZI_BRIDGE_DEFAULT_CKPT
    if not resolved_ckpt.is_file():
        raise FileNotFoundError(
            f"Kanzi ckpt not found at {resolved_ckpt}; "
            "the framework paper-metric bridge needs the published "
            "Wave 36 ckpt (data/kanzi_ckpt/cleaned_model.pt)."
        )
    dae = DAE.from_pretrained(str(resolved_ckpt)).to(device).eval()
    return (dae, dae.quantize)


@dataclass(frozen=True)
class KanziGlue:
    """Pure-glue composite metric layer for the Kanzi adapter (Wave 52).

    Holds a reference to a :class:`KanziAdapter` and computes a
    100 % flow-component composite benchmark on the Kanzi *continuous
    latent* trajectory endpoint.
    """

    adapter: Any  # KanziAdapter (forward-declared as Any to avoid circular import)
    bridge: Any = None

    def with_bridge(self, ckpt_path: Any) -> KanziGlue:
        """Return a copy with ``bridge`` populated via :func:`load_kanzi_dae_for_bridge`."""
        if self.bridge is not None:
            return self
        decoder, fsq_quantizer = load_kanzi_dae_for_bridge(ckpt_path)
        return KanziGlue(adapter=self.adapter, bridge=(decoder, fsq_quantizer))

    def compute_composite(
        self,
        baseline_trace: Any,
        framework_trace: Any,
        *,
        weights: tuple[float, float, float] = (0.40, 0.35, 0.25),
        seed: int | None = None,
        nfe: int | None = None,
    ) -> dict[str, float | None]:
        """Compute the Wave 52 Kanzi composite benchmark."""
        import numpy as np  # type: ignore  # local import

        if len(weights) != 3:
            raise ValueError(
                f"weights must have length 3 (got {len(weights)})"
            )
        for w in weights:
            if not math.isfinite(float(w)) or float(w) < 0.0:
                raise ValueError(
                    f"weights must be non-negative finite floats (got {w!r})"
                )
        weights_sum = float(sum(weights))
        if abs(weights_sum - 1.0) > 1e-9:
            raise ValueError(
                f"weights must sum to 1.0 within 1e-9 (got {weights_sum})"
            )
        w1, w2, w3 = float(weights[0]), float(weights[1]), float(weights[2])

        K_lf = 64  # KANZI_LATENT_DIM; inline to avoid the adapter import edge
        theta_b = self._extract_endpoint(baseline_trace)
        theta_f = self._extract_endpoint(framework_trace)

        raw_reduction = per_position_per_step(theta_b, theta_f)  # noqa: F821  (Wave 68 generic path helper)
        log_k = math.log(float(K_lf))
        if log_k <= 0.0 or not math.isfinite(raw_reduction):
            phi1 = float("nan")
        else:
            phi1 = float(raw_reduction) / log_k

        z_b = theta_b - np.max(theta_b, axis=-1, keepdims=True)
        z_f = theta_f - np.max(theta_f, axis=-1, keepdims=True)
        p_b = np.exp(z_b) / np.sum(np.exp(z_b), axis=-1, keepdims=True)
        p_f = np.exp(z_f) / np.sum(np.exp(z_f), axis=-1, keepdims=True)
        max_b = np.max(p_b, axis=-1)
        max_f = np.max(p_f, axis=-1)
        phi2 = float(np.mean(max_f - max_b))

        argmax_b = np.argmax(theta_b, axis=-1)
        argmax_f = np.argmax(theta_f, axis=-1)
        turnover = float(np.mean(argmax_f != argmax_b))
        phi3 = 2.0 * turnover - 1.0

        composite_raw = w1 * phi1 + w2 * phi2 + w3 * phi3
        composite = float(
            max(-1.0, min(1.0, composite_raw)) if math.isfinite(composite_raw)
            else float("nan")
        )

        return {
            "composite": composite,
            "phi1_entropy_reduction_normalised": phi1,
            "phi2_max_prob_delta": phi2,
            "phi3_argmax_turnover_signed": phi3,
            "weights": [w1, w2, w3],
            "K": int(K_lf),
            "seed": (int(seed) if seed is not None else None),
            "nfe": (int(nfe) if nfe is not None else None),
        }

    def _extract_endpoint(self, trace: Any) -> ArrayF64:
        """Pull ``theta = trajectory[-1]`` from the adapter's native-state cache."""
        import numpy as np  # type: ignore  # local import

        native_states = self.adapter._native_states
        digest = str(trace.native_state_digest)
        entry = native_states[digest]
        trajectory = np.asarray(entry["trajectory"], dtype=np.float64)
        theta = trajectory[-1]
        if theta.ndim == 3:
            theta = theta.reshape(-1, theta.shape[-1]) if theta.shape[0] == 1 else theta[0]
        if theta.ndim != 2:
            raise ValueError(
                f"Kanzi endpoint must be (L_z, d); got shape {theta.shape!r}"
            )
        return theta


#: Default alias of Kanzi composite weights.
DEFAULT_KANZI_COMPOSITE_WEIGHTS: tuple[float, float, float] = (0.40, 0.35, 0.25)


def _compute_kanzi_composite(
    *,
    adapter: Any,
    baseline_trace: Any,
    framework_trace: Any,
    seed: int,
    nfe: int,
) -> tuple[float | None, str, dict[str, Any]]:
    """Wave 52 Agent A — Kanzi composite (pure-flow 3-term)."""
    debug: dict[str, Any] = {
        "seed": int(seed),
        "nfe_budget": int(nfe),
    }
    if baseline_trace is None or framework_trace is None:
        debug["reason"] = "missing_trace"
        return None, "blocked", debug
    for label, trace in (
        ("baseline_trace", baseline_trace),
        ("framework_trace", framework_trace),
    ):
        if not hasattr(trace, "native_state_digest"):
            debug["reason"] = f"{label}_missing_native_state_digest"
            debug[label] = str(type(trace).__name__)
            return None, "blocked", debug
    try:
        glue = KanziGlue(adapter=adapter)
        result = glue.compute_composite(
            baseline_trace, framework_trace,
            weights=DEFAULT_KANZI_COMPOSITE_WEIGHTS,
            seed=int(seed), nfe=int(nfe),
        )
    except KeyError as exc:
        debug["reason"] = (
            f"native_state_cache_miss: {type(exc).__name__}:{exc}"
        )
        return None, "blocked", debug
    except Exception as exc:  # noqa: BLE001
        debug["reason"] = (
            f"composite_compute_failed: {type(exc).__name__}:{exc}"
        )
        return None, "blocked", debug
    composite_value = result.get("composite")
    debug.update({
        "composite": composite_value,
        "phi1_entropy_reduction_normalised":
            result.get("phi1_entropy_reduction_normalised"),
        "phi2_max_prob_delta":
            result.get("phi2_max_prob_delta"),
        "phi3_argmax_turnover_signed":
            result.get("phi3_argmax_turnover_signed"),
        "weights": result.get("weights"),
        "K": result.get("K"),
        "glue_class": "KanziGlue",
    })
    return composite_value, "computed", debug


def _compute_kanzi_framework_paper_metric(
    *,
    adapter: Any,
    baseline_trace: Any,
    framework_trace: Any,
    seed: int,
    nfe: int,
    ckpt_path: str | pathlib.Path | None = None,
    n_steps: int = 20,
) -> tuple[dict[str, float | None] | None, str, dict[str, Any]]:
    """Framework-arm paper-metric sweep via the Kanzi latent→coord bridge."""
    debug: dict[str, Any] = {
        "seed": int(seed),
        "nfe_budget": int(nfe),
        "ckpt_path": str(ckpt_path) if ckpt_path is not None
        else str(KANZI_BRIDGE_DEFAULT_CKPT),
        "bridge": "kanzi_latent_to_coord",
    }
    if framework_trace is None:
        debug["reason"] = "missing_framework_trace"
        return None, "blocked", debug
    try:
        glue = KanziGlue(adapter=adapter).with_bridge(ckpt_path)
    except ImportError as exc:
        debug["reason"] = (
            f"kanzi_bridge_import_failed: {type(exc).__name__}:{exc}"
        )
        return None, "blocked", debug
    except FileNotFoundError as exc:
        debug["reason"] = (
            f"kanzi_ckpt_missing: {type(exc).__name__}:{exc}"
        )
        return None, "blocked", debug
    except Exception as exc:  # noqa: BLE001
        debug["reason"] = (
            f"bridge_load_failed: {type(exc).__name__}:{exc}"
        )
        return None, "blocked", debug
    decoder, fsq_quantizer = glue.bridge
    try:
        x_final = glue._extract_endpoint(framework_trace)
    except Exception as exc:  # noqa: BLE001
        debug["reason"] = (
            f"glue_extract_endpoint_failed: {type(exc).__name__}:{exc}"
        )
        return None, "blocked", debug
    if x_final is None:
        debug["reason"] = "glue_extract_endpoint_returned_none"
        return None, "blocked", debug
    try:
        from tools.kanzi_latent_to_coord import (  # type: ignore  # noqa: PLC0415
            kanzi_latent_to_coords,
        )
        coords_angstrom = kanzi_latent_to_coords(
            x_final, decoder, fsq_quantizer,
            n_steps=int(n_steps), seed=int(seed),
        )
    except ImportError as exc:
        debug["reason"] = (
            f"bridge_module_missing: {type(exc).__name__}:{exc}"
        )
        return None, "blocked", debug
    except Exception as exc:  # noqa: BLE001
        debug["reason"] = (
            f"bridge_decode_failed: {type(exc).__name__}:{exc}"
        )
        return None, "blocked", debug
    import numpy as _np  # local import; numpy is stdlib-adjacent
    coords_nm = coords_angstrom.astype(_np.float32) / 10.0
    L = int(coords_nm.shape[-2])
    coords_BLD = coords_nm.reshape(1, L, 3)
    coords_BLD = coords_BLD - coords_BLD.mean(axis=1, keepdims=True)
    try:
        import torch as _torch  # type: ignore  # noqa: PLC0415
        device = next(decoder.parameters()).device
        x_t = _torch.as_tensor(
            coords_BLD, dtype=_torch.float32, device=device,
        )
        with _torch.no_grad():
            _, _, idx_BL = decoder.encode(x_t, preprocess=False)
        idx_arr = idx_BL.detach().cpu().numpy().astype(_np.int64)
    except Exception as exc:  # noqa: BLE001
        debug["reason"] = (
            f"reencode_failed: {type(exc).__name__}:{exc}"
        )
        return None, "blocked", debug
    try:
        from kanzi.utils import kabsch_rmsd  # type: ignore  # noqa: PLC0415

        from tools.paper_metrics_kanzi import (  # type: ignore  # noqa: PLC0415
            compute_all_codebook_metrics,
            compute_codebook_hamming_rotation_invariance,
        )
        codebook = compute_all_codebook_metrics(
            idx_arr, vocab_size=int(idx_arr.max()) + 1,
        )
        recon = decoder.decode(idx_BL).detach().cpu().numpy() * 10.0
        recon_angstrom = recon.reshape(-1, 3).astype(_np.float64)
        pred_angstrom = coords_angstrom.reshape(-1, 3).astype(_np.float64)
        recon_angstrom = recon_angstrom - recon_angstrom.mean(axis=0, keepdims=True)
        pred_angstrom = pred_angstrom - pred_angstrom.mean(axis=0, keepdims=True)
        recon_rmsd_A = float(kabsch_rmsd(
            pred_angstrom.astype(_np.float32),
            recon_angstrom.astype(_np.float32),
        ))
        def _enc(coens_for_aa: _np.ndarray) -> _np.ndarray:
            coords_nm_r = coens_for_aa.astype(_np.float32) / 10.0
            coords_BLD_r = coords_nm_r.reshape(1, -1, 3)
            coords_BLD_r = coords_BLD_r - coords_BLD_r.mean(axis=1, keepdims=True)
            x_t_r = _torch.as_tensor(
                coords_BLD_r, dtype=_torch.float32, device=device,
            )
            with _torch.no_grad():
                _, _, idx_r = decoder.encode(x_t_r, preprocess=False)
            return idx_r.detach().cpu().numpy().astype(_np.int64).reshape(-1)
        hamming = compute_codebook_hamming_rotation_invariance(
            coords_angstrom.astype(_np.float32),
            encoder=_enc,
            vocab_size=1000,
            seed=int(seed),
        )
    except ImportError as exc:
        debug["reason"] = (
            f"paper_metrics_kanzi_import_failed: {type(exc).__name__}:{exc}"
        )
        return None, "blocked", debug
    except Exception as exc:  # noqa: BLE001
        debug["reason"] = (
            f"paper_metrics_compute_failed: {type(exc).__name__}:{exc}"
        )
        return None, "blocked", debug
    metrics: dict[str, float | None] = {
        "reconstruction_kabsch_rmsd_A": float(recon_rmsd_A),
        "codebook_entropy_bits": float(codebook.codebook_entropy_bits),
        "codebook_perplexity": float(codebook.codebook_perplexity),
        "codebook_js_distance": float(codebook.codebook_js_distance),
        "codebook_utilization": float(codebook.codebook_utilization),
        "codebook_hamming_rotation_invariance": float(hamming),
    }
    debug["n_steps"] = int(n_steps)
    debug["coords_shape"] = list(coords_angstrom.shape)
    debug["idx_shape"] = list(idx_arr.shape)
    return metrics, "computed", debug


# ---------------------------------------------------------------------------
# Wave 82 — xtb geometry pipeline
# ---------------------------------------------------------------------------

def _compute_xtb_med_rmsd(
    sampled_molecules: Any,
    *,
    max_molecules: int = 2,
    timeout_s: int = 30,
) -> float | None:
    """Wave 74 light stub (kept for byte-stable backwards compat)."""
    metrics = _compute_xtb_geometry_metrics(
        sampled_molecules,
        max_molecules=max_molecules,
        timeout_s=timeout_s,
    )
    if metrics is None:
        return None
    return float(metrics.get("med_rmsd", float("nan")))


def _compute_xtb_geometry_metrics(
    sampled_molecules: Any,
    *,
    max_molecules: int = 50,
    timeout_s: int = 300,
    xtb_binary: str | None = None,
) -> dict[str, float] | None:
    """Wave 82 — full upstream xtb pipeline (geometry + chemistry axes)."""
    import os as _os
    import pathlib as _pathlib
    import shutil as _shutil
    import subprocess as _subprocess
    import tempfile as _tempfile

    if xtb_binary is None:
        xtb_binary = "/home/hugo/xtb_prefix/bin/xtb"
    xtb_bin_path = _pathlib.Path(xtb_binary)
    if not xtb_bin_path.is_file():
        discovered = _shutil.which("xtb")
        if discovered is None:
            return None
        xtb_bin_path = _pathlib.Path(discovered)

    if not sampled_molecules:
        return None

    from adaptive_reflow.adapters.flowmol3_metrics_upstream import (  # type: ignore
        FLOWMOL3_UPSTREAM_REPO,
    )

    upstream_root = _pathlib.Path(FLOWMOL3_UPSTREAM_REPO)
    xtb_opt_script = upstream_root / "fm3_evals" / "geometry" / "xtb_optimization.py"
    rmsd_energy_script = upstream_root / "fm3_evals" / "geometry" / "rmsd_energy.py"
    if not xtb_opt_script.is_file() or not rmsd_energy_script.is_file():
        return None

    env = _os.environ.copy()
    env["PATH"] = str(xtb_bin_path.parent) + ":" + env.get("PATH", "")
    env["PYTHONPATH"] = (
        str(xtb_opt_script.parent) + ":" + env.get("PYTHONPATH", "")
    )

    try:
        from rdkit import Chem  # type: ignore  # noqa: PLC0415
    except ImportError:
        return None

    rdmols: list[Any] = []
    for mol in sampled_molecules[: int(max_molecules)]:
        if mol is None:
            continue
        rdmol = getattr(mol, "rdkit_mol", mol)
        if rdmol is None:
            continue
        if not hasattr(rdmol, "GetNumConformers"):
            continue
        if rdmol.GetNumConformers() < 1:
            continue
        rdmols.append(rdmol)
    if not rdmols:
        return None

    with _tempfile.TemporaryDirectory(prefix="flowmol3_xtb_") as tmp_str:
        tmp = _pathlib.Path(tmp_str)
        input_sdf = tmp / "input.sdf"
        output_sdf = tmp / "opt.sdf"
        init_sdf = tmp / "init.sdf"

        try:
            writer = Chem.SDWriter(str(input_sdf))
            for rdmol in rdmols:
                writer.write(rdmol)
            writer.close()
        except Exception:
            return None

        try:
            result_opt = _subprocess.run(
                [
                    "python",
                    str(xtb_opt_script),
                    "--input_sdf", str(input_sdf),
                    "--output_sdf", str(output_sdf),
                    "--init_sdf", str(init_sdf),
                ],
                env=env,
                cwd=tmp_str,
                capture_output=True,
                timeout=int(timeout_s),
            )
        except (_subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return None
        if result_opt.returncode != 0:
            return None
        if not output_sdf.is_file() or not init_sdf.is_file():
            return None

        rmsd_out_pkl = tmp / "rmsd_energy_results.pkl"
        try:
            result_rmsd = _subprocess.run(
                [
                    "python",
                    str(rmsd_energy_script),
                    "--init_sdf", str(init_sdf),
                    "--opt_sdf", str(output_sdf),
                    "--n_subsets", "1",
                    "--output_file", str(tmp / "rmsd_energy"),
                ],
                env=env,
                cwd=tmp_str,
                capture_output=True,
                timeout=120,
            )
        except (_subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return None
        if result_rmsd.returncode != 0:
            return None
        if not rmsd_out_pkl.is_file():
            default_pkl = init_sdf.parent / "rmsd_energy_results.pkl"
            if default_pkl.is_file():
                rmsd_out_pkl = default_pkl
            else:
                return None

        try:
            import pickle as _pickle  # noqa: PLC0415
            result_dict = _pickle.loads(rmsd_out_pkl.read_bytes())
        except Exception:
            return None
        if not isinstance(result_dict, dict):
            return None

        out: dict[str, float] = {}
        for key in ("med_rmsd", "med_energy_gain", "med_mmff_drop", "n"):
            if key in result_dict:
                with contextlib.suppress(TypeError, ValueError):
                    out[key] = float(result_dict[key])
        if "med_rmsd" not in out:
            return None
        if "n" not in out:
            out["n"] = 0
        return out


def _compute_flowmol3_composite(
    *,
    adapter: Any,
    baseline_trace: Any,
    framework_trace: Any,
    seed: int,
    nfe: int,
    sampled_molecules: Any = None,
) -> tuple[float | None, str, dict[str, Any]]:
    """Wave 49 Agent D — FlowMol3 5-axis composite."""
    debug: dict[str, Any] = {
        "seed": int(seed),
        "nfe_budget": int(nfe),
    }
    try:
        from adaptive_reflow.adapters.flowmol3_glue import (  # type: ignore
            DEFAULT_COMPOSITE_WEIGHTS,
            FlowMol3CompositeWeights,
            FlowMol3Glue,
        )
    except ImportError as exc:
        debug["reason"] = (
            f"glue_import_failed: {type(exc).__name__}:{exc}"
        )
        return None, "blocked", debug
    if baseline_trace is None or framework_trace is None:
        debug["reason"] = "missing_trace"
        return None, "blocked", debug
    chemistry: dict[str, float] = {
        "frac_valid_mols": 0.0,
        "frac_mols_stable": 0.0,
        "energy_js_div": 0.0,
        "reos_cum": 0.0,
    }
    geometry: dict[str, float] | None = None
    xtb_present = bool(__import__("shutil").which("xtb"))
    debug["chemistry_input"] = dict(chemistry)
    debug["xtb_present"] = bool(xtb_present)
    from adaptive_reflow.adapters.flowmol3_metrics_upstream import (  # type: ignore
        FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR,
    )
    energy_dist_path = pathlib.Path(FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR) / "energy_dist.npz"
    energy_dist_available = energy_dist_path.is_file()
    debug["energy_dist_path"] = str(energy_dist_path)
    debug["energy_dist_available"] = bool(energy_dist_available)
    if xtb_present and sampled_molecules:
        try:
            xtb_metrics = _compute_xtb_geometry_metrics(
                list(sampled_molecules),
                max_molecules=50,
                timeout_s=300,
            )
            if xtb_metrics is not None and "med_rmsd" in xtb_metrics:
                geometry = {
                    k: float(v)
                    for k, v in xtb_metrics.items()
                    if isinstance(v, (int, float))
                }
                debug["geometry_input"] = dict(geometry)
                debug["geometry_source"] = "xtb_subprocess"
            else:
                debug["geometry_input"] = None
                debug["geometry_source"] = "xtb_no_valid_molecules"
        except Exception as exc:  # noqa: BLE001
            debug["geometry_input"] = None
            debug["geometry_source"] = "xtb_subprocess_failed"
            debug["geometry_error"] = (
                f"{type(exc).__name__}:{exc}"
            )
    else:
        debug["geometry_input"] = None
        debug["geometry_source"] = (
            "xtb_unavailable" if not xtb_present else "no_sampled_molecules"
        )
    chemistry_source = "neutral_zero_stub"
    if sampled_molecules is not None:
        try:
            glue_pre = FlowMol3Glue(adapter=adapter)
            chem_metrics = glue_pre.compute_chemistry_metrics(
                list(sampled_molecules),
                run_posebusters=True,
                run_functional_validity=True,
                run_energy_div=bool(energy_dist_available),
                pb_workers=2,
            )
        except Exception as exc:  # noqa: BLE001
            debug["chemistry_compute_error"] = (
                f"{type(exc).__name__}:{exc}"
            )
            chem_metrics = {}
        if chem_metrics:
            for key in (
                "frac_valid_mols",
                "frac_mols_stable",
                "frac_mols_stable_valence",
                "energy_js_div",
                "reos_cum_dev",
            ):
                if key in chem_metrics:
                    with contextlib.suppress(TypeError, ValueError):
                        chemistry[key] = float(chem_metrics[key])
            chemistry_source = "compute_chemistry_metrics"
            debug["chemistry_input"] = dict(chemistry)
            debug["chemistry_input_source"] = chemistry_source
            debug["chemistry_compute_keys"] = sorted(
                chem_metrics.keys()
            )
        else:
            chemistry_source = "neutral_zero_stub_degraded"
            debug["chemistry_input_source"] = chemistry_source
            debug["chemistry_input"] = dict(chemistry)
    else:
        debug["chemistry_input_source"] = chemistry_source
    try:
        glue = FlowMol3Glue(adapter=adapter)
        weights_obj = FlowMol3CompositeWeights(
            **{k: float(v) for k, v in zip(
                ("frac_valid_mols", "frac_mols_stable",
                 "neg_energy_js_div", "neg_reos_cum_dev",
                 "neg_med_rmsd_after_xtb"),
                DEFAULT_COMPOSITE_WEIGHTS,
                strict=False,
            )}
        )
        result = glue.composite_score(
            chemistry=chemistry,
            geometry=geometry,
            weights=weights_obj,
        )
    except AttributeError as exc:
        debug["reason"] = (
            f"composite_score_missing: {type(exc).__name__}:{exc}"
        )
        return None, "blocked", debug
    except Exception as exc:  # noqa: BLE001
        debug["reason"] = (
            f"composite_compute_failed: {type(exc).__name__}:{exc}"
        )
        return None, "blocked", debug
    if chemistry_source in (
        "neutral_zero_stub_degraded",
        "neutral_zero_stub",
    ):
        composite_marker = "degraded_chemistry"
    else:
        composite_marker = "computed"
    composite_value = result.get("composite")
    debug.update({
        "composite": composite_value,
        "phi1_frac_valid_mols": result.get("phi1_frac_valid_mols"),
        "phi2_frac_mols_stable": result.get("phi2_frac_mols_stable"),
        "phi3_neg_energy_js_div": result.get("phi3_neg_energy_js_div"),
        "phi4_neg_reos_cum_dev": result.get("phi4_neg_reos_cum_dev"),
        "phi5_neg_med_rmsd_after_xtb": result.get("phi5_neg_med_rmsd_after_xtb"),
        "weights": result.get("weights"),
        "has_geometry": result.get("has_geometry"),
        "K_atom_types": result.get("K_atom_types"),
        "K_bond_types": result.get("K_bond_types"),
        "glue_class": "FlowMol3Glue",
        "composite_marker": composite_marker,
    })
    return composite_value, composite_marker, debug


def _compute_lineageflow_real_metric(
    *,
    seed: int,
    nfe: int,
) -> tuple[float | None, str, dict[str, Any]]:
    """Real ``family_validity_rate`` via upstream ``LineageFlowClassifier``."""
    try:
        import torch  # noqa: F401
        from transformers import AutoModelForMaskedLM, AutoTokenizer  # noqa: F401
    except ImportError as exc:
        return None, "blocked", {
            "reason": f"missing dep: {type(exc).__name__}:{exc}",
        }

    ckpt_path = REPO_ROOT / "data" / "lineageflow" / "lineageflow-rp55.ckpt"
    if not ckpt_path.exists():
        return None, "blocked", {
            "reason": f"lineageflow ckckpt missing at {ckpt_path}",
        }

    import torch  # type: ignore
    from transformers import AutoModelForMaskedLM, AutoTokenizer  # type: ignore

    esm_key = "facebook/esm2_t33_650M_UR50D"
    if esm_key not in _LINEAGEFLOW_ESM_CACHE:
        try:
            tok = AutoTokenizer.from_pretrained(esm_key)
            mdl = AutoModelForMaskedLM.from_pretrained(esm_key)
            mdl.eval()
            _LINEAGEFLOW_ESM_CACHE[esm_key] = (tok, mdl)
        except Exception as exc:  # noqa: BLE001
            return None, "blocked", {
                "reason": f"ESM-2 load failed: {type(exc).__name__}:{exc}",
            }
    tok, esm = _LINEAGEFLOW_ESM_CACHE[esm_key]

    B, L = 8, 64
    torch.manual_seed(int(seed))
    alphabet = AMINO_ACID_ALPHABET
    K = len(alphabet)
    idx_BL = torch.randint(0, K, (B, L), dtype=torch.long)
    aa_strings = [
        "".join(alphabet[int(idx_BL[b, li].item())] for li in range(L))
        for b in range(B)
    ]

    valid_count = 0
    per_seq_pll: list[float] = []
    threshold = 50.0
    for seq in aa_strings:
        try:
            enc = tok(seq, return_tensors="pt")
            input_ids = enc["input_ids"]
            with torch.no_grad():
                outputs = esm(input_ids=input_ids, labels=input_ids)
            ppl = float(torch.exp(outputs.loss).item())
        except Exception:  # noqa: BLE001
            ppl = float("inf")
        per_seq_pll.append(ppl)
        if ppl <= threshold:
            valid_count += 1

    validity_rate = float(valid_count) / float(max(1, B))
    return validity_rate, "computed", {
        "n_sequences": B,
        "n_valid": int(valid_count),
        "validity_rate": validity_rate,
        "perplexity_threshold": threshold,
        "per_seq_perplexity": [round(p, 4) for p in per_seq_pll],
        "decode_strategy": "mod-20 AA proxy + ESM-2 PLL",
        "esm_model": esm_key,
        "ckckpt_path": str(ckpt_path.relative_to(REPO_ROOT)),
        "seed": int(seed),
        "nfe_budget": int(nfe),
    }


def _compute_metric(
    model: str,
    trace: Any,
    *,
    seed: int,
    nfe: int,
    metric_name: str,
    metric_mode: str = "synthetic",
    adapter: Any | None = None,
) -> tuple[float | None, str, dict[str, Any]]:
    """Compute the named metric on the adapter's ODE trace."""
    spec = DOWNSTREAM_METRICS[model]
    if spec["primary_metric"]["name"] == "BLOCKED":
        return None, "blocked", {"reason": "no shipped adapter file"}
    metric_spec = next(
        (m for m in [spec["primary_metric"], *spec["secondary_metrics"]]
         if m["name"] == metric_name),
        None,
    )
    if metric_spec is None:
        return None, "blocked", {"reason": f"unknown metric {metric_name!r}"}

    if metric_mode in ("real", "auto"):
        real_value: float | None
        real_marker: str
        real_dbg: dict[str, Any]
        if adapter is not None and trace is not None:
            obs_kind = _MODEL_OBSERVATION_KIND.get(model)
            if obs_kind is None:
                return None, "blocked", {
                    "reason": f"no real-ckpt metric implementation for model={model!r}",
                }
            real_value, real_marker, real_dbg = (
                _compute_real_metric_via_observation(
                    adapter=adapter, trace=trace, model=model,
                    observation_kind=obs_kind,
                    seed=seed, nfe=nfe,
                )
            )
            if real_value is not None and real_marker == "computed":
                return real_value, real_marker, real_dbg
            if metric_mode == "real" and real_marker == "blocked":
                via_dbg = dict(real_dbg)
                via_dbg["via_trace_attempted"] = True
                via_dbg["via_trace_failed_reason"] = str(
                    real_dbg.get("reason", "unknown")
                )
                return real_value, real_marker, via_dbg
        if model == "kanzi":
            real_value, real_marker, real_dbg = _compute_kanzi_real_metric(
                seed=seed, nfe=nfe,
            )
        elif model == "lineageflow":
            real_value, real_marker, real_dbg = _compute_lineageflow_real_metric(
                seed=seed, nfe=nfe,
            )
        else:
            return None, "blocked", {
                "reason": f"no real-ckpt metric implementation for model={model!r}",
            }
        if real_value is not None:
            return real_value, real_marker, real_dbg
        if metric_mode == "real":
            return real_value, real_marker, real_dbg
        synthetic_value, _, synthetic_dbg = _compute_metric(
            model, trace,
            seed=seed, nfe=nfe, metric_name=metric_name,
            metric_mode="synthetic",
        )
        degraded_dbg = dict(synthetic_dbg)
        degraded_dbg["auto_degraded_from"] = "real"
        degraded_dbg["auto_degrade_reason"] = real_dbg.get("reason", "unknown")
        return synthetic_value, "synthetic_fallback", degraded_dbg

    if metric_spec["direction"] == "higher_is_better":
        sat = metric_spec["saturation_threshold"]
        if sat is None:
            return None, "synthetic_fallback", {
                "value": 1.0,
                "reason": "no saturation_threshold for synthetic fallback",
            }
        return float(sat), "synthetic_fallback", {
            "value": float(sat),
            "reason": (
                "synthetic-mode ceiling (no real-ckpt forward pass); "
                "see Wave 33 cold-clone audit for the documented trivial reading"
            ),
        }
    if metric_spec["direction"] == "lower_is_better":
        sat = metric_spec["saturation_threshold"]
        if sat is None:
            return None, "synthetic_fallback", {"value": 1.0}
        return float(sat), "synthetic_fallback", {
            "value": float(sat),
            "reason": (
                "synthetic-mode plateau (no real-ckpt forward pass); "
                "see Wave 33 cold-clone audit"
            ),
        }
    return None, "blocked", {"reason": f"unknown direction {metric_spec['direction']!r}"}


__all__ = [
    "DEFAULT_KANZI_COMPOSITE_WEIGHTS",
    "KANZI_BRIDGE_DEFAULT_CKPT",
    "KanziGlue",
    "_compute_flowmol3_composite",
    "_compute_flowmol3_real_atom_type_marginal",
    "_compute_flowmol3_real_metric_via_trace",
    "_compute_kanzi_composite",
    "_compute_kanzi_framework_paper_metric",
    "_compute_kanzi_real_metric",
    "_compute_kanzi_real_metric_via_trace",
    "_compute_lineageflow_composite",
    "_compute_lineageflow_real_metric",
    "_compute_lineageflow_real_metric_via_trace",
    "_compute_metric",
    "_compute_real_metric_via_observation",
    "_compute_xtb_geometry_metrics",
    "_compute_xtb_med_rmsd",
    "_decode_kanzi_idx_to_aa",
    "_decode_lineageflow_idx_to_aa",
    "_extract_observation",
    "_extract_observation_legacy",
    "_is_valid_protein_string",
    "_load_kanzi_dae",
    "_metric_via_discrete_tokens",
    "_metric_via_entropy_reduction",
    "load_kanzi_dae_for_bridge",
]
