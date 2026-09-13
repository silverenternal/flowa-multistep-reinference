# Open requirements fact sheet (2026-09-13)

Code commits do not by themselves satisfy the six root plans' acceptance
criteria. The current open requirements are:

| Plan | Unmet requirement | Evidence |
|---|---|---|
| Shim audit | Full per-adapter acceptance and follow-up fixes | `docs/audit/wave123-8-adapter-shim-audit.md`; Wan2.2 remains unmeasured |
| Kanzi bridge | N=20 smoke and N=1000 `framework_inv_proj` metric verdict | `docs/audit/kanzi-inv-proj-bridge-followup-2026-09-13.md`; focused tests skipped without torch |
| BRAI metric | LineageFlow and ProtBFN/AbBFN ESM-2 N=100 and N=1000 comparisons | Plan §4 acceptance checklist; no corresponding outputs |
| Beta calibration | CIFAR N=200 matched-NFE and twodim N=100 acceptance runs | Plan §4; no sweep outputs |
| Restart policy | twodim σ=0/0.5 and CIFAR matched-NFE acceptance runs | Plan §4; no sweep outputs |
| Framework-vs-model synthesis | Dependent metric evidence and final acceptance gates | synthesis references Wave 124–126 code, while rows above remain open |

Execution is authorized in this session; remaining blockers are sidecar
dependencies, external weights/ESM-2, compute time, and (for submission
material) review readiness. No requirement is marked complete solely because
implementation code landed.

