"""Sweep driver — per-cell orchestration for ``(model, seed, nfe)`` cells.

OWNER: Wave 97 Agent B — tools/eval/ subpackage split (single responsibility:
the per-cell driver that runs baseline + framework arms, computes the
primary metric, and (optionally) the composite + paper-metric +
upstream-eval block. Consumed by ``eval.cli.main`` in the new layout.

This module is byte-stable against `tools/run_real_ckpt_eval.py` pre-split.
Every exported symbol matches the pre-Wave-97 contract. ``_run_cell`` is
the dispatch hub; it imports ``_solve_baseline`` (from ``eval.baseline``),
``_solve_framework`` (from ``eval.framework``), ``_compute_metric`` (from
``eval.metrics``), and the three composite helpers.

Also re-exports ``_extract_aa_for_fasta`` + ``_extract_ca_coords_for_kanzi``
that the legacy ``--kanzi-upstream-eval`` / ``--lineageflow-upstream-eval``
subprocess invocations consume.
"""
from __future__ import annotations

from typing import Any

from tools.eval.io import (  # type: ignore
    DOWNSTREAM_METRICS,
    REPO_ROOT,
    TIE_AT_SATURATION,
)

# NB: ``_run_cell`` uses :func:`_resolve_metric` (defined below) to
# look up every helper from the ``tools.run_real_ckpt_eval`` shim at
# call time. The legacy test surface monkey-patches
# ``tools.run_real_ckpt_eval._compute_flowmol3_composite`` /
# ``_solve_baseline`` / ``_resolve_adapter`` etc. and expects
# ``_run_cell`` to pick up the patched function. Importing the
# helpers here directly would break that contract — they MUST go
# through the shim.
from tools.eval.metrics import (  # type: ignore  # noqa: F401
    _compute_kanzi_composite,
    _compute_kanzi_framework_paper_metric,
    _compute_lineageflow_composite,
    _compute_flowmol3_composite,
    _compute_metric,
    _decode_kanzi_idx_to_aa,
    _decode_lineageflow_idx_to_aa,
)
from tools.eval.baseline import _solve_baseline  # type: ignore  # noqa: F401
from tools.eval.framework import (  # type: ignore  # noqa: F401
    _resolve_adapter,
    _solve_framework,
)


def _resolve_metric(name: str) -> Any:
    """Look up a metric helper via the ``tools.run_real_ckpt_eval`` shim.

    This indirection preserves the byte-stable behaviour where
    ``tools.run_real_ckpt_eval._compute_*`` is the canonical symbol
    looked up by ``_run_cell``. Tests monkey-patch
    ``tools.run_real_ckpt_eval._compute_flowmol3_composite`` and expect
    the patched function to be called by ``_run_cell`` — without this
    indirection the split into ``tools.eval.sweep`` would break the
    monkey-patch contract.
    """
    import importlib
    shim = importlib.import_module("tools.run_real_ckpt_eval")
    return getattr(shim, name)


def _run_cell(
    model: str,
    seed: int,
    nfe: int,
    *,
    n_rounds: int = 3,
    force_mode: str = "synthetic",
    metric_mode: str = "synthetic",
    composite_metric: str = "auto",
    restart_min_nfe: int | None = None,
    n_molecules: int = 1,
    paper_metrics_flag: bool = False,
    paper_reference: str = "GEOM_DRUGS",
    lineageflow_upstream_eval: bool = False,
    kanzi_upstream_eval: bool = False,
    flowmol3_upstream_eval: bool = False,
    kanzi_framework_paper_metrics: bool = False,
    upstream_n_samples: int = 1000,
) -> dict[str, Any]:
    """Run one (model, seed, nfe_budget) cell.

    Returns a single dict ready to drop into the ``evidence[]`` list of
    a capability_audit-style report.
    """
    spec = DOWNSTREAM_METRICS[model]
    cell: dict[str, Any] = {
        "model": model,
        "seed": int(seed),
        "nfe_budget": int(nfe),
        "axis": spec["axis"],
        "paper": spec["paper"],
        "primary_metric_name": spec["primary_metric"]["name"],
        "primary_metric_direction": spec["primary_metric"]["direction"],
        "n_rounds_framework": int(n_rounds),
        "force_mode_requested": force_mode,
        "metric_mode_requested": metric_mode,
        "restart_min_nfe_requested": restart_min_nfe,
    }
    adapter, mode = _resolve_metric("_resolve_adapter")(
        model,
        force_mode=force_mode,
        restart_min_nfe=restart_min_nfe,
        nfe_budget=int(nfe),
    )
    if adapter is None:
        cell["status"] = "BLOCKED"
        cell["status_detail"] = mode
        cell["baseline_metric"] = None
        cell["framework_metric"] = None
        cell["delta_pct"] = None
        cell["marker"] = "blocked"
        cell["reason"] = (
            f"model={model!r} has no shipped adapter file: "
            f"{spec['adapter_factory']!r}; see docs/audit/gap-audit.md"
        )
        return cell
    cell["adapter_mode"] = mode
    primary = spec["primary_metric"]
    try:
        baseline_trace, baseline_wall = _resolve_metric("_solve_baseline")(
            adapter, nfe=int(nfe), seed=int(seed), n_molecules=int(n_molecules),
        )
        framework_trace, framework_wall = _resolve_metric("_solve_framework")(
            adapter, nfe=int(nfe), seed=int(seed), n_rounds=int(n_rounds),
            n_molecules=int(n_molecules),
        )
    except Exception as exc:  # noqa: BLE001
        cell["status"] = "RUN_ERROR"
        cell["status_detail"] = f"{type(exc).__name__}:{exc}"
        cell["baseline_metric"] = None
        cell["framework_metric"] = None
        cell["delta_pct"] = None
        cell["marker"] = "run_error"
        return cell
    # Wave 70 Phase 4: OPT-IN capture of sampled molecules for the
    # FlowMol3 composite. The FlowMol3 v2 adapter ships
    # ``export_sampled_molecules(trace)`` (Phase 3); v1 / non-flowmol3
    # adapters do not.
    sampled_molecules: list[Any] | None = None
    if model in ("flowmol3", "flowmol3_v2") and hasattr(
        adapter, "export_sampled_molecules",
    ):
        try:
            _sm_result = adapter.export_sampled_molecules(baseline_trace)
            if isinstance(_sm_result, tuple) and len(_sm_result) >= 1:
                sampled_molecules = list(_sm_result[0])
            elif _sm_result is not None:
                sampled_molecules = list(_sm_result)
        except Exception:  # noqa: BLE001
            sampled_molecules = None
    baseline_value, baseline_marker, baseline_dbg = _resolve_metric("_compute_metric")(
        model, baseline_trace, seed=int(seed), nfe=int(nfe),
        metric_name=primary["name"], metric_mode=metric_mode,
        adapter=adapter,
    )
    framework_value, framework_marker, framework_dbg = _resolve_metric("_compute_metric")(
        model, framework_trace, seed=int(seed), nfe=int(nfe),
        metric_name=primary["name"], metric_mode=metric_mode,
        adapter=adapter,
    )
    cell["baseline_metric"] = baseline_value
    cell["baseline_marker"] = baseline_marker
    cell["baseline_debug"] = baseline_dbg
    cell["framework_metric"] = framework_value
    cell["framework_marker"] = framework_marker
    cell["framework_debug"] = framework_dbg
    # Wave 47 composite (Phase-2B wiring): LineageFlow composite.
    if (
        composite_metric != "synthetic"
        and model == "lineageflow"
    ):
        (
            composite_value, composite_marker, composite_dbg,
        ) = _resolve_metric("_compute_lineageflow_composite")(
            adapter=adapter,
            baseline_trace=baseline_trace,
            framework_trace=framework_trace,
            seed=int(seed), nfe=int(nfe),
        )
        cell["composite"] = composite_value
        cell["composite_marker"] = composite_marker
        cell["composite_debug"] = composite_dbg
        cell["composite_components"] = {
            "phi1_entropy_reduction_normalised":
                composite_dbg.get("phi1_entropy_reduction_normalised"),
            "phi2_max_prob_delta":
                composite_dbg.get("phi2_max_prob_delta"),
            "phi3_argmax_turnover_signed":
                composite_dbg.get("phi3_argmax_turnover_signed"),
        }
        cell["composite_weights"] = composite_dbg.get("weights") or [0.40, 0.35, 0.25]
        cell["composite_K"] = composite_dbg.get("K", 33)
    # Wave 52 Agent A composite (Phase-4K wiring): Kanzi composite.
    if (
        composite_metric != "synthetic"
        and model == "kanzi"
    ):
        (
            composite_value, composite_marker, composite_dbg,
        ) = _resolve_metric("_compute_kanzi_composite")(
            adapter=adapter,
            baseline_trace=baseline_trace,
            framework_trace=framework_trace,
            seed=int(seed), nfe=int(nfe),
        )
        cell["composite"] = composite_value
        cell["composite_marker"] = composite_marker
        cell["composite_debug"] = composite_dbg
        cell["composite_components"] = {
            "phi1_entropy_reduction_normalised":
                composite_dbg.get("phi1_entropy_reduction_normalised"),
            "phi2_max_prob_delta":
                composite_dbg.get("phi2_max_prob_delta"),
            "phi3_argmax_turnover_signed":
                composite_dbg.get("phi3_argmax_turnover_signed"),
        }
        cell["composite_weights"] = composite_dbg.get("weights") or [0.40, 0.35, 0.25]
        cell["composite_K"] = composite_dbg.get("K", 64)
        cell["composite_glue_class"] = composite_dbg.get(
            "glue_class", "KanziGlue",
        )
    # Wave 49 Agent D composite (Phase-3C wiring): FlowMol3 composite.
    if (
        composite_metric != "synthetic"
        and model in ("flowmol3", "flowmol3_v2")
    ):
        (
            composite_value, composite_marker, composite_dbg,
        ) = _resolve_metric("_compute_flowmol3_composite")(
            adapter=adapter,
            baseline_trace=baseline_trace,
            framework_trace=framework_trace,
            seed=int(seed), nfe=int(nfe),
            sampled_molecules=sampled_molecules,
        )
        cell["composite"] = composite_value
        cell["composite_marker"] = composite_marker
        cell["composite_debug"] = composite_dbg
        cell["composite_components"] = {
            "frac_valid_mols":
                composite_dbg.get("phi1_frac_valid_mols"),
            "frac_mols_stable":
                composite_dbg.get("phi2_frac_mols_stable"),
            "neg_energy_js_div":
                composite_dbg.get("phi3_neg_energy_js_div"),
            "neg_reos_cum_dev":
                composite_dbg.get("phi4_neg_reos_cum_dev"),
            "neg_med_rmsd_after_xtb":
                composite_dbg.get("phi5_neg_med_rmsd_after_xtb"),
        }
        cell["composite_weights"] = composite_dbg.get("weights") or [
            0.30, 0.25, 0.15, 0.15, 0.15,
        ]
        cell["composite_glue_class"] = composite_dbg.get(
            "glue_class", "FlowMol3Glue",
        )
    # Wave 75 Agent 2: opt-in 4-paper-metric block.
    if paper_metrics_flag and model in ("flowmol3", "flowmol3_v2"):
        cell["paper_metrics_marker"] = "skipped"
        cell["paper_metrics_debug"] = {
            "reason": "not_run",
            "paper_metrics_flag": bool(paper_metrics_flag),
        }
        if sampled_molecules:
            try:
                from tools.paper_metrics import (  # type: ignore  # noqa: PLC0415
                    REFERENCE_GEOM_DRUGS,
                    REFERENCE_NCI_FIRST_5K_PROXY,
                    compute_all_paper_metrics,
                )
                ref_label = paper_reference or REFERENCE_GEOM_DRUGS
                if ref_label not in (REFERENCE_GEOM_DRUGS, REFERENCE_NCI_FIRST_5K_PROXY):
                    ref_label = REFERENCE_GEOM_DRUGS
                paper_metrics_obj = compute_all_paper_metrics(
                    list(sampled_molecules),
                    reference=ref_label,
                    full_pb=True,
                    pb_workers=2,
                )
                cell["paper_validity_pct"] = paper_metrics_obj.paper_validity_pct
                cell["paper_pb_validity_pct"] = paper_metrics_obj.paper_pb_validity_pct
                cell["paper_fg_deviation"] = paper_metrics_obj.paper_fg_deviation
                cell["paper_ood_ring_rate"] = paper_metrics_obj.paper_ood_ring_rate
                cell["paper_metrics_marker"] = "computed"
                cell["paper_metrics_debug"] = {
                    "reference": ref_label,
                    "n_sampled_molecules": len(list(sampled_molecules)),
                    "full_pb": True,
                    "paper_metrics_module": "tools.paper_metrics",
                    "paper_metrics_class": "PaperMetricsResult",
                }
            except ImportError as exc:
                cell["paper_metrics_marker"] = "blocked"
                cell["paper_metrics_debug"] = {
                    "reason": f"paper_metrics_import_failed: {type(exc).__name__}:{exc}",
                }
            except Exception as exc:  # noqa: BLE001
                cell["paper_metrics_marker"] = "blocked"
                cell["paper_metrics_debug"] = {
                    "reason": f"paper_metrics_compute_failed: {type(exc).__name__}:{exc}",
                }
        else:
            cell["paper_metrics_marker"] = "blocked"
            cell["paper_metrics_debug"] = {
                "reason": "no_sampled_molecules",
            }
        if (
            hasattr(adapter, "export_sampled_molecules")
            and model in ("flowmol3_v2",)
        ):
            framework_sampled: list[Any] | None = None
            try:
                _fw_sm_result = adapter.export_sampled_molecules(framework_trace)
                if isinstance(_fw_sm_result, tuple) and len(_fw_sm_result) >= 1:
                    framework_sampled = list(_fw_sm_result[0])
                elif _fw_sm_result is not None:
                    framework_sampled = list(_fw_sm_result)
            except Exception:  # noqa: BLE001
                framework_sampled = None
            cell["paper_metrics_marker_framework"] = "skipped"
            cell["paper_metrics_debug_framework"] = {
                "reason": "not_run",
                "paper_metrics_flag": bool(paper_metrics_flag),
            }
            if framework_sampled:
                try:
                    from tools.paper_metrics import (  # type: ignore  # noqa: PLC0415
                        REFERENCE_GEOM_DRUGS as _REF_GEOM,  # noqa: PLC0415
                        REFERENCE_NCI_FIRST_5K_PROXY as _REF_NCI,  # noqa: PLC0415
                        compute_all_paper_metrics as _compute_paper,  # noqa: PLC0415
                    )
                    ref_label_fw = paper_reference or _REF_GEOM
                    if ref_label_fw not in (_REF_GEOM, _REF_NCI):
                        ref_label_fw = _REF_GEOM
                    paper_metrics_obj_fw = _compute_paper(
                        list(framework_sampled),
                        reference=ref_label_fw,
                        full_pb=True,
                        pb_workers=2,
                    )
                    cell["paper_validity_pct_framework"] = (
                        paper_metrics_obj_fw.paper_validity_pct
                    )
                    cell["paper_pb_validity_pct_framework"] = (
                        paper_metrics_obj_fw.paper_pb_validity_pct
                    )
                    cell["paper_fg_deviation_framework"] = (
                        paper_metrics_obj_fw.paper_fg_deviation
                    )
                    cell["paper_ood_ring_rate_framework"] = (
                        paper_metrics_obj_fw.paper_ood_ring_rate
                    )
                    cell["paper_metrics_marker_framework"] = "computed"
                    cell["paper_metrics_debug_framework"] = {
                        "reference": ref_label_fw,
                        "n_sampled_molecules": len(list(framework_sampled)),
                        "full_pb": True,
                        "paper_metrics_module": "tools.paper_metrics",
                        "paper_metrics_class": "PaperMetricsResult",
                    }
                except ImportError as exc:
                    cell["paper_metrics_marker_framework"] = "blocked"
                    cell["paper_metrics_debug_framework"] = {
                        "reason": f"paper_metrics_import_failed: {type(exc).__name__}:{exc}",
                    }
                except Exception as exc:  # noqa: BLE001
                    cell["paper_metrics_marker_framework"] = "blocked"
                    cell["paper_metrics_debug_framework"] = {
                        "reason": f"paper_metrics_compute_failed: {type(exc).__name__}:{exc}",
                    }
            else:
                cell["paper_metrics_marker_framework"] = "blocked"
                cell["paper_metrics_debug_framework"] = {
                    "reason": "no_sampled_molecules",
                }
    # Wave 79 Agent 2: opt-in per-model upstream-eval subprocess block.
    if (
        lineageflow_upstream_eval
        or kanzi_upstream_eval
        or flowmol3_upstream_eval
    ):
        cell["upstream_eval_metrics"] = {}
        cell["upstream_eval_debug"] = {
            "n_samples": len(n_samples) if False else int(upstream_n_samples),
            "lineageflow_flag": bool(lineageflow_upstream_eval),
            "kanzi_flag": bool(kanzi_upstream_eval),
            "flowmol3_flag": bool(flowmol3_upstream_eval),
        }
        try:
            from tools.upstream_eval import (  # type: ignore  # noqa: PLC0415
                run_flowmol3_upstream_eval,
                run_kanzi_upstream_eval,
                run_lineageflow_upstream_eval,
            )
        except ImportError as exc:
            cell["upstream_eval_debug"]["import_error"] = (
                f"{type(exc).__name__}:{exc}"
            )
            run_flowmol3_upstream_eval = None  # type: ignore
            run_kanzi_upstream_eval = None  # type: ignore
            run_lineageflow_upstream_eval = None  # type: ignore
        upstream_out_dir = (
            REPO_ROOT
            / "verification_outputs"
            / "upstream_eval"
            / f"{model}_seed{seed}nnfe{nfe}"
        )
        upstream_out_dir.mkdir(parents=True, exist_ok=True)
        if lineageflow_upstream_eval and model == "lineageflow":
            cell["upstream_eval_debug"]["lineageflow"] = "not_run"
            if run_lineageflow_upstream_eval is None:
                cell["upstream_eval_debug"]["lineageflow"] = "blocked"
            else:
                family_id = "PF00005.27"
                try:
                    if model == "lineageflow":
                        from adaptive_reflow.adapters.lineageflow import (
                            LINEAGEFLOW_FAMILY_ID_DEFAULT,
                        )
                        family_id = str(LINEAGEFLOW_FAMILY_ID_DEFAULT)
                except Exception:  # noqa: BLE001
                    pass
                fasta_lines: list[str] = [
                    f">baseline_seed{seed}|family={family_id}",
                    _extract_aa_for_fasta(baseline_trace, model),
                    f">framework_seed{seed}|family={family_id}",
                    _extract_aa_for_fasta(framework_trace, model),
                ]
                fasta_path = upstream_out_dir / "samples.fasta"
                fasta_path.write_text(
                    "\n".join(fasta_lines) + "\n", encoding="utf-8",
                )
                try:
                    lf_metrics = run_lineageflow_upstream_eval(
                        fasta_path=str(fasta_path),
                        output_dir=str(upstream_out_dir / "lf_out"),
                    )
                except Exception as exc:  # noqa: BLE001
                    lf_metrics = {
                        "status": 0.0,
                        "reason": f"runner_exception:{type(exc).__name__}:{exc}",
                    }
                cell["upstream_eval_metrics"].update(lf_metrics)
                cell["upstream_eval_debug"]["lineageflow"] = (
                    "computed" if lf_metrics.get("status") == 1.0
                    else "blocked"
                )
        if kanzi_upstream_eval and model == "kanzi":
            cell["upstream_eval_debug"]["kanzi"] = "not_run"
            if run_kanzi_upstream_eval is None:
                cell["upstream_eval_debug"]["kanzi"] = "blocked"
            else:
                coords_lines: list = [
                    _extract_ca_coords_for_kanzi(baseline_trace),
                    _extract_ca_coords_for_kanzi(framework_trace),
                ]
                coords_path = upstream_out_dir / "samples.ca.txt"
                coords_path.write_text(
                    "\n".join(coords_lines) + "\n", encoding="utf-8",
                )
                try:
                    kz_metrics = run_kanzi_upstream_eval(
                        sequences_path=str(coords_path),
                        output_dir=str(upstream_out_dir / "kz_out"),
                        n_samples=int(upstream_n_samples),
                    )
                except Exception as exc:  # noqa: BLE001
                    kz_metrics = {
                        "status": 0.0,
                        "reason": f"runner_exception:{type(exc).__name__}:{exc}",
                    }
                cell["upstream_eval_metrics"].update(kz_metrics)
                cell["upstream_eval_debug"]["kanzi"] = (
                    "computed" if kz_metrics.get("status") == 1.0
                    else "blocked"
                )
        if flowmol3_upstream_eval and model in ("flowmol3", "flowmol3_v2"):
            cell["upstream_eval_debug"]["flowmol3"] = "not_run"
            if run_flowmol3_upstream_eval is None:
                cell["upstream_eval_debug"]["flowmol3"] = "blocked"
            elif not sampled_molecules:
                cell["upstream_eval_debug"]["flowmol3"] = "blocked_no_sampled_molecules"
            else:
                smiles_lines: list[str] = []
                for sm in sampled_molecules[: int(upstream_n_samples)]:
                    rd = getattr(sm, "rdkit_mol", None)
                    if rd is None:
                        continue
                    try:
                        from rdkit import Chem  # type: ignore  # local import
                        smi = Chem.MolToSmiles(rd)
                    except Exception:
                        continue
                    if smi:
                        smiles_lines.append(smi)
                smiles_path = upstream_out_dir / "samples.smi"
                smiles_path.write_text(
                    "\n".join(smiles_lines) + "\n", encoding="utf-8",
                )
                if not smiles_lines:
                    cell["upstream_eval_debug"]["flowmol3"] = "blocked_no_smiles"
                else:
                    try:
                        fm_metrics = run_flowmol3_upstream_eval(
                            smiles_list=str(smiles_path),
                            output_dir=str(upstream_out_dir / "fm_out"),
                            reference=str(paper_reference),
                            pb_workers=2,
                        )
                    except Exception as exc:  # noqa: BLE001
                        fm_metrics = {
                            "status": 0.0,
                            "reason": f"runner_exception:{type(exc).__name__}:{exc}",
                        }
                    cell["upstream_eval_metrics"].update(fm_metrics)
                    cell["upstream_eval_debug"]["flowmol3"] = (
                        "computed" if fm_metrics.get("status") == 1.0
                        else "blocked"
                    )
    # Wave 91 Phase 3 (retry) — Kanzi framework-arm paper-metric block.
    if kanzi_framework_paper_metrics and model == "kanzi":
        cell["kanzi_framework_paper_metrics_marker"] = "skipped"
        cell["kanzi_framework_paper_metrics_debug"] = {
            "reason": "not_run",
            "kanzi_framework_paper_metrics_flag": bool(kanzi_framework_paper_metrics),
            "n_steps_decoder": len(100),
        }
        cell["kanzi_framework_paper_metrics"] = None
        try:
            kfm_metrics, kfm_marker, kfm_dbg = (
                _resolve_metric("_compute_kanzi_framework_paper_metric")(
                    adapter=adapter,
                    baseline_trace=baseline_trace,
                    framework_trace=framework_trace,
                    seed=int(seed), nfe=int(nfe),
                )
            )
        except Exception as exc:  # noqa: BLE001
            kfm_metrics = None
            kfm_marker = "blocked"
            kfm_dbg = {
                "reason": (
                    f"helper_raised: {type(exc).__name__}:{exc}"
                ),
            }
        cell["kanzi_framework_paper_metrics"] = kfm_metrics
        cell["kanzi_framework_paper_metrics_marker"] = kfm_marker
        cell["kanzi_framework_paper_metrics_debug"] = {
            **kfm_dbg,
            "kanzi_framework_paper_metrics_flag": bool(kanzi_framework_paper_metrics),
            "n_steps_decoder": len(100),
        }
    if baseline_value is None or framework_value is None:
        cell["delta_pct"] = None
        cell["signed_delta_pct"] = None
        cell["status"] = "PENDING"
    else:
        raw = (framework_value - baseline_value) / abs(baseline_value) if baseline_value != 0 else 0.0
        cell["delta_pct"] = raw
        if primary["direction"] == "lower_is_better":
            cell["signed_delta_pct"] = -raw
        elif primary["direction"] == "higher_is_better":
            cell["signed_delta_pct"] = raw
        else:
            cell["signed_delta_pct"] = -raw
        sat = primary["saturation_threshold"]
        if sat is not None:
            if primary["direction"] == "higher_is_better":
                at_sat = (
                    baseline_value >= sat * 0.99
                    and framework_value >= sat * 0.99
                )
            else:
                at_sat = (
                    baseline_value <= sat * 1.01
                    and framework_value <= sat * 1.01
                )
            cell["saturation_at_ceiling"] = bool(at_sat)
            if at_sat:
                cell["status"] = TIE_AT_SATURATION
            elif cell["signed_delta_pct"] > 0:
                cell["status"] = "SUPPORTED"
            elif cell["signed_delta_pct"] == 0:
                cell["status"] = "TIE"
            else:
                cell["status"] = "REGRESSION"
        else:
            cell["status"] = "MEASURED"
    cell["wallclock_baseline_s"] = round(baseline_wall, 4)
    cell["wallclock_framework_s"] = round(framework_wall, 4)
    cell["wallclock_ratio"] = round(
        framework_wall / baseline_wall, 4
    ) if baseline_wall > 0 else None
    return cell


def _extract_aa_for_fasta(trace: Any, model: str) -> str:
    """Extract a single AA string from ``trace`` for the LineageFlow FASTA.

    Wave 79 — LineageFlow upstream eval expects a FASTA file of
    decoded protein sequences. Synthetic-mode traces return an
    ``"M" * 30`` proxy so the upstream orchestrator has a parseable
    FASTA even when the v1 shim is in play.
    """
    if trace is None:
        return "M" * 30
    try:
        if model == "lineageflow":
            return _decode_lineageflow_idx_to_aa(
                getattr(trace, "endpoint", None)
                or getattr(trace, "states", None),
            )
        if model == "kanzi":
            return _decode_kanzi_idx_to_aa(
                getattr(trace, "endpoint", None)
                or getattr(trace, "states", None),
            )[0]
    except Exception:  # noqa: BLE001
        return "M" * 30
    return "M" * 30


def _extract_ca_coords_for_kanzi(trace: Any) -> str:
    """Extract a per-line ``x,y,z`` Å coordinate string for the Kanzi driver."""
    if trace is None:
        return ",".join(["0.0"] * 30)
    endpoint = getattr(trace, "endpoint", None) or getattr(trace, "states", None)
    if endpoint is None:
        return ",".join(["0.0"] * 30)
    try:
        import numpy as _np  # type: ignore
        arr = _np.asarray(endpoint, dtype=_np.float64).reshape(-1)
        return ",".join(f"{float(v):.4f}" for v in arr[:512])
    except Exception:  # noqa: BLE001
        return ",".join(["0.0"] * 30)


__all__ = [
    "_extract_aa_for_fasta",
    "_extract_ca_coords_for_kanzi",
    "_run_cell",
]