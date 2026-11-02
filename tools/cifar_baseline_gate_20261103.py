#!/usr/bin/env python3
"""Bounded CIFAR baseline correctness gate before any method comparison."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import types
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official-source", type=Path, required=True)
    parser.add_argument("--official-commit", required=True)
    parser.add_argument("--device", default="cuda:1")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    metadata = {
        "registered_utc": datetime.now(UTC).isoformat(),
        "command": sys.argv,
        "N": 1000,
        "seed": 42,
        "steps": 50,
        "solver": "official Euler convention eps=.001, dt=1/S; no state clipping; only output clamp for features",
        "device": args.device,
        "budget_wall_s": 1800,
        "gate": "original Python model forward matches port within max_abs 1e-4 at 3 time labels; baseline TF-port FID<10 at N1000 vs fresh10k test reference before any framework comparisons",
        "official_repository": "https://github.com/gnobitab/RectifiedFlow",
        "official_commit": args.official_commit,
        "official_code_sha256": {
            p: digest(args.official_source / p)
            for p in ["models/ncsnpp.py", "models/layerspp.py", "models/layers.py", "sampling.py"]
        },
        "weights": str(ROOT / "data/cifar10_rf.pth"),
        "weights_sha256": digest(ROOT / "data/cifar10_rf.pth"),
        "reference_sha256": digest(ROOT / "data/cifar10_test_ref.npz"),
        "legacy_reference_features_sha256": digest(ROOT / "data/cifar10_inception_features.npz"),
        "runner_sha256": digest(__file__),
        "base_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "gpu_snapshot": subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=index,name,memory.free,utilization.gpu",
                "--format=csv,noheader",
            ],
            text=True,
        ),
    }
    (args.out / "METADATA.json").write_text(json.dumps(metadata, indent=2) + "\n")
    start = time.monotonic()
    import torch

    from adaptive_reflow.adapters._gnobitab_ddpmpp import (
        load_gnobitab_rf_cifar_unet,
        strip_module_prefix,
    )
    from adaptive_reflow.adapters.rectified_flow_cifar import _extract_checkpoint_state_dict

    device = torch.device(args.device)
    state = _extract_checkpoint_state_dict(
        torch.load(ROOT / "data/cifar10_rf.pth", map_location="cpu", weights_only=False)
    )
    port = load_gnobitab_rf_cifar_unet(state).to(device).eval()
    # The official fir=False path never uses this compiled extension. Fail if it is invoked.
    op = types.ModuleType("op")

    def unused_fir(*_args, **_kwargs):
        raise RuntimeError("unexpected use of disabled FIR extension")

    op.upfirdn2d = unused_fir
    sys.modules["op"] = op
    sys.path.insert(0, str(args.official_source))
    from models.ncsnpp import NCSNpp

    S = types.SimpleNamespace
    config = S(
        data=S(centered=True, image_size=32, num_channels=3),
        training=S(continuous=False, sde="rectified_flow"),
        model=S(
            nonlinearity="swish",
            nf=128,
            ch_mult=(1, 2, 2, 2),
            num_res_blocks=4,
            attn_resolutions=(16,),
            dropout=0.15,
            resamp_with_conv=True,
            conditional=True,
            fir=False,
            fir_kernel=[1, 3, 3, 1],
            skip_rescale=True,
            resblock_type="biggan",
            progressive="none",
            progressive_input="none",
            embedding_type="positional",
            init_scale=0.0,
            progressive_combine="sum",
            scale_by_sigma=False,
            sigma_max=50.0,
            sigma_min=0.01,
            num_scales=1000,
        ),
    )
    official = NCSNpp(config).float().to(device).eval()
    official.load_state_dict(strip_module_prefix(state), strict=True)
    gen = torch.Generator(device=device).manual_seed(20261103)
    x = torch.randn((2, 3, 32, 32), generator=gen, device=device)
    errors = []
    with torch.inference_mode():
        for t in [0.0, 0.5, 1.0]:
            labels = torch.full((2,), t * 999, device=device)
            a = official(x, labels)
            b = port(x, torch.full((2,), t, device=device))
            errors.append(float((a - b).abs().max()))
    parity = {
        "max_abs": errors,
        "pass": max(errors) <= 1e-4,
        "fir_extension": "unavailable stub; never called; reference fir=False",
        "model_state_keys": len(state),
    }
    (args.out / "FORWARD_PARITY.json").write_text(json.dumps(parity, indent=2) + "\n")
    print("PARITY", parity, flush=True)
    if not parity["pass"]:
        raise RuntimeError("original-model forward parity failed; no generation comparison")
    del official
    torch.cuda.empty_cache()
    outputs = []
    tic = time.monotonic()
    rng = torch.Generator(device=device).manual_seed(42)
    with torch.inference_mode():
        for offset in range(0, 1000, 32):
            count = min(32, 1000 - offset)
            z = torch.randn((count, 3, 32, 32), generator=rng, device=device)
            for step in range(50):
                t = 0.001 + step / 50 * (1 - 0.001)
                z = z + port(z, torch.full((count,), t, device=device)) / 50
            outputs.append(z.cpu().numpy())
            if offset % 256 == 0:
                print("GENERATED", offset + count, flush=True)
    torch.cuda.synchronize()
    generation_s = time.monotonic() - tic
    samples = np.concatenate(outputs)
    np.savez_compressed(args.out / "baseline_samples.npz", samples=samples)
    del port
    torch.cuda.empty_cache()
    from pytorch_fid.inception import InceptionV3

    feature_model = InceptionV3([InceptionV3.BLOCK_INDEX_BY_DIM[2048]]).to(device).eval()

    def features(images):
        out = []
        with torch.inference_mode():
            for offset in range(0, len(images), 64):
                imgs = torch.as_tensor(
                    images[offset : offset + 64], dtype=torch.float32, device=device
                )
                acts = feature_model(((imgs + 1) / 2).clamp(0, 1))[0]
                out.append(acts.flatten(1).cpu().numpy())
        return np.concatenate(out)

    ref = np.load(ROOT / "data/cifar10_test_ref.npz")["samples"]
    ref_features = features(ref)
    generated = features(samples)
    np.savez_compressed(
        args.out / "tfport_features.npz", reference=ref_features, baseline=generated
    )
    from adaptive_reflow.eval.fid import compute_frechet_distance

    fid = float(
        compute_frechet_distance(
            mu_s=generated.astype(np.float64).mean(0),
            sigma_s=np.cov(generated.astype(np.float64), rowvar=False),
            mu_r=ref_features.astype(np.float64).mean(0),
            sigma_r=np.cov(ref_features.astype(np.float64), rowvar=False),
        )
    )
    legacy = np.load(ROOT / "data/cifar10_inception_features.npz")
    legacy_meta = json.loads(str(legacy["metadata"]))
    result = {
        "n": 1000,
        "n_reference": len(ref),
        "n_skipped": 0,
        "baseline_fid_tfport": fid,
        "baseline_gate_pass": fid < 10,
        "generation_wall_s": generation_s,
        "total_wall_s": time.monotonic() - start,
        "forward_parity": parity,
        "feature_family": "pytorch_fid TF-port InceptionV3 2048 pool3; reference recomputed from same10k test images",
        "legacy_cache_family": legacy_meta.get("extractor"),
        "legacy_cache_compatible": False,
        "scope": "Diagnostic, single seed; not a frontier or method win, not a reproduction of published50k FID.",
    }
    (args.out / "RESULT.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
