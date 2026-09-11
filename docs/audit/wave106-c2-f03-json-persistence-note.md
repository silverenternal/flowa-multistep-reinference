# Wave 106.C.2 F-03 — JSON persistence status (no JSON file change needed)

**Audit ref:** docs/audit/wave106-a-2-audit.md F-03.

**Status:** No action needed.

The on-disk `verification_outputs/lineageflow_n1000_{baseline,framework}_q4_2026.json`
files exist (3275 bytes each, mtime 2026-09-08). They contain Wave 81 N=2 per arm
data with `hmmscan_total_hits=0` for both arms — NOT the +116% / 158 / 342 numbers.

The +116% / 158 / 342 numbers are sourced from `docs/audit/wave86-phase3-sweep.md`
§2 (Wave 86 N=1000 per arm, real framework arm with manifest
`framework_fallback_per_family_count = {}`). Per the A.3 audit, the original Wave 86
sweep JSONs at `/tmp/wave86_eval/{baseline,framework}/summary.json` are gitignored
and not in any committed `verification_outputs/` location.

F-01 (the prev commit) already discloses this state inline at every +116%
citation in `cover_letter.md` + `submission_checklist.md` + `supplementary.md` +
`docs/paper-draft.md`. The JSON state itself is already in a persistent
location (the `_q4_2026` suffix); no file move is required.
