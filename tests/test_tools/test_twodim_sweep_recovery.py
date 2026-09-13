"""Cell failures preserve completed controlled experiments without silent reuse."""
import json

import pytest

from tools import run_twodim_controlled_sweep as sweep
from tools.run_controlled_audit import CellResult, CellSpec


def test_failed_cell_resume_matches_uninterrupted_run(monkeypatch, tmp_path):
    monkeypatch.setattr(sweep, '_provenance', lambda specs, allocation: {'schema': 1})
    calls = []
    fail = True

    def evaluate(spec):
        calls.append(spec.seed)
        if fail and spec.seed == 1:
            return CellResult(spec.model, spec.seed, spec.nfe, spec.sigma, error='injected failure')
        return CellResult(spec.model, spec.seed, spec.nfe, spec.sigma,
                          baseline_metric=1., framework_metric=.9,
                          baseline_nfe=10, framework_nfe=10, nfe_matched=True)

    monkeypatch.setattr(sweep, '_run_twodim_fm', evaluate)
    specs = [CellSpec('twodim_fm', seed, 10, 0.) for seed in range(3)]
    output = tmp_path / 'resumed'
    assert sweep.run(specs, output, resume=False, allocation='evidence') == 1
    assert calls == [0, 1, 2]
    assert json.loads((output / 'cell-0001.json').read_text())['result']['baseline_metric'] is None
    fail = False
    calls.clear()
    assert sweep.run(specs, output, resume=True, allocation='evidence') == 0
    assert calls == [1]
    resumed = json.loads((output / 'summary.json').read_text())
    assert resumed['resumed_cells'] == 2
    fresh = tmp_path / 'fresh'
    assert sweep.run(specs, fresh, resume=False, allocation='evidence') == 0
    assert resumed['cells'] == json.loads((fresh / 'summary.json').read_text())['cells']
    with pytest.raises(FileExistsError):
        sweep.run(specs, output, resume=False, allocation='evidence')


def test_resume_rejects_changed_manifest_before_execution(monkeypatch, tmp_path):
    monkeypatch.setattr(sweep, '_provenance', lambda specs, allocation: {'source': 'new'})
    (tmp_path / 'manifest.json').write_text('{"source": "old"}')
    def forbidden(spec):
        pytest.fail('must reject before executing')
    monkeypatch.setattr(sweep, '_run_twodim_fm', forbidden)
    with pytest.raises(ValueError, match='identical manifest'):
        sweep.run([], tmp_path, resume=True, allocation='evidence')


def test_corrupt_success_checkpoint_fails_closed(monkeypatch, tmp_path):
    monkeypatch.setattr(sweep, '_provenance', lambda specs, allocation: {'schema': 1})
    (tmp_path / 'manifest.json').write_text('{"schema": 1}')
    spec = CellSpec('twodim_fm', 0, 10, 0.)
    (tmp_path / 'cell-0000.json').write_text(json.dumps({
        'spec': sweep.asdict(spec), 'success': True,
        'result': {'error': '', 'nfe_matched': True, 'baseline_metric': None, 'framework_metric': 1.}
    }))
    with pytest.raises(ValueError, match='invalid successful checkpoint'):
        sweep.run([spec], tmp_path, resume=True, allocation='evidence')
