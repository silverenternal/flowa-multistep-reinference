# Documentation and evidence audit — 2026-09-13

Scope: claims ledger, governance cross-references, and claim-level regression
tests. No long-running GPU experiments were started.

## Checks

| Check | Command | Result |
|---|---|---|
| Claims consistency | `python tools/check_claims_consistency.py` | PASS; 39 active, 2 deprecated, drift 0 |
| Claim 045 provenance notes | `pytest -q tests/test_claims/test_claim_045.py` | PASS (3 tests) |
| MkDocs strict build | `mkdocs build --strict` | BLOCKED: `mkdocs` executable is not installed in this environment |

## Findings and fixes

The claims verifier reported missing governance references for CLM-040 and
CLM-041. Both are now linked from `docs/INSIGHTS.md`, restoring complete
cross-reference coverage. Claim 045 tests also exposed stale compatibility
shims after the Wave 105 package split: the top-level merge and scheduler
shims lacked the required CLM-042 / `e_rho / 4` provenance notes. Notes were
added without changing runtime behavior; all three tests pass.

The strict MkDocs check requires the project documentation toolchain to be
installed before release validation. This is an environment gap, not a
documentation failure; CI should continue to run the check in its docs
environment.
