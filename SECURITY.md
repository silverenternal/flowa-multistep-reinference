# Security Policy

## Supported versions

This is a single-maintainer research project. Only the `main` branch
receives security-relevant fixes. Tagged releases on `main` are listed
in `CHANGELOG.md`. There are no backports to older branches.

## No security-sensitive surface

`flowa-multistep-reinference` is a typed-contracts framework for
governed Flow Matching re-inference. The package has **no
security-sensitive surface**:

* **CPU-only.** No GPU code paths. No CUDA, ROCm, Metal, or WebGPU.
* **Stdlib-only.** The runtime depends only on the Python standard
  library. The package imports no third-party Python module at
  import time. Test-time tools (`hypothesis`, `pytest-benchmark`,
  `mutmut`, `mypy`, `ruff`) are dev-only and do not run in shipped
  contexts.
* **No I/O.** The package does not open files, read environment
  variables, or touch the network. It has no `open()`, no `os.environ`,
  no `urllib`, no `requests`, no `socket`.
* **No subprocess.** No shelling out, no `subprocess`, no `os.system`,
  no `multiprocessing`.
* **No GPU / native tensor.** `import torch` is forbidden inside
  `adaptive_reflow/`. Adapters wrap their native tensor libraries
  behind an opaque `TensorRef` boundary.
* **No mutation of inputs.** Every pure function in `contracts/` and
  `universal/` returns a new dataclass; no in-place state changes.
* **No persistence.** The package writes no log files, no checkpoints,
  no telemetry.

If you find code that violates any of the above, that is a defect and
should be filed as a bug.

## Reporting a vulnerability

Because the package has no security-sensitive surface, the
realistic attack surface is the **build / supply chain**: a malicious
commit to `main`, a compromised PyPI release, or a tampered source
mirror. To report one of these:

* Open a private security advisory via GitHub:
  `https://github.com/silverenternal/flowa-multistep-reinference/security/advisories/new`
* Or email the maintainer at the address in the commit history.

Please do **not** open a public issue for a suspected supply-chain
defect. The maintainer will acknowledge within seven days and ship a
fix or downgrade path within thirty days of confirmation.

## Out of scope

The following are deliberately out of scope as security reports:

* Empirical claims about Flow Matching model behaviour (use the
  research-issue tracker instead).
* Performance regressions outside the 20% regression threshold
  (use `tools/bench/check_budgets.py` and the bench-regression
  workflow).
* Failure modes in `adaptive_reflow.legacy/` (quarantined; the
  quarantine is the mitigation).
* Crashes in test-only tooling (`hypothesis`, `mutmut`, etc.).

The audit-code policy documented in ADR-0005 is a *contract-correctness*
invariant, not a security boundary; a missing `AUDIT_*` constant is a
test-coverage defect, not a vulnerability.