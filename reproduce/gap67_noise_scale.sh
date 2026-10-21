#!/bin/bash
# =============================================================================
# gap67_noise_scale.sh — GAP-67 second-moment-preserving restart blend
#
# Question: is the R5c fidelity cost caused by the blend's second-moment
# deficit, and does restoring that moment remove it?
#
# The restart writes the path state at t = m as
#     y = m * x1_hat + (1 - m) * x0_fresh
# which is under-dispersed by m^2 (v_base - v_hat) relative to the model's own
# dispersion. Scaling the fresh noise by c restores it:
#     c^2 = 1 + m^2 (v_base - v_hat) / (1 - m)^2
#
# The c values below are ORACLE-CALIBRATED: v_hat is taken from the already
# measured gap57 arm (see docs/audit/gap67-covariance-preservation.md §2).
# This is a mechanism screen, not a deployable calibration.
#
# Baselines are reused verbatim from gap57-equal-nfe-ladder-n1000/<ckpt>_s42/
# (RK4 is deterministic and shared_prior makes round 0 byte-identical).
#
# Output: verification_outputs/gap67-noise-scale/<ckpt>_c<scale>.json
#
# USAGE:
#   bash reproduce/gap67_noise_scale.sh          # all 4 checkpoints
# =============================================================================

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

export OMP_NUM_THREADS=1
OUT_ROOT="verification_outputs/gap67-noise-scale"
BASE_ROOT="verification_outputs/gap57-equal-nfe-ladder-n1000"
mkdir -p "$OUT_ROOT"

# ckpt_tag : ckpt_path : c
CELLS=(
  "production:data/mnist_fm/production.ckpt.npz:1.0052"
  "w16e1_10k:data/mnist_fm/w16e1_10k.ckpt.npz:1.0324"
  "w16e1_60k:data/mnist_fm/w16e1.ckpt.npz:1.0127"
  "w16e1_5k:data/mnist_fm/w16e1_5k.ckpt.npz:1.0599"
)

for cell in "${CELLS[@]}"; do
  IFS=":" read -r tag ckpt scale <<< "$cell"
  echo "=== ${tag} c=${scale} ==="
  python3 tools/gap67_noise_scale_screen.py \
    --ckpt "$ckpt" \
    --baseline-npz "$BASE_ROOT/${tag}_s42/baseline_samples.npz" \
    --scale "$scale" \
    --label "$tag" \
    --out "$OUT_ROOT/${tag}_c${scale}.json" \
    || { echo "FAILED ${tag}"; exit 1; }
done

echo "all four cells done -> $OUT_ROOT"
