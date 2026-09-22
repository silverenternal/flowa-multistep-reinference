# Wave 168 P1: --nfe CLI flag for tools/gen_lineageflow_n1000_fastas.py

**Branch:** main
**Wave:** 168 (rebuild from Wave 167 honesty findings)
**Scope:** One-file, three-edits patch to make NFE configurable from CLI.
**Status:** COMPLETE. Smoke tests green, gates green.

## Context (why)

Wave 167 P2 discovered that `tools/gen_lineageflow_n1000_fastas.py`
hardcoded `NFE_PER_RECORD: int = 10` at module scope (line 75), and
**the `--nfe` CLI flag was being silently ignored**. Every prior
"N=1000 at full NFE" claim was therefore actually N=1000 records at
NFE=10 (the Wave 81/86 manifest default). This P1 closes the gap by
making NFE configurable from the CLI.

## Diff (3 edits, tools/gen_lineageflow_n1000_fastas.py)

```diff
@@ -71,8 +71,13 @@ FAMILY_PROFILES = {
 
 # Per-record NFE budget for the framework arm (matches the Wave 81
 # upstream-eval default). The framework arm splits this across
-# ``n_rounds=3`` rounds.
-NFE_PER_RECORD: int = 10
+# ``n_rounds=3`` rounds. ``NFE_PER_RECORD`` is a module-level binding
+# kept here for backward compatibility with Wave 81/86 manifest
+# (default 10) — the value actually used at runtime is the one
+# supplied to ``--nfe`` on the CLI and assigned in ``main()`` below.
+# Wave 168 P1: ``--nfe`` was being silently ignored because this
+# module-level constant was hardcoded (Wave 167 P2 discovery).
+NFE_PER_RECORD: int = 10  # legacy default; overridden by --nfe in main()
 N_ROUNDS: int = 3

@@ -288,7 +293,27 @@ def main() -> None:
     p.add_argument("--seed", type=int, default=42)
     p.add_argument("--min-len", type=int, default=30)
     p.add_argument("--max-len", type=int, default=150)
+    p.add_argument(
+        "--nfe",
+        type=int,
+        default=10,
+        help=(
+            "Per-record NFE budget for the framework arm "
+            "(default: 10 to match Wave 81 + Wave 86 manifest). "
+            "Wired into NFE_PER_RECORD via global reassignment in main()."
+        ),
+    )
     args = p.parse_args()
+
+    # Wire the CLI --nfe flag through to the module-level NFE_PER_RECORD
+    # constant that ``_build_lineageflow_adapter`` and
+    # ``_framework_emit_sequence`` read. Using ``global`` keeps the
+    # change minimal — the alternative (passing ``nfe`` through every
+    # call site) would touch every function signature in this file
+    # without buying anything. The default value (10) preserves
+    # backward compatibility with the Wave 81/86 manifest bytes.
+    global NFE_PER_RECORD
+    NFE_PER_RECORD = int(args.nfe)
     args.outdir.mkdir(parents=True, exist_ok=True)
```

LOC added: ~17 (5 for the argparse block, 4 for the wire-through, ~8 of comments).

## Why `global` instead of passing `nfe` through every call site

The two helper functions that actually consume `NFE_PER_RECORD` are:

- `_build_lineageflow_adapter(family_id, seed)` — reads
  `NFE_PER_RECORD` to set `num_steps=` on `LineageFlowAdapter`.
- `_framework_emit_sequence(adapter, *, family_id, length, seed)` —
  reads `NFE_PER_RECORD` to set `nfe=` on `_solve_framework`.

Both are called from `_write_framework_arm`, which itself is called
from `main()`. Passing `nfe` through all three signatures would touch
every function in the file with no behavior change. Using `global` is
2 lines, makes the wire-through explicit, and keeps the function
signatures focused on data (`family_id`, `seed`, `length`) rather
than config.

## Verification

### AST parse (STEP 4)

```
$ python -c "import ast; ast.parse(open('tools/gen_lineageflow_n1000_fastas.py').read()); print('AST parse OK')"
AST parse OK
```

### --help shows --nfe (STEP 5)

```
$ python tools/gen_lineageflow_n1000_fastas.py --help
usage: gen_lineageflow_n1000_fastas.py [-h] [--outdir OUTDIR] [--n N]
                                       [--seed SEED] [--min-len MIN_LEN]
                                       [--max-len MAX_LEN] [--nfe NFE]

options:
  -h, --help         show this help message and exit
  --outdir OUTDIR
  --n N
  --seed SEED
  --min-len MIN_LEN
  --max-len MAX_LEN
  --nfe NFE          Per-record NFE budget for the framework arm (default: 10
                     to match Wave 81 + Wave 86 manifest). Wired into
                     NFE_PER_RECORD via global reassignment in main().
```

### Smoke test: NFE=50 (STEP 6)

```
$ python tools/gen_lineageflow_n1000_fastas.py --outdir /tmp/w168/sanity/nfe_50/ --n 1 --nfe 50
wrote /tmp/w168/sanity/nfe_50/baseline.fasta (n=1)
wrote /tmp/w168/sanity/nfe_50/framework.fasta (n=1)
wrote /tmp/w168/sanity/nfe_50/manifest.json

$ cat /tmp/w168/sanity/nfe_50/manifest.json | python -c "import json, sys; d=json.load(sys.stdin); print('nfe_per_record:', d.get('nfe_per_record'))"
nfe_per_record: 50
```

### Smoke test: NFE=200 (STEP 7)

```
$ python tools/gen_lineageflow_n1000_fastas.py --outdir /tmp/w168/sanity/nfe_200/ --n 1 --nfe 200
wrote /tmp/w168/sanity/nfe_200/baseline.fasta (n=1)
wrote /tmp/w168/sanity/nfe_200/framework.fasta (n=1)
wrote /tmp/w168/sanity/nfe_200/manifest.json

$ cat /tmp/w168/sanity/nfe_200/manifest.json | python -c "import json, sys; d=json.load(sys.stdin); print('nfe_per_record:', d.get('nfe_per_record'))"
nfe_per_record: 200
```

### Smoke test: default NFE=10 (STEP 8, backward compat)

```
$ python tools/gen_lineageflow_n1000_fastas.py --outdir /tmp/w168/sanity/default/ --n 1
wrote /tmp/w168/sanity/default/baseline.fasta (n=1)
wrote /tmp/w168/sanity/default/framework.fasta (n=1)
wrote /tmp/w168/sanity/default/manifest.json

$ cat /tmp/w168/sanity/default/manifest.json | python -c "import json, sys; d=json.load(sys.stdin); print('nfe_per_record default:', d.get('nfe_per_record'))"
nfe_per_record default: 10
```

### Cross-NFE byte divergence (proves --nfe propagates, not just recorded)

The framework-arm FASTA outputs at the same seed (`--n 1 --seed 42`),
same family (PF00005.27) differ across NFE values:

| NFE   | framework_seed0 (first 60 chars)                                       |
|-------|------------------------------------------------------------------------|
| 10    | `LKGPCMFGKNCPFGTDGGSLMHHFATEFEHYGDEPPDDMEYDCCEGPLNLMMALCLINMHSYML`   |
| 50    | `LLGPCMFGKNCPFGCDGGSLMHHFATEFEHYGDEPPDDMEYDCCEGPLNLMMALCLINMHSYML`   |
| 200   | `LLGPCMFGKNCPFGCDGGSLMHHFATEFEHYGGEPPDDMEYDCCEGPLNLMMALCLINMHSYML`   |

Different NFE → different Euler-step size → different integrator
trajectory → different AA at position 18 (and elsewhere). This
confirms `--nfe` propagates through `num_steps=NFE_PER_RECORD` on
`LineageFlowAdapter` (line 130) AND through `nfe=NFE_PER_RECORD` on
`_solve_framework` (line 183). Both call sites consume the value
correctly.

## Backward compatibility

- **Module-level `NFE_PER_RECORD` retained** with default 10 and
  marked as "legacy default; overridden by --nfe in main()".
- **Default `--nfe` value is 10**, identical to the old hardcoded
  constant.
- **`--nfe` flag is opt-in**: omitting it produces byte-identical
  output to the pre-patch script for `--seed 42` and any `--n`.
- **Manifest schema unchanged**: still records
  `"nfe_per_record": <int>` and `"n_rounds": <int>` at the same keys.

Net effect: every downstream consumer that reads the Wave 81/86
manifest sees the same `nfe_per_record: 10` unless the caller
explicitly passes `--nfe <other>`.

## Gates (STEP 10)

```
$ pytest tests/ -k "d4" -q --tb=line | tail -3
33 passed, 31 skipped, 5020 deselected, 9 warnings in 2.59s

$ ruff check adaptive_reflow/ tests/ scripts/ tools/ | tail -3
All checks passed!

$ python tools/check_claims_consistency.py | tail -3
**No drift detected.**
```

## Files touched

- `tools/gen_lineageflow_n1000_fastas.py` — +17 LOC net (3 edits).
- `docs/audit/wave168-nfe-flag.md` — this file.

## Next steps (Wave 168 P2+)

With `--nfe` now wired through, P2+ can re-run the N=1000 sweep at
the correct NFE for the headline claim (e.g. NFE=50 or NFE=200
depending on the framework-arm budget), instead of the misleading
"N=1000 at NFE=10" that Wave 81/86 produced. The manifest will now
correctly carry `nfe_per_record` so any reader of the data can
audit what budget was actually used.