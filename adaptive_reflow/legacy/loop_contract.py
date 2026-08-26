"""Local loop contract for adaptive reflow."""

from __future__ import annotations

from pocket_modules.mechanisms.library_contracts import build_local_loop_contract


def build_loop_contract():
    return build_local_loop_contract(
        mechanism_id="inference.adaptive_reflow",
        metric_family="binding_gnina",
        hooks=("condition_delta", "ode_step", "evaluator_feedback"),
        service_modules=("control_policy", "external_metric_feedback", "restart_memory"),
        command=(
            "python scripts/run_metric_family_workbench.py --metric-family binding_gnina "
            "--config configs/mechanisms/flowa_metric_family_bundles.json"
        ),
    )


__all__ = ["build_loop_contract"]
