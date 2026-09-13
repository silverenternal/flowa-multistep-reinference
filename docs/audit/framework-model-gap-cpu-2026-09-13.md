# Framework/model metrics gap — CPU audit

The synthesis plan's CPU-verifiable decision-metric improvement is already
landed as P2-W33-C. `tools/run_controlled_audit.py` uses continuous
`_per_position_entropy` for LineageFlow decision values while retaining the
saturated `family_validity` field for compatibility. The entropy helper is
finite, bounded by `log(K)`, and returns NaN for degenerate inputs.

Focused validation passed **16 tests** across the entropy and controlled-audit
contracts (11 warnings). No external weights, model downloads, SOTA claims, or
long sweeps were used. Remaining hypotheses (beta calibration, ESM-2 NLL,
adapter bridges) require model-specific experiments and remain deferred.
