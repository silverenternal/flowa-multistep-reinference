# Open requirements fact sheet (2026-09-13)

Code commits do not by themselves satisfy the six root plans' acceptance
criteria. The current open requirements are:

| Plan | Unmet requirement | Evidence |
|---|---|---|
| Shim audit | Full per-adapter acceptance and follow-up fixes | `docs/audit/wave123-8-adapter-shim-audit.md`; Wan2.2 remains unmeasured |
| Kanzi bridge | Scientific bridge calibration, full refinement protocol and N=1000 verdict | N=20 legacy single-rollout diagnostic completed; sidecar tests run with Torch. See `docs/audit/kanzi-inv-proj-bridge-followup-2026-09-13.md`. |
| BRAI metric | LineageFlow and ProtBFN/AbBFN ESM-2 N=100 and N=1000 comparisons | Plan §4 acceptance checklist; no corresponding outputs |
| Beta calibration | Threshold acceptance and planned twodim N=100 protocol | CIFAR N=200 matched per-sample NFE=50 completed with regression; twodim quick smoke exists but does not prove the specified calibration protocol. |
| Restart policy | Guard-specific acceptance under the planned restart protocol | twodim σ=0/0.5 quick diagnostics and CIFAR N=200 outputs exist; no verified acceptance of the complete restart policy. |
| Framework-vs-model synthesis | Dependent metric evidence and final acceptance gates | synthesis references Wave 124–126 code, while rows above remain open |

Execution is authorized in this session. Kanzi checkpoint, sidecar dependencies
and GPU execution were verified available; they are not current blockers.
Remaining work includes protocol corrections and required experiments; other
models' external weights/ESM-2 must be checked separately. Submission material
also depends on review readiness. No requirement is marked complete solely because
implementation code landed.

