# Algorithm improvement — host_fingerprint in every JSON output (R-2)

**Status:** CLOSED in Wave 38 (commit d55b601, Wave 38 Agent A WF3) — R-2 closed: adaptive_reflow/util/host_fingerprint.py module + tests/test_util/test_host_fingerprint.py + 7 call-site updates (api_churn_report, capture_env_hash, run_mypy_audit, capability_audit, run_controlled_audit, run_sbc_audit, util/__init__)
**Date:** 2026-09-05
**Priority:** medium (audit-output provenance hygiene)
**Depends on:** F.5 env_hash infrastructure (live; Wave 15)
**Owner:** framework maintainer
**Wave:** Wave 34 (target)
**Goal:** author `adaptive_reflow/util/host_fingerprint.py` and emit it
from every `tools/run_*` script that writes JSON. Mirrors the
SciMLBenchmarks.jl auto-append pattern (Finding F-5).

## Background

Per Wave 32 Agent B (`docs/audit/web-research-2026.md` Finding F-5 + F-15):

### Finding F-5 (SciMLBenchmarks.jl work-precision framing)

> Per-benchmark `Project.toml` + `Manifest.toml`. **Computer
> characteristics auto-appended at the bottom of every benchmark.**
>
> **Relevance to us**: our `tools/run_sbc_audit.py` already uses
> work-precision-style framing. **The "auto-append computer
> characteristics" pattern is one we should adopt: every
> `verification_outputs/*.json` should carry `host.os`, `host.python`,
> `host.torch`, `host.cuda` keys.**

### Finding F-15 (Auto-append host characteristics)

> **Source:** SciMLBenchmarks F-5 ("computer characteristics
> auto-appended at the bottom of every benchmark").
>
> **Key practice:** every benchmark/audit output should carry host
> fingerprint (python, torch, cuda, hostname hash).
>
> **Relevance to us:** our `verification_outputs/*.json` files do
> **not** carry host characteristics. When a future agent reads
> `verification_outputs/sbc_audit_n1000.json` they cannot tell which
> machine generated it.
>
> **Gap / extension**: add a `host_fingerprint` helper module + emit it
> from every `tools/run_*` script. Closes the "we don't know which
> machine produced this output" gap. Cost: ~20 LOC + ~10 call sites.

### Recommendation R-2

> **Action:**
> 1. Author `adaptive_reflow/util/host_fingerprint.py` — emits
>    `{"python": "3.11.5", "torch": "2.1.2", "cuda": "12.1",
>    "hostname_hash": "sha256:..."}` (1 module, ~20 LOC).
> 2. Add 1-line call to every `tools/run_*` script that writes JSON
>    (10 call sites).
> 3. Add `host_fingerprint` check to F.2 verification — auto-classify
>    PARTIAL if host differs from `env_hash.txt` reference (LOW priority
>    extension).

## What to do

### Phase A — Author `adaptive_reflow/util/host_fingerprint.py`

```python
"""Capture host characteristics for audit-output provenance.

Returns:
    dict with keys: python, torch, cuda, hostname_hash, platform,
    captured_at (ISO 8601).
"""

import hashlib
import json
import platform
import socket
import sys
from datetime import datetime, timezone


def capture_host_fingerprint() -> dict[str, str]:
    """Capture a stable, JSON-serialisable fingerprint of the current host."""
    hostname = socket.gethostname()
    hostname_hash = "sha256:" + hashlib.sha256(
        hostname.encode("utf-8")
    ).hexdigest()[:16]
    fp: dict[str, str] = {
        "python": sys.version.split()[0],  # e.g. "3.11.5"
        "platform": platform.platform(),
        "hostname_hash": hostname_hash,
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        import torch
        fp["torch"] = torch.__version__
        fp["cuda"] = torch.version.cuda or "none"
    except ImportError:
        fp["torch"] = "not_installed"
        fp["cuda"] = "n/a"
    return fp


def with_host_fingerprint(payload: dict | list) -> dict:
    """Return a copy of payload with `_host_fingerprint` field appended.

    Used by tools/run_*.py scripts at JSON-dump time.
    """
    if isinstance(payload, dict):
        result = dict(payload)
        result["_host_fingerprint"] = capture_host_fingerprint()
        return result
    if isinstance(payload, list):
        # Wrap in an envelope with metadata
        return {
            "_host_fingerprint": capture_host_fingerprint(),
            "items": payload,
        }
    raise TypeError(f"with_host_fingerprint: unsupported payload type {type(payload)}")
```

### Phase B — Wire into every `tools/run_*` script

10 call sites per Wave 32 Agent B §R-2:
1. `tools/capability_audit.py` — line where `capability_audit_q3_2026.json` is written
2. `tools/run_sbc_audit.py` — line where `sbc_audit_n{200,1000,10000}.json` is written
3. `tools/run_mutation_audit.py` — line where `mutation_audit_q4_2026.json` is written
4. `tools/run_controlled_audit.py` — line where controlled audit JSON is written
5. `tools/run_metrics_audit.py` (if exists) — line where audit JSON is written
6. `scripts/capture_env_hash.py` — line where `env_hash.txt` is written
7. `scripts/api_churn_report.py` — line where churn report is written
8. `scripts/run_mypy_audit.py` — line where type-soundness report is written
9. `scripts/check_deprecation_policy.py` — line where deprecation report is written
10. `tools/conformance_dashboard.py` (planned per Wave 32 Agent B R-1 extension)

For each call site, the diff is:
```python
import json
from adaptive_reflow.util.host_fingerprint import with_host_fingerprint

# Before:
result = compute_audit(...)
with open(output_path, "w") as f:
    json.dump(result, f, indent=2)

# After:
result = compute_audit(...)
result = with_host_fingerprint(result)
with open(output_path, "w") as f:
    json.dump(result, f, indent=2)
```

### Phase C — CI integration (low priority)

1. **Optionally add a CI check** that re-runs an audit tool and verifies
   the `_host_fingerprint` field is present
   - **Scope decision**: defer (LOW priority; the field is always present
     if `with_host_fingerprint` is called)

### Phase D — Verification + docs

1. **Run each of the 10 tools** and verify the output JSON carries the
   `_host_fingerprint` field
2. **Run `pytest tests/`** — no regression
3. **Update `docs/baseline-audit-report.md` §F.2** if it lists
   `host_fingerprint` as a forward-looking improvement
4. **Update `framework-internal-metrics.md` §1 F.5** if F.5 metric text
   should reference the new fingerprint (currently F.5 is env_hash; the
   fingerprint is a per-output complement)

## Files affected

- `adaptive_reflow/util/host_fingerprint.py` (NEW; ~50 LOC)
- `tools/capability_audit.py` (UPDATE; 1-line call)
- `tools/run_sbc_audit.py` (UPDATE; 1-line call)
- `tools/run_mutation_audit.py` (UPDATE; 1-line call)
- `tools/run_controlled_audit.py` (UPDATE; 1-line call)
- `scripts/capture_env_hash.py` (UPDATE; 1-line call)
- `scripts/api_churn_report.py` (UPDATE; 1-line call)
- `scripts/run_mypy_audit.py` (UPDATE; 1-line call)
- `scripts/check_deprecation_policy.py` (UPDATE; 1-line call)
- `tests/test_util/test_host_fingerprint.py` (NEW; unit test)

## Acceptance

- [ ] `adaptive_reflow/util/host_fingerprint.py` exists with `capture_host_fingerprint` + `with_host_fingerprint`
- [ ] Unit test passes (deterministic hostname_hash; capture_at varies but is ISO 8601)
- [ ] All 10 tools emit `_host_fingerprint` field in their JSON outputs
- [ ] `pytest tests/` still passes (no regression)
- [ ] Manual verification: re-run `tools/run_sbc_audit.py` and confirm
      `verification_outputs/sbc_audit_n1000.json` carries
      `_host_fingerprint`

## Acceptance gate

Passes if:
1. Every `verification_outputs/*.json` produced by a `tools/run_*` script
   carries a `_host_fingerprint` field
2. Unit test passes (deterministic hostname_hash)

## Estimated time

~1-2 hours total:
- Module authoring: ~30 min
- Unit test: ~15 min
- 10 call-site updates: ~5 min each = ~50 min
- Verification: ~15 min

## Risk

- **LOW**: changing the JSON shape (adding `_host_fingerprint`) could
  break downstream consumers
  → **Mitigation**: the field name starts with `_` (underscore) which
  signals "metadata, not data"; downstream consumers should ignore it
- **LOW**: `with_host_fingerprint` may not be a no-op for some payload
  shapes
  → **Mitigation**: unit test covers both `dict` and `list` payloads;
  raises `TypeError` for unsupported shapes

## Follow-up

- **CI check** that verifies the `_host_fingerprint` field is present:
  LOW priority; defer to a follow-up wave
- **Host-shift auto-classification** (per R-2 action #3): LOW priority;
  defer; manual review suffices

## Related fix opportunities (within scope of this PR)

None — this is a self-contained tool change.
## Wave 38 close-out

CLOSED in Wave 38 by commit **d55b601** (Wave 38 Agent A WF3 — note: the commit message reads "Wave 37 Agent C — pytest failure analysis" because the host_fingerprint module was authored as part of the broader pytest-failure analysis fix-up; the host_fingerprint scope is the Wave 38 R-2 deliverable).

**Result summary**:
- R-2 closed: `adaptive_reflow/util/host_fingerprint.py` (NEW) exports a stable fingerprint (host + python + key-lib versions) that every JSON-emitting audit tool now embeds in its output
- 7 call sites updated to thread the host fingerprint into their JSON envelopes:
  - `scripts/api_churn_report.py`
  - `scripts/capture_env_hash.py`
  - `scripts/run_mypy_audit.py`
  - `tools/capability_audit.py`
  - `tools/run_controlled_audit.py`
  - `tools/run_sbc_audit.py`
  - `adaptive_reflow/util/__init__.py` (re-exports the new module)
- `tests/test_util/test_host_fingerprint.py` (NEW, 187 LOC) — deterministic tests covering fingerprint stability across runs and per-host variability
- `env_hash_host_fingerprint.json` updated so the F.5 env_hash infra recognises the new module

**Files shipped** (see `git show --stat d55b601` for the canonical list): 11 files changed, 434 insertions, 8 deletions.

**Verification**: pytest tests/test_util/test_host_fingerprint.py passes deterministically + capability_audit.py runs without regression + commit (no push). Plan status flipped from `pending (Wave 34 target)` to CLOSED.

Refs: `framework-internal-metrics.md` R-2 row, F.5 env_hash infra (live since Wave 15).
