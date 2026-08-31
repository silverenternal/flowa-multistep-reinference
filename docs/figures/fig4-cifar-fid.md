# Figure 4 — CIFAR-10 baseline vs FlowA framework FID

![CIFAR-10 FID bars](fig4-cifar-fid.png)

**Caption.** CIFAR-10 Rectified Flow (Liu 2022 NeurIPS Spotlight, 61.8 M
parameters, gnobitab `state_dict`) baseline (single-pass 50-NFE Euler)
vs FlowA framework with 4 schedulers (10 rounds × 50 framework samples
each). Published Liu 2022 SOTA = 2.58 is shown as the reference line
(yellow dashed). Honest framing: framework uses ~25 NFE per sample vs
baseline's 50 NFE; framework rows are +24–31% higher than baseline at
this budget; **scheduler discrimination: YES** at v4 (4 distinct FIDs
spread across a ~5.1-FID window).

**Source data**: `docs/r4-survey/cifar_results_v4/comparison.md`,
`docs/r4-survey/cifar_results_v4/summary.json`, `docs/CLAIMS.md`
CLM-040 / CLM-041.
**Paper reference**: `docs/paper-plan.md` §4.3.