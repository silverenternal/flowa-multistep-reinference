"""Service catalog for adaptive reflow."""

from __future__ import annotations

from pocket_modules.mechanisms.library_contracts import service_catalog

SERVICE_MODULES = ("control_policy", "external_metric_feedback", "orchestration", "restart_memory")
SERVICE_ENTRYPOINTS = (
    "control_policy.adaptive_reflow_metric_priority_controls",
    "external_metric_feedback.adaptive_reflow_external_metric_controls",
    "restart_memory.adaptive_reflow_memory_restart_coords",
)


def available_services():
    return service_catalog(
        package=__package__ or "",
        modules=SERVICE_MODULES,
        service_entrypoints=SERVICE_ENTRYPOINTS,
    )


__all__ = ["SERVICE_ENTRYPOINTS", "SERVICE_MODULES", "available_services"]
