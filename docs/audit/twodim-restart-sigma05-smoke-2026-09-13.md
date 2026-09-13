# Twodim restart-policy sigma=0.5 smoke (2026-09-13)

The quick controlled audit ran `twodim_fm` at NFE 10, 50, and 200 with
`sigma=0.5`, seed 0. All matched-NFE checks passed and no measurement
artifacts were detected. Framework W2 deltas were `+0.1624`, `+0.1338`, and
`+0.0993`, respectively, so this smoke records regression evidence and does
not close the restart-policy acceptance requirement.

The JSON checkpoint is at
`verification_outputs/twodim_restart_sigma05_smoke_20260913/result.json`.
