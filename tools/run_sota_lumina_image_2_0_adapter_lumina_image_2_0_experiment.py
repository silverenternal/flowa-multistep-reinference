"""SOTA Lumina-Image 2.0 experiment harness — STUB.

This is a STUB harness. The Lumina-Image 2.0 SOTA experiment is
described in
``docs/r4-survey/07-sota-experiment-protocol.md`` but the full
implementation requires:

* The published ``Alpha-VLLM/Lumina-Image-2.0`` checkpoint
  (consolidated.00-of-01.pth + text_encoder ~ 14 GB + transformer
  ~ 18 GB + VAE), totalling ~ 52.65 GB. Per
  ``weights_metadata.json`` ``download_status=skipped_too_large``,
  this must be supplied by the user.
* A GPU host (CPU-only execution is ~5-15 minutes per 50-step sample
  at 1024x1024 with bfloat16, which breaks the protocol's "1-4 hours
  per checkpoint" budget).
* A Gemma2 license on huggingface.co/google/gemma-2-2b -- the text
  encoder is a gated model; ``--hf-token`` or ``HUGGINGFACE_HUB_TOKEN``
  must be supplied.
* The GenEval / DPG / T2I-CompBench evaluator packages (geva,
  dpg_bench, t2i_compbench) running in a separate evaluator venv.

This stub does not invoke any of the heavy dependencies. It prints a
TODO message and exits. See ``docs/r4-survey/07-sota-experiment-protocol.md``
for the full seven-step runbook and the wiring plan.

Usage
-----

::

    # The harness is a stub -- it prints a TODO message and exits.
    python tools/run_sota_lumina_image_2_0_adapter_lumina_image_2_0_experiment.py \\
        --help
"""

from __future__ import annotations

import argparse
import sys


def _build_argparser() -> argparse.ArgumentParser:
    """Build the canonical LuminaImage2.0 SOTA experiment CLI surface.

    The arguments mirror the published experiment protocol so future
    implementers can fill in the bodies without changing the CLI.
    """
    parser = argparse.ArgumentParser(
        prog="run_sota_lumina_image_2_0_adapter_lumina_image_2_0_experiment.py",
        description=(
            "SOTA Lumina-Image 2.0 flow-matching experiment "
            "(STUB; see docs/r4-survey/07-sota-experiment-protocol.md)."
        ),
    )
    parser.add_argument(
        "--checkpoint",
        type=str,
        default="data/Lumina-Image-2.0",
        help="Path to the Lumina-Image 2.0 checkpoint directory.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/lumina_image_2_0_out",
        help="Output directory for samples, comparisons, and metrics.",
    )
    parser.add_argument(
        "--n-prompts",
        type=int,
        default=100,
        help="Number of prompts to draw from the curated prompt suite.",
    )
    parser.add_argument(
        "--n-rounds",
        type=int,
        default=20,
        help="Number of FlowA re-inference rounds per scheduler.",
    )
    parser.add_argument(
        "--framework-samples",
        type=int,
        default=500,
        help="Number of independent chains to aggregate per scheduler.",
    )
    parser.add_argument(
        "--guidance-scale",
        type=float,
        default=4.0,
        help="CFG guidance scale (paper default 4.0).",
    )
    parser.add_argument(
        "--num-steps",
        type=int,
        default=50,
        help="Per-round ODE integration steps (paper default 50).",
    )
    parser.add_argument(
        "--cfg-trunc-ratio",
        type=float,
        default=0.25,
        help="CFG-Trunc ratio (paper default 0.25).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Deterministic seed for the prompt-sampler + RNG chain.",
    )
    parser.add_argument(
        "--text-encoder-cache",
        type=str,
        default="data/lumina_text_embeddings.npz",
        help="Path to the pre-cached Gemma2 text-embedding store.",
    )
    parser.add_argument(
        "--no-vae-decode",
        action="store_true",
        help="Skip the FLUX.1-dev VAE decode step (latent-only).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Print a TODO message and exit.

    The full implementation lives behind the dependency blockers
    listed in the module docstring; this stub is the load-bearing
    "I exist at the documented path" entry point.
    """
    parser = _build_argparser()
    args = parser.parse_args(argv)
    print(
        "[run_sota_lumina_image_2_0_adapter_lumina_image_2_0_experiment] "
        "STUB: the Lumina-Image 2.0 SOTA harness is not yet implemented.\n"
        "Required dependency blockers (see module docstring):\n"
        "  1. Alpha-VLLM/Lumina-Image-2.0 checkpoint (~52.65 GB) --\n"
        "     weights_metadata.json declares download_status=skipped_too_large;\n"
        "     the user must supply this per\n"
        "     docs/r4-survey/07-sota-experiment-protocol.md section 2.\n"
        "  2. GPU host (CPU-only execution breaks the protocol budget).\n"
        "  3. Gemma2 license (gated model; --hf-token required).\n"
        "  4. GenEval / DPG / T2I-CompBench evaluator venv (separate from\n"
        "     the framework's repo, per the FID-venv pattern).\n"
        "Parsed args:\n"
        f"  checkpoint={args.checkpoint}\n"
        f"  output_dir={args.output_dir}\n"
        f"  n_prompts={args.n_prompts}\n"
        f"  n_rounds={args.n_rounds}\n"
        f"  framework_samples={args.framework_samples}\n"
        f"  guidance_scale={args.guidance_scale}\n"
        f"  num_steps={args.num_steps}\n"
        f"  cfg_trunc_ratio={args.cfg_trunc_ratio}\n"
        f"  seed={args.seed}\n"
        f"  text_encoder_cache={args.text_encoder_cache}\n"
        f"  no_vae_decode={args.no_vae_decode}\n",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())