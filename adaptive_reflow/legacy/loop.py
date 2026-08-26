"""Package-local executable loop for adaptive reflow."""

from __future__ import annotations

import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

if __package__ in {None, ""}:
    for parent in Path(__file__).resolve().parents:
        if (parent / "pocket_modules").is_dir():
            sys.path.insert(0, str(parent))
            __package__ = ".".join(Path(__file__).resolve().parent.relative_to(parent).parts)
            break

from pocket_modules.flowa_core import FlowKernel, FlowPanel
from pocket_modules.mechanism_runtime import MechanismAdapter, MechanismLoop
from pocket_modules.mechanisms.local_loop import json_default, run_package_local_loop

from .mechanism_adapter import AdaptiveReflowMechanism


def run_local_loop(payload: Mapping[str, Any] | None = None, metrics: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        run_package_local_loop(
            mechanism=AdaptiveReflowMechanism(),
            payload=payload,
            metrics=metrics,
            kernel_cls=FlowKernel,
            panel_cls=FlowPanel,
            adapter_cls=MechanismAdapter,
            loop_cls=MechanismLoop,
        ),
    )


if __name__ == "__main__":
    import json

    print(json.dumps(run_local_loop(), indent=2, sort_keys=True, default=json_default))


__all__ = ["run_local_loop"]
