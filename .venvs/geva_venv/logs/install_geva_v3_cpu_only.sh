#!/usr/bin/env bash
# install_geva_v3_cpu_only.sh
# CPU-only mmcv-full 1.7.2 + mmdet 2.28.2 + GenEval stack in `.venvs/geva_venv`.
# Sibling to install_geva_v2.sh; that one aimed for a CUDA build (blocked by
# CUDA 13.2 / torch 2.7+cu128 mismatch). This v3 build is CPU-only and is
# what the operator can run TODAY.
#
# Usage:
#   bash .venvs/geva_venv/logs/install_geva_v3_cpu_only.sh
#
# After this completes, the wrapper (`tools/run_image_eval.py`) can be
# invoked with `--geneval-binary .venvs/geva_venv/bin/python`; the
# upstream GenEval `evaluate_images.py` will load with the CPU-only
# mmcv-full + mmdet 2.28.2 stack. Inference is correct but slow
# (no CUDA kernels are linked), so this build is for testing the
# pipeline contract only. For paper-fidelity numbers, run on a CUDA
# 12.x host (CUDA_HOME set to a 12.x toolkit).

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VENV="${PROJECT_ROOT}/.venvs/geva_venv"
PY="${VENV}/bin/python"
PIP="${VENV}/bin/pip"

# 1. setuptools 84 removed `pkg_resources`; mmcv-full 1.7.2 setup.py
#    imports `from pkg_resources import ...`. Pin an older setuptools
#    for the duration of the build (does not affect runtime imports).
${PIP} install --quiet 'setuptools<70' wheel

# 2. Source-build mmcv-full 1.7.2 with the CPU-only ops path.
#    - MMCV_WITH_OPS=1 ensures `_ext.cpython-*.so` is built.
#    - FORCE_CUDA=0 prevents `setup.py` from selecting CUDAExtension on
#      this host (where `torch.cuda.is_available()` is True but the local
#      nvcc is CUDA 13.2 — incompatible with the torch 2.7+cu128 runtime).
#    - setup.py is patched (see mmcv_setup_patch.py) to override
#      `torch.cuda.is_available` to return False during the build, so the
#      "Compiling mmcv._ext only with CPU" branch is taken. Without the
#      patch, the function returns True and CUDAExtension is selected,
#      which then hits `_check_cuda_version` and dies.
WORK=/tmp/mmcv-full-1.7.2-build
rm -rf "${WORK}" && mkdir -p "${WORK}"
cd "${WORK}"
curl -fsSL -o mmcv-full-1.7.2.tar.gz \
    https://files.pythonhosted.org/packages/source/m/mmcv-full/mmcv-full-1.7.2.tar.gz
tar xzf mmcv-full-1.7.2.tar.gz
cp "${VENV}/logs/mmcv_setup_patch.py" mmcv-full-1.7.2/setup_patch.py
cd mmcv-full-1.7.2
# Apply the patch (in-place, idempotent)
${PY} setup_patch.py

# Build the wheel
MMCV_WITH_OPS=1 FORCE_CUDA=0 ${PY} setup.py bdist_wheel

# Install the wheel into the venv (no deps because the only deps needed
# are opencv-python-headless, yapf, addict, scipy, terminaltables, etc.
# which we install explicitly below).
cp dist/mmcv_full-1.7.2-*.whl "${VENV}/logs/"
${PIP} install --quiet --no-deps --no-build-isolation \
    "dist/mmcv_full-1.7.2-*.whl"

# 3. mmdet 2.28.2 (the version GenEval pins for Mask2Former config)
${PIP} install --quiet --no-deps --no-build-isolation mmdet==2.28.2

# 4. mmcv-full runtime deps
${PIP} install --quiet opencv-python-headless yapf addict scipy terminaltables matplotlib pycocotools

# 5. GenEval upstream deps (evaluate_images.py + summary_scores.py)
${PIP} install --quiet open_clip_torch clip-benchmark einops ftfy regex

# 6. Smoke test
${PY} -c "
import warnings; warnings.filterwarnings('ignore')
import torch, mmcv, mmdet
print('torch:', torch.__version__, 'torch.version.cuda:', torch.version.cuda)
print('mmcv:', mmcv.__version__, 'compiling_cuda_version:', mmcv.ops.get_compiling_cuda_version())
print('mmdet:', mmdet.__version__)
print('mmcv._ext symbols (first 6):', sorted([n for n in dir(mmcv._ext) if not n.startswith('_')])[:6])
import sys; sys.path.insert(0, '${VENV}/repo/evaluation')
import evaluate_images
print('evaluate_images importable -- CPU-only GenEval stack is LIVE')
"

echo
echo "OK -- GenEval stack installed (CPU-only)."
echo "Wheel archived at: ${VENV}/logs/mmcv_full-1.7.2-*-cpu_only.whl"
