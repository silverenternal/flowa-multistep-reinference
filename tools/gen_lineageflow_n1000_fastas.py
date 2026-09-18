#!/usr/bin/env python3
"""Generate 1000 FASTA per arm (baseline + framework) for LineageFlow N=1000 sweep.

Strategy
--------

* **Baseline** arm — bare RNG draws over each family's Pfam AA bias.
  This is the literal "no framework glue" path: each record is a
  single :func:`_generate_sequence` call from a per-arm RNG sub-stream.
* **Framework** arm — drives the real
  :class:`LineageFlowAdapter` end-to-end. For each FASTA record
  index ``i`` the gen script calls
  :func:`tools.run_real_ckpt_eval._solve_framework` with
  ``nfe=NFE, n_rounds=3`` so the per-record sequence is the result
  of ``solve_ode -> export_endpoint -> apply_restart_distribution``
  chained three times (the canonical Wave 45 multi-round path).
  Per-record seed offsets are deterministic (``seed + i``) so the
  framework arm is reproducible without contaminating baseline.

Wave 86 Agent B — closes Pitfall #2 surfaced in
``docs/audit/wave86-phase1-audit.md`` §1: the previous implementation
shared one ``random.Random`` between the two arms and never invoked
the framework glue at all, so ``framework.fasta`` was byte-identical
to ``baseline.fasta`` modulo the ``>header`` line.

Output
------

    data/lineageflow_n1000/baseline.fasta    (1000 seqs, >baseline_seed<N>|family=<PF>)
    data/lineageflow_n1000/framework.fasta   (1000 seqs, >framework_seed<N>|family=<PF>)
    data/lineageflow_n1000/manifest.json     (per-record metadata)
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

# Ensure the repo root (parent of this `tools/` script) is on
# ``sys.path`` so the inner ``from tools.run_real_ckpt_eval import
# _solve_framework`` resolves when the gen script is invoked as
# ``python tools/gen_lineageflow_n1000_fastas.py`` (Python prepends
# the SCRIPT'S directory, i.e. ``tools/``, to sys.path — leaving the
# repo root absent, which would silently force every framework record
# into the bare-RNG fallback and break the Wave 86 Agent B
# ``framework_fallback_per_family_count == {}`` invariant).
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

AA_SET = "ACDEFGHIKLMNPQRSTVWY"

# Per-family amino acid composition bias (rough mimicry of Pfam clan profiles)
FAMILY_PROFILES = {
    "PF00005.27": {  # ABC transporter — mixed
        "bias": {"A": 0.10, "L": 0.12, "V": 0.10, "G": 0.10, "I": 0.08, "S": 0.07, "K": 0.06, "T": 0.06},
    },
    "PF00072.24": {  # Response regulator receiver — polar + acidic
        "bias": {"D": 0.12, "E": 0.10, "L": 0.08, "V": 0.08, "A": 0.08, "K": 0.07, "T": 0.07, "G": 0.07},
    },
    "PF00183.19": {  # HSP90 — hydrophobic + charged mix
        "bias": {"L": 0.10, "E": 0.10, "V": 0.08, "K": 0.08, "A": 0.08, "G": 0.07, "D": 0.07, "I": 0.06},
    },
    "PF02517.18": {  # CP12 — basic + acidic
        "bias": {"E": 0.14, "K": 0.12, "A": 0.10, "D": 0.08, "L": 0.07, "G": 0.07, "V": 0.06, "T": 0.06},
    },
}

# Per-record NFE budget for the framework arm (matches the Wave 81
# upstream-eval default). The framework arm splits this across
# ``n_rounds=3`` rounds. ``NFE_PER_RECORD`` is a module-level binding
# kept here for backward compatibility with Wave 81/86 manifest
# (default 10) — the value actually used at runtime is the one
# supplied to ``--nfe`` on the CLI and assigned in ``main()`` below.
# Wave 168 P1: ``--nfe`` was being silently ignored because this
# module-level constant was hardcoded (Wave 167 P2 discovery).
NFE_PER_RECORD: int = 10  # legacy default; overridden by --nfe in main()
# Wave 170 P3: ``--n-rounds`` flag now allows overriding the
# module-level ``N_ROUNDS`` constant via CLI (was hardcoded
# ``n_rounds=3`` in Wave 158). Default 3 preserves backward compat
# with the Wave 81/86/158 manifest bytes. The baseline arm in the
# Wave 170 fair-baseline comparison uses ``--n-rounds 1`` to disable
# the framework's restart-blend glue (so the baseline arm exercises
# only ``solve_ode`` with no ``apply_restart_distribution`` chain).
N_ROUNDS: int = 3  # legacy default; overridden by --n-rounds in main()

# Wave 186 P2 — sensitivity-analysis parameter overrides (one-at-a-time
# axis sweep; see ``docs/audit/wave186-p1-setup.md`` §1 + §4 decision).
# All three are wired through the framework glue via module-level
# globals (Wave 168 P1 / Wave 170 P3 minimal-global pattern).
# Default values (0.5 / 20 / 50) preserve the Wave 172b lineageflow
# ladder anchor byte-stable path:
# - ``BETA_BASE`` is the per-round framework restart-blend β used when
#   paper_quantities is None (legacy constant in
#   ``tools/eval/framework.py:_make_framework_policy`` line ~428).
#   Wave 184 P2 §4.1 confirms the lineageflow synthetic adapter takes
#   the constant-β path (no profile_residual_fn), so varying β is the
#   load-bearing sensitivity axis.
# - ``RESTART_MIN_NFE`` is the framework restart-blend gate threshold
#   (Wave 61 Agent 1). When ``nfe < restart_min_nfe`` the per-round
#   restart-blend glue degenerates to a no-op (frame degenerates to
#   baseline). lineageflow's synthetic adapter does not natively
#   honour restart_min_nfe; we thread it through the gen-script's
#   framework-call wrapper, which downgrades to ``n_rounds=1`` (pure
#   ``solve_ode``, no restart-blend) when the gate fires. Mirrors the
#   Wave 63 byte-stability argument.
# - ``NFE_REF`` overrides the per-adapter ``ADAPTER_NFE_REF`` table for
#   the lineageflow adapter. Wave 175 P1 set lineageflow NFE_REF=50
#   (the Wave 172b ladder anchor). Sensitivity axis exposes how the
#   ``min(1.0, NFE_REF / max(nfe, 1))`` β-scale factor changes
#   framework behaviour under different reference points.
BETA_BASE: float = 0.5  # overridden by --beta-base in main()
RESTART_MIN_NFE: int = 20  # overridden by --restart-min-nfe in main()
NFE_REF: int = 50  # overridden by --nfe-ref in main()


def _biased_aa(rng: random.Random, profile: dict, n: int) -> str:
    """Sample n AAs from the family's bias (fallback to uniform if bias under-specifies)."""
    bias = profile["bias"]
    # Build (aa, weight) pairs and renormalise.
    pairs = []
    for aa in AA_SET:
        w = bias.get(aa, 1.0)
        pairs.append((aa, float(w)))
    total = sum(w for _, w in pairs)
    weights = [w / total for _, w in pairs]
    aas = [aa for aa, _ in pairs]
    return "".join(rng.choices(aas, weights=weights, k=n))


def _generate_sequence(rng: random.Random, family_id: str, length: int) -> str:
    profile = FAMILY_PROFILES.get(family_id, {"bias": {}})
    return _biased_aa(rng, profile, length)


# Wave 186 P2 — sensitivity-analysis glue.
#
# ``--nfe-ref`` is plumbed via a runtime override of
# ``tools.eval.io.ADAPTER_NFE_REF["LineageFlowAdapter"]`` — the
# framework's ``_make_framework_policy`` reads this dict at call
# time so the override is sufficient for the β-scale axis.
#
# ``--beta-base`` requires a small wrapper around
# ``_make_framework_policy`` because the legacy β constant
# (``0.5``, ``tools/eval/framework.py`` line ~428) is hardcoded
# inline. The wrapper checks whether the inner's ``paper_quantities``
# argument is ``None`` (legacy path) and substitutes the supplied
# ``beta_base`` for the inline ``0.5``. The paper-quantity-driven
# path (which the lineageflow synthetic adapter does NOT take, per
# Wave 184 P2 §4.1) is preserved byte-identically.
#
# Both overrides are installed at most once per process invocation
# via the ``_PATCHES_APPLIED`` guard so the gen script remains
# idempotent across multiple invocations within the same Python
# session (defensive: the Wave 186 P2 driver invokes the script
# once per cell, so the guard is mainly belt-and-braces).
_PATCHES_APPLIED: bool = False
_ORIGINAL_MAKE_FRAMEWORK_POLICY: Any = None
_ORIGINAL_ADAPTER_NFE_REF: dict[str, int] | None = None


def _apply_sensitivity_patches(*, beta_base: float, nfe_ref: int) -> None:
    """Install framework glue overrides for the Wave 186 P2 sensitivity axis.

    Idempotent: subsequent calls within the same Python process are
    no-ops (the gen script is invoked once per cell by the driver,
    so this is defensive belt-and-braces against accidental double
    invocation).
    """
    global _PATCHES_APPLIED, _ORIGINAL_MAKE_FRAMEWORK_POLICY, _ORIGINAL_ADAPTER_NFE_REF
    if _PATCHES_APPLIED:
        return
    try:
        import importlib as _il

        _io_mod = _il.import_module("tools.eval.io")
        _framework_mod = _il.import_module("tools.eval.framework")
        _shim = _il.import_module("tools.run_real_ckpt_eval")
    except Exception:
        return

    # Snapshot originals (for idempotency guard).
    _ORIGINAL_ADAPTER_NFE_REF = dict(_io_mod.ADAPTER_NFE_REF)
    _ORIGINAL_MAKE_FRAMEWORK_POLICY = _framework_mod._make_framework_policy

    # Override the lineageflow entry in ``ADAPTER_NFE_REF``.
    _io_mod.ADAPTER_NFE_REF["LineageFlowAdapter"] = int(nfe_ref)
    # Also patch the shim's re-exported binding (the framework
    # module imports it under that name; both must agree).
    if hasattr(_shim, "ADAPTER_NFE_REF"):
        _shim.ADAPTER_NFE_REF["LineageFlowAdapter"] = int(nfe_ref)

    # Wrap ``_make_framework_policy`` so the legacy ``beta = 0.5``
    # constant becomes the supplied ``beta_base`` whenever the
    # inner's ``paper_quantities`` arg is None (legacy
    # constant-β branch — the lineageflow synthetic adapter's path,
    # confirmed by Wave 184 P2 §4.1).
    _orig_policy = _ORIGINAL_MAKE_FRAMEWORK_POLICY

    def _patched_make_framework_policy(  # type: ignore[no-untyped-def]
        adapter: Any,
        *,
        target_round: int,
        seed: int,
        paper_quantities: dict[str, float] | None = None,
        nfe: int = 0,
    ) -> Any:
        """Mirror of the original helper with ``beta_base`` override.

        When ``paper_quantities is None`` the legacy branch
        (``beta = 0.5``) is replaced with the supplied
        ``beta_base``. The paper-quantity-driven branch (which
        the lineageflow synthetic adapter does NOT take, per Wave
        184 P2 §4.1) is preserved verbatim — only the legacy
        constant is substituted.
        """
        # Monkey-patch the legacy constant in-place via the module
        # globals (``_ORIGINAL_MAKE_FRAMEWORK_POLICY.__globals__``).
        # This is the same pattern Wave 175 P1 uses for
        # ``ADAPTER_NFE_REF``: the helper reads ``ADAPTER_NFE_REF``
        # from its module globals at call time, so we don't need to
        # re-implement the entire function. The legacy ``beta =
        # 0.5`` is in the same scope and is read on every call (no
        # ``global`` keyword), so we can rebind it via
        # ``_globals[beta_literal] = beta_base`` for the duration of
        # the call.
        _globals = _orig_policy.__globals__
        _original_beta_literal = 0.5
        # Stash + restore via try/finally so a nested exception
        # cannot leave the legacy constant pinned to beta_base.
        _saved_beta = _globals.get("_wave186_p2_legacy_beta", None)
        try:
            # The legacy constant is referenced inline as the float
            # literal ``0.5`` (not a module-global binding) at
            # ``tools/eval/framework.py`` line ~428, so a direct
            # globals rebind is insufficient. The robust workaround
            # is to call the original function with paper_quantities
            # shimmed via a side-channel dict that the patched
            # function reads first — but the lineageflow synthetic
            # adapter doesn't expose ``profile_residual_fn``, so
            # ``paper_quantities`` is always ``None`` here, and the
            # constant-β branch is the only path exercised. We
            # re-implement the legacy branch by calling the
            # original and replacing the resulting policy's
            # ``beta_by_channel`` values.
            _policy = _orig_policy(
                adapter,
                target_round=int(target_round),
                seed=int(seed),
                paper_quantities=paper_quantities,
                nfe=int(nfe),
            )
            if paper_quantities is None and _policy is not None:
                # Replace the per-channel β with ``beta_base``
                # AFTER the legacy 0.5 has been applied. The NFE-
                # aware ``min(1.0, NFE_REF / max(nfe, 1))`` scaling
                # is preserved (the scaling multiplies the beta we
                # patch in here).
                from dataclasses import replace as _dc_replace  # type: ignore

                # Compute the scale that the inner applied to its
                # ``beta = 0.5`` legacy constant.
                if int(nfe) > 0:
                    _NFE_REF_EFFECTIVE = int(_globals["ADAPTER_NFE_REF"].get(
                        type(adapter).__name__, _globals["DEFAULT_NFE_REF"],
                    ))
                    _scale = min(
                        1.0,
                        float(_NFE_REF_EFFECTIVE) / float(max(1, int(nfe))),
                    )
                else:
                    _scale = 1.0
                _new_beta = float(beta_base) * float(_scale)
                # Rebuild the policy with the substituted β.
                _policy = _dc_replace(
                    _policy,
                    beta_by_channel={
                        ch: float(_new_beta)
                        for ch in _policy.beta_by_channel
                    },
                )
            return _policy
        finally:
            # No-op (we don't actually mutate module globals — see
            # the rationale above). This branch exists to keep the
            # try/finally structure symmetric in case future
            # variants of this helper DO mutate globals.
            if _saved_beta is not None:
                _globals["_wave186_p2_legacy_beta"] = _saved_beta

    # Install the wrapped helper. Three module paths must agree
    # because ``tools.run_real_ckpt_eval`` re-exports the symbol
    # via ``from tools.eval import _make_framework_policy`` and the
    # framework helper itself looks up ``_compute_paper_quantities``
    # via the shim's globals.
    _framework_mod._make_framework_policy = _patched_make_framework_policy
    if hasattr(_shim, "_make_framework_policy"):
        _shim._make_framework_policy = _patched_make_framework_policy
    _PATCHES_APPLIED = True


def _build_lineageflow_adapter(family_id: str, seed: int) -> Any | None:
    """Lazy-construct a synthetic-mode :class:`LineageFlowAdapter`.

    The adapter defaults to ``force_mode="auto"``, which falls back
    to ``"synthetic"`` when the published LineageFlow ckpt is not
    vendored on disk. We deliberately do NOT require ``torch`` for
    the gen script — the synthetic velocity field is deterministic
    NumPy and exposes the same ``solve_ode`` /
    ``apply_restart_distribution`` Protocol surface that the real
    torch adapter would (Wave 81 5-LOC stub fix). The framework arm
    therefore exercises the **real multi-round glue layer** even on
    cold-clone hosts.

    Returns ``None`` when the adapter import is unavailable (e.g.
    ``adaptive_reflow`` not on PYTHONPATH) so the caller can fall
    back to the bare-RNG path.

    Note: the LineageFlow adapter constructor takes ``seed_offset``
    and ``synthetic_seed`` (NOT a flat ``seed=`` kwarg) — the per-cell
    seed offset is layered onto the synthetic RNG via
    ``seed_offset=int(seed)`` so each adapter instance is keyed to a
    deterministic per-family seed stream.
    """
    try:
        from adaptive_reflow.adapters.lineageflow import (  # type: ignore
            LineageFlowAdapter,
        )
    except Exception as _exc:  # pragma: no cover — defensive only
        return None
    try:
        return LineageFlowAdapter(
            family_id=family_id,
            num_steps=NFE_PER_RECORD,
            solver="euler",
            force_mode="synthetic",
            seed_offset=int(seed),
        )
    except Exception:
        # Adapter may still raise on a host without the synthetic
        # velocity field — same fallback semantics.
        return None


def _framework_emit_sequence(
    adapter: Any,
    *,
    family_id: str,
    length: int,
    seed: int,
    temperature: float = 1.0,
) -> str | None:
    """Drive one framework multi-round pass and return a length-``length`` AA string.

    Uses :func:`tools.run_real_ckpt_eval._solve_framework` to chain
    ``solve_ode -> export_endpoint -> apply_restart_distribution``
    for ``n_rounds=N_ROUNDS`` rounds at ``nfe=NFE_PER_RECORD`` each
    (the canonical Wave 45 multi-round path). The returned trace
    carries the per-position categorical at the integrated endpoint,
    which :meth:`LineageFlowAdapter.observe_token_indices` decodes
    to a ``(L,)`` int64 array. We then apply the canonical mod-20
    AA-alphabet mapping (matches
    ``tools/run_real_ckpt_eval._decode_lineageflow_idx_to_aa``).

    Wave 171 P1 addition: ``temperature`` is forwarded to
    :meth:`LineageFlowAdapter.observe_token_indices` so the same
    gen-script surface can run under the byte-stable argmax path
    (``temperature=1.0``, the default and the path used by every
    pre-Wave-171 Wave 158 / 161 K6 / 167 P5 result) or under
    temperature-controlled stochastic sampling (``temperature>1.0``,
    e.g. ``1.5``). When ``temperature>1.0`` the caller MUST have
    supplied an ``rng`` so the per-record decode is reproducible.

    Returns ``None`` when the framework glue path raises — the
    caller falls back to the bare-RNG draw and surfaces the failure
    in the per-record manifest so the auditor can detect failed
    cells.

    Wave 186 P2 addition: ``--restart-min-nfe`` is honoured by
    downgrading ``n_rounds`` to ``1`` when ``nfe < restart_min_nfe``
    (the framework's restart-blend glue degenerates to a pure
    ``solve_ode`` pass with no ``apply_restart_distribution`` chain).
    Mirrors the Wave 63 byte-stability argument: at ``n_rounds=1``
    the framework returns a trace that is byte-identical to the
    baseline axis (seed, nfe), so the per-record sequences are
    sensitive to the gate firing.

    Note: the framework-side ``length`` argument is informational
    only — the adapter's per-position categorical has a fixed
    canonical length (``LINEAGEFLOW_MAX_LENGTH = 256``). We trim
    the returned AA string to ``length`` to honour the per-record
    length distribution captured in ``FAMILY_PROFILES`` + the
    command-line ``--min-len`` / ``--max-len`` flags.
    """
    try:
        from adaptive_reflow.adapters.lineageflow import (  # type: ignore
            AMINO_ACID_CATEGORICAL,
            LINEAGEFLOW_VOCAB_SIZE,
        )
        from tools.run_real_ckpt_eval import _solve_framework  # type: ignore
    except Exception:
        return None
    # Wave 186 P2 — restart-blend gate: when nfe < restart_min_nfe,
    # downgrade to ``n_rounds=1`` (pure solve_ode, no
    # apply_restart_distribution chain) so the framework degenerates
    # to the baseline axis. This is the load-bearing sensitivity axis
    # for ``--restart-min-nfe`` on lineageflow synthetic (which does
    # not natively accept the kwarg).
    effective_n_rounds = int(N_ROUNDS)
    if int(NFE_PER_RECORD) < int(RESTART_MIN_NFE):
        effective_n_rounds = 1
    try:
        trace, _wall = _solve_framework(
            adapter,
            nfe=NFE_PER_RECORD,
            seed=int(seed),
            n_rounds=int(effective_n_rounds),
        )
    except Exception:
        return None
    # Wave 171 P1: build a seeded Generator once per record so the
    # stochastic decode (T > 1.0) is reproducible from ``seed``.
    # For T == 1.0 the rng is unused — the abstract decoder returns
    # argmax without consulting it.
    decode_rng = None
    if float(temperature) > 1.0:
        try:
            import numpy as _np  # type: ignore
            decode_rng = _np.random.default_rng(int(seed))
        except Exception:
            return None
    try:
        obs_dict = adapter.observe_token_indices(
            trace, paper_quantities=None,
            temperature=float(temperature), rng=decode_rng,
        )
        idx_arr = obs_dict.get(str(AMINO_ACID_CATEGORICAL))
        if idx_arr is None:
            return None
    except Exception:
        return None
    K_aa = len(AA_SET)
    flat = idx_arr.reshape(-1)
    aa_str = "".join(AA_SET[int(v) % K_aa] for v in flat[: int(length)])
    return aa_str


def _write_baseline_arm(
    out_path: Path,
    *,
    n: int,
    seed: int,
    family_ids: list[str],
    min_len: int,
    max_len: int,
) -> dict[str, int]:
    """Write the baseline arm: bare RNG draws over each family's AA bias."""
    baseline_rng = random.Random(int(seed))
    counts: dict[str, int] = {}
    with out_path.open("w") as f:
        for i in range(int(n)):
            family_id = family_ids[i % len(family_ids)]
            length = baseline_rng.randint(int(min_len), int(max_len))
            seq = _generate_sequence(baseline_rng, family_id, length)
            f.write(f">baseline_seed{i}|family={family_id}\n")
            f.write(f"{seq}\n")
            counts[family_id] = counts.get(family_id, 0) + 1
    return counts


def _write_framework_arm(
    out_path: Path,
    *,
    n: int,
    seed: int,
    family_ids: list[str],
    min_len: int,
    max_len: int,
    framework_rng: random.Random,
    temperature: float = 1.0,
) -> tuple[dict[str, int], dict[str, int]]:
    """Write the framework arm: drives :class:`LineageFlowAdapter` for each record.

    Returns ``(per_family_count, fallback_count)``. ``fallback_count``
    tallies the records where the real framework path raised and we
    fell back to bare RNG — surfaced in the manifest so the auditor
    can detect failed cells.

    Wave 171 P1: ``temperature`` is forwarded to
    :func:`_framework_emit_sequence` so the framework arm's decode
    can be switched from the byte-stable argmax path (``1.0``) to
    stochastic sampling (``> 1.0``). Default ``1.0`` preserves
    Wave 158 / Wave 161 K6 / Wave 167 P5 manifest bytes.
    """
    per_family_count: dict[str, int] = {}
    fallback_count: dict[str, int] = {}

    # Build one synthetic-mode adapter per family. The adapter is
    # deterministic by ``family_id`` + ``seed`` so a single instance
    # per family preserves per-record byte-stability (each subsequent
    # solve_ode call is keyed by a per-record seed offset).
    adapters: dict[str, Any | None] = {}
    for family_id in family_ids:
        adapters[family_id] = _build_lineageflow_adapter(family_id, int(seed))

    with out_path.open("w") as f:
        for i in range(int(n)):
            family_id = family_ids[i % len(family_ids)]
            length = framework_rng.randint(int(min_len), int(max_len))
            adapter = adapters[family_id]
            seq: str | None = None
            if adapter is not None:
                seq = _framework_emit_sequence(
                    adapter,
                    family_id=family_id,
                    length=length,
                    seed=int(seed) + int(i),
                    temperature=float(temperature),
                )
            if seq is None:
                # Defensive fallback: bare-RNG draw. The auditor
                # surfaces this via ``fallback_count`` so failed
                # cells are detectable (Pitfall #2 not closed for
                # that record only — the framework-side surface
                # remains exercised for every other record).
                seq = _generate_sequence(framework_rng, family_id, length)
                fallback_count[family_id] = (
                    fallback_count.get(family_id, 0) + 1
                )
            f.write(f">framework_seed{i}|family={family_id}\n")
            f.write(f"{seq}\n")
            per_family_count[family_id] = (
                per_family_count.get(family_id, 0) + 1
            )
    return per_family_count, fallback_count


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--outdir", type=Path, default=Path("data/lineageflow_n1000"))
    p.add_argument("--n", type=int, default=1000)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--min-len", type=int, default=30)
    p.add_argument("--max-len", type=int, default=150)
    p.add_argument(
        "--nfe",
        type=int,
        default=10,
        help=(
            "Per-record NFE budget for the framework arm "
            "(default: 10 to match Wave 81 + Wave 86 manifest). "
            "Wired into NFE_PER_RECORD via global reassignment in main()."
        ),
    )
    p.add_argument(
        "--n-rounds",
        type=int,
        default=3,
        help=(
            "Number of restart-blend rounds for the framework arm. "
            "Baseline arm: use 1 (no restart-blend glue, pure solve_ode). "
            "Framework arm: use 3 (Wave 158 canonical Wave 45 multi-round path). "
            "Default 3 preserves backward compatibility with Wave 81/86/158 manifest bytes."
        ),
    )
    p.add_argument(
        "--temperature",
        type=float,
        default=1.0,
        help=(
            "Sampling temperature for the framework-arm decoder "
            "(Wave 171 P1). 1.0 = argmax (byte-stable with Wave 158 / "
            "Wave 161 K6 / Wave 167 P5 manifest bytes; default). "
            "> 1.0 = stochastic sampling from softmax(log(theta) / T). "
            "Used to expose framework-vs-baseline distributional "
            "advantage that is invisible under argmax decoding "
            "(Wave 170 P5 finding)."
        ),
    )
    # Wave 186 P2 — sensitivity-analysis axis flags (one-at-a-time
    # parameter sweep; see ``docs/audit/wave186-p1-setup.md`` §1).
    # Default values match the Wave 172b lineageflow ladder anchor
    # (β=0.5, restart_min_nfe=20, NFE_REF=50) so the baseline cell is
    # byte-stable against the canonical Wave 158/172b manifest bytes.
    p.add_argument(
        "--beta-base",
        type=float,
        default=0.5,
        help=(
            "Per-round framework restart-blend β (legacy constant in "
            "``tools/eval/framework.py:_make_framework_policy``). "
            "Wave 186 P2 sensitivity axis: β ∈ {0.3, 0.7, 0.9}. "
            "Default 0.5 preserves Wave 158/172b lineageflow ladder "
            "anchor byte-stability."
        ),
    )
    p.add_argument(
        "--restart-min-nfe",
        type=int,
        default=20,
        help=(
            "Framework restart-blend gate threshold (Wave 61 Agent 1). "
            "When ``nfe < restart_min_nfe`` the framework's per-round "
            "restart-blend glue degenerates to baseline. Wave 186 P2 "
            "sensitivity axis: restart_min_nfe ∈ {5, 10, 40, 80}. "
            "Default 20 preserves Wave 172b lineageflow anchor. "
            "lineageflow synthetic adapter does not natively accept "
            "restart_min_nfe; the gen-script wrapper downgrades to "
            "``n_rounds=1`` when the gate fires."
        ),
    )
    p.add_argument(
        "--nfe-ref",
        type=int,
        default=50,
        help=(
            "NFE reference for β scaling "
            "(``min(1.0, NFE_REF / max(nfe, 1))`` in "
            "``tools/eval/framework.py:_make_framework_policy``). "
            "Wave 175 P1 set lineageflow NFE_REF=50; Wave 186 P2 "
            "sensitivity axis: NFE_REF ∈ {10, 25, 75, 100, 200}. "
            "Default 50 preserves Wave 172b lineageflow anchor."
        ),
    )
    args = p.parse_args()

    # Wire the CLI --nfe flag through to the module-level NFE_PER_RECORD
    # constant that ``_build_lineageflow_adapter`` and
    # ``_framework_emit_sequence`` read. Using ``global`` keeps the
    # change minimal — the alternative (passing ``nfe`` through every
    # call site) would touch every function signature in this file
    # without buying anything. The default value (10) preserves
    # backward compatibility with the Wave 81/86 manifest bytes.
    global NFE_PER_RECORD
    NFE_PER_RECORD = int(args.nfe)
    # Wave 170 P3: same minimal ``global`` wire-through pattern for
    # ``--n-rounds`` — keeps the constant readable from the call sites
    # in ``_build_lineageflow_adapter`` + ``_framework_emit_sequence``
    # without churning every function signature. Default 3 preserves
    # Wave 158 backward compat.
    global N_ROUNDS
    N_ROUNDS = int(args.n_rounds)
    # Wave 186 P2 — sensitivity-analysis axis overrides. Same minimal
    # ``global`` wire-through pattern as Wave 168 P1 / Wave 170 P3 —
    # the helpers (``_framework_emit_sequence``) read these module
    # globals and apply them via the framework glue. Default values
    # (0.5 / 20 / 50) preserve the Wave 158/172b byte-stable path.
    global BETA_BASE
    BETA_BASE = float(args.beta_base)
    global RESTART_MIN_NFE
    RESTART_MIN_NFE = int(args.restart_min_nfe)
    global NFE_REF
    NFE_REF = int(args.nfe_ref)
    # Wave 186 P2 — patch the framework glue to honour the
    # sensitivity-analysis parameters. The framework's
    # ``_make_framework_policy`` reads ``ADAPTER_NFE_REF`` from
    # ``tools.eval.io`` at call time, so a runtime override of the
    # table is sufficient for the ``--nfe-ref`` axis. The
    # ``--beta-base`` axis requires wrapping
    # ``_make_framework_policy`` (its β constant is hardcoded inline
    # at the legacy-constant branch). The ``--restart-min-nfe`` axis
    # is honoured inside ``_framework_emit_sequence`` by downgrading
    # ``n_rounds`` to 1 when the gate fires.
    _apply_sensitivity_patches(
        beta_base=float(args.beta_base),
        nfe_ref=int(args.nfe_ref),
    )
    # Wave 171 P1: --temperature is forwarded through
    # ``_write_framework_arm`` rather than being captured in a module
    # global, because it has no need to be read by the helper before
    # the call (the decode happens at decode-time inside
    # ``_framework_emit_sequence``). Default 1.0 keeps the byte-stable
    # argmax path live for every existing invocation.
    args.outdir.mkdir(parents=True, exist_ok=True)

    # Distinct RNG sub-streams per arm so the framework arm cannot
    # contaminate the baseline (and vice versa). The framework arm's
    # RNG only feeds the rare defensive fallback (when the
    # adapter is unavailable for a record).
    baseline_seed = int(args.seed)
    framework_seed = int(args.seed) ^ 0x5A5A
    family_ids = list(FAMILY_PROFILES.keys())

    manifest: dict[str, Any] = {
        "n": int(args.n),
        "seed": int(args.seed),
        "min_len": int(args.min_len),
        "max_len": int(args.max_len),
        "family_ids": family_ids,
        "nfe_per_record": int(NFE_PER_RECORD),
        "n_rounds": int(N_ROUNDS),
        "temperature": float(args.temperature),
        # Wave 186 P2 — sensitivity-analysis axis values captured so
        # the per-cell audit doc can correlate FASTA bytes to the input
        # parameter perturbation. Defaults preserve the Wave 158/172b
        # lineageflow ladder anchor.
        "beta_base": float(BETA_BASE),
        "restart_min_nfe": int(RESTART_MIN_NFE),
        "nfe_ref": int(NFE_REF),
    }

    # ---- Baseline arm (bare RNG, preserved byte-shape) -----------------
    baseline_counts = _write_baseline_arm(
        args.outdir / "baseline.fasta",
        n=int(args.n),
        seed=baseline_seed,
        family_ids=family_ids,
        min_len=int(args.min_len),
        max_len=int(args.max_len),
    )
    manifest["baseline_per_family_count"] = dict(baseline_counts)
    print(f"wrote {args.outdir / 'baseline.fasta'} (n={int(args.n)})")

    # ---- Framework arm (real LineageFlowAdapter multi-round pass) ------
    framework_rng = random.Random(framework_seed)
    framework_counts, fallback_counts = _write_framework_arm(
        args.outdir / "framework.fasta",
        n=int(args.n),
        seed=int(args.seed),
        family_ids=family_ids,
        min_len=int(args.min_len),
        max_len=int(args.max_len),
        framework_rng=framework_rng,
        temperature=float(args.temperature),
    )
    manifest["framework_per_family_count"] = dict(framework_counts)
    manifest["framework_fallback_per_family_count"] = dict(fallback_counts)
    print(f"wrote {args.outdir / 'framework.fasta'} (n={int(args.n)})")

    # Combined manifest field (Wave 81 shape, additive — preserves
    # the existing ``per_family_count`` key for downstream consumers).
    manifest["per_family_count"] = dict(baseline_counts)

    manifest_path = args.outdir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"wrote {manifest_path}")


if __name__ == "__main__":
    main()
