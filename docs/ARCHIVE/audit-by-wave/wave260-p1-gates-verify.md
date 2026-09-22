# Wave 260 P1 — Gates verify after metrics.py revert

## Context

Per user directive ("所有对于别人官方仓库里做的所有更改都要撤回"), all local defensive patches
applied to the vendored upstream file `data/FlowMol3/repo/flowmol/analysis/metrics.py` must be
reverted, and any background retries (seed 44 rerun) must be killed. Wave 260 P1 verifies that
all gates remain GREEN after the revert.

## Pre-revert state (commit 590ce42, Wave 259 P1)

metrics.py had been locally patched with four rounds of defensive try/except + getattr guards
across Waves 244/245/258/259 to tolerate partial / malformed `SampledMolecule` objects
(`Mol` objects rather than `SampledMolecule`). These patches modified vendored upstream code
and are explicitly forbidden by the user's directive — vendored upstream code must be left
untouched.

## Revert action

Working tree of `data/FlowMol3/repo/flowmol/analysis/metrics.py` restored to byte-identical
upstream content (hash `20a3adbcbf09e631ae5519f5dbf4f117`, matching the hash recorded at the
upstream commit the file is vendored from). Diff vs HEAD: 15 insertions / 76 deletions,
removing the Wave 244/245/258/259 `try/except AttributeError`, `getattr(..., None)`, and
`del rdmol`/`del df_pb` defensive wrappers and restoring the upstream direct-attribute access
patterns.

## Background task kill

No background `python` processes are running. The `wave242_p1_flowmol3_rescue_single_mol.py`
seed-44 retry was already terminated before this audit (ps grep returns empty).

## Gates (all GREEN)

### 1. D.4 byte-stable

```
$ timeout 30 .venvs/lineageflow_venv/bin/python -m pytest tests/test_d4_regression_vectors.py -q --no-header
30 passed, 3 warnings in 2.43s
```

30 / 30 PASS preserved.

### 2. mkdocs build --strict

```
$ timeout 30 mkdocs build --strict
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: /home/hugo/codes/flowa-multistep-reinference/site
INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.
INFO    -  Documentation built in 24.46 seconds
```

0 warnings, exit clean. Pass preserved.

### 3. claims consistency

```
$ python3 tools/check_claims_consistency.py
**No drift detected.**
```

No drift. Pass preserved.

### 4. metrics.py revert verification

```
$ md5sum data/FlowMol3/repo/flowmol/analysis/metrics.py
20a3adbcbf09e631ae5519f5dbf4f117  data/FlowMol3/repo/flowmol/analysis/metrics.py
```

md5 matches expected upstream hash — file content byte-identical to upstream. Revert complete.

### 5. Background process check

```
$ ps -ef | grep -E "wave242_p1|wave87_n1000_sweep" | grep -v grep | head -3
(empty)
```

No background seed-44 retry process running.

## Hard-rule compliance

- Framework source code: untouched.
- Vendored upstream code: reverted to byte-identical upstream (the only change to
  `data/FlowMol3/repo/flowmol/analysis/metrics.py` is removal of the Wave 244/245/258/259
  local patches).
- Background tasks: none active, none touched.
- D.4 30 / 30 PASS: preserved.
- mkdocs 0 warnings: preserved.
- claims consistency no drift: preserved.

## Conclusion

All gates GREEN after metrics.py revert. The vendored upstream file is now byte-identical to
upstream, the seed-44 retry is not running, and the three quality gates that Wave 258 P3
last verified (D.4, mkdocs strict, claims consistency) all still pass with the reverted
content.
