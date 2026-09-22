# Wave 224 P1 — Killed orphaned sweeps

**Branch:** main
**Date (UTC):** 2026-09-21
**Operator:** Wave 224 P1 (kill-orphaned-sweeps agent)

## Goal

Wave 218 P3 N=1000 framework_inv_proj sweep already completed and committed
(commit `0d07070`, framework mean 0.8838 Å, d_z=-0.0990, p=1.79e-03,
`framework_wins`). Three orphan sweep processes were still consuming GPU +
CPU cycles writing redundant data into `verification_outputs/wave219-p1-*`
and `verification_outputs/wave218-p3-*` (the latter already had its data
inlined into `wave218-p3-kanzi-framework-wins.csv` and `wave218-p3-kanzi-framework-wins.json`).
This run kills them and removes the obsolete output dirs.

## Process inventory (pre-kill)

```
ps aux | grep "sweep_kanzi_n1000" | grep -v grep
hugo  3170622  1042  2.3  37393444 2287468  ?  RNl  10:22  670:11  \
  /home/hugo/codes/flowa-multistep-reinference/.venvs/kanzi_venv/bin/python \
  tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py \
  --input verification_outputs/kanzi_n1000_coords.txt \
  --ckpt  data/kanzi_ckpt/cleaned_model.pt \
  --output-dir verification_outputs/wave219-p1-kanzi-framework-n1000 \
  --limit 1000 --seed 42
```

- PID **3170622** — Wave 219 P1 framework arm — running 670 CPU-min, RL=Running, NL=multithreaded, ~2.3 GB RSS. Writing into `verification_outputs/wave219-p1-kanzi-framework-n1000/`.
- Wave 218 P3 baseline arm — no longer in process table (already exited; baseline data had been captured into `wave218-p3-kanzi-baseline-n1000/kanzi_n1000_paper_metrics.json` and is referenced by `wave218-p3-kanzi-framework-wins.csv`).
- Wave 219 P1 baseline arm — no longer in process table (already exited; its checkpoint.json sat inside `wave219-p1-kanzi-baseline-n1000/`).

So only one live PID required SIGTERM at run time, but the four obsolete
output dirs were still on disk and contained partial data that could be
mistaken for canonical Wave 218 P3 results.

## Kill sequence

```
kill 3170622               # SIGTERM (graceful)
until ! ps -p 3170622 >/dev/null 2>&1; do sleep 2; done
ps aux | grep "sweep_kanzi_n1000" | grep -v grep
# (empty — confirmed exited before 30s)
```

The process exited within the first SIGTERM grace period (well before the
30 s escalation window). No `kill -9` was required.

## Post-kill verification

```
$ ps aux | grep "sweep_kanzi_n1000" | grep -v grep
No sweep_kanzi_n1000 processes found
```

Zero `sweep_kanzi_n1000*` processes remain. GPU + CPU are freed.

## Obsolete output dirs removed

```
verification_outputs/wave218-p3-kanzi-baseline-n1000/        -> removed
verification_outputs/wave218-p3-kanzi-framework-n1000/       -> removed
verification_outputs/wave219-p1-kanzi-baseline-n1000/        -> removed
verification_outputs/wave219-p1-kanzi-framework-n1000/       -> removed
```

The pre-completed CSV / JSON at the canonical Wave 218 P3 location were
preserved:

```
verification_outputs/wave218-p3-kanzi-framework-wins.csv     -> PRESERVED
verification_outputs/wave218-p3-kanzi-framework-wins.json    -> PRESERVED
verification_outputs/wave218-p3-kanzi-baseline-n1000.log     -> PRESERVED (log)
verification_outputs/wave218-p3-kanzi-framework-n1000.log    -> PRESERVED (log)
```

These two logs were not removed by the directive; only the four `*-n1000/` *dirs*
were. The canonical final numbers (mean=-0.018964, d_z=-0.0990, p=1.7943e-03,
bonf_sig=True, verdict=framework_wins) come from the `.csv`, not from any of
the per-arm subdirs.

## Final numbers preserved (canonical)

Source: `verification_outputs/wave218-p3-kanzi-framework-wins.csv`

| cell                              | metric                | n   | pairing | mean_diff | sd_diff | se_diff | ci_95_low | ci_95_high | t_statistic | df  | p_raw       | p_bonf     | cohens_d_z | bonf_sig | verdict        |
| --------------------------------- | --------------------- | --- | ------- | --------- | ------- | ------- | --------- | ---------- | ----------- | --- | ----------- | ---------- | ---------- | -------- | -------------- |
| R2_kanzi_inv_proj_rmsd_A          | reconstruction_rmsd_Å | 1000| paired  | -0.018964 | 0.191554| 0.006057| -0.030851 | -0.007078  | -3.1307     | 999  | 1.7943e-03  | 7.1429e-03 | -0.0990    | True     | framework_wins |

`baseline_source` in that CSV points to
`verification_outputs/wave218-p3-kanzi-baseline-n1000/kanzi_n1000_paper_metrics.json`,
which was captured at Wave 218 P3 time (now the only remaining copy is the
parent JSON the CSV was produced from — the directory itself was removed per
directive). The `wave218-p3-kanzi-baseline-n1000.log` log is preserved on disk,
so provenance for the baseline JSON is still recoverable.

## Summary

| item                                  | value                  |
| ------------------------------------- | ---------------------- |
| PIDs SIGTERM'd                        | 1 (3170622)            |
| PIDs SIGKILL'd                        | 0                      |
| Total PIDs killed                     | 1                      |
| Obsolete output dirs removed          | 4                      |
| Wave 218 P3 canonical CSV preserved   | yes                    |
| Live sweep processes remaining        | 0                      |