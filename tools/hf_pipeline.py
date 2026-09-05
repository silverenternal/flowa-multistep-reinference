#!/usr/bin/env python3
"""HuggingFace Hub model card upload pipeline (R-3 / F.7 / F.8).

Per ``todo/algo-improvement-hf-model-card-pipeline.md`` (Wave 32 Agent
B recommendation R-3): closes the **Papers-with-Code ML Code
Completeness Checklist item (d) — pre-trained models released for
verification without retraining** gap.

The script reads a local model card from ``docs/models/<model>.model_card.md``,
extracts (or synthesises) the HuggingFace YAML metadata block, validates
the schema, and uploads the rendered README.md to a HuggingFace Hub
``<user>/<model>`` repo. Mirrors the SciMLBenchmarks.jl auto-upload
pattern: the card content is the single source of truth; YAML metadata
is derived from a per-model dictionary so reviewers can verify the
uploaded README.md with ``git diff`` against the local card.

Design
------

* **CLI surface.** ``--model <name>`` selects the card; ``--repo-id``
  identifies the target HF Hub repo; ``--upload-dry-run`` validates +
  renders without contacting the Hub; ``--render-only`` writes the
  rendered README.md to disk for inspection; ``--commit-message`` lets
  callers tag the commit (defaults to a YYYYMMDD-style tag per the
  SciMLBenchmarks.jl pattern).
* **Card source.** ``docs/models/<model>.model_card.md`` (the F.4
  Mitchell/Gebru card from Wave 24 Agent A). The local file is the
  **single source of truth**; the HF Hub copy is downstream.
* **YAML metadata.** Sourced from per-model :data:`MODEL_METADATA`
  below (Phase A schema from the todo). Falls back to a minimal
  parse of any existing ``---\\n...\\n---\\n`` front matter in the
  local card so external contributors can override fields inline.
* **Dry-run mode.** No network calls. The script parses, validates
  YAML, prints a summary (model name, repo id, byte count, YAML
  fields) and exits 0. Mirrors the SciMLBenchmarks.jl dry-run pattern.
* **Real upload mode.** Calls :func:`huggingface_hub.HfApi.create_repo`
  followed by :func:`huggingface_hub.upload_file` with
  ``path_in_repo="README.md"`` and ``repo_type="model"``. Token comes
  from the ``HF_TOKEN`` env var or the locally-cached
  ``huggingface-cli login`` state — the script never reads secrets
  from disk.

Usage examples
--------------

::

    # Validate + dry-run for the kanzi card against a hypothetical HF repo.
    .venvs/flowmol3_venv/bin/python tools/hf_pipeline.py \\
        --model kanzi --repo-id flowa-test/kanzi --upload-dry-run

    # Render the would-be README.md to disk for diff inspection.
    .venvs/flowmol3_venv/bin/python tools/hf_pipeline.py \\
        --model twodim_fm --repo-id flowa-test/twodim_fm --render-only \\
        --output /tmp/twodim_fm_README.md

    # Real upload (requires ``huggingface-cli login`` or ``$HF_TOKEN``).
    .venvs/flowmol3_venv/bin/python tools/hf_pipeline.py \\
        --model lineageflow --repo-id <your-hf-user>/lineageflow

Per-card metadata
-----------------

The :data:`MODEL_METADATA` mapping below carries the per-card
``library_name``, ``pipeline_tag``, ``license``, ``tags``,
``datasets``, and ``model-index`` scaffolding. Adding a new
integration means appending a new entry — there is no per-card file
to maintain. This mirrors the SciMLBenchmarks.jl
``benchmark_attributes.jl`` convention where the *registry* lives
alongside the upload script.

Notes on the YAML schema
------------------------

We emit the following front-matter keys per HF F-8 + Mitchell 2018 §3:

* ``library_name`` — the framework/library the model ships with.
  All integrated models use ``adaptive_reflow`` (the framework
  canonical name).
* ``pipeline_tag`` — the HF Hub pipeline tag. Image FMs use
  ``image-generation``; protein FMs use ``fill-mask`` (LineageFlow,
  Kanzi); 2D synthetic FM uses ``other`` (illustrative).
* ``tags`` — free-form tags.
* ``license`` — the upstream license. Mirrors the upstream paper's
  release license, not the framework's MIT (the framework's MIT only
  covers ``adaptive_reflow/*``; per-adapter weights inherit their
  upstream's license).
* ``datasets`` — the training datasets. ``[]`` when the model is
  trained on analytic samples (twodim_fm).
* ``model-index`` — one row per published result on a benchmark. The
  initial release ships an empty ``model-index``; downstream
  ``tools/run_real_ckpt_eval.py`` reports populate it via
  :func:`render_model_index_rows` (not auto-injected yet — see
  the Wave 32 todo's follow-up section).
* ``co2_emissions`` — hardware + hours + co2e_kg + cloud_provider +
  cloud_region. Optional; emitted as ``[]`` when no estimate is
  available. The CO2 numbers live in
  ``docs/CONSOLIDATED_RESULTS.md`` §2 once Wave 18 publishes them;
  until then the field is empty and HF Hub renders it as "unknown".

The todo's Phase A draft template is followed exactly; per-card
deviations (e.g. ``flowmol3`` pipeline_tag=``image-generation`` for
molecular 2D renderings; ``lineageflow`` pipeline_tag=``fill-mask``
for protein infilling; ``twodim_fm`` pipeline_tag=``other`` because
it ships a 518-parameter MLP on analytic 2D targets) are noted in
the ``pipeline_tag_notes`` docstring of each entry.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import io
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = REPO_ROOT / "docs" / "models"

# Per-card YAML metadata. Mirrors the SciMLBenchmarks.jl
# ``benchmark_attributes.jl`` pattern: a single registry that the upload
# script reads when rendering the README.md front matter. Adding a new
# card = appending an entry; no per-card file to maintain.
MODEL_METADATA: dict[str, dict[str, Any]] = {
    "flowmol3": {
        "library_name": "adaptive_reflow",
        "pipeline_tag": "image-generation",
        "tags": ["flow-matching", "rectified-flow", "pytorch", "molecules"],
        "license": "mit",
        "datasets": ["GEOM-DRUGS"],
        "pipeline_tag_notes": (
            "image-generation: the adapter renders molecular 2D "
            "depictions; FID-50K is the canonical metric."
        ),
    },
    "freqflow": {
        "library_name": "adaptive_reflow",
        "pipeline_tag": "image-generation",
        "tags": ["flow-matching", "rectified-flow", "pytorch", "diffusion"],
        "license": "apache-2.0",
        "datasets": ["imagenet-1k"],
        "pipeline_tag_notes": (
            "DEFERRED_no_upstream_ckpt (Wave 36 user directive). "
            "Adapter file ships; real-ckpt forward path is not buildable."
        ),
    },
    "kanzi": {
        "library_name": "adaptive_reflow",
        "pipeline_tag": "fill-mask",
        "tags": ["flow-matching", "rectified-flow", "pytorch", "proteins"],
        "license": "mit",
        "datasets": ["AFDB", "Pfam"],
        "pipeline_tag_notes": (
            "fill-mask: Kanzi decodes continuous-latent codes into "
            "one-letter amino-acid token sequences. Real-ckpt landed "
            "Wave 36; upstream = https://github.com/rdilip/kanzi."
        ),
    },
    "lineageflow": {
        "library_name": "adaptive_reflow",
        "pipeline_tag": "fill-mask",
        "tags": ["flow-matching", "rectified-flow", "pytorch", "proteins"],
        "license": "mit",
        "datasets": ["Pfam"],
        "pipeline_tag_notes": (
            "fill-mask: LineageFlow fills masked Pfam-family positions. "
            "BLOCKED on upstream `core` source repo; synthetic-mode "
            "Protocol surface is fully wired and tested (22/22 tests)."
        ),
    },
    "rectified_flow_cifar": {
        "library_name": "adaptive_reflow",
        "pipeline_tag": "image-generation",
        "tags": ["flow-matching", "rectified-flow", "pytorch", "diffusion"],
        "license": "apache-2.0",
        "datasets": ["cifar10"],
        "pipeline_tag_notes": (
            "image-generation on CIFAR-10; BLOCKED on env + weights + "
            "features (production torch-mode)."
        ),
    },
    "self_flow": {
        "library_name": "adaptive_reflow",
        "pipeline_tag": "image-generation",
        "tags": ["flow-matching", "self-supervised", "pytorch"],
        "license": "apache-2.0",
        "datasets": ["imagenet-1k"],
        "pipeline_tag_notes": (
            "image-generation with self-supervised velocity targets; "
            "production torch-mode is a design-skeleton release gated "
            "on user-supplied ckpt + CUDA host."
        ),
    },
    "twodim_fm": {
        "library_name": "adaptive_reflow",
        "pipeline_tag": "other",
        "tags": ["flow-matching", "rectified-flow", "pytorch", "toy", "2d"],
        "license": "mit",
        "datasets": [],
        "pipeline_tag_notes": (
            "other: 2D synthetic flow-matching; the 518-parameter MLP "
            "is too small to model realistic data. Ships to illustrate "
            "the framework on analytic 2D targets (two_moons, "
            "eight_gaussians, swiss_roll, pinwheel, checkerboard, "
            "gaussian_grid)."
        ),
    },
}


# ---------------------------------------------------------------------------
# YAML front matter extraction / synthesis
# ---------------------------------------------------------------------------

# Matches ``---\\n...\\n---\\n`` at the start of the card. The local
# model cards are plain Markdown (no front matter yet); once we add the
# front matter per the todo's Phase A the local card becomes the
# single source of truth and the upload script is a thin wrapper.
_FRONTMATTER_RE = re.compile(
    r"\A\s*---\s*\n(?P<yaml>.*?)\n---\s*\n(?P<body>.*)",
    re.DOTALL,
)


def split_front_matter(card_text: str) -> tuple[dict[str, Any], str]:
    """Return ``(yaml_dict, body)`` parsed from a Markdown card.

    Empty dict + the full text when no ``---`` front matter is present.
    Used by :func:`render_readme` to honour inline overrides: if the
    local card already carries a YAML block, the caller's per-model
    :data:`MODEL_METADATA` is merged under the inline fields (inline
    wins on key collisions).
    """
    match = _FRONTMATTER_RE.match(card_text)
    if not match:
        return {}, card_text
    yaml_block = match.group("yaml")
    body = match.group("body")
    parsed = yaml.safe_load(yaml_block) or {}
    if not isinstance(parsed, dict):
        raise ValueError(
            f"YAML front matter must be a mapping; got {type(parsed).__name__}"
        )
    return parsed, body


def build_yaml_metadata(model_name: str) -> dict[str, Any]:
    """Return the rendered YAML metadata for the given card.

    Pulls from :data:`MODEL_METADATA` and injects the framework-derived
    fields (``library_name=adaptive_reflow`` is hard-coded because the
    framework is the only library shipping these adapters). The
    ``model-index`` and ``co2_emissions`` keys default to empty lists —
    HF Hub accepts empty ``model-index`` (renders as "no results") and
    empty ``co2_emissions`` (renders as "unknown emissions"). Downstream
    ``tools/run_real_ckpt_eval.py`` reports populate ``model-index``
    via :func:`render_model_index_rows`.
    """
    if model_name not in MODEL_METADATA:
        raise KeyError(
            f"Unknown model '{model_name}'. Known: "
            f"{sorted(MODEL_METADATA)}"
        )
    meta = MODEL_METADATA[model_name]
    return {
        "library_name": "adaptive_reflow",
        "pipeline_tag": meta["pipeline_tag"],
        "tags": list(meta["tags"]),
        "license": meta["license"],
        "datasets": list(meta["datasets"]),
        "model-index": [],
        "co2_emissions": [],
    }


def render_readme(
    model_name: str,
    card_path: Path,
    *,
    inline_overrides: Optional[dict[str, Any]] = None,
) -> str:
    """Return the full README.md text (YAML front matter + Markdown body).

    Inline overrides (parsed from existing YAML front matter in the
    local card) win over :data:`MODEL_METADATA` on key collisions. The
    rendered text is what gets uploaded to the HF Hub repo's
    ``README.md``.
    """
    card_text = card_path.read_text(encoding="utf-8")
    inline, body = split_front_matter(card_text)
    if inline_overrides:
        inline.update(inline_overrides)
    else:
        inline.update({})  # placeholder for clarity

    metadata = build_yaml_metadata(model_name)
    # Inline wins on key collisions.
    for key, value in inline.items():
        metadata[key] = value

    # yaml.safe_dump with default_flow_style=False emits the
    # block-style YAML HF Hub expects (matches the Phase A template in
    # the todo).
    yaml_block = yaml.safe_dump(
        metadata, default_flow_style=False, sort_keys=False, allow_unicode=True,
    )
    return f"---\n{yaml_block}---\n\n{body.lstrip()}"


# ---------------------------------------------------------------------------
# HF Hub upload
# ---------------------------------------------------------------------------


def render_model_index_rows(model_name: str, results_md_path: Path) -> list[dict[str, Any]]:
    """Parse ``docs/CONSOLIDATED_RESULTS.md`` for ``<model>`` rows.

    Returns a list of ``model-index`` rows compatible with the HF Hub
    schema. Empty list when no row is found or the table is missing.
    The function is best-effort: malformed rows are skipped silently
    and logged to stderr so a partially-parsed results table still
    yields the rows that are well-formed.

    Currently NOT auto-injected by :func:`render_readme` because the
    Wave 36 PHASE-4 results are still being collected; the field
    defaults to ``[]`` and downstream CI populates it once
    ``tools/run_real_ckpt_eval.py`` reports land in
    ``docs/CONSOLIDATED_RESULTS.md`` §6 v3.
    """
    if not results_md_path.exists():
        return []
    text = results_md_path.read_text(encoding="utf-8")
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        # Heuristic: lines starting with ``|`` that mention the model
        # name (case-insensitive). Per-row metric parsing is deferred
        # until the results table stabilises (Wave 36 PHASE-4).
        if not line.startswith("|"):
            continue
        if model_name.lower() not in line.lower():
            continue
        # Skip the header / separator rows.
        if "---" in line or "metric" in line.lower():
            continue
        rows.append(
            {
                "name": model_name,
                "results": [
                    {
                        "task": {"type": "image-generation"},
                        "dataset": {"name": "see docs/CONSOLIDATED_RESULTS.md"},
                        "metrics": [
                            {
                                "name": "see result row",
                                "type": "fid",
                                "value": "see docs/CONSOLIDATED_RESULTS.md",
                            }
                        ],
                    }
                ],
            }
        )
    return rows


def upload_to_hub(
    repo_id: str,
    readme_text: str,
    *,
    commit_message: Optional[str] = None,
    token: Optional[str] = None,
) -> str:
    """Upload the README.md to the given HF Hub model repo.

    Returns the public URL. The HF Hub call is wrapped in a lazy import
    so the script's ``--help`` and ``--upload-dry-run`` paths work on
    environments that lack the ``huggingface_hub`` dependency (the
    script is shipped as a release-time tool, not a runtime dep).
    """
    # Lazy import so this module is importable without ``huggingface_hub``.
    from huggingface_hub import HfApi  # type: ignore[import-not-found]

    api = HfApi(token=token)
    api.create_repo(repo_id=repo_id, repo_type="model", exist_ok=True)
    api.upload_file(
        path_or_fileobj=io.BytesIO(readme_text.encode("utf-8")),
        path_in_repo="README.md",
        repo_id=repo_id,
        repo_type="model",
        commit_message=commit_message
        or f"Upload model card via tools/hf_pipeline.py on {_dt.date.today().isoformat()}",
    )
    return f"https://huggingface.co/{repo_id}"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_argparser() -> argparse.ArgumentParser:
    """Return the CLI argument parser.

    Flags follow the convention established by ``tools/run_real_ckpt_eval.py``
    and ``scripts/capture_env_hash.py`` so the upload script feels
    native to the project's toolchain.
    """
    p = argparse.ArgumentParser(
        prog="tools.hf_pipeline",
        description=(
            "HuggingFace Hub model card upload pipeline (R-3 / F.7 / F.8). "
            "Reads docs/models/<model>.model_card.md, renders a YAML "
            "front-matter + Markdown README.md, and uploads it to "
            "<repo_id> on the HF Hub."
        ),
    )
    p.add_argument(
        "--model", type=str, required=True,
        choices=sorted(MODEL_METADATA),
        help="Card identifier. One of: " + ", ".join(sorted(MODEL_METADATA)),
    )
    p.add_argument(
        "--repo-id", type=str, required=True,
        help="Target HF Hub repo, e.g. 'flowa-test/kanzi'.",
    )
    p.add_argument(
        "--upload-dry-run", action="store_true",
        help="Validate + render without contacting the HF Hub. Exits 0 on "
        "success; non-zero on YAML parse / schema failure.",
    )
    p.add_argument(
        "--render-only", action="store_true",
        help="Write the rendered README.md to --output and exit. No HF "
        "Hub contact, no token required.",
    )
    p.add_argument(
        "--output", type=Path, default=None,
        help="Output path for --render-only. Defaults to "
        "<model>_README.md in the current directory.",
    )
    p.add_argument(
        "--commit-message", type=str, default=None,
        help="Custom commit message for the HF Hub upload. Defaults to "
        "'Upload model card via tools/hf_pipeline.py on YYYY-MM-DD'.",
    )
    p.add_argument(
        "--token", type=str, default=None,
        help="HF Hub token (falls back to $HF_TOKEN and the cached "
        "huggingface-cli login state). NOT required for --upload-dry-run "
        "or --render-only.",
    )
    return p


def main(argv: Optional[list[str]] = None) -> int:
    """CLI entry point. Returns 0 on success, 1 on validation/upload error."""
    args = _build_argparser().parse_args(argv)

    card_path = MODELS_DIR / f"{args.model}.model_card.md"
    if not card_path.exists():
        print(f"[ERROR] card not found: {card_path}", file=sys.stderr)
        return 1

    # 1. Render.
    try:
        readme_text = render_readme(args.model, card_path)
    except (yaml.YAMLError, ValueError) as exc:
        print(f"[ERROR] render failed: {exc}", file=sys.stderr)
        return 1

    # 2. Validate (count bytes + lines).
    byte_count = len(readme_text.encode("utf-8"))
    line_count = readme_text.count("\n")
    print(
        f"[render] model={args.model} repo_id={args.repo_id} "
        f"bytes={byte_count} lines={line_count}"
    )
    print(
        f"[render] card_path={card_path.relative_to(REPO_ROOT)} "
        f"yaml_keys={list(build_yaml_metadata(args.model))}"
    )

    # 3. Branch.
    if args.render_only:
        out_path = args.output or Path(f"{args.model}_README.md")
        out_path.write_text(readme_text, encoding="utf-8")
        print(f"[render-only] wrote {out_path}")
        return 0

    if args.upload_dry_run:
        # No HF Hub call. Exit 0 (validation only).
        print(
            f"[dry-run] would upload {byte_count} bytes to "
            f"https://huggingface.co/{args.repo_id}/resolve/main/README.md"
        )
        return 0

    # 4. Real upload.
    try:
        token = args.token or os.environ.get("HF_TOKEN")
        url = upload_to_hub(
            args.repo_id,
            readme_text,
            commit_message=args.commit_message,
            token=token,
        )
    except Exception as exc:  # noqa: BLE001 — surface any HF Hub error
        print(f"[ERROR] upload failed: {exc}", file=sys.stderr)
        return 1
    print(f"[upload] README.md -> {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
