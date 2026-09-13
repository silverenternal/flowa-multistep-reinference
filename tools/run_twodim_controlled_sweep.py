"""Resumable serial TwoDimFM controls with immutable execution provenance.

Each completed cell is durable. Failed cells are retried by --resume; an
existing directory is never silently reused for a different experiment.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import platform
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

import numpy as np
import scipy

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.run_controlled_audit import CellSpec, _run_twodim_fm  # noqa: E402 -- checkout bootstrap


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic(path: Path, payload: dict) -> None:
    fd, name = tempfile.mkstemp(prefix=path.name, suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(payload, stream, indent=2, allow_nan=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def _finite_json(value):
    if isinstance(value, dict):
        return {k: _finite_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_finite_json(v) for v in value]
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def _provenance(specs: list[CellSpec], allocation: str) -> dict:
    sources = sorted((_REPO / 'adaptive_reflow').rglob('*.py'))
    sources += [_REPO / 'tools/run_controlled_audit.py', Path(__file__).resolve()]
    source_hash = hashlib.sha256()
    for source in sources:
        source_hash.update(str(source.relative_to(_REPO)).encode())
        source_hash.update(bytes.fromhex(_sha(source)))
    weights = {str(Path(s.twodim_weights).resolve()): _sha(Path(s.twodim_weights)) for s in specs}
    return dict(schema=1, cells=[asdict(s) for s in specs], allocation=allocation,
                source_sha256=source_hash.hexdigest(), weights=weights,
                python=sys.version, executable=sys.executable, numpy=np.__version__,
                scipy=scipy.__version__, machine=platform.machine(),
                threads={key: os.environ.get(key) for key in
                         ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')})


def run(specs: list[CellSpec], output: Path, *, resume: bool, allocation: str) -> int:
    from tools import run_controlled_audit as audit
    audit.NFE_ALLOCATION = allocation
    expected = _provenance(specs, allocation)
    output.mkdir(parents=True, exist_ok=True)
    with (output / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        manifest_path = output / 'manifest.json'
        if resume:
            if not manifest_path.exists() or json.loads(manifest_path.read_text()) != expected:
                raise ValueError('resume requires identical manifest, sources, weights and environment')
        else:
            if manifest_path.exists() or any(output.glob('cell-*.json')):
                raise FileExistsError('existing run: use --resume with the same configuration')
            _atomic(manifest_path, expected)
        summaries = []
        failed = 0
        resumed = 0
        for i, spec in enumerate(specs):
            path = output / f'cell-{i:04d}.json'
            payload = None
            if path.exists():
                saved = json.loads(path.read_text())
                if saved.get('spec') != asdict(spec):
                    raise ValueError('cell specification differs from manifest')
                if saved.get('success') is True:
                    result = saved['result']
                    if (result.get('error') or not result.get('nfe_matched')
                            or any(not isinstance(result.get(k), (int, float))
                                   or not np.isfinite(result[k])
                                   for k in ('baseline_metric', 'framework_metric'))):
                        raise ValueError('invalid successful checkpoint')
                    payload = saved
                    resumed += 1
            if payload is None:
                result = _run_twodim_fm(spec)
                success = (not result.error and result.nfe_matched
                           and np.isfinite(result.baseline_metric)
                           and np.isfinite(result.framework_metric))
                payload = dict(spec=asdict(spec), success=bool(success),
                               result=_finite_json(result.to_dict()))
                _atomic(path, payload)
            failed += not payload['success']
            r = payload['result']
            summaries.append(dict(cell=i, success=payload['success'], seed=spec.seed,
                                  nfe=spec.nfe, sigma=spec.sigma, guard=spec.restart_guard,
                                  baseline=r['baseline_metric'], framework=r['framework_metric'],
                                  delta=r['delta'], error=r['error']))
            print(f'cell {i + 1}/{len(specs)} success={payload["success"]}', flush=True)
        _atomic(output / 'summary.json', dict(cells=summaries, failed_cells=failed,
                                             resumed_cells=resumed, complete=not failed))
        return int(bool(failed))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--weights', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--n-samples', type=int, default=20)
    parser.add_argument('--seeds', type=int, nargs='+', default=[42])
    parser.add_argument('--nfe', type=int, nargs='+', default=[50])
    parser.add_argument('--sigma', type=float, nargs='+', default=[0., .5])
    parser.add_argument('--guards', choices=['on', 'off'], nargs='+', default=['on', 'off'])
    parser.add_argument('--nfe-allocation', choices=['uniform', 'evidence'], default='evidence')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args(argv)
    if args.n_samples < 2 or any(n < 10 or n % 2 for n in args.nfe):
        parser.error('N >= 2 and even NFE >= 10 required')
    if any(not np.isfinite(s) or s < 0 for s in args.sigma):
        parser.error('sigma must be finite and nonnegative')
    specs = [CellSpec('twodim_fm', seed, nfe, sigma, args.n_samples,
                      guard == 'on', str(args.weights.resolve()))
             for seed in args.seeds for nfe in args.nfe for sigma in args.sigma
             for guard in args.guards]
    return run(specs, args.output_dir, resume=args.resume, allocation=args.nfe_allocation)


if __name__ == '__main__':
    raise SystemExit(main())
