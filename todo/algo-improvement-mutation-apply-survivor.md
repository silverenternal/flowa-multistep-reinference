# Algorithm improvement — mutation audit apply-survivor feature (R-4)

**Status:** pending (NEW — Wave 32 Agent B recommendation R-4)
**Date:** 2026-09-05
**Priority:** low (current workflow works; this is an enhancement)
**Depends on:** Wave 17 Phase 2 + Wave 25 F.6 mutation audit (live; 0.833 score)
**Owner:** framework maintainer
**Wave:** Wave 34 (target)
**Goal:** add a `apply-survivor` subcommand to
`tools/run_mutation_audit.py` that emits a surviving mutant as a patch
  against the source code. Closes the mutmut-style feedback loop
  (Finding F-10).

## Background

Per Wave 32 Agent B (`docs/audit/web-research-2026.md` Findings F-9 + F-10 + F-19):

### Finding F-10 (mutmut killer feature: apply on disk)

> **Killer feature: `mutmut apply <mutant>`** — apply a surviving mutant
> to disk so the developer can develop a killing test against it. Most
> mutation tools only report survivors; mutmut lets you turn survivors
> into code in your editor.

### Finding F-19 (apply survivor to disk)

> **Source:** mutmut F-10.
>
> **Key practice:** `mutmut apply <id>` writes the surviving mutant to
> the actual source code so the developer can iterate against it.
>
> **Relevance to us:** our F.6 audit reports survivors in
> `docs/mutation_audit_q4_2026.md` §5; the workflow to act on them is
> "read actionable item → manually edit source → run pytest → repeat".
>
> **Gap / extension:** add `mutmut apply`-style subcommand to
> `tools/run_mutation_audit.py`. Closes the survivor feedback loop.

### Recommendation R-4

> **Action:**
> 1. Add `python tools/run_mutation_audit.py apply <survivor_id>`
   subcommand — emits `mutants/survivor_<id>.patch` and applies it to
   the source (2-day extension).
> 2. Document the workflow in `docs/mutation_audit_q4_2026.md` §6.

## Current workflow (manual)

1. Read `docs/mutation_audit_q4_2026.md` §5 actionable items
2. Identify the surviving mutant by ID (e.g. `MUT-001`)
3. Manually edit the source file to introduce the mutation
4. Run `pytest tests/...` to confirm the test does NOT kill the mutant
5. Write a killing test
7. Revert the manual mutation
8. Confirm the killing test passes against the original source
9. Re-run mutation audit

The "apply on disk" feature automates step 3 and step 7.

## What to do

### Phase A — Extend `tools/run_mutation_audit.py`

1. **Read the current `tools/run_mutation_audit.py`** (886 lines per
   Wave 32 Agent C audit) to understand the existing survivor JSON shape
2. **Add a `apply` subcommand**:
   ```python
   import argparse
   from pathlib import Path

   def main():
       parser = argparse.ArgumentParser()
       subparsers = parser.add_subparsers(dest="command")

       # ... existing audit subcommand ...

       apply_parser = subparsers.add_parser(
           "apply",
           help="Apply a surviving mutant to disk for inspection",
       )
       apply_parser.add_argument("survivor_id", type=str,
                                  help="Survivor ID (e.g. MUT-001)")
       apply_parser.add_argument("--patch-only", action="store_true",
                                  help="Emit the patch without applying it")
       args = parser.parse_args()

       if args.command == "apply":
           apply_survivor(args.survivor_id, args.patch_only)

   def apply_survivor(survivor_id: str, patch_only: bool = False) -> None:
       """Apply a surviving mutant to disk; emit a patch file."""
       audit_json = Path("verification_outputs/mutation_audit_q4_2026.json")
       if not audit_json.exists():
           raise FileNotFoundError(
               f"Run the audit first: python tools/run_mutation_audit.py audit"
           )
       with audit_json.open() as f:
           audit = json.load(f)
       survivor = next(
           (s for s in audit["survivors"] if s["id"] == survivor_id),
           None,
       )
       if survivor is None:
           raise ValueError(f"Survivor {survivor_id} not found in audit")

       # Generate the patch
       patch_path = Path(f"mutants/survivor_{survivor_id}.patch")
       patch_path.parent.mkdir(exist_ok=True)
       patch_content = generate_patch(survivor)
       patch_path.write_text(patch_content)

       if patch_only:
           print(f"Patch emitted: {patch_path}")
           return

       # Apply the patch (uses `git apply`)
       import subprocess
       result = subprocess.run(
           ["git", "apply", str(patch_path)],
           capture_output=True, text=True,
       )
       if result.returncode != 0:
           raise RuntimeError(
               f"git apply failed: {result.stderr}\n"
               f"Patch file retained at {patch_path}"
           )
       print(f"Applied {survivor_id}; patch retained at {patch_path}")
       print(f"Run pytest, write a killing test, then `git apply -R {patch_path}` to revert.")
   ```

3. **Add the `generate_patch` helper** that converts the survivor JSON
   (operator + location + before/after) to a unified-diff patch:
   ```python
   def generate_patch(survivor: dict) -> str:
       """Convert a survivor JSON entry to a unified-diff patch string."""
       file_path = survivor["file"]
       line_no = survivor["line"]
       before = survivor["before"]
       after = survivor["after"]
       return (
           f"--- a/{file_path}\n"
           f"+++ b/{file_path}\n"
           f"@@ -{line_no},1 +{line_no},1 @@\n"
           f"-{before}\n"
           f"+{after}\n"
       )
   ```

### Phase B — Survivor CLI ergonomics

1. **Add a `list` subcommand** to enumerate surviving mutants:
   ```python
   list_parser = subparsers.add_parser("list", help="List surviving mutants")
   list_parser.add_argument("--json", action="store_true")
   ```

2. **Add a `revert` helper** that wraps `git apply -R`:
   ```python
   def revert_survivor(survivor_id: str) -> None:
       patch_path = Path(f"mutants/survivor_{survivor_id}.patch")
       if not patch_path.exists():
           raise FileNotFoundError(patch_path)
       subprocess.run(["git", "apply", "-R", str(patch_path)], check=True)
       print(f"Reverted {survivor_id}")
   ```

### Phase C — Documentation update

1. **Update `docs/mutation_audit_q4_2026.md` §6** with the new
   workflow:
   ```markdown
   ## 6. Acting on survivors (Wave 32 R-4)

   To act on a survivor, use the new apply subcommand:

   ```bash
   # List surviving mutants
   python tools/run_mutation_audit.py list

   # Apply a survivor to disk (for inspection / killing-test development)
   python tools/run_mutation_audit.py apply MUT-001

   # Or emit the patch without applying
   python tools/run_mutation_audit.py apply MUT-001 --patch-only

   # After writing a killing test, revert the mutation
   python tools/run_mutation_audit.py revert MUT-001  # or: git apply -R mutants/MUT-001.patch
   ```

   This closes the survivor feedback loop that mutmut pioneered.
   ```

### Phase D — Verification

1. **Run `python tools/run_mutation_audit.py list`** — should list all
   surviving mutants from `verification_outputs/mutation_audit_q4_2026.json`
2. **Run `python tools/run_mutation_audit.py apply MUT-001 --patch-only`**
   on a known survivor — should emit `mutants/MUT-001.patch`
3. **Run `python tools/run_mutation_audit.py apply MUT-001`** — should
   apply the patch; verify with `git diff`
4. **Run `python tools/run_mutation_audit.py revert MUT-001`** (or
   `git apply -R mutants/MUT-001.patch`) — should revert
5. **Verify source is restored** — `git diff` should be empty

## Files affected

- `tools/run_mutation_audit.py` (UPDATE; add `apply` + `list` + `revert`
  subcommands, ~80 LOC)
- `docs/mutation_audit_q4_2026.md` §6 (UPDATE; document the new workflow)
- `mutants/survivor_*.patch` (NEW; emitted on demand)

## Acceptance

- [ ] `apply` subcommand works (patch-only + apply modes)
- [ ] `list` subcommand works
- [ ] `revert` subcommand works (or `git apply -R` documented)
- [ ] `docs/mutation_audit_q4_2026.md` §6 documents the workflow
- [ ] Manual verification: apply → revert round-trip succeeds
- [ ] `pytest tests/` still passes (no source change)

## Acceptance gate

Passes if:
1. `apply` subcommand successfully emits + applies a patch
2. `revert` subcommand (or manual `git apply -R`) restores the source
3. The round-trip is clean (no source drift after apply + revert)

## Estimated time

~1-2 hours total:
- Tool extension: ~1 hour
- Documentation: ~15 min
- Manual verification: ~15 min

## Risk

- **LOW**: `git apply` may fail if the patch doesn't match the current
  source (e.g. another commit changed the line)
  → **Mitigation**: retain the patch file on failure; user can manually
  reconcile
- **LOW**: the `before`/`after` strings in the JSON may not exactly match
  the source line (e.g. trailing whitespace)
  → **Mitigation**: the `generate_patch` helper strips trailing whitespace;
  document the convention

## Follow-up

- **CI integration** (auto-list survivors on each PR): LOW priority;
  defer; manual review suffices
- **Visual patch viewer** (e.g. open the patch in `code --diff`): LOW
  priority; defer

## Related fix opportunities (within scope of this PR)

Per `docs/audit/framework-code-review.md` §1.15 [MEDIUM-14]:
- `_op_weight_perturbation` skips constants in `(-1, 0, 1)` (line 227-228)
  but skips too aggressively when `0.5` or `0.95` is meaningful
- Document the skip list explicitly (1-line; include in this PR)

Per `docs/audit/framework-code-review.md` §1.15 [LOW-28]:
- `_run_twodim_fm` calls `self._adapter._batched_integrate_rk4(...)`
  accessing a private method
- Add the `# test seam` comment (1-line; include in this PR)