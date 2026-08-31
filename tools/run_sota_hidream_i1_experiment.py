"""HiDream-I1 SOTA experiment harness — STUB (R17 design-only release).

This module is a **stub** for the HiDream-I1 text-to-image SOTA
experiment harness. The full harness (analogous to
``tools/run_sota_cifar_experiment.py`` but text-conditional + 1024x1024)
is intentionally **not implemented** because:

1. HiDream-I1 is a 17B-parameter sparse-DiT model that requires
   ~64GB HBM at fp16 inference (~34GB DiT weights + ~30GB across
   four text encoders: CLIP-L, CLIP-G, T5-XXL, Llama-3.1-8B). The
   sandbox is CPU-only and cannot host this workload.
2. The published ``HiDream-ai/HiDream-I1-{Full,Dev,Fast}`` HuggingFace
   repos are unreachable from the sandbox (no HF token; the
   pre-acquired ``weights_metadata.json`` has no ``repo_id`` slot).
3. The CIFAR FID harness (``C:/.../flowa_fid_env`` /
   ``tools/compute_cifar_fid.py``) cannot be reused because it is
   InceptionV3-only and HiDream-I1's published metrics intentionally
   exclude FID (paper §4, Tables 1-3: DPG-Bench + GenEval + HPSv2.1).
4. DPG-Bench, GenEval, and HPSv2.1 each require their own eval model
   (MiniCPM-V 2.6, GenEval detection+text-match, HPSv2.1 CLIP-H
   respectively) — all separate dependencies that are out of scope for
   the skeleton release.

The adapter side is fully wired: see
``adaptive_reflow/adapters/hidream_i1.py`` and the test suite at
``tests/test_adapters/test_hidream_i1.py`` (22 tests, all passing).
The ``tools/run_sota_hidream_i1_experiment.py`` stub should be
implemented by a user who has:

* A CUDA host with >=40GB HBM (A100 40GB minimum for the Fast
  variant fp16; H100/H800 80GB for the Full variant without
  quantization).
* Local copies of ``HiDream-ai/HiDream-I1-{Full,Dev,Fast}`` weights
  (or equivalents) + the FLUX.1 VAE weights.
* The four text encoders (CLIP-L/14, CLIP-G/14, T5-XXL,
  Llama-3.1-8B-Instruct).
* An evaluation stack for at least one of DPG-Bench / GenEval /
  HPSv2.1 / FID-against-MS-COCO-30K.

The expected harness surface (for reference, when implemented):

.. code-block:: text

    $ python tools/run_sota_hidream_i1_experiment.py \\
        --prompts-csv data/dpg_bench_prompts.csv \\
        --variant full \\
        --eval-set dpg-bench \\
        --n-samples 4 \\
        --n-rounds 20 \\
        --device cuda --dtype bf16 \\
        --output-dir ./hidream_i1_out

Required CLI surface (when implemented):

* ``--prompts-csv`` — path to the prompt set CSV (DPG-Bench 1K /
  GenEval 553 / HPSv2.1 3200 / MS-COCO-30K captions).
* ``--variant {full,dev,fast}`` — HiDream-I1 distillation variant.
* ``--eval-set {dpg-bench, geneval, hpsv2, ms-coco-fid}`` — evaluation
  metric to dispatch.
* ``--n-samples`` — samples per prompt (1 for DPG, >=4 for
  GenEval/HPSv2).
* ``--n-rounds`` — number of FlowA re-inference rounds.
* ``--device {cpu,cuda,cuda:0,...}`` — inference device.
* ``--dtype {fp16,bf16,fp8-quantized}`` — model dtype.
* ``--output-dir`` — output directory for per-scheduler results.
* ``--schedulers`` — comma-separated list of (cosine, codim,
  evidence, freetraj).

Tasks satisfied
---------------

* None (harness is a stub; the adapter design is documented in
  ``docs/r4-survey/`` §HiDream-I1 + the adapter module docstring).
"""

from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path
from typing import Sequence


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_sota_hidream_i1_experiment",
        description=(
            "HiDream-I1 SOTA experiment harness (R17 stub; see module "
            "docstring for the unimplemented CLI surface)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--prompts-csv",
        type=Path,
        default=None,
        help="Path to the prompt set CSV (DPG-Bench 1K / GenEval 553 / HPSv2.1 3200).",
    )
    parser.add_argument(
        "--variant",
        type=str,
        default="full",
        choices=("full", "dev", "fast"),
        help="HiDream-I1 distillation variant (full=50 NFE, dev=28 NFE, fast=14 NFE).",
    )
    parser.add_argument(
        "--eval-set",
        type=str,
        default="dpg-bench",
        choices=("dpg-bench", "geneval", "hpsv2", "ms-coco-fid"),
        help="Evaluation metric to dispatch.",
    )
    parser.add_argument(
        "--n-samples",
        type=int,
        default=16,
        help="Samples per prompt (1 for DPG, >=4 for GenEval/HPSv2).",
    )
    parser.add_argument(
        "--n-rounds",
        type=int,
        default=20,
        help="Number of FlowA re-inference rounds.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="Inference device (cuda:0 recommended for HiDream-I1).",
    )
    parser.add_argument(
        "--dtype",
        type=str,
        default="bf16",
        choices=("fp16", "bf16", "fp8-quantized"),
        help="Model dtype (fp8-quantized requires bitsandbytes / quanto).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./hidream_i1_out"),
        help="Output directory for per-scheduler results.",
    )
    parser.add_argument(
        "--schedulers",
        type=str,
        default="cosine,codim,evidence,freetraj",
        help="Comma-separated list of schedulers (default: 4 canonical schedulers).",
    )
    parser.add_argument(
        "--weights-path",
        type=Path,
        default=None,
        help="Explicit path to the HiDream-I1 weights file (auto-detected when None).",
    )
    return parser


def _print_stub_message(args: argparse.Namespace) -> None:
    msg = textwrap.dedent(
        f"""
        ============================================================================
        HiDream-I1 SOTA experiment harness — STUB (R17 design-only release)
        ============================================================================

        The HiDream-I1 harness is **not implemented** in this skeleton release.
        Reasons (see module docstring for the full list):

          1. HiDream-I1 is a 17B-parameter sparse-DiT model that requires
             ~64GB HBM at fp16 inference (DiT weights + 4 text encoders).
             The sandbox is CPU-only and cannot host this workload.
          2. The published HiDream-ai/HiDream-I1-{{Full,Dev,Fast}} HF repos
             are unreachable from the sandbox (no HF token).
          3. The CIFAR FID harness (InceptionV3) cannot be reused because
             HiDream-I1's published metrics deliberately exclude FID.
          4. DPG-Bench / GenEval / HPSv2.1 each require their own eval
             model (MiniCPM-V 2.6, detection+text-match, HPSv2.1 CLIP-H).

        The adapter side is fully wired. See:

          * adaptive_reflow/adapters/hidream_i1.py          — adapter
          * tests/test_adapters/test_hidream_i1.py           — 22 passing tests
          * adaptive_reflow/adapters/hidream_i1.py docstring — design spec

        Requested (but not run):

          * variant       = {getattr(args, 'variant', 'full')}
          * eval-set      = {getattr(args, 'eval_set', 'dpg-bench')}
          * n-samples     = {getattr(args, 'n_samples', 16)}
          * n-rounds      = {getattr(args, 'n_rounds', 20)}
          * device        = {getattr(args, 'device', 'cpu')}
          * dtype         = {getattr(args, 'dtype', 'bf16')}
          * output-dir    = {getattr(args, 'output_dir', Path('./hidream_i1_out'))}
          * schedulers    = {getattr(args, 'schedulers', 'cosine,codim,evidence,freetraj')}
          * prompts-csv   = {getattr(args, 'prompts_csv', None)}
          * weights-path  = {getattr(args, 'weights_path', None)}

        To implement this harness:

          1. Acquire HiDream-I1 weights via `huggingface-cli download
             HiDream-ai/HiDream-I1-Full` (Full / Dev / Fast variants).
          2. Install the FLUX.1 VAE weights (black-forest-labs/FLUX.1-dev VAE).
          3. Implement the four text encoders (CLIP-L/14, CLIP-G/14, T5-XXL,
             Llama-3.1-8B-Instruct) — `transformers.AutoModel.from_pretrained`
             for each.
          4. Wire `adaptive_reflow.adapters.hidream_i1.HiDreamI1Adapter`
             in `torch` mode (replace the `_load_torch_pipeline` stub with
             the real pipeline).
          5. Implement the per-eval-set dispatch (DPG-Bench via
             MiniCPM-V 2.6, GenEval via the official detection+text-match
             pipeline, HPSv2 via HPSv2.1 CLIP-H, FID via InceptionV3
             against MS-COCO-30K).
          6. Update the stub to dispatch to the real implementation.

        Exiting with non-zero status (75 = EX_TEMPFAIL) so CI can detect
        the stub and surface the gap.

        ============================================================================
        """
    )
    print(msg, file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    _print_stub_message(args)
    # EX_TEMPFAIL: temporary failure that the user can resolve by
    # supplying the missing inputs (HiDream-I1 weights + a CUDA host +
    # eval-stack). 75 = sysexits.h EX_TEMPFAIL.
    return 75


if __name__ == "__main__":
    raise SystemExit(main())
