# Intentionally empty

`docs/CLAIMS.md` (CLM-065) links to this directory and says so in the prose:
the N=1000 LineageFlow sweep was killed for CPU wall-clock, and Wave 201
removed that blocker. Nothing was ever written here.

Git cannot track an empty directory, so this README exists to keep the path
resolvable on a fresh clone — the `baseline/` and `framework/` subdirectories
are the two arm names the sweep would have filled.

The live LineageFlow N=1000 evidence is elsewhere:

- `verification_outputs/lineageflow_n1000_omegafold_q4_2026_baseline.json`
- `verification_outputs/lineageflow_n1000_omegafold_q4_2026_framework.json`
- `verification_outputs/wave206-p1-lineageflow-n1000/`

Audit: [`docs/audit/clone-reproducibility.md`](../../docs/audit/clone-reproducibility.md).
