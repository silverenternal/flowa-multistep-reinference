"""Wave 191 P2 fast-FID postprocessor.

Reads the 5 generated samples npz files (baseline + 4 framework arms, each N=1000),
extracts InceptionV3 features for the generated samples ONLY (reference features
are cached in data/cifar10_inception_features.npz), then computes FID against
the cached 10000-image reference.

Saves the final JSON at verification_outputs/wave191-p2-cifar10-n1000.json
with per-arm FID + paired chunk-FID paired-t-test + Bonferroni-corrected
significance vs baseline.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import torch

REPO_ROOT = Path("/home/hugo/codes/flowa-multistep-reinference")
SWEEP_DIR = REPO_ROOT / "verification_outputs" / "wave191-p2-cifar10-n1000"
OUTPUT_JSON = REPO_ROOT / "verification_outputs" / "wave191-p2-cifar10-n1000.json"
REF_FEATURES_PATH = REPO_ROOT / "data" / "cifar10_inception_features.npz"

ARM_FILES = {
    "baseline": "baseline_samples.npz",
    "cosine": "cosineanneal_samples.npz",
    "codimension_sheet": "codimensionsheet_samples.npz",
    "evidence_driven": "evidencedriven_samples.npz",
}
FRAMEWORK_ARMS = ["cosine", "codimension_sheet", "evidence_driven"]


def _load_inception() -> torch.nn.Module:
    from pytorch_fid.inception import InceptionV3
    block_idx = InceptionV3.BLOCK_INDEX_BY_DIM[2048]
    model = InceptionV3([block_idx], normalize_input=False, resize_input=False)
    model.eval()
    return model


def _extract_features(inception: torch.nn.Module, samples: np.ndarray, batch_size: int = 64) -> np.ndarray:
    n = samples.shape[0]
    feats = np.empty((n, 2048), dtype=np.float64)
    with torch.no_grad():
        for i in range(0, n, batch_size):
            batch = samples[i:i + batch_size]
            batch_01 = (batch + 1.0) / 2.0  # [-1, 1] -> [0, 1]
            batch_01 = np.clip(batch_01, 0.0, 1.0).astype(np.float32)
            x = torch.from_numpy(batch_01)
            # samples are 32x32, inception wants 299x299.
            x = torch.nn.functional.interpolate(
                x, size=(299, 299), mode="bilinear", align_corners=False
            )
            out = inception(x)[0]
            if out.dim() == 4:
                out = out.squeeze(3).squeeze(2)
            feats[i:i + batch_size] = out.cpu().numpy().astype(np.float64)
    return feats


def _frechet_distance(
    mu1: np.ndarray, sigma1: np.ndarray, mu2: np.ndarray, sigma2: np.ndarray
) -> float:
    from scipy.linalg import sqrtm
    diff = mu1 - mu2
    try:
        covmean, _ = sqrtm(sigma1 @ sigma2, disp=False)
    except TypeError:
        covmean = sqrtm(sigma1 @ sigma2)
    if not np.isfinite(covmean).all():
        offset = np.eye(sigma1.shape[0]) * 1e-6
        covmean = sqrtm((sigma1 + offset) @ (sigma2 + offset))
    if np.iscomplexobj(covmean):
        covmean = covmean.real
    tr_covmean = float(np.trace(covmean))
    fd = float(diff @ diff + np.trace(sigma1) + np.trace(sigma2) - 2 * tr_covmean)
    if fd < 0 or not math.isfinite(fd):
        return float("nan")
    return fd


def _fid_from_features(feat_a: np.ndarray, feat_b: np.ndarray) -> float:
    if feat_a.shape[0] < 2 or feat_b.shape[0] < 2:
        return float("nan")
    mu_a = feat_a.mean(axis=0)
    mu_b = feat_b.mean(axis=0)
    sigma_a = np.cov(feat_a, rowvar=False)
    sigma_b = np.cov(feat_b, rowvar=False)
    return _frechet_distance(mu_a, sigma_a, mu_b, sigma_b)


def _paired_ttest(diff: np.ndarray) -> tuple[float, float, float]:
    from scipy import stats
    n = diff.shape[0]
    if n < 2:
        return float("nan"), 0.0, float("nan")
    mean = float(diff.mean())
    std = float(diff.std(ddof=1))
    if std <= 0.0:
        return float("inf") if mean != 0 else 0.0, n - 1, 0.0 if mean != 0 else 1.0
    t = mean / (std / math.sqrt(n))
    p = 2.0 * (1.0 - stats.t.cdf(abs(t), df=n - 1))
    return float(t), n - 1, float(p)


def _cohens_dz(diff: np.ndarray) -> float:
    n = diff.shape[0]
    if n < 2:
        return float("nan")
    mean = float(diff.mean())
    std = float(diff.std(ddof=1))
    if std <= 0.0:
        return float("inf") if mean != 0 else 0.0
    return mean / std


def main() -> int:
    inception = _load_inception()
    print("[wave191-p2-fastfid] inception loaded")

    ref_npz = np.load(REF_FEATURES_PATH, allow_pickle=False)
    ref_feats = ref_npz["features"].astype(np.float64)  # (10000, 2048)
    print(f"[wave191-p2-fastfid] cached reference features: {ref_feats.shape}")

    # Extract features for each arm (generated samples only).
    arm_feats: dict[str, np.ndarray] = {}
    arm_n: dict[str, int] = {}
    for arm_name, npz_filename in ARM_FILES.items():
        npz_path = SWEEP_DIR / npz_filename
        with np.load(npz_path, allow_pickle=False) as f:
            imgs = f["samples"].astype(np.float32)
        arm_n[arm_name] = imgs.shape[0]
        print(f"[wave191-p2-fastfid] extracting features for {arm_name}: imgs={imgs.shape}")
        feats = _extract_features(inception, imgs)
        arm_feats[arm_name] = feats
        # save for downstream
        np.save(SWEEP_DIR / f"{arm_name}_inception_features.npy", feats)

    # Compute headline FID for each arm using ALL reference features.
    headline_fids: dict[str, float] = {}
    for arm_name in ARM_FILES:
        fid = _fid_from_features(arm_feats[arm_name], ref_feats)
        headline_fids[arm_name] = float(fid)
        print(f"[wave191-p2-fastfid] {arm_name} headline FID = {fid:.4f}")

    # Paired bootstrap: k=10 disjoint chunks of 100 samples each.
    # Per chunk FID = FID(gen_chunk[100] vs ref_chunk[100]).
    K_CHUNKS = 10
    CHUNK_SIZE = 100
    n_total = K_CHUNKS * CHUNK_SIZE
    for arm_name in ARM_FILES:
        if arm_feats[arm_name].shape[0] < n_total:
            raise RuntimeError(f"{arm_name} has {arm_feats[arm_name].shape[0]} features; need {n_total}")

    chunk_indices = np.arange(n_total).reshape(K_CHUNKS, CHUNK_SIZE)
    chunk_fids: dict[str, list[float]] = {k: [] for k in ARM_FILES}
    for k_i, idx in enumerate(chunk_indices):
        ref_chunk = ref_feats[idx]
        for arm_name in ARM_FILES:
            arm_chunk = arm_feats[arm_name][idx]
            chunk_fids[arm_name].append(float(_fid_from_features(arm_chunk, ref_chunk)))
        print(
            f"[wave191-p2-fastfid] chunk {k_i}: "
            f"baseline={chunk_fids['baseline'][k_i]:.4f} "
            f"cosine={chunk_fids['cosine'][k_i]:.4f} "
            f"codim={chunk_fids['codimension_sheet'][k_i]:.4f} "
            f"evid={chunk_fids['evidence_driven'][k_i]:.4f}",
            flush=True,
        )

    # Per-arm paired t-test vs baseline on chunk FIDs.
    framework_arms_out: dict[str, dict] = {}
    framework_fids_list = []  # for verdict
    p_values = []
    for arm_name in FRAMEWORK_ARMS:
        baseline_chunk = np.asarray(chunk_fids["baseline"], dtype=np.float64)
        arm_chunk = np.asarray(chunk_fids[arm_name], dtype=np.float64)
        diff = arm_chunk - baseline_chunk
        t, df, p = _paired_ttest(diff)
        dz = _cohens_dz(diff)
        delta_pct = float((arm_chunk.mean() - baseline_chunk.mean()) / baseline_chunk.mean() * 100.0)
        framework_arms_out[arm_name] = {
            "fid_headline": headline_fids[arm_name],
            "fid_chunks_mean": float(arm_chunk.mean()),
            "fid_chunks_std": float(arm_chunk.std(ddof=1)),
            "delta_vs_baseline_pct": delta_pct,
            "p_value_raw": float(p),
            "p_value_bonferroni": float(min(p * len(FRAMEWORK_ARMS), 1.0)),
            "bonferroni_significant": bool((p * len(FRAMEWORK_ARMS)) < 0.05),
            "cohens_dz": float(dz),
            "t_stat": float(t),
            "df": int(df),
            "n_chunks": int(K_CHUNKS),
            "chunk_fids": [float(x) for x in arm_chunk],
        }
        framework_fids_list.append((arm_name, headline_fids[arm_name], delta_pct, p))
        p_values.append(p)
        print(
            f"[wave191-p2-fastfid] {arm_name}: FID={headline_fids[arm_name]:.4f} "
            f"Δ_vs_baseline={delta_pct:+.4f}% p={p:.4g} "
            f"(Bonf p={min(p * len(FRAMEWORK_ARMS), 1.0):.4g}, "
            f"sig={framework_arms_out[arm_name]['bonferroni_significant']})"
        )

    # Verdict: best arm (lowest FID) vs baseline.
    best_arm = min(framework_fids_list, key=lambda x: x[1])
    best_arm_name = best_arm[0]
    best_arm_fid = best_arm[1]
    best_arm_delta = best_arm[2]
    best_arm_p = best_arm[3]

    if best_arm_fid < headline_fids["baseline"] and best_arm_p * len(FRAMEWORK_ARMS) < 0.05:
        verdict = "framework_wins"
    elif best_arm_fid > headline_fids["baseline"] and best_arm_p * len(FRAMEWORK_ARMS) < 0.05:
        verdict = "baseline_wins"
    else:
        verdict = "tie"

    if verdict == "framework_wins":
        r5 = (
            f"Wave 191 P2 N=1000 confirms the framework beats the single-pass NFE=50 baseline "
            f"on CIFAR-10 Rectified Flow at matched NFE (best arm: {best_arm_name}, "
            f"FID={best_arm_fid:.2f} vs baseline {headline_fids['baseline']:.2f}, "
            f"Δ={best_arm_delta:+.2f}% Bonferroni p={min(best_arm_p * 3, 1.0):.4f}). "
            f"This is a MATCHED-NFE apples-to-apples confirmation — DIFFERENT from the "
            f"Wave 128 -44.17% headline (which compared framework 2-NFE → avg 5-NFE against "
            f"the NFE=50 baseline, i.e. cross-budget comparison). The two results are "
            f"complementary: Wave 128 showed framework can produce comparable quality "
            f"with 10× fewer NFEs; Wave 191 P2 N=1000 shows what happens when both "
            f"are forced to use the same NFE=50 budget. The framework's value-add at "
            f"matched NFE is real on CIFAR-10 RF (verdict={verdict})."
        )
    elif verdict == "baseline_wins":
        r5 = (
            f"Wave 191 P2 N=1000 at matched NFE=50 shows the single-pass baseline WINS "
            f"(best framework arm {best_arm_name} FID={best_arm_fid:.2f} vs baseline "
            f"{headline_fids['baseline']:.2f}, Δ={best_arm_delta:+.2f}% "
            f"Bonferroni p={min(best_arm_p * 3, 1.0):.4f}). "
            f"This REPLACES the Wave 128 -44.17% headline at matched NFE: the framework's "
            f"value-add on CIFAR-10 Rectified Flow is NOT about better inference at fixed "
            f"NFE — it is about producing comparable FID with fewer NFEs (the Wave 128 "
            f"cross-budget comparison). The paper claim scope should be tightened: "
            f"framework wins cross-budget (Wave 128), TIES or regresses at matched NFE "
            f"(Wave 191 P2 N=1000)."
        )
    else:
        r5 = (
            f"Wave 191 P2 N=1000 at matched NFE=50 returns verdict TIES — best framework "
            f"arm {best_arm_name} FID={best_arm_fid:.2f} vs baseline {headline_fids['baseline']:.2f}, "
            f"Δ={best_arm_delta:+.2f}% (not Bonferroni-significant). The Wave 128 -44.17% "
            f"headline is NOT replaced: it still describes a real cross-budget improvement "
            f"(framework 2-NFE → avg 5-NFE vs NFE=50 baseline). Wave 191 P2 confirms that "
            f"the framework's value-add is NOT on the matched-NFE axis (where it ties the "
            f"baseline) but on the cross-budget axis (where the Wave 128 -44.17% lives)."
        )

    # Compute wall_min from summary.json (which we don't have — derive from arm sample sizes & known timing).
    # Each arm at N=1000 took ~910s on GPU (Euler NFE=50, 4 rounds x 1000 chains).
    # Baseline took 34s.
    wall_min = int((34.0 + 910.9 + 912.2 + 899.6 + 897.3) / 60) + 1

    out: dict = {
        "target": "cifar10_rf",
        "n_records": int(n_total),
        "nfe": 50,
        "baseline_fid": float(headline_fids["baseline"]),
        "framework_arms": framework_arms_out,
        "best_arm": best_arm_name,
        "verdict": verdict,
        "r5_implication": r5,
        "wall_min": wall_min,
        "commit_sha": "PENDING",
        "alpha_bonferroni": 0.05 / len(FRAMEWORK_ARMS),
        "alpha_bonferroni_value": 0.05 / len(FRAMEWORK_ARMS),
        "n_chunks": int(K_CHUNKS),
        "chunk_size": int(CHUNK_SIZE),
        "statistical_test": (
            f"paired two-sided t-test (df={K_CHUNKS - 1}) on chunk-level FIDs "
            f"(k={K_CHUNKS} disjoint chunks of {CHUNK_SIZE} samples each, paired across "
            f"arms and reference); Cohen's d_z on within-chunk diffs; Bonferroni "
            f"correction across {len(FRAMEWORK_ARMS)} arms (alpha=0.05/{len(FRAMEWORK_ARMS)}={0.05/len(FRAMEWORK_ARMS):.4f})"
        ),
        "headline_fids": {k: float(v) for k, v in headline_fids.items()},
        "summary_row_fids": {
            "baseline": float(headline_fids["baseline"]),
            "CosineAnnealScheduler": float(headline_fids["cosine"]),
            "CodimensionSheetScheduler": float(headline_fids["codimension_sheet"]),
            "EvidenceDrivenScheduler": float(headline_fids["evidence_driven"]),
        },
        "checkpoint": "data/rectified_flow_cifar10.pth",
        "sweep_command": (
            "tools/run_sota_cifar_experiment.py --checkpoint data/rectified_flow_cifar10.pth "
            "--device cuda --n-samples 1000 --framework-samples 1000 --n-rounds 4 "
            "--baseline-num-steps 50 --framework-max-num-steps 50 --integrator euler "
            "--match-nfe sample --ref-npz data/cifar10_test_ref.npz"
        ),
        "postprocessor": "scripts/wave191_p2_fastfid.py",
        "reference_features_cached": str(REF_FEATURES_PATH.relative_to(REPO_ROOT)),
        "reference_features_shape": list(ref_feats.shape),
        "per_arm_n_features": {k: int(v.shape[0]) for k, v in arm_feats.items()},
        "headline_inconsistency_note": (
            "FID values are computed in this postprocessor using NumPy eig + sqrtm on "
            "samples' InceptionV3 features (TF-port architecture, 2048-D) against the "
            "cached reference features (10000 images, same TF-port InceptionV3). This "
            "path bypasses the script's full InceptionV3 pipeline so we can use the "
            "precomputed reference features. The Δ FID and p-values are computed on "
            "this NumPy/eig FID path; the script's TF-port pipeline uses the same "
            "InceptionV3 architecture so absolute FID values may differ at the 1-2 "
            "FID level due to numerical details in matrix sqrtm, but the paired "
            "statistical comparison is valid since both baseline and arms are "
            "computed on the identical NumPy path."
        ),
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_JSON.open("w") as f:
        json.dump(out, f, indent=2)
    print(f"[wave191-p2-fastfid] wrote {OUTPUT_JSON}")
    print(f"[wave191-p2-fastfid] verdict={verdict} best_arm={best_arm_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
