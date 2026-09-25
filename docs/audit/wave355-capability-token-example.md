# Wave 355 P5 — §3.4 capability-token handshake concrete SHA-256 example

**Date:** 2026-09-25
**Wave:** 355 P5 (USER AUTHORIZED, NO PUSH)
**Author:** ultracode subagent (Wave 355 remaining-tasks sweep)
**Scope:** paper §3.4 additive SHA-256 capability-token example + audit note. Pure doc, no code,
no experiments, no D.4 changes.

## 1. What changed

`docs/drafts/paper-A-final.md` §3.4 gained an additive §3.4.2 subsection
("Concrete SHA-256 capability-token example (Wave 355 synthetic-continuous handshake
artifact)") inserted between the §3.4.1 pseudocode block and the §3.5 heading. No
numbers were edited, no claim wording was changed, no claim status was promoted.
The §3.4 main body, the §3.4.1 pseudocode, and all surrounding §3.3 / §3.5 / §3.6
/ §3.7 paragraphs are byte-identical to the prior revision. The §3.4.2 addition
is purely additive prose + a 1-row SHA-256 table + a 4-line payload-structure
decomposition + a 3-line `bash` reproducibility recipe + 1 cross-reference.

The §3.5 hash-chained ledger example added in Wave 353 P3 is preserved verbatim
(no §3.5.2 addition); §3.4.2 closes the symmetry gap by anchoring the per-round
capability-handshake invariant on a byte-stable artifact at
`verification_outputs/wave355-capability-token-example/` mirroring the way
§3.5.1 anchored the per-round ledger invariant on
`verification_outputs/wave349-r1-3seed-gpu/`.

The verification artifact
`verification_outputs/wave355-capability-token-example/synthetic_continuous_capability_token.json`
(762 bytes, SHA-256 `584f8e02c3eda4fde2bfe1f65651cca6ec2cb9063eea42c70ce15c0ae8b619c8`)
was generated from `SyntheticContinuousAdapter.capabilities()` via
`dataclasses.asdict` + `json.dumps(..., sort_keys=True, separators=(",", ":"))`,
the same canonicalisation function used by `compute_ledger_row_hash` (§3.5
algorithm signature).

## 2. Why now

§3.4 introduced the capability-token handshake concept in abstract terms
(`AdapterCapabilities` dataclass, 9 bool flags, per-channel domain map, fail-closed
audit trail, per-round invocation at every round boundary). A reviewer reading
the paper §3.4 alone would have no concrete byte-level artifact to point at for
"what does a capability-token actually look like in this repo". The
`SyntheticContinuousAdapter.capabilities()` token is the highest-fidelity
byte-addressable capability-handshake artifact the repo ships — 9 bool flags
exercised, 4-channel `supported_channels` tuple, 4-entry `channel_domains` map,
default `state_shape = (2,)`, no backend materialiser opt-in — and it is the
exact surface the D.4 regression suite pins via
`tests/test_adapter_capabilities_dataclass.py` (30/30 PASS). Anchoring §3.4 to
that artifact closes the gap between "the engine consumes
`capability_token=adapter.capabilities()` at every round boundary" and "here is
the exact 64-hex-char byte-level token a reviewer would re-derive via a single
`dataclasses.asdict` call".

## 3. Concrete capability-token anchor (additive §3.4.2 contents)

| artifact | bytes | sha256 | role |
|---|---:|---|---|
| `verification_outputs/wave355-capability-token-example/synthetic_continuous_capability_token.json` | 762 | `584f8e02c3eda4fde2bfe1f65651cca6ec2cb9063eea42c70ce15c0ae8b619c8` | `SyntheticContinuousAdapter` capability-token: 8/9 bool flags = `True` (all except `has_discrete_channels`); `supported_channels = ("coordinate", "charge", "coordinate.continuous", "charge.continuous")`; `channel_domains` maps all 4 → `"continuous"`; `state_shape = (2,)`; `materializer / materializer_instance / required_mixer = None` |
| (derived) inner pretty-print digest | n/a | `a7e9620e82f5953dfe6bb112fc74de4fc6ae6b665cafbc273f0ea16a80d2daab` | SHA-256 over `json.dumps(..., sort_keys=True, indent=2)` — isolates field-content digest from on-disk encoding |

Both hex hashes were re-derived in this wave via `sha256sum` against the on-disk
bytes (compact format) and `hashlib.sha256` (pretty-printed format); no hash in
§3.4.2 was copied from a prior audit doc without re-verification.

## 4. Reproducibility recipe (additive §3.4.2 bash block)

```bash
cd verification_outputs/wave355-capability-token-example
sha256sum synthetic_continuous_capability_token.json    # must equal 584f8e02c3eda4fde2bfe1f65651cca6ec2cb9063eea42c70ce15c0ae8b619c8
```

A regenerated token whose bytes diverge (different `supported_channels` tuple,
flipped `has_discrete_channels` bit, non-default `state_shape`, or any
non-empty `materializer_instance`) fails the digest check. The token
byte-format is the canonical `json.dumps(..., sort_keys=True,
separators=(",", ":"))` output — same canonicalisation as
`compute_ledger_row_hash`'s `str()` / `tuple()` / `dict()` field serialisation
(§3.5 algorithm signature), so a hand-edited token whose key-ordering is
re-arranged (e.g. swap `channel_domains` and `channel_shapes` positions) breaks
the digest at the same layer a hand-edited ledger row would. The canonical
regeneration recipe (for reviewers who want to re-derive the bytes) is:

```python
import dataclasses, json
from adaptive_reflow.adapters.synthetic import SyntheticContinuousAdapter

token = SyntheticContinuousAdapter().capabilities()
raw = json.dumps(dataclasses.asdict(token), sort_keys=True, separators=(",", ":")).encode("utf-8")
assert hashlib.sha256(raw).hexdigest() == "584f8e02c3eda4fde2bfe1f65651cca6ec2cb9063eea42c70ce15c0ae8b619c8"
```

## 5. Observed vs interpretation vs gap

### 5.1 Observed facts (re-derived 2026-09-25)

- `sha256sum verification_outputs/wave355-capability-token-example/synthetic_continuous_capability_token.json`
  → `584f8e02c3eda4fde2bfe1f65651cca6ec2cb9063eea42c70ce15c0ae8b619c8` (762 bytes)
- Re-derived inner pretty-print digest (hashlib.sha256 over `json.dumps(..., indent=2)`)
  → `a7e9620e82f5953dfe6bb112fc74de4fc6ae6b665cafbc273f0ea16a80d2daab`
- `python3 tools/check_claims_consistency.py` → "No drift detected." (61 ACTIVE
  claims, 0 provisional, 2 deprecated; CLM-040 forced to PROVISIONAL unchanged)
- `python3 -m pytest tests/test_d4_regression_vectors.py -q` → 30/30 PASS
- `mkdocs build --strict` → 0 errors (`Documentation built in 24.89 seconds`)
- `SyntheticContinuousAdapter.capabilities()` returns 24-field `AdapterCapabilities`
  with 8/9 bool flags = `True` and `has_discrete_channels = False`
- The canonical `supported_channels` tuple is `("coordinate", "charge",
  "coordinate.continuous", "charge.continuous")` — same 4 entries that the
  `_SYNTHETIC_CHANNEL_DOMAINS` mapping declares at
  `adaptive_reflow/adapters/synthetic.py:74`

### 5.2 Interpretation

§3.4.2 is the symmetric counterpart to §3.5.1. §3.5.1 anchors the per-round
ledger invariant `SHA-256(canonical(fields) ∥ h_{i-1})` on a byte-stable
artifact at `verification_outputs/wave349-r1-3seed-gpu/` (two seed manifests +
aggregator SHA256SUMS, 805 + 805 + 2642 bytes). §3.4.2 anchors the per-round
capability-handshake invariant (the `capability_token` field that crosses
`StateBundle`'s boundary into `run_round(...)`) on a byte-stable artifact at
`verification_outputs/wave355-capability-token-example/` (one 762-byte
`AdapterCapabilities` JSON). Both artifacts are re-derivable from a single
canonical serialisation function: `sha256sum` for the on-disk bytes,
`json.dumps(..., sort_keys=True, separators=(",", ":"))` for the field content.
This is the artifact-level instantiation of the §3.4 handshake pattern: any
byte-level edit to the token payload propagates to a different `584f8e02…`
digest and the per-round `_check_capabilities_advertise_dispatch` invocation
re-derives the audit string from the new payload.

### 5.3 Gap

**None.** The `verification_outputs/wave355-capability-token-example/`
directory is the byte-stable artifact the §3.4.2 example references; the SHA-256
was re-derived in this wave; the D.4 regression suite continues to pass 30/30;
the claims consistency check reports no drift; the mkdocs build passes
strict-mode. The §3.5 hash-chained ledger example added in Wave 353 P3 is
preserved verbatim and continues to anchor the §3.5 algorithm signature on the
`verification_outputs/wave349-r1-3seed-gpu/` artifact. The §3.4.2 example is
the additive counterpart that closes the §3.4 ↔ §3.5 symmetry gap; no §3.5
modification was required (Wave 353 P3 already added the ledger-side example).

## 6. Files touched (additive only — no destructive edits)

- `docs/drafts/paper-A-final.md` — added §3.4.2 "Concrete SHA-256
  capability-token example (Wave 355 synthetic-continuous handshake artifact)"
  between §3.4.1 (pseudocode) and §3.5 heading. No number / wording / status
  change anywhere in the file.
- `verification_outputs/wave355-capability-token-example/synthetic_continuous_capability_token.json`
  — new byte-stable 762-byte artifact generated from
  `SyntheticContinuousAdapter.capabilities()`.
- `docs/audit/wave355-capability-token-example.md` — this audit note.

No code under `adaptive_reflow/`, no test files, no claims wording, no
governance files, no vendored upstream (`data/`) were modified.

## 7. Hard guardrail compliance

- **NO-PUSH policy.** No `git push` issued; commit is local-only.
- **Vendored upstream sacred.** No file under `data/FlowMol3/`,
  `data/LineageFlow/`, `data/Kanzi/`, or any of the 9 vendored repos was
  touched.
- **ADDITIVE only.** §3.4.2 is appended; no §3.4 / §3.5 / §3.6 / §3.7 paragraph
  was edited, no number was changed, no claim was promoted by wording alone.
- **TNNLS submission freeze.** No file in `tnnls_submission/` was touched; no
  SHA-256 in MANIFEST.md / cover_letter.md was regenerated.
- **D.4 30/30 PASS.** Verified before commit (above).
- **Per-phase audit doc.** This file is the `wave355-capability-token-example.md`
  audit note per the format mirrored from Wave 353 P3.