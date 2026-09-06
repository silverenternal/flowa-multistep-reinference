"""Wave 52 — SOTA re-inference baselines for the adaptive_reflow framework.

This package contains three standalone baseline implementations, selected
by Agent A's read-only SOTA survey (`docs/audit/wave52-sota-baselines-survey.md`):

* ``consistency_model`` — Consistency Models + iCT (Song 2023; Song & Dhariwal 2024).
* ``rectified_flow_reflow`` — Rectified Flow + Reflow (Liu et al. 2022, ICLR 2023 Spotlight).
* ``dpm_solver_plus_plus`` — DPMSolver++ multistep (Lu et al. 2022/2023).

Each baseline is a pure-NumPy/NumPy+SciPy script that consumes the existing
``adaptive_reflow`` adapter Protocol surface (``batched_inference``,
``_velocity_field``) so the comparison is "same checkpoint, different
outer inference loop". None of them touch ``adaptive_reflow/`` code.

Run via ``scripts/baselines/run_baselines.py`` — produces a single JSON
artefact at ``verification_outputs/baseline_comparison_q4_2026.json``.
"""
