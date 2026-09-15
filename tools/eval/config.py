"""Run-profile YAML loader for the eval harness.

OWNER: Wave 112.B Agent — Commit C-4 (config infra).

Reads per-model run profiles from ``configs/runs/<model>_<purpose>.yaml`` and
validates the schema described in ``docs/audit/wave111-b-config-scattering-audit.md``
§2 + ``docs/audit/wave111-data-linkage-plan.md`` §4.

Resolution order is **CLI flag > YAML value > module-level default**. The
canonical CLI (``tools/eval/cli.py``) accepts ``--config <yaml>`` and overrides
nothing by default — the YAML profile is the new default surface, CLI flags are
the override surface (not the other way around).

Schema (required keys):
    model, seed, nfe_budgets, max_records, force_mode, metric_mode

Schema (optional keys):
    composite_metric, n_rounds, n_molecules, pb_engine, restart_min_nfe,
    paper_metrics, paper_reference, kanzi_upstream_eval,
    kanzi_framework_paper_metrics, flowmol3_upstream_eval,
    lineageflow_upstream_eval, upstream_n_samples, adapter_force_mode,
    adapter_num_steps, adapter_solver, output_filename

Usage:
    from tools.eval.config import load_run_profile
    cfg = load_run_profile(pathlib.Path("configs/runs/kanzi_n1000_baseline.yaml"))
    seed = cfg["seed"]
"""
from __future__ import annotations

import pathlib
import re
import sys
from typing import Any

import yaml

# Schema: required vs optional keys, plus per-key type validators.
# Wave 111.B design — see docs/audit/wave111-b-config-scattering-audit.md §2.
REQUIRED_KEYS: tuple[str, ...] = (
    "model",
    "seed",
    "nfe_budgets",
    "max_records",
    "force_mode",
    "metric_mode",
)

ALLOWED_OPTIONAL_KEYS: tuple[str, ...] = (
    "composite_metric",
    "n_rounds",
    "n_molecules",
    "pb_engine",
    "restart_min_nfe",
    "paper_metrics",
    "paper_reference",
    "kanzi_upstream_eval",
    "kanzi_framework_paper_metrics",
    "flowmol3_upstream_eval",
    "lineageflow_upstream_eval",
    "upstream_n_samples",
    "adapter_force_mode",
    "adapter_num_steps",
    "adapter_solver",
    "output_filename",
)

ALLOWED_KEYS: frozenset[str] = frozenset(REQUIRED_KEYS + ALLOWED_OPTIONAL_KEYS)

# Subset of keys that map 1:1 to canonical CLI flags (used by tools/eval/cli.py
# to plumb YAML -> argparse defaults). Order matches the YAML schema in §4 of
# the Wave 111 plan.
_CLI_FLAG_MAP: dict[str, str] = {
    "seed": "seed",                          # canonical CLI uses --seeds (CSV)
    "composite_metric": "composite_metric",
    "n_rounds": "n_rounds",
    "n_molecules": "n_molecules",
    "pb_engine": "pb_engine",
    "restart_min_nfe": "restart_min_nfe",
    "paper_metrics": "paper_metrics",
    "paper_reference": "paper_reference",
    "kanzi_upstream_eval": "kanzi_upstream_eval",
    "kanzi_framework_paper_metrics": "kanzi_framework_paper_metrics",
    "flowmol3_upstream_eval": "flowmol3_upstream_eval",
    "lineageflow_upstream_eval": "lineageflow_upstream_eval",
    "upstream_n_samples": "upstream_n_samples",
}


class ConfigError(ValueError):
    """Raised on missing required keys, unknown keys, or type errors."""


def _validate_key_types(cfg: dict[str, Any]) -> None:
    """Per-key type validation. Raises ConfigError on type mismatch."""
    # model: str
    if not isinstance(cfg["model"], str):
        raise ConfigError(f"key 'model' must be str, got {type(cfg['model']).__name__}")
    # seed: int
    if not isinstance(cfg["seed"], int) or isinstance(cfg["seed"], bool):
        raise ConfigError(f"key 'seed' must be int, got {type(cfg['seed']).__name__}")
    # nfe_budgets: list[int]
    nfe = cfg["nfe_budgets"]
    if not isinstance(nfe, list) or not all(isinstance(x, int) and not isinstance(x, bool) for x in nfe):
        raise ConfigError(
            f"key 'nfe_budgets' must be list[int], got {type(nfe).__name__}"
        )
    if not nfe:
        raise ConfigError("key 'nfe_budgets' must be non-empty")
    # max_records: int
    if not isinstance(cfg["max_records"], int) or isinstance(cfg["max_records"], bool):
        raise ConfigError(
            f"key 'max_records' must be int, got {type(cfg['max_records']).__name__}"
        )
    if cfg["max_records"] < 0:
        raise ConfigError(f"key 'max_records' must be >= 0, got {cfg['max_records']}")
    # force_mode: synthetic|real|auto
    if cfg["force_mode"] not in ("synthetic", "real", "auto"):
        raise ConfigError(
            f"key 'force_mode' must be synthetic|real|auto, got {cfg['force_mode']!r}"
        )
    # metric_mode: synthetic|real|auto
    if cfg["metric_mode"] not in ("synthetic", "real", "auto"):
        raise ConfigError(
            f"key 'metric_mode' must be synthetic|real|auto, got {cfg['metric_mode']!r}"
        )

    # Optional: composite_metric
    if "composite_metric" in cfg:
        v = cfg["composite_metric"]
        if v not in (None, "synthetic", "real", "auto"):
            raise ConfigError(
                f"key 'composite_metric' must be None|synthetic|real|auto, got {v!r}"
            )
    # Optional: n_rounds, n_molecules, restart_min_nfe, upstream_n_samples
    for k in ("n_rounds", "n_molecules", "restart_min_nfe", "upstream_n_samples"):
        if k in cfg:
            v = cfg[k]
            if not isinstance(v, int) or isinstance(v, bool):
                raise ConfigError(f"key '{k}' must be int, got {type(v).__name__}")
            if v < 0:
                raise ConfigError(f"key '{k}' must be >= 0, got {v}")
    # Optional: pb_engine
    if "pb_engine" in cfg:
        v = cfg["pb_engine"]
        if v not in (None, "uff", "xtb"):
            raise ConfigError(
                f"key 'pb_engine' must be None|uff|xtb, got {v!r}"
            )
    # Optional: paper_reference
    if "paper_reference" in cfg:
        v = cfg["paper_reference"]
        if v not in ("GEOM_DRUGS", "NCI_first_5K_proxy"):
            raise ConfigError(
                f"key 'paper_reference' must be GEOM_DRUGS|NCI_first_5K_proxy, got {v!r}"
            )
    # Optional: paper_metrics + upstream-eval flags (YAML bools; validator
    # accepts both bool and str since YAML scalars coerce freely).
    for k in (
        "paper_metrics",
        "kanzi_upstream_eval",
        "kanzi_framework_paper_metrics",
        "flowmol3_upstream_eval",
        "lineageflow_upstream_eval",
    ):
        if k in cfg and not isinstance(cfg[k], (bool, str)):
            raise ConfigError(
                f"key '{k}' must be bool|str, got {type(cfg[k]).__name__}"
            )
    # adapter_force_mode / adapter_solver: always str.
    for k in ("adapter_force_mode", "adapter_solver"):
        if k in cfg and not isinstance(cfg[k], str):
            raise ConfigError(
                f"key '{k}' must be str, got {type(cfg[k]).__name__}"
            )
    # adapter_num_steps must be int
    if "adapter_num_steps" in cfg:
        v = cfg["adapter_num_steps"]
        if not isinstance(v, int) or isinstance(v, bool):
            raise ConfigError(
                f"key 'adapter_num_steps' must be int, got {type(v).__name__}"
            )
    # output_filename: str
    if "output_filename" in cfg and not isinstance(cfg["output_filename"], str):
        raise ConfigError(
            f"key 'output_filename' must be str, got {type(cfg['output_filename']).__name__}"
        )


def _extract_version(path: pathlib.Path) -> str:
    """Extract the `# Profile version: YYYY-MM-DD (Wave XXX)` line.

    Falls back to ``unknown`` if not found; missing version is not a hard error
    (the loader prints a warning rather than failing).
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return "unknown"
    m = re.search(r"#\s*Profile version:\s*(\d{4}-\d{2}-\d{2})\s*\(([^)]+)\)", text)
    if m:
        return f"{m.group(1)} ({m.group(2)})"
    return "unknown"


def load_run_profile(path: pathlib.Path | str) -> dict[str, Any]:
    """Load + validate a run-profile YAML.

    Returns a flat dict with the schema keys (see module docstring).
    Raises :class:`ConfigError` on missing required keys, unknown keys, or
    type errors. Prints ``[PROFILE] <path> v=<ver> seed=<n> force_mode=<m>
    nfe=<list> N=<n>`` to stderr on success (visible in the cell loop).

    The CLI invocation contract is::

        load_run_profile(pathlib.Path("configs/runs/kanzi_n1000_baseline.yaml"))

    The returned dict is the **single source of truth** for the run profile;
    CLI flags override its values one-flag-at-a-time (see ``tools/eval/cli.py``
    resolution helper).
    """
    p = pathlib.Path(path)
    if not p.is_file():
        raise ConfigError(f"profile not found: {p}")

    # PyYAML safe_load — flat key-value (no nested includes per Wave 111.B §4).
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ConfigError(
            f"profile root must be a mapping (key-value), got {type(raw).__name__}"
        )

    # Unknown keys first (clearer error than missing-key).
    unknown = sorted(set(raw) - ALLOWED_KEYS)
    if unknown:
        raise ConfigError(
            f"profile {p} has unknown keys: {unknown}. "
            f"Allowed: {sorted(ALLOWED_KEYS)}"
        )

    # Missing required keys.
    missing = sorted(set(REQUIRED_KEYS) - set(raw))
    if missing:
        raise ConfigError(
            f"profile {p} missing required keys: {missing}. "
            f"Required: {list(REQUIRED_KEYS)}"
        )

    # Type + value validation.
    _validate_key_types(raw)

    # Print summary on load — visible in the eval cell loop.
    version = _extract_version(p)
    print(
        f"[PROFILE] {p} v={version} "
        f"seed={raw['seed']} force_mode={raw['force_mode']} "
        f"nfe={raw['nfe_budgets']} N={raw['max_records']}",
        file=sys.stderr,
    )

    return raw


def resolve(
    cli_value: Any,
    yaml_value: Any,
    default: Any,
) -> Any:
    """CLI flag > YAML value > module default.

    Used by ``tools/eval/cli.py`` to apply the resolution order per-flag::

        args.seed = resolve(cli_seeds, yaml_seed, default_seeds)
    """
    if cli_value is not None:
        return cli_value
    if yaml_value is not None:
        return yaml_value
    return default


__all__ = [
    "ALLOWED_KEYS",
    "ALLOWED_OPTIONAL_KEYS",
    "ConfigError",
    "REQUIRED_KEYS",
    "load_run_profile",
    "resolve",
]
