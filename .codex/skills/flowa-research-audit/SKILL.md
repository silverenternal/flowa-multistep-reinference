---
name: flowa-research-audit
description: Audit FlowA research or engineering claims against code, configs, regression vectors, and recorded results; use when investigating gaps, regressions, or readiness.
---

# FlowA Research Audit

Audit claims with a reproducible evidence chain.

- Start from the relevant claim, adapter, wave, or metric; inspect `docs/CLAIMS.md`, `todo/STATUS.md`, and the owning code/config before drawing conclusions.
- Record exact file paths, commit, environment/venv, sample size, and command used. Separate observed facts, interpretation, and unresolved gaps.
- Prefer existing audit and verification tools; do not rerun long GPU sweeps merely to restate a recorded result.
- Check D.4 regression vectors and applicable capability gates after code changes. Preserve fail-closed behavior and the user-gated push policy.
- Write findings to `docs/audit/<topic>.md` or the requested audit surface, then summarize impact and the smallest next action.
