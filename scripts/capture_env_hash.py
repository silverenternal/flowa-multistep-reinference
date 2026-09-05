"""Capture env_hash per framework-internal-metrics rev 2 §1 F.5.

env_hash = SHA256( requirements-lock.txt + python --version + torch.__version__ +
                   torch.version.cuda + adapter-specific dependency versions )

Wave 36 PHASE-4 extension: the capture() function additionally reports
the *importable* versions of PHASE-4 SOTA-integration deps (rdkit,
biopython, transformers, diffusers, torchvision). These are the
packages the Wave 21 Kanzi / FreqFlow / LineageFlow adapters
additionally depend on; folding them into env_hash.txt ensures the F.5
cold-clone reproducibility gate (per framework-freeze-checklist MUST-1)
catches drift in the PHASE-4 dependency surface (e.g. a future
biopython>=2.0 bump that breaks Wave 10 LineageFlow encoding).

NOT full pip freeze (sensitive to install order, --extra-index-url, OS pkg mgr).

Usage:
    python scripts/capture_env_hash.py capture  # writes env_hash.txt
    python scripts/capture_env_hash.py verify   # compares to committed env_hash.txt
    python scripts/capture_env_hash.py show     # prints to stdout
"""
import hashlib, sys, subprocess, pathlib, platform
from typing import Optional

# PHASE-4 SOTA-integration dep probes. Each entry is a (import_name,
# label) pair. When importable, the version is captured; otherwise
# ``not-installed`` is recorded (the env_hash gate stays operational
# on CPU-only sandboxes that lack rdkit/biopython/etc.).
_PHASE4_DEPS: tuple[tuple[str, str], ...] = (
    ("rdkit", "rdkit"),
    ("Bio", "biopython"),
    ("transformers", "transformers"),
    ("diffusers", "diffusers"),
    ("torchvision", "torchvision"),
    ("torch_geometric", "torch_geometric"),
    ("dgl", "dgl"),
)

def capture() -> dict[str, str]:
    # 1. requirements-lock.txt content hash
    lock_path = pathlib.Path(__file__).resolve().parent.parent / "requirements-lock.txt"
    lock_hash = hashlib.sha256(lock_path.read_bytes()).hexdigest()

    # 2. python --version
    py_version = subprocess.check_output([sys.executable, "--version"]).decode().strip()

    # 3. torch.__version__ + torch.version.cuda (optional; skip if torch not installed)
    torch_info = "torch:not-installed"
    try:
        import torch
        torch_info = f"torch:{torch.__version__}+cuda{torch.version.cuda}"
    except ImportError:
        pass

    # 4. adapter-specific deps (rdkit, scipy, etc.) — read from docs/adapter-dependencies.md
    deps_path = pathlib.Path(__file__).resolve().parent.parent / "docs" / "adapter-dependencies.md"
    deps_hash = hashlib.sha256(deps_path.read_bytes()).hexdigest()

    out: dict[str, str] = {
        "lock_hash": lock_hash,
        "python_version": py_version,
        "torch_version": torch_info,
        "adapter_deps_hash": deps_hash,
    }

    # 5. PHASE-4 SOTA-integration dep versions (Wave 36 extension)
    for import_name, label in _PHASE4_DEPS:
        try:
            mod = __import__(import_name)
            ver = getattr(mod, "__version__", "unknown")
            out[f"{label}_version"] = f"{label}:{ver}"
        except Exception:
            out[f"{label}_version"] = f"{label}:not-installed"

    return out

def write_env_hash(path: pathlib.Path) -> None:
    info = capture()
    with path.open("w") as f:
        for k, v in info.items():
            f.write(f"{k}={v}\n")
    composite = hashlib.sha256("\n".join(f"{k}={v}" for k, v in info.items()).encode()).hexdigest()
    with path.open("a") as f:
        f.write(f"composite_hash={composite}\n")

def verify_env_hash(path: pathlib.Path) -> bool:
    info = capture()
    if not path.exists():
        print(f"FAIL: {path} does not exist")
        return False
    existing = dict(line.strip().split("=", 1) for line in path.read_text().splitlines() if "=" in line)
    ok = True
    for k, v in info.items():
        if existing.get(k) != v:
            print(f"FAIL: {k} drifted: was {existing.get(k)!r}, now {v!r}")
            ok = False
    return ok

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "capture"
    env_hash_path = pathlib.Path(__file__).resolve().parent.parent / "env_hash.txt"
    if cmd == "capture":
        write_env_hash(env_hash_path)
        print(f"wrote {env_hash_path}")
    elif cmd == "verify":
        sys.exit(0 if verify_env_hash(env_hash_path) else 1)
    elif cmd == "show":
        for k, v in capture().items():
            print(f"{k}={v}")
    else:
        print(f"unknown command: {cmd}"); sys.exit(2)