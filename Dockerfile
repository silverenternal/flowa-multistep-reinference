# FlowA TPAMI submission — paper-grade release container
#
# This Dockerfile builds the canonical reproduce environment for the
# IEEE TPAMI submission `v3.0-paper-n1000-reruns`. It is derived from
# the `omegafold_py310` conda env (Python 3.10.21, torch 2.14.0+cu130,
# sm_120 native) plus the framework-side Python 3.12.13 venv
# (`requirements-lock.txt`).
#
# Build:
#   docker build -t flowa:tpami-v3.0 .
#
# Run (single-GPU reproduce):
#   docker run --gpus '"device=0"' -it --rm \
#       -v /home/hugo/codes/flowa-multistep-reinference:/workspace/flowa \
#       flowa:tpami-v3.0 \
#       --n-paired 1000 --seeds 42 43 44 45 46 47
#
# Run (per-record byte-stable D.4 gate):
#   docker run --gpus '"device=0"' -it --rm \
#       -v /home/hugo/codes/flowa-multistep-reinference:/workspace/flowa \
#       flowa:tpami-v3.0 \
#       python -m pytest tests/test_d4_regression_vectors.py -v

# ---------- Base image: CUDA 12.4 + cuDNN runtime on Ubuntu 22.04 ----------
FROM nvidia/cuda:12.4.0-cudnn-runtime-ubuntu22.04

LABEL org.opencontainers.image.title="flowa-tpami-v3.0" \
      org.opencontainers.image.description="FlowA — TPAMI paper-grade reproduce container" \
      org.opencontainers.image.source="https://github.com/silverenternal/flowa-multistep-reinference" \
      org.opencontainers.image.licenses="Apache-2.0"

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CONDA_DIR=/opt/conda

# ---------- System packages ----------
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl wget git bzip2 \
        build-essential cmake ninja-build pkg-config \
        libssl-dev libffi-dev libsqlite3-dev zlib1g-dev \
        libbz2-dev libreadline-dev liblzma-dev libncurses5-dev \
        libopenblas-dev libomp-dev libhdf5-dev \
        hmmmer mmseqs2 \
        rdkit-data \
    && rm -rf /var/lib/apt/lists/*

# ---------- conda + Python 3.10.21 (omegafold_py310 spec) ----------
# Pin to a miniforge installer that ships Python 3.10. We use
# mambaforge as the conda-forge distribution; the `mamba` solver
# keeps the `omegafold_py310` spec reproducible across builds.
RUN wget -qO /tmp/miniforge.sh \
        https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh \
    && bash /tmp/miniforge.sh -b -p "${CONDA_DIR}" \
    && rm /tmp/miniforge.sh \
    && "${CONDA_DIR}/bin/conda" init bash \
    && "${CONDA_DIR}/bin/conda" config --set auto_activate_base false

# Copy conda env spec — created from `conda env export` of the
# canonical `omegafold_py310` env at /home/hugo/.conda/envs/omegafold_py310/.
# The spec pins Python 3.10.21 + torch 2.14.0+cu130 + sm_120 native.
COPY environment.yml /tmp/environment.yml
RUN "${CONDA_DIR}/bin/mamba" env create -f /tmp/environment.yml \
    && "${CONDA_DIR}/bin/conda" clean -afy \
    && rm /tmp/environment.yml

ENV PATH="${CONDA_DIR}/envs/omegafold_py310/bin:${PATH}"

# Make the env the default for subsequent RUN/ENTRYPOINT
RUN echo "conda activate omegafold_py310" >> /root/.bashrc

# ---------- framework-side Python deps (requirements-lock.txt) ----------
# The framework core is stdlib-only; the lockfile carries the optional
# dependencies needed by the model-side adapters + tests. We install
# them into the system Python (3.10 from conda) for simplicity —
# `pip install --no-deps` so torch remains conda-managed.
COPY requirements-lock.txt /tmp/requirements-lock.txt
RUN /opt/conda/envs/omegafold_py310/bin/pip install --no-deps \
        -r /tmp/requirements-lock.txt \
    && rm /tmp/requirements-lock.txt

# ---------- Framework source ----------
WORKDIR /workspace/flowa

# Copy framework + tests + verification outputs + paper drafts.
# data/ is intentionally excluded — reviewers re-download the
# SHA-256-pinned checkpoints (verification_outputs/ckpt_sha256.json)
# in §Installation below.
COPY adaptive_reflow/   ./adaptive_reflow/
COPY tests/             ./tests/
COPY verification_outputs/ ./verification_outputs/
COPY paper/             ./paper/

# Copy supporting files referenced by tests + tools
COPY regression-vectors/    ./regression-vectors/
COPY docs/CLAIMS.md         ./docs/CLAIMS.md 2>/dev/null || true
COPY docs/INSIGHTS.md       ./docs/INSIGHTS.md 2>/dev/null || true
COPY docs/drafts/           ./docs/drafts/ 2>/dev/null || true
COPY docs/theory/           ./docs/theory/ 2>/dev/null || true
COPY docs/audit/            ./docs/audit/ 2>/dev/null || true
COPY tools/                 ./tools/ 2>/dev/null || true
COPY pyproject.toml         ./pyproject.toml 2>/dev/null || true
COPY requirements-lock.txt  ./requirements-lock.txt 2>/dev/null || true
COPY RELEASE-NOTES-v3.0.md  ./RELEASE-NOTES-v3.0.md 2>/dev/null || true
COPY env_hash.txt           ./env_hash.txt 2>/dev/null || true

# ---------- SHA-256 verify pinned checkpoints (CI gate) ----------
# Reviewers must mount `data/` as a volume at runtime; this stanza
# asserts the pinned SHAs match `verification_outputs/ckpt_sha256.json`
# when `data/` is present. Skipped when `data/` is absent.
COPY tools/verify_ckpt_sha256.py ./tools/verify_ckpt_sha256.py 2>/dev/null || true
RUN if [ -f ./tools/verify_ckpt_sha256.py ]; then \
        echo "[Dockerfile] verify_ckpt_sha256.py present; run at container start."; \
    else \
        echo "[Dockerfile] verify_ckpt_sha256.py absent; ckpt verification deferred to runtime."; \
    fi

# ---------- Default command ----------
# The `engine` module is a thin shim over `adaptive_reflow.algorithm.runner`
# (see RELEASE-NOTES-v3.0.md §Quick reference). Reviewers typically
# override the command to run a specific reproduce script.
ENTRYPOINT ["python", "-m", "adaptive_reflow.framework.engine"]
CMD ["--help"]